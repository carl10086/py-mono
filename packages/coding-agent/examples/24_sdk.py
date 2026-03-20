#!/usr/bin/env python3
"""
Phase 5 验证示例：SDK 核心功能测试

运行方式：
    cd packages/coding-agent && uv run python examples/24_sdk.py
"""

from __future__ import annotations

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "ai" / "src"))
sys.path.insert(0, str(root_dir / "agent" / "src"))
sys.path.insert(0, str(root_dir / "coding-agent" / "src"))

from coding_agent.sdk import (
    create_coding_tools,
    create_read_only_tools,
    create_agent_session,
    CreateAgentSessionOptions,
    CreateAgentSessionResult,
)


def test_create_coding_tools():
    """测试创建编码工具集"""
    print("=" * 60)
    print("测试创建编码工具集")
    print("=" * 60)

    # 使用默认工作目录
    tools = create_coding_tools()
    print(f"\n默认工作目录:")
    print(f"  工具数量: {len(tools)}")
    print(f"  工具名称: {list(tools.keys())}")

    # 使用指定工作目录
    tools_cwd = create_coding_tools("/tmp/test")
    print(f"\n指定工作目录:")
    print(f"  工具数量: {len(tools_cwd)}")

    # 验证工具存在
    assert "read" in tools
    assert "bash" in tools
    assert "edit" in tools
    assert "write" in tools

    print("\n✓ 编码工具集测试通过")


def test_create_read_only_tools():
    """测试创建只读工具集"""
    print("\n" + "=" * 60)
    print("测试创建只读工具集")
    print("=" * 60)

    # 使用默认工作目录
    tools = create_read_only_tools()
    print(f"\n默认工作目录:")
    print(f"  工具数量: {len(tools)}")
    print(f"  工具名称: {list(tools.keys())}")

    # 使用指定工作目录
    tools_cwd = create_read_only_tools("/home/user/project")
    print(f"\n指定工作目录:")
    print(f"  工具数量: {len(tools_cwd)}")

    # 验证工具存在
    assert "read" in tools
    assert "grep" in tools
    assert "find" in tools
    assert "ls" in tools
    assert "bash" in tools

    print("\n✓ 只读工具集测试通过")


def test_create_agent_session_minimal():
    """测试最小配置创建 AgentSession"""
    print("\n" + "=" * 60)
    print("测试最小配置创建 AgentSession")
    print("=" * 60)

    result = create_agent_session()

    print(f"\n创建结果:")
    print(f"  会话类型: {type(result.session).__name__}")
    print(f"  有回退消息: {result.model_fallback_message is not None}")
    if result.model_fallback_message:
        print(f"  回退消息: {result.model_fallback_message}")

    # 验证会话属性
    assert result.session is not None
    assert hasattr(result.session, "agent")
    assert hasattr(result.session, "session_manager")
    assert hasattr(result.session, "settings_manager")

    print("\n✓ 最小配置创建测试通过")


def test_create_agent_session_custom():
    """测试自定义配置创建 AgentSession"""
    print("\n" + "=" * 60)
    print("测试自定义配置创建 AgentSession")
    print("=" * 60)

    # 创建自定义工具集
    custom_tools = list(create_read_only_tools().values())

    options = CreateAgentSessionOptions(
        cwd="/tmp/test-project",
        tools=custom_tools,
    )

    result = create_agent_session(options)

    print(f"\n创建结果:")
    print(f"  会话类型: {type(result.session).__name__}")
    print(f"  工作目录: {result.session._cwd}")

    # 验证配置
    assert result.session._cwd == "/tmp/test-project"

    print("\n✓ 自定义配置创建测试通过")


def test_create_agent_session_with_model():
    """测试带模型的 AgentSession 创建"""
    print("\n" + "=" * 60)
    print("测试带模型的 AgentSession 创建")
    print("=" * 60)

    # 创建占位模型
    class FakeModel:
        def __init__(self):
            self.id = "fake-model"
            self.provider = "fake-provider"

    fake_model = FakeModel()

    options = CreateAgentSessionOptions(
        model=fake_model,
    )

    result = create_agent_session(options)

    print(f"\n创建结果:")
    print(f"  会话类型: {type(result.session).__name__}")
    print(f"  Agent 模型: {result.session.agent.model}")

    # 验证模型被使用
    assert result.session.agent.model == fake_model

    print("\n✓ 带模型创建测试通过")


def test_sdk_types():
    """测试 SDK 类型"""
    print("\n" + "=" * 60)
    print("测试 SDK 类型")
    print("=" * 60)

    # 测试 CreateAgentSessionOptions
    opts = CreateAgentSessionOptions(
        cwd="/test",
        agent_dir="/agent",
    )
    print(f"\nCreateAgentSessionOptions:")
    print(f"  cwd: {opts.cwd}")
    print(f"  agent_dir: {opts.agent_dir}")

    # 测试 CreateAgentSessionResult
    result = create_agent_session()
    print(f"\nCreateAgentSessionResult:")
    print(f"  有会话: {result.session is not None}")
    print(f"  有回退消息: {result.model_fallback_message is not None}")

    print("\n✓ SDK 类型测试通过")


def main() -> int:
    """主函数"""
    try:
        test_create_coding_tools()
        test_create_read_only_tools()
        test_create_agent_session_minimal()
        test_create_agent_session_custom()
        test_create_agent_session_with_model()
        test_sdk_types()

        print("\n" + "=" * 60)
        print("所有 SDK 测试通过!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
