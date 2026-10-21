"""Tests for ``dkit perms``."""

from __future__ import annotations

import pytest

from dkit.commands.perms import permission_flags
from dkit.core.errors import UsageError


def test_decode_single_bit() -> None:
    flags = permission_flags()
    assert [flag.name for flag in flags.flags_in(2048)] == ["SEND_MESSAGES"]


def test_decode_combination() -> None:
    flags = permission_flags()
    value = 1 << 11 | 1 << 14 | 1 << 28
    assert [flag.name for flag in flags.flags_in(value)] == [
        "SEND_MESSAGES",
        "EMBED_LINKS",
        "MANAGE_ROLES",
    ]


def test_decode_zero_is_empty() -> None:
    assert permission_flags().flags_in(0) == []


def test_encode_from_names() -> None:
    flags = permission_flags()
    assert flags.value_of(["SEND_MESSAGES", "MANAGE_ROLES"]) == 268437504


def test_encode_is_order_independent_and_idempotent() -> None:
    flags = permission_flags()
    assert flags.value_of(["MANAGE_ROLES", "SEND_MESSAGES"]) == flags.value_of(
        ["SEND_MESSAGES", "MANAGE_ROLES"]
    )
    assert flags.value_of(["SEND_MESSAGES", "SEND_MESSAGES"]) == 2048


def test_names_are_case_and_separator_insensitive() -> None:
    flags = permission_flags()
    assert flags.resolve("send_messages").name == "SEND_MESSAGES"
    assert flags.resolve("Send-Messages").name == "SEND_MESSAGES"
    assert flags.resolve("  send messages  ").name == "SEND_MESSAGES"


def test_round_trip_every_permission_individually() -> None:
    """name -> number -> name must hold for every known permission."""
    flags = permission_flags()
    for flag in flags:
        value = flags.value_of([flag.name])
        assert [found.name for found in flags.flags_in(value)] == [flag.name]


def test_round_trip_all_permissions_at_once() -> None:
    flags = permission_flags()
    names = list(flags.names)
    value = flags.value_of(names)
    assert value == flags.mask
    assert [flag.name for flag in flags.flags_in(value)] == names


def test_unknown_bits_are_reported() -> None:
    flags = permission_flags()
    # Bit 47 is unassigned, bit 63 is far beyond anything documented.
    value = flags.mask | 1 << 47 | 1 << 63
    assert flags.unknown_bits(value) == [47, 63]


def test_unknown_name_raises_with_a_suggestion() -> None:
    with pytest.raises(UsageError) as excinfo:
        permission_flags().resolve("SEND_MESSAGE")
    assert "unknown permission name" in str(excinfo.value)
    assert "SEND_MESSAGES" in (excinfo.value.hint or "")


# --- CLI behaviour ------------------------------------------------------


def test_cli_decode(cli) -> None:
    result = cli("perms", "2048")
    assert result.exit_code == 0
    assert "SEND_MESSAGES" in result.stdout


def test_cli_decode_json(cli) -> None:
    payload = cli("--json", "perms", "268437504").json
    assert payload["names"] == ["SEND_MESSAGES", "MANAGE_ROLES"]
    assert payload["value"] == "268437504"
    assert payload["hex"] == "0x0000000010000800"
    assert payload["unknown_bits"] == []


def test_cli_encode_json(cli) -> None:
    payload = cli("--json", "perms", "--names", "SEND_MESSAGES,MANAGE_ROLES").json
    assert payload["value"] == "268437504"
    assert payload["names"] == ["SEND_MESSAGES", "MANAGE_ROLES"]


def test_cli_round_trip_through_the_cli(cli) -> None:
    """names -> number -> names, both directions through the CLI."""
    encoded = cli("--json", "perms", "--names", "VIEW_CHANNEL,SEND_MESSAGES").json
    decoded = cli("--json", "perms", encoded["value"]).json
    assert decoded["names"] == ["VIEW_CHANNEL", "SEND_MESSAGES"]


def test_cli_accepts_hexadecimal(cli) -> None:
    assert cli("--json", "perms", "0x800").json["names"] == ["SEND_MESSAGES"]


def test_cli_value_is_a_string_for_big_integers(cli) -> None:
    """Permissions are emitted as strings, as the Discord API itself does."""
    payload = cli("--json", "perms", "--names", "BYPASS_SLOWMODE").json
    assert payload["value"] == "4503599627370496"
    assert isinstance(payload["value"], str)


def test_cli_warns_about_administrator(cli) -> None:
    result = cli("perms", "8")
    assert result.exit_code == 0
    assert "ADMINISTRATOR" in result.stderr


def test_cli_warns_about_unknown_bits(cli) -> None:
    result = cli("perms", str(1 << 47))
    assert result.exit_code == 0
    assert "no name for" in result.stderr


def test_cli_zero_reports_nothing_set(cli) -> None:
    result = cli("perms", "0")
    assert result.exit_code == 0
    assert "no permissions set" in result.stdout


@pytest.mark.parametrize(
    "argv",
    [
        ("perms",),
        ("perms", "--names", "SEND_MESSAGE"),
        ("perms", "--names", "NOPE_NOT_REAL"),
        ("perms", "--names", ""),
        ("perms", "--names", ",,,"),
        ("perms", "abc"),
        ("perms", "-1"),
        ("perms", "8", "--names", "ADMINISTRATOR"),
    ],
)
def test_cli_invalid_input_exits_with_code_2(cli, argv: tuple[str, ...]) -> None:
    result = cli(*argv)
    assert result.exit_code == 2
    assert result.stderr.startswith("error:")
