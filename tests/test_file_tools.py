"""Tests for read_file, write_file, and edit_file tools."""

from __future__ import annotations

import pytest

from claw_code_python.tools.edit_file import EditFileTool
from claw_code_python.tools.read_file import ReadFileTool
from claw_code_python.tools.write_file import WriteFileTool


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------


@pytest.fixture()
def read():
    return ReadFileTool()


def test_read_full_file(read, tmp_file):
    path = tmp_file("hello.txt", "line1\nline2\nline3\n")
    result = read.execute({"path": path})
    assert "line1" in result
    assert "line2" in result
    assert "line3" in result


def test_read_with_offset(read, tmp_file):
    path = tmp_file("nums.txt", "alpha\nbeta\ngamma\ndelta\n")
    result = read.execute({"path": path, "offset": 2})
    assert "gamma" in result
    assert "alpha" not in result


def test_read_with_limit(read, tmp_file):
    path = tmp_file("nums.txt", "alpha\nbeta\ngamma\ndelta\n")
    result = read.execute({"path": path, "limit": 2})
    assert "alpha" in result
    assert "beta" in result
    assert "gamma" not in result


def test_read_missing_file(read, tmp_path):
    with pytest.raises(FileNotFoundError):
        read.execute({"path": str(tmp_path / "nope.txt")})


def test_read_binary_file(read, tmp_path):
    p = tmp_path / "bin.dat"
    p.write_bytes(b"\x00\x01\x02\x03")
    with pytest.raises(ValueError, match="binary"):
        read.execute({"path": str(p)})


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------


@pytest.fixture()
def write():
    return WriteFileTool()


def test_write_creates_file(write, tmp_path):
    path = str(tmp_path / "new.txt")
    result = write.execute({"path": path, "content": "hello"})
    assert "Created" in result
    assert (tmp_path / "new.txt").read_text() == "hello"


def test_write_overwrites_file(write, tmp_file):
    path = tmp_file("existing.txt", "old content")
    result = write.execute({"path": path, "content": "new content"})
    assert "Updated" in result
    from pathlib import Path

    assert Path(path).read_text() == "new content"


def test_write_creates_parent_dirs(write, tmp_path):
    path = str(tmp_path / "a" / "b" / "c.txt")
    write.execute({"path": path, "content": "deep"})
    from pathlib import Path

    assert Path(path).read_text() == "deep"


def test_write_rejects_oversized_content(write, tmp_path):
    path = str(tmp_path / "big.txt")
    big = "x" * (10 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="too large"):
        write.execute({"path": path, "content": big})


# ---------------------------------------------------------------------------
# edit_file
# ---------------------------------------------------------------------------


@pytest.fixture()
def edit():
    return EditFileTool()


def test_edit_replaces_first_occurrence(edit, tmp_file):
    path = tmp_file("code.py", "foo = 1\n")
    edit.execute({"path": path, "old_string": "foo", "new_string": "bar"})
    from pathlib import Path

    assert Path(path).read_text() == "bar = 1\n"


def test_edit_replace_all(edit, tmp_file):
    path = tmp_file("code.py", "x = x + x\n")
    edit.execute(
        {"path": path, "old_string": "x", "new_string": "y", "replace_all": True}
    )
    from pathlib import Path

    assert Path(path).read_text() == "y = y + y\n"


def test_edit_errors_on_ambiguous(edit, tmp_file):
    path = tmp_file("dup.py", "x = 1\nx = 2\n")
    with pytest.raises(ValueError, match="appears 2 times"):
        edit.execute({"path": path, "old_string": "x", "new_string": "z"})


def test_edit_errors_on_missing_string(edit, tmp_file):
    path = tmp_file("f.py", "hello\n")
    with pytest.raises(ValueError, match="not found"):
        edit.execute({"path": path, "old_string": "world", "new_string": "!"})


def test_edit_errors_same_strings(edit, tmp_file):
    path = tmp_file("f.py", "hello\n")
    with pytest.raises(ValueError, match="must differ"):
        edit.execute({"path": path, "old_string": "hello", "new_string": "hello"})


def test_edit_missing_file(edit, tmp_path):
    with pytest.raises(FileNotFoundError):
        edit.execute(
            {
                "path": str(tmp_path / "ghost.py"),
                "old_string": "a",
                "new_string": "b",
            }
        )
