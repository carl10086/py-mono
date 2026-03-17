"""
Provider 注册表 - 对齐 pi-mono 架构

提供全局 Provider 注册和获取机制，支持 Protocol 结构子类型。

设计决策：
- 使用 Protocol 而非 ABC，允许第三方实现无需继承特定基类
- stream() 返回 AssistantMessageEventStream（而非 AsyncIterator）
- 支持 api/model 参数化（对齐 TypeScript 泛型设计）
- Contract：调用后错误应编码在流中，而非抛出
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ai.stream import AssistantMessageEventStream
    from ai.types import (
        Api,
        AssistantMessage,
        Context,
        Model,
        ProviderStreamOptions,
        SimpleStreamOptions,
    )


@runtime_checkable
class Provider(Protocol):
    """Provider 协议 - 所有 LLM Provider 必须实现

    与 TypeScript 版本对齐：
    - stream(): 基础流式接口，返回 AssistantMessageEventStream
    - stream_simple(): 简化接口，支持 reasoning/thinkingBudgets
    - complete(): 等待流完成并返回最终结果
    - complete_simple(): 简化 complete 接口

    Contract:
    - 调用后，请求/模型/运行时错误应编码在返回的流中，而不是抛出
    - 错误终止必须产生 stopReason 为 "error" 或 "aborted" 的 AssistantMessage
    - 通过流协议发出错误消息
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 唯一标识符"""
        ...

    @property
    @abstractmethod
    def models(self) -> list[Model]:
        """支持的模型列表"""
        ...

    @abstractmethod
    def stream(
        self,
        model: Model,
        context: Context,
        options: ProviderStreamOptions | None = None,
    ) -> AssistantMessageEventStream:
        """流式生成响应

        Args:
            model: 模型配置（包含 api, provider, baseUrl 等）
            context: 对话上下文（systemPrompt, messages, tools）
            options: 流式选项（temperature, maxTokens, apiKey 等）

        Returns:
            AssistantMessageEventStream: 事件流，支持异步迭代和 result() 获取最终消息

        Contract:
        - 错误应编码在流中，不抛出异常
        - 返回的流可被异步迭代获取实时事件
        - 调用 result() 获取最终的 AssistantMessage
        """
        ...

    @abstractmethod
    def stream_simple(
        self,
        model: Model,
        context: Context,
        options: SimpleStreamOptions | None = None,
    ) -> AssistantMessageEventStream:
        """简化流式接口（支持 reasoning）

        Args:
            model: 模型配置
            context: 对话上下文
            options: 包含 reasoning 和 thinkingBudgets 的选项

        Returns:
            AssistantMessageEventStream: 事件流
        """
        ...

    @abstractmethod
    async def complete(
        self,
        model: Model,
        context: Context,
        options: ProviderStreamOptions | None = None,
    ) -> AssistantMessage:
        """完整响应（等待流结束）

        便捷方法：内部调用 stream() 并等待 result()。

        Args:
            model: 模型配置
            context: 对话上下文
            options: 流式选项

        Returns:
            AssistantMessage: 最终完成的助手消息
        """
        ...

    @abstractmethod
    async def complete_simple(
        self,
        model: Model,
        context: Context,
        options: SimpleStreamOptions | None = None,
    ) -> AssistantMessage:
        """简化 complete 接口"""
        ...

    @abstractmethod
    def get_model(self, model_id: str) -> Model:
        """获取模型配置"""
        ...


# ============================================================================
# 全局注册表
# ============================================================================

_providers: dict[str, Provider] = {}


def register_provider(name: str, provider: Provider) -> None:
    """注册 Provider

    Args:
        name: Provider 名称（唯一标识）
        provider: Provider 实例

    Raises:
        TypeError: 如果 provider 未实现 Provider 协议
        ValueError: 如果 name 已被注册
    """
    # 运行时检查：验证 provider 实现了必需属性
    required_attrs = (
        "name",
        "models",
        "stream",
        "stream_simple",
        "complete",
        "complete_simple",
        "get_model",
    )
    for attr in required_attrs:
        if not hasattr(provider, attr):
            raise TypeError(f"Provider must implement '{attr}' attribute: {type(provider)}")

    if name in _providers:
        raise ValueError(f"Provider '{name}' is already registered")

    _providers[name] = provider


def get_provider(name: str) -> Provider:
    """获取 Provider

    Args:
        name: Provider 名称

    Returns:
        Provider 实例

    Raises:
        ValueError: 如果 Provider 未找到
    """
    if name not in _providers:
        available = ", ".join(list_providers())
        raise ValueError(f"Provider '{name}' not found. Available: {available}")

    return _providers[name]


def list_providers() -> list[str]:
    """列出所有已注册 Provider"""
    return list(_providers.keys())


def unregister_provider(name: str) -> None:
    """注销 Provider（主要用于测试）"""
    _providers.pop(name, None)


def clear_providers() -> None:
    """清空所有 Provider（主要用于测试）"""
    _providers.clear()


# ============================================================================
# API Provider 解析（对齐 pi-mono）
# ============================================================================


def resolve_api_provider(api: Api) -> Provider:
    """解析 API 标识符对应的 Provider

    Args:
        api: API 标识符（如 "anthropic-messages"）

    Returns:
        对应的 Provider 实例

    Raises:
        ValueError: 如果没有 Provider 支持该 API
    """
    # TODO: 实现 API 到 Provider 的映射逻辑
    # 这需要根据 api 字段查找对应的 provider
    # 例如："anthropic-messages" -> anthropic provider
    raise NotImplementedError("API Provider resolution not yet implemented")
