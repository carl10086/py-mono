"""示例 30: 扩展系统完整测试

验证整个扩展系统。
"""

import tempfile
from pathlib import Path

from coding_agent.extensions import (
    Extension,
    ExtensionContext,
    ExtensionRunner,
    ToolDefinition,
    discover_extensions,
    load_extensions,
    wrap_registered_tools,
)

print("=== 扩展系统完整测试 ===")
print()

# 创建临时扩展目录
with tempfile.TemporaryDirectory() as tmpdir:
    ext_dir = Path(tmpdir)

    # 创建示例扩展文件
    (ext_dir / "my_extension.py").write_text("""
from coding_agent.extensions.types import Extension, ExtensionContext, ToolDefinition

class MyExtension(Extension):
    id = "my-ext"
    name = "My Extension"
    version = "1.0.0"
    
    def __init__(self):
        self.tool_calls = 0
    
    def activate(self, context: ExtensionContext) -> None:
        print(f"   [激活] {self.name}")
    
    def deactivate(self) -> None:
        print(f"   [停用] {self.name}")
    
    def get_tools(self) -> list[ToolDefinition]:
        def count_calls():
            self.tool_calls += 1
            return f"调用次数: {self.tool_calls}"
        
        return [
            ToolDefinition(
                name="count",
                description="计数器",
                parameters={},
                execute=count_calls,
            ),
            ToolDefinition(
                name="echo",
                description="回声",
                parameters={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"}
                    }
                },
                execute=lambda msg: f"Echo: {msg}",
            ),
        ]
""")

    print("1. 发现扩展...")
    ext_classes = discover_extensions([ext_dir])
    print(f"   发现 {len(ext_classes)} 个扩展类")
    print()

    print("2. 加载扩展实例...")
    extensions = load_extensions(ext_classes)
    print(f"   已加载 {len(extensions)} 个实例")
    print()

    print("3. 创建运行器并激活...")
    context = ExtensionContext(
        cwd="/workspace",
        agent_dir="/workspace/.coding-agent",
    )
    runner = ExtensionRunner(context)
    activated = runner.activate_all(extensions)
    print(f"   成功激活: {activated}")
    print()

    print("4. 获取并包装工具...")
    tools = wrap_registered_tools(runner.get_all_extensions())
    print(f"   可用工具:")
    for name, tool in tools.items():
        print(f"   - {name}: {tool['description']}")
    print()

    print("5. 执行工具...")
    if "echo" in tools:
        result = tools["echo"]["execute"]("Hello World")
        print(f"   echo('Hello World') = {result}")

    if "count" in tools:
        for i in range(3):
            result = tools["count"]["execute"]()
            print(f"   count() = {result}")
    print()

    print("6. 清理...")
    runner.deactivate_all()
    print(f"   所有扩展已停用")
    print()

print("✓ 扩展系统完整测试通过")
print()
print("=== 扩展系统特性 ===")
print("- 动态扩展发现和加载")
print("- 扩展生命周期管理")
print("- 工具注册和包装")
print("- 命令系统支持")
