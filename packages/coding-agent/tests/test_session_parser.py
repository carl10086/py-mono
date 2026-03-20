from __future__ import annotations

from coding_agent.session.parser import (
    is_valid_session_header,
    migrate_session_entries,
    parse_session_entries,
    validate_session_entries,
)
from coding_agent.session.types import (
    CURRENT_SESSION_VERSION,
    SessionHeader,
    SessionMessageEntry,
)


def test_parse_session() -> None:
    content = """
{"type": "session", "version": 3, "id": "test-session-123", "timestamp": "2024-01-01T00:00:00Z", "cwd": "/test/project"}
{"type": "message", "id": "msg001", "parent_id": null, "timestamp": "2024-01-01T00:00:01Z", "message": {"role": "user", "content": [{"type": "text", "text": "Hello"}], "timestamp": 1704067201000}}
{"type": "thinking_level_change", "id": "think001", "parent_id": "msg001", "timestamp": "2024-01-01T00:00:02Z", "thinking_level": "high"}
{"type": "model_change", "id": "model001", "parent_id": "think001", "timestamp": "2024-01-01T00:00:03Z", "provider": "anthropic", "model_id": "claude-3"}
"""

    entries = parse_session_entries(content)
    assert len(entries) == 4
    assert isinstance(entries[0], SessionHeader)


def test_validation() -> None:
    valid_header = {
        "type": "session",
        "id": "test-123",
        "timestamp": "2024-01-01T00:00:00Z",
        "cwd": "/test",
    }
    assert is_valid_session_header(valid_header) is True

    invalid_header = {
        "type": "message",
        "content": "test",
    }
    assert is_valid_session_header(invalid_header) is False

    content = """
{"type": "session", "version": 3, "id": "test-123", "timestamp": "2024-01-01T00:00:00Z", "cwd": "/test"}
{"type": "message", "id": "msg001", "parent_id": null, "timestamp": "2024-01-01T00:00:01Z", "message": {"role": "user", "content": "Hello", "timestamp": 1000}}
"""
    entries = parse_session_entries(content)
    errors = validate_session_entries(entries)
    assert isinstance(errors, list)


def test_migration() -> None:
    content = """
{"type": "session", "version": 1, "id": "v1-session", "timestamp": "2024-01-01T00:00:00Z", "cwd": "/test"}
{"type": "message", "timestamp": "2024-01-01T00:00:01Z", "message": {"role": "user", "content": "Hello", "timestamp": 1000}}
"""

    entries = parse_session_entries(content)
    assert len(entries) == 2

    header = next((e for e in entries if isinstance(e, SessionHeader)), None)
    assert header is not None
    assert header.version == 1

    migrated = migrate_session_entries(entries)
    assert migrated is True
    assert header.version == CURRENT_SESSION_VERSION

    migrated_again = migrate_session_entries(entries)
    assert migrated_again is False
