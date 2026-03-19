"""路径工具验证示例。

验证 path_utils 模块的基本功能：
1. normalize_path() - 路径规范化
2. is_path_inside() - 路径安全检查
3. validate_path() - 路径验证
"""

from __future__ import annotations

import os
import tempfile

from coding_agent.tools.path_utils import (
    is_path_inside,
    normalize_path,
    resolve_to_cwd,
    validate_path,
)


def test_normalize_path() -> None:
    """测试路径规范化功能。"""
    print("\n【测试 1】normalize_path() - 路径规范化")
    print("-" * 60)

    # 测试基础路径
    assert normalize_path("/foo/bar") == "/foo/bar"
    print("✓ 普通路径保持不变")

    # 测试空白字符
    assert normalize_path("  /foo/bar  ") == "/foo/bar"
    print("✓ 去除首尾空白")

    # 测试 @ 前缀
    assert normalize_path("@/foo/bar") == "/foo/bar"
    print("✓ 去除 @ 前缀")

    # 测试 ~ 扩展
    home = os.path.expanduser("~")
    assert normalize_path("~") == home
    assert normalize_path("~/test") == home + "/test"
    print(f"✓ 扩展 ~ 到主目录: {home}")

    print("\n路径规范化测试通过！")


def test_resolve_to_cwd() -> None:
    """测试路径解析功能。"""
    print("\n【测试 2】resolve_to_cwd() - 解析为绝对路径")
    print("-" * 60)

    cwd = "/home/user/project"

    # 测试绝对路径
    result = resolve_to_cwd("/absolute/path", cwd)
    assert result == "/absolute/path"
    print("✓ 绝对路径直接返回")

    # 测试相对路径
    result = resolve_to_cwd("relative/path", cwd)
    assert result == "/home/user/project/relative/path"
    print("✓ 相对路径相对于 cwd 解析")

    # 测试 ~ 扩展
    home = os.path.expanduser("~")
    result = resolve_to_cwd("~/test", cwd)
    assert result == f"{home}/test"
    print(f"✓ 扩展 ~ 到主目录")

    print("\n路径解析测试通过！")


def test_is_path_inside() -> None:
    """测试路径安全检查功能。"""
    print("\n【测试 3】is_path_inside() - 路径安全检查")
    print("-" * 60)

    root = "/home/user"

    # 相同路径
    assert is_path_inside("/home/user", "/home/user") is True
    print("✓ 目标等于根路径时返回 True")

    # 子路径
    assert is_path_inside("/home/user/project", "/home/user") is True
    print("✓ 子路径在根路径内")

    # 嵌套子路径
    assert is_path_inside("/home/user/a/b/c", "/home/user") is True
    print("✓ 深层嵌套子路径")

    # 路径遍历攻击检测
    assert is_path_inside("/home/user/../../../etc/passwd", "/home/user") is False
    print("✓ 检测到路径遍历攻击")

    # 兄弟路径
    assert is_path_inside("/home/other", "/home/user") is False
    print("✓ 兄弟路径不在范围内")

    # 前缀误判检测
    assert is_path_inside("/home/username", "/home/user") is False
    print("✓ 避免前缀误判")

    print("\n路径安全检查测试通过！")


def test_validate_path() -> None:
    """测试路径验证功能。"""
    print("\n【测试 4】validate_path() - 路径验证")
    print("-" * 60)

    cwd = os.getcwd()

    # 创建临时文件用于测试
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"test content")
        tmp_path = tmp.name

    # 获取临时文件所在目录
    tmp_dir = os.path.dirname(tmp_path)

    try:
        # 基础验证
        result = validate_path(tmp_path, cwd)
        assert os.path.isabs(result)
        print("✓ 基础路径验证通过")

        # 存在性检查
        result = validate_path(tmp_path, cwd, require_exists=True)
        assert result == tmp_path
        print("✓ 文件存在性验证通过")

        # 不存在文件应抛出异常
        try:
            validate_path("/nonexistent/file.txt", cwd, require_exists=True)
            assert False, "应抛出 FileNotFoundError"
        except FileNotFoundError:
            print("✓ 不存在的文件正确抛出 FileNotFoundError")

        # 安全沙箱检查 - 使用临时文件所在目录作为允许路径
        allowed_roots = [tmp_dir, cwd]
        result = validate_path(tmp_path, cwd, allowed_roots=allowed_roots)
        assert result == tmp_path
        print(f"✓ 安全沙箱验证通过 (允许路径: {tmp_dir})")

        # 超出沙箱应抛出异常
        try:
            validate_path("/etc/passwd", cwd, allowed_roots=allowed_roots)
            assert False, "应抛出 PermissionError"
        except PermissionError:
            print("✓ 超出安全沙箱正确抛出 PermissionError")

    finally:
        os.unlink(tmp_path)

    print("\n路径验证测试通过！")


def main() -> None:
    """运行所有路径工具验证。"""
    print("=" * 60)
    print("路径工具验证示例")
    print("=" * 60)

    test_normalize_path()
    test_resolve_to_cwd()
    test_is_path_inside()
    test_validate_path()

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    main()
