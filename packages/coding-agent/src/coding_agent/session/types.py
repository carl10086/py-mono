"""
会话条目类型定义 - 对齐 pi-mono TypeScript 实现

提供会话持久化的完整类型系统，包括：
- 会话头部和条目基类
- 各类条目类型（消息、压缩、分支等）
- 树结构和上下文类型
- 类型守卫函数

设计原则：
1. 所有条目都有 id/parentId 形成树结构
2. 支持版本迁移（CURRENT_SESSION_VERSION）
3. 扩展友好的自定义条目类型
"""

from __future__ import annotations

from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from ai.types import ImageContent, TextContent

# ============================================================================
# 版本常量
# ============================================================================

CURRENT_SESSION_VERSION = 3
"""当前会话文件版本号

版本历史：
- v1: 初始版本，条目无 id/parentId
- v2: 添加树结构（id/parentId），compaction 使用 firstKeptEntryId
- v3: 重命名 hookMessage role 为 custom
"""

# ============================================================================
# 基础类型
# ============================================================================


class SessionEntryBase(BaseModel):
    """所有会话条目的基类

    每个条目都有唯一的 id 和指向父节点的 parentId，
    形成树结构支持分支和导航。

    属性：
        type: 条目类型标识符
        id: 唯一标识符（8位十六进制）
        parent_id: 父条目ID（None 表示根节点）
        timestamp: ISO 8601 格式时间戳
    """

    type: str
    id: str
    parent_id: str | None
    timestamp: str


class SessionHeader(BaseModel):
    """会话文件头部

    每个会话文件的第一行，包含会话元数据。

    属性：
        type: 固定为 "session"
        version: 会话文件版本号
        id: 会话唯一标识符（UUID）
        timestamp: 创建时间戳（ISO 8601）
        cwd: 工作目录路径
        parent_session: 父会话路径（fork 时设置）
    """

    type: Literal["session"] = "session"
    version: int = CURRENT_SESSION_VERSION
    id: str
    timestamp: str
    cwd: str
    parent_session: str | None = None


class NewSessionOptions(BaseModel):
    """创建新会话的选项

    属性：
        id: 可选的会话ID（默认自动生成）
        parent_session: 父会话路径（fork 时使用）
    """

    id: str | None = None
    parent_session: str | None = None


# ============================================================================
# 条目类型
# ============================================================================


class SessionMessageEntry(SessionEntryBase):
    """消息条目

    存储 LLM 对话中的消息（user/assistant/toolResult/custom）。

    属性：
        type: 固定为 "message"
        message: AgentMessage 实例
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    type: Literal["message"] = "message"
    message: Any  # AgentMessage - 使用 Any 避免 Pydantic 序列化问题


class ThinkingLevelChangeEntry(SessionEntryBase):
    """思考级别变更条目

    记录用户或系统更改思考级别的操作。

    属性：
        type: 固定为 "thinking_level_change"
        thinking_level: 新的思考级别
    """

    type: Literal["thinking_level_change"] = "thinking_level_change"
    thinking_level: str


class ModelChangeEntry(SessionEntryBase):
    """模型变更条目

    记录用户切换模型的操作。

    属性：
        type: 固定为 "model_change"
        provider: 模型提供商
        model_id: 模型标识符
    """

    type: Literal["model_change"] = "model_change"
    provider: str
    model_id: str


class CompactionEntry(BaseModel):
    """压缩条目

    记录上下文压缩操作，包含被压缩内容的摘要。

    属性：
        type: 固定为 "compaction"
        id: 唯一标识符
        parent_id: 父条目ID
        timestamp: ISO 8601 时间戳
        summary: 压缩摘要文本
        first_kept_entry_id: 第一个保留条目的ID
        tokens_before: 压缩前的 token 数量
        details: 扩展特定的详细数据（可选）
        from_hook: 是否由扩展生成（可选）
    """

    type: Literal["compaction"] = "compaction"
    id: str
    parent_id: str | None
    timestamp: str
    summary: str
    first_kept_entry_id: str
    tokens_before: int
    details: Any | None = None
    from_hook: bool | None = None


class BranchSummaryEntry(BaseModel):
    """分支摘要条目

    在分支导航时生成，记录被放弃路径的摘要。

    属性：
        type: 固定为 "branch_summary"
        id: 唯一标识符
        parent_id: 父条目ID
        timestamp: ISO 8601 时间戳
        from_id: 分支起始条目ID（或 "root"）
        summary: 分支摘要文本
        details: 扩展特定的详细数据（可选）
        from_hook: 是否由扩展生成（可选）
    """

    type: Literal["branch_summary"] = "branch_summary"
    id: str
    parent_id: str | None
    timestamp: str
    from_id: str
    summary: str
    details: Any | None = None
    from_hook: bool | None = None


class CustomEntry(BaseModel):
    """自定义条目（用于扩展）

    扩展可以使用此类型存储特定数据到会话中，
    不参与 LLM 上下文构建。

    用途：跨会话重载时恢复扩展内部状态。

    属性：
        type: 固定为 "custom"
        id: 唯一标识符
        parent_id: 父条目ID
        timestamp: ISO 8601 时间戳
        custom_type: 扩展类型标识符
        data: 扩展数据（任意类型）
    """

    type: Literal["custom"] = "custom"
    id: str
    parent_id: str | None
    timestamp: str
    custom_type: str
    data: Any | None = None


class LabelEntry(BaseModel):
    """标签条目

    用户对条目的书签/标记。

    属性：
        type: 固定为 "label"
        id: 唯一标识符
        parent_id: 父条目ID
        timestamp: ISO 8601 时间戳
        target_id: 被标记的条目ID
        label: 标签文本（None 表示清除标签）
    """

    type: Literal["label"] = "label"
    id: str
    parent_id: str | None
    timestamp: str
    target_id: str
    label: str | None = None


class SessionInfoEntry(BaseModel):
    """会话信息条目

    存储会话元数据，如用户定义的显示名称。

    属性：
        type: 固定为 "session_info"
        id: 唯一标识符
        parent_id: 父条目ID
        timestamp: ISO 8601 时间戳
        name: 会话显示名称（可选）
    """

    type: Literal["session_info"] = "session_info"
    id: str
    parent_id: str | None
    timestamp: str
    name: str | None = None


class CustomMessageEntry(BaseModel):
    """自定义消息条目（参与 LLM 上下文）

    与 CustomEntry 不同，此类型参与 LLM 上下文构建，
    内容会被转换为用户消息发送到 LLM。

    display 控制 TUI 渲染：
    - False: 完全隐藏
    - True: 以特殊样式渲染（与用户消息不同）

    属性：
        type: 固定为 "custom_message"
        id: 唯一标识符
        parent_id: 父条目ID
        timestamp: ISO 8601 时间戳
        custom_type: 扩展类型标识符
        content: 消息内容（字符串或内容块数组）
        details: 扩展元数据（可选，不发送到 LLM）
        display: 是否在 TUI 中显示
    """

    type: Literal["custom_message"] = "custom_message"
    id: str
    parent_id: str | None
    timestamp: str
    custom_type: str
    content: str | list[TextContent | ImageContent]
    details: Any | None = None
    display: bool


# ============================================================================
# 联合类型
# ============================================================================

SessionEntry: TypeAlias = (
    SessionMessageEntry
    | ThinkingLevelChangeEntry
    | ModelChangeEntry
    | CompactionEntry
    | BranchSummaryEntry
    | CustomEntry
    | CustomMessageEntry
    | LabelEntry
    | SessionInfoEntry
)
"""会话条目联合类型（不包含头部）"""

FileEntry: TypeAlias = SessionHeader | SessionEntry
"""文件条目联合类型（包含头部和所有条目）"""

# ============================================================================
# 树结构和上下文类型
# ============================================================================


class SessionTreeNode(BaseModel):
    """会话树节点

    用于 get_tree() 返回的防御性会话结构副本。

    属性：
        entry: 条目数据
        children: 子节点列表
        label: 条目标签（如果有）
    """

    entry: SessionEntry
    children: list["SessionTreeNode"] = Field(default_factory=list)
    label: str | None = None


class SessionContext(BaseModel):
    """会话上下文

    build_session_context() 返回的结果，包含发送到 LLM 的消息列表。

    属性：
        messages: LLM 消息列表
        thinking_level: 当前思考级别
        model: 当前模型信息（如果有）
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    messages: list[Any]  # list[AgentMessage] - 使用 Any 避免序列化问题
    thinking_level: str = "off"
    model: dict[str, str] | None = None


class SessionInfo(BaseModel):
    """会话信息

    用于列表展示和会话选择器的元数据。

    属性：
        path: 会话文件路径
        id: 会话ID
        cwd: 工作目录
        name: 用户定义的显示名称（可选）
        parent_session_path: 父会话路径（fork 时设置，可选）
        created: 创建时间
        modified: 最后修改时间
        message_count: 消息数量
        first_message: 第一条消息预览
        all_messages_text: 所有消息的合并文本（用于搜索）
    """

    path: str
    id: str
    cwd: str
    name: str | None = None
    parent_session_path: str | None = None
    created: str  # ISO 8601
    modified: str  # ISO 8601
    message_count: int
    first_message: str
    all_messages_text: str


# ============================================================================
# 类型守卫函数
# ============================================================================


def is_session_message_entry(entry: SessionEntry) -> bool:
    """检查条目是否为消息条目"""
    return entry.type == "message"


def is_thinking_level_change_entry(entry: SessionEntry) -> bool:
    """检查条目是否为思考级别变更条目"""
    return entry.type == "thinking_level_change"


def is_model_change_entry(entry: SessionEntry) -> bool:
    """检查条目是否为模型变更条目"""
    return entry.type == "model_change"


def is_compaction_entry(entry: SessionEntry) -> bool:
    """检查条目是否为压缩条目"""
    return entry.type == "compaction"


def is_branch_summary_entry(entry: SessionEntry) -> bool:
    """检查条目是否为分支摘要条目"""
    return entry.type == "branch_summary"


def is_custom_entry(entry: SessionEntry) -> bool:
    """检查条目是否为自定义条目"""
    return entry.type == "custom"


def is_custom_message_entry(entry: SessionEntry) -> bool:
    """检查条目是否为自定义消息条目"""
    return entry.type == "custom_message"


def is_label_entry(entry: SessionEntry) -> bool:
    """检查条目是否为标签条目"""
    return entry.type == "label"


def is_session_info_entry(entry: SessionEntry) -> bool:
    """检查条目是否为会话信息条目"""
    return entry.type == "session_info"


def is_message_with_content(entry: SessionEntry) -> bool:
    """检查条目是否为包含内容的消息条目"""
    if not is_session_message_entry(entry):
        return False
    # 安全访问 message 属性
    try:
        msg = getattr(entry, "message", None)
        if msg is None:
            return False
        return hasattr(msg, "content") and hasattr(msg, "role")
    except AttributeError:
        return False


# ============================================================================
# 辅助函数
# ============================================================================


def get_entry_type_name(entry: SessionEntry) -> str:
    """获取条目类型的中文名称

    Args:
        entry: 会话条目

    Returns:
        条目类型的中文描述
    """
    type_names = {
        "message": "消息",
        "thinking_level_change": "思考级别变更",
        "model_change": "模型变更",
        "compaction": "压缩",
        "branch_summary": "分支摘要",
        "custom": "自定义",
        "custom_message": "自定义消息",
        "label": "标签",
        "session_info": "会话信息",
    }
    return type_names.get(entry.type, f"未知类型({entry.type})")
