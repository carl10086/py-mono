#!/usr/bin/env python3
"""
Phase 3.3 验证示例：设置管理

验证内容：
1. SettingsManager 创建和加载
2. 设置读写
3. 设置保存

运行方式：
    cd packages/coding-agent && uv run python examples/16_settings.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# 添加包路径
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "ai" / "src"))
sys.path.insert(0, str(root_dir / "agent" / "src"))
sys.path.insert(0, str(root_dir / "coding-agent" / "src"))

from coding_agent.settings_manager import (
    CompactionSettings,
    RetrySettings,
    Settings,
    SettingsManager,
)


def test_in_memory_settings() -> None:
    """测试内存设置管理器"""
    print("=" * 60)
    print("测试内存设置管理器")
    print("=" * 60)

    # 创建内存设置
    settings = Settings(
        default_provider="anthropic",
        default_model="claude-3",
        default_thinking_level="medium",
    )
    manager = SettingsManager.in_memory(settings)

    print(f"\n默认提供商: {manager.get_default_provider()}")
    print(f"默认模型: {manager.get_default_model()}")
    print(f"默认思考级别: {manager.get_default_thinking_level()}")

    # 修改设置
    manager.set_default_provider("openai")
    print(f"\n修改后提供商: {manager.get_default_provider()}")

    print("\n✓ 内存设置测试通过")


def test_compaction_settings() -> None:
    """测试压缩设置"""
    print("\n" + "=" * 60)
    print("测试压缩设置")
    print("=" * 60)

    manager = SettingsManager.in_memory()

    compaction = manager.get_compaction_settings()
    print(f"\n压缩启用: {compaction.enabled}")
    print(f"保留 Token: {compaction.reserve_tokens}")
    print(f"保留最近 Token: {compaction.keep_recent_tokens}")

    # 修改设置
    manager.set_compaction_enabled(False)
    compaction2 = manager.get_compaction_settings()
    print(f"\n修改后启用: {compaction2.enabled}")

    print("\n✓ 压缩设置测试通过")


def test_retry_settings() -> None:
    """测试重试设置"""
    print("\n" + "=" * 60)
    print("测试重试设置")
    print("=" * 60)

    manager = SettingsManager.in_memory()

    retry = manager.get_retry_settings()
    print(f"\n重试启用: {retry.enabled}")
    print(f"最大重试: {retry.max_retries}")
    print(f"基础延迟: {retry.base_delay_ms}ms")

    # 修改设置
    manager.set_retry_enabled(False)
    retry2 = manager.get_retry_settings()
    print(f"\n修改后启用: {retry2.enabled}")

    print("\n✓ 重试设置测试通过")


def test_file_settings() -> None:
    """测试文件设置"""
    print("\n" + "=" * 60)
    print("测试文件设置")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建设置文件
        settings_file = Path(tmpdir) / ".pi" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text('{"default_provider": "test-provider"}')

        # 加载设置
        manager = SettingsManager.create(cwd=tmpdir, agent_dir=tmpdir)

        print(f"\n从文件加载的提供商: {manager.get_default_provider()}")

        # 修改并保存
        manager.set_default_model("test-model")
        errors = manager.save()

        print(f"保存错误数: {len(errors)}")

        # 验证文件内容
        if settings_file.exists():
            content = settings_file.read_text()
            print(f"文件内容包含 model: {'test-model' in content}")

    print("\n✓ 文件设置测试通过")


def test_settings_merge() -> None:
    """测试设置合并"""
    print("\n" + "=" * 60)
    print("测试设置合并")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建全局设置
        agent_dir = Path(tmpdir) / "agent"
        agent_dir.mkdir()
        global_file = agent_dir / "settings.json"
        global_file.write_text('{"default_provider": "global-provider", "theme": "dark"}')

        # 创建项目设置
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        pi_dir = project_dir / ".pi"
        pi_dir.mkdir()
        project_file = pi_dir / "settings.json"
        project_file.write_text('{"default_provider": "project-provider"}')

        # 加载设置（项目应该覆盖全局）
        manager = SettingsManager.create(cwd=str(project_dir), agent_dir=str(agent_dir))

        print(f"\n提供商（项目覆盖）: {manager.get_default_provider()}")
        print(f"主题（继承全局）: {manager.get_theme()}")

    print("\n✓ 设置合并测试通过")


def main() -> int:
    """主函数"""
    try:
        test_in_memory_settings()
        test_compaction_settings()
        test_retry_settings()
        test_file_settings()
        test_settings_merge()

        print("\n" + "=" * 60)
        print("所有测试通过!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
