"""Tests for agent-session-store."""

import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import pytest
from agent_session_store import Session, SessionStore, SessionStoreError


def make_store(tmp_path=None):
    if tmp_path is None:
        tmp_path = tempfile.mkdtemp()
    return SessionStore(tmp_path), tmp_path


# ---------------------------------------------------------------------------
# new()
# ---------------------------------------------------------------------------

def test_new_returns_id():
    store, _ = make_store()
    sid = store.new()
    assert isinstance(sid, str)
    assert len(sid) > 0

def test_new_creates_file():
    store, tmp = make_store()
    sid = store.new()
    assert Path(tmp, f"{sid}.jsonl").exists()

def test_new_custom_id():
    store, _ = make_store()
    sid = store.new("custom_id_123")
    assert sid == "custom_id_123"

def test_new_duplicate_raises():
    store, _ = make_store()
    store.new("dup")
    with pytest.raises(SessionStoreError, match="already exists"):
        store.new("dup")

def test_new_with_meta():
    store, _ = make_store()
    sid = store.new(meta={"task": "research"})
    session = store.load(sid)
    assert session.meta["task"] == "research"


# ---------------------------------------------------------------------------
# add_message()
# ---------------------------------------------------------------------------

def test_add_message():
    store, _ = make_store()
    sid = store.new()
    store.add_message(sid, {"role": "user", "content": "Hello"})
    session = store.load(sid)
    assert len(session.messages) == 1
    assert session.messages[0]["content"] == "Hello"

def test_add_multiple_messages():
    store, _ = make_store()
    sid = store.new()
    store.add_message(sid, {"role": "user", "content": "Q1"})
    store.add_message(sid, {"role": "assistant", "content": "A1"})
    store.add_message(sid, {"role": "user", "content": "Q2"})
    session = store.load(sid)
    assert len(session.messages) == 3
    assert session.messages[2]["content"] == "Q2"

def test_add_message_order_preserved():
    store, _ = make_store()
    sid = store.new()
    for i in range(5):
        store.add_message(sid, {"role": "user", "content": str(i)})
    session = store.load(sid)
    contents = [m["content"] for m in session.messages]
    assert contents == ["0", "1", "2", "3", "4"]

def test_add_message_missing_session_raises():
    store, _ = make_store()
    with pytest.raises(SessionStoreError, match="not found"):
        store.add_message("nonexistent", {"role": "user", "content": "x"})

def test_add_message_with_meta():
    store, _ = make_store()
    sid = store.new()
    store.add_message(sid, {"role": "user", "content": "x"}, meta={"turn": 1})
    session = store.load(sid)
    assert len(session.messages) == 1


# ---------------------------------------------------------------------------
# set_meta()
# ---------------------------------------------------------------------------

def test_set_meta():
    store, _ = make_store()
    sid = store.new()
    store.set_meta(sid, status="running")
    session = store.load(sid)
    assert session.meta["status"] == "running"

def test_set_meta_overwrites():
    store, _ = make_store()
    sid = store.new(meta={"status": "init"})
    store.set_meta(sid, status="complete")
    session = store.load(sid)
    assert session.meta["status"] == "complete"

def test_set_meta_missing_session_raises():
    store, _ = make_store()
    with pytest.raises(SessionStoreError):
        store.set_meta("nonexistent", x=1)


# ---------------------------------------------------------------------------
# delete()
# ---------------------------------------------------------------------------

def test_delete():
    store, tmp = make_store()
    sid = store.new()
    store.delete(sid)
    assert not Path(tmp, f"{sid}.jsonl").exists()

def test_delete_missing_raises():
    store, _ = make_store()
    with pytest.raises(SessionStoreError, match="not found"):
        store.delete("nonexistent")


# ---------------------------------------------------------------------------
# exists() / list_sessions() / count()
# ---------------------------------------------------------------------------

def test_exists_true():
    store, _ = make_store()
    sid = store.new()
    assert store.exists(sid) is True

def test_exists_false():
    store, _ = make_store()
    assert store.exists("nope") is False

def test_list_sessions_empty():
    store, _ = make_store()
    assert store.list_sessions() == []

def test_list_sessions():
    store, _ = make_store()
    store.new("b_session")
    store.new("a_session")
    assert store.list_sessions() == ["a_session", "b_session"]

def test_count():
    store, _ = make_store()
    assert store.count() == 0
    store.new()
    store.new()
    assert store.count() == 2


# ---------------------------------------------------------------------------
# Session object
# ---------------------------------------------------------------------------

def test_session_message_count():
    store, _ = make_store()
    sid = store.new()
    store.add_message(sid, {"role": "user", "content": "x"})
    session = store.load(sid)
    assert session.message_count == 1

def test_session_timestamps():
    import time
    store, _ = make_store()
    before = time.time()
    sid = store.new()
    after = time.time()
    session = store.load(sid)
    assert before <= session.created_at <= after
    assert session.updated_at is not None

def test_session_repr():
    store, _ = make_store()
    sid = store.new()
    session = store.load(sid)
    r = repr(session)
    assert "Session" in r
    assert sid in r


# ---------------------------------------------------------------------------
# Persistence (survives reload)
# ---------------------------------------------------------------------------

def test_reload_messages():
    tmp = tempfile.mkdtemp()
    store1 = SessionStore(tmp)
    sid = store1.new()
    store1.add_message(sid, {"role": "user", "content": "Q"})
    store1.add_message(sid, {"role": "assistant", "content": "A"})

    # Create new store pointing to same directory
    store2 = SessionStore(tmp)
    session = store2.load(sid)
    assert len(session.messages) == 2

def test_repr():
    store, _ = make_store()
    r = repr(store)
    assert "SessionStore" in r
