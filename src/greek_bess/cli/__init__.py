"""Command-line entry points for market data and battery dispatch.

Each subcommand lives in the module for its stage of the workflow and declares
itself in that module's `COMMANDS`; `_main` assembles them into one parser and
one dispatch table.
"""

from __future__ import annotations

from ._main import COMMANDS, build_parser, main
from ._registry import Command

__all__ = ["COMMANDS", "Command", "build_parser", "main"]
