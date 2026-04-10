"""Session persistence -- save/load conversation history as JSONL.

Each session is stored as a single JSONL file under ~/.claw/sessions/.
Every line is a JSON object with a "type" discriminator:

  {"type": "meta",  "session_id": "...", "created_at": "...", "model": "..."}
  {"type": "turn",  "seq": 1, "timestamp": "...", "messages": [...],
                    "tool_calls": [...], "input_tokens": N, "output_tokens": N}

Append-only design: a crash between writes never corrupts the file --
you only lose the last partial turn.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Message

_SESSIONS_DIR = Path.home() / ".claw" / "sessions"


def _sessions_dir() -> Path:
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return _SESSIONS_DIR


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Session:
    """Represents one conversation session backed by a JSONL file."""

    def __init__(
        self,
        session_id: str | None = None,
        model: str = "unknown",
    ) -> None:
        self.session_id: str = session_id or str(uuid.uuid4())
        self.model: str = model
        self.created_at: str = _now()
        self._path: Path = _sessions_dir() / f"{self.session_id}.jsonl"
        self._turn_seq: int = 0
        self._wrote_meta: bool = False

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def _append(self, record: dict[str, Any]) -> None:
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _ensure_meta(self) -> None:
        if not self._wrote_meta:
            self._append({
                "type": "meta",
                "session_id": self.session_id,
                "created_at": self.created_at,
                "model": self.model,
            })
            self._wrote_meta = True

    def save_turn(
        self,
        messages: list[Message],
        tool_calls: list[dict[str, Any]],
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Append one completed turn to the session file."""
        self._ensure_meta()
        self._turn_seq += 1
        self._append({
            "type": "turn",
            "seq": self._turn_seq,
            "timestamp": _now(),
            "messages": [m.model_dump() for m in messages],
            "tool_calls": tool_calls,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        })

    @property
    def path(self) -> Path:
        return self._path

    # ------------------------------------------------------------------
    # Reading / listing
    # ------------------------------------------------------------------

    @staticmethod
    def load(session_id: str) -> "LoadedSession":
        """Load all records from a session file by ID."""
        path = _sessions_dir() / f"{session_id}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"session not found: {session_id}")
        records: list[dict[str, Any]] = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return LoadedSession(session_id=session_id, path=path, records=records)

    @staticmethod
    def list_all() -> list[dict[str, Any]]:
        """Return summary dicts for every session, newest first."""
        results = []
        for p in sorted(
            _sessions_dir().glob("*.jsonl"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        ):
            sid = p.stem
            meta: dict[str, Any] = {"session_id": sid, "path": str(p)}
            try:
                with p.open(encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        rec = json.loads(line)
                        if rec.get("type") == "meta":
                            meta.update(rec)
                            break
            except (OSError, json.JSONDecodeError):
                pass
            results.append(meta)
        return results


class LoadedSession:
    """A fully-loaded session (read-only view)."""

    def __init__(
        self,
        session_id: str,
        path: Path,
        records: list[dict[str, Any]],
    ) -> None:
        self.session_id = session_id
        self.path = path
        self.records = records

    @property
    def meta(self) -> dict[str, Any]:
        return next((r for r in self.records if r.get("type") == "meta"), {})

    @property
    def turns(self) -> list[dict[str, Any]]:
        return [r for r in self.records if r.get("type") == "turn"]
