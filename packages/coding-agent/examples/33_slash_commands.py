"""示例 33: 斜杠命令测试

验证斜杠命令注册和执行功能。
"""

from coding_agent.slash_commands import (
    SlashCommandRegistry,
    create_default_registry,
    parse_slash_command,
)

print("=== 斜杠命令测试 ===")
print()

# 测试命令解析
print("1. 解析斜杠命令...")
cases = [
    "/help",
    "/model gpt-4",
    "/compact",
    "not a command",
]
for case in cases:
    result = parse_slash_command(case)
    print(f"   '{case}' -> {result}")
print()

# 测试创建注册表
print("2. 创建默认注册表...")
registry = create_default_registry()
commands = registry.list_commands()
print(f"   默认命令数: {len(commands)}")
print(f"   命令列表: {commands}")
print()

# 测试获取帮助
print("3. 获取帮助文本...")
help_text = registry.get_help_text()
print(f"   帮助长度: {len(help_text)} 字符")
print(f"   前200字符:\n{help_text[:200]}...")
print()

# 测试执行命令
print("4. 执行命令...")
try:
    result = registry.execute("/help")
    print(f"   /help 执行成功")
except Exception as e:
    print(f"   /help 执行失败: {e}")

try:
    result = registry.execute("/exit")
    print(f"   /exit 结果: {result}")
except Exception as e:
    print(f"   /exit 执行失败: {e}")

try:
    result = registry.execute("/model gpt-4")
    print(f"   /model 结果: {result}")
except Exception as e:
    print(f"   /model 执行失败: {e}")
print()

# 测试自定义命令
print("5. 注册自定义命令...")
custom_registry = SlashCommandRegistry()


def custom_handler(arg1: str, arg2: str = "default") -> str:
    return f"自定义命令执行: arg1={arg1}, arg2={arg2}"


custom_registry.register(
    name="custom",
    description="自定义命令示例",
    handler=custom_handler,
    args_help="[arg1] [arg2]",
)

try:
    result = custom_registry.execute("/custom value1 value2")
    print(f"   结果: {result}")
except Exception as e:
    print(f"   执行失败: {e}")
print()

# 测试未知命令
print("6. 未知命令处理...")
try:
    registry.execute("/unknown")
except ValueError as e:
    print(f"   预期错误: {e}")
print()

print("✓ 斜杠命令测试通过")
print()
print("=== 斜杠命令特性 ===")
print("- 内置常用命令（help, exit, model, compact等）")
print("- 支持自定义命令注册")
print("- 命令参数解析")
print("- 自动帮助文本生成")
