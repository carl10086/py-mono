"""SessionManager 核心模块 - 对齐 pi-mono TypeScript 实现

会话管理器 - 管理 JSONL 格式的会话持久化。

核心设计：
1. Append-only 树结构：每个条目有 id 和 parent_id
2. 叶子指针：_leaf_id 指向当前节点，新条目作为其子节点
3. 延迟刷盘：等第一个 assistant 消息才真正写文件
4. 版本迁移：支持 v1→v2→v3 格式升级

存储格式：
    JSONL - 每行一个 JSON 条目，首行是 session header

树结构示例：
    Root (session header, id=null)
    └── Message 1 (id=1, parent_id=null)
        └── Message 2 (id=2, parent_id=1) ← _leaf_id
            └── Message 3 (id=3, parent_id=2)

API 设计原则：
- 工厂方法创建实例（create, open, in_memory）
- 追加方法返回完整 entry 对象（方便调用方使用）
- 使用 snake_case 命名（Python 惯例）
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from coding_agent.config import get_default_session_dir, get_sessions_dir
from coding_agent.messages import BranchSummaryMessage, CompactionSummaryMessage
from coding_agent.session.types import (
    CURRENT_SESSION_VERSION,
    BranchSummaryEntry,
    CompactionEntry,
    CustomEntry,
    CustomMessageEntry,
    FileEntry,
    LabelEntry,
    ModelChangeEntry,
    NewSessionOptions,
    SessionContext,
    SessionEntry,
    SessionHeader,
    SessionInfo,
    SessionMessageEntry,
    SessionInfoEntry,
    SessionTreeNode,
    ThinkingLevelChangeEntry,
)


# ============================================================================
# ID 生成器
# ============================================================================


def _generate_id(existing_ids: set[str]) -> str:
    """生成唯一的短 ID（8位十六进制）

    使用 UUID 前 8 位，检查碰撞。

    算法：
    1. 循环最多 100 次生成 UUID 前 8 位
    2. 如果不冲突则返回
    3. 100 次都冲突则返回完整 UUID

    Args:
        existing_ids: 已存在的 ID 集合（用于碰撞检测）

    Returns:
        唯一的 8 字符十六进制字符串
    """
    for _ in range(100):
        short_id = uuid.uuid4().hex[:8]
        if short_id not in existing_ids:
            return short_id
    # 极端情况：100 次都冲突，回退到完整 UUID
    return uuid.uuid4().hex


# ============================================================================
# 会话信息构建辅助函数
# ============================================================================


def _is_message_with_content(entry: SessionEntry) -> bool:
    """检查条目是否为包含 content 的消息

    用于统计消息数量等场景。
    """
    if entry.type != "message":
        return False
    msg = getattr(entry, "message", None)
    return hasattr(msg, "content") and hasattr(msg, "role")


def _extract_text_from_content(content: Any) -> str:
    """从消息 content 中提取纯文本

    content 可能是：
    - str: 直接返回
    - list[dict]: 提取所有 type="text" 的 text 字段
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
        return " ".join(texts)
    return ""


def _get_entry_timestamp(entry: SessionEntry) -> int:
    """获取条目的 Unix 时间戳（毫秒）

    优先使用消息内的 timestamp，其次使用条目的 timestamp 字段。
    """
    if entry.type == "message":
        msg = getattr(entry, "message", None)
        if msg and hasattr(msg, "timestamp"):
            return msg.timestamp
    try:
        dt = datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except (ValueError, AttributeError):
        return 0


# ============================================================================
# 会话管理器
# ============================================================================


class SessionManager:
    """会话管理器 - 管理 JSONL 格式的会话文件

    核心职责：
    - 追加消息和元数据到会话
    - 持久化到 JSONL 文件
    - 提供树形遍历接口

    属性：
        session_id: 当前会话 ID
        session_file: 会话文件路径（None 表示内存模式）
        session_dir: 会话目录
        cwd: 工作目录
        is_persisted(): 是否持久化模式

    使用方式：
        # 创建新会话
        manager = SessionManager.create("/project")

        # 追加消息
        msg = {"role": "user", "content": "Hello"}
        manager.append_message(msg)

        # 查询
        entries = manager.get_entries()       # 所有条目
        branch = manager.get_branch()         # 从根到当前叶子
    """

    def __init__(
        self,
        cwd: str,
        session_dir: str,
        session_file: str | None,
        persist: bool,
    ) -> None:
        """初始化会话管理器（私有，请使用工厂方法）

        Args:
            cwd: 工作目录
            session_dir: 会话存储目录
            session_file: 初始会话文件路径（None 则创建新会话）
            persist: 是否持久化到文件
        """
        self._cwd = cwd
        self._session_dir = session_dir
        self._persist = persist

        # 刷盘状态：首次有 assistant 消息时才真正写文件
        # 这样确保空的或只有 user 消息的会话不会产生文件
        self._flushed = False

        # 会话标识
        self._session_id = ""
        self._session_file: str | None = None

        # 内存中的所有条目（包含头部）
        self._file_entries: list[FileEntry] = []

        # ID → 条目 索引，用于快速查找
        self._by_id: dict[str, SessionEntry] = {}

        # 标签索引：target_id → label
        self._labels_by_id: dict[str, str] = {}

        # 当前叶子节点 ID
        # 新条目会作为此节点的子节点
        self._leaf_id: str | None = None

        # 如果持久化模式且有目录，创建目录
        if persist and session_dir:
            Path(session_dir).mkdir(parents=True, exist_ok=True)

        # 根据是否有初始文件决定加载还是创建
        if session_file:
            self.set_session_file(session_file)
        else:
            self.new_session()

    # ========================================================================
    # 工厂方法
    # ========================================================================

    @staticmethod
    def create(cwd: str, session_dir: str | None = None) -> SessionManager:
        """创建新会话（持久化模式）

        Args:
            cwd: 工作目录
            session_dir: 会话目录（默认使用 ~/.pi/agent/sessions/<encoded-cwd>/）

        Returns:
            SessionManager 实例
        """
        dir_path = session_dir or get_default_session_dir(cwd)
        return SessionManager(cwd, dir_path, None, True)

    @staticmethod
    def open(file_path: str, session_dir: str | None = None) -> SessionManager:
        """打开现有会话文件

        Args:
            file_path: 会话文件路径
            session_dir: 会话目录（默认使用文件的父目录）

        Returns:
            SessionManager 实例
        """
        path = Path(file_path)
        cwd = str(Path.cwd())

        # 从文件头部读取工作目录
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line:
                        data = json.loads(first_line)
                        if data.get("type") == "session":
                            cwd = data.get("cwd", cwd)
            except (json.JSONDecodeError, OSError):
                pass

        dir_path = session_dir or str(path.parent)
        return SessionManager(cwd, dir_path, file_path, True)

    @staticmethod
    def in_memory(cwd: str | None = None) -> SessionManager:
        """创建内存会话（不持久化，用于测试）

        Args:
            cwd: 工作目录（默认当前目录）

        Returns:
            内存模式的 SessionManager
        """
        cwd = cwd or str(Path.cwd())
        return SessionManager(cwd, "", None, False)

    # ========================================================================
    # 属性访问
    # ========================================================================

    @property
    def session_id(self) -> str:
        """当前会话 ID"""
        return self._session_id

    @property
    def session_file(self) -> str | None:
        """会话文件路径（持久化模式）"""
        return self._session_file

    @property
    def session_dir(self) -> str:
        """会话目录"""
        return self._session_dir

    @property
    def cwd(self) -> str:
        """工作目录"""
        return self._cwd

    def is_persisted(self) -> bool:
        """是否持久化模式"""
        return self._persist

    # ========================================================================
    # 会话管理
    # ========================================================================

    def set_session_file(self, session_file: str) -> None:
        """切换到指定的会话文件

        用于：
        - 恢复已存在的会话
        - 在分支间切换

        Args:
            session_file: 会话文件路径
        """
        self._session_file = str(Path(session_file).resolve())
        path = Path(self._session_file)

        if path.exists():
            # 文件存在，加载条目
            self._load_entries_from_file()

            # 空文件或损坏 → 创建新会话但保留路径
            if not self._file_entries:
                explicit_path = self._session_file
                self.new_session()
                self._session_file = explicit_path
                self._rewrite_file()
                self._flushed = True
                return

            # 恢复会话 ID
            header = self._get_header()
            self._session_id = header.id if header else str(uuid.uuid4())

            # 版本迁移
            if self._migrate_entries():
                self._rewrite_file()

            # 构建索引
            self._build_index()
            self._flushed = True
        else:
            # 文件不存在，创建新会话但保留指定路径
            explicit_path = self._session_file
            self.new_session()
            self._session_file = explicit_path

    def _load_entries_from_file(self) -> None:
        """从会话文件加载所有条目到内存

        注意：当前实现只解析 session 头部，
        message 等其他条目类型需要后续完善。
        """
        self._file_entries = []
        if not self._session_file:
            return

        path = Path(self._session_file)
        if not path.exists():
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entry = self._parse_entry(data)
                        if entry:
                            self._file_entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

    def _parse_entry(self, data: dict[str, Any]) -> FileEntry | None:
        """解析 JSON 条目数据

        支持所有会话条目类型的解析，确保从文件恢复时不丢失数据。

        Args:
            data: JSON 解析后的字典

        Returns:
            类型化的条目，或 None（无法解析）
        """
        entry_type = data.get("type")
        if entry_type == "session":
            return SessionHeader(**data)
        if entry_type == "message":
            return SessionMessageEntry(**data)
        if entry_type == "thinking_level_change":
            return ThinkingLevelChangeEntry(**data)
        if entry_type == "model_change":
            return ModelChangeEntry(**data)
        if entry_type == "compaction":
            return CompactionEntry(**data)
        if entry_type == "branch_summary":
            return BranchSummaryEntry(**data)
        if entry_type == "custom":
            return CustomEntry(**data)
        if entry_type == "custom_message":
            return CustomMessageEntry(**data)
        if entry_type == "label":
            return LabelEntry(**data)
        if entry_type == "session_info":
            return SessionInfoEntry(**data)
        return None

    def _get_header(self) -> SessionHeader | None:
        """获取会话头部（第一个 session 类型条目）"""
        for entry in self._file_entries:
            if isinstance(entry, SessionHeader):
                return entry
        return None

    def _migrate_entries(self) -> bool:
        """执行版本迁移

        Returns:
            是否发生了迁移
        """
        header = self._get_header()
        if not header:
            return False

        version = getattr(header, "version", 1)
        if version >= CURRENT_SESSION_VERSION:
            return False

        if version < 2:
            self._migrate_v1_to_v2()
        if version < 3:
            self._migrate_v2_to_v3()

        return True

    def _migrate_v1_to_v2(self) -> None:
        """v1 → v2 迁移

        变化：
        - 添加 id 和 parent_id 字段形成树结构
        """
        ids: set[str] = set()
        prev_id: str | None = None

        for entry in self._file_entries:
            if isinstance(entry, SessionHeader):
                entry.version = 2
                continue

            new_id = _generate_id(ids)
            ids.add(new_id)

            if hasattr(entry, "id"):
                entry.id = new_id
            if hasattr(entry, "parent_id"):
                entry.parent_id = prev_id

            prev_id = new_id

    def _migrate_v2_to_v3(self) -> None:
        """v2 → v3 迁移

        变化：
        - hookMessage role → custom
        """
        for entry in self._file_entries:
            if isinstance(entry, SessionHeader):
                entry.version = 3
                continue

            if isinstance(entry, SessionMessageEntry):
                msg = entry.message
                if hasattr(msg, "role") and msg.role == "hookMessage":
                    msg.role = "custom"

    def _rewrite_file(self) -> None:
        """重写整个会话文件

        用于：
        - 首次刷盘（重写所有条目）
        - 版本迁移后（重写以应用新格式）
        """
        if not self._persist or not self._session_file:
            return

        path = Path(self._session_file)
        with open(path, "w", encoding="utf-8") as f:
            for entry in self._file_entries:
                f.write(json.dumps(entry.model_dump(), default=str) + "\n")

    def _build_index(self) -> None:
        """构建内存索引

        索引包括：
        - _by_id: ID → 条目 映射
        - _labels_by_id: 标签映射
        - _leaf_id: 当前叶子节点

        注意：按顺序遍历，最后一个条目的 ID 即为叶子
        """
        self._by_id.clear()
        self._labels_by_id.clear()
        self._leaf_id = None

        for entry in self._file_entries:
            if isinstance(entry, SessionHeader):
                continue

            if hasattr(entry, "id"):
                self._by_id[entry.id] = entry
                self._leaf_id = entry.id

            if isinstance(entry, LabelEntry):
                if entry.label:
                    self._labels_by_id[entry.target_id] = entry.label
                else:
                    self._labels_by_id.pop(entry.target_id, None)

    def new_session(self, options: NewSessionOptions | None = None) -> str | None:
        """创建新会话

        会重置所有内存状态，开始一个全新的会话。

        Args:
            options: 新会话选项（可选）

        Returns:
            新会话文件路径（持久化模式）或 None（内存模式）
        """
        opts = options or NewSessionOptions()
        self._session_id = opts.id or str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        header = SessionHeader(
            id=self._session_id,
            timestamp=timestamp,
            cwd=self._cwd,
            parent_session=opts.parent_session,
        )

        self._file_entries = [header]
        self._by_id.clear()
        self._labels_by_id.clear()
        self._leaf_id = None
        self._flushed = False

        if self._persist:
            # 文件名格式：时间戳_uuid.jsonl
            file_ts = timestamp.replace(":", "-").replace(".", "-")
            self._session_file = str(
                Path(self._session_dir) / f"{file_ts}_{self._session_id}.jsonl"
            )

        return self._session_file

    # ========================================================================
    # 公共追加方法
    # ========================================================================

    def append_message(self, message: Any) -> SessionMessageEntry:
        """追加消息条目

        消息会成为当前叶子节点的子节点，之后它成为新的叶子。

        Args:
            message: AgentMessage 实例

        Returns:
            创建的消息条目
        """
        entry = SessionMessageEntry(
            id=_generate_id(set(self._by_id.keys())),
            parent_id=self._leaf_id,
            timestamp=datetime.now().isoformat(),
            message=message,
        )
        self._append_entry(entry)
        return entry

    def append_thinking_level_change(self, level: str) -> ThinkingLevelChangeEntry:
        """追加思考级别变更条目

        Args:
            level: 新的思考级别（off/minimal/low/medium/high）

        Returns:
            创建的变更条目
        """
        entry = ThinkingLevelChangeEntry(
            id=_generate_id(set(self._by_id.keys())),
            parent_id=self._leaf_id,
            timestamp=datetime.now().isoformat(),
            thinking_level=level,
        )
        self._append_entry(entry)
        return entry

    def append_model_change(self, provider: str, model_id: str) -> ModelChangeEntry:
        """追加模型变更条目

        Args:
            provider: 提供商名称（如 anthropic）
            model_id: 模型标识符（如 claude-3-sonnet）

        Returns:
            创建的变更条目
        """
        entry = ModelChangeEntry(
            id=_generate_id(set(self._by_id.keys())),
            parent_id=self._leaf_id,
            timestamp=datetime.now().isoformat(),
            provider=provider,
            model_id=model_id,
        )
        self._append_entry(entry)
        return entry

    def append_compaction(
        self,
        summary: str,
        first_kept_entry_id: str,
        tokens_before: int,
        details: Any | None = None,
        from_hook: bool | None = None,
    ) -> CompactionEntry:
        """追加压缩摘要条目

        Args:
            summary: 压缩摘要文本
            first_kept_entry_id: 第一个保留条目的 ID
            tokens_before: 压缩前的 token 数量
            details: 扩展特定的详细数据（可选）
            from_hook: 是否由扩展生成（可选）

        Returns:
            创建的压缩条目
        """
        entry = CompactionEntry(
            id=_generate_id(set(self._by_id.keys())),
            parent_id=self._leaf_id,
            timestamp=datetime.now().isoformat(),
            summary=summary,
            first_kept_entry_id=first_kept_entry_id,
            tokens_before=tokens_before,
            details=details,
            from_hook=from_hook,
        )
        self._append_entry(entry)
        return entry

    def append_branch_summary(
        self,
        from_id: str,
        summary: str,
        details: Any | None = None,
        from_hook: bool | None = None,
    ) -> BranchSummaryEntry:
        """追加分支摘要条目

        Args:
            from_id: 分支起始条目 ID（或 "root"）
            summary: 分支摘要文本
            details: 扩展特定的详细数据（可选）
            from_hook: 是否由扩展生成（可选）

        Returns:
            创建的分支摘要条目
        """
        entry = BranchSummaryEntry(
            id=_generate_id(set(self._by_id.keys())),
            parent_id=self._leaf_id,
            timestamp=datetime.now().isoformat(),
            from_id=from_id,
            summary=summary,
            details=details,
            from_hook=from_hook,
        )
        self._append_entry(entry)
        return entry

    def append_custom_entry(self, custom_type: str, data: Any | None = None) -> CustomEntry:
        """追加自定义条目（用于扩展）

        Args:
            custom_type: 扩展类型标识符
            data: 扩展数据（可选）

        Returns:
            创建的自定义条目
        """
        entry = CustomEntry(
            id=_generate_id(set(self._by_id.keys())),
            parent_id=self._leaf_id,
            timestamp=datetime.now().isoformat(),
            custom_type=custom_type,
            data=data,
        )
        self._append_entry(entry)
        return entry

    def append_session_info(self, name: str | None = None) -> SessionInfoEntry:
        """追加会话信息条目

        Args:
            name: 会话显示名称（可选）

        Returns:
            创建的会话信息条目
        """
        entry = SessionInfoEntry(
            id=_generate_id(set(self._by_id.keys())),
            parent_id=self._leaf_id,
            timestamp=datetime.now().isoformat(),
            name=name,
        )
        self._append_entry(entry)
        return entry

    def append_label_change(self, target_id: str, label: str | None = None) -> LabelEntry:
        """追加标签变更条目

        Args:
            target_id: 被标记的条目 ID
            label: 标签文本（None 表示清除标签）

        Returns:
            创建的标签条目
        """
        entry = LabelEntry(
            id=_generate_id(set(self._by_id.keys())),
            parent_id=self._leaf_id,
            timestamp=datetime.now().isoformat(),
            target_id=target_id,
            label=label,
        )
        self._append_entry(entry)
        return entry

    def append_custom_message(
        self,
        custom_type: str,
        content: Any,
        display: bool = True,
        details: Any | None = None,
    ) -> CustomMessageEntry:
        """追加自定义消息条目（参与 LLM 上下文）

        Args:
            custom_type: 扩展类型标识符
            content: 消息内容
            display: 是否在 TUI 中显示
            details: 扩展元数据（可选）

        Returns:
            创建的自定义消息条目
        """
        entry = CustomMessageEntry(
            id=_generate_id(set(self._by_id.keys())),
            parent_id=self._leaf_id,
            timestamp=datetime.now().isoformat(),
            custom_type=custom_type,
            content=content,
            display=display,
            details=details,
        )
        self._append_entry(entry)
        return entry

    # ========================================================================
    # 内部追加方法
    # ========================================================================

    def _append_entry(self, entry: SessionEntry) -> None:
        """内部：追加条目到内存

        1. 添加到文件条目列表
        2. 更新 ID 索引
        3. 更新叶子指针
        4. 持久化到磁盘

        Args:
            entry: 要追加的条目
        """
        self._file_entries.append(entry)
        self._by_id[entry.id] = entry
        self._leaf_id = entry.id
        self._persist_entry(entry)

    def _persist_entry(self, entry: SessionEntry) -> None:
        """持久化单个条目到文件

        策略：
        - 如果还没有 assistant 消息，不刷盘（保持文件干净）
        - 首次刷盘时重写整个文件（确保一致性）
        - 后续追加时只追加新条目
        """
        if not self._persist or not self._session_file:
            return

        # 检查是否有 assistant 消息
        def _get_role(msg: Any) -> str | None:
            if isinstance(msg, dict):
                return msg.get("role")
            return getattr(msg, "role", None)

        has_assistant = any(
            isinstance(e, SessionMessageEntry) and _get_role(e.message) == "assistant"
            for e in self._file_entries
        )

        if not has_assistant:
            # 还没有 assistant 消息，标记为未刷新
            self._flushed = False
            return

        if not self._flushed:
            # 首次写入，重写整个文件
            self._rewrite_file()
            self._flushed = True
        else:
            # 追加模式
            path = Path(self._session_file)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.model_dump(), default=str) + "\n")

    # ========================================================================
    # 树遍历
    # ========================================================================

    def get_leaf_id(self) -> str | None:
        """获取当前叶子节点 ID

        Returns:
            叶子节点 ID，或 None（空会话）
        """
        return self._leaf_id

    def get_entry(self, entry_id: str) -> SessionEntry | None:
        """根据 ID 获取条目

        Args:
            entry_id: 条目 ID

        Returns:
            条目，或 None（不存在）
        """
        return self._by_id.get(entry_id)

    def get_branch(self, from_id: str | None = None) -> list[SessionEntry]:
        """获取从根到指定节点的路径

        用于构建 LLM 上下文。

        Args:
            from_id: 起始节点 ID（None 表示当前叶子）

        Returns:
            从根到该节点的条目列表（有序）
        """
        path: list[SessionEntry] = []
        current_id = from_id if from_id is not None else self._leaf_id

        while current_id:
            entry = self._by_id.get(current_id)
            if not entry:
                break
            path.insert(0, entry)
            current_id = entry.parent_id

        return path

    def get_leaf_entry(self) -> SessionEntry | None:
        """获取当前叶子节点条目

        Returns:
            叶子节点条目，或 None（空会话）
        """
        if not self._leaf_id:
            return None
        return self._by_id.get(self._leaf_id)

    def get_children(self, parent_id: str) -> list[SessionEntry]:
        """获取指定节点的所有直接子节点

        Args:
            parent_id: 父节点 ID

        Returns:
            子节点列表
        """
        children: list[SessionEntry] = []
        for entry in self._by_id.values():
            if entry.parent_id == parent_id:
                children.append(entry)
        return children

    def get_tree(self) -> list[SessionTreeNode]:
        """获取会话树结构

        返回所有条目的树形结构，用于 UI 展示。

        Returns:
            根节点列表
        """
        entries = self.get_entries()
        node_map: dict[str, SessionTreeNode] = {}
        roots: list[SessionTreeNode] = []

        for entry in entries:
            label = self._labels_by_id.get(entry.id)
            node_map[entry.id] = SessionTreeNode(entry=entry, children=[], label=label)

        for entry in entries:
            node = node_map[entry.id]
            if entry.parent_id is None or entry.parent_id == entry.id:
                roots.append(node)
            else:
                parent = node_map.get(entry.parent_id)
                if parent:
                    parent.children.append(node)
                else:
                    roots.append(node)

        def sort_children(nodes: list[SessionTreeNode]) -> None:
            for node in nodes:
                if node.children:
                    node.children.sort(key=lambda n: n.entry.timestamp)
                    sort_children(node.children)

        sort_children(roots)
        return roots

    def branch(self, branch_from_id: str) -> None:
        """从指定节点创建新分支

        将叶子指针移动到指定节点。之后的追加操作会创建该节点的新子节点，
        形成新分支。现有条目不会被修改或删除。

        Args:
            branch_from_id: 分支起始节点 ID

        Raises:
            ValueError: 节点不存在
        """
        if branch_from_id not in self._by_id:
            raise ValueError(f"Entry {branch_from_id} not found")
        self._leaf_id = branch_from_id

    def reset_leaf(self) -> None:
        """重置叶子指针到根之前

        将叶子指针设为 None。之后的追加操作会创建新的根条目（parent_id = null）。
        用于重新编辑第一条用户消息。
        """
        self._leaf_id = None

    def branch_with_summary(
        self,
        branch_from_id: str | None,
        summary: str,
        details: Any | None = None,
        from_hook: bool | None = None,
    ) -> BranchSummaryEntry:
        """从指定节点创建新分支，并添加分支摘要

        与 branch() 相同，但会添加一个 branch_summary 条目来捕获
        被放弃的对话路径的上下文。

        Args:
            branch_from_id: 分支起始节点 ID（None 表示从头开始）
            summary: 分支摘要文本
            details: 扩展特定的详细数据（可选）
            from_hook: 是否由扩展生成（可选）

        Returns:
            创建的分支摘要条目

        Raises:
            ValueError: 节点不存在
        """
        if branch_from_id is not None and branch_from_id not in self._by_id:
            raise ValueError(f"Entry {branch_from_id} not found")
        self._leaf_id = branch_from_id
        return self.append_branch_summary(
            from_id=branch_from_id or "root",
            summary=summary,
            details=details,
            from_hook=from_hook,
        )

    def get_entries(self) -> list[SessionEntry]:
        """获取所有非头部条目

        Returns:
            条目列表（不含 session header）
        """
        return [e for e in self._file_entries if not isinstance(e, SessionHeader)]

    def build_session_context(self, leaf_id: str | None = None) -> SessionContext:
        """构建会话上下文

        从指定叶子节点回溯构建 LLM 消息列表，同时处理：
        - 思考级别提取
        - 模型信息提取
        - 压缩摘要插入
        - 分支摘要插入
        - 自定义消息转换

        Args:
            leaf_id: 叶子节点 ID（None 表示当前叶子）

        Returns:
            SessionContext：包含消息列表、思考级别、模型信息
        """
        entries = self.get_entries()

        if not entries:
            return SessionContext(messages=[], thinking_level="off", model=None)

        if leaf_id is None:
            leaf_id = self._leaf_id

        if leaf_id is None:
            return SessionContext(messages=[], thinking_level="off", model=None)

        if leaf_id == "":
            return SessionContext(messages=[], thinking_level="off", model=None)

        leaf_entry = self._by_id.get(leaf_id)
        if not leaf_entry:
            leaf_entry = entries[-1] if entries else None

        if not leaf_entry:
            return SessionContext(messages=[], thinking_level="off", model=None)

        path: list[SessionEntry] = []
        current: SessionEntry | None = leaf_entry
        while current:
            path.insert(0, current)
            parent_id = current.parent_id
            if parent_id:
                current = self._by_id.get(parent_id)
            else:
                current = None

        thinking_level = "off"
        model: dict[str, str] | None = None
        compaction: CompactionEntry | None = None

        for entry in path:
            if entry.type == "thinking_level_change":
                thinking_level = entry.thinking_level
            elif entry.type == "model_change":
                model = {"provider": entry.provider, "model_id": entry.model_id}
            elif entry.type == "message":
                msg = getattr(entry, "message", None)
                if msg and hasattr(msg, "provider") and hasattr(msg, "model"):
                    model = {
                        "provider": getattr(msg, "provider", ""),
                        "model_id": getattr(msg, "model", ""),
                    }
            elif entry.type == "compaction":
                compaction = entry

        def _get_role(msg: Any) -> str | None:
            if isinstance(msg, dict):
                return msg.get("role")
            return getattr(msg, "role", None)

        def _append_message(entry: SessionEntry) -> None:
            if entry.type == "message":
                msg = getattr(entry, "message", None)
                if msg:
                    messages.append(msg)
            elif entry.type == "custom_message":
                msg_dict: dict[str, Any] = {
                    "role": "custom",
                    "custom_type": entry.custom_type,
                    "content": entry.content,
                    "display": entry.display,
                    "details": entry.details,
                }
                messages.append(msg_dict)
            elif entry.type == "branch_summary" and entry.summary:
                ts = 0
                try:
                    dt = datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00"))
                    ts = int(dt.timestamp() * 1000)
                except (ValueError, AttributeError):
                    pass
                messages.append(
                    BranchSummaryMessage(summary=entry.summary, from_id=entry.from_id, timestamp=ts)
                )

        messages: list[Any] = []

        if compaction:
            ts = 0
            try:
                dt = datetime.fromisoformat(compaction.timestamp.replace("Z", "+00:00"))
                ts = int(dt.timestamp() * 1000)
            except (ValueError, AttributeError):
                pass
            messages.append(
                CompactionSummaryMessage(
                    summary=compaction.summary, tokens_before=compaction.tokens_before, timestamp=ts
                )
            )

            compaction_idx = -1
            for i, e in enumerate(path):
                if e.type == "compaction" and e.id == compaction.id:
                    compaction_idx = i
                    break

            if compaction_idx > 0:
                found_first_kept = False
                first_kept_id = compaction.first_kept_entry_id

                for i in range(compaction_idx):
                    entry = path[i]
                    if entry.id == first_kept_id:
                        found_first_kept = True
                    if found_first_kept:
                        _append_message(entry)

            for i in range(compaction_idx + 1, len(path)):
                _append_message(path[i])
        else:
            for entry in path:
                _append_message(entry)

        return SessionContext(messages=messages, thinking_level=thinking_level, model=model)

    def get_session_name(self) -> str | None:
        """获取当前会话名称

        从最新的 session_info 条目获取会话名称。

        Returns:
            会话名称，或 None（未设置）
        """
        entries = self.get_entries()
        for entry in reversed(entries):
            if entry.type == "session_info":
                name = getattr(entry, "name", None)
                if name:
                    stripped = name.strip()
                    if stripped:
                        return stripped
        return None

    # ========================================================================
    # 静态工厂方法
    # ========================================================================

    @staticmethod
    def continue_recent(cwd: str, session_dir: str | None = None) -> SessionManager:
        """继续最近的会话，或创建新会话

        Args:
            cwd: 工作目录
            session_dir: 会话目录（默认使用 ~/.pi/agent/sessions/<encoded-cwd>/）

        Returns:
            SessionManager 实例
        """
        dir_path = session_dir or get_default_session_dir(cwd)
        most_recent = _find_most_recent_session(dir_path)
        if most_recent:
            return SessionManager(cwd, dir_path, most_recent, True)
        return SessionManager(cwd, dir_path, None, True)

    @staticmethod
    def fork_from(
        source_path: str, target_cwd: str, session_dir: str | None = None
    ) -> SessionManager:
        """从另一个项目目录分叉会话

        在目标工作目录中创建包含源会话完整历史的新会话。

        Args:
            source_path: 源会话文件路径
            target_cwd: 目标工作目录
            session_dir: 会话目录（默认使用目标工作目录的默认目录）

        Returns:
            新创建的 SessionManager 实例

        Raises:
            ValueError: 源会话文件无效或为空
        """
        import shutil

        source_entries = _load_entries_from_file(source_path)
        if not source_entries:
            raise ValueError(f"Cannot fork: source session file is empty or invalid: {source_path}")

        has_header = any(isinstance(e, SessionHeader) for e in source_entries)
        if not has_header:
            raise ValueError(f"Cannot fork: source session has no header: {source_path}")

        dir_path = session_dir or get_default_session_dir(target_cwd)
        Path(dir_path).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().isoformat()
        file_ts = timestamp.replace(":", "-").replace(".", "-")
        new_session_id = uuid.uuid4().hex
        new_session_file = str(Path(dir_path) / f"{file_ts}_{new_session_id}.jsonl")

        header = SessionHeader(
            id=new_session_id,
            timestamp=timestamp,
            cwd=target_cwd,
            parent_session=source_path,
        )

        with open(new_session_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(header.model_dump(), default=str) + "\n")

            for entry in source_entries:
                if not isinstance(entry, SessionHeader):
                    f.write(json.dumps(entry.model_dump(), default=str) + "\n")

        return SessionManager(target_cwd, dir_path, new_session_file, True)

    @staticmethod
    async def list(
        cwd: str,
        session_dir: str | None = None,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[SessionInfo]:
        """列出指定工作目录的所有会话

        Args:
            cwd: 工作目录（用于计算默认会话目录）
            session_dir: 可选的会话目录（默认使用 ~/.pi/agent/sessions/<encoded-cwd>/）
            on_progress: 可选的进度回调 (loaded, total)

        Returns:
            按 modified 时间降序排序的会话列表
        """
        dir_path = session_dir or get_default_session_dir(cwd)
        sessions = await _list_sessions_from_dir(dir_path, on_progress)
        sessions.sort(key=lambda s: s.modified, reverse=True)
        return sessions

    @staticmethod
    async def list_all(
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[SessionInfo]:
        """列出所有项目目录的会话

        Args:
            on_progress: 可选的进度回调 (loaded, total)

        Returns:
            按 modified 时间降序排序的会话列表
        """
        sessions_dir = get_sessions_dir()
        sessions_dir_path = Path(sessions_dir)

        if not sessions_dir_path.exists():
            return []

        sessions: list[SessionInfo] = []
        try:
            dirs = [d for d in sessions_dir_path.iterdir() if d.is_dir()]
        except OSError:
            return []

        dir_files: list[list[str]] = []
        total_files = 0
        for dir_entry in dirs:
            try:
                files = [
                    str(f) for f in dir_entry.iterdir() if f.suffix == ".jsonl" and f.is_file()
                ]
                dir_files.append(files)
                total_files += len(files)
            except OSError:
                dir_files.append([])

        loaded = 0

        async def process_file(file_path: str) -> SessionInfo | None:
            return await _build_session_info(file_path)

        for files in dir_files:
            if not files:
                continue
            results = await asyncio.gather(*[process_file(f) for f in files])
            for info in results:
                loaded += 1
                if on_progress:
                    on_progress(loaded, total_files)
                if info:
                    sessions.append(info)

        sessions.sort(key=lambda s: s.modified, reverse=True)
        return sessions


# ============================================================================
# 辅助函数
# ============================================================================


def _find_most_recent_session(session_dir: str) -> str | None:
    """查找最近修改的会话文件

    Args:
        session_dir: 会话目录

    Returns:
        最近会话文件路径，或 None
    """
    try:
        if not Path(session_dir).exists():
            return None

        files = []
        for f in Path(session_dir).iterdir():
            if f.suffix == ".jsonl" and f.is_file():
                try:
                    mtime = f.stat().st_mtime
                    files.append((str(f), mtime))
                except OSError:
                    continue

        if not files:
            return None

        files.sort(key=lambda x: x[1], reverse=True)
        return files[0][0]
    except OSError:
        return None


def _load_entries_from_file(file_path: str) -> list[FileEntry]:
    """从会话文件加载所有条目

    Args:
        file_path: 会话文件路径

    Returns:
        条目列表
    """
    entries: list[FileEntry] = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = _parse_entry_global(data)
                    if entry:
                        entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return entries


def _parse_entry_global(data: dict[str, Any]) -> FileEntry | None:
    """全局条目解析函数（用于静态方法）"""
    entry_type = data.get("type")
    if entry_type == "session":
        return SessionHeader(**data)
    if entry_type == "message":
        return SessionMessageEntry(**data)
    if entry_type == "thinking_level_change":
        return ThinkingLevelChangeEntry(**data)
    if entry_type == "model_change":
        return ModelChangeEntry(**data)
    if entry_type == "compaction":
        return CompactionEntry(**data)
    if entry_type == "branch_summary":
        return BranchSummaryEntry(**data)
    if entry_type == "custom":
        return CustomEntry(**data)
    if entry_type == "custom_message":
        return CustomMessageEntry(**data)
    if entry_type == "label":
        return LabelEntry(**data)
    if entry_type == "session_info":
        return SessionInfoEntry(**data)
    return None


# ============================================================================
# 会话列表辅助函数
# ============================================================================


def _is_message_with_content(message: Any) -> bool:
    """检查消息是否有文本内容"""
    return hasattr(message, "role") and hasattr(message, "content")


def _extract_text_content(message: Any) -> str:
    """从消息内容中提取文本"""
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
        return " ".join(texts)
    return ""


def _get_entry_timestamp(entry: FileEntry) -> int | None:
    """从条目获取时间戳"""
    if hasattr(entry, "timestamp"):
        ts = entry.timestamp
        if isinstance(ts, str):
            try:
                return int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1000)
            except ValueError:
                return None
        elif isinstance(ts, (int, float)):
            return int(ts)
    return None


def _get_last_activity_time(entries: list[FileEntry]) -> int | None:
    """从条目列表获取最后活动时间"""
    last_activity: int | None = None
    for entry in entries:
        if entry.type != "message":
            continue
        message = getattr(entry, "message", None)
        if not _is_message_with_content(message):
            continue
        if message.role != "user" and message.role != "assistant":
            continue
        ts = getattr(message, "timestamp", None)
        if isinstance(ts, (int, float)):
            last_activity = max(last_activity or 0, int(ts))
            continue
        entry_ts = _get_entry_timestamp(entry)
        if entry_ts is not None:
            last_activity = max(last_activity or 0, entry_ts)
    return last_activity


def _get_session_modified_date(
    entries: list[FileEntry],
    header: SessionHeader,
    stats_mtime: float,
) -> datetime:
    """获取会话最后修改时间"""
    last_activity = _get_last_activity_time(entries)
    if last_activity and last_activity > 0:
        return datetime.fromtimestamp(last_activity / 1000)
    header_ts = getattr(header, "timestamp", None)
    if isinstance(header_ts, str):
        try:
            return datetime.fromisoformat(header_ts.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.fromtimestamp(stats_mtime)


async def _build_session_info(file_path: str) -> SessionInfo | None:
    """从会话文件构建 SessionInfo 元数据

    Args:
        file_path: 会话文件路径

    Returns:
        SessionInfo 对象，或 None（解析失败）
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        entries: list[FileEntry] = []
        lines = content.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entry = _parse_entry_global(data)
                if entry:
                    entries.append(entry)
            except json.JSONDecodeError:
                continue

        if not entries:
            return None

        header = entries[0]
        if not isinstance(header, SessionHeader):
            return None

        stats = os.stat(file_path)
        message_count = 0
        all_messages: list[str] = []
        first_message = ""
        name: str | None = None

        for entry in entries:
            if entry.type == "session_info":
                info_entry = entry
                name_val = getattr(info_entry, "name", None)
                if name_val:
                    stripped = name_val.strip()
                    if stripped:
                        name = stripped

            if entry.type != "message":
                continue

            message_count += 1
            message = getattr(entry, "message", None)
            if not _is_message_with_content(message):
                continue
            if message.role != "user" and message.role != "assistant":
                continue

            text_content = _extract_text_content(message)
            if not text_content:
                continue

            all_messages.append(text_content)
            if not first_message and message.role == "user":
                first_message = text_content

        cwd = getattr(header, "cwd", "") or ""
        parent_session_path = getattr(header, "parent_session", None)

        modified = _get_session_modified_date(entries, header, stats.st_mtime)

        return SessionInfo(
            path=file_path,
            id=header.id,
            cwd=cwd,
            name=name,
            parent_session_path=parent_session_path,
            created=header.timestamp,
            modified=modified.isoformat(),
            message_count=message_count,
            first_message=first_message or "(no messages)",
            all_messages_text=" ".join(all_messages),
        )
    except OSError:
        return None


async def _list_sessions_from_dir(
    dir_path: str,
    on_progress: Callable[[int, int], None] | None = None,
    progress_offset: int = 0,
    progress_total: int | None = None,
) -> list[SessionInfo]:
    """异步列出目录中的所有会话

    Args:
        dir_path: 会话目录路径
        on_progress: 进度回调 (loaded, total)
        progress_offset: 进度偏移量
        progress_total: 总数（用于累积进度）

    Returns:
        SessionInfo 列表
    """
    sessions: list[SessionInfo] = []
    dir_path_obj = Path(dir_path)

    if not dir_path_obj.exists():
        return sessions

    try:
        files = [f for f in dir_path_obj.iterdir() if f.suffix == ".jsonl" and f.is_file()]
        total = progress_total if progress_total is not None else len(files)

        async def process_file(file_path: Path) -> SessionInfo | None:
            return await _build_session_info(str(file_path))

        tasks = [process_file(f) for f in files]
        results = await asyncio.gather(*tasks)

        loaded = 0
        for info in results:
            loaded += 1
            if on_progress:
                on_progress(progress_offset + loaded, total)
            if info:
                sessions.append(info)

    except OSError:
        pass

    return sessions


# ============================================================================
# 类型别名
# ============================================================================

ReadonlySessionManager = SessionManager
"""只读会话管理器类型别名

用于函数参数类型注解，表示该函数只读取会话不修改。
对应 TypeScript 的 Pick<T, 'getXxx' | 'getYyy'> 模式。
"""
