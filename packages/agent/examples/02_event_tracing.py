"""
示例 02: 完整事件追踪（Thinking + Tools）

学习目标：
- 验证所有事件类型都能正确发出
- 观察 text/thinking/toolcall 的 start/delta/end 事件
- 结合思考模式和工具调用

运行：
    uv run python examples/02_event_tracing.py
"""

from __future__ import annotations

import asyncio
from typing import Any

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ai.providers import KimiProvider
from ai.types import TextContent
from agent import Agent, AgentOptions, AgentTool, AgentToolResult


class CalculatorTool:
    """计算器工具"""

    name = "calculate"
    label = "计算器"
    description = "计算数学表达式。必须使用此工具计算，不要直接心算。"
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
        expression = params.get("expression", "")
        try:
            allowed_names = {"abs": abs, "max": max, "min": min, "pow": pow, "round": round}
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return AgentToolResult(
                content=[TextContent(text=f"{expression} = {result}")],
                details={"expression": expression, "result": result},
            )
        except Exception as e:
            return AgentToolResult(
                content=[TextContent(text=f"计算错误: {e}")],
                details={"error": str(e)},
            )


def create_event_logger():
    """创建事件日志记录器，追踪所有事件类型"""
    event_counts: dict[str, int] = {}
    event_sequence: list[str] = []

    def on_event(event: dict[str, Any]) -> None:
        event_type = event.get("type", "")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

        if event_type == "message_update":
            assistant_event = event.get("assistant_message_event")
            if assistant_event:
                inner_type = getattr(assistant_event, "type", "")
                event_sequence.append(f"message_update[{inner_type}]")

                # 打印详细事件信息
                delta = getattr(assistant_event, "delta", "")
                content_index = getattr(assistant_event, "content_index", -1)
                print(f"  📤 {inner_type:20s} index={content_index} delta_len={len(str(delta))}")
        elif event_type == "tool_execution_start":
            tool_name = event.get("toolName", "")
            args = event.get("args", {})
            print(f"  🔧 tool_execution_start: {tool_name}({args})")
        elif event_type == "tool_execution_end":
            tool_name = event.get("toolName", "")
            print(f"  ✅ tool_execution_end: {tool_name}")
        else:
            event_sequence.append(event_type)
            if event_type in [
                "message_start",
                "message_end",
                "turn_start",
                "turn_end",
                "agent_start",
                "agent_end",
            ]:
                print(f"  📍 {event_type}")

    def print_summary():
        print("\n" + "=" * 60)
        print("事件统计:")
        print("=" * 60)
        for event_type, count in sorted(event_counts.items()):
            print(f"  {event_type:30s}: {count:3d}")

        print("\n关键事件检查:")
        expected_events = [
            "text_start",
            "text_delta",
            "text_end",
            "thinking_start",
            "thinking_delta",
            "thinking_end",
            "toolcall_start",
            "toolcall_delta",
            "toolcall_end",
        ]
        for evt in expected_events:
            found = any(evt in seq for seq in event_sequence)
            status = "✅" if found else "❌"
            print(f"  {status} {evt}")

    return on_event, print_summary


async def main():
    print("=" * 60)
    print("示例 02: 完整事件追踪（Thinking + Tools）")
    print("=" * 60)
    print("\n本示例验证所有事件类型都能正确发出")

    # 获取 provider
    provider = KimiProvider()

    # 创建 stream_fn
    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    # 创建 Agent
    agent = Agent(AgentOptions(stream_fn=stream_fn))
    agent.set_model(provider.get_model())

    # 启用思考模式
    agent.set_thinking_level("medium")

    # 设置工具
    agent.set_tools([CalculatorTool()])

    # 创建事件追踪器
    on_event, print_summary = create_event_logger()
    agent.subscribe(on_event)

    try:
        # 发送需要计算的问题
        prompt = (
            "请解决以下问题，展示你的思考过程：\n"
            "一家商店苹果 5 元/斤，香蕉 3 元/斤。\n"
            "小明买了 2 斤苹果和 3 斤香蕉，请计算总价。\n"
            "请使用 calculate 工具进行计算。"
        )
        print(f"\n用户: {prompt}\n")
        print("事件流:")
        print("-" * 60)

        await agent.prompt(prompt)
        await agent.wait_for_idle()

        # 打印统计
        print_summary()

        # 显示对话历史
        print(f"\n对话历史: {len(agent.state.messages)} 条消息")
        for i, msg in enumerate(agent.state.messages, 1):
            role = getattr(msg, "role", "unknown")
            content = getattr(msg, "content", [])
            content_types = [getattr(c, "type", "?") for c in content]
            print(f"  {i}. {role}: {content_types}")

        print("\n✅ 完成！")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
