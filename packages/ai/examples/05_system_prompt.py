"""
示例 05: 系统提示与角色设定

学习目标：
- 使用 system_prompt 设定助手角色
- 不同角色的行为差异
- 系统提示对对话的影响

运行：
    uv run python examples/system_prompt.py
"""

from __future__ import annotations

import asyncio

from ai.providers.anthropic import AnthropicProvider
from ai.types import Context, Model, ModelCapabilities, ModelCost, UserMessage


async def chat_with_persona(system_prompt: str, user_message: str, persona_name: str) -> str:
    """使用指定角色进行对话"""

    model = Model(
        id="claude-3-5-sonnet-20241022",
        name="Claude 3.5 Sonnet",
        api="anthropic-messages",
        provider="anthropic",
        capabilities=ModelCapabilities(input=["text"]),
        cost=ModelCost(input=0, output=0, cache_read=0, cache_write=0),
        context_window=262144,
        max_tokens=2048,
    )

    context = Context(
        system_prompt=system_prompt,
        messages=[UserMessage(text=user_message)],
    )

    provider = AnthropicProvider()
    response = await provider.complete(model=model, context=context)

    # 提取文本回复
    texts = [c.text for c in response.content if c.type == "text"]
    return "".join(texts)


async def main():
    print("=" * 60)
    print("示例 05: 系统提示与角色设定")
    print("=" * 60)

    user_message = "请用一句话介绍 Python 编程语言。"

    print(f"\n用户问题: {user_message}\n")

    # 定义不同角色
    personas = [
        {
            "name": "技术专家",
            "prompt": """你是一位资深的软件工程师和技术专家。
你的回答应该专业、准确，包含技术细节。
使用专业术语，但确保解释清晰。""",
        },
        {
            "name": "小学老师",
            "prompt": """你是一位和蔼可亲的小学老师。
你的回答应该简单易懂，使用生动的比喻。
避免复杂的技术术语，用孩子们能理解的语言。""",
        },
        {
            "name": "诗人",
            "prompt": """你是一位浪漫的诗人。
你的回答应该优美、富有想象力，使用修辞手法。
用诗意的语言表达技术概念。""",
        },
    ]

    for persona in personas:
        print("=" * 60)
        print(f"角色: {persona['name']}")
        print("=" * 60)
        print(f"System Prompt: {persona['prompt'][:100]}...")
        print()

        try:
            response = await chat_with_persona(
                system_prompt=persona["prompt"],
                user_message=user_message,
                persona_name=persona["name"],
            )
            print(f"回复: {response}\n")
        except Exception as e:
            print(f"错误: {e}\n")

    print("=" * 60)
    print("演示完成")
    print("=" * 60)
    print("\n观察不同角色对同一个问题的回答差异。")


if __name__ == "__main__":
    asyncio.run(main())
