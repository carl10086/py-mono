#!/usr/bin/env python3
"""
Phase 2 验证示例：会话类型和配置

验证内容：
1. 会话条目类型的创建
2. 配置路径函数

运行方式：
    cd packages/coding-agent && uv run python examples/09_session_types.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加所有包路径
root_dir = Path(__file__).parent.parent.parent.parent  # packages/
sys.path.insert(0, str(root_dir / "ai" / "src"))
sys.path.insert(0, str(root_dir / "agent" / "src"))
sys.path.insert(0, str(root_dir / "coding-agent" / "src"))

from coding_agent.config import (
    VERSION,
    get_agent_dir,
    get_default_session_dir,
    get_sessions_dir,
    is_valid_session_file,
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
    """测试配置功能"""
    print("=" * 60)
    print("测试配置模块")
    print("=" * 60)

    print(f"\n版本: {VERSION}")
    print(f"会话版本: {CURRENT_SESSION_VERSION}")

    print("\n目录路径:")
    agent_dir = get_agent_dir()
    print(f"  Agent 目录: {agent_dir}")

    sessions_dir = get_sessions_dir()
    print(f"  会话目录: {sessions_dir}")

    cwd_session_dir = get_default_session_dir("/home/user/myproject")
    print(f"  默认会话目录: {cwd_session_dir}")

    print("\n✓ 配置测试通过")


def test_session_types() -> None:
    """测试会话条目类型"""
    print("\n" + "=" * 60)
    print("测试会话条目类型")
    print("=" * 60)

    # 测试基础类型
    print("\n1. 基础类型")
    base = SessionEntryBase(
        type="test",
        id="abc123",
        parent_id=None,
        timestamp="2024-01-01T00:00:00Z",
    )
    print(f"   SessionEntryBase: id={base.id}, type={base.type}")

    # 测试头部
    print("\n2. 会话头部")
    header = SessionHeader(
        id="session-uuid-123",
        timestamp="2024-01-01T00:00:00Z",
        cwd="/home/user/project",
    )
    print(f"   SessionHeader: id={header.id}, version={header.version}")

    # 测试条目类型
    print("\n3. 各种条目类型")

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
    print(f"   SessionMessageEntry: {get_entry_type_name(msg_entry)}")
    assert is_session_message_entry(msg_entry)

    think_entry = ThinkingLevelChangeEntry(
        id="think001",
        parent_id="msg001",
        timestamp="2024-01-01T00:00:02Z",
        thinking_level="high",
    )
    print(f"   ThinkingLevelChangeEntry: {get_entry_type_name(think_entry)}")

    model_entry = ModelChangeEntry(
        id="model001",
        parent_id="think001",
        timestamp="2024-01-01T00:00:03Z",
        provider="anthropic",
        model_id="claude-3-sonnet",
    )
    print(f"   ModelChangeEntry: {get_entry_type_name(model_entry)}")
    assert is_model_change_entry(model_entry)

    compaction_entry = CompactionEntry(
        id="compact001",
        parent_id="model001",
        timestamp="2024-01-01T00:00:04Z",
        summary="Summary of previous conversation",
        first_kept_entry_id="msg001",
        tokens_before=10000,
    )
    print(f"   CompactionEntry: {get_entry_type_name(compaction_entry)}")
    assert is_compaction_entry(compaction_entry)

    # 测试上下文
    print("\n4. 会话上下文")
    context = SessionContext(
        messages=[],
        thinking_level="medium",
        model={"provider": "anthropic", "modelId": "claude-3"},
    )
    print(f"   SessionContext: thinking_level={context.thinking_level}")

    # 测试会话信息
    print("\n5. 会话信息")
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
    print(f"   SessionInfo: name={info.name}, messages={info.message_count}")

    # 测试树节点
    print("\n6. 树节点")
    tree_node = SessionTreeNode(
        entry=msg_entry,
        children=[],
        label="First message",
    )
    print(f"   SessionTreeNode: label={tree_node.label}, children={len(tree_node.children)}")

    print("\n✓ 会话类型测试通过")


def test_options() -> None:
    """测试选项类型"""
    print("\n" + "=" * 60)
    print("测试选项类型")
    print("=" * 60)

    # 测试新会话选项
    options = NewSessionOptions(
        id="custom-session-id",
        parent_session="/path/to/parent.jsonl",
    )
    print(f"\nNewSessionOptions: id={options.id}, parent={options.parent_session}")

    # 测试默认选项
    default_options = NewSessionOptions()
    print(f"Default NewSessionOptions: id={default_options.id}")

    print("\n✓ 选项类型测试通过")


def main() -> int:
    """主函数"""
    try:
        test_config()
        test_session_types()
        test_options()

        print("\n" + "=" * 60)
        print("所有测试通过!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
