"""Environment variable names used by the MCP server."""

from __future__ import annotations

# Working directory for artifacts, workspace root
ENV_WORKDIR = "rhythm_vibe_mcp_WORKDIR"

# MuseScore API authentication
ENV_MUSESCORE_TOKEN = "MUSESCORE_API_TOKEN"
ENV_MUSESCORE_BASE = "MUSESCORE_API_BASE"

# Default values
DEFAULT_WORKDIR = "."
DEFAULT_MUSESCORE_BASE = "https://musescore.com/api"
