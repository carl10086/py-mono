from __future__ import annotations

from coding_agent.config import (
    VERSION,
    get_agent_dir,
    get_default_session_dir,
    get_sessions_dir,
)
from coding_agent.session.types import (
    CURRENT_SESSION_VERSION,
    CompactionEntry,
    ModelChangeEntry,
    NewSessionOptions,
    SessionContext,
    SessionEntryBase,
    SessionHeader,
    SessionInfo,
    SessionMessageEntry,
    SessionTreeNode,
    ThinkingLevelChangeEntry,
    get_entry_type_name,
    is_compaction_entry,
    is_model_change_entry,
    is_session_message_entry,
)


def test_config() -> None:
    assert VERSION is not None
    assert CURRENT_SESSION_VERSION is not None
    assert get_agent_dir() is not None
    assert get_sessions_dir() is not None


def test_session_types() -> None:
    base = SessionEntryBase(
        type="test",
        id="abc123",
        parent_id=None,
        timestamp="2024-01-01T00:00:00Z",
    )
    assert base.id == "abc123"
    assert base.type == "test"

    header = SessionHeader(
        id="session-uuid-123",
        timestamp="2024-01-01T00:00:00Z",
        cwd="/home/user/project",
    )
    assert header.id == "session-uuid-123"
    assert header.version == CURRENT_SESSION_VERSION

    msg_entry = SessionMessageEntry(
        id="msg001",
        parent_id=None,
        timestamp="2024-01-01T00:00:01Z",
        message={
            "role": "user",
            "content": [{"type": "text", "text": "Hello"}],
            "timestamp": 1704067201000,
        },
    )
    assert is_session_message_entry(msg_entry)
    assert "消息" in get_entry_type_name(msg_entry) or "message" in get_entry_type_name(msg_entry)

    think_entry = ThinkingLevelChangeEntry(
        id="think001",
        parent_id="msg001",
        timestamp="2024-01-01T00:00:02Z",
        thinking_level="high",
    )
    assert "thinking" in get_entry_type_name(think_entry) or "思考" in get_entry_type_name(
        think_entry
    )

    model_entry = ModelChangeEntry(
        id="model001",
        parent_id="think001",
        timestamp="2024-01-01T00:00:03Z",
        provider="anthropic",
        model_id="claude-3-sonnet",
    )
    assert is_model_change_entry(model_entry)
    assert model_entry.provider == "anthropic"

    compaction_entry = CompactionEntry(
        id="compact001",
        parent_id="model001",
        timestamp="2024-01-01T00:00:04Z",
        summary="Summary of previous conversation",
        first_kept_entry_id="msg001",
        tokens_before=10000,
    )
    assert is_compaction_entry(compaction_entry)
    assert "Summary" in compaction_entry.summary

    context = SessionContext(
        messages=[],
        thinking_level="medium",
        model={"provider": "anthropic", "modelId": "claude-3"},
    )
    assert context.thinking_level == "medium"

    info = SessionInfo(
        path="/path/to/session.jsonl",
        id="session-123",
        cwd="/home/user/project",
        name="My Session",
        created="2024-01-01T00:00:00Z",
        modified="2024-01-01T01:00:00Z",
        message_count=42,
        first_message="Hello, how can I help?",
        all_messages_text="Hello...",
    )
    assert info.name == "My Session"
    assert info.message_count == 42

    tree_node = SessionTreeNode(
        entry=msg_entry,
        children=[],
        label="First message",
    )
    assert tree_node.label == "First message"
    assert len(tree_node.children) == 0


def test_options() -> None:
    options = NewSessionOptions(
        id="custom-session-id",
        parent_session="/path/to/parent.jsonl",
    )
    assert options.id == "custom-session-id"
    assert options.parent_session == "/path/to/parent.jsonl"

    default_options = NewSessionOptions()
    assert default_options is not None
