"""文件读取工具。

提供文件内容读取功能，支持文本文件和图像文件。
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Any, Protocol

from agent import AgentTool, AgentToolResult
from ai.types import ImageContent, TextContent

from coding_agent.tools.path_utils import resolve_to_cwd
from coding_agent.tools.truncate import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    TruncationResult,
    format_size,
    truncate_head,
)

__all__ = [
    "ReadOperations",
    "ReadToolOptions",
    "ReadToolDetails",
    "create_read_tool",
]


class ReadOperations(Protocol):
    """可插拔的文件读取操作。

    用于覆盖默认的文件系统操作，例如远程系统（SSH）。

    """

    async def read_file(self, absolute_path: str) -> bytes:
        """读取文件内容为字节数组。"""
        ...

    async def access(self, absolute_path: str) -> None:
        """检查文件是否可读（不可读时抛出异常）。"""
        ...

    async def detect_image_mime_type(self, absolute_path: str) -> str | None:
        """检测图像MIME类型，非图像文件返回None。"""
        ...


@dataclass
class ReadToolDetails:
    """读取工具的详细结果信息。

    Attributes:
        truncation: 截断结果信息（如果发生截断）。

    """

    truncation: TruncationResult | None = None


@dataclass
class ReadToolOptions:
    """读取工具选项。

    Attributes:
        auto_resize_images: 是否自动调整图像大小（最大2000x2000）。
        operations: 自定义文件读取操作（默认使用本地文件系统）。

    """

    auto_resize_images: bool = True
    operations: ReadOperations | None = None


class _DefaultReadOperations:
    """默认的本地文件系统操作。"""

    async def read_file(self, absolute_path: str) -> bytes:
        """读取文件内容。"""
        with open(absolute_path, "rb") as f:
            return f.read()

    async def access(self, absolute_path: str) -> None:
        """检查文件可读性。"""
        if not os.path.exists(absolute_path):
            raise FileNotFoundError(f"文件不存在: {absolute_path}")
        if not os.access(absolute_path, os.R_OK):
            raise PermissionError(f"无法读取文件: {absolute_path}")

    async def detect_image_mime_type(self, absolute_path: str) -> str | None:
        """检测图像MIME类型。"""
        ext = os.path.splitext(absolute_path)[1].lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        return mime_map.get(ext)


def _get_default_operations() -> ReadOperations:
    """获取默认的文件操作实现。"""
    return _DefaultReadOperations()


def _read_tool_description() -> str:
    """生成读取工具的描述文本。"""
    return (
        f"Read the contents of a file. Supports text files and images "
        f"(jpg, png, gif, webp). Images are sent as attachments. "
        f"For text files, output is truncated to {DEFAULT_MAX_LINES} lines "
        f"or {format_size(DEFAULT_MAX_BYTES)} (whichever is hit first). "
        f"Use offset/limit for large files. When you need the full file, "
        f"continue with offset until complete."
    )


async def _read_text_file(
    content: str,
    path: str,
    offset: int | None,
    limit: int | None,
) -> tuple[list[TextContent | ImageContent], ReadToolDetails]:
    """处理文本文件读取。

    Args:
        content: 文件内容字符串。
        path: 文件路径（用于错误消息）。
        offset: 起始行号（1-indexed）。
        limit: 最大读取行数。

    Returns:
        (内容列表, 详细信息)。

    """
    all_lines = content.split("\n")
    total_file_lines = len(all_lines)

    # 应用offset（1-indexed转0-indexed）
    start_line = max(0, (offset or 1) - 1)
    start_line_display = start_line + 1

    # 检查offset是否超出范围
    if start_line >= len(all_lines):
        raise ValueError(f"Offset {offset} 超出文件范围（文件共 {len(all_lines)} 行）")

    # 如果指定了limit，使用limit；否则让truncate_head决定
    selected_content: str
    user_limited_lines: int | None = None
    if limit is not None:
        end_line = min(start_line + limit, len(all_lines))
        selected_content = "\n".join(all_lines[start_line:end_line])
        user_limited_lines = end_line - start_line
    else:
        selected_content = "\n".join(all_lines[start_line:])

    # 应用截断（同时考虑行数和字节数限制）
    truncation = truncate_head(selected_content)

    output_text: str
    details = ReadToolDetails(truncation=truncation)

    if truncation.first_line_exceeds_limit:
        # 第一行超过30KB - 提示使用bash命令
        first_line_size = format_size(len(all_lines[start_line].encode("utf-8")))
        output_text = (
            f"[Line {start_line_display} 大小为 {first_line_size}，"
            f"超过 {format_size(DEFAULT_MAX_BYTES)} 限制。"
            f"使用 bash: sed -n '{start_line_display}p' {path} | "
            f"head -c {DEFAULT_MAX_BYTES}]"
        )
    elif truncation.truncated:
        # 发生截断 - 构建可操作的提示
        end_line_display = start_line_display + truncation.output_lines - 1
        next_offset = end_line_display + 1

        output_text = truncation.content

        if truncation.truncated_by == "lines":
            output_text += (
                f"\n\n[显示第 {start_line_display}-{end_line_display} 行，"
                f"共 {total_file_lines} 行。使用 offset={next_offset} 继续。]"
            )
        else:
            output_text += (
                f"\n\n[显示第 {start_line_display}-{end_line_display} 行，"
                f"共 {total_file_lines} 行（{format_size(DEFAULT_MAX_BYTES)} "
                f"限制）。使用 offset={next_offset} 继续。]"
            )
    elif user_limited_lines is not None and start_line + user_limited_lines < len(all_lines):
        # 用户指定了limit，还有更多内容，但没有触发截断
        remaining = len(all_lines) - (start_line + user_limited_lines)
        next_offset = start_line + user_limited_lines + 1

        output_text = truncation.content
        output_text += f"\n\n[文件还有 {remaining} 行。使用 offset={next_offset} 继续。]"
    else:
        # 无截断，未超出用户限制
        output_text = truncation.content
        details = ReadToolDetails(truncation=None)

    return [TextContent(type="text", text=output_text)], details


async def _read_image_file(
    data: bytes,
    mime_type: str,
    auto_resize: bool,
) -> list[TextContent | ImageContent]:
    """处理图像文件读取。

    Args:
        data: 图像字节数据。
        mime_type: MIME类型。
        auto_resize: 是否自动调整大小。

    Returns:
        内容列表。

    """
    base64_data = base64.b64encode(data).decode("utf-8")

    # 注：图像调整大小功能待实现，目前直接返回原图
    text_note = f"读取图像文件 [{mime_type}]"

    return [
        TextContent(type="text", text=text_note),
        ImageContent(type="image", data=base64_data, mime_type=mime_type),
    ]


class _ReadTool:
    """读取工具实现类。"""

    def __init__(
        self,
        cwd: str,
        auto_resize_images: bool,
        operations: ReadOperations,
    ) -> None:
        """初始化读取工具。

        Args:
            cwd: 当前工作目录。
            auto_resize_images: 是否自动调整图像大小。
            operations: 文件操作实现。

        """
        self._cwd = cwd
        self._auto_resize_images = auto_resize_images
        self._operations = operations

        # AgentTool 协议属性
        self.name = "read"
        self.label = "read"
        self.description = _read_tool_description()
        self.parameters = {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要读取的文件路径（相对或绝对）",
                },
                "offset": {
                    "type": "integer",
                    "description": "起始行号（1-indexed，可选）",
                },
                "limit": {
                    "type": "integer",
                    "description": "最大读取行数（可选）",
                },
            },
            "required": ["path"],
        }

    async def execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any = None,
        on_update: Any = None,
    ) -> AgentToolResult[ReadToolDetails]:
        """执行读取操作。

        Args:
            tool_call_id: 工具调用ID。
            params: 参数字典（包含 path, offset, limit）。
            signal: 取消信号（可选）。
            on_update: 进度更新回调（可选）。

        Returns:
            工具执行结果。

        """
        path = params.get("path", "")
        offset = params.get("offset")
        limit = params.get("limit")

        # 解析绝对路径
        absolute_path = resolve_to_cwd(path, self._cwd)

        # 检查是否已取消
        if signal is not None and hasattr(signal, "cancelled") and signal.cancelled:
            raise RuntimeError("操作已取消")

        # 检查文件可访问性
        await self._operations.access(absolute_path)

        # 再次检查取消状态
        if signal is not None and hasattr(signal, "cancelled") and signal.cancelled:
            raise RuntimeError("操作已取消")

        # 检测文件类型
        mime_type = await self._operations.detect_image_mime_type(absolute_path)

        # 读取文件
        data = await self._operations.read_file(absolute_path)

        # 根据类型处理
        if mime_type:
            # 图像文件
            content = await _read_image_file(data, mime_type, self._auto_resize_images)
            details = ReadToolDetails(truncation=None)
        else:
            # 文本文件
            text_content = data.decode("utf-8")
            content, details = await _read_text_file(text_content, path, offset, limit)

        return AgentToolResult(content=content, details=details)


def create_read_tool(
    cwd: str,
    options: ReadToolOptions | None = None,
) -> AgentTool:
    """创建文件读取工具。

    Args:
        cwd: 当前工作目录，用于解析相对路径。
        options: 工具选项（可选）。

    Returns:
        文件读取工具实例。

    Example:
        >>> tool = create_read_tool("/home/user/project")
        >>> result = await tool.execute("call_1", {"path": "main.py"})

    """
    auto_resize = options.auto_resize_images if options else True
    operations = options.operations if options and options.operations else _get_default_operations()

    return _ReadTool(
        cwd=cwd,
        auto_resize_images=auto_resize,
        operations=operations,
    )
