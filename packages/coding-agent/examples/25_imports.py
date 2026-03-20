#!/usr/bin/env python3
"""
Phase 5 验证示例：导入测试

运行方式：
    cd packages/coding-agent && uv run python examples/25_imports.py
"""

from __future__ import annotations

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "ai" / "src"))
sys.path.insert(0, str(root_dir / "agent" / "src"))
sys.path.insert(0, str(root_dir / "coding-agent" / "src"))


def test_main_imports():
    """测试从主模块导入"""
    print("=" * 60)
    print("测试从 coding_agent 主模块导入")
    print("=" * 60)

    # 导入主模块
    import coding_agent

    print(f"\n模块版本: {coding_agent.__version__}")

    # 测试 AgentSession 相关
    assert hasattr(coding_agent, "AgentSession")
    assert hasattr(coding_agent, "AgentSessionConfig")
    assert hasattr(coding_agent, "PromptOptions")
    print("✓ AgentSession 相关导入成功")

    # 测试 Bash 执行器
    assert hasattr(coding_agent, "BashResult")
    assert hasattr(coding_agent, "execute_bash")
    print("✓ Bash 执行器导入成功")

    # 测试消息相关
    assert hasattr(coding_agent, "BashExecutionMessage")
    assert hasattr(coding_agent, "CustomMessage")
    assert hasattr(coding_agent, "BranchSummaryMessage")
    assert hasattr(coding_agent, "CompactionSummaryMessage")
    assert hasattr(coding_agent, "ExtendedMessage")
    assert hasattr(coding_agent, "convert_to_llm")
    print("✓ 消息相关导入成功")

    # 测试模型注册表
    assert hasattr(coding_agent, "ModelInfo")
    assert hasattr(coding_agent, "ModelRegistry")
    print("✓ 模型注册表导入成功")

    # 测试设置管理
    assert hasattr(coding_agent, "SettingsManager")
    assert hasattr(coding_agent, "CompactionSettings")
    assert hasattr(coding_agent, "RetrySettings")
    print("✓ 设置管理导入成功")

    # 测试系统提示
    assert hasattr(coding_agent, "build_system_prompt")
    print("✓ 系统提示导入成功")

    # 测试压缩功能
    assert hasattr(coding_agent, "compact")
    assert hasattr(coding_agent, "should_compact")
    assert hasattr(coding_agent, "estimate_tokens")
    assert hasattr(coding_agent, "CompactionConfigSettings")
    print("✓ 压缩功能导入成功")

    # 测试分支摘要
    assert hasattr(coding_agent, "generate_branch_summary")
    assert hasattr(coding_agent, "BranchSummaryResult")
    print("✓ 分支摘要导入成功")

    # 测试 SDK
    assert hasattr(coding_agent, "create_agent_session")
    assert hasattr(coding_agent, "create_coding_tools")
    assert hasattr(coding_agent, "create_read_only_tools")
    assert hasattr(coding_agent, "CreateAgentSessionOptions")
    assert hasattr(coding_agent, "CreateAgentSessionResult")
    print("✓ SDK 导入成功")

    print("\n✓ 主模块所有导入测试通过")


def test_session_imports():
    """测试从 session 子模块导入"""
    print("\n" + "=" * 60)
    print("测试从 session 子模块导入")
    print("=" * 60)

    from coding_agent.session import SessionManager, SessionEntry
    from coding_agent.session.types import SessionMessageEntry

    print("✓ session 子模块导入成功")
    assert SessionManager is not None
    assert SessionEntry is not None
    assert SessionMessageEntry is not None

    print("\n✓ session 子模块导入测试通过")


def test_tools_imports():
    """测试从 tools 子模块导入"""
    print("\n" + "=" * 60)
    print("测试从 tools 子模块导入")
    print("=" * 60)

    from coding_agent.tools import (
        create_read_tool,
        create_write_tool,
        create_edit_tool,
        create_bash_tool,
        create_grep_tool,
        create_find_tool,
        create_ls_tool,
    )

    print("✓ tools 子模块导入成功")
    assert create_read_tool is not None
    assert create_write_tool is not None

    print("\n✓ tools 子模块导入测试通过")


def test_compaction_imports():
    """测试从 compaction 子模块导入"""
    print("\n" + "=" * 60)
    print("测试从 compaction 子模块导入")
    print("=" * 60)

    from coding_agent.compaction import (
        compact,
        CompactionSettings,
        BranchSummaryResult,
        FileOperations,
    )

    print("✓ compaction 子模块导入成功")
    assert compact is not None
    assert CompactionSettings is not None

    print("\n✓ compaction 子模块导入测试通过")


def test_functional_imports():
    """测试功能导入是否可用"""
    print("\n" + "=" * 60)
    print("测试功能导入是否可用")
    print("=" * 60)

    from coding_agent import create_agent_session, create_coding_tools

    # 测试工具创建
    tools = create_coding_tools()
    assert len(tools) == 4
    print("✓ create_coding_tools 可用")

    # 测试会话创建
    result = create_agent_session()
    assert result.session is not None
    print("✓ create_agent_session 可用")

    print("\n✓ 功能导入测试通过")


def main() -> int:
    """主函数"""
    try:
        test_main_imports()
        test_session_imports()
        test_tools_imports()
        test_compaction_imports()
        test_functional_imports()

        print("\n" + "=" * 60)
        print("所有导入测试通过!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
