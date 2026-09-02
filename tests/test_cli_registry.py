"""The subcommand registry has to stay coherent as commands are added.

Before the registry existed, a subcommand was declared in one place and handled
in another, and nothing connected the two: a parser entry with no matching
`elif` branch parsed fine and then fell through to an `AssertionError`, and a
branch whose name nobody declared was simply dead. These check the pairing that
replaced that arrangement.
"""

from __future__ import annotations

import unittest

from greek_bess.cli import COMMANDS, build_parser
from greek_bess.cli._main import COMMAND_MODULES


class CommandRegistryTests(unittest.TestCase):
    def test_every_declared_command_is_reachable_from_the_parser(self) -> None:
        parser = build_parser()
        (subparsers,) = [
            action
            for action in parser._actions
            if action.dest == "command" and action.choices is not None
        ]

        self.assertEqual(
            sorted(subparsers.choices), sorted(command.name for command in COMMANDS)
        )

    def test_no_two_commands_claim_the_same_name(self) -> None:
        names = [command.name for command in COMMANDS]
        self.assertEqual(sorted(names), sorted(set(names)))

    def test_every_command_carries_help_and_a_callable_pair(self) -> None:
        for command in COMMANDS:
            with self.subTest(command=command.name):
                self.assertTrue(command.help.strip(), "help text is required")
                self.assertTrue(callable(command.configure))
                self.assertTrue(callable(command.run))

    def test_each_module_contributes_at_least_one_command(self) -> None:
        # A module that stops contributing has either been emptied or dropped
        # its COMMANDS tuple, both of which silently remove subcommands.
        for module in COMMAND_MODULES:
            with self.subTest(module=module.__name__):
                self.assertTrue(module.COMMANDS)

    def test_the_registry_covers_every_command_module(self) -> None:
        declared = sum(len(module.COMMANDS) for module in COMMAND_MODULES)
        self.assertEqual(declared, len(COMMANDS))


if __name__ == "__main__":
    unittest.main()
