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


def test_build_session_context() -> None:
    """测试 build_session_context 构建 LLM 上下文"""
    manager = SessionManager.in_memory("/test/project")

    msg1 = {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
    manager.append_message(msg1)

    msg2 = {"role": "assistant", "content": [{"type": "text", "text": "Hi there"}]}
    manager.append_message(msg2)

    manager.append_thinking_level_change("high")

    msg3 = {"role": "user", "content": [{"type": "text", "text": "How are you?"}]}
    manager.append_message(msg3)

    context = manager.build_session_context()

    assert len(context.messages) == 3
    assert context.thinking_level == "high"
    assert context.model is None


def test_build_session_context_empty() -> None:
    """测试 build_session_context 空会话"""
    manager = SessionManager.in_memory("/test/project")

    context = manager.build_session_context()

    assert len(context.messages) == 0
    assert context.thinking_level == "off"
    assert context.model is None


def test_append_compaction() -> None:
    """测试追加压缩条目"""
    manager = SessionManager.in_memory("/test/project")

    entry = manager.append_compaction(
        summary="Previous conversation was about setting up a project.",
        first_kept_entry_id="abc123",
        tokens_before=5000,
        details={"reason": "context_limit"},
    )

    assert entry.id is not None
    assert entry.type == "compaction"
    assert entry.summary == "Previous conversation was about setting up a project."
    assert entry.first_kept_entry_id == "abc123"
    assert entry.tokens_before == 5000
    assert entry.details == {"reason": "context_limit"}


def test_append_branch_summary() -> None:
    """测试追加分支摘要条目"""
    manager = SessionManager.in_memory("/test/project")

    entry = manager.append_branch_summary(
        from_id="branch-point-123",
        summary="Earlier we discussed Python best practices.",
    )

    assert entry.id is not None
    assert entry.type == "branch_summary"
    assert entry.from_id == "branch-point-123"
    assert entry.summary == "Earlier we discussed Python best practices."


def test_append_custom_entry() -> None:
    """测试追加自定义条目"""
    manager = SessionManager.in_memory("/test/project")

    entry = manager.append_custom_entry(
        custom_type="my_extension",
        data={"key": "value"},
    )

    assert entry.id is not None
    assert entry.type == "custom"
    assert entry.custom_type == "my_extension"
    assert entry.data == {"key": "value"}


def test_append_custom_message() -> None:
    """测试追加自定义消息条目"""
    manager = SessionManager.in_memory("/test/project")

    entry = manager.append_custom_message(
        custom_type="notification",
        content="Build completed successfully",
        display=True,
    )

    assert entry.id is not None
    assert entry.type == "custom_message"
    assert entry.custom_type == "notification"
    assert entry.content == "Build completed successfully"
    assert entry.display is True


def test_append_session_info() -> None:
    """测试追加会话信息条目"""
    manager = SessionManager.in_memory("/test/project")

    entry = manager.append_session_info(name="My Session")

    assert entry.id is not None
    assert entry.type == "session_info"
    assert entry.name == "My Session"

    name = manager.get_session_name()
    assert name == "My Session"


def test_append_label_change() -> None:
    """测试追加标签变更条目"""
    manager = SessionManager.in_memory("/test/project")

    msg = {"role": "user", "content": "Hello"}
    msg_entry = manager.append_message(msg)

    label_entry = manager.append_label_change(target_id=msg_entry.id, label="important")

    assert label_entry.id is not None
    assert label_entry.type == "label"
    assert label_entry.target_id == msg_entry.id
    assert label_entry.label == "important"


def test_branch_and_reset_leaf() -> None:
    """测试分支导航和重置叶子"""
    manager = SessionManager.in_memory("/test/project")

    msg1 = manager.append_message({"role": "user", "content": "Message 1"})
    msg2 = manager.append_message({"role": "assistant", "content": "Response 2"})
    msg3 = manager.append_message({"role": "user", "content": "Message 3"})

    assert manager.get_leaf_entry().id == msg3.id

    manager.branch(msg1.id)
    assert manager.get_leaf_entry().id == msg1.id

    msg4 = manager.append_message({"role": "user", "content": "Branch message"})
    assert msg4.parent_id == msg1.id

    manager.reset_leaf()
    assert manager.get_leaf_entry() is None

    msg5 = manager.append_message({"role": "user", "content": "After reset"})
    assert msg5.parent_id is None


def test_branch_with_summary() -> None:
    """测试分支并生成摘要"""
    manager = SessionManager.in_memory("/test/project")

    msg1 = manager.append_message({"role": "user", "content": "Original message"})
    manager.append_message({"role": "assistant", "content": "Original response"})

    summary_entry = manager.branch_with_summary(
        branch_from_id=msg1.id,
        summary="We discussed the initial topic.",
    )

    assert summary_entry.type == "branch_summary"
    assert summary_entry.from_id == msg1.id
    assert summary_entry.summary == "We discussed the initial topic."


def test_get_tree() -> None:
    """测试获取会话树结构"""
    manager = SessionManager.in_memory("/test/project")

    msg1 = manager.append_message({"role": "user", "content": "Message 1"})
    manager.append_message({"role": "assistant", "content": "Response 1"})

    manager.branch(msg1.id)
    manager.append_message({"role": "user", "content": "Branch message"})

    tree = manager.get_tree()
    assert len(tree) >= 1

    root = tree[0]
    assert root.entry.type == "message"
    assert len(root.children) >= 1


def test_get_children() -> None:
    """测试获取直接子节点"""
    manager = SessionManager.in_memory("/test/project")

    msg1 = manager.append_message({"role": "user", "content": "Message 1"})
    child1 = manager.append_message({"role": "assistant", "content": "Child 1"})
    manager.append_message({"role": "user", "content": "Child 2"})

    children = manager.get_children(msg1.id)
    assert len(children) == 1
    assert children[0].id == child1.id


def test_get_leaf_entry() -> None:
    """测试获取叶子条目"""
    manager = SessionManager.in_memory("/test/project")

    assert manager.get_leaf_entry() is None

    msg1 = manager.append_message({"role": "user", "content": "Hello"})
    assert manager.get_leaf_entry().id == msg1.id

    msg2 = manager.append_message({"role": "assistant", "content": "Hi"})
    assert manager.get_leaf_entry().id == msg2.id


def test_fork_from() -> None:
    """测试从源会话分叉"""
    with tempfile.TemporaryDirectory() as tmpdir:
        source_manager = SessionManager.create("/source/project", tmpdir)
        source_manager.append_message({"role": "user", "content": "Hello from source"})
        source_manager.append_message({"role": "assistant", "content": "Hi there!"})
        source_file = source_manager.session_file
        assert source_file is not None

        forked_manager = SessionManager.fork_from(source_file, "/target/project")

        assert forked_manager.cwd == "/target/project"
        assert len(forked_manager._file_entries) >= 2

        entries = forked_manager.get_entries()
        assert len(entries) == 2


def test_list_sessions() -> None:
    """测试列出指定目录的会话"""
    import asyncio

    async def run_test():
        with tempfile.TemporaryDirectory() as tmpdir:
            manager1 = SessionManager.create("/test/project", tmpdir)
            manager1.append_message({"role": "user", "content": "Session 1"})
            manager1.append_message({"role": "assistant", "content": "Response 1"})

            manager2 = SessionManager.create("/test/project", tmpdir)
            manager2.append_message({"role": "user", "content": "Session 2"})
            manager2.append_message({"role": "assistant", "content": "Response 2"})

            sessions = await SessionManager.list("/test/project", session_dir=tmpdir)
            assert len(sessions) == 2

    asyncio.run(run_test())


def test_list_all_sessions() -> None:
    """测试列出所有会话"""
    import asyncio

    async def run_test():
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager.create("/test/project", tmpdir)
            manager.append_message({"role": "user", "content": "Hello"})
            manager.append_message({"role": "assistant", "content": "Hi"})

            sessions = await SessionManager.list_all()
            assert len(sessions) >= 1

    asyncio.run(run_test())


def test_switch_session() -> None:
    """测试 AgentSession.switch_session - Agent 状态恢复"""
    import asyncio

    async def run_test():
        from coding_agent.agent_session import AgentSession, AgentSessionConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionManager.create("/test/project", tmpdir)
            sm.append_message({"role": "user", "content": "Hello"})
            sm.append_message({"role": "assistant", "content": "Hi there!"})
            session_file = sm.session_file

            config = AgentSessionConfig(cwd="/test/project", session_manager=sm)
            session = AgentSession(config)

            assert len(session.build_context()) == 2

            await session.switch_session(session_file)

            assert len(session.build_context()) == 2
            assert len(session.agent.state.messages) == 2

    asyncio.run(run_test())
