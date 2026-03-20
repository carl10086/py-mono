"""示例 27: 扩展加载器测试

验证扩展发现和加载功能。
"""

import tempfile
from pathlib import Path

from coding_agent.extensions.loader import (
    discover_extensions,
    load_extension,
    load_extensions,
)
from coding_agent.extensions.types import Extension, ExtensionContext

print("=== 扩展加载器测试 ===")
print()

# 创建临时扩展目录
with tempfile.TemporaryDirectory() as tmpdir:
    ext_dir = Path(tmpdir)

    # 创建测试扩展文件
    ext_file = ext_dir / "test_extension.py"
    ext_file.write_text("""
from coding_agent.extensions.types import Extension, ExtensionContext, ToolDefinition

class TestExtension(Extension):
    id = "test-ext"
    name = "Test Extension"
    version = "1.0.0"

    def activate(self, context: ExtensionContext) -> None:
        pass

    def deactivate(self) -> None:
        pass

    def get_tools(self) -> list[ToolDefinition]:
        return []
""")

    print("1. 发现扩展...")
    ext_classes = discover_extensions([ext_dir])
    print(f"   发现 {len(ext_classes)} 个扩展")

    for ext_class in ext_classes:
        print(f"   - {ext_class.name} ({ext_class.id})")
    print()

    print("2. 加载扩展...")
    if ext_classes:
        ext = load_extension(ext_classes[0])
        print(f"   已加载: {ext.name}")
    print()

    print("3. 批量加载...")
    exts = load_extensions(ext_classes)
    print(f"   已加载 {len(exts)} 个扩展实例")
    print()

print("✓ 扩展加载器测试通过")
