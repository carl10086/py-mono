"""AgentSession 核心模块 - Phase 1 集成 SessionManager

实现：
- SessionManager 集成
- 消息持久化
- 上下文重建

对应 pi-mono: core/agent-session.ts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from agent import Agent, AgentEvent, AgentOptions, AgentTool
from ai.providers import KimiProvider

from coding_agent.session.manager import SessionManager
from coding_agent.settings_manager import SettingsManager

if TYPE_CHECKING:
    from ai.types import Model


@dataclass
class AgentSessionConfig:
    """AgentSession 配置"""

    cwd: str
    provider: KimiProvider | None = None
    model_id: str | None = None
    system_prompt: str = "你是一个有帮助的 AI 编程助手。"
    tools: list[AgentTool] | None = None
    session_manager: SessionManager | None = None
    settings_manager: SettingsManager | None = None


class AgentSession:
    """AgentSession - 核心抽象

    管理：
    - Agent 状态访问
    - 会话持久化（通过 SessionManager）
    - 事件订阅和转发
    """

    def __init__(self, config: AgentSessionConfig) -> None:
        """初始化 AgentSession

        Args:
            config: 配置对象
        """
        self._cwd = config.cwd
        self._provider = config.provider or KimiProvider()
        self._model_id = config.model_id
        self._system_prompt = config.system_prompt
        self._tools = config.tools or []
        self._session_manager = config.session_manager
        self._settings_manager = config.settings_manager

        self._agent: Agent | None = None
        self._event_listeners: list[Callable[[AgentEvent], None]] = []
        self._turn_index = 0

        self._init_agent()

    def _init_agent(self) -> None:
        """初始化 Agent 实例"""

        async def stream_fn(model: Any, context: Any, options: Any) -> Any:
            return self._provider.stream_simple(model, context, options)

        self._agent = Agent(AgentOptions(stream_fn=stream_fn))
        model = (
            self._provider.get_model(self._model_id)
            if self._model_id
            else self._provider.get_model()
        )
        self._agent.set_model(model)
        self._agent.set_system_prompt(self._system_prompt)
        if self._tools:
            self._agent.set_tools(self._tools)

        self._agent.subscribe(self._on_agent_event)

    def _on_agent_event(self, event: AgentEvent) -> None:
        """Agent 事件处理器 - 持久化消息

        Args:
            event: Agent 事件
        """
        # 转发给监听器
        for listener in self._event_listeners:
            try:
                listener(event)
            except Exception:
                pass

        # 持久化消息
        self._persist_event(event)

    def _persist_event(self, event: dict[str, Any]) -> None:
        """持久化事件到 SessionManager

        Args:
            event: Agent 事件
        """
        if not self._session_manager:
            return

        if event.get("type") == "message_end":
            message = event.get("message")
            if not message:
                return

            role = getattr(message, "role", None)
            if role in ("user", "assistant", "tool_result"):
                self._session_manager.append_message(message)

    @property
    def agent(self) -> Agent:
        """获取底层 Agent 实例"""
        if self._agent is None:
            raise RuntimeError("Agent not initialized")
        return self._agent

    @property
    def session_manager(self) -> SessionManager | None:
        """获取会话管理器"""
        return self._session_manager

    @property
    def settings_manager(self) -> SettingsManager | None:
        """获取设置管理器"""
        return self._settings_manager

    @property
    def model(self) -> Model | None:
        """获取当前模型"""
        return self._agent.state.model if self._agent else None

    @property
    def is_streaming(self) -> bool:
        """是否正在流式输出"""
        return self._agent.state.is_streaming if self._agent else False

    async def prompt(
        self,
        message: str,
        images: list[Any] | None = None,
    ) -> None:
        """发送消息到 Agent

        Args:
            message: 用户消息
            images: 可选的图片列表
        """
        if not self._agent:
            raise RuntimeError("Agent not initialized")

        await self._agent.prompt(message, images)
        await self._agent.wait_for_idle()

    def build_context(self) -> list[Any]:
        """从会话构建上下文消息列表

        从当前叶子节点回溯构建，用于恢复对话历史。

        Returns:
            消息列表
        """
        if not self._session_manager:
            return []

        entries = self._session_manager.get_branch()
        messages: list[Any] = []
        for entry in entries:
            if entry.type == "message":
                msg = getattr(entry, "message", None)
                if msg:
                    messages.append(msg)
        return messages

    def subscribe(self, listener: Callable[[dict[str, Any]], None]) -> Callable[[], None]:
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

    def get_cwd(self) -> str:
        """获取工作目录"""
        return self._cwd

    async def switch_session(self, session_path: str) -> None:
        """切换到指定会话

        实现"继续上次对话"功能：
        1. 中断当前 agent
        2. 加载指定会话文件
        3. 重建上下文
        4. 恢复 agent 状态

        Args:
            session_path: 会话文件路径
        """
        if not self._session_manager:
            raise RuntimeError("No session manager configured")

        if not self._agent:
            raise RuntimeError("Agent not initialized")

        self._agent.abort()
        await self._agent.wait_for_idle()

        self._session_manager.set_session_file(session_path)

        context = self._session_manager.build_session_context()

        self._agent.replace_messages(context.messages)

        if context.model:
            try:
                model = self._provider.get_model(context.model.get("model_id"))
                self._agent.set_model(model)
            except Exception:
                pass

        if context.thinking_level and context.thinking_level != "off":
            self._agent.set_thinking_level(context.thinking_level)

        self._turn_index = 0


def create_agent_session(
    cwd: str,
    provider: KimiProvider | None = None,
    model_id: str | None = None,
    system_prompt: str | None = None,
    tools: list[AgentTool] | None = None,
    session_manager: SessionManager | None = None,
) -> AgentSession:
    """创建 AgentSession 的便捷函数

    Args:
        cwd: 工作目录
        provider: LLM Provider，默认使用 KimiProvider
        model_id: 模型 ID，默认使用 provider 的默认模型
        system_prompt: 系统提示词
        tools: 工具列表
        session_manager: SessionManager，默认创建新的

    Returns:
        AgentSession 实例
    """
    if session_manager is None:
        session_manager = SessionManager.create(cwd)

    config = AgentSessionConfig(
        cwd=cwd,
        provider=provider,
        model_id=model_id,
        system_prompt=system_prompt or "你是一个有帮助的 AI 编程助手。",
        tools=tools,
        session_manager=session_manager,
    )
    return AgentSession(config)


__all__ = [
    "AgentSession",
    "AgentSessionConfig",
    "PromptOptions",
    "create_agent_session",
]


@dataclass
class PromptOptions:
    """prompt() 方法选项"""

    expand_prompt_templates: bool = True
    images: list[Any] | None = None
    streaming_behavior: str | None = None
    source: str = "interactive"
