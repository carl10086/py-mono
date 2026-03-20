"""压缩和分支摘要的共享工具函数 - 对齐 pi-mono TypeScript 实现

提供文件操作追踪、消息序列化、摘要系统提示等功能。
"""

from __future__ import annotations

from typing import Any

# ============================================================================
# 文件操作追踪
# ============================================================================


class FileOperations:
    """文件操作追踪器"""

    def __init__(self) -> None:
        """初始化文件操作追踪器"""
        self.read: set[str] = set()
        self.written: set[str] = set()
        self.edited: set[str] = set()


def create_file_ops() -> FileOperations:
    """创建新的文件操作追踪器

    Returns:
        FileOperations 实例
    """
    return FileOperations()


def extract_file_ops_from_message(message: Any, file_ops: FileOperations) -> None:
    """从助手消息的工具调用中提取文件操作

    Args:
        message: AgentMessage
        file_ops: FileOperations 实例（会被修改）
    """
    if getattr(message, "role", None) != "assistant":
        return

    content = getattr(message, "content", None)
    if not content or not isinstance(content, list):
        return

    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "toolCall":
            continue

        args = block.get("arguments", {})
        if not isinstance(args, dict):
            continue

        path = args.get("path")
        if not isinstance(path, str):
            continue

        tool_name = block.get("name")
        if tool_name == "read":
            file_ops.read.add(path)
        elif tool_name == "write":
            file_ops.written.add(path)
        elif tool_name == "edit":
            file_ops.edited.add(path)


def compute_file_lists(file_ops: FileOperations) -> tuple[list[str], list[str]]:
    """计算最终文件列表

    Returns:
        (read_files, modified_files) 元组
        - read_files: 只读的文件（未被修改）
        - modified_files: 被修改的文件
    """
    modified = set(file_ops.edited) | set(file_ops.written)
    read_only = [f for f in file_ops.read if f not in modified]
    modified_files = list(modified)
    return sorted(read_only), sorted(modified_files)


def format_file_operations(read_files: list[str], modified_files: list[str]) -> str:
    """将文件操作格式化为 XML 标签

    Args:
        read_files: 只读文件列表
        modified_files: 修改的文件列表

    Returns:
        格式化的 XML 字符串
    """
    sections: list[str] = []

    if read_files:
        sections.append(f"<read-files>\n{'\n'.join(read_files)}\n</read-files>")

    if modified_files:
        sections.append(f"<modified-files>\n{'\n'.join(modified_files)}\n</modified-files>")

    if not sections:
        return ""

    return f"\n\n{'\n\n'.join(sections)}"


# ============================================================================
# 消息序列化
# ============================================================================

TOOL_RESULT_MAX_CHARS = 2000
"""工具结果在序列化摘要中的最大字符数"""


def _truncate_for_summary(text: str, max_chars: int) -> str:
    """截断文本用于摘要

    Args:
        text: 原始文本
        max_chars: 最大字符数

    Returns:
        截断后的文本
    """
    if len(text) <= max_chars:
        return text
    truncated_chars = len(text) - max_chars
    return f"{text[:max_chars]}\n\n[... {truncated_chars} more characters truncated]"


def serialize_conversation(messages: list[dict[str, Any]]) -> str:
    """将 LLM 消息序列化为文本用于摘要

    这防止模型将其视为要继续的对话。
    先调用 convert_to_llm() 处理自定义消息类型。

    Args:
        messages: LLM 消息列表

    Returns:
        序列化后的文本
    """
    parts: list[str] = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")

        if role == "user":
            text = content if isinstance(content, str) else ""
            if isinstance(content, list):
                text_parts = [
                    c.get("text", "")
                    for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                ]
                text = "".join(text_parts)
            if text:
                parts.append(f"[User]: {text}")

        elif role == "assistant":
            text_parts: list[str] = []
            thinking_parts: list[str] = []
            tool_calls: list[str] = []

            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    block_type = block.get("type")
                    if block_type == "text":
                        text_parts.append(block.get("text", ""))
                    elif block_type == "thinking":
                        thinking_parts.append(block.get("thinking", ""))
                    elif block_type == "toolCall":
                        args = block.get("arguments", {})
                        args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                        tool_calls.append(f"{block.get('name')}({args_str})")

            if thinking_parts:
                parts.append(f"[Assistant thinking]: {'\n'.join(thinking_parts)}")
            if text_parts:
                parts.append(f"[Assistant]: {'\n'.join(text_parts)}")
            if tool_calls:
                parts.append(f"[Assistant tool calls]: {'; '.join(tool_calls)}")

        elif role == "toolResult":
            text = ""
            if isinstance(content, list):
                text_parts = [
                    c.get("text", "")
                    for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                ]
                text = "".join(text_parts)
            if text:
                truncated = _truncate_for_summary(text, TOOL_RESULT_MAX_CHARS)
                parts.append(f"[Tool result]: {truncated}")

    return "\n\n".join(parts)


# ============================================================================
# 摘要系统提示
# ============================================================================

SUMMARIZATION_SYSTEM_PROMPT = """You are a context summarization assistant. Your task is to read a conversation between a user and an AI coding assistant, then produce a structured summary following the exact format specified.

Do NOT continue the conversation. Do NOT respond to any questions in the conversation. ONLY output the structured summary."""


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "FileOperations",
    "create_file_ops",
    "extract_file_ops_from_message",
    "compute_file_lists",
    "format_file_operations",
    "TOOL_RESULT_MAX_CHARS",
    "serialize_conversation",
    "SUMMARIZATION_SYSTEM_PROMPT",
]
