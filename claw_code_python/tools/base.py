"""Base class for all agent tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Abstract base class every tool must implement.

    Mirrors the tool trait in rust/crates/runtime/src/tools/lib.rs.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name used in API requests (e.g. "calculator")."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Short human-readable description shown to the LLM."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict:
        """JSON Schema dict describing the tool's input parameters."""
        ...

    @abstractmethod
    def execute(self, tool_input: dict[str, Any]) -> str:
        """Run the tool and return a plain-text result (or error message)."""
        ...

    def to_api_definition(self) -> dict:
        """Return the tool definition dict sent to the Anthropic API."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
