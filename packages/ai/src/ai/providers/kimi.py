"""
Kimi Provider - 完全独立实现。

使用 OpenAI SDK 访问 Kimi API，支持：
- 流式对话生成
- Thinking/Reasoning 模式
- Prompt 缓存控制

环境变量：
- KIMI_API_KEY / API_KEY: API 密钥
- KIMI_BASE_URL: API 地址（默认: https://api.moonshot.ai/v1）

默认配置（与 kimi-cli 保持一致）：
- 默认模型: kimi-k2-turbo-preview
- 上下文窗口: 256K (262144 tokens)
- 最大输出: 32K (32768 tokens)
- 默认输出: 32000 tokens
"""

from __future__ import annotations

import asyncio
import copy
import json
import os
from collections.abc import Sequence
from typing import Any, Literal, cast

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

# 默认模型配置
DEFAULT_MODEL: str = "kimi-k2-turbo-preview"
DEFAULT_BASE_URL: str = "https://api.moonshot.ai/v1"
DEFAULT_MAX_TOKENS: int = 32000  # 默认输出 token 数（与 kimi-cli 一致）

# 模型能力限制
CONTEXT_WINDOW: int = 262144  # 256K 上下文窗口
MAX_OUTPUT_TOKENS: int = 32768  # 最大输出 token 数

# Generation 参数默认值
DEFAULT_TEMPERATURE: float | None = None
DEFAULT_TOP_P: float | None = None

# Thinking 预算映射（tokens）
THINKING_BUDGETS: dict[str, int | None] = {
    "off": None,
    "minimal": 512,
    "low": 1024,
    "medium": 4096,
    "high": 16000,
    "xhigh": 32000,
}

# 支持的模型列表
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

# 环境变量名称
ENV_API_KEY: str = "KIMI_API_KEY"
ENV_API_KEY_ALT: str = "API_KEY"
ENV_BASE_URL: str = "KIMI_BASE_URL"
ENV_BASE_URL_ALT: str = "BASE_URL"


type ThinkingLevel = Literal["minimal", "low", "medium", "high", "xhigh"]


class KimiOptions(StreamOptions):
    """Kimi 特定选项。"""

    tool_choice: str | dict[str, Any] | None = None


class KimiProvider:
    """Kimi Provider - 使用 OpenAI SDK。

    支持从环境变量自动读取配置：
    - KIMI_API_KEY / API_KEY: API 密钥
    - KIMI_BASE_URL / BASE_URL: API 地址

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

        # 自定义配置
        provider = KimiProvider(
            model="kimi-k2",
            api_key="your-key",
            base_url="https://api.moonshot.ai/v1",
            default_max_tokens=32000,
        )
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
            base_url: API 地址，默认 https://api.moonshot.ai/v1
            default_max_tokens: 默认最大输出 token 数，默认 32000
        """
        self._model = model
        self._api_key = api_key or self._get_api_key()
        self._base_url = base_url or self._get_base_url()
        self._default_max_tokens = default_max_tokens
        self._generation_kwargs: dict[str, Any] = {}

    @staticmethod
    def _get_api_key() -> str:
        """从环境变量获取 API Key。"""
        return os.environ.get(ENV_API_KEY) or os.environ.get(ENV_API_KEY_ALT) or ""

    @staticmethod
    def _get_base_url() -> str:
        """从环境变量获取 Base URL。"""
        return os.environ.get(ENV_BASE_URL) or os.environ.get(ENV_BASE_URL_ALT) or DEFAULT_BASE_URL

    def with_thinking(self, effort: ThinkingLevel | Literal["off"]) -> KimiProvider:
        """配置 thinking 模式。

        Args:
            effort: 思考强度 - off/minimal/low/medium/high/xhigh

        Returns:
            新的 KimiProvider 实例（不可变模式）
        """
        new_provider = copy.copy(self)
        new_provider._generation_kwargs = copy.deepcopy(self._generation_kwargs)

        budget = THINKING_BUDGETS.get(effort)
        thinking_config = (
            {"type": "disabled"} if budget is None else {"type": "enabled", "budget_tokens": budget}
        )

        extra_body = new_provider._generation_kwargs.get("extra_body", {})
        extra_body["thinking"] = thinking_config
        new_provider._generation_kwargs["extra_body"] = extra_body

        return new_provider

    def with_cache_key(self, key: str) -> KimiProvider:
        """配置 prompt 缓存 key。

        Args:
            key: 缓存 key（通常使用 session_id）

        Returns:
            新的 KimiProvider 实例（不可变模式）
        """
        new_provider = copy.copy(self)
        new_provider._generation_kwargs = copy.deepcopy(self._generation_kwargs)
        new_provider._generation_kwargs["prompt_cache_key"] = key
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
            api="openai-chat",
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
            api="openai-chat",
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
        extra_body = self._generation_kwargs.get("extra_body", {})
        cfg = extra_body.get("thinking")

        if not cfg:
            return None
        if cfg.get("type") == "disabled":
            return "off"

        budget = cfg.get("budget_tokens", 0)
        return self._budget_to_effort(budget)

    @staticmethod
    def _budget_to_effort(budget: int) -> ThinkingLevel:
        """将 budget_tokens 映射回 effort 等级。"""
        if budget <= 512:
            return "minimal"
        elif budget <= 1024:
            return "low"
        elif budget <= 4096:
            return "medium"
        elif budget <= 16000:
            return "high"
        else:
            return "xhigh"

    def stream(
        self,
        model: Model | str,
        context: Context,
        options: KimiOptions | None = None,
    ) -> AssistantMessageEventStream:
        """流式生成响应。

        Args:
            model: 模型配置或模型 ID
            context: 对话上下文
            options: 生成选项

        Returns:
            流式响应事件流
        """
        model_obj = model if isinstance(model, Model) else self.get_model(model)
        stream = create_assistant_message_event_stream()

        asyncio.create_task(self._stream_worker(model_obj, context, options, stream))
        return stream

    async def _stream_worker(
        self,
        model: Model,
        context: Context,
        options: KimiOptions | None,
        stream: AssistantMessageEventStream,
    ) -> None:
        """后台流式处理任务。"""
        output = self._create_initial_output(model)

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
            params = self._build_request_params(model, context, options)
            stream.push(EventStart(partial=output))

            await self._process_stream(client, params, output, stream)
            stream.push(EventDone(reason="stop", message=output))

        except Exception as e:
            output.stop_reason = "error"
            output.error_message = str(e)
            stream.push(EventError(reason="error", error=output))

    def _create_initial_output(self, model: Model) -> AssistantMessage:
        """创建初始 AssistantMessage。"""
        return AssistantMessage(
            role="assistant",
            content=[],
            api=model.api,
            provider=model.provider,
            model=model.id,
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

    def _build_request_params(
        self,
        model: Model,
        context: Context,
        options: KimiOptions | None,
    ) -> dict[str, Any]:
        """构建 API 请求参数。"""
        params: dict[str, Any] = {
            "model": model.id,
            "messages": convert_messages(context.messages),
            "max_tokens": (
                options.max_tokens if options and options.max_tokens else model.max_tokens
            ),
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        if context.system_prompt:
            params["system"] = context.system_prompt
        if options and options.temperature is not None:
            params["temperature"] = options.temperature
        if context.tools:
            params["tools"] = convert_tools(context.tools)
        if options and options.tool_choice is not None:
            params["tool_choice"] = options.tool_choice

        # 合并 generation_kwargs（thinking、cache_key 等）
        params.update(self._generation_kwargs)

        return params

    async def _process_stream(
        self,
        client: Any,
        params: dict[str, Any],
        output: AssistantMessage,
        stream: AssistantMessageEventStream,
    ) -> None:
        """处理流式响应。"""
        current_content: dict[str, Any] | None = None

        response = await client.chat.completions.create(**params)

        async for chunk in response:
            self._update_usage(output, chunk)

            choices = getattr(chunk, "choices", None)
            if not choices:
                continue

            delta = choices[0].delta if choices else None
            if not delta:
                continue

            # 处理 thinking 内容
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                current_content = self._handle_reasoning(reasoning, current_content, output, stream)

            # 处理文本内容
            if delta.content:
                current_content = self._handle_text(
                    str(delta.content), current_content, output, stream
                )

            # 处理工具调用
            tool_calls = getattr(delta, "tool_calls", None)
            if tool_calls:
                for tool_call in tool_calls:
                    current_content = self._handle_tool_call(
                        tool_call, current_content, output, stream
                    )

        # 发送结束事件
        self._finalize_content(current_content, output, stream)

    def _update_usage(self, output: AssistantMessage, chunk: Any) -> None:
        """更新 Token 使用量。"""
        usage = getattr(chunk, "usage", None)
        if not usage:
            return

        output.usage.input = getattr(usage, "prompt_tokens", 0) or 0
        output.usage.output = getattr(usage, "completion_tokens", 0) or 0
        output.usage.total_tokens = output.usage.input + output.usage.output

    def _handle_reasoning(
        self,
        reasoning: str,
        current: dict[str, Any] | None,
        output: AssistantMessage,
        stream: AssistantMessageEventStream,
    ) -> dict[str, Any]:
        """处理 reasoning/thinking 内容。"""
        # 开始新的 thinking 块
        if not current or current.get("type") != "thinking":
            self._finalize_content(current, output, stream)

            block = ThinkingContent(thinking="")
            content_list = cast(list[Any], output.content)
            content_list.append(block)
            idx = len(content_list) - 1
            stream.push(EventThinkingStart(content_index=idx, partial=output))
            current = {"type": "thinking", "block": block, "index": idx}

        # 追加内容
        block = current["block"]
        block.thinking += reasoning
        stream.push(
            EventThinkingDelta(
                content_index=current["index"],
                delta=reasoning,
                partial=output,
            )
        )

        return current

    def _handle_text(
        self,
        text: str,
        current: dict[str, Any] | None,
        output: AssistantMessage,
        stream: AssistantMessageEventStream,
    ) -> dict[str, Any]:
        """处理文本内容。"""
        # 开始新的文本块
        if not current or current.get("type") != "text":
            self._finalize_content(current, output, stream)

            block = TextContent(text="")
            content_list = cast(list[Any], output.content)
            content_list.append(block)
            idx = len(content_list) - 1
            stream.push(EventTextStart(content_index=idx, partial=output))
            current = {"type": "text", "block": block, "index": idx}

        # 追加内容
        block = current["block"]
        block.text += text
        stream.push(
            EventTextDelta(
                content_index=current["index"],
                delta=text,
                partial=output,
            )
        )

        return current

    def _handle_tool_call(
        self,
        tool_call: Any,
        current: dict[str, Any] | None,
        output: AssistantMessage,
        stream: AssistantMessageEventStream,
    ) -> dict[str, Any]:
        """处理工具调用。"""
        func = getattr(tool_call, "function", None)
        if not func:
            return current

        # 开始新的工具调用
        if not current or current.get("type") != "tool":
            self._finalize_content(current, output, stream)

            block = ToolCall(
                id=getattr(tool_call, "id", "") or "",
                name=getattr(func, "name", "") or "",
                arguments={},
            )
            content_list = cast(list[Any], output.content)
            content_list.append(block)
            idx = len(content_list) - 1
            stream.push(EventToolCallStart(content_index=idx, partial=output))
            current = {"type": "tool", "block": block, "index": idx, "json": ""}

        # 追加参数
        args = getattr(func, "arguments", None)
        if args:
            current["json"] += str(args)
            # 尝试解析 JSON
            try:
                current["block"].arguments = json.loads(current["json"])
            except json.JSONDecodeError:
                pass

            stream.push(
                EventToolCallDelta(
                    content_index=current["index"],
                    delta=str(args),
                    partial=output,
                )
            )

        return current

    def _finalize_content(
        self,
        current: dict[str, Any] | None,
        output: AssistantMessage,
        stream: AssistantMessageEventStream,
    ) -> None:
        """完成当前内容块。"""
        if not current:
            return

        idx = current["index"]
        block = current["block"]
        content_type = current["type"]

        if content_type == "text":
            stream.push(EventTextEnd(content_index=idx, content=block.text, partial=output))
        elif content_type == "thinking":
            stream.push(EventThinkingEnd(content_index=idx, content=block.thinking, partial=output))
        elif content_type == "tool":
            stream.push(EventToolCallEnd(content_index=idx, tool_call=block, partial=output))

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


def convert_messages(messages: Sequence[Message]) -> list[dict[str, Any]]:
    """转换消息为 OpenAI 格式。"""
    result: list[dict[str, Any]] = []

    for msg in messages:
        if isinstance(msg, UserMessage):
            result.append(convert_user_message(msg))
        elif isinstance(msg, AssistantMessage):
            result.append(convert_assistant_message(msg))
        elif isinstance(msg, ToolResultMessage):
            result.append(convert_tool_result_message(msg))

    return result


def convert_user_message(msg: UserMessage) -> dict[str, Any]:
    """转换用户消息。"""
    if isinstance(msg.content, str):
        return {"role": "user", "content": msg.content}

    # 多模态内容
    content_blocks = []
    for item in msg.content:
        if isinstance(item, TextContent):
            content_blocks.append({"type": "text", "text": item.text})
        elif isinstance(item, ImageContent):
            content_blocks.append(convert_image_content(item))

    return {"role": "user", "content": content_blocks}


def convert_image_content(item: ImageContent) -> dict[str, Any]:
    """转换图像内容为 OpenAI 格式。"""
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{item.mime_type};base64,{item.data}"},
    }


def convert_assistant_message(msg: AssistantMessage) -> dict[str, Any]:
    """转换助手消息。"""
    content_blocks = []

    for item in msg.content:
        if isinstance(item, TextContent):
            content_blocks.append({"type": "text", "text": item.text})
        elif isinstance(item, ToolCall):
            content_blocks.append(convert_tool_call(item))

    return {"role": "assistant", "content": content_blocks}


def convert_tool_call(item: ToolCall) -> dict[str, Any]:
    """转换工具调用为 OpenAI 格式。"""
    return {
        "type": "function",
        "function": {
            "name": item.name,
            "arguments": json.dumps(item.arguments) if item.arguments else "{}",
        },
    }


def convert_tool_result_message(msg: ToolResultMessage) -> dict[str, Any]:
    """转换工具结果消息。"""
    content = msg.content[0].text if len(msg.content) == 1 else ""

    if len(msg.content) > 1 or (
        len(msg.content) == 1 and not isinstance(msg.content[0], TextContent)
    ):
        # 多模态或复杂内容
        content_blocks = []
        for item in msg.content:
            if isinstance(item, TextContent):
                content_blocks.append({"type": "text", "text": item.text})
            elif isinstance(item, ImageContent):
                content_blocks.append(convert_image_content(item))
        content = content_blocks

    return {
        "role": "tool",
        "tool_call_id": msg.tool_call_id,
        "content": content,
    }


def convert_tools(tools: Sequence[Tool]) -> list[dict[str, Any]]:
    """转换工具定义为 OpenAI 格式。"""
    return [convert_tool(tool) for tool in tools]


def convert_tool(tool: Tool) -> dict[str, Any]:
    """转换单个工具定义。"""
    schema = tool.parameters
    if hasattr(tool.parameters, "model_json_schema"):
        schema = tool.parameters.model_json_schema()
    elif not isinstance(tool.parameters, dict):
        schema = {"type": "object"}

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": schema,
        },
    }
