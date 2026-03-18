"""
Kimi Provider - 基于 Anthropic SDK 实现。

使用 Anthropic SDK 访问 Kimi API，支持：
- 流式对话生成
- Thinking/Reasoning 模式
- Prompt 缓存控制

环境变量：
- KIMI_API_KEY / API_KEY / ANTHROPIC_API_KEY: API 密钥
- ANTHROPIC_BASE_URL: API 地址（默认: https://api.kimi.com/coding/）

默认配置（与 kimi-cli 保持一致）：
- 默认模型: kimi-k2-turbo-preview
- 上下文窗口: 256K (262144 tokens)
- 最大输出: 32K (32768 tokens)
- 默认输出: 32000 tokens
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any, Literal

from ai.stream import (
    AssistantMessageEventStream,
    EventDone,
    EventError,
    EventStart,
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
)
from ai.types import (
    AssistantMessage,
    Context,
    ImageContent,
    Message,
    Model,
    ModelCapabilities,
    ModelCost,
    SimpleStreamOptions,
    StopReason,
    StreamOptions,
    TextContent,
    ThinkingContent,
    Tool,
    ToolCall,
    ToolResultMessage,
    Usage,
    UsageCost,
    UserMessage,
)

# =============================================================================
# 常量定义 - Kimi API 默认配置
# =============================================================================

DEFAULT_MODEL: str = "kimi-k2-turbo-preview"
DEFAULT_BASE_URL: str = "https://api.kimi.com/coding/"
DEFAULT_MAX_TOKENS: int = 32000

CONTEXT_WINDOW: int = 262144
MAX_OUTPUT_TOKENS: int = 32768

THINKING_BUDGETS: dict[str, int | None] = {
    "off": None,
    "minimal": 512,
    "low": 1024,
    "medium": 4096,
    "high": 16000,
    "xhigh": 32000,
}

SUPPORTED_MODELS: dict[str, dict[str, Any]] = {
    "kimi-k2-turbo-preview": {
        "name": "Kimi K2 Turbo",
        "context_window": CONTEXT_WINDOW,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "supports_thinking": True,
    },
    "kimi-k2": {
        "name": "Kimi K2",
        "context_window": CONTEXT_WINDOW,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "supports_thinking": True,
    },
}

ENV_API_KEY: str = "KIMI_API_KEY"
ENV_API_KEY_ALT: str = "API_KEY"
ENV_API_KEY_ANTHROPIC: str = "ANTHROPIC_API_KEY"
ENV_BASE_URL: str = "ANTHROPIC_BASE_URL"
ENV_BASE_URL_ALT: str = "BASE_URL"


type ThinkingLevel = Literal["minimal", "low", "medium", "high", "xhigh"]


def parse_json(json_str: str) -> dict[str, Any]:
    """解析可能不完整的 JSON。"""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # 尝试提取完整对象
        depth = 0
        last_valid = 0
        in_string = False
        escape = False

        for i, char in enumerate(json_str):
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"' and not escape:
                in_string = not in_string
                continue
            if not in_string:
                if char in "{[":
                    depth += 1
                elif char == "}" or char == "]":
                    depth -= 1
                    if depth == 0:
                        last_valid = i + 1

        if last_valid > 0:
            try:
                return json.loads(json_str[:last_valid])
            except json.JSONDecodeError:
                pass
        return {}


def map_stop_reason(reason: str | None) -> StopReason:
    """映射 Anthropic 的停止原因。"""
    if reason is None:
        return "stop"
    mapping: dict[str, StopReason] = {
        "end_turn": "stop",
        "max_tokens": "length",
        "tool_use": "toolUse",
        "stop_sequence": "stop",
    }
    return mapping.get(reason, "stop")


def convert_messages(messages: Sequence[Message]) -> list[dict[str, Any]]:
    """转换消息为 Anthropic 格式。"""
    result: list[dict[str, Any]] = []

    for msg in messages:
        if isinstance(msg, UserMessage):
            result.append(_convert_user_message(msg))
        elif isinstance(msg, AssistantMessage):
            result.append(_convert_assistant_message(msg))
        elif isinstance(msg, ToolResultMessage):
            result.append(_convert_tool_result_message(msg))

    return result


def _convert_user_message(msg: UserMessage) -> dict[str, Any]:
    """转换用户消息为 Anthropic 格式。"""
    if isinstance(msg.content, str):
        return {"role": "user", "content": msg.content}

    blocks = []
    for item in msg.content:
        if isinstance(item, TextContent):
            blocks.append({"type": "text", "text": item.text})
        elif isinstance(item, ImageContent):
            blocks.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": item.mime_type,
                        "data": item.data,
                    },
                }
            )
    return {"role": "user", "content": blocks}


def _convert_assistant_message(msg: AssistantMessage) -> dict[str, Any]:
    """转换助手消息为 Anthropic 格式。"""
    blocks = []
    for item in msg.content:
        if isinstance(item, TextContent):
            blocks.append({"type": "text", "text": item.text})
        elif isinstance(item, ToolCall):
            blocks.append(
                {
                    "type": "tool_use",
                    "id": item.id,
                    "name": item.name,
                    "input": item.arguments,
                }
            )
    return {"role": "assistant", "content": blocks}


def _convert_tool_result_message(msg: ToolResultMessage) -> dict[str, Any]:
    """转换工具结果消息为 Anthropic 格式。"""
    content = (
        msg.content[0].text
        if len(msg.content) == 1
        else [
            {"type": "text", "text": item.text}
            if isinstance(item, TextContent)
            else {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": item.mime_type,
                    "data": item.data,
                },
            }
            for item in msg.content
        ]
    )
    tool_result = {
        "type": "tool_result",
        "tool_use_id": msg.tool_call_id,
        "content": content,
    }
    if msg.is_error:
        tool_result["is_error"] = True
    return {"role": "user", "content": [tool_result]}


def convert_tools(tools: Sequence[Tool]) -> list[dict[str, Any]]:
    """转换工具定义为 Anthropic 格式。"""
    result = []
    for tool in tools:
        schema = tool.parameters
        if hasattr(tool.parameters, "model_json_schema"):
            schema = tool.parameters.model_json_schema()
        elif not isinstance(tool.parameters, dict):
            schema = {"type": "object"}

        result.append(
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": schema,
            }
        )
    return result


class KimiOptions(StreamOptions):
    """Kimi 特定选项。"""

    tool_choice: str | dict[str, Any] | None = None


class KimiProvider:
    """Kimi Provider - 使用 Anthropic SDK。

    支持从环境变量自动读取配置：
    - KIMI_API_KEY / API_KEY / ANTHROPIC_API_KEY: API 密钥
    - ANTHROPIC_BASE_URL / BASE_URL: API 地址

    默认配置（与 kimi-cli 保持一致）：
        - 模型: kimi-k2-turbo-preview
        - 上下文: 256K tokens
        - 最大输出: 32K tokens
        - 默认输出: 32000 tokens

    示例：
        # 基础使用
        provider = KimiProvider()
        provider = provider.with_thinking("medium")
        stream = provider.stream(model, context)
    """

    name: str = "kimi"

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        base_url: str | None = None,
        default_max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        """初始化 KimiProvider。

        Args:
            model: 模型 ID，默认 kimi-k2-turbo-preview
            api_key: API 密钥，默认从环境变量读取
            base_url: API 地址，默认 https://api.kimi.com/coding/
            default_max_tokens: 默认最大输出 token 数，默认 32000
        """
        self._model = model
        self._api_key = api_key or self._get_api_key()
        self._base_url = base_url or self._get_base_url()
        self._default_max_tokens = default_max_tokens
        self._thinking_budget: int | None = None
        self._cache_key: str | None = None

    @staticmethod
    def _get_api_key() -> str:
        """从环境变量获取 API Key。"""
        return (
            os.environ.get(ENV_API_KEY)
            or os.environ.get(ENV_API_KEY_ALT)
            or os.environ.get(ENV_API_KEY_ANTHROPIC)
            or ""
        )

    @staticmethod
    def _get_base_url() -> str:
        """从环境变量获取 Base URL。"""
        return os.environ.get(ENV_BASE_URL) or os.environ.get(ENV_BASE_URL_ALT) or DEFAULT_BASE_URL

    def with_thinking(self, effort: ThinkingLevel | Literal["off"]) -> KimiProvider:
        """配置 thinking 模式。

        Args:
            effort: 思考强度 - off/minimal/low/medium/high/xhigh

        Returns:
            新的 KimiProvider 实例
        """
        import copy

        new_provider = copy.copy(self)
        new_provider._thinking_budget = THINKING_BUDGETS.get(effort)
        return new_provider

    def with_cache_key(self, key: str) -> KimiProvider:
        """配置 prompt 缓存 key。

        Args:
            key: 缓存 key（通常使用 session_id）

        Returns:
            新的 KimiProvider 实例
        """
        import copy

        new_provider = copy.copy(self)
        # Kimi 通过 Anthropic SDK 支持 prompt_cache_key
        new_provider._cache_key = key
        return new_provider

    def get_model(self, model_id: str | None = None) -> Model:
        """获取模型配置。

        Args:
            model_id: 模型 ID，默认使用初始化时的模型

        Returns:
            Model 配置对象
        """
        resolved_id = model_id or self._model

        if resolved_id in SUPPORTED_MODELS:
            config = SUPPORTED_MODELS[resolved_id]
            return self._build_model_from_config(resolved_id, config)

        return self._build_default_model(resolved_id)

    def _build_model_from_config(self, model_id: str, config: dict[str, Any]) -> Model:
        """从配置构建 Model 对象。"""
        return Model(
            id=model_id,
            name=config["name"],
            api="anthropic-messages",
            provider="kimi",
            base_url=self._base_url,
            capabilities=ModelCapabilities(
                reasoning=config.get("supports_thinking", False),
                input=["text", "image"],
            ),
            cost=ModelCost(input=0, output=0, cache_read=0, cache_write=0),
            context_window=config["context_window"],
            max_tokens=config["max_tokens"],
        )

    def _build_default_model(self, model_id: str) -> Model:
        """构建默认 Model 对象（未知模型）。"""
        return Model(
            id=model_id,
            name=model_id,
            api="anthropic-messages",
            provider="kimi",
            base_url=self._base_url,
            capabilities=ModelCapabilities(reasoning=False, input=["text"]),
            cost=ModelCost(input=0, output=0, cache_read=0, cache_write=0),
            context_window=CONTEXT_WINDOW,
            max_tokens=self._default_max_tokens,
        )

    @property
    def models(self) -> list[Model]:
        """返回支持的模型列表。"""
        return [self.get_model(mid) for mid in SUPPORTED_MODELS.keys()]

    @property
    def thinking_effort(self) -> ThinkingLevel | Literal["off"] | None:
        """获取当前 thinking 配置。"""
        if self._thinking_budget is None:
            return None
        if self._thinking_budget == 0:
            return "off"

        # 将 budget 映射回 effort 等级
        if self._thinking_budget <= 512:
            return "minimal"
        elif self._thinking_budget <= 1024:
            return "low"
        elif self._thinking_budget <= 4096:
            return "medium"
        elif self._thinking_budget <= 16000:
            return "high"
        else:
            return "xhigh"

    def stream(
        self,
        model: Model | str,
        context: Context,
        options: KimiOptions | None = None,
    ) -> AssistantMessageEventStream:
        """流式生成响应。"""
        from anthropic import AsyncAnthropic

        model_obj = model if isinstance(model, Model) else self.get_model(model)
        stream = create_assistant_message_event_stream()

        async def _run():
            output = AssistantMessage(
                role="assistant",
                content=[],
                api=model_obj.api,
                provider=model_obj.provider,
                model=model_obj.id,
                usage=Usage(
                    input=0,
                    output=0,
                    cache_read=0,
                    cache_write=0,
                    total_tokens=0,
                    cost=UsageCost(input=0, output=0, cache_read=0, cache_write=0, total=0),
                ),
                stop_reason="stop",
            )

            try:
                # 创建客户端
                client = AsyncAnthropic(api_key=self._api_key, base_url=self._base_url)

                # 构建参数
                params: dict[str, Any] = {
                    "model": model_obj.id,
                    "messages": convert_messages(context.messages),
                    "max_tokens": (
                        options.max_tokens
                        if options and options.max_tokens
                        else model_obj.max_tokens
                    ),
                }

                if context.system_prompt:
                    params["system"] = context.system_prompt
                if options and options.temperature is not None:
                    params["temperature"] = options.temperature
                if context.tools:
                    params["tools"] = convert_tools(context.tools)
                if options and options.tool_choice is not None:
                    params["tool_choice"] = options.tool_choice

                # 添加 thinking 配置
                if self._thinking_budget is not None:
                    params["extra_body"] = {
                        "thinking": {
                            "type": "enabled",
                            "budget_tokens": self._thinking_budget,
                        }
                    }

                # 发送开始事件
                stream.push(EventStart(partial=output))

                blocks: list[dict] = []
                current_thinking_block: ThinkingContent | None = None

                # 流式请求
                async with client.messages.stream(**params) as response:
                    async for event in response:
                        if event.type == "message_start":
                            usage = event.message.usage
                            output.usage.input = usage.input_tokens or 0
                            output.usage.output = usage.output_tokens or 0
                            output.usage.cache_read = (
                                getattr(usage, "cache_read_input_tokens", 0) or 0
                            )
                            output.usage.cache_write = (
                                getattr(usage, "cache_creation_input_tokens", 0) or 0
                            )
                            output.usage.total_tokens = sum(
                                [
                                    output.usage.input,
                                    output.usage.output,
                                    output.usage.cache_read,
                                    output.usage.cache_write,
                                ]
                            )

                        elif event.type == "content_block_start":
                            if event.content_block.type == "text":
                                block = TextContent(text="")
                                output.content.append(block)
                                blocks.append(
                                    {"type": "text", "index": event.index, "block": block}
                                )
                                stream.push(
                                    EventTextStart(
                                        content_index=len(output.content) - 1, partial=output
                                    )
                                )

                            elif event.content_block.type == "thinking":
                                block = ThinkingContent(thinking="")
                                output.content.append(block)
                                current_thinking_block = block
                                idx = len(output.content) - 1
                                stream.push(EventThinkingStart(content_index=idx, partial=output))

                            elif event.content_block.type == "tool_use":
                                block = ToolCall(
                                    id=event.content_block.id,
                                    name=event.content_block.name,
                                    arguments={},
                                )
                                output.content.append(block)
                                blocks.append(
                                    {
                                        "type": "tool",
                                        "index": event.index,
                                        "block": block,
                                        "json": "",
                                    }
                                )
                                stream.push(
                                    EventToolCallStart(
                                        content_index=len(output.content) - 1, partial=output
                                    )
                                )

                        elif event.type == "content_block_delta":
                            if event.delta.type == "text_delta":
                                for b in blocks:
                                    if b["index"] == event.index and b["type"] == "text":
                                        b["block"].text += event.delta.text
                                        idx = output.content.index(b["block"])
                                        stream.push(
                                            EventTextDelta(
                                                content_index=idx,
                                                delta=event.delta.text,
                                                partial=output,
                                            )
                                        )
                                        break

                            elif event.delta.type == "thinking_delta":
                                if current_thinking_block:
                                    current_thinking_block.thinking += event.delta.thinking
                                    idx = output.content.index(current_thinking_block)
                                    stream.push(
                                        EventThinkingDelta(
                                            content_index=idx,
                                            delta=event.delta.thinking,
                                            partial=output,
                                        )
                                    )

                            elif event.delta.type == "input_json_delta":
                                for b in blocks:
                                    if b["index"] == event.index and b["type"] == "tool":
                                        b["json"] += event.delta.partial_json
                                        b["block"].arguments = parse_json(b["json"])
                                        idx = output.content.index(b["block"])
                                        stream.push(
                                            EventToolCallDelta(
                                                content_index=idx,
                                                delta=event.delta.partial_json,
                                                partial=output,
                                            )
                                        )
                                        break

                        elif event.type == "content_block_stop":
                            # 查找对应的内容块并发送结束事件
                            for b in blocks:
                                if b["index"] == event.index:
                                    if b["type"] == "text":
                                        idx = output.content.index(b["block"])
                                        stream.push(
                                            EventTextEnd(
                                                content_index=idx,
                                                content=b["block"].text,
                                                partial=output,
                                            )
                                        )
                                    elif b["type"] == "tool":
                                        b["block"].arguments = parse_json(b["json"])
                                        idx = output.content.index(b["block"])
                                        stream.push(
                                            EventToolCallEnd(
                                                content_index=idx,
                                                tool_call=b["block"],
                                                partial=output,
                                            )
                                        )
                                    break

                            # 检查是否是 thinking 块结束
                            if current_thinking_block and event.content_block:
                                if getattr(event.content_block, "type", None) == "thinking":
                                    idx = output.content.index(current_thinking_block)
                                    stream.push(
                                        EventThinkingEnd(
                                            content_index=idx,
                                            content=current_thinking_block.thinking,
                                            partial=output,
                                        )
                                    )
                                    current_thinking_block = None

                        elif event.type == "message_delta":
                            if event.delta.stop_reason:
                                output.stop_reason = map_stop_reason(event.delta.stop_reason)
                            if event.usage:
                                if event.usage.input_tokens is not None:
                                    output.usage.input = event.usage.input_tokens
                                if event.usage.output_tokens is not None:
                                    output.usage.output = event.usage.output_tokens

                # 发送结束事件
                stream.push(EventDone(reason=output.stop_reason, message=output))

            except Exception as e:
                output.stop_reason = "error"
                output.error_message = str(e)
                stream.push(EventError(reason="error", error=output))

        import asyncio

        asyncio.create_task(_run())
        return stream

    async def complete(
        self,
        model: Model | str,
        context: Context,
        options: KimiOptions | None = None,
    ) -> AssistantMessage:
        """获取完整响应（非流式）。"""
        s = self.stream(model, context, options)
        return await s.result()

    def stream_simple(
        self,
        model: Model | str,
        context: Context,
        options: SimpleStreamOptions | None = None,
    ) -> AssistantMessageEventStream:
        """简化流式接口。"""
        opts = KimiOptions()
        if options:
            opts.temperature = options.temperature
            opts.max_tokens = options.max_tokens
        return self.stream(model, context, opts)

    async def complete_simple(
        self,
        model: Model | str,
        context: Context,
        options: SimpleStreamOptions | None = None,
    ) -> AssistantMessage:
        """简化 complete 接口。"""
        s = self.stream_simple(model, context, options)
        return await s.result()
