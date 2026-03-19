"""
示例 03: EventStream API 测试

学习目标：
- 使用 EventStream API 消费 Agent 事件
- 对比 Promise API 和 EventStream API
- 验证 agent_loop/agent_loop_continue 函数

运行：
    uv run python examples/03_event_stream_api.py
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
    AgentEventStream,
    AgentLoopConfig,
    AgentOptions,
    Agent,
    agent_loop,
    agent_loop_continue,
)


class CalculatorTool:
    """计算器工具"""

    name = "calculate"
    label = "计算器"
    description = "计算数学表达式"
    parameters = {
        "type": "object",
        "properties": {"expression": {"type": "string", "description": "要计算的数学表达式"}},
        "required": ["expression"],
    }

    async def execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any = None,
        on_update: Any = None,
    ) -> Any:
        expression = params.get("expression", "")
        try:
            allowed = {"abs": abs, "max": max, "min": min, "pow": pow, "round": round}
            result = eval(expression, {"__builtins__": {}}, allowed)
            from agent import AgentToolResult

            return AgentToolResult(
                content=[TextContent(text=f"{expression} = {result}")],
                details={"expression": expression, "result": result},
            )
        except Exception as e:
            from agent import AgentToolResult

            return AgentToolResult(
                content=[TextContent(text=f"错误: {e}")],
                details={"error": str(e)},
            )


async def test_event_stream_api():
    """测试 EventStream API"""
    print("=" * 60)
    print("测试 EventStream API")
    print("=" * 60)

    provider = KimiProvider()

    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    # 创建上下文
    context = AgentContext(
        system_prompt="你是一个数学助手。使用 calculate 工具计算。",
        messages=[],
        tools=[CalculatorTool()],
    )

    # 创建配置（注意：AgentLoopConfig 不需要 stream_fn）
    config = AgentLoopConfig(
        model=provider.get_model(),
    )

    # 创建用户消息
    user_msg = UserMessage(text="计算 2 + 3 * 4")

    print(f"\n用户: {user_msg.content}\n")
    print("事件流:")
    print("-" * 60)

    # 使用 EventStream API，stream_fn 作为独立参数传递
    stream = agent_loop([user_msg], context, config, stream_fn=stream_fn)

    event_count = 0
    async for event in stream:
        event_count += 1
        event_type = event.get("type", "")

        if event_type == "message_update":
            inner = event.get("assistant_message_event")
            if inner:
                inner_type = getattr(inner, "type", "")
                print(f"  [{event_count:3d}] {event_type:20s} -> {inner_type}")
        elif event_type in ["tool_execution_start", "tool_execution_end"]:
            tool_name = event.get("tool_name", "")
            print(f"  [{event_count:3d}] {event_type:20s} -> {tool_name}")
        else:
            print(f"  [{event_count:3d}] {event_type}")

    # 获取结果
    messages = await stream.result()

    print("-" * 60)
    print(f"\n共收到 {event_count} 个事件")
    print(f"产生 {len(messages)} 条新消息")

    return messages


async def test_promise_vs_event_stream():
    """对比 Promise API 和 EventStream API"""
    print("\n" + "=" * 60)
    print("Promise API vs EventStream API 对比")
    print("=" * 60)

    provider = KimiProvider()

    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    # Promise API - 使用 Agent 类
    print("\n1. Promise API (Agent 类):")
    agent = Agent(AgentOptions(stream_fn=stream_fn))
    agent.set_model(provider.get_model())
    agent.set_system_prompt("简短回答")

    promise_events: list[str] = []

    def on_event(event):
        promise_events.append(event.get("type", ""))

    agent.subscribe(on_event)
    await agent.prompt("你好")
    await agent.wait_for_idle()

    print(f"   收到 {len(promise_events)} 个事件")
    print(f"   事件类型: {set(promise_events)}")

    # EventStream API
    print("\n2. EventStream API (agent_loop):")
    context = AgentContext(system_prompt="简短回答", messages=[], tools=[])
    config = AgentLoopConfig(model=provider.get_model())
    user_msg = UserMessage(text="你好")

    stream = agent_loop([user_msg], context, config, stream_fn=stream_fn)

    event_stream_events: list[str] = []
    async for event in stream:
        event_stream_events.append(event.get("type", ""))

    await stream.result()

    print(f"   收到 {len(event_stream_events)} 个事件")
    print(f"   事件类型: {set(event_stream_events)}")

    # 对比
    print("\n3. 对比结果:")
    if set(promise_events) == set(event_stream_events):
        print("   ✅ 两套 API 产生的事件类型一致")
    else:
        print(f"   ⚠️  事件类型有差异:")
        print(f"      Promise API 特有: {set(promise_events) - set(event_stream_events)}")
        print(f"      EventStream 特有: {set(event_stream_events) - set(promise_events)}")


async def main():
    print("=" * 60)
    print("示例 03: EventStream API 测试")
    print("=" * 60)

    try:
        # 测试 EventStream API
        await test_event_stream_api()

        # 对比测试
        await test_promise_vs_event_stream()

        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
