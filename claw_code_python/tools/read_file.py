"""read_file tool -- read a text file with optional line-window.

Mirrors rust/crates/runtime/src/file_ops.rs :: read_file().

Key behaviour:
  - Rejects files > 10 MB.
  - Rejects binary files (NUL-byte detection on first 8 KB).
  - offset / limit select a window of lines (1-based offset presented to the
    user but 0-based internally, matching the Rust implementation).
  - Path may be absolute or relative; relative paths are resolved against CWD.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .base import Tool

MAX_READ_SIZE = 10 * 1024 * 1024  # 10 MB


def _is_binary(path: Path) -> bool:
    """Return True if the first 8 KB of *path* contain a NUL byte."""
    try:
        with path.open("rb") as fh:
            chunk = fh.read(8192)
        return b"\x00" in chunk
    except OSError:
        return False


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


class ReadFileTool(Tool):
    """Read a text file, optionally restricted to a line window."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return (
            "Read the contents of a text file at the given path. "
            "Use offset (0-based line index) and limit (number of lines) "
            "to read a window of the file. "
            "Returns the file content with 1-based line numbers prepended to each line."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file.",
                },
                "offset": {
                    "type": "integer",
                    "description": "0-based line index to start reading from (default 0).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to return (default: all).",
                },
            },
            "required": ["path"],
        }

    def execute(self, tool_input: dict[str, Any]) -> str:
        path_str: str = tool_input["path"]
        offset: int = int(tool_input.get("offset") or 0)
        limit: int | None = tool_input.get("limit")
        if limit is not None:
            limit = int(limit)

        path = _resolve(path_str)

        if not path.exists():
            raise FileNotFoundError(f"file not found: {path}")
        if not path.is_file():
            raise IsADirectoryError(f"path is not a file: {path}")

        size = path.stat().st_size
        if size > MAX_READ_SIZE:
            raise ValueError(
                f"file is too large ({size} bytes, max {MAX_READ_SIZE} bytes)"
            )

        if _is_binary(path):
            raise ValueError("file appears to be binary")

        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        total_lines = len(lines)

        start = min(offset, total_lines)
        if limit is not None:
            end = min(start + limit, total_lines)
        else:
            end = total_lines

        selected = lines[start:end]

        # Prepend 1-based line numbers, matching the Rust output format.
        numbered = "\n".join(
            f"{i + start + 1}\t{line}" for i, line in enumerate(selected)
        )

        header = (
            f"File: {path}\n"
            f"Lines {start + 1}-{end} of {total_lines}\n"
            f"---\n"
        )
        return header + numbered
