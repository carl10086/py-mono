"""文件编辑工具。

提供基于字符串替换的文件编辑功能，支持模糊匹配和差异显示。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol

from agent import AgentTool, AgentToolResult
from ai.types import TextContent

from coding_agent.tools.edit_diff import (
    detect_line_ending,
    fuzzy_find_text,
    generate_diff_string,
    normalize_for_fuzzy_match,
    normalize_to_lf,
    restore_line_endings,
    strip_bom,
)
from coding_agent.tools.path_utils import resolve_to_cwd

__all__ = [
    "EditOperations",
    "EditToolOptions",
    "EditToolDetails",
    "create_edit_tool",
]


class EditOperations(Protocol):
    """可插拔的文件编辑操作。

    用于覆盖默认的文件系统操作，例如远程系统（SSH）。

    """

    async def read_file(self, absolute_path: str) -> bytes:
        """读取文件内容为字节数组。"""
        ...

    async def write_file(self, absolute_path: str, content: str) -> None:
        """将内容写入文件。"""
        ...

    async def access(self, absolute_path: str) -> None:
        """检查文件是否可读可写（不可读写时抛出异常）。"""
        ...


@dataclass
class EditToolDetails:
    """编辑工具的详细结果信息。

    Attributes:
        diff: 变更的统一差异格式。
        first_changed_line: 新文件中第一个变更的行号（用于编辑器导航）。

    """

    diff: str
    first_changed_line: int | None = None


@dataclass
class EditToolOptions:
    """编辑工具选项。

    Attributes:
        operations: 自定义文件编辑操作（默认使用本地文件系统）。

    """

    operations: EditOperations | None = None


class _DefaultEditOperations:
    """默认的本地文件系统操作。"""

    async def read_file(self, absolute_path: str) -> bytes:
        """读取文件内容。"""
        with open(absolute_path, "rb") as f:
            return f.read()

    async def write_file(self, absolute_path: str, content: str) -> None:
        """写入文件内容。"""
        with open(absolute_path, "w", encoding="utf-8") as f:
            f.write(content)

    async def access(self, absolute_path: str) -> None:
        """检查文件可访问性。"""
        if not os.path.exists(absolute_path):
            raise FileNotFoundError(f"文件不存在: {absolute_path}")
        if not os.access(absolute_path, os.R_OK | os.W_OK):
            raise PermissionError(f"无法读写文件: {absolute_path}")


def _get_default_operations() -> EditOperations:
    """获取默认的文件操作实现。"""
    return _DefaultEditOperations()


class _EditTool:
    """编辑工具实现类。"""

    def __init__(
        self,
        cwd: str,
        operations: EditOperations,
    ) -> None:
        """初始化编辑工具。

        Args:
            cwd: 当前工作目录。
            operations: 文件操作实现。

        """
        self._cwd = cwd
        self._operations = operations

        # AgentTool 协议属性
        self.name = "edit"
        self.label = "edit"
        self.description = (
            "Edit a file by replacing exact text. The oldText must match exactly "
            "(including whitespace). Use this for precise, surgical edits."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要编辑的文件路径（相对或绝对）",
                },
                "oldText": {
                    "type": "string",
                    "description": "要查找并替换的精确文本（必须完全匹配）",
                },
                "newText": {
                    "type": "string",
                    "description": "替换旧文本的新文本",
                },
            },
            "required": ["path", "oldText", "newText"],
        }

    async def execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any = None,
        on_update: Any = None,
    ) -> AgentToolResult[EditToolDetails]:
        """执行编辑操作。

        Args:
            tool_call_id: 工具调用ID。
            params: 参数字典（包含 path, oldText, newText）。
            signal: 取消信号（可选）。
            on_update: 进度更新回调（可选）。

        Returns:
            工具执行结果。

        """
        path = params.get("path", "")
        old_text = params.get("oldText", "")
        new_text = params.get("newText", "")

        # 解析绝对路径
        absolute_path = resolve_to_cwd(path, self._cwd)

        # 检查是否已取消
        if signal is not None and hasattr(signal, "cancelled") and signal.cancelled:
            raise RuntimeError("操作已取消")

        # 检查文件是否存在
        try:
            await self._operations.access(absolute_path)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"文件不存在: {path}") from e

        # 再次检查取消状态
        if signal is not None and hasattr(signal, "cancelled") and signal.cancelled:
            raise RuntimeError("操作已取消")

        # 读取文件
        buffer = await self._operations.read_file(absolute_path)
        raw_content = buffer.decode("utf-8")

        # 再次检查取消状态
        if signal is not None and hasattr(signal, "cancelled") and signal.cancelled:
            raise RuntimeError("操作已取消")

        # 移除BOM（LLM不会在oldText中包含不可见的BOM）
        bom, content = strip_bom(raw_content)

        # 检测并标准化换行符
        original_ending = detect_line_ending(content)
        normalized_content = normalize_to_lf(content)
        normalized_old_text = normalize_to_lf(old_text)
        normalized_new_text = normalize_to_lf(new_text)

        # 使用模糊匹配查找旧文本（先尝试精确匹配，再尝试模糊匹配）
        match_result = fuzzy_find_text(normalized_content, normalized_old_text)

        if not match_result.found:
            raise ValueError(
                f"无法在 {path} 中找到精确的文本。旧文本必须完全匹配，包括所有空白字符和换行符。"
            )

        # 统计匹配次数
        fuzzy_content = normalize_for_fuzzy_match(normalized_content)
        fuzzy_old_text_normalized = normalize_for_fuzzy_match(normalized_old_text)
        occurrences = fuzzy_content.count(fuzzy_old_text_normalized)

        if occurrences > 1:
            raise ValueError(
                f"在 {path} 中找到了 {occurrences} 处匹配的文本。"
                f"文本必须是唯一的。请提供更多上下文以使其唯一。"
            )

        # 再次检查取消状态
        if signal is not None and hasattr(signal, "cancelled") and signal.cancelled:
            raise RuntimeError("操作已取消")

        # 执行替换
        base_content = match_result.content_for_replacement
        new_content = (
            base_content[: match_result.index]
            + normalized_new_text
            + base_content[match_result.index + match_result.match_length :]
        )

        # 验证替换确实改变了内容
        if base_content == new_content:
            raise ValueError(
                f"未对 {path} 进行任何更改。替换产生了相同的内容。"
                f"这可能表示特殊字符存在问题或文本不如预期存在。"
            )

        # 恢复原始换行符和BOM
        final_content = bom + restore_line_endings(new_content, original_ending)
        await self._operations.write_file(absolute_path, final_content)

        # 再次检查取消状态
        if signal is not None and hasattr(signal, "cancelled") and signal.cancelled:
            raise RuntimeError("操作已取消")

        # 生成差异
        diff_result = generate_diff_string(base_content, new_content)

        return AgentToolResult(
            content=[TextContent(type="text", text=f"成功在 {path} 中替换文本。")],
            details=EditToolDetails(
                diff=diff_result.diff,
                first_changed_line=diff_result.first_changed_line,
            ),
        )


def create_edit_tool(
    cwd: str,
    options: EditToolOptions | None = None,
) -> AgentTool:
    """创建文件编辑工具。

    Args:
        cwd: 当前工作目录，用于解析相对路径。
        options: 工具选项（可选）。

    Returns:
        文件编辑工具实例。

    Example:
        >>> tool = create_edit_tool("/home/user/project")
        >>> result = await tool.execute(
        ...     "call_1",
        ...     {"path": "main.py", "oldText": "foo", "newText": "bar"}
        ... )

    """
    operations = options.operations if options and options.operations else _get_default_operations()

    return _EditTool(
        cwd=cwd,
        operations=operations,
    )
