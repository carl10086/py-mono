from __future__ import annotations

from coding_agent.system_prompt import (
    TOOL_DESCRIPTIONS,
    BuildSystemPromptOptions,
    build_system_prompt,
)


def test_default_system_prompt() -> None:
    prompt = build_system_prompt()
    assert len(prompt) > 0
    assert "Available tools:" in prompt
    assert "Guidelines:" in prompt
    assert "Current date:" in prompt
    assert "Current working directory:" in prompt


def test_custom_system_prompt() -> None:
    options = BuildSystemPromptOptions(
        custom_prompt="You are a specialized Python expert.",
        append_system_prompt="Focus on type hints and documentation.",
    )
    prompt = build_system_prompt(options)
    assert "You are a specialized Python expert." in prompt
    assert "Focus on type hints and documentation." in prompt


def test_tool_selection() -> None:
    options = BuildSystemPromptOptions(selected_tools=["read", "bash"])
    prompt = build_system_prompt(options)
    assert "- read:" in prompt
    assert "- bash:" in prompt


def test_tool_snippets() -> None:
    options = BuildSystemPromptOptions(
        selected_tools=["read", "customTool"],
        tool_snippets={
            "customTool": "A custom tool for special operations",
        },
    )
    prompt = build_system_prompt(options)
    assert "A custom tool for special operations" in prompt
    assert "- read:" in prompt


def test_prompt_guidelines() -> None:
    options = BuildSystemPromptOptions(
        prompt_guidelines=[
            "Always add type hints",
            "Follow PEP 8 style guide",
        ],
    )
    prompt = build_system_prompt(options)
    assert "Always add type hints" in prompt
    assert "Follow PEP 8 style guide" in prompt


def test_context_files() -> None:
    options = BuildSystemPromptOptions(
        context_files=[
            {"path": "project-rules.md", "content": "Always use async/await for I/O operations."},
            {"path": "style-guide.md", "content": "Use snake_case for function names."},
        ],
    )
    prompt = build_system_prompt(options)
    assert "# Project Context" in prompt
    assert "## project-rules.md" in prompt
    assert "## style-guide.md" in prompt


def test_tool_descriptions() -> None:
    assert len(TOOL_DESCRIPTIONS) > 0
    assert "read" in TOOL_DESCRIPTIONS
    assert "bash" in TOOL_DESCRIPTIONS
