"""
示例 03: 工具调用 (Function Calling)

学习目标：
- 定义和使用 Tool
- 处理 ToolCall 和 ToolResultMessage
- 完成完整的工具调用循环

运行：
    uv run python examples/03_tool_calling.py
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

from pydantic import BaseModel, Field

from ai.providers import KimiProvider
from ai.types import (
    Context,
    TextContent,
    Tool,
    ToolResultMessage,
    UserMessage,
)


class GetWeatherParams(BaseModel):
    """获取天气参数"""

    city: str = Field(description="城市名称，如 '北京'、'上海'")
    date: str | None = Field(default=None, description="日期，格式 YYYY-MM-DD，不传则使用今天")


class CalculatorParams(BaseModel):
    """计算器参数"""

    expression: str = Field(description="数学表达式，如 '2 + 3 * 4'")


def get_weather(city: str, date: str | None = None) -> str:
    """模拟获取天气"""
    today = date or datetime.now().strftime("%Y-%m-%d")
    # 模拟数据
    weather_map = {
        "北京": "晴天，25°C",
        "上海": "多云，22°C",
        "深圳": "小雨，28°C",
    }
    weather = weather_map.get(city, "晴朗，20°C")
    return json.dumps({"city": city, "date": today, "weather": weather}, ensure_ascii=False)


def calculator(expression: str) -> str:
    """安全计算器"""
    try:
        # 只允许基本运算符和数字
        allowed_chars = set("0123456789+-*/(). ")
        if not all(c in allowed_chars for c in expression):
            return json.dumps({"error": "表达式包含非法字符"}, ensure_ascii=False)
        result = eval(expression, {"__builtins__": {}}, {})
        return json.dumps({"expression": expression, "result": result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


async def main():
    print("=" * 60)
    print("示例 03: 工具调用")
    print("=" * 60)

    # 定义工具
    tools = [
        Tool(
            name="get_weather",
            description="获取指定城市的天气信息",
            parameters=GetWeatherParams,
        ),
        Tool(
            name="calculator",
            description="计算数学表达式",
            parameters=CalculatorParams,
        ),
    ]

    provider = KimiProvider()
    model = provider.get_model()

    # 构建带工具的上下文
    context = Context(
        messages=[
            UserMessage(text="北京的天气怎么样？顺便计算一下 123 + 456 * 2 等于多少？"),
        ],
        tools=tools,
    )

    print(f"\n用户: {context.messages[0].content}")
    print("\n等待助手响应...")

    try:
        # 第一次调用 - 获取工具调用请求
        response = await provider.complete(model=model, context=context)

        print("\n" + "=" * 60)
        print("助手响应 (第 1 轮)")
        print("=" * 60)

        # 检查是否有工具调用
        tool_calls = [item for item in response.content if item.type == "toolCall"]

        if tool_calls:
            print(f"助手请求调用 {len(tool_calls)} 个工具:")

            # 显示工具调用详情
            for call in tool_calls:
                print(f"\n  📞 工具: {call.name}")
                print(f"     ID: {call.id}")
                print(f"     参数: {json.dumps(call.arguments, ensure_ascii=False)}")

            # 执行工具并构建结果消息
            tool_results = []
            for call in tool_calls:
                print(f"\n  ⚙️  执行 {call.name}...")

                if call.name == "get_weather":
                    result = get_weather(**call.arguments)
                elif call.name == "calculator":
                    result = calculator(**call.arguments)
                else:
                    result = json.dumps({"error": f"未知工具: {call.name}"}, ensure_ascii=False)

                print(f"     结果: {result}")

                tool_results.append(
                    ToolResultMessage(
                        tool_call_id=call.id,
                        tool_name=call.name,
                        content=[TextContent(text=result)],
                    )
                )

            # 构建第二轮对话上下文
            messages = list(context.messages)
            messages.append(response)  # 助手消息（包含 tool calls）
            messages.extend(tool_results)  # 工具结果

            context2 = Context(messages=messages, tools=tools)

            print("\n" + "=" * 60)
            print("发送工具结果给助手...")
            print("=" * 60)

            # 第二次调用 - 获取最终回复
            final_response = await provider.complete(model=model, context=context2)

            print("\n" + "=" * 60)
            print("助手最终回复")
            print("=" * 60)

            for content in final_response.content:
                if content.type == "text":
                    print(content.text)

            print(f"\n总 Token 数: {final_response.usage.total_tokens}")
        else:
            # 没有工具调用，直接输出文本
            for content in response.content:
                if content.type == "text":
                    print(content.text)

    except Exception as e:
        print(f"\n错误: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
