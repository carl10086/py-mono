"""上下文压缩 - 对齐 pi-mono TypeScript 实现

长会话的上下文压缩功能。
纯函数用于压缩逻辑，会话管理器处理 I/O。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from coding_agent.compaction.utils import (
    FileOperations,
    compute_file_lists,
    create_file_ops,
    extract_file_ops_from_message,
)
from coding_agent.session.types import CompactionEntry, SessionEntry


# ============================================================================
# 压缩设置
# ============================================================================


@dataclass
class CompactionSettings:
    """压缩设置"""

    enabled: bool = True
    reserve_tokens: int = 16384
    keep_recent_tokens: int = 20000


DEFAULT_COMPACTION_SETTINGS = CompactionSettings()


# ============================================================================
# Token 计算
# ============================================================================


def calculate_context_tokens(usage: dict[str, Any]) -> int:
    """计算总上下文 token 数

    使用原生 totalTokens 字段（如果可用），否则从组件计算。

    Args:
        usage: Usage 字典

    Returns:
        总 token 数
    """
    return usage.get("totalTokens", 0) or (
        usage.get("input", 0)
        + usage.get("output", 0)
        + usage.get("cacheRead", 0)
        + usage.get("cacheWrite", 0)
    )


def estimate_tokens(text: str) -> int:
    """估算文本的 token 数

    使用简单的启发式：每 4 个字符约 1 个 token。

    Args:
        text: 文本内容

    Returns:
        估算的 token 数
    """
    return len(text) // 4


def estimate_context_tokens(entries: list[SessionEntry]) -> int:
    """估算条目列表的总 token 数

    Args:
        entries: 会话条目列表

    Returns:
        估算的总 token 数
    """
    total = 0
    for entry in entries:
        if entry.type == "message":
            msg = getattr(entry, "message", None)
            if msg is None:
                continue
            if isinstance(msg, dict):
                content = msg.get("content")
            elif hasattr(msg, "content"):
                content = msg.content
            else:
                continue
            if isinstance(content, str):
                total += estimate_tokens(content)
            elif isinstance(content, list):
                for block in cast(list[dict[str, Any]], content):
                    if "text" in block:
                        total += estimate_tokens(block["text"])
    return total


# ============================================================================
# 压缩判断
# ============================================================================


def should_compact(
    entries: list[SessionEntry],
    settings: CompactionSettings,
    threshold_tokens: int = 8000,
) -> bool:
    """判断是否需要压缩

    Args:
        entries: 会话条目列表
        settings: 压缩设置
        threshold_tokens: 触发压缩的 token 阈值

    Returns:
        如果需要压缩返回 True
    """
    if not settings.enabled:
        return False

    estimated_tokens = estimate_context_tokens(entries)
    return estimated_tokens > threshold_tokens


# ============================================================================
# 文件操作提取
# ============================================================================


@dataclass
class CompactionDetails:
    """压缩条目详情"""

    read_files: list[str]
    modified_files: list[str]


def extract_file_operations(
    entries: list[SessionEntry],
    prev_compaction_index: int = -1,
) -> FileOperations:
    """从条目提取文件操作

    Args:
        entries: 会话条目列表
        prev_compaction_index: 前一个压缩条目索引

    Returns:
        FileOperations 实例
    """
    file_ops = create_file_ops()

    # 从前一个压缩条目中收集（如果是生成的）
    if prev_compaction_index >= 0 and prev_compaction_index < len(entries):
        prev_entry = entries[prev_compaction_index]
        if (
            isinstance(prev_entry, CompactionEntry)
            and not getattr(prev_entry, "from_hook", False)
            and prev_entry.details
        ):
            details = cast(dict[str, Any], prev_entry.details)
            read_files = details.get("readFiles", [])
            modified_files = details.get("modifiedFiles", [])
            if isinstance(read_files, list):
                for f in cast(list[str], read_files):
                    file_ops.read.add(f)
            if isinstance(modified_files, list):
                for f in cast(list[str], modified_files):
                    file_ops.edited.add(f)

    # 从消息中提取工具调用
    for entry in entries:
        if entry.type == "message":
            msg = getattr(entry, "message", None)
            if msg:
                extract_file_ops_from_message(msg, file_ops)

    return file_ops


# ============================================================================
# 压缩准备
# ============================================================================


@dataclass
class PrepareCompactionResult:
    """压缩准备结果"""

    messages: list[Any]
    """用于摘要的消息列表"""

    file_ops: FileOperations
    """文件操作"""

    tokens_before: int
    """压缩前的 token 数"""

    first_kept_entry_id: str | None
    """第一个保留条目的 ID"""


@dataclass
class CompactionResult:
    """压缩结果"""

    summary: str
    """摘要文本"""

    first_kept_entry_id: str
    """第一个保留条目的 ID"""

    tokens_before: int
    """压缩前的 token 数"""

    details: CompactionDetails | None = None
    """扩展数据（如文件列表）"""


def prepare_compaction(
    entries: list[SessionEntry],
    settings: CompactionSettings,
) -> PrepareCompactionResult:
    """准备压缩

    收集需要摘要的消息和文件操作。

    Args:
        entries: 会话条目列表
        settings: 压缩设置

    Returns:
        压缩准备结果
    """
    messages: list[Any] = []
    tokens_before = 0
    first_kept_entry_id: str | None = None

    def _get_content(msg: Any) -> Any:
        """从 message 中获取 content"""
        if isinstance(msg, dict):
            return msg.get("content")
        return getattr(msg, "content", None)

    # 收集消息用于摘要
    for entry in entries:
        if entry.type == "message":
            msg = getattr(entry, "message", None)
            if msg:
                messages.append(msg)
                content = _get_content(msg)
                if isinstance(content, str):
                    tokens_before += estimate_tokens(content)
                elif isinstance(content, list):
                    for block in cast(list[dict[str, Any]], content):
                        if "text" in block:
                            tokens_before += estimate_tokens(block["text"])

    # 提取文件操作
    file_ops = extract_file_operations(entries)

    # 确定第一个保留条目（保留最近的 keep_recent_tokens）
    cumulative_tokens = 0
    for entry in reversed(entries):
        if entry.type == "message":
            msg = getattr(entry, "message", None)
            content = _get_content(msg) if msg else None
            if content:
                msg_tokens = 0
                if isinstance(content, str):
                    msg_tokens = estimate_tokens(content)
                elif isinstance(content, list):
                    msg_tokens = sum(
                        estimate_tokens(block.get("text", ""))
                        for block in cast(list[dict[str, Any]], content)
                    )
                cumulative_tokens += msg_tokens
                if cumulative_tokens > settings.keep_recent_tokens:
                    first_kept_entry_id = entry.id
                    break

    return PrepareCompactionResult(
        messages=messages,
        file_ops=file_ops,
        tokens_before=tokens_before,
        first_kept_entry_id=first_kept_entry_id,
    )


def compact(
    entries: list[SessionEntry],
    settings: CompactionSettings,
    generate_summary_fn: Any | None = None,
) -> CompactionResult | None:
    """执行压缩

    Args:
        entries: 会话条目列表
        settings: 压缩设置
        generate_summary_fn: 生成摘要的函数（可选）

    Returns:
        压缩结果，如果不需要压缩返回 None
    """
    if not should_compact(entries, settings):
        return None

    # 准备压缩
    prep = prepare_compaction(entries, settings)

    # 生成摘要（如果有提供函数）
    summary = "Conversation summary placeholder"
    if generate_summary_fn:
        try:
            summary = generate_summary_fn(prep.messages)
        except Exception:
            pass

    # 计算文件列表
    read_files, modified_files = compute_file_lists(prep.file_ops)

    # 创建详情
    details = CompactionDetails(
        read_files=read_files,
        modified_files=modified_files,
    )

    return CompactionResult(
        summary=summary,
        first_kept_entry_id=prep.first_kept_entry_id or "",
        tokens_before=prep.tokens_before,
        details=details,
    )


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 设置
    "CompactionSettings",
    "DEFAULT_COMPACTION_SETTINGS",
    # Token 计算
    "calculate_context_tokens",
    "estimate_tokens",
    "estimate_context_tokens",
    # 压缩判断
    "should_compact",
    # 压缩执行
    "CompactionDetails",
    "CompactionResult",
    "PrepareCompactionResult",
    "prepare_compaction",
    "compact",
]
