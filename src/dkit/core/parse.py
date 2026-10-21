"""Input parsing shared by the commands.

All integer handling goes through Python's arbitrary-precision ``int``; no
value is ever truncated to 32 or 64 bits.
"""

from __future__ import annotations

from datetime import datetime, timezone

from dkit.core.errors import UsageError

#: Separators accepted inside a list of names.
_NAME_SEPARATORS = ",;"


def parse_int(text: str, *, what: str = "value") -> int:
    """Parse a non-negative integer in decimal, ``0x`` hex or ``0b`` binary form.

    Raises:
        UsageError: if the text is not a non-negative integer.
    """
    raw = text.strip().replace("_", "")
    if not raw:
        raise UsageError(f"{what} is empty")
    if raw.startswith("-"):
        raise UsageError(f"{what} must not be negative: {text!r}")

    lowered = raw.lower()
    try:
        if lowered.startswith(("0x", "0b", "0o")):
            return int(raw, 0)
        if not raw.isdigit():
            raise ValueError(raw)
        return int(raw, 10)
    except ValueError:
        raise UsageError(
            f"{what} is not a valid integer: {text!r}",
            hint="pass a decimal number, or a 0x-prefixed hexadecimal number",
        ) from None


def looks_like_int(text: str) -> bool:
    """Return ``True`` if ``text`` should be treated as a number, not a name."""
    raw = text.strip().replace("_", "").lower()
    if not raw:
        return False
    if raw.startswith(("0x", "0b", "0o")):
        return len(raw) > 2 and all(c.isalnum() for c in raw[2:])
    return raw.isdigit()


def normalise_name(name: str) -> str:
    """Normalise a flag name: upper case, spaces and dashes become underscores."""
    return name.strip().upper().replace("-", "_").replace(" ", "_")


def split_names(text: str) -> list[str]:
    """Split a comma-separated list of names, dropping empty entries."""
    buffer = text
    for separator in _NAME_SEPARATORS:
        buffer = buffer.replace(separator, "\n")
    return [part.strip() for part in buffer.split("\n") if part.strip()]


def parse_datetime(text: str, *, what: str = "date") -> datetime:
    """Parse an ISO-8601 timestamp into a timezone-aware UTC ``datetime``.

    A trailing ``Z`` is accepted, and a timestamp without an offset is
    interpreted as UTC.
    """
    raw = text.strip()
    if not raw:
        raise UsageError(f"{what} is empty")

    candidate = raw
    if candidate.endswith(("Z", "z")):
        # datetime.fromisoformat only understands 'Z' from Python 3.11 on.
        candidate = f"{candidate[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        raise UsageError(
            f"{what} is not a valid ISO-8601 timestamp: {text!r}",
            hint="example: 2016-04-30T11:18:25Z (or 2016-04-30T11:18:25.796+00:00)",
        ) from None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_datetime(moment: datetime) -> str:
    """Render a UTC datetime as ISO-8601 with millisecond precision."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + (
        f"{moment.microsecond // 1000:03d}Z"
    )
