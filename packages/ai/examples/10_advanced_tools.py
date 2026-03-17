"""
示例 10: 复杂工具链调用

学习目标：
- 多工具组合使用
- 工具依赖与链式调用
- 并行工具调用

运行：
    uv run python examples/10_advanced_tools.py
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from ai.providers import KimiProvider
from ai.types import (
    AssistantMessage,
    Context,
    TextContent,
    Tool,
    ToolResultMessage,
    UserMessage,
)


class SearchParams(BaseModel):
    """搜索参数"""

    query: str = Field(description="搜索关键词")
    limit: int = Field(default=5, description="返回结果数量")


class WeatherParams(BaseModel):
    """天气参数"""

    location: str = Field(description="地点")
    date: str = Field(default="today", description="日期")


class CalculateParams(BaseModel):
    """计算参数"""

    operation: str = Field(description="操作类型: add, subtract, multiply, divide")
    a: float = Field(description="第一个数字")
    b: float = Field(description="第二个数字")


def mock_search(query: str, limit: int) -> list[dict[str, Any]]:
    """模拟搜索功能"""
    mock_results = {
        "Python": [
            {
                "title": "Python 官方文档",
                "url": "https://docs.python.org",
                "snippet": "Python 编程语言官方文档",
            },
            {
                "title": "Python 教程",
                "url": "https://docs.python.org/tutorial",
                "snippet": "适合初学者的 Python 教程",
            },
        ],
        "天气": [
            {"title": "天气预报", "url": "https://weather.com", "snippet": "全球天气预报服务"},
        ],
    }
    return mock_results.get(query, [{"title": f"搜索结果: {query}", "snippet": "模拟搜索结果"}])[
        :limit
    ]


def mock_weather(location: str, date: str) -> dict[str, Any]:
    """模拟天气查询"""
    weather_data = {
        "北京": {"temperature": 25, "condition": "晴朗", "humidity": "45%"},
        "上海": {"temperature": 22, "condition": "多云", "humidity": "65%"},
    }
    return weather_data.get(location, {"temperature": 20, "condition": "未知", "humidity": "50%"})


def mock_calculate(operation: str, a: float, b: float) -> dict[str, Any]:
    """模拟计算功能"""
    operations = {
        "add": a + b,
        "subtract": a - b,
        "multiply": a * b,
        "divide": a / b if b != 0 else float("inf"),
    }
    result = operations.get(operation, 0)
    return {"operation": operation, "a": a, "b": b, "result": result}


# 工具定义
TOOLS = [
    Tool(
        name="search",
        description="搜索互联网信息",
        parameters=SearchParams,
    ),
    Tool(
        name="get_weather",
        description="获取指定地点的天气",
        parameters=WeatherParams,
    ),
    Tool(
        name="calculate",
        description="执行数学计算",
        parameters=CalculateParams,
    ),
]


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """执行工具"""
    try:
        if name == "search":
            result = mock_search(**arguments)
        elif name == "get_weather":
            result = mock_weather(**arguments)
        elif name == "calculate":
            result = mock_calculate(**arguments)
        else:
            return json.dumps({"error": f"未知工具: {name}"})

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


async def run_conversation(
    provider: KimiProvider,
    model: Any,
    messages: list,
    max_iterations: int = 5,
) -> AssistantMessage:
    """运行多轮对话直到完成"""

    for iteration in range(max_iterations):
        print(f"\n  迭代 {iteration + 1}/{max_iterations}...")

        context = Context(messages=messages, tools=TOOLS)
        response = await provider.complete(model=model, context=context)

        # 检查是否有工具调用
        tool_calls = [item for item in response.content if item.type == "toolCall"]

        if not tool_calls:
            print("  没有工具调用，对话完成")
            return response

        print(f"  检测到 {len(tool_calls)} 个工具调用")

        # 执行工具
        tool_results = []
        for call in tool_calls:
            print(f"    执行: {call.name}({json.dumps(call.arguments, ensure_ascii=False)})")
            result = execute_tool(call.name, call.arguments)
            print(f"    结果: {result[:100]}...")

            tool_results.append(
                ToolResultMessage(
                    tool_call_id=call.id,
                    tool_name=call.name,
                    content=[TextContent(text=result)],
                )
            )

        # 更新消息历史
        messages.append(response)
        messages.extend(tool_results)

    print("  达到最大迭代次数")
    return response


async def main():
    print("=" * 60)
    print("示例 10: 复杂工具链调用")
    print("=" * 60)

    provider = KimiProvider()
    model = provider.get_model()

    # 测试用例 1: 搜索 + 天气组合
    print("\n" + "=" * 60)
    print("测试 1: 搜索和天气组合")
    print("=" * 60)

    messages1 = [UserMessage(text="搜索 Python 相关信息，并告诉我北京的天气如何。")]

    try:
        result1 = await run_conversation(provider, model, messages1)
        print("\n最终结果:")
        for content in result1.content:
            if content.type == "text":
                print(content.text[:200] + "...")
    except Exception as e:
        print(f"错误: {e}")

    # 测试用例 2: 计算链
    print("\n" + "=" * 60)
    print("测试 2: 复杂计算链")
    print("=" * 60)

    messages2 = [UserMessage(text="计算 100 + 200 的结果，然后将结果乘以 3。")]

    try:
        result2 = await run_conversation(provider, model, messages2)
        print("\n最终结果:")
        for content in result2.content:
            if content.type == "text":
                print(content.text)
    except Exception as e:
        print(f"错误: {e}")

    # 测试用例 3: 多工具组合
    print("\n" + "=" * 60)
    print("测试 3: 多工具场景")
    print("=" * 60)

    messages3 = [
        UserMessage(text="帮我搜索 Python 编程，查一下上海的天气，然后计算 50 除以 2 的结果。")
    ]

    try:
        result3 = await run_conversation(provider, model, messages3)
        print("\n最终结果:")
        for content in result3.content:
            if content.type == "text":
                print(content.text[:300] + "...")
    except Exception as e:
        print(f"错误: {e}")

    print("\n" + "=" * 60)
    print("复杂工具链演示完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
