"""
示例 04: Agent Steering 功能

学习目标：
- 使用 steer() 中断 Agent
- 理解 steering 队列
- 在运行中插入新指令

运行：
    uv run python examples/04_steering.py
"""

from __future__ import annotations

import asyncio

from ai.providers import KimiProvider
from ai.types import UserMessage
from agent import Agent, AgentOptions


async def main():
    print("=" * 60)
    print("示例 04: Agent Steering 功能")
    print("=" * 60)
    print("\n本示例演示如何在 Agent 运行时插入 steering 消息")
    print("steering 消息会在当前 turn 完成后优先处理")

    # 获取 provider
    provider = KimiProvider()

    # 创建 stream_fn
    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    # 创建 Agent
    agent = Agent(AgentOptions(stream_fn=stream_fn))
    agent.set_model(provider.get_model())

    # 追踪事件
    events_log: list[str] = []

    def on_event(event):
        event_type = event.get("type", "")
        if event_type == "turn_start":
            events_log.append("🔄 Turn 开始")
        elif event_type == "turn_end":
            events_log.append("🏁 Turn 结束")
        elif event_type == "agent_end":
            events_log.append("✨ Agent 结束")

    agent.subscribe(on_event)

    try:
        # 模拟：先发送一个长问题
        print("\n[步骤 1] 发送初始问题...")
        await agent.prompt("请详细介绍一下 Python 的历史")

        # 模拟：在第一个问题处理过程中插入 steering
        print("[步骤 2] 插入 steering 消息...")
        agent.steer(UserMessage(text="不用介绍了，直接回答：Python 最新版本是多少？"))

        # 等待完成
        await agent.wait_for_idle()

        print("\n事件日志:")
        for log in events_log:
            print(f"  {log}")

        print(f"\n总消息数: {len(agent.state.messages)}")
        print("\n说明: steering 消息会在当前 turn 结束后优先处理")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
