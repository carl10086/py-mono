"""
Anthropic Provider 实现 - 简化版

直接使用 anthropic SDK，从环境变量读取配置：
- ANTHROPIC_API_KEY / API_KEY (API 密钥)
- ANTHROPIC_BASE_URL / BASE_URL (自定义 API 地址)

使用方式：
    export API_KEY=your-api-key
    export BASE_URL=https://api.moonshot.cn  # kimi 或其他兼容 API

    provider = AnthropicProvider()
    model = Model(
        id="kimi-k2-turbo-preview",  # 你的模型名
        name="Kimi K2",
        api="anthropic-messages",
        provider="anthropic",
        base_url=os.environ.get("BASE_URL", "https://api.anthropic.com"),
        capabilities=ModelCapabilities(input=["text"]),
        cost=ModelCost(input=0, output=0, cache_read=0, cache_write=0),
        context_window=128000,
        max_tokens=8192,
    )
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any

from ai.stream import (
    AssistantMessageEventStream,
    EventDone,
    EventError,
    EventStart,
    EventTextDelta,
    EventTextEnd,
    EventTextStart,
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
    SimpleStreamOptions,
    StopReason,
    StreamOptions,
    TextContent,
    Tool,
    ToolCall,
    ToolResultMessage,
    Usage,
    UsageCost,
    UserMessage,
)


class AnthropicOptions(StreamOptions):
    """Anthropic 特定选项"""

    tool_choice: str | dict[str, Any] | None = None


def convert_messages(messages: Sequence[Message]) -> list[dict[str, Any]]:
    """转换消息格式"""
    result: list[dict[str, Any]] = []

    for msg in messages:
        if isinstance(msg, UserMessage):
            if isinstance(msg.content, str):
                result.append({"role": "user", "content": msg.content})
            else:
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
                result.append({"role": "user", "content": blocks})

        elif isinstance(msg, AssistantMessage):
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
            result.append({"role": "assistant", "content": blocks})

        elif isinstance(msg, ToolResultMessage):
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
            result.append({"role": "user", "content": [tool_result]})

    return result


def convert_tools(tools: Sequence[Tool]) -> list[dict[str, Any]]:
    """转换工具定义"""
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


def map_stop_reason(reason: str | None) -> StopReason:
    """映射停止原因"""
    mapping = {
        "end_turn": "stop",
        "max_tokens": "length",
        "tool_use": "toolUse",
        "stop_sequence": "stop",
    }
    return mapping.get(reason, "stop")


def parse_json(json_str: str) -> dict[str, Any]:
    """解析可能不完整的 JSON"""
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


class AnthropicProvider:
    """Anthropic Provider - 直接使用环境变量配置"""

    name: str = "anthropic"

    def stream(
        self, model: Model, context: Context, options: AnthropicOptions | None = None
    ) -> AssistantMessageEventStream:
        """流式生成"""
        from anthropic import AsyncAnthropic

        stream = create_assistant_message_event_stream()

        async def _run():
            # 初始化输出
            output = AssistantMessage(
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

            try:
                # 创建客户端 - SDK 自动从环境变量读取配置
                client = AsyncAnthropic()

                # 构建参数
                params = {
                    "model": model.id,
                    "messages": convert_messages(context.messages),
                    "max_tokens": options.max_tokens
                    if options and options.max_tokens
                    else model.max_tokens,
                }

                if context.system_prompt:
                    params["system"] = context.system_prompt
                if options and options.temperature is not None:
                    params["temperature"] = options.temperature
                if context.tools:
                    params["tools"] = convert_tools(context.tools)
                if options and options.tool_choice is not None:
                    params["tool_choice"] = options.tool_choice

                # 发送开始事件
                stream.push(EventStart(partial=output))

                blocks: list[dict] = []

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

                        elif event.type == "message_delta":
                            if event.delta.stop_reason:
                                output.stop_reason = map_stop_reason(event.delta.stop_reason)
                            if event.usage:
                                if event.usage.input_tokens is not None:
                                    output.usage.input = event.usage.input_tokens
                                if event.usage.output_tokens is not None:
                                    output.usage.output = event.usage.output_tokens

                # 成功结束
                stream.push(EventDone(reason=output.stop_reason, message=output))

            except Exception as e:
                output.stop_reason = "error"
                output.error_message = str(e)
                stream.push(EventError(reason="error", error=output))

        import asyncio

        asyncio.create_task(_run())
        return stream

    async def complete(
        self, model: Model, context: Context, options: AnthropicOptions | None = None
    ) -> AssistantMessage:
        """完整响应"""
        s = self.stream(model, context, options)
        return await s.result()

    def stream_simple(
        self, model: Model, context: Context, options: SimpleStreamOptions | None = None
    ) -> AssistantMessageEventStream:
        """简化流式"""
        opts = AnthropicOptions()
        if options:
            opts.temperature = options.temperature
            opts.max_tokens = options.max_tokens
        return self.stream(model, context, opts)

    async def complete_simple(
        self, model: Model, context: Context, options: SimpleStreamOptions | None = None
    ) -> AssistantMessage:
        """简化 complete"""
        s = self.stream_simple(model, context, options)
        return await s.result()

    def get_model(self, model_id: str) -> Model:
        """获取模型 - 需要用户自己配置"""
        raise NotImplementedError(
            "请直接创建 Model 对象，例如:\n"
            "model = Model(\n"
            '    id="kimi-k2-turbo-preview",\n'
            '    name="Kimi K2",\n'
            '    api="anthropic-messages",\n'
            '    provider="anthropic",\n'
            "    ...\n"
            ")"
        )

    @property
    def models(self) -> list[Model]:
        """返回空列表，需要用户自己管理模型"""
        return []
