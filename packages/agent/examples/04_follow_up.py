"""
示例 04: Follow-up 自动续接对话

学习目标：
- 理解 get_follow_up_messages 回调的工作机制
- 实现一次调用 agent_loop，自动处理多轮对话

场景：
用户一次性提出 3 个问题，Agent 自动连续回答，无需多次调用

运行：
    uv run python examples/04_follow_up.py
"""

from __future__ import annotations

import asyncio
from typing import Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ai.providers import KimiProvider
from ai.types import TextContent, UserMessage
from agent import AgentContext, AgentLoopConfig, agent_loop, AgentToolResult


class WeatherTool:
    """天气查询工具"""

    name = "get_weather"
    label = "天气查询"
    description = "查询指定城市和日期的天气"
    parameters = {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名称"},
            "date": {"type": "string", "description": "日期"},
        },
        "required": ["city", "date"],
    }

    WEATHER_DB = {
        ("北京", "今天"): {"weather": "晴", "temp": "25°C"},
        ("北京", "明天"): {"weather": "多云", "temp": "22°C"},
        ("北京", "后天"): {"weather": "小雨", "temp": "20°C"},
    }

    async def execute(
        self, tool_call_id: str, params: dict[str, Any], signal: Any = None, on_update: Any = None
    ) -> AgentToolResult:
        city = params.get("city", "")
        date = params.get("date", "")
        result = self.WEATHER_DB.get((city, date), {"weather": "未知", "temp": "--"})
        text = f"{city}{date}天气：{result['weather']}，{result['temp']}"
        return AgentToolResult(content=[TextContent(text=text)])


async def main():
    print("=" * 60)
    print("Follow-up 自动续接对话")
    print("=" * 60)

    # 预定义的问题队列
    questions = [
        "今天北京天气怎么样？",
        "那明天呢？",  # 第一轮结束后自动发送
        "后天呢？",  # 第二轮结束后自动发送
    ]

    # 🔴 关键：Follow-up 回调函数
    # 当一轮对话结束后，Agent 会调用此函数检查是否有后续问题
    async def get_follow_up() -> list[Any] | None:
        if questions:
            text = questions.pop(0)
            print(f"\n[Follow-up] 自动发送: {text}")
            return [UserMessage(text=text)]
        return None

    provider = KimiProvider()

    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    # 初始化上下文
    context = AgentContext(system_prompt="天气助手", messages=[], tools=[WeatherTool()])

    # 🔴 关键：配置中包含 get_follow_up_messages 回调
    config = AgentLoopConfig(
        model=provider.get_model(),
        get_follow_up_messages=get_follow_up,
    )

    # 获取第一个问题
    first_question = questions.pop(0)
    print(f"\n[开始] {first_question}")

    # 🔴 只调用一次 agent_loop，但会处理多轮对话
    stream = agent_loop(
        prompts=[UserMessage(text=first_question)],
        context=context,
        config=config,
        stream_fn=stream_fn,
    )

    # 消费所有事件（包含多轮）
    turn = 0
    async for event in stream:
        event_type = event.get("type")

        if event_type == "turn_start":
            turn += 1
            print(f"\n--- 第 {turn} 轮 ---")
        elif event_type == "message_update":
            inner = event.get("assistant_message_event")
            if inner and getattr(inner, "type", "") == "text_delta":
                print(getattr(inner, "delta", ""), end="", flush=True)
        elif event_type == "tool_execution_start":
            print(f"\n🔧 调用: {event.get('tool_name')}")

    messages = await stream.result()

    print(f"\n\n✅ 完成！共 {turn} 轮对话，{len(messages)} 条消息")
    print(f"✅ 只调用了一次 agent_loop，自动处理了所有 Follow-up")


if __name__ == "__main__":
    asyncio.run(main())
