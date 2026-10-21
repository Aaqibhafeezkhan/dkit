"""Error types with their associated process exit codes."""

from __future__ import annotations

EXIT_OK = 0
EXIT_USAGE = 2


class DkitError(Exception):
    """Base class for every error raised deliberately by dkit."""

    exit_code = EXIT_USAGE


class UsageError(DkitError):
    """The user passed something dkit cannot work with.

    Carries an optional ``hint`` that is printed below the error message to
    point the user at the fix.
    """

    exit_code = EXIT_USAGE

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.hint = hint
