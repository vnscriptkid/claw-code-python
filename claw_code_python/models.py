"""Core message types mirroring the Anthropic Messages API."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union
from pydantic import BaseModel, Field


class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ToolUseBlock(BaseModel):
    """Emitted by the assistant when it wants to call a tool."""
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict[str, Any]


class ToolResultBlock(BaseModel):
    """Sent by the user to return a tool's output to the assistant."""
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str
    is_error: bool = False


# Discriminated union -- Pydantic picks the right model from the "type" field.
ContentBlock = Annotated[
    Union[TextBlock, ToolUseBlock, ToolResultBlock],
    Field(discriminator="type"),
]


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: list[ContentBlock]

    @classmethod
    def user(cls, text: str) -> "Message":
        return cls(role="user", content=[TextBlock(text=text)])

    @classmethod
    def assistant(cls, text: str) -> "Message":
        return cls(role="assistant", content=[TextBlock(text=text)])

    def text(self) -> str:
        """Return concatenated text from all text blocks."""
        return "".join(b.text for b in self.content if isinstance(b, TextBlock))


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


class MessageResponse(BaseModel):
    id: str
    model: str
    content: list[ContentBlock]
    usage: TokenUsage

    def text(self) -> str:
        return "".join(b.text for b in self.content if isinstance(b, TextBlock))
