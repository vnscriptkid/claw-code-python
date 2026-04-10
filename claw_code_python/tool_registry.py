"""Tool registry -- registers tools and dispatches execution by name."""

from __future__ import annotations

from typing import Any

from .tools.base import Tool


class ToolRegistry:
    """Central registry that maps tool names to Tool instances.

    Mirrors the tool executor concept in
    rust/crates/runtime/src/conversation.rs (self.tool_executor.execute).
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool, overwriting any existing tool with the same name."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def api_definitions(self) -> list[dict[str, Any]]:
        """Return tool definitions in the format expected by the Anthropic API."""
        return [t.to_api_definition() for t in self._tools.values()]

    def execute(self, name: str, tool_input: dict[str, Any]) -> tuple[str, bool]:
        """Execute a tool by name.

        Returns:
            (output, is_error) -- output text and whether it represents an error.
        """
        tool = self._tools.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'", True
        try:
            return tool.execute(tool_input), False
        except Exception as exc:  # noqa: BLE001
            return f"Error executing '{name}': {exc}", True
