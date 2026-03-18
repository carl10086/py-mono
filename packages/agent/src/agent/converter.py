"""
消息转换器模块 - 提供默认的消息转换实现。

与 pi-mono 的 convertToLlm 对齐，处理 AgentMessage 到 LLM Message 的转换。
支持自定义消息的过滤和转换。
"""

from collections.abc import Sequence

from ai.types import Message

from agent.types import AgentMessage


def is_standard_role(role: str) -> bool:
    """
    检查角色是否为标准 LLM 消息角色。

    标准消息角色包括：user、assistant、toolResult。

    参数：
        role: 待检查的角色字符串

    返回：
        True 如果是标准角色，否则 False
    """
    return role in ("user", "assistant", "toolResult")


def get_message_role(msg: AgentMessage) -> str:
    """
    安全获取消息的角色字段。

    参数：
        msg: 消息对象

    返回：
        角色字符串，无法获取时返回 "unknown"
    """
    return getattr(msg, "role", "unknown")


async def strict_convert_to_llm(
    messages: Sequence[AgentMessage],
) -> Sequence[Message]:
    """
    严格模式转换器。

    只接受标准 LLM 消息，拒绝所有自定义消息。
    用于不提供自定义 convert_to_llm 的场景。

    参数：
        messages: 混合类型的消息序列

    返回：
        仅包含标准消息的序列

    示例：
        >>> messages = [user_msg, custom_msg, assistant_msg]
        >>> result = await strict_convert_to_llm(messages)
        >>> # result 只包含 user_msg 和 assistant_msg
    """
    result: list[Message] = []

    for msg in messages:
        role = get_message_role(msg)
        if is_standard_role(role):
            # 使用类型断言，因为此时 msg 确实是 Message 类型
            result.append(msg)  # type: ignore[arg-type]
            continue

        print(f"[Agent] 警告: 忽略非标准消息类型 '{role}'")

    return result
