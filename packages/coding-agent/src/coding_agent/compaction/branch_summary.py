"""分支摘要 - 对齐 pi-mono TypeScript 实现

树导航的分支摘要。当导航到会话树的不同点时，
生成离开分支的摘要，以免丢失上下文。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from coding_agent.compaction.utils import (
    FileOperations,
    compute_file_lists,
    create_file_ops,
    extract_file_ops_from_message,
)
from coding_agent.session.types import SessionEntry


# ============================================================================
# 类型定义
# ============================================================================


@dataclass
class BranchSummaryResult:
    """分支摘要结果"""

    summary: str | None = None
    read_files: list[str] | None = None
    modified_files: list[str] | None = None
    aborted: bool = False
    error: str | None = None


@dataclass
class BranchSummaryDetails:
    """分支摘要详情"""

    read_files: list[str]
    modified_files: list[str]


@dataclass
class BranchPreparation:
    """分支准备结果"""

    messages: list[Any]
    """用于摘要的消息列表"""

    file_ops: FileOperations
    """文件操作"""

    total_tokens: int
    """消息中的总估算 token 数"""


@dataclass
class CollectEntriesResult:
    """收集条目结果"""

    entries: list[SessionEntry]
    """要摘要的条目（按时间顺序）"""

    common_ancestor_id: str | None
    """新旧位置的共同祖先，如果有的话"""


# ============================================================================
# 条目收集
# ============================================================================


def collect_entries_for_branch_summary(
    entries: list[SessionEntry],
    entry_map: dict[str, SessionEntry],
    old_leaf_id: str | None,
    target_id: str,
) -> CollectEntriesResult:
    """收集导航时应摘要的条目

    从 old_leaf_id 回溯到与 target_id 的共同祖先，
    沿途收集条目。

    Args:
        entries: 所有会话条目列表
        entry_map: ID 到条目的映射
        old_leaf_id: 当前位置（从哪里导航）
        target_id: 目标位置（导航到哪里）

    Returns:
        要摘要的条目和共同祖先
    """
    # 如果没有旧位置，没有什么可摘要的
    if not old_leaf_id:
        return CollectEntriesResult(entries=[], common_ancestor_id=None)

    # 找到共同祖先
    def get_branch(entry_id: str) -> list[str]:
        """获取从根到指定 ID 的路径"""
        path: list[str] = []
        current_id: str | None = entry_id
        while current_id:
            path.insert(0, current_id)
            entry = entry_map.get(current_id)
            current_id = entry.parent_id if entry else None
        return path

    old_path = set(get_branch(old_leaf_id))
    target_path = get_branch(target_id)

    # target_path 是根优先，所以从后向前迭代找最深的共同祖先
    common_ancestor_id: str | None = None
    for entry_id in reversed(target_path):
        if entry_id in old_path:
            common_ancestor_id = entry_id
            break

    # 从旧叶子回溯到共同祖先收集条目
    result_entries: list[SessionEntry] = []
    current: str | None = old_leaf_id

    while current and current != common_ancestor_id:
        entry = entry_map.get(current)
        if not entry:
            break
        result_entries.append(entry)
        current = entry.parent_id

    # 反转以获得时间顺序
    result_entries.reverse()

    return CollectEntriesResult(
        entries=result_entries,
        common_ancestor_id=common_ancestor_id,
    )


# ============================================================================
# 准备分支摘要
# ============================================================================


def prepare_branch_summary(
    entries: list[SessionEntry],
) -> BranchPreparation:
    """准备分支摘要

    提取消息和文件操作用于摘要。

    Args:
        entries: 会话条目列表

    Returns:
        分支准备结果
    """
    from coding_agent.compaction.compaction import estimate_tokens

    messages: list[Any] = []
    file_ops = create_file_ops()
    total_tokens = 0

    for entry in entries:
        if entry.type == "message":
            msg = getattr(entry, "message", None)
            if msg:
                # 跳过工具结果 - 上下文在助手的工具调用中
                role = getattr(msg, "role", None)
                if role != "toolResult":
                    messages.append(msg)
                    # 提取文件操作
                    extract_file_ops_from_message(msg, file_ops)
                    # 估算 token
                    content = getattr(msg, "content", None)
                    if isinstance(content, str):
                        total_tokens += estimate_tokens(content)
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and "text" in block:
                                total_tokens += estimate_tokens(block["text"])

    return BranchPreparation(
        messages=messages,
        file_ops=file_ops,
        total_tokens=total_tokens,
    )


# ============================================================================
# 生成分支摘要
# ============================================================================


def generate_branch_summary(
    entries: list[SessionEntry],
    from_id: str,
    generate_summary_fn: Any | None = None,
) -> BranchSummaryResult:
    """生成分支摘要

    Args:
        entries: 会话条目列表
        from_id: 分支起始 ID
        generate_summary_fn: 生成摘要的函数（可选）

    Returns:
        分支摘要结果
    """
    # 准备分支摘要
    prep = prepare_branch_summary(entries)

    if not prep.messages:
        return BranchSummaryResult(
            summary="No conversation to summarize.",
            read_files=[],
            modified_files=[],
        )

    # 生成摘要
    summary = "Branch summary placeholder"
    if generate_summary_fn:
        try:
            summary = generate_summary_fn(prep.messages)
        except Exception as e:
            return BranchSummaryResult(
                error=str(e),
            )

    # 计算文件列表
    read_files, modified_files = compute_file_lists(prep.file_ops)

    return BranchSummaryResult(
        summary=summary,
        read_files=read_files,
        modified_files=modified_files,
    )


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 类型
    "BranchSummaryResult",
    "BranchSummaryDetails",
    "BranchPreparation",
    "CollectEntriesResult",
    # 函数
    "collect_entries_for_branch_summary",
    "prepare_branch_summary",
    "generate_branch_summary",
]
