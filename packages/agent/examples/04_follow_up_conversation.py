"""
示例 04: Follow-up 多轮对话

学习目标：
- 理解 Follow-up 消息的工作机制
- 实现连续的多轮对话
- 对比：简单循环 vs Follow-up 回调

场景：
用户：今天北京天气怎么样？
Agent：今天北京晴，25度
用户：那明天呢？（Follow-up）
Agent：明天北京多云，22度

关键理解：
- Follow-up 是在 agent_loop 内部自动续接对话
- 不需要多次调用 agent_loop
- 一轮结束后，通过 get_follow_up_messages 获取新消息继续

运行：
    uv run python examples/04_follow_up_conversation.py
"""

from __future__ import annotations

import asyncio
from typing import Any

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ai.providers import KimiProvider
from ai.types import TextContent, UserMessage
from agent import (
    AgentContext,
    AgentLoopConfig,
    agent_loop,
    AgentToolResult,
)


class WeatherTool:
    """天气查询工具"""

    name = "get_weather"
    label = "天气查询"
    description = "查询指定城市和日期的天气"
    parameters = {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名称"},
            "date": {"type": "string", "description": "日期，如今天、明天"},
        },
        "required": ["city", "date"],
    }

    WEATHER_DB = {
        ("北京", "今天"): {"weather": "晴", "temp": "25°C"},
        ("北京", "明天"): {"weather": "多云", "temp": "22°C"},
    }

    async def execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any = None,
        on_update: Any = None,
    ) -> AgentToolResult:
        city = params.get("city", "")
        date = params.get("date", "")
        result = self.WEATHER_DB.get((city, date), {"weather": "未知", "temp": "--"})
        text = f"{city}{date}天气：{result['weather']}，{result['temp']}"
        return AgentToolResult(
            content=[TextContent(text=text)], details={"city": city, "date": date, **result}
        )


async def demo_simple_loop():
    """方式 1：简单循环调用（最常用）"""
    print("=" * 60)
    print("方式 1：简单循环调用（推荐）")
    print("=" * 60)
    print("这种方式最简单：每次用户输入都调用一次 agent_loop\n")

    provider = KimiProvider()

    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    # 模拟用户输入队列
    user_messages = [
        "今天北京天气怎么样？",
        "那明天呢？",
    ]

    # 维护上下文
    context = AgentContext(system_prompt="天气助手", messages=[], tools=[WeatherTool()])

    for i, text in enumerate(user_messages, 1):
        print(f"\n【第 {i} 轮】")
        print(f"🧑 用户: {text}")
        print("🤖 Agent: ", end="", flush=True)

        # 每次调用 agent_loop（新的流）
        stream = agent_loop(
            prompts=[UserMessage(text=text)],
            context=context,
            config=AgentLoopConfig(model=provider.get_model()),
            stream_fn=stream_fn,
        )

        # 收集输出
        assistant_text = ""
        async for event in stream:
            if event.get("type") == "message_update":
                inner = event.get("assistant_message_event")
                if inner and getattr(inner, "type", "") == "text_delta":
                    delta = getattr(inner, "delta", "")
                    print(delta, end="", flush=True)
                    assistant_text += delta

        # 更新上下文（将这一轮的消息加入）
        new_messages = await stream.result()
        context.messages.extend(new_messages)

        print(f"\n✅ 上下文现在共 {len(context.messages)} 条消息")

    print("\n✅ 多轮对话完成")


async def demo_follow_up_callback():
    """方式 2：Follow-up 回调（特殊场景）"""
    print("\n" + "=" * 60)
    print("方式 2：Follow-up 回调（自动续接）")
    print("=" * 60)
    print("这种方式：一次 agent_loop 调用，自动处理多轮\n")

    provider = KimiProvider()

    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    # 预定义的消息队列
    message_queue = [
        "那明天呢？",  # 第一轮结束后自动发送
    ]

    # 🔴 关键：Follow-up 回调
    async def get_follow_up():
        """在对话结束后自动提供新消息"""
        await asyncio.sleep(0.1)  # 模拟检查
        if message_queue:
            text = message_queue.pop(0)
            print(f"\n[Follow-up 回调触发] 自动发送: {text}")
            return [UserMessage(text=text)]
        return None

    # 初始化上下文
    context = AgentContext(system_prompt="天气助手", messages=[], tools=[WeatherTool()])

    # 配置：包含 follow-up 回调
    config = AgentLoopConfig(
        model=provider.get_model(),
        get_follow_up_messages=get_follow_up,  # 🔴 关键配置
    )

    print("【开始】只调用一次 agent_loop")
    print("🧑 用户: 今天北京天气怎么样？\n")

    # 🔴 只调用一次，但会处理多轮
    stream = agent_loop(
        prompts=[UserMessage(text="今天北京天气怎么样？")],
        context=context,
        config=config,
        stream_fn=stream_fn,
    )

    # 消费所有事件（包含多轮）
    turn_count = 0
    async for event in stream:
        event_type = event.get("type")

        if event_type == "turn_start":
            turn_count += 1
            if turn_count > 1:
                print(f"\n【第 {turn_count} 轮自动开始】")
        elif event_type == "message_update":
            inner = event.get("assistant_message_event")
            if inner and getattr(inner, "type", "") == "text_delta":
                delta = getattr(inner, "delta", "")
                print(delta, end="", flush=True)
        elif event_type == "tool_execution_start":
            tool_name = event.get("tool_name")
            print(f"\n🔧 调用工具: {tool_name}")

    final_messages = await stream.result()
    print(f"\n\n✅ 总共 {turn_count} 轮对话，{len(final_messages)} 条消息")
    print("✅ 只调用了一次 agent_loop，但自动处理了 Follow-up")


async def main():
    """运行对比演示"""
    try:
        # 演示方式 1（推荐）
        await demo_simple_loop()

        # 演示方式 2（特殊场景）
        await demo_follow_up_callback()

        print("\n" + "=" * 60)
        print("💡 总结")
        print("=" * 60)
        print("""
方式 1（简单循环）：
  - 每次用户输入都调用 agent_loop
  - 代码简单直观
  - 适合：交互式 CLI、Web 应用

方式 2（Follow-up 回调）：
  - 一次调用，自动续接
  - 适合：批量处理、异步消息队列
  - 使用场景较少

推荐使用方式 1！
""")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
