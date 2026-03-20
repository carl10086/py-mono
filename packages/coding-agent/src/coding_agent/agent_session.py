"""AgentSession 核心模块 - 对齐 pi-mono TypeScript 实现（简化版）

Agent 生命周期和会话管理的核心抽象。

简化说明：
- 核心架构和配置结构
- 移除了完整的事件系统和扩展集成（需要 AI Agent 核心）
- 保留了主要 API 和类型定义
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ai.types import ImageContent, Model

from coding_agent.session.manager import SessionManager
from coding_agent.settings_manager import SettingsManager


# ============================================================================
# 类型定义
# ============================================================================


@dataclass
class AgentSessionConfig:
    """AgentSession 配置"""

    agent: Any
    session_manager: SessionManager
    settings_manager: SettingsManager
    cwd: str
    resource_loader: Any | None = None
    custom_tools: list[Any] | None = None
    initial_active_tool_names: list[str] | None = None


@dataclass
class PromptOptions:
    """prompt() 方法选项"""

    expand_prompt_templates: bool = True
    images: list[ImageContent] | None = None
    streaming_behavior: str | None = None
    source: str = "interactive"


# ============================================================================
# AgentSession 类
# ============================================================================


class AgentSession:
    """AgentSession - 核心抽象

    管理：
    - Agent 状态访问
    - 会话持久化
    - 模型和思考级别管理
    - Bash 执行
    """

    def __init__(self, config: AgentSessionConfig) -> None:
        """初始化 AgentSession

        Args:
            config: 配置对象
        """
        self.agent = config.agent
        self.session_manager = config.session_manager
        self.settings_manager = config.settings_manager
        self._cwd = config.cwd
        self._resource_loader = config.resource_loader
        self._custom_tools = config.custom_tools or []
        self._initial_active_tool_names = config.initial_active_tool_names

        # 事件监听器
        self._event_listeners: list[Callable[[Any], None]] = []

        # 转向索引
        self._turn_index = 0

    def prompt(self, message: str, options: PromptOptions | None = None) -> None:
        """发送消息到 Agent

        Args:
            message: 用户消息
            options: 提示选项
        """
        # TODO: 实现完整的 prompt 逻辑
        # 需要集成 AI Agent 核心
        pass

    def subscribe(self, listener: Callable[[Any], None]) -> Callable[[], None]:
        """订阅事件

        Args:
            listener: 事件监听器

        Returns:
            取消订阅函数
        """
        self._event_listeners.append(listener)

        def unsubscribe() -> None:
            self._event_listeners.remove(listener)

        return unsubscribe

    def execute_bash(self, command: str) -> dict[str, Any]:
        """执行 Bash 命令

        Args:
            command: 命令

        Returns:
            执行结果
        """
        from coding_agent.bash_executor import execute_bash

        result = execute_bash(command, cwd=self._cwd)
        return {
            "output": result.output,
            "exitCode": result.exit_code,
            "cancelled": result.cancelled,
            "truncated": result.truncated,
        }

    def get_cwd(self) -> str:
        """获取工作目录"""
        return self._cwd


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "AgentSessionConfig",
    "PromptOptions",
    "AgentSession",
]
