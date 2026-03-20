"""会话管理器核心 - 对齐 pi-mono TypeScript 实现

提供 JSONL 文件格式的会话持久化管理，支持：
- 创建、加载、追加会话条目
- 树结构导航和分支
- 版本迁移（v1→v2→v3）
- 内存和持久化两种模式
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from coding_agent.config import get_default_session_dir
from coding_agent.session.types import (
    CURRENT_SESSION_VERSION,
    FileEntry,
    LabelEntry,
    NewSessionOptions,
    SessionContext,
    SessionEntry,
    SessionHeader,
    SessionInfo,
    SessionMessageEntry,
    SessionTreeNode,
)


# ============================================================================
# ID 生成
# ============================================================================


def _generate_id(by_id: set[str]) -> str:
    """生成唯一的短 ID（8位十六进制）

    使用 UUID 前 8 位，检查碰撞。

    Args:
        by_id: 已存在的 ID 集合

    Returns:
        唯一的 8 字符十六进制字符串
    """
    for _ in range(100):
        short_id = uuid.uuid4().hex[:8]
        if short_id not in by_id:
            return short_id
    # 回退到完整 UUID
    return uuid.uuid4().hex


# ============================================================================
# 条目追加
# ============================================================================


def _is_message_with_content(entry: SessionEntry) -> bool:
    """检查条目是否为包含 content 的消息"""
    if entry.type != "message":
        return False
    msg = getattr(entry, "message", None)
    return hasattr(msg, "content") and hasattr(msg, "role")


def _extract_text_from_content(content: Any) -> str:
    """从内容中提取文本"""
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
    """获取条目的 Unix 时间戳（毫秒）"""
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
# 会话信息构建
# ============================================================================


def _count_messages(entries: list[FileEntry]) -> int:
    """计算消息条目数量"""
    return sum(1 for e in entries if isinstance(e, SessionEntry) and e.type == "message")


def _extract_first_message(entries: list[FileEntry]) -> str:
    """提取第一条用户消息"""
    for entry in entries:
        if not isinstance(entry, SessionEntry):
            continue
        if entry.type == "message":
            msg = getattr(entry, "message", None)
            if msg and getattr(msg, "role", None) == "user":
                content = getattr(msg, "content", "")
                return _extract_text_from_content(content)[:100]
    return "(no messages)"


def _extract_all_messages_text(entries: list[FileEntry]) -> str:
    """提取所有消息的文本内容"""
    texts = []
    for entry in entries:
        if not isinstance(entry, SessionEntry):
            continue
        if entry.type == "message":
            msg = getattr(entry, "message", None)
            if msg:
                content = getattr(msg, "content", "")
                text = _extract_text_from_content(content)
                if text:
                    texts.append(text)
    return " ".join(texts)


def _find_latest_session_info_name(entries: list[FileEntry]) -> str | None:
    """查找最新的会话名称"""
    for entry in reversed(entries):
        if not isinstance(entry, SessionEntry):
            continue
        if entry.type == "session_info":
            name = getattr(entry, "name", None)
            if name:
                return name.strip()
    return None


def _get_last_activity_time(entries: list[FileEntry]) -> int | None:
    """获取最后活动时间戳"""
    last_time: int | None = None
    for entry in entries:
        if not isinstance(entry, SessionEntry):
            continue
        if entry.type == "message":
            msg = getattr(entry, "message", None)
            if msg and getattr(msg, "role", None) in ("user", "assistant"):
                timestamp = getattr(msg, "timestamp", None)
                if timestamp:
                    last_time = max(last_time or 0, timestamp)
                else:
                    entry_time = _get_entry_timestamp(entry)
                    if entry_time:
                        last_time = max(last_time or 0, entry_time)
    return last_time


def _build_session_info(file_path: str, entries: list[FileEntry]) -> SessionInfo | None:
    """构建会话信息"""
    if not entries:
        return None

    header = entries[0]
    if not isinstance(header, SessionHeader):
        return None

    path = Path(file_path)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0

    msg_count = _count_messages(entries)
    first_msg = _extract_first_message(entries)
    all_text = _extract_all_messages_text(entries)
    name = _find_latest_session_info_name(entries)

    # 计算修改时间
    last_activity = _get_last_activity_time(entries)
    if last_activity:
        modified_ts = last_activity / 1000
    else:
        try:
            modified_ts = datetime.fromisoformat(
                header.timestamp.replace("Z", "+00:00")
            ).timestamp()
        except ValueError:
            modified_ts = mtime

    return SessionInfo(
        path=file_path,
        id=header.id,
        cwd=header.cwd,
        name=name,
        parent_session_path=header.parent_session,
        created=header.timestamp,
        modified=datetime.fromtimestamp(modified_ts).isoformat(),
        message_count=msg_count,
        first_message=first_msg,
        all_messages_text=all_text[:1000],  # 限制长度
    )


# ============================================================================
# 会话管理器
# ============================================================================


class SessionManager:
    """会话管理器 - 管理 JSONL 格式的会话文件

    使用 append-only 树结构存储会话，支持：
    - 消息追加和持久化
    - 分支导航
    - 版本迁移
    - 内存和文件两种模式

    属性：
        session_id: 当前会话 ID
        session_file: 会话文件路径（None 表示内存模式）
        session_dir: 会话目录
        cwd: 工作目录
        persist: 是否持久化到文件
    """

    def __init__(
        self,
        cwd: str,
        session_dir: str,
        session_file: str | None,
        persist: bool,
    ) -> None:
        """初始化会话管理器（私有，使用工厂方法创建）"""
        self._cwd = cwd
        self._session_dir = session_dir
        self._persist = persist
        self._flushed = False
        self._session_id = ""
        self._session_file: str | None = None
        self._file_entries: list[FileEntry] = []
        self._by_id: dict[str, SessionEntry] = {}
        self._labels_by_id: dict[str, str] = {}
        self._leaf_id: str | None = None

        if persist and session_dir:
            Path(session_dir).mkdir(parents=True, exist_ok=True)

        if session_file:
            self.set_session_file(session_file)
        else:
            self.new_session()

    # ========================================================================
    # 属性访问
    # ========================================================================

    @property
    def session_id(self) -> str:
        """获取会话 ID"""
        return self._session_id

    @property
    def session_file(self) -> str | None:
        """获取会话文件路径"""
        return self._session_file

    @property
    def session_dir(self) -> str:
        """获取会话目录"""
        return self._session_dir

    @property
    def cwd(self) -> str:
        """获取工作目录"""
        return self._cwd

    def is_persisted(self) -> bool:
        """检查是否为持久化模式"""
        return self._persist

    # ========================================================================
    # 会话管理
    # ========================================================================

    def set_session_file(self, session_file: str) -> None:
        """切换到指定的会话文件

        Args:
            session_file: 会话文件路径
        """
        self._session_file = str(Path(session_file).resolve())
        path = Path(self._session_file)

        if path.exists():
            self._load_entries_from_file()

            if not self._file_entries:
                # 文件为空或损坏，创建新会话
                explicit_path = self._session_file
                self.new_session()
                self._session_file = explicit_path
                self._rewrite_file()
                self._flushed = True
                return

            header = self._get_header()
            self._session_id = header.id if header else str(uuid.uuid4())

            if self._migrate_entries():
                self._rewrite_file()

            self._build_index()
            self._flushed = True
        else:
            # 文件不存在，创建新会话但保留路径
            explicit_path = self._session_file
            self.new_session()
            self._session_file = explicit_path

    def _load_entries_from_file(self) -> None:
        """从文件加载条目"""
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
        """解析条目数据"""
        entry_type = data.get("type")
        if entry_type == "session":
            return SessionHeader(**data)
        # 其他类型在版本迁移后解析
        return None

    def _get_header(self) -> SessionHeader | None:
        """获取会话头部"""
        for entry in self._file_entries:
            if isinstance(entry, SessionHeader):
                return entry
        return None

    def _migrate_entries(self) -> bool:
        """迁移条目到当前版本，返回是否发生迁移"""
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
        """从 v1 迁移到 v2"""
        ids: set[str] = set()
        prev_id: str | None = None

        for entry in self._file_entries:
            if isinstance(entry, SessionHeader):
                entry.version = 2
                continue

            # 为条目添加 id 和 parent_id
            new_id = _generate_id(ids)
            ids.add(new_id)

            # 这里需要修改条目的 id 和 parent_id
            # 由于条目是 dataclass/Pydantic 实例，需要特殊处理
            if hasattr(entry, "id"):
                entry.id = new_id
            if hasattr(entry, "parent_id"):
                entry.parent_id = prev_id

            prev_id = new_id

    def _migrate_v2_to_v3(self) -> None:
        """从 v2 迁移到 v3"""
        for entry in self._file_entries:
            if isinstance(entry, SessionHeader):
                entry.version = 3
                continue

            # 更新 role 为 hookMessage 的消息
            if isinstance(entry, SessionMessageEntry):
                msg = entry.message
                if hasattr(msg, "role") and msg.role == "hookMessage":
                    msg.role = "custom"

    def _rewrite_file(self) -> None:
        """重写整个会话文件"""
        if not self._persist or not self._session_file:
            return

        path = Path(self._session_file)
        with open(path, "w", encoding="utf-8") as f:
            for entry in self._file_entries:
                f.write(json.dumps(entry.model_dump(), default=str) + "\n")

    def _build_index(self) -> None:
        """构建 ID 索引"""
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

        Args:
            options: 新会话选项

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
            file_ts = timestamp.replace(":", "-").replace(".", "-")
            self._session_file = str(
                Path(self._session_dir) / f"{file_ts}_{self._session_id}.jsonl"
            )

        return self._session_file

    # ========================================================================
    # 条目追加
    # ========================================================================

    def _append_entry(self, entry: SessionEntry) -> None:
        """内部：追加条目到会话"""
        self._file_entries.append(entry)
        self._by_id[entry.id] = entry
        self._leaf_id = entry.id
        self._persist_entry(entry)

    def _persist_entry(self, entry: SessionEntry) -> None:
        """持久化单个条目"""
        if not self._persist or not self._session_file:
            return

        # 检查是否有助手消息
        has_assistant = any(
            isinstance(e, SessionMessageEntry) and getattr(e.message, "role", None) == "assistant"
            for e in self._file_entries
            if isinstance(e, SessionMessageEntry)
        )

        if not has_assistant:
            # 还没有助手消息，标记为未刷新
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
        """获取当前叶子节点 ID"""
        return self._leaf_id

    def get_entry(self, entry_id: str) -> SessionEntry | None:
        """根据 ID 获取条目"""
        return self._by_id.get(entry_id)

    def get_branch(self, from_id: str | None = None) -> list[SessionEntry]:
        """获取从指定节点到根的路径

        Args:
            from_id: 起始节点 ID（None 表示当前叶子）

        Returns:
            从根到该节点的条目列表
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
        """获取所有非头部条目"""
        return [e for e in self._file_entries if not isinstance(e, SessionHeader)]

    # ========================================================================
    # 静态工厂方法
    # ========================================================================

    @staticmethod
    def create(cwd: str, session_dir: str | None = None) -> SessionManager:
        """创建新会话

        Args:
            cwd: 工作目录
            session_dir: 可选的会话目录

        Returns:
            新创建的 SessionManager
        """
        dir_path = session_dir or get_default_session_dir(cwd)
        return SessionManager(cwd, dir_path, None, True)

    @staticmethod
    def open(file_path: str, session_dir: str | None = None) -> SessionManager:
        """打开现有会话文件

        Args:
            file_path: 会话文件路径
            session_dir: 可选的会话目录

        Returns:
            SessionManager 实例
        """
        # 从文件头部读取 cwd
        path = Path(file_path)
        cwd = str(Path.cwd())

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
        """创建内存会话（不持久化）

        Args:
            cwd: 可选的工作目录

        Returns:
            内存模式的 SessionManager
        """
        cwd = cwd or str(Path.cwd())
        return SessionManager(cwd, "", None, False)


# ============================================================================
# 只读会话管理器类型
# ============================================================================

ReadonlySessionManager = SessionManager
"""只读会话管理器类型别名（与 TypeScript Pick 对应）"""
