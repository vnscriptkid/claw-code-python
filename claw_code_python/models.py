"""Core message types mirroring the Anthropic Messages API."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel


class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str


# Union of content block types (extended in later steps with tool_use / tool_result)
ContentBlock = TextBlock


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
