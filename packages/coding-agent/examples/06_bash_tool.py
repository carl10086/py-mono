"""Bash 工具验证示例.

验证 bash 执行工具的各项功能。
"""

import asyncio
import os
import tempfile

from coding_agent.tools.bash import bash_tool, create_bash_tool


async def test_basic_command() -> None:
    """测试基本命令执行."""
    print("=== 测试1: 基本命令 ===")
    tool = bash_tool()

    result = await tool.execute(
        "test-1",
        {"command": "echo 'Hello from bash!'"},
    )

    print(f"结果类型: {type(result)}")
    content = result.content[0].text
    print(f"输出: {content[:100]}...")
    print("✓ 基本命令执行成功\n")


async def test_working_directory() -> None:
    """测试工作目录切换."""
    print("=== 测试2: 工作目录 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tool = create_bash_tool(tmpdir)

        result = await tool.execute(
            "test-2",
            {"command": "pwd"},
        )

        content = result.content[0].text
        print(f"工作目录输出: {content.strip()}")
        print(f"期望路径: {tmpdir}")
        assert tmpdir in content, "工作目录不匹配"
        print("✓ 工作目录切换成功\n")


async def test_command_with_error() -> None:
    """测试命令错误处理."""
    print("=== 测试3: 命令错误处理 ===")
    tool = bash_tool()

    result = await tool.execute(
        "test-3",
        {"command": "exit 42"},
    )

    print(f"结果: {result.content[0].text}")
    assert "exit code 42" in result.content[0].text or "命令退出码: 42" in result.content[0].text
    print("✓ 命令错误处理成功\n")


async def test_timeout() -> None:
    """测试超时功能."""
    print("=== 测试4: 超时功能 ===")
    tool = bash_tool()

    result = await tool.execute(
        "test-4",
        {"command": "sleep 10", "timeout": 1},
    )

    print(f"结果: {result.content[0].text}")
    assert "超时" in result.content[0].text
    print("✓ 超时功能正常\n")


async def test_output_truncation() -> None:
    """测试输出截断."""
    print("=== 测试5: 输出截断 ===")
    tool = bash_tool()

    result = await tool.execute(
        "test-5",
        {"command": "seq 1 3000"},
    )

    content = result.content[0].text
    details = result.details

    print(f"输出行数: {len(content.split(chr(10)))}")
    if details and details.truncation:
        trunc = details.truncation
        print(f"截断信息: 总共 {trunc.total_lines} 行，显示 {trunc.output_lines} 行")
        print(f"临时文件: {details.full_output_path}")
    else:
        print("输出未被截断")

    print("✓ 输出截断功能正常\n")


async def test_environment_variables() -> None:
    """测试环境变量."""
    print("=== 测试6: 环境变量 ===")
    tool = bash_tool()

    result = await tool.execute(
        "test-6",
        {"command": "echo $HOME && echo $PATH | head -c 50"},
    )

    content = result.content[0].text
    print(f"环境变量输出: {content}")
    assert os.environ.get("HOME", "") in content
    print("✓ 环境变量继承成功\n")


async def test_multiline_command() -> None:
    """测试多行命令."""
    print("=== 测试7: 多行命令 ===")
    tool = bash_tool()

    cmd = 'echo "Line 1"\necho "Line 2"\necho "Line 3"'
    result = await tool.execute(
        "test-7",
        {"command": cmd},
    )

    content = result.content[0].text
    print(f"输出:\n{content}")
    assert "Line 1" in content
    assert "Line 2" in content
    assert "Line 3" in content
    print("✓ 多行命令执行成功\n")


async def test_stderr_output() -> None:
    """测试 stderr 输出捕获."""
    print("=== 测试8: stderr 捕获 ===")
    tool = bash_tool()

    result = await tool.execute(
        "test-8",
        {"command": "echo 'stdout' && echo 'stderr' >&2"},
    )

    content = result.content[0].text
    print(f"输出:\n{content}")
    assert "stdout" in content
    assert "stderr" in content
    print("✓ stderr 捕获成功\n")


async def main() -> None:
    """运行所有测试."""
    print("Bash 工具验证\n")
    print("=" * 50)

    await test_basic_command()
    await test_working_directory()
    await test_command_with_error()
    await test_timeout()
    await test_output_truncation()
    await test_environment_variables()
    await test_multiline_command()
    await test_stderr_output()

    print("=" * 50)
    print("所有测试通过！")


if __name__ == "__main__":
    asyncio.run(main())
