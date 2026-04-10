"""Anthropic API client -- thin wrapper around the Messages API."""

from __future__ import annotations

import os
import httpx

from .models import (
    ContentBlock,
    Message,
    MessageResponse,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    TokenUsage,
)

_API_URL = "https://api.anthropic.com/v1/messages"
_DEFAULT_MODEL = "claude-haiku-4-5"
_DEFAULT_MAX_TOKENS = 8096

# Approximate cost per million tokens (input / output) for a rough estimate
_COST_PER_MTok: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (0.80, 4.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-opus-4-5": (15.00, 75.00),
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    in_rate, out_rate = _COST_PER_MTok.get(model, (3.00, 15.00))
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000


def _serialize_block(block: ContentBlock) -> dict:
    """Convert a ContentBlock to the dict format expected by the Anthropic API."""
    if isinstance(block, TextBlock):
        return {"type": "text", "text": block.text}
    if isinstance(block, ToolUseBlock):
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    if isinstance(block, ToolResultBlock):
        d: dict = {
            "type": "tool_result",
            "tool_use_id": block.tool_use_id,
            "content": block.content,
        }
        if block.is_error:
            d["is_error"] = True
        return d
    # Fallback for any future block type added to the union
    return block.model_dump()


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = _DEFAULT_MODEL,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        system: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass api_key=..."
            )
        self.model = model
        self.max_tokens = max_tokens
        self.system = system
        self._http = httpx.Client(timeout=120.0)

    def send_message(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
    ) -> MessageResponse:
        """Send a list of messages to the API and return the response."""
        payload: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": m.role,
                    "content": [_serialize_block(b) for b in m.content],
                }
                for m in messages
            ],
        }
        if self.system:
            payload["system"] = self.system
        if tools:
            payload["tools"] = tools

        resp = self._http.post(
            _API_URL,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
        )
        if resp.is_error:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise httpx.HTTPStatusError(
                f"HTTP {resp.status_code}: {detail}",
                request=resp.request,
                response=resp,
            )
        data = resp.json()

        content: list[ContentBlock] = []
        for b in data["content"]:
            if b["type"] == "text":
                content.append(TextBlock(text=b["text"]))
            elif b["type"] == "tool_use":
                content.append(ToolUseBlock(id=b["id"], name=b["name"], input=b["input"]))
            # other block types (e.g. thinking) are ignored for now

        usage = TokenUsage(
            input_tokens=data["usage"]["input_tokens"],
            output_tokens=data["usage"]["output_tokens"],
        )
        return MessageResponse(
            id=data["id"],
            model=data["model"],
            content=content,
            usage=usage,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "LLMClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()
