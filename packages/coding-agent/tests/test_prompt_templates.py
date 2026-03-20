from __future__ import annotations

from coding_agent.prompt_templates import (
    CODE_REVIEW_TEMPLATE,
    REFACTORING_TEMPLATE,
    create_prompt_template,
    expand_prompt_template,
    expand_template_string,
    get_builtin_template,
    list_builtin_templates,
)


def test_create_prompt_template():
    template = create_prompt_template(
        template_id="greeting",
        name="问候模板",
        description="生成问候语",
        template="你好，{{name}}！欢迎{{action}}。",
        defaults={"action": "加入我们"},
    )
    assert template.id == "greeting"
    assert "name" in template.variables
    assert "action" in template.defaults


def test_expand_prompt_template():
    template = create_prompt_template(
        template_id="greeting",
        name="问候模板",
        description="生成问候语",
        template="你好，{{name}}！欢迎{{action}}。",
        defaults={"action": "加入我们"},
    )
    result = expand_prompt_template(template, {"name": "张三"})
    assert "张三" in result
    assert "加入我们" in result


def test_expand_prompt_template_strict():
    template = create_prompt_template(
        template_id="test",
        name="Test",
        description="Test",
        template="Hello {{name}}",
    )
    try:
        expand_prompt_template(template, {}, strict=True)
        assert False
    except ValueError:
        pass


def test_expand_template_string():
    result = expand_template_string(
        "今天是{{day}}，天气{{weather}}", {"day": "周一", "weather": "晴朗"}
    )
    assert "周一" in result
    assert "晴朗" in result


def test_list_builtin_templates():
    builtin_ids = list_builtin_templates()
    assert len(builtin_ids) > 0


def test_get_builtin_template():
    builtin_ids = list_builtin_templates()
    if builtin_ids:
        tid = builtin_ids[0]
        t = get_builtin_template(tid)
        assert t is not None
        assert t.id == tid


def test_code_review_template():
    code_review = expand_prompt_template(
        CODE_REVIEW_TEMPLATE,
        {
            "language": "python",
            "code": "def hello():\n    print('Hello')",
            "focus_areas": "性能优化",
        },
    )
    assert len(code_review) > 0


def test_refactoring_template():
    refactoring = expand_prompt_template(
        REFACTORING_TEMPLATE,
        {
            "language": "python",
            "code": "def calc(a,b): return a+b",
            "constraints": "保持简洁",
        },
    )
    assert len(refactoring) > 0
