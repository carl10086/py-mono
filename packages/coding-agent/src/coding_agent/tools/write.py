"""文件写入工具。

提供文件内容写入功能，支持自动创建目录。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol

from agent import AgentTool, AgentToolResult
from ai.types import TextContent

from coding_agent.tools.path_utils import resolve_to_cwd

__all__ = [
    "WriteOperations",
    "WriteToolOptions",
    "create_write_tool",
]


class WriteOperations(Protocol):
    """可插拔的文件写入操作。

    用于覆盖默认的文件系统操作，例如远程系统（SSH）。

    """

    async def write_file(self, absolute_path: str, content: str) -> None:
        """将内容写入文件。"""
        ...

    async def mkdir(self, dir_path: str) -> None:
        """创建目录（递归）。"""
        ...


@dataclass
class WriteToolOptions:
    """写入工具选项。

    Attributes:
        operations: 自定义文件写入操作（默认使用本地文件系统）。

    """

    operations: WriteOperations | None = None


class _DefaultWriteOperations:
    """默认的本地文件系统操作。"""

    async def write_file(self, absolute_path: str, content: str) -> None:
        """写入文件内容。"""
        with open(absolute_path, "w", encoding="utf-8") as f:
            f.write(content)

    async def mkdir(self, dir_path: str) -> None:
        """递归创建目录。"""
        os.makedirs(dir_path, exist_ok=True)


def _get_default_operations() -> WriteOperations:
    """获取默认的文件操作实现。"""
    return _DefaultWriteOperations()


class _WriteTool:
    """写入工具实现类。"""

    def __init__(
        self,
        cwd: str,
        operations: WriteOperations,
    ) -> None:
        """初始化写入工具。

        Args:
            cwd: 当前工作目录。
            operations: 文件操作实现。

        """
        self._cwd = cwd
        self._operations = operations

        # AgentTool 协议属性
        self.name = "write"
        self.label = "write"
        self.description = (
            "Write content to a file. Creates the file if it doesn't exist, "
            "overwrites if it does. Automatically creates parent directories."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要写入的文件路径（相对或绝对）",
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容",
                },
            },
            "required": ["path", "content"],
        }

    def _is_cancelled(self, signal: Any | None) -> bool:
        """检查是否已取消."""
        return signal is not None and hasattr(signal, "cancelled") and signal.cancelled

    def _cancelled_result(self, path: str) -> AgentToolResult[None]:
        """返回取消状态的错误结果."""
        return AgentToolResult(
            content=[TextContent(text=f"操作已取消：{path}")],
            is_error=True,
        )

    def _error_result(self, message: str) -> AgentToolResult[None]:
        """返回错误结果."""
        return AgentToolResult(
            content=[TextContent(text=f"写入失败：{message}")],
            is_error=True,
        )

    async def execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any = None,
        on_update: Any = None,
    ) -> AgentToolResult[None]:
        """执行写入操作.

        Args:
            tool_call_id: 工具调用ID。
            params: 参数字典（包含 path, content）。
            signal: 取消信号（可选）。
            on_update: 进度更新回调（可选）。

        Returns:
            工具执行结果。错误时返回 is_error=True 的结果，不抛出异常。

        """
        path = params.get("path", "")
        content = params.get("content", "")

        absolute_path = resolve_to_cwd(path, self._cwd)
        dir_path = os.path.dirname(absolute_path)

        if self._is_cancelled(signal):
            return self._cancelled_result(path)

        try:
            await self._operations.mkdir(dir_path)
        except OSError as e:
            return self._error_result(f"创建目录失败: {e}")

        if self._is_cancelled(signal):
            return self._cancelled_result(path)

        try:
            await self._operations.write_file(absolute_path, content)
        except OSError as e:
            return self._error_result(f"写入文件失败: {e}")

        if self._is_cancelled(signal):
            return self._cancelled_result(path)

        return AgentToolResult(
            content=[TextContent(text=f"成功写入 {len(content)} 字节到 {path}")],
            details=None,
        )


def create_write_tool(
    cwd: str,
    options: WriteToolOptions | None = None,
) -> AgentTool:
    """创建文件写入工具。

    Args:
        cwd: 当前工作目录，用于解析相对路径。
        options: 工具选项（可选）。

    Returns:
        文件写入工具实例。

    Example:
        >>> tool = create_write_tool("/home/user/project")
        >>> result = await tool.execute("call_1", {"path": "output.txt", "content": "Hello"})

    """
    operations = options.operations if options and options.operations else _get_default_operations()

    return _WriteTool(
        cwd=cwd,
        operations=operations,
    )
