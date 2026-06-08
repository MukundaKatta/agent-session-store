# agent-session-store

Persist and retrieve multi-turn agent sessions to JSONL files — crash-safe append, metadata, list/delete.

Zero dependencies. Python 3.10+. MIT.

## Install

```bash
pip install agent-session-store
```

## Usage

```python
from agent_session_store import SessionStore

store = SessionStore("~/.agent_sessions")

# Start a new session
sid = store.new(meta={"task": "research", "user": "alice"})

# Append messages as the conversation progresses
store.add_message(sid, {"role": "user", "content": "What is DNA?"})
store.add_message(sid, {"role": "assistant", "content": "DNA is..."})

# Load back (e.g. on the next request)
session = store.load(sid)
print(session.messages)   # all messages in order
print(session.meta)       # {"task": "research", "user": "alice"}
```

## Session metadata

```python
# Set at creation
sid = store.new(meta={"task": "research"})

# Update during the session
store.set_meta(sid, status="complete", cost_usd=0.12)
```

## List and manage sessions

```python
store.list_sessions()   # ["abc123", "def456", ...]
store.count()           # 2
store.exists("abc123")  # True
store.delete("abc123")
```

## Session object

```python
session = store.load(sid)
session.session_id      # "abc123def456"
session.messages        # [{"role": "user", "content": "..."}, ...]
session.message_count   # 12
session.meta            # {"task": "research", ...}
session.created_at      # Unix timestamp
session.updated_at      # Unix timestamp
```

## Crash-safe

Messages are appended to disk immediately — if the process crashes mid-session, all messages up to the crash are preserved.

A crash can leave a **partial final line** in the JSONL file (a torn write). By
default, `load()` tolerates this: it skips any corrupted or partially written
line and returns every complete message. Pass `strict=True` to instead raise a
`SessionStoreError` when a malformed line is encountered:

```python
store = SessionStore("~/.agent_sessions", strict=True)  # raise on corruption
```

## API reference

`SessionStore(directory, *, id_length=12, strict=False)`

| Method | Description |
| --- | --- |
| `new(session_id=None, *, meta=None) -> str` | Create a session, return its ID. Raises `SessionStoreError` if the ID already exists. |
| `add_message(session_id, message, *, meta=None) -> None` | Append a message. Raises if the session is missing. |
| `set_meta(session_id, **kwargs) -> None` | Merge key/value pairs into the session metadata. |
| `load(session_id) -> Session` | Read the session back from disk. |
| `delete(session_id) -> None` | Remove a session permanently. |
| `exists(session_id) -> bool` | Whether the session exists. |
| `list_sessions() -> list[str]` | All session IDs, sorted. |
| `count() -> int` | Number of sessions in the store. |

`Session` is a dataclass with `session_id`, `messages`, `meta`, `created_at`,
`updated_at`, and a `message_count` property. All operations raise
`SessionStoreError` on invalid input (missing or duplicate sessions).

## Development

Run the test suite with the standard library only — no third-party
dependencies are required:

```bash
python3 -m unittest discover -s tests
```

## License

MIT
