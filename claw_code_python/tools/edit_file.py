"""edit_file tool -- targeted string-replacement within a file.

Mirrors rust/crates/runtime/src/file_ops.rs :: edit_file().

Key behaviour:
  - old_string must exist in the file (otherwise error).
  - old_string and new_string must differ (otherwise error).
  - By default replaces only the FIRST occurrence (replace_all=False).
  - When replace_all=False, raises an error if old_string appears more than
    once, to prevent accidental partial edits.
  - The file must already exist (use write_file for new files).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import Tool


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


class EditFileTool(Tool):
    """Replace the first (or all) occurrence(s) of a string in a file."""

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return (
            "Replace a specific string in a file with a new string. "
            "old_string must appear in the file; use enough context to make it "
            "unique so the correct location is edited. "
            "Set replace_all=true to replace every occurrence. "
            "The file must already exist -- use write_file to create new files."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file to edit.",
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact text to find in the file.",
                },
                "new_string": {
                    "type": "string",
                    "description": "The text to replace old_string with.",
                },
                "replace_all": {
                    "type": "boolean",
                    "description": (
                        "Replace all occurrences of old_string. "
                        "Default false (replace only the first occurrence, "
                        "and fail if the string appears more than once)."
                    ),
                },
            },
            "required": ["path", "old_string", "new_string"],
        }

    def execute(self, tool_input: dict[str, Any]) -> str:
        path_str: str = tool_input["path"]
        old_string: str = tool_input["old_string"]
        new_string: str = tool_input["new_string"]
        replace_all: bool = bool(tool_input.get("replace_all", False))

        if old_string == new_string:
            raise ValueError("old_string and new_string must differ")

        path = _resolve(path_str)

        if not path.exists():
            raise FileNotFoundError(f"file not found: {path}")
        if not path.is_file():
            raise IsADirectoryError(f"path is not a file: {path}")

        original = path.read_text(encoding="utf-8", errors="replace")

        if old_string not in original:
            raise ValueError("old_string not found in file")

        if not replace_all:
            count = original.count(old_string)
            if count > 1:
                raise ValueError(
                    f"old_string appears {count} times in the file; "
                    "add more surrounding context to make it unique, "
                    "or set replace_all=true to replace all occurrences"
                )
            updated = original.replace(old_string, new_string, 1)
        else:
            count = original.count(old_string)
            updated = original.replace(old_string, new_string)

        path.write_text(updated, encoding="utf-8")

        replaced = count if replace_all else 1
        return (
            f"Edited {path}: replaced {replaced} occurrence(s) of "
            f"{len(old_string)}-char string with {len(new_string)}-char string"
        )
