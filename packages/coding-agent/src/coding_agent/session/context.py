"""会话上下文模块 - 构建 LLM 上下文

提供从会话条目构建 LLM 上下文的功能：
- 树遍历收集消息
- 处理压缩和分支摘要
- 支持分支导航
"""

from __future__ import annotations

from typing import Any

from coding_agent.session.types import (
    BranchSummaryEntry,
    CompactionEntry,
    CustomMessageEntry,
    ModelChangeEntry,
    SessionContext,
    SessionEntry,
    SessionMessageEntry,
    ThinkingLevelChangeEntry,
)


def get_latest_compaction_entry(entries: list[SessionEntry]) -> CompactionEntry | None:
    """获取最新的压缩条目

    从后向前扫描条目列表，找到第一个（最新的）压缩条目。

    Args:
        entries: 会话条目列表

    Returns:
        最新的压缩条目，如果没有返回 None

    Example:
        >>> entries = [msg1, msg2, compaction, msg3]
        >>> entry = get_latest_compaction_entry(entries)
        >>> entry == compaction
        True
    """
    for entry in reversed(entries):
        if isinstance(entry, CompactionEntry):
            return entry
    return None


def _extract_message_content(entry: SessionEntry) -> Any | None:
    """从条目提取消息内容

    Args:
        entry: 会话条目

    Returns:
        消息数据或 None
    """
    if isinstance(entry, SessionMessageEntry):
        return entry.message
    elif isinstance(entry, CustomMessageEntry):
        # 构建自定义消息
        return {
            "role": "custom",
            "custom_type": entry.custom_type,
            "content": entry.content,
            "display": entry.display,
            "details": entry.details,
            "timestamp": entry.timestamp,
        }
    elif isinstance(entry, BranchSummaryEntry):
        # 构建分支摘要消息
        return {
            "role": "branch_summary",
            "summary": entry.summary,
            "from_id": entry.from_id,
            "timestamp": entry.timestamp,
        }
    return None


def _get_entry_timestamp(entry: SessionEntry) -> str:
    """获取条目的时间戳"""
    return entry.timestamp


def build_session_context(
    entries: list[SessionEntry],
    leaf_id: str | None = None,
    by_id: dict[str, SessionEntry] | None = None,
) -> SessionContext:
    """构建会话上下文

    从会话条目构建 LLM 上下文，包括：
    - 树遍历从叶子到根收集路径
    - 处理压缩（从 firstKeptEntryId 开始保留）
    - 处理分支摘要
    - 提取思考级别和模型信息

    Args:
        entries: 会话条目列表
        leaf_id: 叶子节点 ID（None 表示使用最后一个条目）
        by_id: ID 到条目的映射（可选，会重新构建）

    Returns:
        SessionContext 包含消息列表、思考级别和模型信息

    Example:
        >>> entries = [...]
        >>> context = build_session_context(entries)
        >>> len(context.messages)
        10
        >>> context.thinking_level
        'medium'
    """
    # 构建 ID 索引
    if by_id is None:
        by_id = {e.id: e for e in entries if hasattr(e, "id")}

    # 确定叶子节点
    if leaf_id is None:
        # 使用最后一个条目
        if entries:
            leaf = entries[-1]
            leaf_id = leaf.id
        else:
            # 空会话
            return SessionContext(messages=[], thinking_level="off", model=None)
    elif leaf_id is None:
        # 显式 null - 返回空上下文
        return SessionContext(messages=[], thinking_level="off", model=None)

    # 查找叶子条目
    leaf = by_id.get(leaf_id)
    if not leaf:
        if entries:
            leaf = entries[-1]
            leaf_id = leaf.id
        else:
            return SessionContext(messages=[], thinking_level="off", model=None)

    # 从叶子遍历到根，收集路径
    path: list[SessionEntry] = []
    current: SessionEntry | None = leaf
    while current:
        path.insert(0, current)
        parent_id = current.parent_id
        current = by_id.get(parent_id) if parent_id else None

    # 提取设置和查找压缩点
    thinking_level = "off"
    model: dict[str, str] | None = None
    compaction: CompactionEntry | None = None

    for entry in path:
        if isinstance(entry, ThinkingLevelChangeEntry):
            thinking_level = entry.thinking_level
        elif isinstance(entry, ModelChangeEntry):
            model = {"provider": entry.provider, "modelId": entry.model_id}
        elif isinstance(entry, SessionMessageEntry):
            msg = entry.message
            if hasattr(msg, "role") and msg.role == "assistant":
                # 从助手消息提取模型信息
                provider = getattr(msg, "provider", None)
                model_id = getattr(msg, "model", None)
                if provider and model_id:
                    model = {"provider": provider, "modelId": model_id}
        elif isinstance(entry, CompactionEntry):
            compaction = entry

    # 构建消息列表
    messages: list[Any] = []

    def append_message(entry: SessionEntry) -> None:
        """添加条目消息到列表"""
        msg = _extract_message_content(entry)
        if msg:
            messages.append(msg)

    if compaction:
        # 有压缩：先添加摘要，然后从 firstKeptEntryId 开始
        messages.append(
            {
                "role": "compaction_summary",
                "summary": compaction.summary,
                "tokens_before": compaction.tokens_before,
                "timestamp": compaction.timestamp,
            }
        )

        # 找到压缩点在路径中的位置
        compaction_idx = next(
            (i for i, e in enumerate(path) if e.id == compaction.id),
            -1,
        )

        if compaction_idx >= 0:
            # 添加保留的消息（从 firstKeptEntryId 到压缩点之前）
            found_first = False
            for i in range(compaction_idx):
                entry = path[i]
                if entry.id == compaction.first_kept_entry_id:
                    found_first = True
                if found_first:
                    append_message(entry)

            # 添加压缩点之后的消息
            for i in range(compaction_idx + 1, len(path)):
                append_message(path[i])
        else:
            # 压缩点不在路径中，添加所有消息
            for entry in path:
                append_message(entry)
    else:
        # 无压缩：添加所有消息
        for entry in path:
            append_message(entry)

    return SessionContext(
        messages=messages,
        thinking_level=thinking_level,
        model=model,
    )


def find_compaction_cut_point(
    entries: list[SessionEntry],
    compaction: CompactionEntry,
) -> int:
    """找到压缩切割点

    返回压缩条目在列表中的索引。

    Args:
        entries: 条目列表
        compaction: 压缩条目

    Returns:
        索引位置，如果未找到返回 -1
    """
    for i, entry in enumerate(entries):
        if entry.id == compaction.id:
            return i
    return -1


def collect_entries_for_branch_summary(
    entries: list[SessionEntry],
    from_id: str,
    to_id: str | None,
    by_id: dict[str, SessionEntry],
) -> list[SessionEntry]:
    """收集需要摘要的分支条目

    收集从 from_id 到 to_id（不包括）之间的所有条目。

    Args:
        entries: 完整条目列表
        from_id: 分支起始 ID
        to_id: 分支结束 ID（None 表示到叶子）
        by_id: ID 映射

    Returns:
        需要摘要的条目列表
    """
    result: list[SessionEntry] = []

    # 找到 from_id 和 to_id 在树中的位置
    current_id: str | None = from_id
    visited: set[str] = set()

    while current_id and current_id != to_id:
        if current_id in visited:
            # 防止循环
            break
        visited.add(current_id)

        entry = by_id.get(current_id)
        if not entry:
            break

        result.append(entry)
        current_id = entry.parent_id

    return result


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 核心函数
    "build_session_context",
    "get_latest_compaction_entry",
    # 辅助函数
    "find_compaction_cut_point",
    "collect_entries_for_branch_summary",
]
