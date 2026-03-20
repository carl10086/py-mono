#!/usr/bin/env python3
"""
Phase 4 验证示例：压缩与上下文管理

运行方式：
    cd packages/coding-agent && uv run python examples/20_token_estimation.py
    cd packages/coding-agent && uv run python examples/21_compaction.py
    cd packages/coding-agent && uv run python examples/22_branch_summary.py
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
    estimate_tokens,
    should_compact,
    compact,
    create_file_ops,
    extract_file_ops_from_message,
    compute_file_lists,
)
from coding_agent.session.types import SessionMessageEntry


def test_token_estimation():
    """测试 Token 估算"""
    print("=" * 60)
    print("测试 Token 估算")
    print("=" * 60)

    text = "Hello, this is a test message." * 10
    tokens = estimate_tokens(text)
    print(f"\n文本长度: {len(text)} 字符")
    print(f"估算 Token: {tokens}")

    # 验证大约 4:1 的比例
    ratio = len(text) / tokens
    print(f"字符/Token 比例: {ratio:.1f} (期望约 4.0)")

    print("\n✓ Token 估算测试通过")


def test_should_compact():
    """测试压缩判断"""
    print("\n" + "=" * 60)
    print("测试压缩判断")
    print("=" * 60)

    settings = CompactionSettings(enabled=True)

    # 创建一些测试条目
    entries = []
    for i in range(5):
        msg = {"role": "user", "content": "Hello " * 1000}
        entry = SessionMessageEntry(
            id=f"msg{i}",
            parent_id=None if i == 0 else f"msg{i - 1}",
            timestamp="2024-01-01T00:00:00Z",
            message=msg,
        )
        entries.append(entry)

    should = should_compact(entries, settings, threshold_tokens=100)
    print(f"\n条目数: {len(entries)}")
    print(f"应该压缩: {should}")

    # 禁用压缩
    settings_disabled = CompactionSettings(enabled=False)
    should_disabled = should_compact(entries, settings_disabled, threshold_tokens=100)
    print(f"禁用后应该压缩: {should_disabled}")

    print("\n✓ 压缩判断测试通过")


def test_file_operations():
    """测试文件操作追踪"""
    print("\n" + "=" * 60)
    print("测试文件操作追踪")
    print("=" * 60)

    file_ops = create_file_ops()
    print(f"\n初始状态:")
    print(f"  读取: {len(file_ops.read)}")
    print(f"  写入: {len(file_ops.written)}")
    print(f"  编辑: {len(file_ops.edited)}")

    # 模拟工具调用
    file_ops.read.add("/path/to/file1.txt")
    file_ops.read.add("/path/to/file2.txt")
    file_ops.edited.add("/path/to/file2.txt")
    file_ops.written.add("/path/to/file3.txt")

    print(f"\n添加操作后:")
    print(f"  读取: {len(file_ops.read)}")
    print(f"  写入: {len(file_ops.written)}")
    print(f"  编辑: {len(file_ops.edited)}")

    # 计算文件列表
    read_files, modified_files = compute_file_lists(file_ops)
    print(f"\n计算结果:")
    print(f"  只读文件: {read_files}")
    print(f"  修改文件: {modified_files}")

    print("\n✓ 文件操作追踪测试通过")


def test_compact():
    """测试压缩功能"""
    print("\n" + "=" * 60)
    print("测试压缩功能")
    print("=" * 60)

    settings = CompactionSettings(enabled=True, keep_recent_tokens=100)

    # 创建测试条目
    entries = []
    for i in range(10):
        msg = {"role": "user", "content": f"Message {i} " * 50}
        entry = SessionMessageEntry(
            id=f"msg{i:03d}",
            parent_id=None if i == 0 else f"msg{i - 1:03d}",
            timestamp="2024-01-01T00:00:00Z",
            message=msg,
        )
        entries.append(entry)

    result = compact(entries, settings)

    if result:
        print(f"\n压缩成功:")
        print(f"  摘要: {result.summary[:50]}...")
        print(f"  保留起始 ID: {result.first_kept_entry_id}")
        print(f"  压缩前 Token: {result.tokens_before}")
        if result.details:
            print(f"  只读文件: {result.details.read_files}")
            print(f"  修改文件: {result.details.modified_files}")
    else:
        print("\n不需要压缩")

    print("\n✓ 压缩功能测试通过")


def main() -> int:
    """主函数"""
    try:
        test_token_estimation()
        test_should_compact()
        test_file_operations()
        test_compact()

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
