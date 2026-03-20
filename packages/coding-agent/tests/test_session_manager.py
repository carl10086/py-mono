from __future__ import annotations

import tempfile
from typing import Any

from coding_agent.session import SessionManager
from coding_agent.session.types import NewSessionOptions


class MockMessage:
    """模拟 AgentMessage"""

    def __init__(self, role: str, content: str) -> None:
        self.role = role
        self.content = content
        self.timestamp = 1234567890


def test_in_memory_session() -> None:
    manager = SessionManager.in_memory("/test/project")
    assert manager.session_id is not None
    assert manager.cwd == "/test/project"
    assert manager.is_persisted() is False


def test_persistent_session() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SessionManager.create(
            cwd="/home/user/myproject",
            session_dir=tmpdir,
        )

        assert manager.session_id is not None
        assert manager.is_persisted() is True


def test_open_session() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        manager1 = SessionManager.create(
            cwd="/home/user/project1",
            session_dir=tmpdir,
        )

        msg1 = MockMessage("user", "Hello")
        manager1.append_message(msg1)
        msg2 = MockMessage("assistant", "Hi")
        manager1.append_message(msg2)

        original_id = manager1.session_id
        session_file = manager1.session_file

        assert session_file is not None
        import os

        assert os.path.exists(session_file)

        manager2 = SessionManager.open(session_file)
        assert manager2.session_id == original_id
        assert manager2.cwd == "/home/user/project1"


def test_tree_navigation() -> None:
    manager = SessionManager.in_memory("/test/project")

    manager.append_message(MockMessage("user", "Hello"))
    manager.append_message(MockMessage("assistant", "Hi"))

    assert manager.get_leaf_id() is not None
    entries = manager.get_entries()
    assert len(entries) == 2
    branch = manager.get_branch()
    assert isinstance(branch, list)
    assert len(branch) == 2


def test_append_message() -> None:
    """测试追加消息条目"""
    manager = SessionManager.in_memory("/test/project")

    msg1 = MockMessage("user", "Hello")
    entry1 = manager.append_message(msg1)

    assert entry1.id is not None
    assert entry1.type == "message"
    assert entry1.parent_id is None

    entries = manager.get_entries()
    assert len(entries) == 1
    assert entries[0].id == entry1.id


def test_append_multiple_messages() -> None:
    """测试追加多条消息形成链"""
    manager = SessionManager.in_memory("/test/project")

    msg1 = MockMessage("user", "First")
    entry1 = manager.append_message(msg1)

    msg2 = MockMessage("assistant", "Response")
    entry2 = manager.append_message(msg2)

    assert entry2.parent_id == entry1.id

    branch = manager.get_branch()
    assert len(branch) == 2


def test_append_thinking_level_change() -> None:
    """测试追加思考级别变更"""
    manager = SessionManager.in_memory("/test/project")

    entry = manager.append_thinking_level_change("high")

    assert entry.id is not None
    assert entry.type == "thinking_level_change"
    assert entry.thinking_level == "high"


def test_append_model_change() -> None:
    """测试追加模型变更"""
    manager = SessionManager.in_memory("/test/project")

    entry = manager.append_model_change("anthropic", "claude-3-sonnet")

    assert entry.id is not None
    assert entry.type == "model_change"
    assert entry.provider == "anthropic"
    assert entry.model_id == "claude-3-sonnet"


def test_persist_after_assistant_message() -> None:
    """测试消息持久化到文件（需要 assistant 消息触发）"""
    import json

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SessionManager.create(
            cwd="/test/project",
            session_dir=tmpdir,
        )

        msg1 = MockMessage("user", "Hello")
        manager.append_message(msg1)

        msg2 = MockMessage("assistant", "Hi there")
        manager.append_message(msg2)

        assert manager.session_file is not None
        import os

        assert os.path.exists(manager.session_file)

        with open(manager.session_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 3

        entries_data = [json.loads(line) for line in lines]
        assert entries_data[0]["type"] == "session"
        assert entries_data[1]["type"] == "message"
        assert "message" in entries_data[1]
        assert entries_data[2]["type"] == "message"
        assert "message" in entries_data[2]


def test_reload_session_preserves_messages() -> None:
    """测试重新加载会话后消息是否保留

    验证 _parse_entry 能正确解析所有条目类型。
    使用 dict 模拟实际的消息结构（AgentMessage 是 Pydantic 模型会正确序列化）。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        manager1 = SessionManager.create(
            cwd="/test/project",
            session_dir=tmpdir,
        )

        msg1 = {"role": "user", "content": "Hello"}
        manager1.append_message(msg1)

        msg2 = {"role": "assistant", "content": "Hi there"}
        manager1.append_message(msg2)

        msg3 = {"role": "user", "content": "How are you?"}
        manager1.append_message(msg3)

        session_file = manager1.session_file
        assert session_file is not None

        manager2 = SessionManager.open(session_file)

        entries = manager2.get_entries()
        assert len(entries) == 3

        assert entries[0].type == "message"
        assert entries[1].type == "message"
        assert entries[2].type == "message"

        branch = manager2.get_branch()
        assert len(branch) == 3

        reloaded_msg1 = branch[0].message
        reloaded_msg2 = branch[1].message
        reloaded_msg3 = branch[2].message

        assert reloaded_msg1["role"] == "user"
        assert reloaded_msg1["content"] == "Hello"
        assert reloaded_msg2["role"] == "assistant"
        assert reloaded_msg2["content"] == "Hi there"
        assert reloaded_msg3["role"] == "user"
        assert reloaded_msg3["content"] == "How are you?"
