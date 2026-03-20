"""技能系统 - 可复用的技能定义和加载

提供技能加载、管理和格式化功能，用于构建 Agent 提示。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger: logging.Logger = logging.getLogger(__name__)


# ============================================================================
# 技能类型定义
# ============================================================================


@dataclass
class Skill:
    """技能定义

    表示一个可复用的技能，包含名称、描述和具体内容。

    属性：
        id: 技能唯一标识符
        name: 技能显示名称
        description: 技能描述
        content: 技能具体内容/提示模板
        tags: 技能标签列表
        metadata: 额外元数据
    """

    id: str
    name: str
    description: str
    content: str
    tags: list[str]
    metadata: dict[str, Any]


# ============================================================================
# 技能加载
# ============================================================================


def _load_skill_from_file(file_path: Path) -> Skill | None:
    """从单个文件加载技能。

    支持 .json 和 .md 格式。
    - .json: 包含完整技能定义
    - .md: 第一个 # 标题作为名称，内容作为 content

    Args:
        file_path: 技能文件路径

    Returns:
        技能对象或 None
    """
    try:
        if file_path.suffix == ".json":
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return Skill(
                id=data.get("id", file_path.stem),
                name=data.get("name", file_path.stem),
                description=data.get("description", ""),
                content=data.get("content", ""),
                tags=data.get("tags", []),
                metadata=data.get("metadata", {}),
            )

        elif file_path.suffix == ".md":
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            # 解析标题
            name = file_path.stem
            description = ""
            skill_content = content

            for i, line in enumerate(lines):
                if line.startswith("# "):
                    name = line[2:].strip()
                    skill_content = "\n".join(lines[i + 1 :]).strip()
                    break

            # 解析前置元数据（如果存在）
            tags: list[str] = []
            metadata: dict[str, Any] = {}

            if lines and lines[0].startswith("---"):
                # YAML 前置元数据（简化处理）
                end_idx = 1
                for j in range(1, len(lines)):
                    if lines[j].startswith("---"):
                        end_idx = j
                        break

                for line in lines[1:end_idx]:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()

                        if key == "description":
                            description = value
                        elif key == "tags":
                            tags = [t.strip() for t in value.split(",")]
                        else:
                            metadata[key] = value

                skill_content = "\n".join(lines[end_idx + 1 :]).strip()

            return Skill(
                id=file_path.stem,
                name=name,
                description=description,
                content=skill_content,
                tags=tags,
                metadata=metadata,
            )

        else:
            logger.warning(f"不支持的技能文件格式: {file_path.suffix}")
            return None

    except Exception as e:
        logger.error(f"加载技能文件失败 {file_path}: {e}")
        return None


def load_skills_from_dir(directory: Path) -> dict[str, Skill]:
    """从目录加载所有技能。

    Args:
        directory: 技能目录路径

    Returns:
        技能ID到技能对象的映射
    """
    skills: dict[str, Skill] = {}

    if not directory.exists():
        logger.warning(f"技能目录不存在: {directory}")
        return skills

    for file_path in directory.iterdir():
        if file_path.suffix in (".json", ".md"):
            skill = _load_skill_from_file(file_path)
            if skill is not None:
                if skill.id in skills:
                    logger.warning(f"技能ID重复: {skill.id}")
                else:
                    skills[skill.id] = skill

    return skills


def load_skills(
    directories: list[Path],
) -> dict[str, Skill]:
    """从多个目录加载技能。

    后面的目录可以覆盖前面的同名技能。

    Args:
        directories: 技能目录列表

    Returns:
        技能ID到技能对象的映射
    """
    all_skills: dict[str, Skill] = {}

    for directory in directories:
        dir_skills = load_skills_from_dir(directory)
        for skill_id, skill in dir_skills.items():
            if skill_id in all_skills:
                logger.debug(f"技能被覆盖: {skill_id}")
            all_skills[skill_id] = skill

    return all_skills


# ============================================================================
# 技能格式化
# ============================================================================


def format_skill_for_prompt(skill: Skill) -> str:
    """将单个技能格式化为提示文本。

    Args:
        skill: 技能对象

    Returns:
        格式化后的提示文本
    """
    lines: list[str] = []

    lines.append(f"## {skill.name}")
    lines.append("")

    if skill.description:
        lines.append(f"**描述**: {skill.description}")
        lines.append("")

    if skill.tags:
        lines.append(f"**标签**: {', '.join(skill.tags)}")
        lines.append("")

    lines.append(skill.content)
    lines.append("")
    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def format_skills_for_prompt(
    skills: dict[str, Skill],
    skill_ids: list[str] | None = None,
) -> str:
    """将多个技能格式化为提示文本。

    Args:
        skills: 技能字典
        skill_ids: 要包含的技能ID列表，None表示包含所有

    Returns:
        格式化后的提示文本
    """
    if skill_ids is None:
        skill_ids = list(skills.keys())

    lines: list[str] = []
    lines.append("# 可用技能")
    lines.append("")

    for skill_id in skill_ids:
        if skill_id in skills:
            lines.append(format_skill_for_prompt(skills[skill_id]))
        else:
            logger.warning(f"技能未找到: {skill_id}")

    return "\n".join(lines)


def get_skill_by_tag(
    skills: dict[str, Skill],
    tag: str,
) -> list[Skill]:
    """按标签筛选技能。

    Args:
        skills: 技能字典
        tag: 标签名称

    Returns:
        匹配的技能列表
    """
    return [s for s in skills.values() if tag in s.tags]


def search_skills(
    skills: dict[str, Skill],
    query: str,
) -> list[Skill]:
    """搜索技能。

    在名称、描述和内容中搜索。

    Args:
        skills: 技能字典
        query: 搜索关键词

    Returns:
        匹配的技能列表
    """
    query_lower = query.lower()
    results: list[Skill] = []

    for skill in skills.values():
        if (
            query_lower in skill.name.lower()
            or query_lower in skill.description.lower()
            or query_lower in skill.content.lower()
        ):
            results.append(skill)

    return results
