"""A small bitfield engine shared by the ``perms`` and ``intents`` commands.

Both Discord permissions and gateway intents are "a name per bit" sets, so
they are modelled by the same :class:`FlagSet`. Values are plain Python
integers and may therefore be arbitrarily large; permissions already exceed
32 bits and are approaching 64.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any

from dkit.core.errors import UsageError
from dkit.core.parse import normalise_name
from dkit.core.suggest import suggestion_hint


@dataclass(frozen=True)
class Flag:
    """A single named bit."""

    name: str
    bit: int
    description: str = ""
    privileged: bool = False
    requires_2fa: bool = False
    channel_types: tuple[str, ...] = ()
    events: tuple[str, ...] = field(default=())

    @property
    def value(self) -> int:
        """The integer value of this flag, i.e. ``1 << bit``."""
        return 1 << self.bit

    @property
    def hex(self) -> str:
        """The flag value as a zero-padded 64-bit hexadecimal string."""
        return f"0x{self.value:016x}"

    def as_dict(self) -> dict[str, Any]:
        """A JSON-serialisable view of this flag."""
        payload: dict[str, Any] = {
            "name": self.name,
            "bit": self.bit,
            "value": str(self.value),
            "hex": self.hex,
            "description": self.description,
        }
        if self.channel_types:
            payload["channel_types"] = list(self.channel_types)
        if self.requires_2fa:
            payload["requires_2fa"] = True
        if self.privileged:
            payload["privileged"] = True
        if self.events:
            payload["events"] = list(self.events)
        return payload


class FlagSet:
    """An immutable collection of :class:`Flag` objects, indexed by name."""

    def __init__(self, flags: Iterable[Flag], *, label: str) -> None:
        self._flags: tuple[Flag, ...] = tuple(sorted(flags, key=lambda f: f.bit))
        self._by_name = {flag.name: flag for flag in self._flags}
        self._by_bit = {flag.bit: flag for flag in self._flags}
        self.label = label

    def __iter__(self) -> Iterator[Flag]:
        return iter(self._flags)

    def __len__(self) -> int:
        return len(self._flags)

    @property
    def names(self) -> tuple[str, ...]:
        """Every known flag name, ordered by bit position."""
        return tuple(flag.name for flag in self._flags)

    @property
    def mask(self) -> int:
        """A mask of every bit dkit knows a name for."""
        mask = 0
        for flag in self._flags:
            mask |= flag.value
        return mask

    def resolve(self, name: str) -> Flag:
        """Look up a flag by name, tolerating case and ``-``/space separators.

        Raises:
            UsageError: with a 'did you mean ...?' hint for unknown names.
        """
        key = normalise_name(name)
        try:
            return self._by_name[key]
        except KeyError:
            hint = suggestion_hint(key, self.names)
            raise UsageError(
                f"unknown {self.label} name: {name!r}",
                hint=hint,
            ) from None

    def value_of(self, names: Sequence[str]) -> int:
        """Combine the named flags into a single integer value."""
        value = 0
        for name in names:
            value |= self.resolve(name).value
        return value

    def flags_in(self, value: int) -> list[Flag]:
        """Every known flag contained in ``value``, ordered by bit position."""
        return [flag for flag in self._flags if value & flag.value]

    def unknown_bits(self, value: int) -> list[int]:
        """Bit positions set in ``value`` that dkit has no name for.

        A non-empty result usually means Discord added a flag since this
        data file was last verified.
        """
        leftover = value & ~self.mask
        return [bit for bit in range(leftover.bit_length()) if leftover >> bit & 1]
