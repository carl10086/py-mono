"""消息类型和转换器 - 对齐 pi-mono TypeScript 实现

扩展 AgentMessage 类型，添加 coding-agent 特定的消息类型，
并提供转换器将它们转换为 LLM 兼容的消息格式。
"""

from __future__ import annotations

from typing import Any, TypeAlias

from ai.types import ImageContent, TextContent
from agent.types import AgentMessage

# ============================================================================
# 常量
# ============================================================================

COMPACTION_SUMMARY_PREFIX = """The conversation history before this point was compacted into the following summary:

<summary>
"""

COMPACTION_SUMMARY_SUFFIX = """
</summary>"""

BRANCH_SUMMARY_PREFIX = """The following is a summary of a branch that this conversation came back from:

<summary>
"""

BRANCH_SUMMARY_SUFFIX = "</summary>"


# ============================================================================
# 消息类型
# ============================================================================


class BashExecutionMessage:
    """Bash 执行消息类型（通过 ! 命令执行）

    属性：
        role: 固定为 "bashExecution"
        command: 执行的命令
        output: 输出内容
        exit_code: 退出码（undefined 表示被终止/取消）
        cancelled: 是否被取消
        truncated: 是否被截断
        full_output_path: 完整输出文件路径（如果被截断）
        timestamp: Unix 时间戳（毫秒）
        exclude_from_context: 是否从 LLM 上下文中排除（!! 前缀）
    """

    def __init__(
        self,
        command: str,
        output: str,
        exit_code: int | None = None,
        cancelled: bool = False,
        truncated: bool = False,
        full_output_path: str | None = None,
        timestamp: int | None = None,
        exclude_from_context: bool = False,
    ) -> None:
        self.role: str = "bashExecution"
        self.command = command
        self.output = output
        self.exit_code = exit_code
        self.cancelled = cancelled
        self.truncated = truncated
        self.full_output_path = full_output_path
        self.timestamp = timestamp or 0
        self.exclude_from_context = exclude_from_context


class CustomMessage:
    """自定义消息类型（通过 sendMessage() 注入）

    扩展可以注入的自定义消息。

    属性：
        role: 固定为 "custom"
        custom_type: 自定义类型标识符
        content: 内容（字符串或内容块数组）
        display: 是否在 TUI 中显示
        details: 扩展元数据
        timestamp: Unix 时间戳（毫秒）
    """

    def __init__(
        self,
        custom_type: str,
        content: str | list[TextContent | ImageContent],
        display: bool,
        details: Any | None = None,
        timestamp: int | None = None,
    ) -> None:
        self.role: str = "custom"
        self.custom_type = custom_type
        self.content = content
        self.display = display
        self.details = details
        self.timestamp = timestamp or 0


class BranchSummaryMessage:
    """分支摘要消息类型

    属性：
        role: 固定为 "branchSummary"
        summary: 摘要文本
        from_id: 分支起始 ID
        timestamp: Unix 时间戳（毫秒）
    """

    def __init__(
        self,
        summary: str,
        from_id: str,
        timestamp: int | None = None,
    ) -> None:
        self.role: str = "branchSummary"
        self.summary = summary
        self.from_id = from_id
        self.timestamp = timestamp or 0


class CompactionSummaryMessage:
    """压缩摘要消息类型

    属性：
        role: 固定为 "compactionSummary"
        summary: 摘要文本
        tokens_before: 压缩前的 token 数量
        timestamp: Unix 时间戳（毫秒）
    """

    def __init__(
        self,
        summary: str,
        tokens_before: int,
        timestamp: int | None = None,
    ) -> None:
        self.role: str = "compactionSummary"
        self.summary = summary
        self.tokens_before = tokens_before
        self.timestamp = timestamp or 0


# ============================================================================
# 类型联合
# ============================================================================

ExtendedMessage: TypeAlias = (
    AgentMessage
    | BashExecutionMessage
    | CustomMessage
    | BranchSummaryMessage
    | CompactionSummaryMessage
)


# ============================================================================
# 转换函数
# ============================================================================


def bash_execution_to_text(msg: BashExecutionMessage) -> str:
    """将 BashExecutionMessage 转换为用户消息文本

    Args:
        msg: Bash 执行消息

    Returns:
        格式化的文本表示
    """
    text = f"Ran `{msg.command}`\n"
    if msg.output:
        text += f"```\n{msg.output}\n```"
    else:
        text += "(no output)"

    if msg.cancelled:
        text += "\n\n(command cancelled)"
    elif msg.exit_code is not None and msg.exit_code != 0:
        text += f"\n\nCommand exited with code {msg.exit_code}"

    if msg.truncated and msg.full_output_path:
        text += f"\n\n[Output truncated. Full output: {msg.full_output_path}]"

    return text


def create_branch_summary_message(
    summary: str,
    from_id: str,
    timestamp: str,
) -> BranchSummaryMessage:
    """创建分支摘要消息

    Args:
        summary: 摘要文本
        from_id: 分支起始 ID
        timestamp: ISO 8601 时间戳字符串

    Returns:
        BranchSummaryMessage 实例
    """
    from datetime import datetime

    ts = int(datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp() * 1000)
    return BranchSummaryMessage(summary, from_id, ts)


def create_compaction_summary_message(
    summary: str,
    tokens_before: int,
    timestamp: str,
) -> CompactionSummaryMessage:
    """创建压缩摘要消息

    Args:
        summary: 摘要文本
        tokens_before: 压缩前的 token 数量
        timestamp: ISO 8601 时间戳字符串

    Returns:
        CompactionSummaryMessage 实例
    """
    from datetime import datetime

    ts = int(datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp() * 1000)
    return CompactionSummaryMessage(summary, tokens_before, ts)


def create_custom_message(
    custom_type: str,
    content: str | list[TextContent | ImageContent],
    display: bool,
    details: Any | None,
    timestamp: str,
) -> CustomMessage:
    """创建自定义消息

    Args:
        custom_type: 自定义类型标识符
        content: 消息内容
        display: 是否在 TUI 中显示
        details: 扩展元数据
        timestamp: ISO 8601 时间戳字符串

    Returns:
        CustomMessage 实例
    """
    from datetime import datetime

    ts = int(datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp() * 1000)
    return CustomMessage(custom_type, content, display, details, ts)


# ============================================================================
# LLM 转换函数
# ============================================================================


def convert_to_llm(messages: list[Any]) -> list[dict[str, Any]]:
    """将 AgentMessage（包括自定义类型）转换为 LLM 兼容的消息

    被以下模块使用：
    - Agent 的 transform_to_llm 选项（用于 prompt 调用和队列消息）
    - Compaction 的 generate_summary（用于摘要）
    - 自定义扩展和工具

    Args:
        messages: AgentMessage 列表（可能包含自定义类型）

    Returns:
        LLM 兼容的消息列表
    """
    result: list[dict[str, Any] | None] = []

    for msg in messages:
        role = getattr(msg, "role", None)

        if role == "bashExecution":
            # 跳过从上下文中排除的消息（!! 前缀）
            if getattr(msg, "exclude_from_context", False):
                result.append(None)
                continue
            result.append(
                {
                    "role": "user",
                    "content": [{"type": "text", "text": bash_execution_to_text(msg)}],
                    "timestamp": msg.timestamp,
                }
            )

        elif role == "custom":
            content = msg.content
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            result.append(
                {
                    "role": "user",
                    "content": content,
                    "timestamp": msg.timestamp,
                }
            )

        elif role == "branchSummary":
            result.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": BRANCH_SUMMARY_PREFIX + msg.summary + BRANCH_SUMMARY_SUFFIX,
                        }
                    ],
                    "timestamp": msg.timestamp,
                }
            )

        elif role == "compactionSummary":
            result.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": COMPACTION_SUMMARY_PREFIX
                            + msg.summary
                            + COMPACTION_SUMMARY_SUFFIX,
                        }
                    ],
                    "timestamp": msg.timestamp,
                }
            )

        elif role in ("user", "assistant", "toolResult"):
            # 标准消息类型直接返回
            result.append(msg.model_dump() if hasattr(msg, "model_dump") else msg)

        else:
            # 未知类型，跳过
            result.append(None)

    # 过滤掉 None
    return [m for m in result if m is not None]


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 常量
    "COMPACTION_SUMMARY_PREFIX",
    "COMPACTION_SUMMARY_SUFFIX",
    "BRANCH_SUMMARY_PREFIX",
    "BRANCH_SUMMARY_SUFFIX",
    # 消息类型
    "BashExecutionMessage",
    "CustomMessage",
    "BranchSummaryMessage",
    "CompactionSummaryMessage",
    # 类型联合
    "ExtendedMessage",
    # 转换函数
    "bash_execution_to_text",
    "create_branch_summary_message",
    "create_compaction_summary_message",
    "create_custom_message",
    "convert_to_llm",
]
