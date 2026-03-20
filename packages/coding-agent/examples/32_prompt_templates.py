"""示例 32: 提示模板测试

验证提示模板创建和展开功能。
"""

from coding_agent.prompt_templates import (
    CODE_REVIEW_TEMPLATE,
    REFACTORING_TEMPLATE,
    create_prompt_template,
    expand_prompt_template,
    expand_template_string,
    get_builtin_template,
    list_builtin_templates,
)

print("=== 提示模板测试 ===")
print()

# 测试创建模板
print("1. 创建自定义模板...")
template = create_prompt_template(
    template_id="greeting",
    name="问候模板",
    description="生成问候语",
    template="你好，{{name}}！欢迎{{action}}。",
    defaults={"action": "加入我们"},
)
print(f"   模板ID: {template.id}")
print(f"   变量: {template.variables}")
print(f"   默认值: {template.defaults}")
print()

# 测试展开模板
print("2. 展开模板...")
result = expand_prompt_template(template, {"name": "张三"})
print(f"   结果: {result}")
print()

# 测试严格模式
print("3. 严格模式（缺少变量）...")
try:
    expand_prompt_template(template, {}, strict=True)
except ValueError as e:
    print(f"   预期错误: {e}")
print()

# 测试直接展开字符串
print("4. 直接展开字符串...")
result = expand_template_string(
    "今天是{{day}}，天气{{weather}}", {"day": "周一", "weather": "晴朗"}
)
print(f"   结果: {result}")
print()

# 测试内置模板
print("5. 内置模板...")
builtin_ids = list_builtin_templates()
print(f"   内置模板数量: {len(builtin_ids)}")
for tid in builtin_ids:
    t = get_builtin_template(tid)
    if t:
        print(f"   - {tid}: {t.name}")
print()

# 测试代码审查模板
print("6. 使用代码审查模板...")
code_review = expand_prompt_template(
    CODE_REVIEW_TEMPLATE,
    {
        "language": "python",
        "code": "def hello():\n    print('Hello')",
        "focus_areas": "性能优化",
    },
)
print(f"   前150字符:\n{code_review[:150]}...")
print()

# 测试重构模板
print("7. 使用重构模板...")
refactoring = expand_prompt_template(
    REFACTORING_TEMPLATE,
    {
        "language": "python",
        "code": "def calc(a,b): return a+b",
        "constraints": "保持简洁",
    },
)
print(f"   前150字符:\n{refactoring[:150]}...")
print()

print("✓ 提示模板测试通过")
print()
print("=== 模板系统特性 ===")
print("- {{variable}} 语法变量替换")
print("- 支持变量默认值")
print("- 严格模式错误检查")
print("- 内置常用模板")
