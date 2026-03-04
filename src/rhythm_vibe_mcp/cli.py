"""Canonical CLI for rhythm-vibe-mcp: dynamically generated from registered MCP tools.

All subcommands and options are derived exclusively from the server's tool list.
When tools are added, removed, or renamed, the CLI updates automatically.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
import json
import sys
from typing import TYPE_CHECKING, Any

from rhythm_vibe_mcp.constants.cli import (
    CLI_DESCRIPTION,
    CLI_ERROR_PREFIX,
    CLI_PROG,
    CLI_TOOL_HELP,
    CLI_TOOL_METAVAR,
    SCHEMA_KEY_DEFAULT,
    SCHEMA_KEY_DESCRIPTION,
    SCHEMA_KEY_PROPERTIES,
    SCHEMA_KEY_REQUIRED,
    SCHEMA_KEY_TYPE,
)
from rhythm_vibe_mcp.constants.json import JSON_INDENT
from rhythm_vibe_mcp.runtime_enums import JsonSchemaType
from rhythm_vibe_mcp.services.catalog import FastMcpToolCatalog

# Import server so tools are registered; then we introspect.
from rhythm_vibe_mcp.server import mcp

if TYPE_CHECKING:
    from typing import NotRequired, TypedDict

    class JsonPropertySchema(TypedDict):
        type: NotRequired[str]
        description: NotRequired[str]
        default: NotRequired[Any]

    class JsonToolSchema(TypedDict):
        properties: NotRequired[dict[str, JsonPropertySchema]]
        required: NotRequired[list[str]]


_tool_catalog = FastMcpToolCatalog(mcp)


class ServerParameters:
    """Parameters describing how a local MCP server process should be launched."""

    __slots__ = ("command", "args", "cwd")

    def __init__(self, command: str, args: list[str], cwd: str | None) -> None:
        self.command = command
        self.args = args
        self.cwd = cwd


def _coerce_scalar(value: str) -> Any:
    """Best-effort scalar coercion from CLI strings."""
    try:
        return json.loads(value)
    except Exception:
        return value


def _parse_key_value_arguments(items: list[str]) -> dict[str, Any]:
    """Parse repeated key=value arguments into a dictionary."""
    parsed: dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            continue
        key, raw_value = item.split("=", 1)
        key = key.strip()
        if not key:
            continue
        parsed[key] = _coerce_scalar(raw_value)
    return parsed


def _parse_call_arguments(args: argparse.Namespace) -> dict[str, Any]:
    """Merge JSON argument payload with repeated key=value CLI args.

    Repeated key=value args override values from --json-args.
    """
    payload: dict[str, Any] = {}
    json_args = getattr(args, "json_args", "") or ""
    if json_args:
        parsed_json = json.loads(json_args)
        if isinstance(parsed_json, dict):
            payload.update(parsed_json)
    kv_items = list(getattr(args, "arg", []) or [])
    payload.update(_parse_key_value_arguments(kv_items))
    return payload


def _server_parameters(args: argparse.Namespace) -> ServerParameters:
    """Build server launch parameters used by MCP client workflows."""
    server_command = getattr(args, "server_command", "python")
    server_args = list(getattr(args, "server_arg", []) or [])
    server_cwd_raw = getattr(args, "server_cwd", None)
    server_cwd = str(server_cwd_raw) if server_cwd_raw else None
    launch_args = server_args or [
        "-m",
        "rhythm_vibe_mcp.server",
        "--transport",
        "stdio",
    ]
    return ServerParameters(command=server_command, args=launch_args, cwd=server_cwd)


def _schema_type_to_parser(schema: dict[str, Any]) -> type:
    """Map JSON schema type to argparse type.

    Args:
    ----
        schema (Any): Description for schema.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of _schema_type_to_parser logic.

    """
    t = str(schema.get(SCHEMA_KEY_TYPE, JsonSchemaType.STRING.value))
    if t == JsonSchemaType.INTEGER.value:
        return int
    if t == JsonSchemaType.NUMBER.value:
        return float
    if t == JsonSchemaType.BOOLEAN.value:
        return bool
    return str


def _add_tool_subparser(
    subparsers: argparse._SubParsersAction,
    tool_name: str,
    description: str,
    parameters: dict[str, Any],
) -> None:
    """Add one subparser for a tool, with arguments from its JSON schema.

    Args:
    ----
        subparsers (Any): Description for subparsers.
        tool_name (Any): Description for tool_name.
        description (Any): Description for description.
        parameters (Any): Description for parameters.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of _add_tool_subparser logic.

    """
    from rhythm_vibe_mcp.constants.limits import CLI_DESCRIPTION_FIRST_LINE_MAX_LEN

    help_text = (
        (description or tool_name)
        .strip()
        .split("\n")[0][:CLI_DESCRIPTION_FIRST_LINE_MAX_LEN]
    )
    parser = subparsers.add_parser(
        tool_name.replace("_", "-"),
        help=help_text,
        description=description or None,
    )
    parser.set_defaults(_tool_name=tool_name)
    schema = parameters
    props = schema.get(SCHEMA_KEY_PROPERTIES) or {}
    required = set(schema.get(SCHEMA_KEY_REQUIRED) or [])
    for prop_name, prop_schema in props.items():
        opt_name = "--" + prop_name.replace("_", "-")
        schema_type = str(prop_schema.get(SCHEMA_KEY_TYPE, JsonSchemaType.STRING.value))
        default = prop_schema.get(SCHEMA_KEY_DEFAULT)
        is_required = prop_name in required
        if schema_type == JsonSchemaType.BOOLEAN.value:
            parser.add_argument(
                opt_name,
                dest=prop_name,
                action="store_true",
                default=default if default is not None else False,
                help=prop_schema.get(SCHEMA_KEY_DESCRIPTION, ""),
            )
        else:
            type_fn = _schema_type_to_parser(prop_schema)
            parser.add_argument(
                opt_name,
                dest=prop_name,
                type=type_fn,
                required=is_required,
                default=default,
                metavar=prop_name.upper(),
                help=prop_schema.get(SCHEMA_KEY_DESCRIPTION, ""),
            )


def _build_parser() -> argparse.ArgumentParser:
    """Build parser with one subcommand per registered tool.

    Args:
    ----
        None

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of _build_parser logic.

    """
    parser = argparse.ArgumentParser(
        prog=CLI_PROG,
        description=CLI_DESCRIPTION,
    )
    subparsers = parser.add_subparsers(
        dest="tool",
        metavar=CLI_TOOL_METAVAR,
        help=CLI_TOOL_HELP,
    )
    tools = _tool_catalog.list_tools()
    for tool in tools:
        _add_tool_subparser(
            subparsers,
            tool.name,
            tool.description,
            tool.parameters,
        )
    return parser


def _parsed_args_to_arguments(
    args: argparse.Namespace,
    tool_name: str,
) -> dict[str, Any]:
    """Convert parsed namespace to the arguments dict for the tool.

    Args:
    ----
        args (Any): Description for args.
        tool_name (Any): Description for tool_name.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of _parsed_args_to_arguments logic.

    """
    tool = _tool_catalog.get_tool(tool_name)
    if not tool:
        return {}
    props = (tool.parameters.get(SCHEMA_KEY_PROPERTIES) or {}).keys()
    return {p: getattr(args, p) for p in props if hasattr(args, p)}


async def _run_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Run one tool asynchronously and return its text output.

    Args:
    ----
        tool_name (Any): Description for tool_name.
        arguments (Any): Description for arguments.

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of _run_tool logic.

    """
    result = await _tool_catalog.call_tool(tool_name, arguments)
    if isinstance(result, Sequence) and not isinstance(result, (str, bytes, bytearray)):
        if not result:
            return ""
        first = result[0]
        if hasattr(first, "text"):
            return first.text
        return str(first)
    if isinstance(result, dict):
        return json.dumps(result, indent=JSON_INDENT)
    return str(result)


def main() -> int:
    """Executes logic for main.

    Args:
    ----
        None

    Returns:
    -------
        Any: Description of return value.

    Processing Logic:
    -------------------
        - High level explanation of main logic.

    """
    parser = _build_parser()
    args = parser.parse_args()
    if not args.tool:
        parser.print_help()
        return 0
    tool_name = getattr(args, "_tool_name", args.tool).replace("-", "_")
    arguments = _parsed_args_to_arguments(args, tool_name)
    try:
        output = asyncio.run(_run_tool(tool_name, arguments))
        print(output)
        return 0
    except Exception as e:
        print(f"{CLI_ERROR_PREFIX} {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
