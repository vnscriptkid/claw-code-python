#!/usr/bin/env python3
"""Step 5: Search Tools (Glob + Grep).

Adds glob_search and write_file on top of Step 4.
The agent can now search for files by pattern and search file contents
by regex, making it self-sufficient in exploring any codebase.

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

from .agent_loop import run_turn  # noqa: E402
from .llm_client import LLMClient, _estimate_cost  # noqa: E402
from .models import Message  # noqa: E402
from .tool_registry import ToolRegistry  # noqa: E402
from .session import Session  # noqa: E402
from .tools.calculator import CalculatorTool  # noqa: E402
from .tools.read_file import ReadFileTool  # noqa: E402
from .tools.write_file import WriteFileTool  # noqa: E402
from .tools.edit_file import EditFileTool  # noqa: E402
from .tools.bash import BashTool  # noqa: E402
from .tools.glob_search import GlobSearchTool  # noqa: E402
from .tools.grep_search import GrepSearchTool  # noqa: E402


SYSTEM_PROMPT = (
    "You are a helpful coding assistant. "
    "You can read, write, and edit files on disk, run shell commands, and search codebases. "
    "When asked to compute arithmetic, use the calculator tool. "
    "When working with files, always use the file tools rather than guessing content. "
    "When you need to run commands (tests, installs, git, etc.), use the bash tool. "
    "Keep bash commands focused and avoid interactive prompts. "
    "Use glob_search to find files by name/pattern and grep_search to search file contents by regex."
)
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_DIM = "\033[2m"
_RESET = "\033[0m"
_BOLD = "\033[1m"


def _print_banner(session_id: str) -> None:
    print(f"{_BOLD}claw-code-python{_RESET}  (step 5 — search tools)")
    print(f'{_DIM}Type "exit" or press Ctrl-D to quit.{_RESET}')
    print(f"{_DIM}Session: {session_id}{_RESET}")
    print(f"{_DIM}Viewer:  python -m claw_code_python.viewer --serve{_RESET}")
    print()


def _print_usage(model: str, input_tokens: int, output_tokens: int) -> None:
    cost = _estimate_cost(model, input_tokens, output_tokens)
    print(
        f"{_DIM}[{input_tokens} in / {output_tokens} out | ~${cost:.4f}]{_RESET}",
        file=sys.stderr,
    )


def run() -> None:
    model = os.environ.get("CLAW_MODEL", "claude-haiku-4-5")
    session = Session(model=model)

    _print_banner(session.session_id)

    try:
        client = LLMClient(model=model, system=SYSTEM_PROMPT)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(EditFileTool())
    registry.register(BashTool())
    registry.register(GlobSearchTool())
    registry.register(GrepSearchTool())

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

            try:
                result = run_turn(user_input, conversation, client, registry)
            except Exception as e:  # noqa: BLE001
                print(f"API error: {e}", file=sys.stderr)
                # Remove the failed user message so conversation stays clean.
                if conversation and conversation[-1].role == "user":
                    conversation.pop()
                continue

            # Persist this turn to disk.
            session.save_turn(
                messages=conversation,
                tool_calls=[
                    {
                        "name": tc.name,
                        "input": tc.input,
                        "output": tc.output,
                        "is_error": tc.is_error,
                    }
                    for tc in result.tool_calls
                ],
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )

            # Show any tool calls that happened during this turn.
            for tc in result.tool_calls:
                inp_str = ", ".join(f"{k}={v!r}" for k, v in tc.input.items())
                status = "error" if tc.is_error else "ok"
                print(
                    f"{_YELLOW}[tool:{_RESET} {tc.name}({inp_str})"
                    f"{_YELLOW} →{_RESET} {tc.output!r}"
                    f" {_DIM}({status}){_RESET}{_YELLOW}]{_RESET}"
                )

            print(f"{_CYAN}claude>{_RESET} {result.text}")
            print()
            _print_usage(model, result.input_tokens, result.output_tokens)
            print()


if __name__ == "__main__":
    run()
