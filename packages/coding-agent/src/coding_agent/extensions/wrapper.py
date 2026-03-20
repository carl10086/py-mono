"""扩展工具包装器 - 包装扩展工具以集成到 Agent

提供工具包装功能，将扩展提供的工具注册到 Agent。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .types import Extension, ToolDefinition

logger: logging.Logger = logging.getLogger(__name__)

# 存储包装后的工具
_registered_tools: dict[str, Any] = {}


def wrap_registered_tool(
    tool_def: ToolDefinition,
) -> dict[str, Any]:
    """包装单个工具。

    Args:
        tool_def: 工具定义

    Returns:
        包装后的工具定义（符合 Tool 格式）
    """
    return {
        "name": tool_def.name,
        "description": tool_def.description,
        "parameters": tool_def.parameters,
        "execute": tool_def.execute,
    }


def wrap_registered_tools(
    extensions: list[Extension],
) -> dict[str, Any]:
    """批量包装扩展工具。

    Args:
        extensions: 扩展实例列表

    Returns:
        工具名称到工具定义的映射
    """
    tools: dict[str, Any] = {}

    for ext in extensions:
        try:
            ext_tools = ext.get_tools()
            for tool_def in ext_tools:
                if tool_def.name in tools:
                    logger.warning(f"工具名称冲突: {tool_def.name}")
                    continue
                tools[tool_def.name] = wrap_registered_tool(tool_def)
                logger.debug(f"注册扩展工具: {tool_def.name}")
        except Exception as e:
            logger.error(f"获取扩展 {ext.id} 的工具失败: {e}")

    return tools


def get_wrapped_tools() -> dict[str, Any]:
    """获取所有已包装的工具。

    Returns:
        工具名称到工具定义的映射
    """
    return _registered_tools.copy()


def register_tool(name: str, tool_def: dict[str, Any]) -> None:
    """注册工具到全局注册表。

    Args:
        name: 工具名称
        tool_def: 工具定义
    """
    _registered_tools[name] = tool_def


def unregister_tool(name: str) -> None:
    """从全局注册表移除工具。

    Args:
        name: 工具名称
    """
    if name in _registered_tools:
        del _registered_tools[name]


def clear_registered_tools() -> None:
    """清空全局工具注册表。"""
    _registered_tools.clear()
