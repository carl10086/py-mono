"""会话管理模块。

提供 JSONL 会话持久化和会话管理功能。
"""

from __future__ import annotations

from coding_agent.session.context import (
    build_session_context,
    collect_entries_for_branch_summary,
    find_compaction_cut_point,
    get_latest_compaction_entry,
)
from coding_agent.session.manager import ReadonlySessionManager, SessionManager
from coding_agent.session.parser import (
    is_valid_session_header,
    migrate_session_entries,
    parse_session_entries,
    parse_session_file,
    validate_session_entries,
)
from coding_agent.session.types import (
    BranchSummaryEntry,
    CompactionEntry,
    CustomEntry,
    CustomMessageEntry,
    CURRENT_SESSION_VERSION,
    FileEntry,
    LabelEntry,
    ModelChangeEntry,
    NewSessionOptions,
    SessionContext,
    SessionEntry,
    SessionEntryBase,
    SessionHeader,
    SessionInfo,
    SessionInfoEntry,
    SessionMessageEntry,
    SessionTreeNode,
    ThinkingLevelChangeEntry,
)

__all__ = [
    # 版本常量
    "CURRENT_SESSION_VERSION",
    # 基础类型
    "SessionEntryBase",
    "SessionHeader",
    "NewSessionOptions",
    # 条目类型
    "SessionMessageEntry",
    "ThinkingLevelChangeEntry",
    "ModelChangeEntry",
    "CompactionEntry",
    "BranchSummaryEntry",
    "CustomEntry",
    "CustomMessageEntry",
    "LabelEntry",
    "SessionInfoEntry",
    # 联合类型
    "SessionEntry",
    "FileEntry",
    # 树结构和上下文
    "SessionTreeNode",
    "SessionContext",
    "SessionInfo",
    # 管理器
    "SessionManager",
    "ReadonlySessionManager",
    # 解析器
    "parse_session_entries",
    "parse_session_file",
    "migrate_session_entries",
    "is_valid_session_header",
    "validate_session_entries",
    # 上下文
    "build_session_context",
    "get_latest_compaction_entry",
    "find_compaction_cut_point",
    "collect_entries_for_branch_summary",
]
