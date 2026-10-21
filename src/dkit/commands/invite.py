"""``dkit invite`` - build a correct OAuth2 bot invite URL."""

from __future__ import annotations

import argparse
from typing import Any
from urllib.parse import quote, urlencode

from dkit.commands.perms import permission_flags
from dkit.core import data
from dkit.core.errors import UsageError
from dkit.core.output import Printer
from dkit.core.parse import looks_like_int, parse_int, split_names
from dkit.core.registry import Command
from dkit.core.suggest import suggestion_hint

DESCRIPTION = """\
Build an OAuth2 authorization URL that adds your application to a server.
Permissions may be given as names or as an integer; query parameters are
URL-encoded, with scopes separated by %20 as the official documentation shows.
"""


def _oauth2() -> dict[str, Any]:
    return data.load("oauth2")


def validate_client_id(raw: str) -> str:
    """Check that the client ID is a plain numeric snowflake."""
    candidate = raw.strip()
    if not candidate:
        raise UsageError("--client-id is empty")
    if not candidate.isdigit():
        raise UsageError(
            f"--client-id must be numeric: {raw!r}",
            hint=("an application (client) ID is a Discord snowflake, e.g. 157730590492196864"),
        )
    return candidate


def validate_scopes(raw: str | None) -> list[str]:
    """Split and validate the requested OAuth2 scopes."""
    known = _oauth2()["scopes"]
    scopes = split_names(raw) if raw is not None else list(_oauth2()["default_scopes"])
    if not scopes:
        raise UsageError(
            "--scopes did not contain any scope names",
            hint="example: --scopes bot,applications.commands",
        )

    for scope in scopes:
        if scope not in known:
            raise UsageError(
                f"unknown OAuth2 scope: {scope!r}",
                hint=suggestion_hint(scope, known),
            )

    # De-duplicate while preserving the order the user asked for.
    return list(dict.fromkeys(scopes))


def resolve_permissions(raw: str | None) -> tuple[int | None, list[str]]:
    """Return the permissions integer and the names it covers.

    ``raw`` may be an integer or a comma-separated list of permission names.
    ``None`` means the caller did not request any permissions.
    """
    if raw is None:
        return None, []

    flags = permission_flags()
    if looks_like_int(raw):
        value = parse_int(raw, what="--perms value")
    else:
        names = split_names(raw)
        if not names:
            raise UsageError(
                "--perms did not contain any permission names",
                hint="example: --perms SEND_MESSAGES,EMBED_LINKS",
            )
        value = flags.value_of(names)
    return value, [flag.name for flag in flags.flags_in(value)]


def build_url(client_id: str, scopes: list[str], permissions: int | None) -> str:
    """Assemble the authorization URL with properly encoded query parameters."""
    params: list[tuple[str, str]] = [
        ("client_id", client_id),
        ("scope", " ".join(scopes)),
    ]
    if permissions is not None:
        params.append(("permissions", str(permissions)))
    query = urlencode(params, quote_via=quote, safe="")
    return f"{_oauth2()['authorize_url']}?{query}"


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Register the arguments of ``dkit invite``."""
    parser.add_argument(
        "--client-id",
        required=True,
        metavar="ID",
        help="your application's client ID (a numeric snowflake)",
    )
    parser.add_argument(
        "--perms",
        metavar="NAMES|NUMBER",
        help="permissions to request, as names or an integer",
    )
    parser.add_argument(
        "--scopes",
        metavar="SCOPES",
        help="comma-separated OAuth2 scopes (default: bot,applications.commands)",
    )


def run(args: argparse.Namespace, out: Printer) -> dict[str, Any]:
    """Execute ``dkit invite``."""
    client_id = validate_client_id(args.client_id)
    scopes = validate_scopes(args.scopes)
    permissions, permission_names = resolve_permissions(args.perms)

    url = build_url(client_id, scopes, permissions)
    warnings: list[str] = []
    if permissions is not None and "bot" not in scopes:
        warnings.append(
            "permissions only take effect together with the 'bot' scope, which is not in --scopes"
        )
    if "ADMINISTRATOR" in permission_names:
        warnings.append(
            "the requested permissions include ADMINISTRATOR, which grants "
            "every permission and bypasses channel overwrites"
        )

    out.heading("Invite URL")
    out.line(f"  {out.style(url, 'blue', 'bold')}")
    out.line()
    out.field("Client ID", client_id)
    out.field("Scopes", ", ".join(scopes))
    if permissions is None:
        out.field("Permissions", out.style("(none requested)", "dim"))
    else:
        out.field("Permissions", str(permissions))
        for name in permission_names:
            out.line(f"    {out.style('-', 'dim')} {name}")
    out.warnings(warnings)

    return {
        "url": url,
        "client_id": client_id,
        "scopes": scopes,
        "permissions": None if permissions is None else str(permissions),
        "permission_names": permission_names,
        "warnings": warnings,
        "source": data.provenance("oauth2"),
    }


COMMAND = Command(
    name="invite",
    help="build an OAuth2 invite URL for your bot",
    description=DESCRIPTION,
    add_arguments=add_arguments,
    run=run,
    epilog=(
        "examples:\n"
        "  dkit invite --client-id 157730590492196864\n"
        "  dkit invite --client-id 157730590492196864 --perms SEND_MESSAGES,EMBED_LINKS\n"
        "  dkit invite --client-id 157730590492196864 --perms 68608 --scopes bot\n"
    ),
)
