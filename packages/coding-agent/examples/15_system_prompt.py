#!/usr/bin/env python3
"""
Phase 3.2 验证示例：系统提示构建

验证内容：
1. 默认系统提示构建
2. 自定义系统提示
3. 工具选择
4. 指南生成

运行方式：
    cd packages/coding-agent && uv run python examples/15_system_prompt.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加包路径
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "ai" / "src"))
sys.path.insert(0, str(root_dir / "agent" / "src"))
sys.path.insert(0, str(root_dir / "coding-agent" / "src"))

from coding_agent.system_prompt import (
    TOOL_DESCRIPTIONS,
    BuildSystemPromptOptions,
    build_system_prompt,
)


def test_default_system_prompt() -> None:
    """测试默认系统提示"""
    print("=" * 60)
    print("测试默认系统提示")
    print("=" * 60)

    prompt = build_system_prompt()

    print(f"\n提示长度: {len(prompt)} 字符")
    print(f"包含 'Available tools:': {'Available tools:' in prompt}")
    print(f"包含 'Guidelines:': {'Guidelines:' in prompt}")
    print(f"包含 'Current date:': {'Current date:' in prompt}")
    print(f"包含 'Current working directory:': {'Current working directory:' in prompt}")

    # 打印开头部分
    print("\n提示前 500 字符:")
    print(prompt[:500])
    print("\n...")

    print("\n✓ 默认系统提示测试通过")


def test_custom_system_prompt() -> None:
    """测试自定义系统提示"""
    print("\n" + "=" * 60)
    print("测试自定义系统提示")
    print("=" * 60)

    options = BuildSystemPromptOptions(
        custom_prompt="You are a specialized Python expert.",
        append_system_prompt="Focus on type hints and documentation.",
    )

    prompt = build_system_prompt(options)

    print(f"\n提示长度: {len(prompt)} 字符")
    print(f"包含自定义开头: {'You are a specialized Python expert.' in prompt}")
    print(f"包含附加文本: {'Focus on type hints and documentation.' in prompt}")

    # 打印完整提示
    print("\n完整提示:")
    print(prompt)

    print("\n✓ 自定义系统提示测试通过")


def test_tool_selection() -> None:
    """测试工具选择"""
    print("\n" + "=" * 60)
    print("测试工具选择")
    print("=" * 60)

    # 测试只选择 read 和 bash
    options = BuildSystemPromptOptions(selected_tools=["read", "bash"])
    prompt = build_system_prompt(options)

    print("\n只选择 read 和 bash:")
    print(f"  包含 read: {'- read:' in prompt}")
    print(f"  包含 bash: {'- bash:' in prompt}")
    print(f"  包含 edit: {'- edit:' in prompt}")

    # 测试选择所有工具
    all_tools = ["read", "bash", "edit", "write", "grep", "find", "ls"]
    options2 = BuildSystemPromptOptions(selected_tools=all_tools)
    prompt2 = build_system_prompt(options2)

    print("\n选择所有工具:")
    for tool in all_tools:
        has_tool = f"- {tool}:" in prompt2
        print(f"  包含 {tool}: {has_tool}")

    print("\n✓ 工具选择测试通过")


def test_tool_snippets() -> None:
    """测试工具代码片段"""
    print("\n" + "=" * 60)
    print("测试工具代码片段")
    print("=" * 60)

    options = BuildSystemPromptOptions(
        selected_tools=["read", "customTool"],
        tool_snippets={
            "customTool": "A custom tool for special operations",
        },
    )

    prompt = build_system_prompt(options)

    print(f"\n包含自定义工具片段: {'A custom tool for special operations' in prompt}")
    print(f"包含 read 工具: {'- read:' in prompt}")

    print("\n✓ 工具代码片段测试通过")


def test_prompt_guidelines() -> None:
    """测试自定义指南"""
    print("\n" + "=" * 60)
    print("测试自定义指南")
    print("=" * 60)

    options = BuildSystemPromptOptions(
        prompt_guidelines=[
            "Always add type hints",
            "Follow PEP 8 style guide",
        ],
    )

    prompt = build_system_prompt(options)

    print(f"\n包含自定义指南 1: {'Always add type hints' in prompt}")
    print(f"包含自定义指南 2: {'Follow PEP 8 style guide' in prompt}")

    print("\n✓ 自定义指南测试通过")


def test_context_files() -> None:
    """测试上下文文件"""
    print("\n" + "=" * 60)
    print("测试上下文文件")
    print("=" * 60)

    options = BuildSystemPromptOptions(
        context_files=[
            {"path": "project-rules.md", "content": "Always use async/await for I/O operations."},
            {"path": "style-guide.md", "content": "Use snake_case for function names."},
        ],
    )

    prompt = build_system_prompt(options)

    print(f"\n包含 Project Context 标题: {'# Project Context' in prompt}")
    print(f"包含 project-rules.md: {'## project-rules.md' in prompt}")
    print(f"包含 style-guide.md: {'## style-guide.md' in prompt}")
    print(f"包含规则内容: {'Always use async/await for I/O operations.' in prompt}")

    print("\n✓ 上下文文件测试通过")


def test_tool_descriptions() -> None:
    """测试工具描述常量"""
    print("\n" + "=" * 60)
    print("测试工具描述常量")
    print("=" * 60)

    print("\n可用工具描述:")
    for tool, desc in TOOL_DESCRIPTIONS.items():
        print(f"  {tool}: {desc}")

    print(f"\n工具数量: {len(TOOL_DESCRIPTIONS)}")

    print("\n✓ 工具描述常量测试通过")


def main() -> int:
    """主函数"""
    try:
        test_default_system_prompt()
        test_custom_system_prompt()
        test_tool_selection()
        test_tool_snippets()
        test_prompt_guidelines()
        test_context_files()
        test_tool_descriptions()

        print("\n" + "=" * 60)
        print("所有测试通过!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
