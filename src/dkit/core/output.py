"""Terminal and JSON output.

Commands build a JSON-serialisable payload and, in text mode, render it
through a :class:`Printer`. The printer's text helpers are no-ops in JSON
mode, so a command never has to branch on the output format.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterable
from typing import Any, TextIO

_RESET = "\033[0m"
_STYLES = {
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
}


def colors_enabled(*, no_color: bool, stream: TextIO) -> bool:
    """Decide whether ANSI colors should be used.

    Colors are off when ``--no-color`` is passed, when the ``NO_COLOR``
    environment variable is set (see https://no-color.org), or when the
    stream is not an interactive terminal.
    """
    if no_color or os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


class Printer:
    """Writes human-readable text, unless the CLI is in ``--json`` mode."""

    def __init__(
        self,
        *,
        json_mode: bool = False,
        color: bool = False,
        stream: TextIO | None = None,
        error_stream: TextIO | None = None,
    ) -> None:
        self.json_mode = json_mode
        self.color = color
        self.stream = stream if stream is not None else sys.stdout
        self.error_stream = error_stream if error_stream is not None else sys.stderr

    # -- styling ---------------------------------------------------------
    def style(self, text: str, *names: str) -> str:
        """Wrap ``text`` in the named ANSI styles, if colors are enabled."""
        if not self.color or not names:
            return text
        prefix = "".join(_STYLES[name] for name in names if name in _STYLES)
        return f"{prefix}{text}{_RESET}" if prefix else text

    # -- text output (suppressed in JSON mode) ---------------------------
    def line(self, text: str = "") -> None:
        """Print one line of human-readable output."""
        if not self.json_mode:
            print(text, file=self.stream)

    def heading(self, text: str) -> None:
        """Print a bold heading."""
        self.line(self.style(text, "bold"))

    def field(self, label: str, value: str, *, width: int = 12) -> None:
        """Print an indented ``label: value`` row with aligned values."""
        self.line(f"  {self.style(label.ljust(width), 'cyan')} {value}")

    def note(self, text: str) -> None:
        """Print a dimmed note."""
        self.line(self.style(text, "dim"))

    def warnings(self, messages: Iterable[str]) -> None:
        """Print warnings to stderr so stdout stays pipe-friendly."""
        if self.json_mode:
            return
        for message in messages:
            label = self.style("warning:", "yellow", "bold")
            print(f"{label} {message}", file=self.error_stream)

    # -- machine-readable output -----------------------------------------
    def emit_json(self, payload: dict[str, Any]) -> None:
        """Print the payload as indented JSON (JSON mode only)."""
        if self.json_mode:
            print(json.dumps(payload, indent=2, sort_keys=False), file=self.stream)

    def error(self, message: str, *, hint: str | None = None) -> None:
        """Print an error, and an optional hint, to stderr."""
        label = self.style("error:", "red", "bold")
        print(f"{label} {message}", file=self.error_stream)
        if hint:
            print(f"  {self.style(hint, 'dim')}", file=self.error_stream)
