"""
示例 01: 基础 Agent 使用（流式输出版）

学习目标：
- 创建 Agent 实例
- 实时流式输出响应
- 使用 utils 简化代码

运行：
    uv run python examples/01_basic_agent.py
"""

from __future__ import annotations

import asyncio

from ai import ThinkingLevel
from ai.providers import KimiProvider
from agent import Agent, AgentOptions

# 导入工具
import sys
from pathlib import Path

# 添加 examples 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from utils import streaming_printer


async def main():
    print("=" * 60)
    print("示例 01: 基础 Agent 使用（流式输出版）")
    print("=" * 60)

    # 获取模型和 provider（启用 thinking 模式）
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
    print(f"\n用户: {prompt_text}\n")

    try:
        # 使用工具创建流式处理器
        agent.subscribe(streaming_printer(show_thinking=True))

        # 发送提示
        await agent.prompt(prompt_text)
        await agent.wait_for_idle()

        print(f"\n\n✅ 完成！对话历史: {len(agent.state.messages)} 条消息")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
