"""
Canonical CLI for lilycode-mcp: dynamically generated from registered MCP tools.

All subcommands and options are derived exclusively from the server's tool list.
When tools are added, removed, or renamed, the CLI updates automatically.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from lilycode_mcp.cli_constants import (
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
    SCHEMA_TYPE_BOOLEAN,
    SCHEMA_TYPE_INTEGER,
    SCHEMA_TYPE_NUMBER,
    SCHEMA_TYPE_STRING,
)
from lilycode_mcp.json_constants import JSON_INDENT
# Import server so tools are registered; then we introspect.
from lilycode_mcp.server import mcp


def _schema_type_to_parser(schema: dict[str, Any]) -> type:
    """Map JSON schema type to argparse type."""
    t = schema.get(SCHEMA_KEY_TYPE, SCHEMA_TYPE_STRING)
    if t == SCHEMA_TYPE_INTEGER:
        return int
    if t == SCHEMA_TYPE_NUMBER:
        return float
    if t == SCHEMA_TYPE_BOOLEAN:
        return bool
    return str


def _add_tool_subparser(
    subparsers: argparse._SubParsersAction,
    tool_name: str,
    description: str,
    parameters: dict[str, Any],
) -> None:
    """Add one subparser for a tool, with arguments from its JSON schema."""
    from lilycode_mcp.limits_constants import CLI_DESCRIPTION_FIRST_LINE_MAX_LEN

    help_text = (description or tool_name).strip().split("\n")[0][:CLI_DESCRIPTION_FIRST_LINE_MAX_LEN]
    parser = subparsers.add_parser(
        tool_name.replace("_", "-"),
        help=help_text,
        description=description or None,
    )
    parser.set_defaults(_tool_name=tool_name)
    props = parameters.get(SCHEMA_KEY_PROPERTIES) or {}
    required = set(parameters.get(SCHEMA_KEY_REQUIRED) or [])
    for prop_name, prop_schema in props.items():
        opt_name = "--" + prop_name.replace("_", "-")
        schema_type = prop_schema.get(SCHEMA_KEY_TYPE, SCHEMA_TYPE_STRING)
        default = prop_schema.get(SCHEMA_KEY_DEFAULT)
        is_required = prop_name in required
        if schema_type == SCHEMA_TYPE_BOOLEAN:
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
    """Build parser with one subcommand per registered tool."""
    parser = argparse.ArgumentParser(
        prog=CLI_PROG,
        description=CLI_DESCRIPTION,
    )
    subparsers = parser.add_subparsers(
        dest="tool",
        metavar=CLI_TOOL_METAVAR,
        help=CLI_TOOL_HELP,
    )
    tools = mcp._tool_manager.list_tools()
    for tool in tools:
        _add_tool_subparser(
            subparsers,
            tool.name,
            tool.description,
            tool.parameters,
        )
    return parser


def _parsed_args_to_arguments(args: argparse.Namespace, tool_name: str) -> dict[str, Any]:
    """Convert parsed namespace to the arguments dict for the tool."""
    tool = mcp._tool_manager.get_tool(tool_name)
    if not tool:
        return {}
    props = (tool.parameters.get(SCHEMA_KEY_PROPERTIES) or {}).keys()
    return {p: getattr(args, p) for p in props if hasattr(args, p)}


async def _run_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Run one tool asynchronously and return its text output."""
    result = await mcp._tool_manager.call_tool(
        tool_name,
        arguments,
        context=None,
        convert_result=True,
    )
    # call_tool(convert_result=True) may return (content_blocks, structured) or list/dict
    if isinstance(result, tuple) and len(result) >= 1:
        result = result[0]
    if isinstance(result, list) and result:
        first = result[0]
        if hasattr(first, "text"):
            return first.text
        return str(first)
    if isinstance(result, dict):
        return json.dumps(result, indent=JSON_INDENT)
    return str(result)


def main() -> int:
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
