"""示例 34: 资源加载器测试

验证资源加载功能。
"""

import tempfile
from pathlib import Path

from coding_agent.resource_loader import (
    DefaultResourceLoader,
    InMemoryResourceLoader,
    ResourceNotFoundError,
)

print("=== 资源加载器测试 ===")
print()

# 测试内存加载器
print("1. 内存资源加载器...")
mem_loader = InMemoryResourceLoader()
mem_loader.add_resource("greeting", "Hello, World!")
mem_loader.add_resource("config", '{"version": "1.0"}')

print(f"   资源列表: {mem_loader.list_resources()}")
print(f"   greeting 存在: {mem_loader.exists('greeting')}")
print(f"   unknown 存在: {mem_loader.exists('unknown')}")

text = mem_loader.load_text("greeting")
print(f"   加载文本: {text}")

json_data = mem_loader.load_json("config")
print(f"   加载JSON: {json_data}")
print()

# 测试资源不存在
print("2. 资源不存在处理...")
try:
    mem_loader.load_text("nonexistent")
except ResourceNotFoundError as e:
    print(f"   预期错误: {e}")
print()

# 测试文件加载器
print("3. 默认文件加载器...")
with tempfile.TemporaryDirectory() as tmpdir:
    base_path = Path(tmpdir)

    # 创建资源文件
    (base_path / "messages").mkdir()
    (base_path / "messages" / "welcome.txt").write_text("欢迎！")
    (base_path / "config.json").write_text('{"debug": true}')
    (base_path / "docs").mkdir(parents=True)
    (base_path / "docs" / "guide.md").write_text("# 使用指南")

    loader = DefaultResourceLoader(base_path)

    print(f"   资源列表:")
    for rid in loader.list_resources():
        print(f"     - {rid}")

    # 加载文本
    welcome = loader.load_text("messages.welcome")
    print(f"   加载 messages.welcome: {welcome}")

    # 加载JSON
    config = loader.load_json("config")
    print(f"   加载 config: {config}")

    # 检查存在性
    print(f"   messages.welcome 存在: {loader.exists('messages.welcome')}")
    print(f"   missing 存在: {loader.exists('missing')}")

print()

print("✓ 资源加载器测试通过")
print()
print("=== 资源加载器特性 ===")
print("- 文件系统资源加载（DefaultResourceLoader）")
print("- 内存资源加载（InMemoryResourceLoader）")
print("- 支持文本和JSON加载")
print("- 点号分隔的资源ID")
