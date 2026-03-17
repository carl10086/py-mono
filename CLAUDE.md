# Py-Mono: AI Agent 架构

## 目标

构建 **AI 编程助手** —— 一个能理解代码、执行命令、自主完成开发任务的智能 Agent。

不是简单的 chat，而是能动手做事的 Agent：
- 读代码、改代码、写代码
- 运行测试、检查错误、修复问题
- 调用工具、访问 API、查询文档
- 自主规划任务、执行、验证结果

## 核心参考

参考项目源码存放在 `refer/` 目录：

- `refer/pi-mono/` - 架构参考：monorepo 结构、分层架构、依赖注入
- `refer/kimi-cli/` - 技术栈参考：Python + uv + asyncio + Pydantic
- `refer/opencode/` - 实现参考：Agent 生命周期、工具系统、上下文管理

## 项目结构

```
packages/
├── ai/              # AI 核心层（LLM 接口、Agent 基类、工具系统、记忆管理）
└── agent/           # Agent 运行时（CLI 交互、服务进程、配置管理、插件系统）
```

## 设计原则

1. **能跑起来**: 先实现最小可用版本，再迭代优化
2. **工具优先**: 核心能力是工具调用，不是对话
3. **可观测**: 每一步操作都可见、可追踪、可回滚
4. **可扩展**: 新工具、新模型、新能力易于添加

## 开发命令

```bash
uv sync              # 安装依赖
uv run poe lint      # 代码风格检查 (ruff)
uv run poe typecheck # 类型检查 (pyright) - ⚠️ 强制要求
uv run poe test      # 运行测试
uv run poe check     # 完整检查 (lint + typecheck + test)
```

## 依赖管理设计

采用 **分散式 dev 依赖** 策略（方案1）：

```
py-mono/
├── pyproject.toml          # 根目录：只定义生产依赖，不定义 dev 依赖
├── packages/
│   ├── ai/
│   │   └── pyproject.toml  # 子包：定义自己的 dev 依赖（pytest等）
│   └── agent/
│       └── pyproject.toml  # 子包：定义自己的 dev 依赖
```

**为什么这样设计：**
- Python 没有像 Maven 的 `<parent>` 继承机制
- 每个子包是独立单元，自行管理开发和测试依赖
- 避免在根目录重复定义 dev 依赖

**运行测试：**
```bash
# 正确做法：在子包目录运行
cd packages/ai && uv run pytest

# 错误做法：在根目录运行（根目录没有安装 pytest）
uv run pytest  # ❌ ModuleNotFoundError: pytest
```

## 代码质量强制要求

**每次修改代码后必须运行：**

```bash
cd packages/ai && uv run poe typecheck  # 强制！检查类型注解
```

**类型检查配置使用 pyright，启用严格模式：**
- 所有函数参数必须标注类型
- 所有类属性必须标注类型（包括私有属性 `_api_key` 等）
- 重写方法必须使用 `@override` 装饰器
- 不允许有 `Unknown` 类型

**完整检查流程（提交前）：**
```bash
cd packages/ai
uv run poe check  # 运行 lint + typecheck + test
```

## 注意事项

- 不能用 系统的 python 运行，必须使用 uv 环境
- 开发依赖（pytest等）只在子包中可用，根目录不重复安装
- **修改代码后必须运行类型检查**，确保 pyright 无 errors
