"""
示例 03: Agent 多轮对话

学习目标：
- 管理对话历史
- 连续发送多个提示
- 查看完整的对话上下文

运行：
    uv run python examples/03_conversation.py
"""

from __future__ import annotations

import asyncio

from ai.providers import KimiProvider
from agent import Agent, AgentOptions


async def main():
    print("=" * 60)
    print("示例 03: Agent 多轮对话")
    print("=" * 60)

    # 获取 provider
    provider = KimiProvider()

    # 创建 stream_fn
    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    # 创建 Agent
    agent = Agent(AgentOptions(stream_fn=stream_fn))
    agent.set_model(provider.get_model())

    # 对话流程
    prompts = [
        "你好，我叫小明",
        "我叫什么名字？",
        "请用一句话总结我们的对话",
    ]

    # 简单的响应处理器
    responses: list[tuple[str, str]] = []

    def on_event(event):
        if event.get("type") == "message_end":
            message = event.get("message")
            if message and getattr(message, "role", "") == "assistant":
                if hasattr(message, "content"):
                    for c in message.content:
                        if getattr(c, "type", "") == "text":
                            responses.append(("助手", c.text))
                            break

    agent.subscribe(on_event)

    try:
        for i, prompt in enumerate(prompts, 1):
            print(f"\n{'=' * 60}")
            print(f"第 {i}/{len(prompts)} 轮")
            print("=" * 60)
            print(f"用户: {prompt}")
            print("助手: ", end="", flush=True)

            await agent.prompt(prompt)
            await agent.wait_for_idle()

            if responses:
                print(responses[-1][1])

            print(f"\n[对话历史: {len(agent.state.messages)} 条消息]")

        print("\n" + "=" * 60)
        print("完整对话历史")
        print("=" * 60)
        for i, msg in enumerate(agent.state.messages, 1):
            role = "用户" if getattr(msg, "role", "") == "user" else "助手"
            content_str = ""
            if hasattr(msg, "content") and msg.content:
                for c in msg.content:
                    if hasattr(c, "text"):
                        content_str = c.text[:60] + "..."
                        break
            print(f"{i}. {role}: {content_str}")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
