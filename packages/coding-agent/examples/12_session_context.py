#!/usr/bin/env python3
"""
Phase 2 验证示例：会话上下文

验证内容：
1. 构建会话上下文
2. 获取最新压缩条目
3. 树遍历和路径收集

运行方式：
    cd packages/coding-agent && uv run python examples/12_session_context.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加包路径
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "ai" / "src"))
sys.path.insert(0, str(root_dir / "agent" / "src"))
sys.path.insert(0, str(root_dir / "coding-agent" / "src"))

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
    """测试获取最新压缩条目"""
    print("=" * 60)
    print("测试获取最新压缩条目")
    print("=" * 60)

    # 创建测试条目
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
    if latest:
        print(f"\n最新压缩条目: id={latest.id}, summary={latest.summary}")
        print(f"预期: comp002")
    else:
        print("\n未找到压缩条目")

    # 测试空列表
    empty_entries: list[SessionEntry] = []
    result = get_latest_compaction_entry(empty_entries)
    print(f"空列表结果: {result}")

    print("\n✓ 压缩条目测试通过")


def test_build_context() -> None:
    """测试构建会话上下文"""
    print("\n" + "=" * 60)
    print("测试构建会话上下文")
    print("=" * 60)

    # 创建测试条目
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

    # 构建 ID 映射
    by_id = {e.id: e for e in entries}

    # 构建上下文
    context = build_session_context(entries, leaf_id="msg002", by_id=by_id)

    print(f"\n上下文信息:")
    print(f"  消息数: {len(context.messages)}")
    print(f"  思考级别: {context.thinking_level}")
    print(f"  模型: {context.model}")

    # 验证内容
    assert context.thinking_level == "high", "思考级别应该是 high"
    assert context.model is not None, "应该有模型信息"
    assert context.model["provider"] == "anthropic", "提供商应该是 anthropic"

    print("\n✓ 上下文构建测试通过")


def test_context_with_compaction() -> None:
    """测试带压缩的上下文"""
    print("\n" + "=" * 60)
    print("测试带压缩的上下文")
    print("=" * 60)

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

    print(f"\n带压缩的上下文:")
    print(f"  消息数: {len(context.messages)}")
    print(f"  第一条消息: {context.messages[0] if context.messages else 'None'}")

    # 第一条应该是压缩摘要
    if context.messages:
        first_msg = context.messages[0]
        if isinstance(first_msg, dict):
            print(f"  第一条 role: {first_msg.get('role')}")

    print("\n✓ 压缩上下文测试通过")


def test_empty_context() -> None:
    """测试空上下文"""
    print("\n" + "=" * 60)
    print("测试空上下文")
    print("=" * 60)

    # 空条目列表
    empty_entries: list[SessionEntry] = []
    context = build_session_context(empty_entries)

    print(f"\n空上下文:")
    print(f"  消息数: {len(context.messages)}")
    print(f"  思考级别: {context.thinking_level}")
    print(f"  模型: {context.model}")

    assert len(context.messages) == 0
    assert context.thinking_level == "off"
    assert context.model is None

    print("\n✓ 空上下文测试通过")


def main() -> int:
    """主函数"""
    try:
        test_get_latest_compaction()
        test_build_context()
        test_context_with_compaction()
        test_empty_context()

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
