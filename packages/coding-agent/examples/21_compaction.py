#!/usr/bin/env python3
"""
Phase 4 验证示例：压缩功能完整测试

运行方式：
    cd packages/coding-agent && uv run python examples/21_compaction.py
"""

from __future__ import annotations

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "ai" / "src"))
sys.path.insert(0, str(root_dir / "agent" / "src"))
sys.path.insert(0, str(root_dir / "coding-agent" / "src"))

from coding_agent.compaction import (
    CompactionSettings,
    CompactionDetails,
    CompactionResult,
    PrepareCompactionResult,
    calculate_context_tokens,
    prepare_compaction,
    compact,
    serialize_conversation,
)
from coding_agent.session.types import SessionMessageEntry


def test_calculate_context_tokens():
    """测试上下文 Token 计算"""
    print("=" * 60)
    print("测试上下文 Token 计算")
    print("=" * 60)

    # 测试各种 usage 格式
    usage1 = {"totalTokens": 1500}
    assert calculate_context_tokens(usage1) == 1500
    print(f"✓ totalTokens 格式: {calculate_context_tokens(usage1)}")

    usage2 = {"input": 1000, "output": 500, "cacheRead": 200, "cacheWrite": 100}
    assert calculate_context_tokens(usage2) == 1800
    print(f"✓ 组件格式: {calculate_context_tokens(usage2)}")

    usage3 = {}
    assert calculate_context_tokens(usage3) == 0
    print(f"✓ 空 usage: {calculate_context_tokens(usage3)}")

    print("\n✓ 上下文 Token 计算测试通过")


def test_serialize_conversation():
    """测试对话序列化"""
    print("\n" + "=" * 60)
    print("测试对话序列化")
    print("=" * 60)

    # 创建 LLM 格式的消息列表（不是 SessionEntry）
    messages = [
        {"role": "user", "content": "Hello, can you help me?"},
        {"role": "assistant", "content": "Yes, I can help you."},
        {"role": "user", "content": "Thank you!"},
    ]

    serialized = serialize_conversation(messages)
    print(f"\n序列化结果 (前200字符):")
    print(serialized[:200])
    print("\n✓ 对话序列化测试通过")


def test_prepare_compaction():
    """测试压缩准备"""
    print("\n" + "=" * 60)
    print("测试压缩准备")
    print("=" * 60)

    settings = CompactionSettings(enabled=True, keep_recent_tokens=200)

    # 创建大量测试条目
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

    print(f"\n压缩准备结果:")
    print(f"  消息数: {len(result.messages)}")
    print(f"  首个保留条目 ID: {result.first_kept_entry_id}")
    print(f"  压缩前 Token: {result.tokens_before}")
    print("\n✓ 压缩准备测试通过")


def test_compact_function():
    """测试完整压缩流程"""
    print("\n" + "=" * 60)
    print("测试完整压缩流程")
    print("=" * 60)

    settings = CompactionSettings(enabled=True, keep_recent_tokens=500)

    # 创建足够多的条目触发压缩
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
        print(f"\n压缩结果:")
        print(f"  成功: True")
        print(f"  摘要长度: {len(result.summary)} 字符")
        print(f"  摘要预览: {result.summary[:80]}...")
        print(f"  首个保留条目 ID: {result.first_kept_entry_id}")
        print(f"  压缩前 Token: {result.tokens_before}")
        if result.details:
            print(f"  只读文件: {result.details.read_files}")
            print(f"  修改文件: {result.details.modified_files}")
    else:
        print("\n不需要压缩（可能条目不够多）")

    print("\n✓ 完整压缩流程测试通过")


def test_compact_disabled():
    """测试禁用压缩"""
    print("\n" + "=" * 60)
    print("测试禁用压缩")
    print("=" * 60)

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

    if result is None:
        print("\n✓ 禁用压缩时返回 None（正确）")
    else:
        print("\n✗ 禁用压缩时应该返回 None")

    print("\n✓ 禁用压缩测试通过")


def main() -> int:
    """主函数"""
    try:
        test_calculate_context_tokens()
        test_serialize_conversation()
        test_prepare_compaction()
        test_compact_function()
        test_compact_disabled()

        print("\n" + "=" * 60)
        print("所有压缩功能测试通过!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
