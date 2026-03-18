"""
示例 05: Agent 状态管理

学习目标：
- 查看和修改 Agent 状态
- 重置对话
- 保存和恢复状态

运行：
    uv run python examples/05_state_management.py
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ai.providers import KimiProvider
from agent import Agent, AgentOptions


@dataclass
class AgentSnapshot:
    """Agent 状态快照"""

    system_prompt: str
    message_count: int


async def main():
    print("=" * 60)
    print("示例 05: Agent 状态管理")
    print("=" * 60)

    # 获取 provider
    provider = KimiProvider()

    # 创建 stream_fn
    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    # 创建 Agent
    agent = Agent(AgentOptions(stream_fn=stream_fn))
    agent.set_model(provider.get_model())
    agent.set_system_prompt("你是一个乐于助人的助手。")

    # 快照列表
    snapshots: list[tuple[str, AgentSnapshot]] = []

    def take_snapshot(name: str):
        snapshot = AgentSnapshot(
            system_prompt=agent.state.system_prompt,
            message_count=len(agent.state.messages),
        )
        snapshots.append((name, snapshot))

    def print_state(label: str):
        print(f"\n[{label}]")
        print(f"  系统提示: {agent.state.system_prompt[:30]}...")
        print(f"  消息数: {len(agent.state.messages)}")
        print(f"  是否流式: {agent.state.is_streaming}")

    try:
        # 初始状态
        take_snapshot("初始")
        print_state("初始状态")

        # 第一轮对话
        print("\n[第一轮对话]")
        await agent.prompt("你好！")
        await agent.wait_for_idle()
        take_snapshot("第一轮后")
        print_state("第一轮后")

        # 第二轮对话
        print("\n[第二轮对话]")
        await agent.prompt("今天天气怎么样？")
        await agent.wait_for_idle()
        take_snapshot("第二轮后")
        print_state("第二轮后")

        # 重置
        print("\n[重置 Agent]")
        agent.reset()
        take_snapshot("重置后")
        print_state("重置后")

        # 打印所有快照
        print("\n" + "=" * 60)
        print("状态快照历史")
        print("=" * 60)
        for name, snapshot in snapshots:
            print(f"\n{name}:")
            print(f"  系统提示: {snapshot.system_prompt[:30]}...")
            print(f"  消息数: {snapshot.message_count}")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
