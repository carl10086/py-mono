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

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from coding_agent.config import get_default_session_dir
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
    SessionEntry,
    SessionHeader,
    SessionMessageEntry,
    SessionInfoEntry,
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

    def get_entries(self) -> list[SessionEntry]:
        """获取所有非头部条目

        Returns:
            条目列表（不含 session header）
        """
        return [e for e in self._file_entries if not isinstance(e, SessionHeader)]


# ============================================================================
# 类型别名
# ============================================================================

ReadonlySessionManager = SessionManager
"""只读会话管理器类型别名

用于函数参数类型注解，表示该函数只读取会话不修改。
对应 TypeScript 的 Pick<T, 'getXxx' | 'getYyy'> 模式。
"""
