"""
示例 04: 多轮对话

学习目标：
- 维护对话历史
- 消息数组的构建与管理
- 实现交互式对话循环

运行：
    uv run python examples/04_conversation.py
"""

from __future__ import annotations

import asyncio

from ai.providers import KimiProvider
from ai.types import AssistantMessage, Context, UserMessage


async def main():
    print("=" * 60)
    print("示例 04: 多轮对话")
    print("=" * 60)

    provider = KimiProvider()
    model = provider.get_model()

    # 对话历史
    messages: list[UserMessage | AssistantMessage] = []

    # 预设欢迎语
    print("\n🤖 助手已就绪。输入 'quit' 或 'exit' 退出对话。\n")

    # 对话轮数限制
    max_turns = 3

    for turn in range(max_turns):
        # 模拟用户输入（实际应用中应该是 input()）
        if turn == 0:
            user_input = "你好，我叫小明"
        elif turn == 1:
            user_input = "我叫什么名字？"
        else:
            user_input = "刚才我们聊了什么？"

        print(f"用户: {user_input}")

        # 添加用户消息
        messages.append(UserMessage(text=user_input))

        # 构建上下文
        context = Context(messages=messages)

        try:
            # 获取助手回复
            response = await provider.complete(model=model, context=context)

            # 提取回复文本
            reply_text = ""
            for content in response.content:
                if content.type == "text":
                    reply_text += content.text

            print(f"助手: {reply_text}\n")

            # 保存助手回复到历史
            messages.append(response)

            # 显示当前对话统计
            print(f"  📊 当前对话: {len(messages)} 条消息")
            print(f"  📝 本轮 Token: {response.usage.total_tokens}")
            print()

        except Exception as e:
            print(f"错误: {e}")
            break

    print("=" * 60)
    print("对话结束")
    print("=" * 60)
    print(f"\n总消息数: {len(messages)}")
    print("\n对话历史:")
    for i, msg in enumerate(messages):
        role = "用户" if msg.role == "user" else "助手"
        content_preview = ""
        if msg.role == "user":
            content_preview = msg.content if isinstance(msg.content, str) else "[多模态内容]"
        else:
            # AssistantMessage
            texts = [c.text for c in msg.content if c.type == "text"]
            content_preview = "".join(texts)[:50] + "..."

        print(f"  [{i + 1}] {role}: {content_preview}")


if __name__ == "__main__":
    asyncio.run(main())
