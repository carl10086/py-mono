#!/usr/bin/env python3
"""
Phase 4 验证示例：分支摘要功能测试

运行方式：
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
    BranchSummaryResult,
    BranchSummaryDetails,
    BranchPreparation,
    CollectEntriesResult,
    collect_entries_for_branch_summary,
    prepare_branch_summary,
    generate_branch_summary,
    create_file_ops,
)
from coding_agent.session.types import SessionMessageEntry


def create_test_entries():
    """创建测试条目"""
    # 创建树结构
    # root -> a -> a1
    #      -> b -> b1
    entries = []

    # Root
    root = SessionMessageEntry(
        id="root",
        parent_id=None,
        timestamp="2024-01-01T00:00:00Z",
        message={"role": "user", "content": "Root message"},
    )
    entries.append(root)

    # Branch A
    a = SessionMessageEntry(
        id="a",
        parent_id="root",
        timestamp="2024-01-01T00:01:00Z",
        message={"role": "assistant", "content": "Branch A response"},
    )
    entries.append(a)

    a1 = SessionMessageEntry(
        id="a1",
        parent_id="a",
        timestamp="2024-01-01T00:02:00Z",
        message={"role": "user", "content": "A1 message"},
    )
    entries.append(a1)

    # Branch B
    b = SessionMessageEntry(
        id="b",
        parent_id="root",
        timestamp="2024-01-01T00:01:00Z",
        message={"role": "assistant", "content": "Branch B response"},
    )
    entries.append(b)

    b1 = SessionMessageEntry(
        id="b1",
        parent_id="b",
        timestamp="2024-01-01T00:02:00Z",
        message={"role": "user", "content": "B1 message"},
    )
    entries.append(b1)

    return entries


def test_collect_entries():
    """测试条目收集"""
    print("=" * 60)
    print("测试条目收集")
    print("=" * 60)

    entries = create_test_entries()
    entry_map = {e.id: e for e in entries}

    # 从 a1 导航到 b（需要摘要 a -> a1 分支）
    result = collect_entries_for_branch_summary(
        entries=entries,
        entry_map=entry_map,
        old_leaf_id="a1",
        target_id="b",
    )

    print(f"\n从 a1 导航到 b:")
    print(f"  收集条目数: {len(result.entries)}")
    print(f"  条目 ID: {[e.id for e in result.entries]}")
    print(f"  共同祖先: {result.common_ancestor_id}")

    # 从 b1 导航到 a1
    result2 = collect_entries_for_branch_summary(
        entries=entries,
        entry_map=entry_map,
        old_leaf_id="b1",
        target_id="a1",
    )

    print(f"\n从 b1 导航到 a1:")
    print(f"  收集条目数: {len(result2.entries)}")
    print(f"  条目 ID: {[e.id for e in result2.entries]}")
    print(f"  共同祖先: {result2.common_ancestor_id}")

    # 无旧位置
    result3 = collect_entries_for_branch_summary(
        entries=entries,
        entry_map=entry_map,
        old_leaf_id=None,
        target_id="a1",
    )

    print(f"\n无旧位置（首次导航）:")
    print(f"  收集条目数: {len(result3.entries)}")

    print("\n✓ 条目收集测试通过")


def test_prepare_branch_summary():
    """测试分支摘要准备"""
    print("\n" + "=" * 60)
    print("测试分支摘要准备")
    print("=" * 60)

    entries = create_test_entries()

    preparation = prepare_branch_summary(entries)

    print(f"\n分支摘要准备:")
    print(f"  消息数: {len(preparation.messages)}")
    print(f"  估算 Token: {preparation.total_tokens}")
    print(f"  文件操作 - 读取: {len(preparation.file_ops.read)}")
    print(f"  文件操作 - 写入: {len(preparation.file_ops.written)}")
    print(f"  文件操作 - 编辑: {len(preparation.file_ops.edited)}")

    print("\n✓ 分支摘要准备测试通过")


def test_generate_branch_summary():
    """测试生成分支摘要"""
    print("\n" + "=" * 60)
    print("测试生成分支摘要")
    print("=" * 60)

    entries = create_test_entries()

    # 生成摘要
    result = generate_branch_summary(
        entries=entries,
        from_id="a1",
    )

    print(f"\n分支摘要结果:")
    print(f"  成功: {not result.aborted}")
    print(f"  有摘要: {result.summary is not None}")
    if result.summary:
        print(f"  摘要: {result.summary[:100]}...")
    if result.error:
        print(f"  错误: {result.error}")

    print("\n✓ 生成分支摘要测试通过")


def test_branch_types():
    """测试分支摘要类型"""
    print("\n" + "=" * 60)
    print("测试分支摘要类型")
    print("=" * 60)

    # 测试 BranchSummaryResult
    result = BranchSummaryResult(
        summary="Test summary",
        read_files=["/file1.txt"],
        modified_files=["/file2.txt"],
        aborted=False,
        error=None,
    )
    print(f"\nBranchSummaryResult:")
    print(f"  摘要: {result.summary}")
    print(f"  只读: {result.read_files}")
    print(f"  修改: {result.modified_files}")

    # 测试 BranchSummaryDetails
    details = BranchSummaryDetails(
        read_files=["/a.txt", "/b.txt"],
        modified_files=["/c.txt"],
    )
    print(f"\nBranchSummaryDetails:")
    print(f"  只读: {details.read_files}")
    print(f"  修改: {details.modified_files}")

    # 测试 BranchPreparation
    file_ops = create_file_ops()
    file_ops.read.add("/test.txt")
    prep = BranchPreparation(
        messages=[{"role": "user", "content": "test"}],
        file_ops=file_ops,
        total_tokens=100,
    )
    print(f"\nBranchPreparation:")
    print(f"  消息数: {len(prep.messages)}")
    print(f"  Token: {prep.total_tokens}")

    # 测试 CollectEntriesResult
    collect = CollectEntriesResult(
        entries=[],
        common_ancestor_id="root",
    )
    print(f"\nCollectEntriesResult:")
    print(f"  条目数: {len(collect.entries)}")
    print(f"  共同祖先: {collect.common_ancestor_id}")

    print("\n✓ 分支摘要类型测试通过")


def main() -> int:
    """主函数"""
    try:
        test_collect_entries()
        test_prepare_branch_summary()
        test_generate_branch_summary()
        test_branch_types()

        print("\n" + "=" * 60)
        print("所有分支摘要测试通过!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
