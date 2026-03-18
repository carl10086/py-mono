"""
示例 07: Agent 工具调用

学习目标：
- 定义和使用 AgentTool
- 理解工具调用生命周期
- 查看工具执行事件
- 使用真实模型触发工具调用

运行：
    uv run python examples/07_tools.py
"""

from __future__ import annotations

import asyncio
from typing import Any

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ai.providers import KimiProvider
from ai.types import UserMessage
from agent import Agent, AgentOptions, AgentTool, AgentToolResult

from utils import streaming_printer


class CalculatorTool:
    """计算器工具 - 计算数学表达式"""

    name = "calculate"
    label = "计算器"
    description = "计算数学表达式，如 1+2, sin(0.5) 等。重要：必须使用此工具计算，不要直接心算。"
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "要计算的数学表达式",
            }
        },
        "required": ["expression"],
    }

    async def execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any = None,
        on_update: Any = None,
    ) -> AgentToolResult[Any]:
        """执行计算"""
        expression = params.get("expression", "")
        try:
            # 安全计算：只允许基本运算
            allowed_names = {
                "abs": abs,
                "max": max,
                "min": min,
                "pow": pow,
                "round": round,
            }
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            from ai.types import TextContent

            return AgentToolResult(
                content=[TextContent(text=f"{expression} = {result}")],
                details={"expression": expression, "result": result},
            )
        except Exception as e:
            from ai.types import TextContent

            return AgentToolResult(
                content=[TextContent(text=f"计算错误: {e}")],
                details={"error": str(e)},
            )


class EchoTool:
    """回显工具 - 返回输入的内容"""

    name = "echo"
    label = "回显"
    description = "将输入的内容原样返回"
    parameters = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "要回显的消息",
            }
        },
        "required": ["message"],
    }

    async def execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: Any = None,
        on_update: Any = None,
    ) -> AgentToolResult[Any]:
        """执行回显"""
        message = params.get("message", "")
        from ai.types import TextContent

        return AgentToolResult(
            content=[TextContent(text=f"Echo: {message}")],
            details={"original": message},
        )


async def main():
    print("=" * 60)
    print("示例 07: Agent 工具调用")
    print("=" * 60)
    print("\n本示例演示真实模型下的工具调用生命周期")

    # 获取 provider
    provider = KimiProvider()

    # 创建 stream_fn
    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    # 创建 Agent
    agent = Agent(AgentOptions(stream_fn=stream_fn))
    agent.set_model(provider.get_model())

    # 创建工具
    calculator = CalculatorTool()
    echo = EchoTool()
    agent.set_tools([calculator, echo])

    # 追踪工具调用
    tool_events: list[str] = []
    tool_count = 0
    has_tool_calls = False

    def on_event(event):
        nonlocal tool_count, has_tool_calls
        event_type = event.get("type", "")

        if event_type == "tool_execution_start":
            has_tool_calls = True
            tool_count += 1
            tool_name = event.get("toolName", "")
            args = event.get("args", {})
            expr = args.get("expression", args.get("message", ""))
            tool_events.append(f"🔧 [{tool_count}] 开始: {tool_name}({expr})")

        elif event_type == "tool_execution_end":
            tool_name = event.get("toolName", "")
            tool_events.append(f"✅ 完成: {tool_name}")

    # 组合处理器：流式输出 + 工具追踪
    agent.subscribe(streaming_printer(show_thinking=True))
    agent.subscribe(on_event)

    try:
        # 使用明确的提示词，要求调用工具
        print("\n发送提示：计算表达式并回显消息")
        print("提示词已优化，明确要求使用工具...\n")

        # 关键：使用强制工具调用的提示词
        prompt = (
            "你有 calculate 和 echo 两个工具。"
            "请按顺序执行以下操作（必须使用工具）：\n"
            "1. 使用 calculate 工具计算 2+3*4\n"
            "2. 使用 calculate 工具计算 15/3\n"
            "3. 使用 echo 工具回显 'Hello, Tool!'\n"
            "4. 最后总结所有结果"
        )

        print(f"用户: {prompt}\n")
        await agent.prompt(prompt)
        await agent.wait_for_idle()

        print("\n" + "=" * 60)
        print("工具调用日志:")
        print("=" * 60)
        if tool_events:
            for log in tool_events:
                print(f"  {log}")
        else:
            print("  ⚠️  未检测到工具调用")

        print(f"\n总消息数: {len(agent.state.messages)}")

        # 验证工具调用
        if has_tool_calls:
            print(f"\n✅ 成功！检测到 {tool_count} 次工具调用")
            print("\n工具生命周期：")
            print("  1. Agent 收到提示 → 生成 toolCall")
            print("  2. 执行工具 → tool_execution_start")
            print("  3. 工具完成 → tool_execution_end")
            print("  4. 工具结果被添加到上下文")
            print("  5. Agent 继续生成最终回复")
        else:
            print("\n⚠️  LLM 没有调用工具，直接回答了问题")
            print("   这是正常的，取决于模型的判断")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
