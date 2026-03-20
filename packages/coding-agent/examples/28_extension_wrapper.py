"""示例 28: 扩展包装器测试

验证工具包装功能。
"""

from coding_agent.extensions.types import (
    Extension,
    ExtensionContext,
    ToolDefinition,
)
from coding_agent.extensions.wrapper import (
    clear_registered_tools,
    get_wrapped_tools,
    register_tool,
    wrap_registered_tool,
    wrap_registered_tools,
)

print("=== 扩展包装器测试 ===")
print()


# 创建测试扩展
class TestExtension(Extension):
    id = "test-ext"
    name = "Test Extension"
    version = "1.0.0"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="hello",
                description="打招呼",
                parameters={"type": "object", "properties": {"name": {"type": "string"}}},
                execute=lambda name: f"Hello, {name}!",
            ),
            ToolDefinition(
                name="add",
                description="加法",
                parameters={
                    "type": "object",
                    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                },
                execute=lambda a, b: a + b,
            ),
        ]


# 测试单个工具包装
print("1. 包装单个工具...")
tool_def = ToolDefinition(
    name="single_tool",
    description="单个工具",
    parameters={},
    execute=lambda: "done",
)
wrapped = wrap_registered_tool(tool_def)
print(f"   名称: {wrapped['name']}")
print(f"   描述: {wrapped['description']}")
print()

# 测试批量包装
print("2. 批量包装扩展工具...")
ext = TestExtension()
tools = wrap_registered_tools([ext])
print(f"   已包装 {len(tools)} 个工具:")
for name in tools:
    print(f"   - {name}")
print()

# 测试工具注册
print("3. 注册工具到全局...")
register_tool("custom_tool", {"name": "custom", "execute": lambda: None})
all_tools = get_wrapped_tools()
print(f"   全局工具数: {len(all_tools)}")
print()

# 清理
print("4. 清理...")
clear_registered_tools()
print(f"   清理后工具数: {len(get_wrapped_tools())}")
print()

print("✓ 扩展包装器测试通过")
