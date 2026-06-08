"""Tests for agent-session-store.

These tests use only the Python standard library (``unittest``) so they run
with::

    python3 -m unittest discover -s tests

They import and exercise the real package from ``src/``.
"""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agent_session_store import (  # noqa: E402
    Session,
    SessionStore,
    SessionStoreError,
)


class StoreTestCase(unittest.TestCase):
    """Base class that gives each test a fresh, auto-cleaned directory."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.store = SessionStore(self.tmp)

    def tearDown(self) -> None:
        self._tmp.cleanup()


# ---------------------------------------------------------------------------
# new()
# ---------------------------------------------------------------------------


class TestNew(StoreTestCase):
    def test_new_returns_id(self):
        sid = self.store.new()
        self.assertIsInstance(sid, str)
        self.assertGreater(len(sid), 0)

    def test_new_creates_file(self):
        sid = self.store.new()
        self.assertTrue(Path(self.tmp, f"{sid}.jsonl").exists())

    def test_new_custom_id(self):
        sid = self.store.new("custom_id_123")
        self.assertEqual(sid, "custom_id_123")

    def test_new_duplicate_raises(self):
        self.store.new("dup")
        with self.assertRaisesRegex(SessionStoreError, "already exists"):
            self.store.new("dup")

    def test_new_with_meta(self):
        sid = self.store.new(meta={"task": "research"})
        session = self.store.load(sid)
        self.assertEqual(session.meta["task"], "research")

    def test_id_length_is_clamped(self):
        short = SessionStore(self.tmp, id_length=2)
        sid = short.new()
        self.assertEqual(len(sid), 8)
        long = SessionStore(self.tmp, id_length=999)
        self.assertEqual(len(long.new()), 32)


# ---------------------------------------------------------------------------
# add_message()
# ---------------------------------------------------------------------------


class TestAddMessage(StoreTestCase):
    def test_add_message(self):
        sid = self.store.new()
        self.store.add_message(sid, {"role": "user", "content": "Hello"})
        session = self.store.load(sid)
        self.assertEqual(len(session.messages), 1)
        self.assertEqual(session.messages[0]["content"], "Hello")

    def test_add_multiple_messages(self):
        sid = self.store.new()
        self.store.add_message(sid, {"role": "user", "content": "Q1"})
        self.store.add_message(sid, {"role": "assistant", "content": "A1"})
        self.store.add_message(sid, {"role": "user", "content": "Q2"})
        session = self.store.load(sid)
        self.assertEqual(len(session.messages), 3)
        self.assertEqual(session.messages[2]["content"], "Q2")

    def test_add_message_order_preserved(self):
        sid = self.store.new()
        for i in range(5):
            self.store.add_message(sid, {"role": "user", "content": str(i)})
        session = self.store.load(sid)
        contents = [m["content"] for m in session.messages]
        self.assertEqual(contents, ["0", "1", "2", "3", "4"])

    def test_add_message_missing_session_raises(self):
        with self.assertRaisesRegex(SessionStoreError, "not found"):
            self.store.add_message("nonexistent", {"role": "user", "content": "x"})

    def test_add_message_with_meta(self):
        sid = self.store.new()
        self.store.add_message(sid, {"role": "user", "content": "x"}, meta={"turn": 1})
        session = self.store.load(sid)
        self.assertEqual(len(session.messages), 1)


# ---------------------------------------------------------------------------
# set_meta()
# ---------------------------------------------------------------------------


class TestSetMeta(StoreTestCase):
    def test_set_meta(self):
        sid = self.store.new()
        self.store.set_meta(sid, status="running")
        session = self.store.load(sid)
        self.assertEqual(session.meta["status"], "running")

    def test_set_meta_overwrites(self):
        sid = self.store.new(meta={"status": "init"})
        self.store.set_meta(sid, status="complete")
        session = self.store.load(sid)
        self.assertEqual(session.meta["status"], "complete")

    def test_set_meta_merges_keys(self):
        sid = self.store.new(meta={"a": 1})
        self.store.set_meta(sid, b=2)
        session = self.store.load(sid)
        self.assertEqual(session.meta, {"a": 1, "b": 2})

    def test_set_meta_missing_session_raises(self):
        with self.assertRaises(SessionStoreError):
            self.store.set_meta("nonexistent", x=1)


# ---------------------------------------------------------------------------
# delete()
# ---------------------------------------------------------------------------


class TestDelete(StoreTestCase):
    def test_delete(self):
        sid = self.store.new()
        self.store.delete(sid)
        self.assertFalse(Path(self.tmp, f"{sid}.jsonl").exists())

    def test_delete_missing_raises(self):
        with self.assertRaisesRegex(SessionStoreError, "not found"):
            self.store.delete("nonexistent")


# ---------------------------------------------------------------------------
# exists() / list_sessions() / count()
# ---------------------------------------------------------------------------


class TestListing(StoreTestCase):
    def test_exists_true(self):
        sid = self.store.new()
        self.assertTrue(self.store.exists(sid))

    def test_exists_false(self):
        self.assertFalse(self.store.exists("nope"))

    def test_list_sessions_empty(self):
        self.assertEqual(self.store.list_sessions(), [])

    def test_list_sessions_sorted(self):
        self.store.new("b_session")
        self.store.new("a_session")
        self.assertEqual(self.store.list_sessions(), ["a_session", "b_session"])

    def test_count(self):
        self.assertEqual(self.store.count(), 0)
        self.store.new()
        self.store.new()
        self.assertEqual(self.store.count(), 2)


# ---------------------------------------------------------------------------
# Session object
# ---------------------------------------------------------------------------


class TestSessionObject(StoreTestCase):
    def test_session_message_count(self):
        sid = self.store.new()
        self.store.add_message(sid, {"role": "user", "content": "x"})
        session = self.store.load(sid)
        self.assertEqual(session.message_count, 1)

    def test_session_timestamps(self):
        before = time.time()
        sid = self.store.new()
        after = time.time()
        session = self.store.load(sid)
        self.assertLessEqual(before, session.created_at)
        self.assertLessEqual(session.created_at, after)
        self.assertIsNotNone(session.updated_at)

    def test_session_repr(self):
        sid = self.store.new()
        session = self.store.load(sid)
        r = repr(session)
        self.assertIn("Session", r)
        self.assertIn(sid, r)

    def test_session_is_dataclass_instance(self):
        sid = self.store.new()
        self.assertIsInstance(self.store.load(sid), Session)


# ---------------------------------------------------------------------------
# Persistence (survives reload)
# ---------------------------------------------------------------------------


class TestPersistence(StoreTestCase):
    def test_reload_messages(self):
        store1 = SessionStore(self.tmp)
        sid = store1.new()
        store1.add_message(sid, {"role": "user", "content": "Q"})
        store1.add_message(sid, {"role": "assistant", "content": "A"})

        # A fresh store pointing at the same directory must see the data.
        store2 = SessionStore(self.tmp)
        session = store2.load(sid)
        self.assertEqual(len(session.messages), 2)

    def test_store_repr(self):
        r = repr(self.store)
        self.assertIn("SessionStore", r)


# ---------------------------------------------------------------------------
# Crash-safety: a torn/corrupted final line must not break load() by default.
# This covers the regression fixed alongside these tests.
# ---------------------------------------------------------------------------


class TestCorruptedLines(StoreTestCase):
    def _append_raw(self, sid: str, text: str) -> None:
        with open(Path(self.tmp, f"{sid}.jsonl"), "a", encoding="utf-8") as f:
            f.write(text)

    def test_torn_final_line_is_skipped(self):
        sid = self.store.new()
        self.store.add_message(sid, {"role": "user", "content": "kept"})
        # Simulate a crash mid-append: a truncated JSON line with no newline.
        self._append_raw(sid, '{"_event": "message", "ts": 1.0, "messa')
        session = self.store.load(sid)  # must not raise
        self.assertEqual(len(session.messages), 1)
        self.assertEqual(session.messages[0]["content"], "kept")

    def test_garbage_line_is_skipped(self):
        sid = self.store.new()
        self._append_raw(sid, "not json at all\n")
        self.store.add_message(sid, {"role": "user", "content": "after"})
        session = self.store.load(sid)
        self.assertEqual(len(session.messages), 1)
        self.assertEqual(session.messages[0]["content"], "after")

    def test_message_event_without_payload_is_skipped(self):
        sid = self.store.new()
        self._append_raw(sid, '{"_event": "message", "ts": 1.0}\n')
        session = self.store.load(sid)
        self.assertEqual(session.messages, [])

    def test_strict_mode_raises_on_corruption(self):
        strict = SessionStore(self.tmp, strict=True)
        sid = strict.new()
        self._append_raw(sid, "this is not json\n")
        with self.assertRaisesRegex(SessionStoreError, "corrupted line"):
            strict.load(sid)

    def test_strict_mode_loads_clean_session(self):
        strict = SessionStore(self.tmp, strict=True)
        sid = strict.new()
        strict.add_message(sid, {"role": "user", "content": "ok"})
        session = strict.load(sid)
        self.assertEqual(len(session.messages), 1)


if __name__ == "__main__":
    unittest.main()
