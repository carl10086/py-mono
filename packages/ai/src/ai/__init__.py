"""
AI 核心模块 - 完全对齐 pi-mono 架构

导出所有公共类型和函数，包括：
- 核心类型（Message, Model, Tool, Context 等）
- 流式事件（AssistantMessageEventStream, EventStream 等）
- Provider 注册和抽象
"""

from __future__ import annotations

# Provider 注册
from ai.registry import (
    Provider,
    clear_providers,
    get_provider,
    list_providers,
    register_provider,
    unregister_provider,
)

# 流式事件
from ai.stream import (
    # 事件类型
    AssistantMessageEvent,
    AssistantMessageEventStream,
    EventDone,
    EventError,
    EventStart,
    # 事件流类
    EventStream,
    EventTextDelta,
    EventTextEnd,
    EventTextStart,
    EventThinkingDelta,
    EventThinkingEnd,
    EventThinkingStart,
    EventToolCallDelta,
    EventToolCallEnd,
    EventToolCallStart,
    create_assistant_message_event_stream,
    # 工具函数
    create_partial_message,
)

# 核心类型
from ai.types import (
    # API 和 Provider
    Api,
    AssistantMessage,
    CacheRetention,
    ContentItem,
    # 上下文
    Context,
    ImageContent,
    KnownApi,
    KnownProvider,
    Message,
    # 模型
    Model,
    ModelCapabilities,
    ModelCost,
    # OpenAI 兼容
    OpenAICompletionsCompat,
    OpenRouterRouting,
    # 配置
    ProviderConfig,
    ProviderStreamOptions,
    SimpleStreamOptions,
    StopReason,
    # 流式选项
    StreamOptions,
    # 内容类型
    TextContent,
    ThinkingBudgets,
    ThinkingContent,
    # 思考和选项
    ThinkingLevel,
    # 工具定义
    Tool,
    ToolCall,
    ToolResultMessage,
    Transport,
    # Token 使用
    Usage,
    UsageCost,
    # 消息类型
    UserMessage,
    VercelGatewayRouting,
)

__version__ = "0.1.0"

__all__ = [
    # API 和 Provider
    "Api",
    "Provider",
    "KnownApi",
    "KnownProvider",
    # 思考和选项
    "ThinkingLevel",
    "ThinkingBudgets",
    "CacheRetention",
    "Transport",
    "StopReason",
    # 内容类型
    "TextContent",
    "ThinkingContent",
    "ImageContent",
    "ToolCall",
    "ContentItem",
    # 消息类型
    "UserMessage",
    "AssistantMessage",
    "ToolResultMessage",
    "Message",
    # Token 使用
    "Usage",
    "UsageCost",
    # 工具定义
    "Tool",
    # 流式选项
    "StreamOptions",
    "SimpleStreamOptions",
    "ProviderStreamOptions",
    # 模型
    "Model",
    "ModelCost",
    "ModelCapabilities",
    # 上下文
    "Context",
    # 配置
    "ProviderConfig",
    # OpenAI 兼容
    "OpenAICompletionsCompat",
    "OpenRouterRouting",
    "VercelGatewayRouting",
    # 流式事件
    "EventStream",
    "AssistantMessageEventStream",
    "create_assistant_message_event_stream",
    "AssistantMessageEvent",
    "EventStart",
    "EventTextStart",
    "EventTextDelta",
    "EventTextEnd",
    "EventThinkingStart",
    "EventThinkingDelta",
    "EventThinkingEnd",
    "EventToolCallStart",
    "EventToolCallDelta",
    "EventToolCallEnd",
    "EventDone",
    "EventError",
    "create_partial_message",
    # Provider 注册
    "Provider",
    "register_provider",
    "get_provider",
    "list_providers",
    "unregister_provider",
    "clear_providers",
]
