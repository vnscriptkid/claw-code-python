"""bash tool -- execute shell commands with timeout and output capture.

Mirrors rust/crates/runtime/src/bash.rs :: execute_bash().

Key behaviour:
  - Runs commands via ``sh -c`` in the current working directory.
  - Optional timeout_ms (default 30 000 ms).  On timeout the process is
    killed and ``interrupted=True`` is set in the result.
  - Combined stdout + stderr are truncated to MAX_OUTPUT_BYTES (16 384 bytes)
    with a trailing marker, matching the Rust implementation.
  - Returns a plain-text summary: stdout, then stderr if non-empty, then an
    exit-code hint when the process exits non-zero.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

from .base import Tool

MAX_OUTPUT_BYTES = 16_384
DEFAULT_TIMEOUT_MS = 30_000


def _truncate(s: str) -> str:
    """Truncate *s* to MAX_OUTPUT_BYTES, appending a marker when trimmed."""
    encoded = s.encode("utf-8")
    if len(encoded) <= MAX_OUTPUT_BYTES:
        return s
    truncated = encoded[:MAX_OUTPUT_BYTES].decode("utf-8", errors="ignore")
    return truncated + "\n\n[output truncated — exceeded 16384 bytes]"


class BashTool(Tool):
    """Execute a shell command and return its output."""

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return (
            "Execute a shell command in the current working directory. "
            "Returns stdout and stderr combined. "
            "Use the 'timeout_ms' parameter to set a maximum run time in "
            "milliseconds (default: 30 000). "
            "Avoid commands that produce interactive prompts."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "timeout_ms": {
                    "type": "integer",
                    "description": (
                        "Maximum time in milliseconds before the command is "
                        "killed (default: 30 000)."
                    ),
                },
                "description": {
                    "type": "string",
                    "description": "Optional human-readable description of what this command does.",
                },
            },
            "required": ["command"],
        }

    def execute(self, tool_input: dict[str, Any]) -> str:
        command: str = tool_input["command"]
        timeout_ms: int = int(tool_input.get("timeout_ms") or DEFAULT_TIMEOUT_MS)
        timeout_secs: float = timeout_ms / 1000.0

        cwd = os.getcwd()

        try:
            proc = subprocess.run(
                ["sh", "-c", command],
                cwd=cwd,
                capture_output=True,
                timeout=timeout_secs,
            )
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout_ms} ms.\n[interrupted]"
        except OSError as exc:
            return f"Failed to start command: {exc}"

        stdout = _truncate(proc.stdout.decode("utf-8", errors="replace"))
        stderr = _truncate(proc.stderr.decode("utf-8", errors="replace"))

        parts: list[str] = []
        if stdout:
            parts.append(stdout)
        if stderr:
            parts.append(f"[stderr]\n{stderr}")
        if proc.returncode != 0:
            parts.append(f"[exit code: {proc.returncode}]")

        return "\n".join(parts) if parts else "(no output)"
