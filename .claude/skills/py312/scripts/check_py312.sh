#!/bin/bash
# Py312 代码质量快速检查脚本
# 用法: ./check_py312.sh [路径]

set -e  # 遇到错误立即退出

TARGET="${1:-.}"
echo "🔍 检查目录: $TARGET"
echo ""

echo "📝 步骤 1/3: 代码风格检查与自动修复..."
ruff check "$TARGET" --fix

echo ""
echo "🎨 步骤 2/3: 代码格式化..."
ruff format "$TARGET"

echo ""
echo "🔬 步骤 3/3: 严格类型检查（Pyright）..."
pyright "$TARGET"

echo ""
echo "✅ 所有检查通过！代码符合 py312 规范。"
