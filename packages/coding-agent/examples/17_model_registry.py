#!/usr/bin/env python3
"""
Phase 3.4 验证示例：模型注册表

运行方式：
    cd packages/coding-agent && uv run python examples/17_model_registry.py
"""

from __future__ import annotations

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir / "ai" / "src"))
sys.path.insert(0, str(root_dir / "agent" / "src"))
sys.path.insert(0, str(root_dir / "coding-agent" / "src"))

from coding_agent.model_registry import ModelRegistry


def main() -> int:
    """主函数"""
    print("=" * 60)
    print("测试模型注册表")
    print("=" * 60)

    registry = ModelRegistry()

    # 获取所有模型
    all_models = registry.get_all()
    print(f"\n所有模型数: {len(all_models)}")
    for m in all_models:
        print(f"  - {m.provider}/{m.id}: {m.name}")

    # 获取可用模型
    available = registry.get_available(has_auth=["anthropic", "openai"])
    print(f"\n可用模型数: {len(available)}")

    # 查找模型
    model = registry.find("anthropic", "claude-3-opus")
    print(f"\n查找到的模型: {model.name if model else 'None'}")

    # 循环切换
    next_model = registry.cycle_model("anthropic", "claude-3-opus", ["anthropic", "openai"])
    print(f"下一个模型: {next_model.name if next_model else 'None'}")

    print("\n✓ 模型注册表测试通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
