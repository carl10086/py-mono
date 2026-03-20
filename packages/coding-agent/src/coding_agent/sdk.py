"""SDK 核心 - 对齐 pi-mono TypeScript 实现（简化版）

提供易用的 SDK 接口：
- 工具工厂函数
- AgentSession 创建
- 只读工具集

简化说明：
- 移除了扩展系统依赖
- 保留了核心工具工厂函数
- create_agent_session 使用简化版实现（不依赖 AI Agent 核心）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from coding_agent.agent_session import AgentSession, AgentSessionConfig
from coding_agent.config import get_agent_dir
from coding_agent.model_registry import ModelRegistry
from coding_agent.session.manager import SessionManager
from coding_agent.settings_manager import SettingsManager
from coding_agent.tools import (
    create_bash_tool,
    create_edit_tool,
    create_find_tool,
    create_grep_tool,
    create_ls_tool,
    create_read_tool,
    create_write_tool,
)


# ============================================================================
# 类型定义
# ============================================================================


@dataclass
class CreateAgentSessionOptions:
    """创建 AgentSession 的选项"""

    cwd: str | None = None
    """工作目录（默认当前目录）"""

    agent_dir: str | None = None
    """Agent 配置目录（默认 ~/.pi/agent）"""

    model: Any | None = None
    """使用的模型"""

    tools: list[Any] | None = None
    """工具列表（默认编码工具集）"""

    session_manager: SessionManager | None = None
    """会话管理器（默认创建新的）"""

    settings_manager: SettingsManager | None = None
    """设置管理器（默认创建新的）"""

    model_registry: ModelRegistry | None = None
    """模型注册表（默认创建新的）"""


@dataclass
class CreateAgentSessionResult:
    """创建 AgentSession 的结果"""

    session: AgentSession
    """创建的会话"""

    model_fallback_message: str | None = None
    """模型回退消息（如果有）"""


# ============================================================================
# 工具工厂函数
# ============================================================================


def create_coding_tools(cwd: str | None = None) -> dict[str, Any]:
    """创建完整的编码工具集

    包含：read, bash, edit, write

    Args:
        cwd: 工作目录（默认当前目录）

    Returns:
        工具字典
    """
    actual_cwd = cwd or "."
    return {
        "read": create_read_tool(actual_cwd),
        "bash": create_bash_tool(actual_cwd),
        "edit": create_edit_tool(actual_cwd),
        "write": create_write_tool(actual_cwd),
    }


def create_read_only_tools(cwd: str | None = None) -> dict[str, Any]:
    """创建只读工具集

    包含：read, grep, find, ls, bash

    Args:
        cwd: 工作目录（默认当前目录）

    Returns:
        工具字典
    """
    actual_cwd = cwd or "."
    return {
        "read": create_read_tool(actual_cwd),
        "grep": create_grep_tool(actual_cwd),
        "find": create_find_tool(actual_cwd),
        "ls": create_ls_tool(actual_cwd),
        "bash": create_bash_tool(actual_cwd),
    }


# ============================================================================
# AgentSession 创建
# ============================================================================


def create_agent_session(
    options: CreateAgentSessionOptions | None = None,
) -> CreateAgentSessionResult:
    """创建 AgentSession
    简化版实现，不依赖完整的 AI Agent 核心。

    Args:
        options: 创建选项

    Returns:
        创建结果，包含会话和可选的警告消息

    Example:
        ```python
        # 最小配置
        result = create_agent_session()
        session = result.session

        # 自定义配置
        result = create_agent_session(
            CreateAgentSessionOptions(
                cwd="/path/to/project",
                tools=[read_tool, bash_tool],
            )
        )
        ```
    """
    opts = options or CreateAgentSessionOptions()

    # 解析配置
    cwd = opts.cwd or "."
    agent_dir = opts.agent_dir or get_agent_dir()

    # 创建或复用管理器
    settings_manager = opts.settings_manager or SettingsManager.create(cwd, agent_dir)
    session_manager = opts.session_manager or SessionManager.create(cwd)
    model_registry = opts.model_registry or ModelRegistry()

    # 获取工具
    tools = opts.tools
    if tools is None:
        tools = list(create_coding_tools(cwd).values())

    # 尝试获取模型
    model = opts.model
    model_fallback_message: str | None = None

    if model is None:
        # 尝试从设置获取默认模型
        available = model_registry.get_available()
        if available:
            model = available[0]
        else:
            model_fallback_message = "没有可用的模型。请配置 API 密钥或使用 /login 命令。"

    # 创建 Agent 占位对象（简化版）
    agent = _create_placeholder_agent(model, tools)

    # 创建 AgentSession 配置
    config = AgentSessionConfig(
        agent=agent,
        session_manager=session_manager,
        settings_manager=settings_manager,
        cwd=cwd,
        custom_tools=opts.tools,
    )

    # 创建会话
    session = AgentSession(config)

    return CreateAgentSessionResult(
        session=session,
        model_fallback_message=model_fallback_message,
    )


def _create_placeholder_agent(model: Any | None, tools: list[Any]) -> Any:
    """创建占位 Agent 对象（简化版）

    Args:
        model: 模型
        tools: 工具列表

    Returns:
        占位 Agent 对象
    """

    class PlaceholderAgent:
        """占位 Agent 类"""

        def __init__(self, model: Any, tools: list[Any]) -> None:
            """初始化占位 Agent"""
            self.model = model
            self.tools = tools
            self.state = {"model": model, "tools": tools}

    return PlaceholderAgent(model, tools)


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 工具工厂
    "create_coding_tools",
    "create_read_only_tools",
    # AgentSession 创建
    "create_agent_session",
    "CreateAgentSessionOptions",
    "CreateAgentSessionResult",
]
