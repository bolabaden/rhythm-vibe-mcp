from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Protocol, cast

if TYPE_CHECKING:
    from collections.abc import Sequence


class ToolDescriptor:
    """Normalized tool metadata used by CLI code paths."""

    __slots__ = ("name", "description", "parameters")

    def __init__(
        self,
        *,
        name: str,
        description: str,
        parameters: dict[str, Any],
    ) -> None:
        self.name = name
        self.description = description
        self.parameters = parameters


class ToolCatalog(Protocol):
    """Public tool catalog interface for CLI discovery and invocation."""

    def list_tools(self) -> list[ToolDescriptor]:
        ...

    def get_tool(self, tool_name: str) -> ToolDescriptor | None:
        ...

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Sequence[Any] | dict[str, Any]:
        ...


class FastMcpToolCatalog:
    """Adapter over FastMCP public APIs (`list_tools` / `call_tool`)."""

    def __init__(self, mcp_server: Any) -> None:
        self._mcp_server = mcp_server

    @staticmethod
    def _input_schema(raw_tool: Any) -> dict[str, Any]:
        schema = getattr(raw_tool, "inputSchema", None)
        if isinstance(schema, dict):
            return schema
        parameters = getattr(raw_tool, "parameters", None)
        if isinstance(parameters, dict):
            return parameters
        return {}

    def list_tools(self) -> list[ToolDescriptor]:
        raw_tools = asyncio.run(self._mcp_server.list_tools())
        return [
            ToolDescriptor(
                name=str(getattr(raw_tool, "name", "")),
                description=str(getattr(raw_tool, "description", "") or ""),
                parameters=self._input_schema(raw_tool),
            )
            for raw_tool in raw_tools
        ]

    def get_tool(self, tool_name: str) -> ToolDescriptor | None:
        for tool in self.list_tools():
            if tool.name == tool_name:
                return tool
        return None

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Sequence[Any] | dict[str, Any]:
        result = await self._mcp_server.call_tool(tool_name, arguments)
        if isinstance(result, dict):
            return result
        return cast("Sequence[Any]", result)
