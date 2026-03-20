"""示例 31: 技能系统测试

验证技能加载和格式化功能。
"""

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

print("=== 技能系统测试 ===")
print()

# 创建临时技能目录
with tempfile.TemporaryDirectory() as tmpdir:
    skills_dir = Path(tmpdir)

    # 创建 JSON 格式技能
    (skills_dir / "code_review.json").write_text(
        '{"id": "code-review", "name": "代码审查", "description": "审查代码质量和最佳实践", "content": "请审查以下代码：\\n1. 检查代码风格\\n2. 识别潜在bug\\n3. 提出优化建议", "tags": ["coding", "review"], "metadata": {"priority": "high"}}'
    )

    # 创建 Markdown 格式技能
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

    # 创建简单 Markdown 技能
    (skills_dir / "testing.md").write_text("""# 测试用例生成

为以下代码生成测试用例：
- 正常情况
- 边界情况
- 异常情况
""")

    print("1. 从目录加载技能...")
    skills = load_skills_from_dir(skills_dir)
    print(f"   加载了 {len(skills)} 个技能")
    for skill_id, skill in skills.items():
        print(f"   - {skill_id}: {skill.name}")
    print()

    print("2. 格式化单个技能...")
    if "code-review" in skills:
        formatted = format_skill_for_prompt(skills["code-review"])
        print(f"   前100字符: {formatted[:100]}...")
    print()

    print("3. 格式化多个技能...")
    multi_formatted = format_skills_for_prompt(skills)
    print(f"   总长度: {len(multi_formatted)} 字符")
    print()

    print("4. 按标签筛选...")
    coding_skills = get_skill_by_tag(skills, "coding")
    print(f"   'coding' 标签技能: {len(coding_skills)}")
    for s in coding_skills:
        print(f"   - {s.name}")
    print()

    print("5. 搜索技能...")
    search_results = search_skills(skills, "代码")
    print(f"   搜索结果: {len(search_results)}")
    for s in search_results:
        print(f"   - {s.name}")
    print()

    print("6. 从多个目录加载...")
    # 创建第二个目录
    with tempfile.TemporaryDirectory() as tmpdir2:
        skills_dir2 = Path(tmpdir2)
        (skills_dir2 / "debugging.json").write_text(
            '{"id": "debugging", "name": "调试技巧", "description": "帮助调试代码问题", "content": "调试步骤：\\n1. 复现问题\\n2. 设置断点\\n3. 检查变量", "tags": ["debugging"], "metadata": {}}'
        )

        all_skills = load_skills([skills_dir, skills_dir2])
        print(f"   总技能数: {len(all_skills)}")
        for sid in all_skills:
            print(f"   - {sid}")
    print()

print("✓ 技能系统测试通过")
print()
print("=== 技能系统特性 ===")
print("- 支持 JSON 和 Markdown 格式")
print("- 多目录加载和覆盖机制")
print("- 标签筛选和搜索功能")
print("- 格式化为提示文本")
