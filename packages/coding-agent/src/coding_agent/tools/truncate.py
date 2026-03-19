"""内容截断工具。

提供文本内容截断功能，用于处理大文件和输出。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = [
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_LINES",
    "TruncationResult",
    "format_size",
    "truncate_head",
    "truncate_tail",
    "truncate_line",
]

DEFAULT_MAX_LINES = 2000
DEFAULT_MAX_BYTES = 50 * 1024


@dataclass
class TruncationResult:
    """截断结果。

    Attributes:
        content: 截断后的内容。
        truncated: 是否发生了截断。
        truncated_by: 哪种限制导致截断："lines" | "bytes" | None。
        total_lines: 原始内容的总行数。
        total_bytes: 原始内容的总字节数。
        output_lines: 截断输出的总行数。
        output_bytes: 截断输出的字节数。
        last_line_partial: 最后一行是否被部分截断（仅适用于尾部截断）。
        first_line_exceeds_limit: 第一行是否超出字节限制（仅适用于头部截断）。
        max_lines: 应用的行数限制。
        max_bytes: 应用的字节数限制。

    """

    content: str
    truncated: bool
    truncated_by: Literal["lines", "bytes"] | None
    total_lines: int
    total_bytes: int
    output_lines: int
    output_bytes: int
    last_line_partial: bool
    first_line_exceeds_limit: bool
    max_lines: int
    max_bytes: int


def format_size(bytes_count: int) -> str:
    """格式化字节大小为可读字符串。

    Args:
        bytes_count: 字节数。

    Returns:
        格式化后的字符串（如 "1.5KB"）。

    """
    if bytes_count < 1024:
        return f"{bytes_count}B"
    elif bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f}KB"
    else:
        return f"{bytes_count / (1024 * 1024):.1f}MB"


def _create_no_truncation_result(
    content: str,
    total_lines: int,
    total_bytes: int,
    max_lines: int,
    max_bytes: int,
) -> TruncationResult:
    """创建无需截断的结果对象。"""
    return TruncationResult(
        content=content,
        truncated=False,
        truncated_by=None,
        total_lines=total_lines,
        total_bytes=total_bytes,
        output_lines=total_lines,
        output_bytes=total_bytes,
        last_line_partial=False,
        first_line_exceeds_limit=False,
        max_lines=max_lines,
        max_bytes=max_bytes,
    )


def truncate_head(
    content: str,
    max_lines: int = DEFAULT_MAX_LINES,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> TruncationResult:
    """从头部开始截断内容，保留前面的行。

    用于文件读取、搜索结果等场景，保留开头部分。

    Args:
        content: 原始内容。
        max_lines: 最大行数（默认2000）。
        max_bytes: 最大字节数（默认50KB）。

    Returns:
        截断结果对象。

    """
    total_bytes = len(content.encode("utf-8"))
    lines = content.split("\n")
    total_lines = len(lines)

    # 检查是否无需截断
    if total_lines <= max_lines and total_bytes <= max_bytes:
        return _create_no_truncation_result(content, total_lines, total_bytes, max_lines, max_bytes)

    # 检查第一行是否超出字节限制
    first_line_bytes = len(lines[0].encode("utf-8"))
    if first_line_bytes > max_bytes:
        return TruncationResult(
            content="",
            truncated=True,
            truncated_by="bytes",
            total_lines=total_lines,
            total_bytes=total_bytes,
            output_lines=0,
            output_bytes=0,
            last_line_partial=False,
            first_line_exceeds_limit=True,
            max_lines=max_lines,
            max_bytes=max_bytes,
        )

    # 收集能容纳的完整行
    output_lines: list[str] = []
    output_bytes_count = 0
    truncated_by: Literal["lines", "bytes"] = "lines"

    for i, line in enumerate(lines):
        if i >= max_lines:
            break

        line_bytes = len(line.encode("utf-8")) + (1 if i > 0 else 0)

        if output_bytes_count + line_bytes > max_bytes:
            truncated_by = "bytes"
            break

        output_lines.append(line)
        output_bytes_count += line_bytes

    # 确定截断原因
    if len(output_lines) >= max_lines and output_bytes_count <= max_bytes:
        truncated_by = "lines"

    output_content = "\n".join(output_lines)
    final_output_bytes = len(output_content.encode("utf-8"))

    return TruncationResult(
        content=output_content,
        truncated=True,
        truncated_by=truncated_by,
        total_lines=total_lines,
        total_bytes=total_bytes,
        output_lines=len(output_lines),
        output_bytes=final_output_bytes,
        last_line_partial=False,
        first_line_exceeds_limit=False,
        max_lines=max_lines,
        max_bytes=max_bytes,
    )


def _truncate_string_from_end(text: str, max_bytes: int) -> str:
    """从字符串末尾开始截断，保留结尾部分。"""
    if len(text.encode("utf-8")) <= max_bytes:
        return text

    # 从后向前找到合适的截断点
    for i in range(len(text) - 1, -1, -1):
        substring = text[i:]
        if len(substring.encode("utf-8")) <= max_bytes:
            return substring

    return ""


def truncate_tail(
    content: str,
    max_lines: int = DEFAULT_MAX_LINES,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> TruncationResult:
    """从尾部开始截断内容，保留后面的行。

    用于日志、命令输出等场景，保留结尾部分。

    Args:
        content: 原始内容。
        max_lines: 最大行数（默认2000）。
        max_bytes: 最大字节数（默认50KB）。

    Returns:
        截断结果对象。

    """
    total_bytes = len(content.encode("utf-8"))
    lines = content.split("\n")
    total_lines = len(lines)

    # 检查是否无需截断
    if total_lines <= max_lines and total_bytes <= max_bytes:
        return _create_no_truncation_result(content, total_lines, total_bytes, max_lines, max_bytes)

    # 从末尾向前工作
    output_lines: list[str] = []
    output_bytes_count = 0
    truncated_by: Literal["lines", "bytes"] = "lines"
    last_line_partial = False

    for i in range(len(lines) - 1, -1, -1):
        if len(output_lines) >= max_lines:
            break

        line = lines[i]
        line_bytes = len(line.encode("utf-8")) + (1 if output_lines else 0)

        if output_bytes_count + line_bytes > max_bytes:
            truncated_by = "bytes"
            # 特殊情况：如果还没添加任何行且此行超出限制，
            # 取该行的末尾部分（部分截断）
            if not output_lines:
                truncated_line = _truncate_string_from_end(line, max_bytes)
                output_lines.insert(0, truncated_line)
                output_bytes_count = len(truncated_line.encode("utf-8"))
                last_line_partial = True
            break

        output_lines.insert(0, line)
        output_bytes_count += line_bytes

    # 确定截断原因
    if len(output_lines) >= max_lines and output_bytes_count <= max_bytes:
        truncated_by = "lines"

    output_content = "\n".join(output_lines)
    final_output_bytes = len(output_content.encode("utf-8"))

    return TruncationResult(
        content=output_content,
        truncated=True,
        truncated_by=truncated_by,
        total_lines=total_lines,
        total_bytes=total_bytes,
        output_lines=len(output_lines),
        output_bytes=final_output_bytes,
        last_line_partial=last_line_partial,
        first_line_exceeds_limit=False,
        max_lines=max_lines,
        max_bytes=max_bytes,
    )


def truncate_line(
    line: str,
    max_chars: int = 500,
) -> tuple[str, bool]:
    """截断单行文本。

    Args:
        line: 原始行文本。
        max_chars: 最大字符数（默认500）。

    Returns:
        (截断后的文本, 是否被截断)。

    """
    if len(line) <= max_chars:
        return line, False

    truncated = f"{line[:max_chars]}... [截断]"
    return truncated, True
