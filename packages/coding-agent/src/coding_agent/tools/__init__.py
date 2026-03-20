"""工具集模块。

提供代码编辑工具：read, write, edit, bash, grep, find, ls
"""

from __future__ import annotations

from typing import Any

from coding_agent.tools.bash import (
    BashOperations,
    BashSpawnContext,
    BashSpawnHook,
    BashToolDetails,
    BashToolOptions,
    create_bash_tool,
    create_local_bash_operations,
)
from coding_agent.tools.edit import create_edit_tool
from coding_agent.tools.find import FindToolDetails, create_find_tool
from coding_agent.tools.grep import GrepToolDetails, create_grep_tool
from coding_agent.tools.ls import LsToolDetails, create_ls_tool
from coding_agent.tools.path_utils import (
    is_path_inside,
    normalize_path,
    resolve_to_cwd,
    validate_path,
)
from coding_agent.tools.read import ReadToolDetails, create_read_tool
from coding_agent.tools.truncate import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    GREP_MAX_LINE_LENGTH,
    TruncationResult,
    format_size,
    truncate_head,
    truncate_line,
    truncate_tail,
)
from coding_agent.tools.write import create_write_tool

__all__ = [
    # 主要工具
    "create_read_tool",
    "create_write_tool",
    "create_edit_tool",
    "create_bash_tool",
    "create_grep_tool",
    "create_find_tool",
    "create_ls_tool",
    # 工具详情类
    "ReadToolDetails",
    "BashToolDetails",
    "GrepToolDetails",
    "FindToolDetails",
    "LsToolDetails",
    # Bash 扩展
    "BashOperations",
    "BashSpawnContext",
    "BashSpawnHook",
    "BashToolOptions",
    "create_local_bash_operations",
    # 路径工具
    "is_path_inside",
    "normalize_path",
    "resolve_to_cwd",
    "validate_path",
    # 截断工具
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_LINES",
    "GREP_MAX_LINE_LENGTH",
    "TruncationResult",
    "format_size",
    "truncate_head",
    "truncate_tail",
    "truncate_line",
    # 便捷函数
    "create_tool_set",
]


def create_tool_set(cwd: str) -> dict[str, Any]:
    """创建完整的工具集合。

    Args:
        cwd: 工作目录，所有工具将在此目录下操作。

    Returns:
        工具名字典，包含所有 Phase 1 工具。

    """
    return {
        "read": create_read_tool(cwd),
        "write": create_write_tool(cwd),
        "edit": create_edit_tool(cwd),
        "bash": create_bash_tool(cwd),
        "grep": create_grep_tool(cwd),
        "find": create_find_tool(cwd),
        "ls": create_ls_tool(cwd),
    }
