"""
示例 01: 基础 Agent 使用

学习目标：
- 创建 Agent 实例
- 设置模型和系统提示
- 发送简单提示
- 理解 Agent 状态

运行：
    uv run python examples/01_basic_agent.py
"""

from __future__ import annotations

import asyncio

from ai.providers import KimiProvider
from agent import Agent, AgentOptions


async def main():
    print("=" * 60)
    print("示例 01: 基础 Agent 使用")
    print("=" * 60)

    # 获取模型和 provider
    provider = KimiProvider()
    model = provider.get_model()

    # 创建 stream_fn，用于调用 LLM
    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    # 创建 Agent 实例，传入 stream_fn
    agent = Agent(AgentOptions(stream_fn=stream_fn))

    # 设置模型
    agent.set_model(model)

    # 设置系统提示
    agent.set_system_prompt("你是一个有帮助的 AI 助手。")

    print(f"\n模型: {model.name} ({model.id})")
    print(f"系统提示: {agent.state.system_prompt}")

    # 发送提示
    prompt_text = "你好，请用一句话介绍自己"
    print(f"\n用户: {prompt_text}")
    print("\n正在思考...")

    try:
        # 收集助手回复
        assistant_text = ""

        def on_event(event):
            nonlocal assistant_text
            event_type = event.get("type", "")

            if event_type == "message_end":
                message = event.get("message")
                if message and getattr(message, "role", "") == "assistant":
                    # 提取文本内容
                    content = getattr(message, "content", [])
                    for item in content:
                        if getattr(item, "type", "") == "text":
                            text = getattr(item, "text", "")
                            assistant_text += text

        agent.subscribe(on_event)

        # 发送提示
        await agent.prompt(prompt_text)
        await agent.wait_for_idle()

        if assistant_text:
            print(f"\n助手: {assistant_text}")

        print(f"\n✅ 完成！对话历史: {len(agent.state.messages)} 条消息")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
