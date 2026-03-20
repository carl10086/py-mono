"""提示模板系统 - 动态提示生成

提供模板定义和展开功能，支持变量替换。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger: logging.Logger = logging.getLogger(__name__)


# ============================================================================
# 模板类型定义
# ============================================================================


@dataclass
class PromptTemplate:
    """提示模板

    包含模板文本和变量定义。

    属性：
        id: 模板唯一标识符
        name: 模板名称
        description: 模板描述
        template: 模板文本（使用 {{variable}} 语法）
        variables: 变量定义列表
        defaults: 变量默认值
    """

    id: str
    name: str
    description: str
    template: str
    variables: list[str]
    defaults: dict[str, str]


# ============================================================================
# 模板解析
# ============================================================================


def _extract_variables(template: str) -> list[str]:
    """从模板中提取变量名。

    Args:
        template: 模板文本

    Returns:
        变量名列表
    """
    pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"
    matches = re.findall(pattern, template)
    return list(dict.fromkeys(matches))  # 去重保持顺序


def create_prompt_template(
    template_id: str,
    name: str,
    description: str,
    template: str,
    defaults: dict[str, str] | None = None,
) -> PromptTemplate:
    """创建提示模板。

    Args:
        template_id: 模板ID
        name: 模板名称
        description: 模板描述
        template: 模板文本
        defaults: 变量默认值

    Returns:
        提示模板对象
    """
    variables = _extract_variables(template)
    return PromptTemplate(
        id=template_id,
        name=name,
        description=description,
        template=template,
        variables=variables,
        defaults=defaults or {},
    )


# ============================================================================
# 模板展开
# ============================================================================


def expand_prompt_template(
    template: PromptTemplate,
    values: dict[str, str] | None = None,
    strict: bool = False,
) -> str:
    """展开提示模板。

    将模板中的变量替换为实际值。

    Args:
        template: 提示模板
        values: 变量值字典
        strict: 是否严格模式（缺少变量时报错）

    Returns:
        展开后的提示文本

    Raises:
        ValueError: 严格模式下缺少变量时抛出
    """
    result = template.template
    merged_values = {**template.defaults, **(values or {})}

    for var in template.variables:
        if var in merged_values:
            placeholder = f"{{{{{var}}}}}"
            result = result.replace(placeholder, merged_values[var])
        elif strict:
            raise ValueError(f"模板变量未提供: {var}")
        else:
            # 非严格模式下保留占位符
            logger.debug(f"模板变量使用默认值: {var}")

    return result


def expand_template_string(
    template_str: str,
    values: dict[str, str],
) -> str:
    """直接展开模板字符串。

    Args:
        template_str: 模板字符串
        values: 变量值字典

    Returns:
        展开后的文本
    """
    result = template_str
    for key, value in values.items():
        placeholder = f"{{{{{key}}}}}"
        result = result.replace(placeholder, value)
    return result


# ============================================================================
# 预定义模板
# ============================================================================


CODE_REVIEW_TEMPLATE = PromptTemplate(
    id="code-review",
    name="代码审查",
    description="审查代码质量",
    template="""请审查以下 {{language}} 代码：

```{{language}}
{{code}}
```

请检查：
1. 代码风格和质量
2. 潜在的错误或bug
3. 性能优化建议
4. 安全性问题

{{#if focus_areas}}
特别关注以下方面：
{{focus_areas}}
{{/if}}""",
    variables=["language", "code", "focus_areas"],
    defaults={"focus_areas": ""},
)

REFACTORING_TEMPLATE = PromptTemplate(
    id="refactoring",
    name="代码重构",
    description="重构代码建议",
    template="""请重构以下 {{language}} 代码：

```{{language}}
{{code}}
```

重构目标：
- 提高可读性
- 减少复杂度
- 改善命名
- 提取重复逻辑

{{#if constraints}}
约束条件：
{{constraints}}
{{/if}}""",
    variables=["language", "code", "constraints"],
    defaults={"constraints": ""},
)

DEBUGGING_TEMPLATE = PromptTemplate(
    id="debugging",
    name="调试帮助",
    description="帮助调试代码",
    template="""请帮助调试以下 {{language}} 代码：

```{{language}}
{{code}}
```

{{#if error_message}}
错误信息：
```
{{error_message}}
```
{{/if}}

{{#if expected_behavior}}
预期行为：
{{expected_behavior}}
{{/if}}

请分析可能的原因并提供解决方案。""",
    variables=["language", "code", "error_message", "expected_behavior"],
    defaults={
        "error_message": "",
        "expected_behavior": "",
    },
)

# 内置模板注册表
BUILTIN_TEMPLATES: dict[str, PromptTemplate] = {
    "code-review": CODE_REVIEW_TEMPLATE,
    "refactoring": REFACTORING_TEMPLATE,
    "debugging": DEBUGGING_TEMPLATE,
}


def get_builtin_template(template_id: str) -> PromptTemplate | None:
    """获取内置模板。

    Args:
        template_id: 模板ID

    Returns:
        模板对象或 None
    """
    return BUILTIN_TEMPLATES.get(template_id)


def list_builtin_templates() -> list[str]:
    """列出所有内置模板ID。

    Returns:
        模板ID列表
    """
    return list(BUILTIN_TEMPLATES.keys())
