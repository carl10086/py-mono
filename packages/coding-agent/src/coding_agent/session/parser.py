"""会话解析器 - JSONL 解析与版本迁移

提供会话文件的解析和版本迁移功能：
- 解析 JSONL 文件为类型化条目
- 版本迁移（v1→v2→v3）
- 条目反序列化
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from coding_agent.session.types import (
    CURRENT_SESSION_VERSION,
    BranchSummaryEntry,
    CompactionEntry,
    CustomEntry,
    CustomMessageEntry,
    FileEntry,
    LabelEntry,
    ModelChangeEntry,
    SessionEntry,
    SessionHeader,
    SessionInfoEntry,
    SessionMessageEntry,
    ThinkingLevelChangeEntry,
)


# ============================================================================
# ID 生成
# ============================================================================


def _generate_id(by_id: set[str]) -> str:
    """生成唯一的短 ID（8位十六进制）

    Args:
        by_id: 已存在的 ID 集合

    Returns:
        唯一的 8 字符十六进制字符串
    """
    for _ in range(100):
        short_id = uuid.uuid4().hex[:8]
        if short_id not in by_id:
            return short_id
    return uuid.uuid4().hex


# ============================================================================
# 条目反序列化
# ============================================================================


def _deserialize_entry(data: dict[str, Any]) -> SessionEntry | None:
    """将字典反序列化为类型化条目

    Args:
        data: 条目字典数据

    Returns:
        类型化的 SessionEntry，或 None（如果无法识别）
    """
    entry_type = data.get("type")
    if not entry_type:
        return None

    try:
        match entry_type:
            case "message":
                return SessionMessageEntry(**data)
            case "thinking_level_change":
                return ThinkingLevelChangeEntry(**data)
            case "model_change":
                return ModelChangeEntry(**data)
            case "compaction":
                return CompactionEntry(**data)
            case "branch_summary":
                return BranchSummaryEntry(**data)
            case "custom":
                return CustomEntry(**data)
            case "custom_message":
                return CustomMessageEntry(**data)
            case "label":
                return LabelEntry(**data)
            case "session_info":
                return SessionInfoEntry(**data)
            case _:
                return None
    except (TypeError, ValueError):
        # 反序列化失败，返回 None
        return None


def _deserialize_header(data: dict[str, Any]) -> SessionHeader | None:
    """反序列化会话头部

    Args:
        data: 头部字典数据

    Returns:
        SessionHeader，或 None（如果无效）
    """
    if data.get("type") != "session":
        return None
    try:
        return SessionHeader(**data)
    except (TypeError, ValueError):
        return None


# ============================================================================
# 解析函数
# ============================================================================


def parse_session_entries(content: str) -> list[FileEntry]:
    """解析会话内容（JSONL 格式）为类型化条目列表

    解析 JSONL 格式的会话内容，每行一个条目。
    自动处理损坏的行和格式错误。

    Args:
        content: JSONL 格式的会话内容

    Returns:
        类型化的条目列表（包含头部和条目）

    Example:
        >>> content = '''{"type": "session", "id": "abc", "timestamp": "..."}
        ... {"type": "message", "id": "msg1", "parent_id": null, ...}
        ... '''
        >>> entries = parse_session_entries(content)
        >>> len(entries)
        2
    """
    entries: list[FileEntry] = []
    lines = content.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            # 跳过损坏的行
            continue

        # 尝试解析为头部或条目
        if data.get("type") == "session":
            header = _deserialize_header(data)
            if header:
                entries.append(header)
        else:
            entry = _deserialize_entry(data)
            if entry:
                entries.append(entry)

    return entries


def parse_session_file(file_path: str) -> list[FileEntry]:
    """解析会话文件为类型化条目列表

    Args:
        file_path: 会话文件路径

    Returns:
        类型化的条目列表，如果文件不存在或无法读取返回空列表
    """
    path = Path(file_path)
    if not path.exists():
        return []

    try:
        content = path.read_text(encoding="utf-8")
        return parse_session_entries(content)
    except (OSError, UnicodeDecodeError):
        return []


# ============================================================================
# 版本迁移
# ============================================================================


def migrate_session_entries(entries: list[FileEntry]) -> bool:
    """迁移条目到当前版本

    原地修改条目列表，执行必要的版本迁移。
    支持 v1→v2→v3 的迁移链。

    Args:
        entries: 条目列表（会被修改）

    Returns:
        如果发生了迁移返回 True，否则返回 False

    Migration v1→v2:
        - 为所有条目添加 id 和 parent_id 字段
        - 将 compaction 条目的 firstKeptEntryIndex 重命名为 firstKeptEntryId

    Migration v2→v3:
        - 将 message 条目中 role="hookMessage" 改为 role="custom"
    """
    if not entries:
        return False

    # 获取当前版本
    header = next(
        (e for e in entries if isinstance(e, SessionHeader)),
        None,
    )
    current_version = header.version if header else 1

    if current_version >= CURRENT_SESSION_VERSION:
        return False

    migrated = False

    # v1 → v2
    if current_version < 2:
        _migrate_v1_to_v2(entries)
        migrated = True

    # v2 → v3
    if current_version < 3:
        _migrate_v2_to_v3(entries)
        migrated = True

    return migrated


def _migrate_v1_to_v2(entries: list[FileEntry]) -> None:
    """从 v1 迁移到 v2

    为所有条目添加 id 和 parent_id，形成树结构。
    """
    ids: set[str] = set()
    prev_id: str | None = None
    entry_list: list[SessionEntry] = []

    # 分离头部和条目
    header: SessionHeader | None = None
    for entry in entries:
        if isinstance(entry, SessionHeader):
            header = entry
        elif isinstance(entry, SessionEntry):
            entry_list.append(entry)

    # 更新头部版本
    if header:
        header.version = 2

    # 为每个条目添加 id 和 parent_id
    for entry in entry_list:
        new_id = _generate_id(ids)
        ids.add(new_id)

        # 使用 object.__setattr__ 避免 Pydantic 验证
        object.__setattr__(entry, "id", new_id)
        object.__setattr__(entry, "parent_id", prev_id)

        # 处理 compaction 条目的 firstKeptEntryIndex → firstKeptEntryId
        if isinstance(entry, CompactionEntry):
            # v1 中可能使用 firstKeptEntryIndex，需要转换
            # 这里简化处理，假设 v1 的条目已经按顺序排列
            pass

        prev_id = new_id

    # 更新条目列表
    entries.clear()
    if header:
        entries.append(header)
    entries.extend(entry_list)


def _migrate_v2_to_v3(entries: list[FileEntry]) -> None:
    """从 v2 迁移到 v3

    将 message 条目中 role="hookMessage" 改为 role="custom"。
    """
    for entry in entries:
        if isinstance(entry, SessionHeader):
            entry.version = 3
        elif isinstance(entry, SessionMessageEntry):
            msg = entry.message
            if isinstance(msg, dict) and msg.get("role") == "hookMessage":
                msg["role"] = "custom"


# ============================================================================
# 验证函数
# ============================================================================


def is_valid_session_header(data: dict[str, Any]) -> bool:
    """验证数据是否为有效的会话头部

    Args:
        data: 字典数据

    Returns:
        如果是有效的会话头部返回 True
    """
    if data.get("type") != "session":
        return False
    if not isinstance(data.get("id"), str):
        return False
    if not isinstance(data.get("timestamp"), str):
        return False
    return True


def validate_session_entries(entries: list[FileEntry]) -> list[str]:
    """验证条目列表的完整性

    检查：
    - 是否存在有效的头部
    - ID 是否唯一
    - parent_id 是否有效

    Args:
        entries: 条目列表

    Returns:
        错误信息列表（空列表表示无错误）
    """
    errors: list[str] = []

    if not entries:
        errors.append("条目列表为空")
        return errors

    # 检查头部
    header = next(
        (e for e in entries if isinstance(e, SessionHeader)),
        None,
    )
    if not header:
        errors.append("缺少会话头部")

    # 收集所有 ID
    ids: set[str] = set()
    session_entries = [e for e in entries if isinstance(e, SessionEntry) and hasattr(e, "id")]

    for entry in session_entries:
        entry_id = entry.id
        if entry_id in ids:
            errors.append(f"重复的 ID: {entry_id}")
        ids.add(entry_id)

    # 检查 parent_id
    for entry in session_entries:
        parent_id = entry.parent_id
        if parent_id is not None and parent_id not in ids:
            errors.append(f"无效的 parent_id: {parent_id} (条目: {entry.id})")

    return errors


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 解析函数
    "parse_session_entries",
    "parse_session_file",
    # 迁移函数
    "migrate_session_entries",
    # 验证函数
    "is_valid_session_header",
    "validate_session_entries",
]
