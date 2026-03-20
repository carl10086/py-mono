from __future__ import annotations

import tempfile
from pathlib import Path

from coding_agent.skills import (
    Skill,
    format_skill_for_prompt,
    format_skills_for_prompt,
    get_skill_by_tag,
    load_skills,
    load_skills_from_dir,
    search_skills,
)


def test_load_skills_from_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)
        (skills_dir / "code_review.json").write_text(
            '{"id": "code-review", "name": "代码审查", "description": "审查代码质量和最佳实践", "content": "请审查以下代码：\\n1. 检查代码风格\\n2. 识别潜在bug\\n3. 提出优化建议", "tags": ["coding", "review"], "metadata": {"priority": "high"}}'
        )

        (skills_dir / "refactoring.md").write_text("""---
description: 代码重构指导
tags: coding, refactoring
---
# 代码重构

请帮助重构以下代码：
1. 提取重复逻辑
2. 简化复杂函数
3. 改善命名
""")

        skills = load_skills_from_dir(skills_dir)
        assert len(skills) >= 2


def test_format_skill_for_prompt():
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)
        (skills_dir / "code_review.json").write_text(
            '{"id": "code-review", "name": "代码审查", "description": "审查代码质量", "content": "请审查代码", "tags": ["coding"], "metadata": {}}'
        )

        skills = load_skills_from_dir(skills_dir)
        if "code-review" in skills:
            formatted = format_skill_for_prompt(skills["code-review"])
            assert len(formatted) > 0


def test_format_skills_for_prompt():
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)
        (skills_dir / "testing.md").write_text("# 测试\n\n请生成测试用例")

        skills = load_skills_from_dir(skills_dir)
        multi_formatted = format_skills_for_prompt(skills)
        assert len(multi_formatted) > 0


def test_get_skill_by_tag():
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)
        (skills_dir / "code_review.json").write_text(
            '{"id": "code-review", "name": "代码审查", "description": "审查", "content": "内容", "tags": ["coding"], "metadata": {}}'
        )
        (skills_dir / "testing.md").write_text(
            "---\ndescription: Testing\ntags: testing\n---\n# Test"
        )

        skills = load_skills_from_dir(skills_dir)
        coding_skills = get_skill_by_tag(skills, "coding")
        assert len(coding_skills) >= 1


def test_search_skills():
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)
        (skills_dir / "code_review.json").write_text(
            '{"id": "code-review", "name": "代码审查", "description": "审查代码", "content": "内容", "tags": ["coding"], "metadata": {}}'
        )

        skills = load_skills_from_dir(skills_dir)
        results = search_skills(skills, "代码")
        assert len(results) >= 1


def test_load_skills_multiple_dirs():
    with tempfile.TemporaryDirectory() as tmpdir1:
        skills_dir1 = Path(tmpdir1)
        (skills_dir1 / "code_review.json").write_text(
            '{"id": "code-review", "name": "代码审查", "description": "审查", "content": "内容", "tags": ["coding"], "metadata": {}}'
        )

        with tempfile.TemporaryDirectory() as tmpdir2:
            skills_dir2 = Path(tmpdir2)
            (skills_dir2 / "debugging.json").write_text(
                '{"id": "debugging", "name": "调试技巧", "description": "调试", "content": "调试步骤", "tags": ["debugging"], "metadata": {}}'
            )

            all_skills = load_skills([skills_dir1, skills_dir2])
            assert len(all_skills) >= 2
