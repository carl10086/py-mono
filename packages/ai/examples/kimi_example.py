"""
KimiProvider 使用示例

展示如何使用 KimiProvider 进行流式对话、启用 reasoning、使用工具等。

运行前请设置环境变量：
    export KIMI_API_KEY=your-api-key

运行示例：
    cd packages/ai
    uv run python examples/kimi_example.py
"""

from __future__ import annotations

import asyncio
import os

from ai.providers import KimiProvider
from ai.types import Context, Model, Tool, UserMessage


async def basic_chat():
    """基础对话示例"""
    print("=" * 50)
    print("示例 1: 基础对话")
    print("=" * 50)

    # 检查 API 密钥
    if not os.environ.get("KIMI_API_KEY") and not os.environ.get("API_KEY"):
        print("错误：请设置 KIMI_API_KEY 或 API_KEY 环境变量")
        return

    # 创建 provider
    provider = KimiProvider(model="kimi-k2-turbo-preview")

    # 构建上下文
    context = Context(
        system_prompt="你是一个有帮助的 AI 助手，回答简洁明了。",
        messages=[UserMessage(content="你好，请介绍一下自己")],
    )

    # 获取模型配置
    model = provider.get_model()

    # 流式生成
    print("助手：", end="", flush=True)
    stream = provider.stream_simple(model=model, context=context)

    async for event in stream:
        match event.type:
            case "text_delta":
                print(event.delta, end="", flush=True)
            case "done":
                print("\n")

    print("✓ 对话完成\n")


async def chat_with_reasoning():
    """启用 Reasoning 的对话示例"""
    print("=" * 50)
    print("示例 2: 启用 Reasoning")
    print("=" * 50)

    if not os.environ.get("KIMI_API_KEY") and not os.environ.get("API_KEY"):
        print("错误：请设置 KIMI_API_KEY 或 API_KEY 环境变量")
        return

    # 创建 provider 并启用 reasoning
    provider = KimiProvider(model="kimi-k2-turbo-preview")
    provider = provider.with_thinking("medium")

    print(f"Thinking 等级: {provider.thinking_effort}")

    context = Context(
        messages=[UserMessage(content="解这个方程: 2x + 5 = 13")],
    )

    model = provider.get_model()
    stream = provider.stream_simple(model=model, context=context)

    thinking_content = []
    answer_content = []
    in_thinking = False

    async for event in stream:
        match event.type:
            case "thinking_start":
                in_thinking = True
                print("\n[思考过程]")
            case "thinking_delta":
                thinking_content.append(event.delta)
                print(event.delta, end="", flush=True)
            case "thinking_end":
                in_thinking = False
                print("\n[思考结束]")
            case "text_start":
                print("\n[回答]")
            case "text_delta":
                answer_content.append(event.delta)
                print(event.delta, end="", flush=True)
            case "done":
                print("\n")

    print(f"\n✓ 思考内容长度: {len(''.join(thinking_content))} 字符")
    print(f"✓ 回答内容长度: {len(''.join(answer_content))} 字符\n")


async def chat_with_tools():
    """使用工具的对话示例"""
    print("=" * 50)
    print("示例 3: 使用工具")
    print("=" * 50)

    if not os.environ.get("KIMI_API_KEY") and not os.environ.get("API_KEY"):
        print("错误：请设置 KIMI_API_KEY 或 API_KEY 环境变量")
        return

    # 定义计算器工具
    calculator_tool = Tool(
        name="calculator",
        description="执行数学计算，支持 + - * / 和括号",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，例如 '2 + 3 * 4'",
                },
            },
            "required": ["expression"],
        },
    )

    provider = KimiProvider(model="kimi-k2-turbo-preview")

    context = Context(
        system_prompt="你可以使用计算器工具来帮助用户进行数学计算。",
        messages=[UserMessage(content="帮我计算 123 乘以 456 是多少")],
        tools=[calculator_tool],
    )

    model = provider.get_model()
    stream = provider.stream(model=model, context=context)

    tool_calls = []

    async for event in stream:
        match event.type:
            case "toolcall_start":
                print(f"\n[工具调用开始]")
            case "toolcall_delta":
                print(f"[工具参数增量: {event.delta}]")
            case "toolcall_end":
                tool_call = event.tool_call
                tool_calls.append(tool_call)
                print(f"\n[工具调用完成]")
                print(f"  工具名: {tool_call.name}")
                print(f"  参数: {tool_call.arguments}")

                # 模拟执行工具
                if tool_call.name == "calculator":
                    expr = tool_call.arguments.get("expression", "")
                    try:
                        result = eval(expr)  # noqa: S307
                        print(f"  结果: {result}")

                        # 将结果返回给模型
                        context.messages.append(
                            UserMessage(content=f"计算器结果: {expr} = {result}")
                        )
                    except Exception as e:
                        print(f"  错误: {e}")
            case "text_delta":
                print(event.delta, end="", flush=True)
            case "done":
                print("\n")

    print(f"✓ 工具调用次数: {len(tool_calls)}\n")


async def list_models():
    """列出支持的模型"""
    print("=" * 50)
    print("示例 4: 列出支持的模型")
    print("=" * 50)

    provider = KimiProvider()

    print("\n支持的模型:")
    for model in provider.models:
        print(f"  - {model.id}: {model.name}")
        print(f"    上下文窗口: {model.context_window} tokens")
        print(f"    最大输出: {model.max_tokens} tokens")
        print(f"    支持 Reasoning: {model.capabilities.reasoning}")
        print()


async def compare_thinking_levels():
    """对比不同 thinking 等级的配置"""
    print("=" * 50)
    print("示例 5: Thinking 等级对比")
    print("=" * 50)

    provider = KimiProvider()

    levels = ["off", "minimal", "low", "medium", "high", "xhigh"]

    print("\nThinking 等级配置:")
    for level in levels:
        p = provider.with_thinking(level)  # type: ignore[arg-type]
        effort = p.thinking_effort

        # 获取实际的 thinking 配置
        kwargs = p._get_generation_kwargs()
        thinking_config = kwargs.get("thinking", {})

        if thinking_config.get("type") == "disabled":
            print(f"  {level:8} -> 禁用")
        else:
            budget = thinking_config.get("budget_tokens", 0)
            print(f"  {level:8} -> {budget:5} tokens")

    print()


async def main():
    """主函数"""
    print("\n" + "=" * 50)
    print("KimiProvider 使用示例")
    print("=" * 50 + "\n")

    # 运行示例
    await list_models()
    await compare_thinking_levels()

    # 以下示例需要 API 密钥
    if os.environ.get("KIMI_API_KEY") or os.environ.get("API_KEY"):
        await basic_chat()
        await chat_with_reasoning()
        await chat_with_tools()
    else:
        print("跳过需要 API 密钥的示例")
        print("请设置 KIMI_API_KEY 或 API_KEY 环境变量\n")


if __name__ == "__main__":
    asyncio.run(main())
