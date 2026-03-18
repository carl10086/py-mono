"""
示例 09: 真实工具调用 + Steering 演示

学习目标：
- 使用真实 LLM 调用工具
- 展示 steering 如何改变工具链的回复方向

场景：
1. 用户要求计算多个复杂表达式
2. Agent 调用计算工具逐个计算
3. 在计算过程中，用户改变主意
4. Agent 完成计算后，回复用户的新问题而非原计划

运行：
    uv run python examples/09_real_tools_steering.py
"""

from __future__ import annotations

import asyncio
from typing import Any

from ai.providers import KimiProvider
from ai.types import UserMessage
from agent import Agent, AgentOptions, AgentTool, AgentToolResult


class CalculatorTool:
    """计算器工具 - 安全计算数学表达式"""

    name = "calculate"
    label = "计算器"
    description = "计算数学表达式，支持 + - * / 和括号，如 '2+3*4'、'(10+5)/3'"
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式，如 '2+3*4'",
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
                content=[TextContent(text=f"{result}")],
                details={"expression": expression, "result": result},
            )
        except Exception as e:
            from ai.types import TextContent

            return AgentToolResult(
                content=[TextContent(text=f"错误: {e}")],
                details={"error": str(e)},
            )


async def main():
    print("=" * 70)
    print("示例 09: 真实工具调用 + Steering 演示")
    print("=" * 70)
    print()
    print("场景：让 AI 计算多个表达式，中途改变主意")
    print()
    print("预期流程：")
    print("  1️⃣  用户：计算 123*456、789/3 和 1000-567")
    print("  2️⃣  AI：调用 calculate 工具计算第一个表达式...")
    print("  3️⃣  ⚡ 用户打断：不用算了，2+2等于几？")
    print("  4️⃣  AI：继续完成剩余计算工具调用...")
    print("  5️⃣  AI：回复 steering 的问题（2+2=4），而非原计划的结果汇总")
    print()
    print("⚠️ 注意：这展示了 steering 的核心价值——改变回复方向")
    print()

    # 初始化 Provider
    provider = KimiProvider()

    # 创建 Agent
    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    agent = Agent(
        AgentOptions(
            stream_fn=stream_fn,
            tool_execution="sequential",  # 顺序执行，便于观察
        )
    )
    agent.set_model(provider.get_model())

    # 创建并设置工具
    calculator = CalculatorTool()
    agent.set_tools([calculator])

    # 追踪事件
    events_log: list[str] = []
    tool_count = 0
    steering_inserted = False

    def on_event(event):
        nonlocal tool_count, steering_inserted
        event_type = event.get("type", "")

        if event_type == "tool_execution_start":
            tool_count += 1
            tool_name = event.get("toolName", "")
            args = event.get("args", {})
            expr = args.get("expression", "") if isinstance(args, dict) else ""
            events_log.append(f"🔧 [{tool_count}] 开始计算: {expr}")

            # 在第一个工具开始后插入 steering
            if tool_count == 1 and not steering_inserted:
                steering_inserted = True
                print("\n" + "=" * 70)
                print("⚡ [steering 插入] 用户改变主意！")
                print('   用户说："不用算了，直接告诉我 2+2 等于几"')
                print("=" * 70 + "\n")
                agent.steer(UserMessage(text="不用算了，直接告诉我 2+2 等于几"))

        elif event_type == "tool_execution_end":
            tool_name = event.get("toolName", "")
            result = event.get("result", {})
            content = result.content if hasattr(result, "content") else []
            text = content[0].text if content else ""
            events_log.append(f"✅ 计算结果: {text}")

        elif event_type == "turn_start":
            events_log.append("🔄 Turn 开始")

        elif event_type == "turn_end":
            tool_results = event.get("tool_results", [])
            if tool_results:
                events_log.append(f"🏁 Turn 结束 (处理了 {len(tool_results)} 个工具)")
            else:
                events_log.append("🏁 Turn 结束 (无工具)")

        elif event_type == "agent_end":
            events_log.append("✨ Agent 结束")

        elif event_type == "message_start":
            msg = event.get("message")
            role = getattr(msg, "role", "unknown")
            if role == "user":
                content = getattr(msg, "content", "")
                if isinstance(content, list) and content:
                    text = getattr(content[0], "text", "")
                elif isinstance(content, str):
                    text = content
                else:
                    text = str(content)
                if len(text) > 50:
                    text = text[:50] + "..."
                events_log.append(f"💬 用户: {text}")
            elif role == "assistant":
                content = getattr(msg, "content", [])
                if content and hasattr(content[0], "text"):
                    text = content[0].text
                    if len(text) > 60:
                        text = text[:60] + "..."
                    events_log.append(f"🤖 AI回复: {text}")

    agent.subscribe(on_event)

    # 发送初始请求
    print("=" * 70)
    print("开始对话")
    print("=" * 70)
    print()
    print("用户：计算 123*456、789/3 和 1000-567")
    print()

    await agent.prompt("请计算以下三个表达式的结果：123*456、789/3 和 1000-567")
    await agent.wait_for_idle()

    # 显示执行日志
    print()
    print("=" * 70)
    print("执行日志:")
    print("=" * 70)
    for log in events_log:
        print(f"  {log}")

    # 分析结果
    print()
    print("=" * 70)
    print("结果分析")
    print("=" * 70)

    messages = agent.state.messages
    print(f"\n总消息数: {len(messages)}")
    print("\n完整对话流程:")
    for i, msg in enumerate(messages, 1):
        role = getattr(msg, "role", "unknown")
        content = getattr(msg, "content", [])
        if isinstance(content, list) and content:
            text = (
                getattr(content[0], "text", "") if hasattr(content[0], "text") else str(content[0])
            )
        elif isinstance(content, str):
            text = content
        else:
            text = str(content)

        # 截断长文本
        if len(text) > 80:
            text = text[:80] + "..."

        print(f"  {i}. {role}: {text}")

    # 检查 steering 效果
    user_msgs = [m for m in messages if getattr(m, "role", "") == "user"]
    assistant_msgs = [m for m in messages if getattr(m, "role", "") == "assistant"]

    has_steering = len(user_msgs) >= 2  # 至少有两个 user 消息（初始 + steering）

    print()
    if has_steering and len(assistant_msgs) >= 2:
        print("✅ 成功！Steering 机制生效：")
        print()
        print("流程说明：")
        print("  1️⃣  AI 收到初始请求，调用 3 个计算工具")
        print("  2️⃣  在第一个工具执行时，插入 steering 消息")
        print("  3️⃣  AI 继续完成剩余计算工具调用（顺序执行）")
        print("  4️⃣  AI 看到 steering 消息，改变了回复方向")
        print()
        print("关键验证：")
        # 检查最后一个 assistant 消息是否包含 "4" 或回答简单问题
        last_reply = ""
        if assistant_msgs:
            last_content = getattr(assistant_msgs[-1], "content", [])
            if last_content and hasattr(last_content[0], "text"):
                last_reply = last_content[0].text

        if "4" in last_reply or "四" in last_reply or "等于" in last_reply:
            print(f"  ✅ 最后回复确实回答了 steering 的问题")
            print(f"     回复内容: {last_reply[:100]}...")
        else:
            print(f"  ⚠️  最后回复可能不是回答 steering 的问题")
            print(f"     回复内容: {last_reply[:100]}...")
        print()
        print("这就是 steering 的核心价值：")
        print("  在工具链执行过程中插入新指令，改变最终回复方向！")
    else:
        print(f"⚠️  steering 可能未生效")
        print(f"   user 消息数: {len(user_msgs)}, assistant 消息数: {len(assistant_msgs)}")
        print(f"   期望: user >= 2, assistant >= 2")

    print()


if __name__ == "__main__":
    asyncio.run(main())
