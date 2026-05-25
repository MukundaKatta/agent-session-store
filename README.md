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

## License

MIT
