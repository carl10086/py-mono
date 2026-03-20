"""系统提示构建模块 - 对齐 pi-mono TypeScript 实现

提供系统提示的构建功能，包括：
- 工具描述生成
- 动态提示模板
- 项目上下文加载
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from coding_agent.config import get_docs_path, get_examples_path, get_readme_path


# ============================================================================
# 工具描述
# ============================================================================

TOOL_DESCRIPTIONS: dict[str, str] = {
    "read": "Read file contents",
    "bash": "Execute bash commands (ls, grep, find, etc.)",
    "edit": "Make surgical edits to files (find exact text and replace)",
    "write": "Create or overwrite files",
    "grep": "Search file contents for patterns (respects .gitignore)",
    "find": "Find files by glob pattern (respects .gitignore)",
    "ls": "List directory contents",
}


# ============================================================================
# 配置选项
# ============================================================================


@dataclass
class BuildSystemPromptOptions:
    """构建系统提示的选项

    属性：
        custom_prompt: 自定义系统提示（替换默认提示）
        selected_tools: 要包含在提示中的工具列表。默认: [read, bash, edit, write]
        tool_snippets: 按工具名称索引的简短代码片段
        prompt_guidelines: 要附加到默认系统提示指南的额外指南列表
        append_system_prompt: 附加到系统提示的文本
        cwd: 工作目录。默认: 当前目录
        context_files: 预加载的上下文文件
        skills: 预加载的技能
    """

    custom_prompt: str | None = None
    selected_tools: list[str] | None = None
    tool_snippets: dict[str, str] | None = None
    prompt_guidelines: list[str] | None = None
    append_system_prompt: str | None = None
    cwd: str | None = None
    context_files: list[dict[str, str]] | None = None
    skills: list[Any] | None = None


# ============================================================================
# 技能格式化（占位符，后续实现）
# ============================================================================


def format_skills_for_prompt(skills: list[Any]) -> str:
    """将技能格式化为提示文本

    Args:
        skills: 技能列表

    Returns:
        格式化后的技能提示文本
    """
    # TODO: 在 skills.py 实现后完善此函数
    return ""


# ============================================================================
# 系统提示构建
# ============================================================================


def build_system_prompt(options: BuildSystemPromptOptions | None = None) -> str:
    """构建系统提示

    Args:
        options: 构建选项

    Returns:
        构建好的系统提示文本
    """
    opts = options or BuildSystemPromptOptions()

    # 解析选项
    custom_prompt = opts.custom_prompt
    selected_tools = opts.selected_tools
    tool_snippets = opts.tool_snippets
    prompt_guidelines = opts.prompt_guidelines
    append_system_prompt = opts.append_system_prompt
    cwd = opts.cwd
    context_files = opts.context_files
    skills = opts.skills

    # 解析工作目录
    import os

    resolved_cwd = cwd or os.getcwd()
    prompt_cwd = resolved_cwd.replace("\\", "/")

    # 日期
    from datetime import datetime

    date = datetime.now().strftime("%Y-%m-%d")

    # 附加部分
    append_section = f"\n\n{append_system_prompt}" if append_system_prompt else ""

    # 上下文文件
    context_files_list = context_files or []
    skills_list = skills or []

    # 如果使用自定义提示
    if custom_prompt:
        prompt = custom_prompt

        if append_section:
            prompt += append_section

        # 附加项目上下文文件
        if context_files_list:
            prompt += "\n\n# Project Context\n\n"
            prompt += "Project-specific instructions and guidelines:\n\n"
            for file_info in context_files_list:
                file_path = file_info.get("path", "")
                content = file_info.get("content", "")
                prompt += f"## {file_path}\n\n{content}\n\n"

        # 附加技能部分（仅当 read 工具可用时）
        has_read = not selected_tools or "read" in selected_tools
        if has_read and skills_list:
            prompt += format_skills_for_prompt(skills_list)

        # 添加日期和工作目录
        prompt += f"\nCurrent date: {date}"
        prompt += f"\nCurrent working directory: {prompt_cwd}"

        return prompt

    # 获取文档路径
    readme_path = get_readme_path()
    docs_path = get_docs_path()
    examples_path = get_examples_path()

    # 构建工具列表
    tools = selected_tools or ["read", "bash", "edit", "write"]
    visible_tools = [
        name
        for name in tools
        if name in TOOL_DESCRIPTIONS or (tool_snippets and name in tool_snippets)
    ]

    if visible_tools:
        tools_list = "\n".join(
            f"- {name}: {tool_snippets.get(name) if tool_snippets and name in tool_snippets else TOOL_DESCRIPTIONS.get(name, name)}"
            for name in visible_tools
        )
    else:
        tools_list = "(none)"

    # 根据可用工具构建指南
    guidelines_list: list[str] = []
    guidelines_set: set[str] = set()

    def add_guideline(guideline: str) -> None:
        """添加指南（去重）"""
        if guideline in guidelines_set:
            return
        guidelines_set.add(guideline)
        guidelines_list.append(guideline)

    has_bash = "bash" in tools
    has_edit = "edit" in tools
    has_write = "write" in tools
    has_grep = "grep" in tools
    has_find = "find" in tools
    has_ls = "ls" in tools
    has_read = "read" in tools

    # 文件探索指南
    if has_bash and not has_grep and not has_find and not has_ls:
        add_guideline("Use bash for file operations like ls, rg, find")
    elif has_bash and (has_grep or has_find or has_ls):
        add_guideline(
            "Prefer grep/find/ls tools over bash for file exploration (faster, respects .gitignore)"
        )

    # 编辑前读取指南
    if has_read and has_edit:
        add_guideline(
            "Use read to examine files before editing. You must use this tool instead of cat or sed."
        )

    # 编辑指南
    if has_edit:
        add_guideline("Use edit for precise changes (old text must match exactly)")

    # 写入指南
    if has_write:
        add_guideline("Use write only for new files or complete rewrites")

    # 输出指南（仅当实际写入或执行时）
    if has_edit or has_write:
        add_guideline(
            "When summarizing your actions, output plain text directly - do NOT use cat or bash to display what you did"
        )

    # 自定义指南
    for guideline in prompt_guidelines or []:
        normalized = guideline.strip()
        if normalized:
            add_guideline(normalized)

    # 总是包含这些
    add_guideline("Be concise in your responses")
    add_guideline("Show file paths clearly when working with files")

    guidelines = "\n".join(f"- {g}" for g in guidelines_list)

    # 构建提示
    prompt = f"""You are an expert coding assistant operating inside pi, a coding agent harness. You help users by reading files, executing commands, editing code, and writing new files.

Available tools:
{tools_list}

In addition to the tools above, you may have access to other custom tools depending on the project.

Guidelines:
{guidelines}

Pi documentation (read only when the user asks about pi itself, its SDK, extensions, themes, skills, or TUI):
- Main documentation: {readme_path}
- Additional docs: {docs_path}
- Examples: {examples_path} (extensions, custom tools, SDK)
- When asked about: extensions (docs/extensions.md, examples/extensions/), themes (docs/themes.md), skills (docs/skills.md), prompt templates (docs/prompt-templates.md), TUI components (docs/tui.md), keybindings (docs/keybindings.md), SDK integrations (docs/sdk.md), custom providers (docs/custom-provider.md), adding models (docs/models.md), pi packages (docs/packages.md)
- When working on pi topics, read the docs and examples, and follow .md cross-references before implementing
- Always read pi .md files completely and follow links to related docs (e.g., tui.md for TUI API details)"""

    if append_section:
        prompt += append_section

    # 附加项目上下文文件
    if context_files_list:
        prompt += "\n\n# Project Context\n\n"
        prompt += "Project-specific instructions and guidelines:\n\n"
        for file_info in context_files_list:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")
            prompt += f"## {file_path}\n\n{content}\n\n"

    # 附加技能部分（仅当 read 工具可用时）
    if has_read and skills_list:
        prompt += format_skills_for_prompt(skills_list)

    # 添加日期和工作目录
    prompt += f"\nCurrent date: {date}"
    prompt += f"\nCurrent working directory: {prompt_cwd}"

    return prompt


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "TOOL_DESCRIPTIONS",
    "BuildSystemPromptOptions",
    "build_system_prompt",
    "format_skills_for_prompt",
]
