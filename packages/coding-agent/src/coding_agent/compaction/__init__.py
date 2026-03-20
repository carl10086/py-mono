"""压缩和摘要模块 - 对齐 pi-mono TypeScript 实现

提供长会话的上下文压缩和分支摘要功能。
"""

from __future__ import annotations

# 从 utils 导入
from coding_agent.compaction.utils import (
    SUMMARIZATION_SYSTEM_PROMPT,
    TOOL_RESULT_MAX_CHARS,
    FileOperations,
    compute_file_lists,
    create_file_ops,
    extract_file_ops_from_message,
    format_file_operations,
    serialize_conversation,
)

# 从 compaction 导入
from coding_agent.compaction.compaction import (
    DEFAULT_COMPACTION_SETTINGS,
    CompactionDetails,
    CompactionResult,
    CompactionSettings,
    PrepareCompactionResult,
    calculate_context_tokens,
    compact,
    estimate_context_tokens,
    estimate_tokens,
    prepare_compaction,
    should_compact,
)

# 从 branch_summary 导入
from coding_agent.compaction.branch_summary import (
    BranchPreparation,
    BranchSummaryDetails,
    BranchSummaryResult,
    CollectEntriesResult,
    collect_entries_for_branch_summary,
    generate_branch_summary,
    prepare_branch_summary,
)

__all__ = [
    # Utils
    "FileOperations",
    "create_file_ops",
    "extract_file_ops_from_message",
    "compute_file_lists",
    "format_file_operations",
    "TOOL_RESULT_MAX_CHARS",
    "serialize_conversation",
    "SUMMARIZATION_SYSTEM_PROMPT",
    # Compaction
    "CompactionSettings",
    "DEFAULT_COMPACTION_SETTINGS",
    "calculate_context_tokens",
    "estimate_tokens",
    "estimate_context_tokens",
    "should_compact",
    "CompactionDetails",
    "CompactionResult",
    "PrepareCompactionResult",
    "prepare_compaction",
    "compact",
    # Branch Summary
    "BranchSummaryResult",
    "BranchSummaryDetails",
    "BranchPreparation",
    "CollectEntriesResult",
    "collect_entries_for_branch_summary",
    "prepare_branch_summary",
    "generate_branch_summary",
]
