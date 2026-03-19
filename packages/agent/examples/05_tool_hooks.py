"""
示例 05: Tool Hook 演示 - 权限控制与结果过滤

学习目标：
- before_tool_call: 权限检查、阻止危险操作
- after_tool_call: 结果过滤、敏感信息保护

场景：
1. 文件删除工具 - 使用 before_tool_call 阻止删除系统文件
2. 密码查询工具 - 使用 after_tool_call 过滤密码明文

运行：
    uv run python examples/05_tool_hooks.py
"""

from __future__ import annotations

import asyncio
from typing import Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ai.providers import KimiProvider
from ai.types import TextContent, UserMessage
from agent import (
    AgentContext,
    AgentLoopConfig,
    AgentOptions,
    Agent,
    BeforeToolCallResult,
    AfterToolCallResult,
    BeforeToolCallContext,
    AfterToolCallContext,
    AgentToolResult,
)


class FileManagerTool:
    """文件管理工具 - 演示权限控制"""

    name = "file_manager"
    label = "文件管理"
    description = "读取或删除文件"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "delete"],
                "description": "操作类型：read 读取，delete 删除",
            },
            "path": {"type": "string", "description": "文件路径"},
        },
        "required": ["action", "path"],
    }

    # 模拟文件系统
    FILES = {
        "/tmp/user_doc.txt": "这是用户文档内容",
        "/etc/passwd": "root:x:0:0:root:/root:/bin/bash",
        "/system/config.ini": "system_key=secret123",
    }

    async def execute(
        self, tool_call_id: str, params: dict[str, Any], signal: Any = None, on_update: Any = None
    ) -> AgentToolResult:
        action = params.get("action")
        path = params.get("path")

        if action == "read":
            content = self.FILES.get(path, f"文件不存在: {path}")
            return AgentToolResult(
                content=[TextContent(text=content)], details={"action": "read", "path": path}
            )
        else:  # delete
            if path in self.FILES:
                del self.FILES[path]
                return AgentToolResult(
                    content=[TextContent(text=f"已删除: {path}")],
                    details={"action": "delete", "path": path},
                )
            return AgentToolResult(
                content=[TextContent(text=f"文件不存在: {path}")],
                details={"action": "delete", "path": path},
                is_error=True,
            )


class PasswordTool:
    """密码查询工具 - 演示结果过滤"""

    name = "get_password"
    label = "密码查询"
    description = "查询账户密码"
    parameters = {
        "type": "object",
        "properties": {"account": {"type": "string", "description": "账户名"}},
        "required": ["account"],
    }

    # 模拟密码数据库
    PASSWORDS = {
        "admin": "SuperSecret123!",
        "user1": "Passw0rd456",
        "guest": "guest123",
    }

    async def execute(
        self, tool_call_id: str, params: dict[str, Any], signal: Any = None, on_update: Any = None
    ) -> AgentToolResult:
        account = params.get("account")
        password = self.PASSWORDS.get(account)

        if password:
            return AgentToolResult(
                content=[TextContent(text=f"账户: {account}\n密码: {password}")],
                details={"account": account, "password": password},
            )
        return AgentToolResult(content=[TextContent(text=f"账户不存在: {account}")], is_error=True)


# =============================================================================
# Hook 函数
# =============================================================================


async def before_tool_call_hook(
    ctx: BeforeToolCallContext, signal: Any
) -> BeforeToolCallResult | None:
    """
    工具执行前钩子 - 权限检查和危险操作拦截

    场景：
    1. 阻止删除系统文件 (/etc/, /system/)
    2. 阻止删除关键配置文件
    """
    tool_name = ctx.tool_call.name
    args = ctx.args

    print(f"\n🔍 [Before Hook] 检查工具: {tool_name}")
    print(f"   参数: {args}")

    if tool_name == "file_manager":
        action = args.get("action")
        path = args.get("path", "")

        # 规则1：禁止删除系统文件
        if action == "delete" and ("/etc/" in path or "/system/" in path):
            print(f"   ⚠️  拦截: 无权删除系统文件 {path}")
            return BeforeToolCallResult(
                block=True,
                reason=f"安全策略：禁止删除系统文件 {path}。您可以删除 /tmp/ 目录下的文件。",
            )

        # 规则2：记录删除操作
        if action == "delete":
            print(f"   📝 记录: 用户尝试删除文件 {path}")

    # 返回 None 表示允许执行
    print(f"   ✅ 允许执行")
    return None


async def after_tool_call_hook(
    ctx: AfterToolCallContext, signal: Any
) -> AfterToolCallResult | None:
    """
    工具执行后钩子 - 结果过滤和敏感信息保护

    场景：
    1. 过滤密码明文，用星号替代
    2. 添加审计标记
    """
    tool_name = ctx.tool_call.name
    result = ctx.result

    print(f"\n🔍 [After Hook] 处理结果: {tool_name}")

    if tool_name == "get_password":
        # 获取原始文本
        original_text = result.content[0].text
        print(f"   原始结果:\n{original_text}")

        # 过滤密码：将明文替换为星号
        import re

        filtered_text = re.sub(r"密码: \S+", "密码: ********", original_text)

        print(f"   过滤后:\n{filtered_text}")
        print(f"   🔒 已隐藏密码明文")

        return AfterToolCallResult(
            content=[TextContent(text=filtered_text)],
            details={**result.details, "filtered": True, "reason": "security"},
        )

    # 对其他工具添加审计标记
    if tool_name == "file_manager":
        return AfterToolCallResult(
            details={
                **result.details,
                "audited": True,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

    return None


# =============================================================================
# 演示
# =============================================================================


async def demo_before_hook():
    """演示 before_tool_call Hook - 权限控制"""
    print("\n" + "=" * 60)
    print("演示 1: Before Hook - 权限控制")
    print("=" * 60)
    print("\n场景：阻止删除系统文件\n")

    provider = KimiProvider()

    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    agent = Agent(AgentOptions(stream_fn=stream_fn))
    agent.set_model(provider.get_model())
    agent.set_tools([FileManagerTool()])
    agent.set_before_tool_call(before_tool_call_hook)

    # 测试1：尝试删除系统文件（应该被阻止）
    print("【测试 1】删除系统文件 /etc/passwd")
    print("-" * 60)
    await agent.prompt("请删除文件 /etc/passwd")
    await agent.wait_for_idle()
    print()

    # 重置 Agent 状态
    agent.reset()
    agent.set_before_tool_call(before_tool_call_hook)

    # 测试2：删除用户文件（应该允许）
    print("\n【测试 2】删除用户文件 /tmp/user_doc.txt")
    print("-" * 60)
    await agent.prompt("请删除文件 /tmp/user_doc.txt")
    await agent.wait_for_idle()
    print()


async def demo_after_hook():
    """演示 after_tool_call Hook - 结果过滤"""
    print("\n" + "=" * 60)
    print("演示 2: After Hook - 结果过滤")
    print("=" * 60)
    print("\n场景：隐藏密码明文\n")

    provider = KimiProvider()

    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    agent = Agent(AgentOptions(stream_fn=stream_fn))
    agent.set_model(provider.get_model())
    agent.set_tools([PasswordTool()])
    agent.set_after_tool_call(after_tool_call_hook)

    # 测试：查询密码（应该被过滤）
    print("【测试】查询 admin 密码")
    print("-" * 60)
    await agent.prompt("请查询 admin 账户的密码")
    await agent.wait_for_idle()
    print()


async def demo_combined_hooks():
    """演示同时使用两个 Hook"""
    print("\n" + "=" * 60)
    print("演示 3: 组合使用 - Before + After Hook")
    print("=" * 60)
    print("\n场景：完整的权限控制和审计日志\n")

    provider = KimiProvider()

    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)

    agent = Agent(AgentOptions(stream_fn=stream_fn))
    agent.set_model(provider.get_model())
    agent.set_tools([FileManagerTool(), PasswordTool()])
    agent.set_before_tool_call(before_tool_call_hook)
    agent.set_after_tool_call(after_tool_call_hook)

    # 复杂场景：先尝试删除系统文件（被阻止），再查询密码（被过滤）
    print("【测试】组合操作")
    print("-" * 60)
    await agent.prompt("请先删除 /system/config.ini，然后查询 user1 的密码")
    await agent.wait_for_idle()
    print()


async def main():
    """主函数"""
    print("=" * 60)
    print("示例 05: Tool Hook 演示")
    print("=" * 60)
    print("\n本示例演示:")
    print("  1. before_tool_call: 权限控制、危险操作拦截")
    print("  2. after_tool_call: 结果过滤、敏感信息保护")

    try:
        await demo_before_hook()
        await demo_after_hook()
        await demo_combined_hooks()

        print("\n" + "=" * 60)
        print("✅ 所有演示完成!")
        print("=" * 60)
        print("\n总结:")
        print("  • before_tool_call: 在工具执行前进行拦截和检查")
        print("  • after_tool_call: 在工具执行后修改和过滤结果")
        print("  • 两者可以组合使用，提供完整的安全控制")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
