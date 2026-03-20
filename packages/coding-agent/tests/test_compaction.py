from __future__ import annotations

from coding_agent.compaction import (
    CompactionSettings,
    calculate_context_tokens,
    compact,
    prepare_compaction,
    serialize_conversation,
)
from coding_agent.session.types import SessionMessageEntry


def test_calculate_context_tokens_total_tokens():
    usage1 = {"totalTokens": 1500}
    assert calculate_context_tokens(usage1) == 1500


def test_calculate_context_tokens_components():
    usage2 = {"input": 1000, "output": 500, "cacheRead": 200, "cacheWrite": 100}
    assert calculate_context_tokens(usage2) == 1800


def test_calculate_context_tokens_empty():
    usage3 = {}
    assert calculate_context_tokens(usage3) == 0


def test_serialize_conversation():
    messages = [
        {"role": "user", "content": "Hello, can you help me?"},
        {"role": "assistant", "content": "Yes, I can help you."},
        {"role": "user", "content": "Thank you!"},
    ]
    serialized = serialize_conversation(messages)
    assert len(serialized) > 0
    assert "Hello" in serialized or "Hello" in serialized


def test_prepare_compaction():
    settings = CompactionSettings(enabled=True, keep_recent_tokens=200)
    entries = []
    for i in range(20):
        msg = {
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"Message {i} content " * 30,
        }
        entry = SessionMessageEntry(
            id=f"msg{i:03d}",
            parent_id=None if i == 0 else f"msg{i - 1:03d}",
            timestamp="2024-01-01T00:00:00Z",
            message=msg,
        )
        entries.append(entry)

    result = prepare_compaction(entries, settings)
    assert result.first_kept_entry_id is not None
    assert result.tokens_before >= 0


def test_compact_function():
    settings = CompactionSettings(enabled=True, keep_recent_tokens=500)
    entries = []
    for i in range(15):
        role = "user" if i % 2 == 0 else "assistant"
        content = f"This is message number {i} with some content. " * 50
        msg = {"role": role, "content": content}
        entry = SessionMessageEntry(
            id=f"msg{i:03d}",
            parent_id=None if i == 0 else f"msg{i - 1:03d}",
            timestamp="2024-01-01T00:00:00Z",
            message=msg,
        )
        entries.append(entry)

    result = compact(entries, settings)
    if result:
        assert len(result.summary) > 0
        assert result.first_kept_entry_id is not None


def test_compact_disabled():
    settings = CompactionSettings(enabled=False)
    entries = []
    for i in range(5):
        msg = {"role": "user", "content": "Test " * 1000}
        entry = SessionMessageEntry(
            id=f"msg{i}",
            parent_id=None if i == 0 else f"msg{i - 1}",
            timestamp="2024-01-01T00:00:00Z",
            message=msg,
        )
        entries.append(entry)

    result = compact(entries, settings)
    assert result is None
