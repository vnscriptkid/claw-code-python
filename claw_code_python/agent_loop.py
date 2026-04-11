"""Core agent loop -- the heart of the coding agent.

Implements run_turn(): the agentic loop that sends messages to the LLM,
executes any tool calls, feeds results back, and repeats until the LLM
produces a final text-only response.

Direct translation of ConversationRuntime.run_turn() from:
  rust/crates/runtime/src/conversation.rs:296-485

Key differences from the Rust version (simplified for Step 2):
  - No permission system (added in Step 8)
  - No pre/post tool-use hooks (added later)
  - No auto-compaction (added in Step 9)
  - No streaming (added in Step 10)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .llm_client import LLMClient
from .models import Message, ToolResultBlock, ToolUseBlock
from .tool_registry import ToolRegistry

_MAX_ITERATIONS = 10


@dataclass
class ToolCallRecord:
    """Records a single tool invocation for display / logging."""

    name: str
    input: dict[str, Any]
    output: str
    is_error: bool


@dataclass
class TurnResult:
    """Outcome of a single user turn (mirrors TurnSummary in Rust)."""

    text: str  # final assistant text response
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    iterations: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


def run_turn(
    user_input: str,
    messages: list[Message],
    client: LLMClient,
    registry: ToolRegistry,
    *,
    max_iterations: int = _MAX_ITERATIONS,
) -> TurnResult:
    """Run one user turn of the agent loop.

    Appends messages in-place (user input, assistant responses, tool results)
    so the caller's conversation history is kept up to date.

    Mirrors ConversationRuntime::run_turn() in conversation.rs:
      1. Push user message
      2. Loop:
         a. Call LLM with tool definitions
         b. Append assistant message
         c. If no tool_use blocks -> break (final response)
         d. Execute each tool_use, collect results as a user message
         e. Append user message with tool_result blocks, continue
      3. Return TurnResult with final text + tool call log
    """
    messages.append(Message.user(user_input))

    tool_calls: list[ToolCallRecord] = []
    iterations = 0
    final_text = ""
    total_input_tokens = 0
    total_output_tokens = 0

    for _ in range(max_iterations):
        iterations += 1

        response = client.send_message(messages, tools=registry.api_definitions())
        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        # Append assistant message (may contain text + tool_use blocks).
        messages.append(Message(role="assistant", content=list(response.content)))

        # Collect all tool_use blocks from this response.
        pending = [b for b in response.content if isinstance(b, ToolUseBlock)]

        if not pending:
            # No tool calls -- this is the final text response.
            final_text = response.text()
            break

        # Execute every tool in this batch and collect results.
        result_blocks: list[ToolResultBlock] = []
        for tu in pending:
            output, is_error = registry.execute(tu.name, tu.input)
            tool_calls.append(
                ToolCallRecord(
                    name=tu.name,
                    input=tu.input,
                    output=output,
                    is_error=is_error,
                )
            )
            result_blocks.append(
                ToolResultBlock(
                    tool_use_id=tu.id,
                    content=output,
                    is_error=is_error,
                )
            )

        # Feed all tool results back as a single user message.
        messages.append(Message(role="user", content=result_blocks))  # type: ignore[arg-type]

    return TurnResult(
        text=final_text,
        tool_calls=tool_calls,
        iterations=iterations,
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
    )
