"""
示例 06: 思考模式 (Thinking Mode)

学习目标：
- 启用思考模式
- 设置思考等级
- 观察思考内容

运行：
    uv run python examples/06_thinking_mode.py
"""

from __future__ import annotations

import asyncio

from ai.providers import KimiProvider
from agent import Agent, AgentOptions


async def main():
    print("=" * 60)
    print("示例 06: 思考模式")
    print("=" * 60)

    # 获取 provider
    provider = KimiProvider()

    # 创建 stream_fn
    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    # 创建 Agent，启用思考模式
    agent = Agent(AgentOptions(stream_fn=stream_fn))
    agent.set_model(provider.get_model())

    # 设置思考等级: off, minimal, low, medium, high, xhigh
    agent.set_thinking_level("medium")

    print(f"\n思考等级: {agent.state.thinking_level}")

    # 收集思考内容
    thinking_content: list[str] = []
    text_content: list[str] = []

    def on_event(event):
        if event.get("type") == "message_end":
            message = event.get("message")
            if message and hasattr(message, "content"):
                for content in message.content:
                    content_type = getattr(content, "type", "")
                    if content_type == "thinking":
                        thinking_text = getattr(content, "thinking", "")
                        if thinking_text:
                            thinking_content.append(thinking_text)
                    elif content_type == "text":
                        text = getattr(content, "text", "")
                        if text:
                            text_content.append(text)

    agent.subscribe(on_event)

    try:
        # 发送需要推理的问题
        question = "一个篮子里有 5 个苹果，拿走 2 个，还剩几个？请解释你的思考过程。"
        print(f"\n问题: {question}")
        print("\n处理中...")

        await agent.prompt(question)
        await agent.wait_for_idle()

        # 显示结果
        print("\n" + "=" * 60)
        print("回复内容")
        print("=" * 60)

        if text_content:
            print("\n📝 最终回答:")
            print("".join(text_content))
        else:
            print("\n📝 最终回答: [无文本内容]")
            print("提示: 思考模式的内容会显示在 content 中，类型为 'thinking'")

        if thinking_content:
            print("\n💭 思考过程:")
            for i, thought in enumerate(thinking_content, 1):
                print(f"\n思考片段 {i}:")
                print(thought[:200] + "..." if len(thought) > 200 else thought)

        print(f"\n✅ 完成！")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
