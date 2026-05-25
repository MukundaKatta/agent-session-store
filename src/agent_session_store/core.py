"""Persist and retrieve multi-turn agent sessions.

Each session is stored as a JSONL file (one event per line) in a directory.
Session IDs are short UUID4 prefixes by default.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class SessionStoreError(Exception):
    """Raised on invalid session store operations."""


@dataclass
class Session:
    """A loaded agent session.

    Attributes:
        session_id: unique session identifier.
        messages: ordered list of message dicts.
        meta: session-level metadata dict.
        created_at: Unix timestamp from the first event.
        updated_at: Unix timestamp from the last event.
    """

    session_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: float | None = None
    updated_at: float | None = None

    @property
    def message_count(self) -> int:
        return len(self.messages)

    def __repr__(self) -> str:
        return (
            f"Session(id={self.session_id!r}, messages={self.message_count}, "
            f"meta={list(self.meta)!r})"
        )


class SessionStore:
    """File-backed store for multi-turn agent sessions.

    Each session is saved as a JSONL file in a directory. Messages are
    appended to the file as they are added, so the store survives crashes.

    Args:
        directory: path to the session store directory (created if missing).
        id_length: number of hex chars in auto-generated session IDs (8..32).

    Example::

        store = SessionStore("~/.agent_sessions")
        sid = store.new(meta={"task": "research"})
        store.add_message(sid, {"role": "user", "content": "Hello"})
        store.add_message(sid, {"role": "assistant", "content": "Hi!"})

        session = store.load(sid)
        print(session.messages)
    """

    def __init__(
        self,
        directory: str | Path,
        *,
        id_length: int = 12,
    ) -> None:
        self.directory = Path(directory).expanduser()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.id_length = max(8, min(32, id_length))

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def new(
        self,
        session_id: str | None = None,
        *,
        meta: dict[str, Any] | None = None,
    ) -> str:
        """Create a new empty session and return its ID.

        Args:
            session_id: optional custom ID; auto-generated if None.
            meta: optional session-level metadata dict.

        Returns:
            Session ID string.

        Raises:
            SessionStoreError: if a session with that ID already exists.
        """
        sid = session_id or uuid.uuid4().hex[: self.id_length]
        path = self._path(sid)
        if path.exists():
            raise SessionStoreError(f"session {sid!r} already exists")
        now = time.time()
        entry: dict[str, Any] = {"_event": "session_created", "ts": now}
        if meta:
            entry["meta"] = meta
        with path.open("w", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return sid

    def add_message(
        self,
        session_id: str,
        message: dict[str, Any],
        *,
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Append a message to the session.

        Args:
            session_id: the session to append to.
            message: a message dict (typically {"role": ..., "content": ...}).
            meta: optional per-message metadata.

        Raises:
            SessionStoreError: if the session does not exist.
        """
        path = self._path(session_id)
        if not path.exists():
            raise SessionStoreError(f"session {session_id!r} not found")
        entry: dict[str, Any] = {
            "_event": "message",
            "ts": time.time(),
            "message": message,
        }
        if meta:
            entry["meta"] = meta
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def set_meta(self, session_id: str, **kwargs: Any) -> None:
        """Append a metadata update event to the session."""
        path = self._path(session_id)
        if not path.exists():
            raise SessionStoreError(f"session {session_id!r} not found")
        entry = {"_event": "meta_update", "ts": time.time(), "meta": kwargs}
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def delete(self, session_id: str) -> None:
        """Delete a session permanently.

        Raises:
            SessionStoreError: if the session does not exist.
        """
        path = self._path(session_id)
        if not path.exists():
            raise SessionStoreError(f"session {session_id!r} not found")
        path.unlink()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, session_id: str) -> Session:
        """Load a session from disk.

        Returns:
            Session object with messages and merged metadata.

        Raises:
            SessionStoreError: if the session does not exist.
        """
        path = self._path(session_id)
        if not path.exists():
            raise SessionStoreError(f"session {session_id!r} not found")
        return self._parse(session_id, path)

    def exists(self, session_id: str) -> bool:
        """Return True if the session exists."""
        return self._path(session_id).exists()

    def list_sessions(self) -> list[str]:
        """Return all session IDs in the store (sorted)."""
        return sorted(
            p.stem for p in self.directory.glob("*.jsonl")
        )

    def count(self) -> int:
        """Return the number of sessions."""
        return len(list(self.directory.glob("*.jsonl")))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _path(self, session_id: str) -> Path:
        return self.directory / f"{session_id}.jsonl"

    def _parse(self, session_id: str, path: Path) -> Session:
        messages: list[dict[str, Any]] = []
        meta: dict[str, Any] = {}
        created_at: float | None = None
        updated_at: float | None = None

        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            ts = entry.get("ts", 0.0)
            if created_at is None:
                created_at = ts
            updated_at = ts
            event = entry.get("_event", "")
            if event == "session_created":
                if "meta" in entry:
                    meta.update(entry["meta"])
            elif event == "meta_update":
                if "meta" in entry:
                    meta.update(entry["meta"])
            elif event == "message":
                messages.append(entry["message"])

        return Session(
            session_id=session_id,
            messages=messages,
            meta=meta,
            created_at=created_at,
            updated_at=updated_at,
        )

    def __repr__(self) -> str:
        return f"SessionStore(directory={str(self.directory)!r}, count={self.count()})"
