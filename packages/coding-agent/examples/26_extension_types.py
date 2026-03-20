"""示例 26: 扩展类型测试

验证扩展类型定义。
"""

from coding_agent.extensions.types import (
    Extension,
    ExtensionContext,
    ToolDefinition,
)

print("=== 扩展类型测试 ===")
print()

# 测试 ToolDefinition
tool_def = ToolDefinition(
    name="test_tool",
    description="测试工具",
    parameters={"type": "object", "properties": {}},
    execute=lambda x: x,
)
print(f"ToolDefinition: {tool_def.name}")
print(f"  Description: {tool_def.description}")
print()

# 测试 ExtensionContext
context = ExtensionContext(
    cwd="/workspace",
    agent_dir="/workspace/.coding-agent",
)
print(f"ExtensionContext:")
print(f"  CWD: {context.cwd}")
print(f"  Agent Dir: {context.agent_dir}")
print()


# 测试自定义扩展
class MyExtension(Extension):
    """自定义扩展示例"""

    id = "my-ext"
    name = "My Extension"
    version = "1.0.0"

    def activate(self, ctx: ExtensionContext) -> None:
        print(f"扩展已激活: {self.name}")

    def deactivate(self) -> None:
        print(f"扩展已停用: {self.name}")

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="my_tool",
                description="我的工具",
                parameters={},
                execute=lambda: "result",
            )
        ]


ext = MyExtension()
print(f"Extension:")
print(f"  ID: {ext.id}")
print(f"  Name: {ext.name}")
print(f"  Version: {ext.version}")
print(f"  Tools count: {len(ext.get_tools())}")
print()

# 测试生命周期
ext.activate(context)
ext.deactivate()

print()
print("✓ 扩展类型测试通过")
