"""
工具参数验证模块

提供工具调用参数的 JSON Schema 验证功能，
对齐 pi-mono 的 validateToolArguments 行为。

设计原则:
- 参数深拷贝后进行验证
- 验证失败提供详细的字段级错误信息
- 支持 Pydantic 模型和原始 dict 作为 schema
"""

from __future__ import annotations

import copy
import json
from collections.abc import Sequence
from typing import Any

from jsonschema import FormatChecker, ValidationError
from jsonschema.validators import Draft7Validator

from ai.types import Tool, ToolCall


class ToolValidationError(Exception):
    """工具参数验证错误

    当工具参数不符合 JSON Schema 时抛出，
    包含详细的字段级错误信息。
    """


def validate_tool_call(
    tools: Sequence[Tool],
    tool_call: ToolCall,
) -> dict[str, Any]:
    """查找工具并验证参数

    在工具列表中查找指定名称的工具，
    并验证工具调用的参数是否符合 schema。

    参数:
        tools: 可用工具列表
        tool_call: 工具调用请求

    返回:
        验证后的参数（可能经过类型强制）

    异常:
        ToolValidationError: 工具不存在或参数验证失败
    """
    tool = next((t for t in tools if t.name == tool_call.name), None)
    if not tool:
        raise ToolValidationError(f'工具 "{tool_call.name}" 未找到')
    return validate_tool_arguments(tool, tool_call)


def validate_tool_arguments(
    tool: Tool,
    tool_call: ToolCall,
) -> dict[str, Any]:
    """验证工具调用参数是否符合 JSON Schema

    使用 jsonschema 进行严格的参数验证。
    注意：与 AJV 不同，jsonschema 不支持自动类型强制。

    参数:
        tool: 工具定义（包含 parameters JSON Schema）
        tool_call: 工具调用请求

    返回:
        验证后的参数（深拷贝）

    异常:
        ToolValidationError: 参数不符合 schema
    """
    schema: dict[str, object] = _extract_schema(tool)
    args = copy.deepcopy(tool_call.arguments)

    # 创建验证器并执行验证
    validator = Draft7Validator(
        schema,
        format_checker=FormatChecker(),
    )

    errors: list[ValidationError] = list(validator.iter_errors(args))  # type: ignore[reportUnknownMemberType]
    if errors:
        error_msg = _build_error_message(tool_call, errors)
        raise ToolValidationError(error_msg)

    return args


def _extract_schema(tool: Tool) -> dict[str, object]:
    """从工具定义中提取 JSON Schema

    支持 Pydantic 模型（通过 model_json_schema）
    或原始 dict 作为 schema。
    """
    if hasattr(tool.parameters, "model_json_schema"):
        schema: dict[str, object] = tool.parameters.model_json_schema()
        return schema
    return tool.parameters


def _build_error_message(
    tool_call: ToolCall,
    errors: list[ValidationError],
) -> str:
    """构建人类可读的验证错误信息

    格式对齐 pi-mono 的错误输出风格:
    - 列出每个字段的错误
    - 显示原始参数便于调试
    """
    errors_str = _format_validation_errors(errors)
    args_str = json.dumps(tool_call.arguments, indent=2, ensure_ascii=False)

    return f'工具 "{tool_call.name}" 参数验证失败:\n{errors_str}\n\n接收到的参数:\n{args_str}'


def _format_validation_errors(errors: list[ValidationError]) -> str:
    """格式化验证错误列表

    将 jsonschema 的 ValidationError 转换为可读字符串，
    每个错误显示字段路径和错误信息。
    """
    lines: list[str] = []
    for err in errors:
        path = ".".join(str(p) for p in err.path) if err.path else "root"
        lines.append(f"  - {path}: {err.message}")
    return "\n".join(lines)
