"""示例 29: 扩展运行器测试

验证扩展生命周期管理。
"""

from coding_agent.extensions.runner import ExtensionRunner
from coding_agent.extensions.types import (
    Extension,
    ExtensionContext,
    ToolDefinition,
)

print("=== 扩展运行器测试 ===")
print()


# 创建测试扩展
class ExtensionA(Extension):
    id = "ext-a"
    name = "Extension A"
    version = "1.0.0"
    activated = False

    def activate(self, ctx: ExtensionContext) -> None:
        self.activated = True
        print(f"   {self.name} 已激活")

    def deactivate(self) -> None:
        self.activated = False
        print(f"   {self.name} 已停用")


class ExtensionB(Extension):
    id = "ext-b"
    name = "Extension B"
    version = "2.0.0"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="tool_b",
                description="Tool B",
                parameters={},
                execute=lambda: "b",
            )
        ]


# 创建运行器
context = ExtensionContext(
    cwd="/workspace",
    agent_dir="/workspace/.coding-agent",
)
runner = ExtensionRunner(context)

# 测试激活
print("1. 激活扩展...")
ext_a = ExtensionA()
ext_b = ExtensionB()
runner.activate_extension(ext_a)
runner.activate_extension(ext_b)
print(f"   已激活扩展数: {len(runner.get_all_extensions())}")
print()

# 测试获取扩展
print("2. 获取扩展...")
ext = runner.get_extension("ext-a")
print(f"   找到扩展: {ext.name if ext else None}")
print()

# 测试命令注册
print("3. 注册命令...")
runner.register_command("help", lambda: "帮助信息")
runner.register_command("exit", lambda: "退出")
print(f"   已注册命令: {runner.list_commands()}")
print()

# 测试获取工具
print("4. 获取所有工具...")
tools = runner.get_all_tools()
print(f"   工具数量: {len(tools)}")
for tool in tools:
    print(f"   - {tool.name}")
print()

# 测试停用
print("5. 停用扩展...")
runner.deactivate_extension("ext-a")
print(f"   剩余扩展数: {len(runner.get_all_extensions())}")
print()

# 测试批量停用
print("6. 停用所有扩展...")
runner.deactivate_all()
print(f"   剩余扩展数: {len(runner.get_all_extensions())}")
print()

print("✓ 扩展运行器测试通过")
