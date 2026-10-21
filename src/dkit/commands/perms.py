"""``dkit perms`` - translate between Discord permission integers and names."""

from __future__ import annotations

import argparse
from typing import Any

from dkit.core import data
from dkit.core.bits import Flag, FlagSet
from dkit.core.errors import UsageError
from dkit.core.output import Printer
from dkit.core.parse import parse_int, split_names
from dkit.core.registry import Command

DESCRIPTION = """\
Decode a Discord permissions integer into permission names, or calculate the
integer for a list of names. Permission values exceed 32 bits, so every value
is handled as an arbitrary-precision Python integer.
"""


def permission_flags() -> FlagSet:
    """The permission flags from ``dkit/data/permissions.json``."""
    entries = data.load("permissions")["permissions"]
    return FlagSet(
        (
            Flag(
                name=entry["name"],
                bit=entry["bit"],
                description=entry["description"],
                requires_2fa=entry.get("requires_2fa", False),
                channel_types=tuple(entry.get("channel_types", ())),
            )
            for entry in entries
        ),
        label="permission",
    )


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit perms``."""
    parser.add_argument(
        "value",
        metavar="NUMBER",
        nargs="?",
        help="a permissions integer to decode, e.g. 2048 or 0x800",
    )
    parser.add_argument(
        "--names",
        metavar="NAMES",
        help="comma-separated permission names to combine into an integer",
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit perms``."""
    if args.names and args.value is not None:
        raise UsageError(
            "--names cannot be combined with a permissions number",
            hint="decode a number, or encode names, but not both at once",
        )
    if not args.names and args.value is None:
        raise UsageError(
            "no permissions value given",
            hint="examples: dkit perms 2048 | dkit perms --names SEND_MESSAGES",
        )

    flags = permission_flags()
    if args.names:
        return _encode(args.names, flags, out)
    return _decode(args.value, flags, out)


def _render(flag: Flag, out: Printer) -> None:
    marks = []
    if flag.requires_2fa:
        marks.append("2FA")
    if flag.channel_types:
        marks.append("/".join(flag.channel_types))
    suffix = f"  {out.style('[' + ', '.join(marks) + ']', 'dim')}" if marks else ""
    out.line(f"  {out.style(flag.name.ljust(36), 'green')} {flag.hex}{suffix}")


def _summary(value: int, flags: FlagSet) -> list[str]:
    warnings: list[str] = []
    unknown = flags.unknown_bits(value)
    if unknown:
        warnings.append(
            "value contains bits dkit has no name for: "
            + ", ".join(str(bit) for bit in unknown)
            + f" (data last verified {data.provenance('permissions')['last_verified']})"
        )
    if value & flags.resolve("ADMINISTRATOR").value:
        warnings.append("ADMINISTRATOR grants every permission and bypasses channel overwrites")
    return warnings


def _payload(
    value: int, matched: list[Flag], warnings: list[str], flags: FlagSet
) -> dict[str, Any]:
    return {
        "value": str(value),
        "hex": f"0x{value:016x}",
        "bit_count": len(matched),
        "permissions": [flag.as_dict() for flag in matched],
        "names": [flag.name for flag in matched],
        "unknown_bits": flags.unknown_bits(value),
        "warnings": warnings,
        "source": data.provenance("permissions"),
    }


def _decode(raw: str, flags: FlagSet, out: Printer) -> dict[str, Any]:
    value = parse_int(raw, what="permissions value")
    matched = flags.flags_in(value)
    warnings = _summary(value, flags)

    out.heading(f"Permissions {value}")
    out.note(f"  hex {value:#018x}  ({len(matched)} of {len(flags)} known permissions)")
    out.line()
    if matched:
        for flag in matched:
            _render(flag, out)
    else:
        out.note("  (no permissions set)")
    out.warnings(warnings)
    return _payload(value, matched, warnings, flags)


def _encode(raw: str, flags: FlagSet, out: Printer) -> dict[str, Any]:
    names = split_names(raw)
    if not names:
        raise UsageError(
            "--names did not contain any permission names",
            hint="example: dkit perms --names SEND_MESSAGES,MANAGE_ROLES",
        )

    matched = [flags.resolve(name) for name in names]
    value = 0
    for flag in matched:
        value |= flag.value
    # De-duplicate while keeping bit order stable.
    matched = flags.flags_in(value)
    warnings = _summary(value, flags)

    out.heading(f"Permissions {out.style(str(value), 'green', 'bold')}")
    out.note(f"  hex {value:#018x}")
    out.line()
    for flag in matched:
        _render(flag, out)
    out.warnings(warnings)
    return _payload(value, matched, warnings, flags)


COMMAND = Command(
    name="perms",
    help="decode a permissions integer, or build one from names",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit perms 2048\n"
        "  dkit perms 0x800\n"
        "  dkit perms --names SEND_MESSAGES,MANAGE_ROLES\n"
    ),
)
