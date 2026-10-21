"""Regression tests for the edge cases requested in issue #8."""

from __future__ import annotations

import json

import pytest

from dkit.cli import main
from dkit.commands import COMMANDS


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (("perms", "２０４８"), "2048"),
        (("perms", "2048\n"), "2048"),
    ],
    ids=["full-width-digits", "trailing-newline"],
)
def test_integer_input_accepts_unicode_digits_and_xargs_newline(cli, argv, expected: str) -> None:
    result = cli("--json", *argv)
    assert result.exit_code == 0
    assert result.json["value"] == expected


def test_name_list_accepts_non_breaking_space_after_separator(cli) -> None:
    result = cli(
        "--json",
        "perms",
        "--names",
        "SEND_MESSAGES,\u00a0MANAGE_ROLES",
    )
    assert result.exit_code == 0
    assert result.json["names"] == ["SEND_MESSAGES", "MANAGE_ROLES"]
    assert result.json["value"] == "268437504"


@pytest.mark.parametrize(
    ("argv", "keys"),
    [
        (
            ("snowflake", "0"),
            {
                "id",
                "created_at",
                "unix_ms",
                "discord_ms",
                "worker_id",
                "process_id",
                "increment",
                "source",
            },
        ),
        (
            ("perms", "2048"),
            {
                "value",
                "hex",
                "bit_count",
                "permissions",
                "names",
                "unknown_bits",
                "warnings",
                "source",
            },
        ),
        (
            ("intents", "GUILDS"),
            {
                "direction",
                "value",
                "value_int",
                "hex",
                "bit_count",
                "intents",
                "names",
                "privileged",
                "unknown_bits",
                "warnings",
                "source",
            },
        ),
        (
            ("invite", "--client-id", "157730590492196864"),
            {
                "url",
                "client_id",
                "scopes",
                "permissions",
                "permission_names",
                "warnings",
                "source",
            },
        ),
        (
            ("timestamp", "2026-10-20T08:30:00Z"),
            {"timestamp", "unix", "styles", "source"},
        ),
    ],
    ids=["snowflake", "perms", "intents", "invite", "timestamp"],
)
def test_json_payload_schema_is_stable(cli, argv: tuple[str, ...], keys: set[str]) -> None:
    result = cli("--json", *argv)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert set(payload) == keys


@pytest.mark.parametrize(
    ("command_name", "example"),
    [
        ("snowflake", "dkit snowflake 175928847299117063"),
        ("perms", "dkit perms 2048"),
        ("invite", "dkit invite --client-id 157730590492196864"),
        ("intents", "dkit intents GUILDS,GUILD_MESSAGES,MESSAGE_CONTENT"),
        ("timestamp", "dkit timestamp 2026-10-20T08:30:00Z"),
    ],
)
def test_command_help_keeps_documented_examples(
    capsys, command_name: str, example: str
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main([command_name, "--help"])
    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "examples:" in output.lower()
    assert example in output


def test_every_registered_command_has_an_examples_section() -> None:
    for command in COMMANDS:
        assert "examples:" in command.epilog.lower()
        assert f"dkit {command.name} " in command.epilog
