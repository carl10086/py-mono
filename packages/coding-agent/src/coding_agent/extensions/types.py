"""扩展类型定义 - 对齐 pi-mono TypeScript 实现（简化版）

提供扩展系统的类型定义，包括：
- 扩展接口
- 扩展上下文
- 工具定义
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


# ============================================================================
# 工具定义
# ============================================================================


@dataclass
class ToolDefinition:
    """工具定义

    扩展可以注册自定义工具。

    属性：
        name: 工具名称
        description: 工具描述
        parameters: JSON Schema 参数定义
        execute: 执行函数
    """

    name: str
    description: str
    parameters: dict[str, Any]
    execute: Callable[..., Any]


# ============================================================================
# 扩展上下文
# ============================================================================


@dataclass
class ExtensionContext:
    """扩展上下文

    提供给扩展的运行时上下文。

    属性：
        cwd: 工作目录
        agent_dir: Agent 目录
        session_manager: 会话管理器
    """

    cwd: str
    agent_dir: str
    session_manager: Any | None = None


# ============================================================================
# 扩展接口
# ============================================================================


class Extension:
    """扩展接口

    所有扩展必须实现此接口。
    """

    id: str
    """扩展唯一标识符"""

    name: str
    """扩展显示名称"""

    version: str
    """扩展版本"""

    def activate(self, context: ExtensionContext) -> None:
        """激活扩展

        Args:
            context: 扩展上下文
        """
        pass

    def deactivate(self) -> None:
        """停用扩展"""
        pass

    def get_tools(self) -> list[ToolDefinition]:
        """获取扩展提供的工具

        Returns:
            工具定义列表
        """
        return []


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "ToolDefinition",
    "ExtensionContext",
    "Extension",
]
