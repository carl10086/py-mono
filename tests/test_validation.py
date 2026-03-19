"""
测试验证模块的基本功能
"""

from ai.types import Tool, ToolCall
from ai.validation import validate_tool_arguments, validate_tool_call, ToolValidationError


# 定义测试工具
weather_tool = Tool(
    name="get_weather",
    description="获取指定城市的天气信息",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名称"},
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "温度单位",
            },
        },
        "required": ["city"],
    },
)


def test_validate_valid_arguments():
    """测试有效参数验证"""
    tool_call = ToolCall(
        id="call_123",
        name="get_weather",
        arguments={"city": "北京", "unit": "celsius"},
    )

    result = validate_tool_arguments(weather_tool, tool_call)

    assert result["city"] == "北京"
    assert result["unit"] == "celsius"
    print("✅ 有效参数验证通过")


def test_validate_missing_required():
    """测试缺少必需参数"""
    tool_call = ToolCall(
        id="call_789",
        name="get_weather",
        arguments={"unit": "celsius"},  # 缺少必需的 city
    )

    try:
        validate_tool_arguments(weather_tool, tool_call)
        assert False, "应该抛出 ToolValidationError"
    except ToolValidationError as e:
        assert "city" in str(e)
        print("✅ 缺少必需参数验证通过")


def test_validate_invalid_enum():
    """测试无效的枚举值"""
    tool_call = ToolCall(
        id="call_abc",
        name="get_weather",
        arguments={"city": "北京", "unit": "invalid_unit"},
    )

    try:
        validate_tool_arguments(weather_tool, tool_call)
        assert False, "应该抛出 ToolValidationError"
    except ToolValidationError as e:
        assert "unit" in str(e)
        print("✅ 无效枚举值验证通过")


def test_validate_tool_call_not_found():
    """测试工具不存在"""
    tools = [weather_tool]
    tool_call = ToolCall(
        id="call_def",
        name="non_existent_tool",
        arguments={},
    )

    try:
        validate_tool_call(tools, tool_call)
        assert False, "应该抛出 ToolValidationError"
    except ToolValidationError as e:
        assert "non_existent_tool" in str(e)
        print("✅ 工具不存在验证通过")


def test_validate_wrong_type():
    """测试类型不匹配"""
    tool = Tool(
        name="calculate",
        description="计算",
        parameters={
            "type": "object",
            "properties": {
                "value": {"type": "number"},
            },
            "required": ["value"],
        },
    )

    tool_call = ToolCall(
        id="call_456",
        name="calculate",
        arguments={"value": "not_a_number"},  # 应该是数字，但传入字符串
    )

    try:
        validate_tool_arguments(tool, tool_call)
        assert False, "应该抛出 ToolValidationError"
    except ToolValidationError as e:
        assert "value" in str(e)
        print("✅ 类型不匹配验证通过")


if __name__ == "__main__":
    print("\n运行验证模块测试...\n")

    test_validate_valid_arguments()
    test_validate_missing_required()
    test_validate_invalid_enum()
    test_validate_tool_call_not_found()
    test_validate_wrong_type()

    print("\n✅ 所有测试通过！\n")
