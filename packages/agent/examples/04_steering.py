"""
示例 04: Agent Steering 功能

学习目标：
- 使用 steer() 中断 Agent
- 理解 steering 队列的工作机制
- 在运行中插入新指令

关键点：
- steer() 必须在对话进行中调用（在 prompt 完成前）
- 可以在事件回调中调用 steer()
- 也可以使用 asyncio.create_task() 不等待 prompt 完成

运行：
    uv run python examples/04_steering.py
"""

from __future__ import annotations

import asyncio

from ai.providers import KimiProvider
from ai.types import UserMessage
from agent import Agent, AgentOptions, AgentMessage


async def main():
    print("=" * 60)
    print("示例 04: Agent Steering 功能")
    print("=" * 60)
    print("\n本示例演示如何在 Agent 运行时插入 steering 消息")
    print("steering 消息会在当前 turn 结束后优先处理")
    print("\n关键：steer() 必须在 prompt() 完成前调用！")

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
    steering_inserted = False

    def on_event(event):
        nonlocal steering_inserted
        event_type = event.get("type", "")

        if event_type == "turn_start":
            events_log.append("🔄 Turn 开始")
        elif event_type == "turn_end":
            events_log.append("🏁 Turn 结束")

            # 在第一个 Turn 结束时插入 steering 消息
            # 这是正确的使用时机：在对话进行中插入
            if not steering_inserted:
                steering_inserted = True
                print("\n[步骤 2] ⚡ 在 Turn 结束时插入 steering 消息...")
                agent.steer(UserMessage(text="不用介绍了，直接回答：Python 最新版本是多少？"))

        elif event_type == "agent_end":
            events_log.append("✨ Agent 结束")

    agent.subscribe(on_event)

    try:
        print("\n[步骤 1] 发送初始问题...")
        print("    用户: 请详细介绍一下 Python 的历史")

        # 发送提示 - 这会启动对话循环
        # 在 on_event 回调中会插入 steering 消息
        # await agent.prompt("请详细介绍一下 Python 的历史")

        await agent.prompt([
            UserMessage(
                role="user",
                content="请详细介绍一下 Python 的历史",
            ),
        ])

        print("\n事件日志:")
        for log in events_log:
            print(f"  {log}")

        print(f"\n总消息数: {len(agent.state.messages)}")

        # 验证 steering 是否生效
        if len(agent.state.messages) >= 3:
            print("\n✅ 成功：steering 消息被正确处理！")
            print("   - 消息1: user (初始问题)")
            print("   - 消息2: assistant (第一次回复)")
            print("   - 消息3: user (steering消息)")
            print("   - 消息4: assistant (对steering的回复)")
        else:
            print("\n⚠️  steering 消息可能未被处理")
            print("   实际消息数:", len(agent.state.messages))

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
