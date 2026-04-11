"""Tests for glob_search and grep_search tools."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claw_code_python.tools.glob_search import GlobSearchTool
from claw_code_python.tools.grep_search import GrepSearchTool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tree(base: Path) -> None:
    """Create a small fake codebase under *base*."""
    (base / "src").mkdir()
    (base / "src" / "main.py").write_text("def main():\n    pass\n")
    (base / "src" / "utils.py").write_text("def helper():\n    return 42\n")
    (base / "tests").mkdir()
    (base / "tests" / "test_main.py").write_text(
        "from src.main import main\ndef test_main():\n    main()\n"
    )
    (base / "README.md").write_text("# Project\n\nSome docs.\n")
    (base / "data.bin").write_bytes(b"\x00\x01\x02binary")


# ---------------------------------------------------------------------------
# glob_search
# ---------------------------------------------------------------------------


@pytest.fixture()
def glob():
    return GlobSearchTool()


@pytest.fixture()
def tree(tmp_path):
    _make_tree(tmp_path)
    return tmp_path


def test_glob_finds_py_files(glob, tree):
    result = json.loads(glob.execute({"pattern": "**/*.py", "root_path": str(tree)}))
    assert result["numFiles"] == 3
    assert all(f.endswith(".py") for f in result["filenames"])


def test_glob_scoped_to_subdir(glob, tree):
    result = json.loads(
        glob.execute({"pattern": "*.py", "root_path": str(tree / "src")})
    )
    assert result["numFiles"] == 2


def test_glob_no_match(glob, tree):
    result = json.loads(glob.execute({"pattern": "**/*.rs", "root_path": str(tree)}))
    assert result["numFiles"] == 0
    assert result["truncated"] is False


def test_glob_truncated_flag(glob, tmp_path):
    # Create 101 files to trigger truncation.
    for i in range(101):
        (tmp_path / f"f{i}.txt").write_text("x")
    result = json.loads(glob.execute({"pattern": "*.txt", "root_path": str(tmp_path)}))
    assert result["truncated"] is True
    assert result["numFiles"] == 100  # capped at MAX_RESULTS


def test_glob_duration_present(glob, tree):
    result = json.loads(glob.execute({"pattern": "**/*.py", "root_path": str(tree)}))
    assert "durationMs" in result
    assert isinstance(result["durationMs"], int)


# ---------------------------------------------------------------------------
# grep_search
# ---------------------------------------------------------------------------


@pytest.fixture()
def grep():
    return GrepSearchTool()


def test_grep_files_with_matches(grep, tree):
    result = json.loads(grep.execute({"pattern": "def ", "path": str(tree)}))
    assert result["mode"] == "files_with_matches"
    assert result["numFiles"] == 3  # main.py, utils.py, test_main.py


def test_grep_content_mode(grep, tree):
    result = json.loads(
        grep.execute(
            {
                "pattern": "def helper",
                "path": str(tree / "src" / "utils.py"),
                "output_mode": "content",
            }
        )
    )
    assert result["content"] is not None
    assert "def helper" in result["content"]
    assert "utils.py:" in result["content"]


def test_grep_count_mode(grep, tree):
    result = json.loads(
        grep.execute({"pattern": "def ", "path": str(tree), "output_mode": "count"})
    )
    assert result["mode"] == "count"
    assert (
        result["numMatches"] == 3
    )  # main.py:def main, utils.py:def helper, test_main.py:def test_main


def test_grep_case_insensitive(grep, tree):
    sensitive = json.loads(grep.execute({"pattern": "DEF", "path": str(tree)}))
    insensitive = json.loads(
        grep.execute({"pattern": "DEF", "path": str(tree), "-i": True})
    )
    assert sensitive["numFiles"] == 0
    assert insensitive["numFiles"] == 3


def test_grep_glob_filter(grep, tree):
    result = json.loads(
        grep.execute({"pattern": "def ", "path": str(tree), "glob": "test_*.py"})
    )
    assert result["numFiles"] == 1
    assert "test_main.py" in result["filenames"][0]


def test_grep_type_filter(grep, tree):
    result = json.loads(grep.execute({"pattern": ".", "path": str(tree), "type": "md"}))
    assert result["numFiles"] == 1
    assert result["filenames"][0].endswith(".md")


def test_grep_context_lines(grep, tree):
    result = json.loads(
        grep.execute(
            {
                "pattern": "return 42",
                "path": str(tree / "src" / "utils.py"),
                "output_mode": "content",
                "context": 1,
            }
        )
    )
    # With 1 line of context we should see "def helper():" before "return 42"
    assert "def helper" in result["content"]
    assert "return 42" in result["content"]


def test_grep_skips_binary(grep, tree):
    # data.bin contains NUL bytes and should be silently skipped
    result = json.loads(grep.execute({"pattern": ".", "path": str(tree)}))
    assert not any("data.bin" in f for f in result["filenames"])


def test_grep_invalid_regex(grep, tree):
    result = grep.execute({"pattern": "[unclosed", "path": str(tree)})
    assert result.startswith("Error: invalid regex pattern")


def test_grep_missing_path(grep, tmp_path):
    result = grep.execute({"pattern": "x", "path": str(tmp_path / "nope")})
    assert result.startswith("Error: path does not exist")


def test_grep_pagination(grep, tree):
    all_r = json.loads(grep.execute({"pattern": "def ", "path": str(tree)}))
    page = json.loads(
        grep.execute(
            {"pattern": "def ", "path": str(tree), "head_limit": 1, "offset": 0}
        )
    )
    assert page["numFiles"] == 1
    assert page["appliedLimit"] == 1
    assert page["filenames"][0] == all_r["filenames"][0]
