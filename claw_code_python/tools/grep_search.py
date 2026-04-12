"""grep_search tool -- regex search over workspace files.

Mirrors rust/crates/runtime/src/file_ops.rs :: grep_search().

Key behaviour:
  - output_mode controls what is returned:
      "files_with_matches"  (default) -- list of file paths that contain a match
      "content"             -- matching lines with optional context, prefixed
                               with ``filepath:lineno:``
      "count"               -- number of matches per file
  - Supports context lines: context (alias -C), before (-B), after (-A).
  - Glob filter (``glob``) and extension filter (``type``) narrow the file set.
  - Case-insensitive matching via ``-i`` / ``case_insensitive``.
  - Results are paginated with ``head_limit`` (default 250) and ``offset``.
  - Binary files are silently skipped.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
from pathlib import Path
from typing import Any

from .base import Tool

_DEFAULT_HEAD_LIMIT = 250


def _resolve(path_str: str | None) -> Path:
    if path_str is None:
        return Path.cwd()
    p = Path(path_str)
    if not p.is_absolute():
        p = Path.cwd() / p
    resolved = p.resolve()
    return resolved


def _is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return b"\x00" in fh.read(8192)
    except OSError:
        return False


def _collect_files(base: Path) -> list[Path]:
    """Return all regular files under *base* (or just *base* if it's a file).

    Hidden directories (names starting with ``.``) are skipped.
    """
    if base.is_file():
        return [base]
    results: list[Path] = []
    for root, dirs, files in os.walk(base):
        # Prune hidden directories in-place so os.walk won't descend into them.
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            results.append(Path(root) / name)
    return results


def _matches_filters(
    path: Path,
    glob_filter: str | None,
    file_type: str | None,
) -> bool:
    if glob_filter is not None:
        path_str = str(path)
        # Match against the full path or just the filename.
        if not fnmatch.fnmatch(path_str, glob_filter) and not fnmatch.fnmatch(
            path.name, glob_filter
        ):
            return False
    if file_type is not None:
        if path.suffix.lstrip(".") != file_type:
            return False
    return True


def _apply_limit(
    items: list,
    head_limit: int | None,
    offset: int | None,
) -> tuple[list, int | None, int | None]:
    offset_val = offset or 0
    items = items[offset_val:]
    limit = head_limit if head_limit is not None else _DEFAULT_HEAD_LIMIT
    if limit == 0:
        return items, None, (offset_val or None)
    truncated = len(items) > limit
    return (
        items[:limit],
        limit if truncated else None,
        offset_val if offset_val > 0 else None,
    )


class GrepSearchTool(Tool):
    """Search file contents using a regex pattern."""

    @property
    def name(self) -> str:
        return "grep_search"

    @property
    def description(self) -> str:
        return (
            "Search file contents using a regular expression. "
            "Returns matching file paths by default ('files_with_matches' mode). "
            "Set output_mode='content' to get the matching lines with context. "
            "Set output_mode='count' to get match counts per file. "
            "Use 'path' to scope the search, 'glob' to filter by filename pattern, "
            "and 'type' to filter by file extension."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regular expression to search for.",
                },
                "path": {
                    "type": "string",
                    "description": (
                        "File or directory to search. "
                        "Defaults to the current working directory."
                    ),
                },
                "glob": {
                    "type": "string",
                    "description": (
                        "Glob pattern to filter which files are searched "
                        "(e.g. '*.py', '**/*.ts')."
                    ),
                },
                "output_mode": {
                    "type": "string",
                    "enum": ["files_with_matches", "content", "count"],
                    "description": (
                        "What to return: 'files_with_matches' (default), "
                        "'content' (matching lines), or 'count' (match counts)."
                    ),
                },
                "context": {
                    "type": "integer",
                    "description": "Lines of context before and after each match (alias: -C).",
                },
                "-C": {
                    "type": "integer",
                    "description": "Lines of context before and after each match.",
                },
                "-B": {
                    "type": "integer",
                    "description": "Lines of context before each match.",
                },
                "-A": {
                    "type": "integer",
                    "description": "Lines of context after each match.",
                },
                "-n": {
                    "type": "boolean",
                    "description": "Include line numbers in content output (default true).",
                },
                "-i": {
                    "type": "boolean",
                    "description": "Case-insensitive matching.",
                },
                "case_insensitive": {
                    "type": "boolean",
                    "description": "Case-insensitive matching (alias: -i).",
                },
                "type": {
                    "type": "string",
                    "description": "Filter files by extension (e.g. 'py', 'ts').",
                },
                "head_limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 250).",
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of results to skip (for pagination).",
                },
                "multiline": {
                    "type": "boolean",
                    "description": "Allow . to match newlines (multiline mode).",
                },
            },
            "required": ["pattern"],
        }

    def execute(self, tool_input: dict[str, Any]) -> str:  # noqa: C901
        raw_pattern: str = tool_input["pattern"]
        search_path: str | None = tool_input.get("path")
        glob_filter: str | None = tool_input.get("glob")
        output_mode: str = tool_input.get("output_mode") or "files_with_matches"
        context: int = int(tool_input.get("context") or tool_input.get("-C") or 0)
        before: int = int(tool_input.get("-B") or context)
        after: int = int(tool_input.get("-A") or context)
        line_numbers: bool = tool_input.get("-n", True) is not False
        case_insensitive: bool = bool(
            tool_input.get("-i") or tool_input.get("case_insensitive") or False
        )
        file_type: str | None = tool_input.get("type")
        head_limit: int | None = (
            int(tool_input["head_limit"])
            if tool_input.get("head_limit") is not None
            else None
        )
        offset: int | None = (
            int(tool_input["offset"]) if tool_input.get("offset") is not None else None
        )
        multiline: bool = bool(tool_input.get("multiline") or False)

        # Compile regex.
        flags = re.IGNORECASE if case_insensitive else 0
        if multiline:
            flags |= re.DOTALL
        try:
            regex = re.compile(raw_pattern, flags)
        except re.error as exc:
            return f"Error: invalid regex pattern: {exc}"

        base_path = _resolve(search_path)
        if not base_path.exists():
            return f"Error: path does not exist: {base_path}"

        filenames: list[str] = []
        content_lines: list[str] = []
        total_matches = 0

        for file_path in _collect_files(base_path):
            if not _matches_filters(file_path, glob_filter, file_type):
                continue
            if _is_binary(file_path):
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            if output_mode == "count":
                count = len(regex.findall(text))
                if count > 0:
                    filenames.append(str(file_path))
                    total_matches += count
                continue

            lines = text.splitlines()
            matched_indices: list[int] = [
                i for i, line in enumerate(lines) if regex.search(line)
            ]
            if not matched_indices:
                continue

            filenames.append(str(file_path))

            if output_mode == "content":
                for idx in matched_indices:
                    total_matches += 1
                    start = max(0, idx - before)
                    end = min(len(lines), idx + after + 1)
                    for lineno, line in enumerate(lines[start:end], start=start):
                        if line_numbers:
                            prefix = f"{file_path}:{lineno + 1}:"
                        else:
                            prefix = f"{file_path}:"
                        content_lines.append(f"{prefix}{line}")

        # Apply pagination.
        filenames, applied_limit, applied_offset = _apply_limit(
            filenames, head_limit, offset
        )

        if output_mode == "content":
            content_lines, c_limit, c_offset = _apply_limit(
                content_lines, head_limit, offset
            )
            result: dict[str, Any] = {
                "mode": output_mode,
                "numFiles": len(filenames),
                "filenames": filenames,
                "content": "\n".join(content_lines),
                "numLines": len(content_lines),
                "numMatches": None,
                "appliedLimit": c_limit,
                "appliedOffset": c_offset,
            }
        else:
            result = {
                "mode": output_mode,
                "numFiles": len(filenames),
                "filenames": filenames,
                "content": None,
                "numLines": None,
                "numMatches": total_matches if output_mode == "count" else None,
                "appliedLimit": applied_limit,
                "appliedOffset": applied_offset,
            }

        return json.dumps(result, indent=2)
