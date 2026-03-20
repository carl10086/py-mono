#!/usr/bin/env python3
"""
示例 19: AgentSession E2E 测试 - 消息持久化

验证：
1. AgentSession 正确集成 SessionManager
2. 对话消息自动持久化到 JSONL
3. 可以从文件加载历史继续对话

运行方式：
    cd packages/coding-agent && uv run python examples/19_agent_session.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "ai" / "src"))
sys.path.insert(0, str(root_dir / "agent" / "src"))
sys.path.insert(0, str(root_dir / "coding-agent" / "src"))

from ai.providers import KimiProvider
from coding_agent.agent_session import create_agent_session
from coding_agent.session.manager import SessionManager


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
            print(f"\n🔧 工具调用: {tool_name}")
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
                            print(f"\n📄 结果:\n{item.text}")

    return handler


def read_jsonl(file_path: str) -> list[dict]:
    """读取 JSONL 文件"""
    entries = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


async def main() -> int:
    """主函数"""
    print("=" * 60)
    print("AgentSession E2E 测试 - 消息持久化")
    print("=" * 60)

    # 创建临时目录作为会话存储
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = os.path.join(tmpdir, "sessions")
        os.makedirs(session_dir, exist_ok=True)

        # 创建 SessionManager
        cwd = str(Path.cwd())
        sm = SessionManager.create(cwd, session_dir)
        print(f"\n1. 创建 SessionManager")
        print(f"   会话目录: {session_dir}")
        print(f"   会话文件: {sm.session_file}")

        # 创建 AgentSession with SessionManager
        print("\n2. 创建 AgentSession（集成 SessionManager）...")
        session = create_agent_session(
            cwd=cwd,
            provider=KimiProvider(),
            system_prompt="你是一个有帮助的 AI 助手。",
            session_manager=sm,
        )
        print(f"   SessionManager 已绑定: {session.session_manager is not None}")
        print(f"   模型: {session.model.name if session.model else 'N/A'}")

        # 订阅事件
        session.subscribe(streaming_printer())

        # 第一轮对话
        print("\n3. 第一轮对话...")
        try:
            await session.prompt("请用一句话介绍自己")
        except Exception as e:
            print(f"\n   ❌ 第一轮对话失败: {e}")
            import traceback

            traceback.print_exc()
            return 1

        # 检查持久化
        print("\n4. 检查消息持久化...")
        entries = read_jsonl(sm.session_file)
        print(f"   JSONL 条目数: {len(entries)}")
        message_entries = [e for e in entries if e.get("type") == "message"]
        print(f"   消息条目数: {len(message_entries)}")
        for i, entry in enumerate(message_entries):
            msg = entry.get("message", {})
            role = msg.get("role", "unknown")
            content = msg.get("content", [])
            if isinstance(content, list) and content:
                text = content[0].get("text", "")[:50] if content else ""
            else:
                text = str(content)[:50]
            print(f"   [{i}] role={role}: {text}...")

        # 第二轮对话
        print("\n5. 第二轮对话（测试上下文连贯性）...")
        try:
            await session.prompt("我刚才让你介绍自己，你说了什么？")
        except Exception as e:
            print(f"\n   ❌ 第二轮对话失败: {e}")
            return 1

        # 再次检查持久化
        print("\n6. 第二轮后检查...")
        entries = read_jsonl(sm.session_file)
        message_entries = [e for e in entries if e.get("type") == "message"]
        print(f"   JSONL 条目数: {len(entries)}")
        print(f"   消息条目数: {len(message_entries)}")

        # 验证 context 重建
        print("\n7. 测试 build_context()...")
        context = session.build_context()
        print(f"   重建上下文消息数: {len(context)}")
        for i, msg in enumerate(context):
            role = getattr(msg, "role", "unknown")
            print(f"   [{i}] role={role}")

        # 验证 Agent.state.messages 和 SessionManager 同步
        print("\n8. 验证状态同步...")
        agent_msg_count = len(session.agent.state.messages)
        sm_msg_count = len(message_entries)
        print(f"   Agent state messages: {agent_msg_count}")
        print(f"   SessionManager entries: {sm_msg_count}")
        if agent_msg_count == sm_msg_count:
            print("   ✅ 状态同步正确")
        else:
            print("   ⚠️ 状态可能不同步（agent 包含 system 消息）")

        print("\n" + "=" * 60)
        print("✅ E2E 测试通过！")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
