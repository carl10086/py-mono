"""
示例 02: Agent 事件监听

学习目标：
- 订阅 Agent 事件
- 理解 Agent 生命周期事件
- 监控对话流程

运行：
    uv run python examples/02_agent_events.py
"""

from __future__ import annotations

import asyncio

from ai.providers import KimiProvider
from agent import Agent, AgentOptions


async def main():
    print("=" * 60)
    print("示例 02: Agent 事件监听")
    print("=" * 60)

    # 获取 provider
    provider = KimiProvider()

    # 创建 stream_fn
    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    # 创建 Agent
    agent = Agent(AgentOptions(stream_fn=stream_fn))
    agent.set_model(provider.get_model())
    agent.set_system_prompt("你是一个简洁的助手。")

    # 事件计数器
    event_counts: dict[str, int] = {}

    def on_event(event):
        event_type = event.get("type", "unknown")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

        # 打印重要事件
        if event_type == "agent_start":
            print("\n🚀 Agent 开始运行")
        elif event_type == "turn_start":
            print("🔄 新 Turn 开始")
        elif event_type == "message_start":
            message = event.get("message")
            if message:
                role = getattr(message, "role", "unknown")
                print(f"💬 {role} 消息开始")
        elif event_type == "message_end":
            message = event.get("message")
            if message:
                role = getattr(message, "role", "unknown")
                content_preview = ""
                if hasattr(message, "content"):
                    texts = [c.text for c in message.content if hasattr(c, "text")]
                    content_preview = "".join(texts)[:50]
                print(f"✅ {role} 消息结束: {content_preview}...")
        elif event_type == "turn_end":
            print("🏁 Turn 结束")
        elif event_type == "agent_end":
            print("✨ Agent 运行结束")

    # 订阅事件
    unsubscribe = agent.subscribe(on_event)

    try:
        print("\n发送提示...")
        await agent.prompt("你好！请介绍一下 Python 的优点。")
        await agent.wait_for_idle()

        print("\n" + "=" * 60)
        print("事件统计:")
        print("=" * 60)
        for event_type, count in sorted(event_counts.items()):
            print(f"  {event_type}: {count}")

        print(f"\n总消息数: {len(agent.state.messages)}")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # 取消订阅
        unsubscribe()


if __name__ == "__main__":
    asyncio.run(main())
