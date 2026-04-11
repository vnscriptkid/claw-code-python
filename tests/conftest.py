"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture()
def tmp_file(tmp_path):
    """Return a factory that creates a named temp file with given content."""

    def _make(name: str = "test.txt", content: str = "") -> str:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return str(p)

    return _make


@pytest.fixture()
def tmp_dir(tmp_path):
    """Return a tmp_path as a string (for tools that take path strings)."""
    return str(tmp_path)
