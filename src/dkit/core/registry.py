"""The command registry.

A command is a small record of metadata plus two functions: one that adds
its arguments to an ``argparse`` parser, and one that runs it. Adding a
command therefore means adding one module and listing it in
``dkit.commands.COMMANDS``.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from dkit.core.output import Printer

#: Signature of a command's argument hook.
AddArguments = Callable[[argparse.ArgumentParser], None]

#: Signature of a command's entry point. It returns the JSON payload.
Run = Callable[[argparse.Namespace, Printer], dict[str, Any]]


@dataclass(frozen=True)
class Command:
    """Everything the CLI needs to expose one subcommand."""

    name: str
    help: str
    add_arguments: AddArguments
    run: Run
    description: str | None = None
    epilog: str | None = None
