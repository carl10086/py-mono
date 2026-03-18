"""
自定义消息类型示例 - 演示 CustomMessage 的使用方法。

本示例展示如何：
1. 定义自定义消息类型（实现 CustomMessage 协议）
2. 实现 convert_to_llm 函数处理自定义消息
3. 在 Agent 中使用自定义消息

与 pi-mono 的 coding-agent 自定义消息对齐。
"""

from __future__ import annotations

from dataclasses import dataclass

from ai.types import Message, TextContent, UserMessage
from agent import AgentMessage


# ============================================================================
# 1. 定义自定义消息类型
# ============================================================================


@dataclass
class BashExecutionMessage:
    """
    Bash 命令执行消息 - 对应 pi-mono 的 BashExecutionMessage。

    用于在对话历史中记录 Bash 命令执行结果，在 TUI 中显示。
    """

    role: str = "bash_execution"
    command: str = ""
    output: str = ""
    exit_code: int | None = None
    timestamp: int = 0


@dataclass
class ProgressMessage:
    """
    进度通知消息 - 用于显示长时间任务的进度。

    此类消息通常不发送给 LLM，仅用于 UI 展示。
    """

    role: str = "progress"
    task_id: str = ""
    percent: int = 0
    status: str = "running"  # "running" | "completed" | "error"
    description: str = ""
    timestamp: int = 0


# ============================================================================
# 2. 实现 convert_to_llm 函数
# ============================================================================


def is_standard_role(role: str) -> bool:
    """检查是否为标准 LLM 消息角色。"""
    return role in ("user", "assistant", "toolResult")


def is_bash_message(msg: AgentMessage) -> bool:
    """检查是否为 Bash 执行消息。"""
    return getattr(msg, "role", None) == "bash_execution"


def is_progress_message(msg: AgentMessage) -> bool:
    """检查是否为进度消息。"""
    return getattr(msg, "role", None) == "progress"


def convert_bash_to_llm(msg: BashExecutionMessage) -> Message:
    """将 Bash 执行消息转换为 LLM 消息。"""
    text = f"执行命令: `{msg.command}`\n```\n{msg.output}\n```"

    if msg.exit_code is not None and msg.exit_code != 0:
        text += f"\n退出码: {msg.exit_code}"

    return UserMessage(content=[TextContent(text=text)])


async def example_convert_to_llm(messages: list[AgentMessage]) -> list[Message]:
    """
    示例消息转换函数。

    处理流程：
    1. 标准消息直接通过
    2. Bash 执行消息转换为 UserMessage
    3. 进度消息跳过（不发送给 LLM）
    4. 未知类型记录警告并跳过
    """
    result: list[Message] = []

    for msg in messages:
        role = getattr(msg, "role", "unknown")

        # 标准消息直接通过（使用类型断言）
        if is_standard_role(role):
            result.append(msg)  # type: ignore[arg-type]
            continue

        # Bash 执行消息：转换为 LLM 格式
        if is_bash_message(msg):
            bash_msg = msg  # type: ignore
            result.append(convert_bash_to_llm(bash_msg))
            continue

        # 进度消息：跳过（UI 专用，不发送给 LLM）
        if is_progress_message(msg):
            continue

        # 未知类型：记录警告
        print(f"[Example] 警告: 未知的自定义消息类型 '{role}'")

    return result


# ============================================================================
# 1. 定义自定义消息类型
# ============================================================================


@dataclass
class BashExecutionMessage:
    """
    Bash 命令执行消息 - 对应 pi-mono 的 BashExecutionMessage。

    用于在对话历史中记录 Bash 命令执行结果，在 TUI 中显示。
    """

    role: str = "bash_execution"
    command: str = ""
    output: str = ""
    exit_code: int | None = None
    timestamp: int = 0


@dataclass
class ProgressMessage:
    """
    进度通知消息 - 用于显示长时间任务的进度。

    此类消息通常不发送给 LLM，仅用于 UI 展示。
    """

    role: str = "progress"
    task_id: str = ""
    percent: int = 0
    status: str = "running"  # "running" | "completed" | "error"
    description: str = ""
    timestamp: int = 0


# ============================================================================
# 2. 实现 convert_to_llm 函数
# ============================================================================


def is_standard_role(role: str) -> bool:
    """检查是否为标准 LLM 消息角色。"""
    return role in ("user", "assistant", "toolResult")


def is_bash_message(msg: AgentMessage) -> bool:
    """检查是否为 Bash 执行消息。"""
    return getattr(msg, "role", None) == "bash_execution"


def is_progress_message(msg: AgentMessage) -> bool:
    """检查是否为进度消息。"""
    return getattr(msg, "role", None) == "progress"


def convert_bash_to_llm(msg: BashExecutionMessage) -> Message:
    """将 Bash 执行消息转换为 LLM 消息。"""
    text = f"执行命令: `{msg.command}`\n```\n{msg.output}\n```"

    if msg.exit_code is not None and msg.exit_code != 0:
        text += f"\n退出码: {msg.exit_code}"

    return UserMessage(content=[TextContent(text=text)])


async def example_convert_to_llm(messages: list[AgentMessage]) -> list[Message]:
    """
    示例消息转换函数。

    处理流程：
    1. 标准消息直接通过
    2. Bash 执行消息转换为 UserMessage
    3. 进度消息跳过（不发送给 LLM）
    4. 未知类型记录警告并跳过
    """
    result: list[Message] = []

    for msg in messages:
        role = getattr(msg, "role", "unknown")

        # 标准消息直接通过（使用类型断言）
        if is_standard_role(role):
            result.append(msg)  # type: ignore[arg-type]
            continue

        # Bash 执行消息：转换为 LLM 格式
        if is_bash_message(msg):
            bash_msg = msg  # type: ignore
            result.append(convert_bash_to_llm(bash_msg))
            continue

        # 进度消息：跳过（UI 专用，不发送给 LLM）
        if is_progress_message(msg):
            continue

        # 未知类型：记录警告
        print(f"[Example] 警告: 未知的自定义消息类型 '{role}'")

    return result


# ============================================================================
# 3. 使用自定义消息
# ============================================================================


async def main() -> None:
    """
    主函数 - 演示自定义消息的完整使用流程。
    """
    # 创建自定义消息
    bash_msg = BashExecutionMessage(
        command="ls -la",
        output="file1.txt\nfile2.txt",
        exit_code=0,
        timestamp=1234567890,
    )

    progress_msg = ProgressMessage(
        task_id="upload",
        percent=50,
        status="running",
        description="Uploading file...",
        timestamp=1234567890,
    )

    # 创建标准用户消息
    user_msg = UserMessage(content=[TextContent(text="请帮我分析这些文件")])

    # 混合消息列表
    messages: list[AgentMessage] = [bash_msg, progress_msg, user_msg]

    # 转换消息
    print("原始消息:")
    for msg in messages:
        role = getattr(msg, "role", "unknown")
        print(f"  - {role}")

    converted = await example_convert_to_llm(messages)

    print(f"\n转换后消息（共 {len(converted)} 条）:")
    for msg in converted:
        print(f"  - {msg.role}: {msg.content[0].text[:30]}...")

    # 创建 Agent 时使用自定义转换器
    # agent = Agent(convert_to_llm=example_convert_to_llm)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
