"""Shared test helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from dkit.cli import main


@dataclass
class Result:
    """The outcome of one CLI invocation."""

    exit_code: int
    stdout: str
    stderr: str

    @property
    def json(self) -> dict:
        """Parse stdout as JSON (for ``--json`` invocations)."""
        return json.loads(self.stdout)


@pytest.fixture
def cli(capsys, monkeypatch):
    """Run the CLI in-process and capture its output and exit code."""
    # Keep output deterministic regardless of the developer's environment.
    monkeypatch.delenv("NO_COLOR", raising=False)

    def run(*argv: str) -> Result:
        exit_code = main(list(argv))
        captured = capsys.readouterr()
        return Result(exit_code=exit_code, stdout=captured.out, stderr=captured.err)

    return run
