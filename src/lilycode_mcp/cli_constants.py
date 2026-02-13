"""CLI identity and user-facing strings for the generated CLI."""

# Parser identity
CLI_PROG = "lilycode-mcp-cli"
CLI_DESCRIPTION = (
    "CLI for lilycode-mcp tools. Subcommands are generated from the server's registered tools."
)

# Subparsers
CLI_TOOL_METAVAR = "TOOL"
CLI_TOOL_HELP = "Tool to run (use TOOL --help for tool-specific options)"

# Error output
CLI_ERROR_PREFIX = "Error:"

# JSON schema type names (for mapping schema types to argparse)
SCHEMA_TYPE_STRING = "string"
SCHEMA_TYPE_INTEGER = "integer"
SCHEMA_TYPE_NUMBER = "number"
SCHEMA_TYPE_BOOLEAN = "boolean"

# JSON schema property keys (for introspecting tool parameters)
SCHEMA_KEY_PROPERTIES = "properties"
SCHEMA_KEY_REQUIRED = "required"
SCHEMA_KEY_TYPE = "type"
SCHEMA_KEY_DEFAULT = "default"
SCHEMA_KEY_DESCRIPTION = "description"
