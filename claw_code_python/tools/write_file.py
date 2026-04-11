"""write_file tool -- create or overwrite a file with given content.

Mirrors rust/crates/runtime/src/file_ops.rs :: write_file().

Key behaviour:
  - Rejects content > 10 MB.
  - Creates parent directories if they don't exist.
  - Reports whether the file was created new or updated.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import Tool

MAX_WRITE_SIZE = 10 * 1024 * 1024  # 10 MB


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


class WriteFileTool(Tool):
    """Create or overwrite a file with the given content."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return (
            "Write content to a file at the given path, creating it if it does not "
            "exist or overwriting it if it does. Parent directories are created "
            "automatically. Content must be plain text (UTF-8)."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file to write.",
                },
                "content": {
                    "type": "string",
                    "description": "Text content to write to the file.",
                },
            },
            "required": ["path", "content"],
        }

    def execute(self, tool_input: dict[str, Any]) -> str:
        path_str: str = tool_input["path"]
        content: str = tool_input["content"]

        if len(content.encode("utf-8")) > MAX_WRITE_SIZE:
            raise ValueError(
                f"content is too large ({len(content.encode())} bytes, "
                f"max {MAX_WRITE_SIZE} bytes)"
            )

        path = _resolve(path_str)
        existed = path.exists()

        if path.parent:
            path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(content, encoding="utf-8")

        action = "Updated" if existed else "Created"
        line_count = content.count("\n") + (
            1 if content and not content.endswith("\n") else 0
        )
        return f"{action} {path} ({line_count} lines, {len(content)} bytes)"
