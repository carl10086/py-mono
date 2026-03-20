#!/usr/bin/env python3
"""
Phase 4 验证示例：压缩功能完整集成测试

运行方式：
    cd packages/coding-agent && uv run python examples/23_compaction_full.py
"""

from __future__ import annotations

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "ai" / "src"))
sys.path.insert(0, str(root_dir / "agent" / "src"))
sys.path.insert(0, str(root_dir / "coding-agent" / "src"))

from coding_agent.compaction import (
    # 压缩功能
    CompactionSettings,
    CompactionResult,
    compact,
    should_compact,
    estimate_tokens,
    estimate_context_tokens,
    prepare_compaction,
    calculate_context_tokens,
    # 分支摘要功能
    BranchSummaryResult,
    collect_entries_for_branch_summary,
    generate_branch_summary,
    prepare_branch_summary,
    # 工具函数
    FileOperations,
    create_file_ops,
    extract_file_ops_from_message,
    compute_file_lists,
    format_file_operations,
    serialize_conversation,
    TOOL_RESULT_MAX_CHARS,
    SUMMARIZATION_SYSTEM_PROMPT,
)
from coding_agent.session.types import SessionMessageEntry


def test_full_compaction_workflow():
    """测试完整压缩工作流"""
    print("=" * 60)
    print("测试完整压缩工作流")
    print("=" * 60)

    # 创建大量消息模拟长会话
    entries = []
    for i in range(50):
        role = "user" if i % 2 == 0 else "assistant"
        content = f"Message {i}: " + "This is some content that adds up. " * 20
        msg = {"role": role, "content": content}
        entry = SessionMessageEntry(
            id=f"msg{i:03d}",
            parent_id=None if i == 0 else f"msg{i - 1:03d}",
            timestamp="2024-01-01T00:00:00Z",
            message=msg,
        )
        entries.append(entry)

    settings = CompactionSettings(enabled=True, keep_recent_tokens=2000)

    # 1. 估算 token
    estimated = estimate_context_tokens(entries)
    print(f"\n1. Token 估算:")
    print(f"   总条目: {len(entries)}")
    print(f"   估算 Token: {estimated}")

    # 2. 检查是否需要压缩
    needs = should_compact(entries, settings, threshold_tokens=5000)
    print(f"\n2. 压缩判断:")
    print(f"   阈值: 5000")
    print(f"   需要压缩: {needs}")

    # 3. 准备压缩
    prep = prepare_compaction(entries, settings)
    print(f"\n3. 压缩准备:")
    print(f"   消息数: {len(prep.messages)}")
    print(f"   首个保留条目 ID: {prep.first_kept_entry_id}")
    print(f"   压缩前 Token: {prep.tokens_before}")

    # 4. 执行压缩
    result = compact(entries, settings)
    print(f"\n4. 压缩结果:")
    if result:
        print(f"   成功: True")
        print(f"   摘要: {result.summary[:60]}...")
        print(f"   保留起始: {result.first_kept_entry_id}")
        print(f"   压缩前 Token: {result.tokens_before}")
    else:
        print(f"   结果: None（未执行或不需要）")

    print("\n✓ 完整压缩工作流测试通过")


def test_file_operations_integration():
    """测试文件操作集成"""
    print("\n" + "=" * 60)
    print("测试文件操作集成")
    print("=" * 60)

    file_ops = create_file_ops()

    # 模拟文件操作
    files_read = ["/src/main.py", "/src/utils.py", "/README.md"]
    files_written = ["/src/main.py"]
    files_edited = ["/src/utils.py"]

    for f in files_read:
        file_ops.read.add(f)
    for f in files_written:
        file_ops.written.add(f)
    for f in files_edited:
        file_ops.edited.add(f)

    print(f"\n文件操作统计:")
    print(f"  读取: {len(file_ops.read)} 个")
    print(f"  写入: {len(file_ops.written)} 个")
    print(f"  编辑: {len(file_ops.edited)} 个")

    # 计算文件列表
    read_files, modified_files = compute_file_lists(file_ops)
    print(f"\n计算结果:")
    print(f"  只读文件: {read_files}")
    print(f"  修改文件: {modified_files}")

    # 格式化输出
    formatted = format_file_operations(read_files, modified_files)
    print(f"\n格式化输出:")
    print(formatted[:200])

    print("\n✓ 文件操作集成测试通过")


def test_branch_summary_integration():
    """测试分支摘要集成"""
    print("\n" + "=" * 60)
    print("测试分支摘要集成")
    print("=" * 60)

    # 创建复杂树结构
    entries = []

    # 主干
    for i in range(5):
        entry = SessionMessageEntry(
            id=f"main{i}",
            parent_id=None if i == 0 else f"main{i - 1}",
            timestamp=f"2024-01-01T00:0{i}:00Z",
            message={"role": "user" if i % 2 == 0 else "assistant", "content": f"Main {i}"},
        )
        entries.append(entry)

    # 分支 A
    for i in range(3):
        entry = SessionMessageEntry(
            id=f"branch_a{i}",
            parent_id="main4" if i == 0 else f"branch_a{i - 1}",
            timestamp=f"2024-01-01T00:1{i}:00Z",
            message={"role": "user" if i % 2 == 0 else "assistant", "content": f"Branch A {i}"},
        )
        entries.append(entry)

    # 分支 B
    for i in range(3):
        entry = SessionMessageEntry(
            id=f"branch_b{i}",
            parent_id="main4" if i == 0 else f"branch_b{i - 1}",
            timestamp=f"2024-01-01T00:2{i}:00Z",
            message={"role": "user" if i % 2 == 0 else "assistant", "content": f"Branch B {i}"},
        )
        entries.append(entry)

    entry_map = {e.id: e for e in entries}

    # 从分支 A 导航到分支 B
    print(f"\n从 branch_a2 导航到 branch_b2:")

    collect_result = collect_entries_for_branch_summary(
        entries=entries,
        entry_map=entry_map,
        old_leaf_id="branch_a2",
        target_id="branch_b2",
    )
    print(f"  收集条目: {len(collect_result.entries)}")
    print(f"  共同祖先: {collect_result.common_ancestor_id}")

    prep = prepare_branch_summary(entries)
    print(f"  准备消息: {len(prep.messages)}")
    print(f"  估算 Token: {prep.total_tokens}")

    # 使用 from_id 参数
    summary_result = generate_branch_summary(
        entries=collect_result.entries,
        from_id="branch_a2",
    )
    print(f"  摘要生成: {'成功' if not summary_result.aborted else '中止'}")

    print("\n✓ 分支摘要集成测试通过")


def test_constants():
    """测试常量"""
    print("\n" + "=" * 60)
    print("测试常量")
    print("=" * 60)

    print(f"\n常量值:")
    print(f"  TOOL_RESULT_MAX_CHARS: {TOOL_RESULT_MAX_CHARS}")
    print(f"  SUMMARIZATION_SYSTEM_PROMPT 长度: {len(SUMMARIZATION_SYSTEM_PROMPT)}")
    print(f"  系统提示预览: {SUMMARIZATION_SYSTEM_PROMPT[:100]}...")

    print("\n✓ 常量测试通过")


def main() -> int:
    """主函数"""
    try:
        test_full_compaction_workflow()
        test_file_operations_integration()
        test_branch_summary_integration()
        test_constants()

        print("\n" + "=" * 60)
        print("所有 Phase 4 集成测试通过!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
