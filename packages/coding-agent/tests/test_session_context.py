from __future__ import annotations

from coding_agent.session.context import (
    build_session_context,
    get_latest_compaction_entry,
)
from coding_agent.session.types import (
    CompactionEntry,
    ModelChangeEntry,
    SessionEntry,
    SessionMessageEntry,
    ThinkingLevelChangeEntry,
)


def test_get_latest_compaction() -> None:
    entries: list[SessionEntry] = [
        SessionMessageEntry(
            id="msg001",
            parent_id=None,
            timestamp="2024-01-01T00:00:01Z",
            message={"role": "user", "content": "Hello", "timestamp": 1000},
        ),
        CompactionEntry(
            id="comp001",
            parent_id="msg001",
            timestamp="2024-01-01T00:00:02Z",
            summary="Summary 1",
            first_kept_entry_id="msg001",
            tokens_before=1000,
        ),
        SessionMessageEntry(
            id="msg002",
            parent_id="comp001",
            timestamp="2024-01-01T00:00:03Z",
            message={"role": "user", "content": "World", "timestamp": 2000},
        ),
        CompactionEntry(
            id="comp002",
            parent_id="msg002",
            timestamp="2024-01-01T00:00:04Z",
            summary="Summary 2",
            first_kept_entry_id="msg002",
            tokens_before=2000,
        ),
    ]

    latest = get_latest_compaction_entry(entries)
    assert latest is not None
    assert latest.id == "comp002"

    empty_entries: list[SessionEntry] = []
    result = get_latest_compaction_entry(empty_entries)
    assert result is None


def test_build_context() -> None:
    entries: list[SessionEntry] = [
        SessionMessageEntry(
            id="msg001",
            parent_id=None,
            timestamp="2024-01-01T00:00:01Z",
            message={"role": "user", "content": "Hello", "timestamp": 1000},
        ),
        ThinkingLevelChangeEntry(
            id="think001",
            parent_id="msg001",
            timestamp="2024-01-01T00:00:02Z",
            thinking_level="high",
        ),
        ModelChangeEntry(
            id="model001",
            parent_id="think001",
            timestamp="2024-01-01T00:00:03Z",
            provider="anthropic",
            model_id="claude-3",
        ),
        SessionMessageEntry(
            id="msg002",
            parent_id="model001",
            timestamp="2024-01-01T00:00:04Z",
            message={"role": "assistant", "content": "Hi!", "timestamp": 2000},
        ),
    ]

    by_id = {e.id: e for e in entries}
    context = build_session_context(entries, leaf_id="msg002", by_id=by_id)

    assert context.thinking_level == "high"
    assert context.model is not None
    assert context.model["provider"] == "anthropic"


def test_context_with_compaction() -> None:
    entries: list[SessionEntry] = [
        SessionMessageEntry(
            id="msg001",
            parent_id=None,
            timestamp="2024-01-01T00:00:01Z",
            message={"role": "user", "content": "First", "timestamp": 1000},
        ),
        SessionMessageEntry(
            id="msg002",
            parent_id="msg001",
            timestamp="2024-01-01T00:00:02Z",
            message={"role": "assistant", "content": "Reply", "timestamp": 2000},
        ),
        CompactionEntry(
            id="comp001",
            parent_id="msg002",
            timestamp="2024-01-01T00:00:03Z",
            summary="Previous conversation",
            first_kept_entry_id="msg001",
            tokens_before=5000,
        ),
        SessionMessageEntry(
            id="msg003",
            parent_id="comp001",
            timestamp="2024-01-01T00:00:04Z",
            message={"role": "user", "content": "Second", "timestamp": 3000},
        ),
    ]

    by_id = {e.id: e for e in entries}
    context = build_session_context(entries, leaf_id="msg003", by_id=by_id)

    assert isinstance(context.messages, list)


def test_empty_context() -> None:
    empty_entries: list[SessionEntry] = []
    context = build_session_context(empty_entries)

    assert len(context.messages) == 0
    assert context.thinking_level == "off"
    assert context.model is None
