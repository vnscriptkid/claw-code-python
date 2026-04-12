"""glob_search tool -- find files matching a glob pattern.

Mirrors rust/crates/runtime/src/file_ops.rs :: glob_search().

Key behaviour:
  - Resolves relative patterns against an optional root_path (default CWD).
  - Returns only regular files (not directories).
  - Results are sorted newest-first by modification time.
  - Truncated to 100 results; ``truncated`` flag set when more exist.
  - Returns a JSON-serialisable result string summarising the matches.
"""

from __future__ import annotations

import fnmatch
import glob as _glob
import json
import time
from pathlib import Path
from typing import Any

from .base import Tool

MAX_RESULTS = 100


# ---------------------------------------------------------------------------
# .gitignore helpers
# ---------------------------------------------------------------------------


def _load_gitignore_patterns(base_dir: Path) -> list[str]:
    """Return the raw (non-comment, non-blank) lines from ``base_dir/.gitignore``."""
    gitignore = base_dir / ".gitignore"
    if not gitignore.is_file():
        return []
    lines: list[str] = []
    for line in gitignore.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.rstrip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def _is_gitignored(path: Path, base_dir: Path, patterns: list[str]) -> bool:
    """Return True if *path* should be excluded by any of the .gitignore *patterns*."""
    try:
        rel = path.relative_to(base_dir)
    except ValueError:
        return False

    rel_str = str(rel)
    parts = rel.parts

    for pattern in patterns:
        # Negation is not supported yet; skip negation lines.
        if pattern.startswith("!"):
            continue

        if pattern.endswith("/"):
            # Directory pattern: exclude any file whose ancestor matches.
            dir_pat = pattern.rstrip("/")
            if any(fnmatch.fnmatch(part, dir_pat) for part in parts[:-1]):
                return True
        elif "/" in pattern:
            # Relative path pattern: match against the full relative path.
            if fnmatch.fnmatch(rel_str, pattern):
                return True
        else:
            # Simple name pattern: match against any path component.
            if any(fnmatch.fnmatch(part, pattern) for part in parts):
                return True

    return False


def _resolve_dir(path_str: str | None) -> Path:
    if path_str is None:
        return Path.cwd()
    p = Path(path_str)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


class GlobSearchTool(Tool):
    """Search for files whose path matches a glob pattern."""

    @property
    def name(self) -> str:
        return "glob_search"

    @property
    def description(self) -> str:
        return (
            "Find files matching a glob pattern (e.g. '**/*.py', 'src/**/*.ts'). "
            "Results are sorted newest-first by modification time and capped at 100. "
            "Use root_path to scope the search to a specific directory."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": (
                        "Glob pattern to match file paths against "
                        "(e.g. '**/*.py', 'tests/**/test_*.py')."
                    ),
                },
                "root_path": {
                    "type": "string",
                    "description": (
                        "Directory to search within. "
                        "Defaults to the current working directory."
                    ),
                },
            },
            "required": ["pattern"],
        }

    def execute(self, tool_input: dict[str, Any]) -> str:
        pattern: str = tool_input["pattern"]
        root_path: str | None = tool_input.get("root_path")

        started = time.monotonic()
        base_dir = _resolve_dir(root_path)

        # Build the full glob expression.
        if Path(pattern).is_absolute():
            search_pattern = pattern
        else:
            search_pattern = str(base_dir / pattern)

        # Collect matching files.
        matches: list[Path] = []
        for entry in _glob.glob(search_pattern, recursive=True):
            p = Path(entry)
            if p.is_file():
                matches.append(p)

        # Filter out .gitignore-excluded files.
        gitignore_patterns = _load_gitignore_patterns(base_dir)
        if gitignore_patterns:
            matches = [
                p
                for p in matches
                if not _is_gitignored(p, base_dir, gitignore_patterns)
            ]

        # Sort newest-first by modification time.
        def _mtime(p: Path) -> float:
            try:
                return p.stat().st_mtime
            except OSError:
                return 0.0

        matches.sort(key=_mtime, reverse=True)

        truncated = len(matches) > MAX_RESULTS
        filenames = [str(p) for p in matches[:MAX_RESULTS]]
        duration_ms = int((time.monotonic() - started) * 1000)

        result = {
            "durationMs": duration_ms,
            "numFiles": len(filenames),
            "filenames": filenames,
            "truncated": truncated,
        }
        return json.dumps(result, indent=2)
