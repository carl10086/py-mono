#!/usr/bin/env python3
"""
示例 03: AgentSession 与 Tools 集成

展示：
1. 使用内存 SessionManager
2. 集成 tools (write, bash, read, edit)
3. 让 Agent 在指定目录下创建 hello world Python 文件并运行

运行方式：
    cd packages/coding-agent && uv run python examples/03_agent_session_with_tools.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from ai.providers import KimiProvider
from coding_agent.agent_session import create_agent_session
from coding_agent.session.manager import SessionManager
from coding_agent.tools.bash import create_bash_tool
from coding_agent.tools.edit import create_edit_tool
from coding_agent.tools.read import create_read_tool
from coding_agent.tools.write import create_write_tool

TARGET_CWD = "/Users/carlyu/soft/tmp/hello"


def streaming_printer():
    """创建流式输出处理器"""

    def handler(event: dict) -> None:
        event_type = event.get("type", "")
        if event_type == "message_update":
            delta = event.get("delta", "")
            if delta:
                print(delta, end="", flush=True)
        elif event_type == "message_end":
            print()
        elif event_type == "tool_execution_start":
            tool_name = event.get("toolName", "")
            args = event.get("args", {})
            print(f"\n[工具调用: {tool_name}]")
            if args:
                for k, v in args.items():
                    print(f"   {k}: {v}")
        elif event_type == "tool_execution_end":
            result = event.get("result")
            if result and hasattr(result, "content"):
                content = result.content
                if content:
                    for item in content:
                        if hasattr(item, "text"):
                            text = item.text
                            if len(text) > 200:
                                text = text[:200] + "..."
                            print(f"\n[工具结果]: {text}")

    return handler


async def main() -> int:
    """主函数"""
    print("=" * 60)
    print("AgentSession 与 Tools 集成示例")
    print("=" * 60)
    print(f"\n目标目录: {TARGET_CWD}")

    os.makedirs(TARGET_CWD, exist_ok=True)

    sm = SessionManager.in_memory(TARGET_CWD)
    print(f"内存 SessionManager 创建成功")

    tools = {
        "read": create_read_tool(TARGET_CWD),
        "write": create_write_tool(TARGET_CWD),
        "edit": create_edit_tool(TARGET_CWD),
        "bash": create_bash_tool(TARGET_CWD),
    }
    print(f"工具集创建成功: {list(tools.keys())}")

    session = create_agent_session(
        cwd=TARGET_CWD,
        provider=KimiProvider(),
        system_prompt="你是一个有帮助的编程助手。",
        tools=list(tools.values()),
        session_manager=sm,
    )
    print(f"AgentSession 创建成功")

    session.subscribe(streaming_printer())

    print("\n" + "-" * 60)
    print("让 Agent 创建 hello.py 并运行...")
    print("-" * 60 + "\n")

    await session.prompt(
        f"在 {TARGET_CWD} 目录下创建一个 hello.py 文件，"
        "输出 'Hello, World!'，然后用 python 命令运行它。"
    )

    print("\n" + "-" * 60)
    print("验证文件是否创建成功...")
    print("-" * 60)

    hello_path = os.path.join(TARGET_CWD, "hello.py")
    if os.path.exists(hello_path):
        print(f"✅ {hello_path} 已创建")
        with open(hello_path, "r", encoding="utf-8") as f:
            content = f.read()
            print(f"文件内容:\n{content}")
    else:
        print(f"❌ {hello_path} 未找到")

    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
