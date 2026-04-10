#!/usr/bin/env python3
"""Step 1: Minimal LLM chat loop.

Usage:
    python -m claw_code_python.main
    # or
    python claw_code_python/main.py

Environment:
    ANTHROPIC_API_KEY  -- required
    CLAW_MODEL         -- optional, default: claude-haiku-4-5
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv  # noqa: E402

load_dotenv()  # loads .env from cwd (or any parent directory)

from .llm_client import LLMClient, _estimate_cost  # noqa: E402
from .models import Message  # noqa: E402


SYSTEM_PROMPT = "You are a helpful coding assistant."
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_DIM = "\033[2m"
_RESET = "\033[0m"
_BOLD = "\033[1m"


def _print_banner() -> None:
    print(f"{_BOLD}claw-code-python{_RESET}  (step 1 — minimal chat loop)")
    print(f'{_DIM}Type "exit" or press Ctrl-D to quit.{_RESET}')
    print()


def _print_usage(model: str, input_tokens: int, output_tokens: int) -> None:
    cost = _estimate_cost(model, input_tokens, output_tokens)
    print(
        f"{_DIM}[{input_tokens} in / {output_tokens} out | ~${cost:.4f}]{_RESET}",
        file=sys.stderr,
    )


def run() -> None:
    _print_banner()
    model = os.environ.get("CLAW_MODEL", "claude-haiku-4-5")

    try:
        client = LLMClient(model=model, system=SYSTEM_PROMPT)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    conversation: list[Message] = []

    with client:
        while True:
            try:
                user_input = input(f"{_GREEN}you>{_RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break

            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", "/exit", "/quit"}:
                print("Bye!")
                break

            conversation.append(Message.user(user_input))

            try:
                response = client.send_message(conversation)
            except Exception as e:  # noqa: BLE001
                print(f"API error: {e}", file=sys.stderr)
                # Remove the failed user message so the conversation stays clean
                conversation.pop()
                continue

            assistant_text = response.text()
            conversation.append(Message.assistant(assistant_text))

            print(f"{_CYAN}claude>{_RESET} {assistant_text}")
            print()
            _print_usage(
                response.model,
                response.usage.input_tokens,
                response.usage.output_tokens,
            )
            print()


if __name__ == "__main__":
    run()
