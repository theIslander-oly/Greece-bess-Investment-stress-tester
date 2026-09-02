"""The subcommand registry.

A command is a name, its help text, a function that adds its arguments to a
parser, and a function that runs it. Grouping those four things means the
parser and the dispatch table are built from one list, so a command cannot be
declared and left unhandled, or handled under a name nothing declares.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """One `greek-bess` subcommand."""

    name: str
    help: str
    configure: Callable[[argparse.ArgumentParser], None]
    run: Callable[[argparse.Namespace], int]
