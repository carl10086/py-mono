# Py-Mono: UV Workspaces 极简测试

✅ **测试目的**: 验证 uv workspaces 的内部依赖功能

## 项目结构

```
py-mono/
├── pyproject.toml              # workspace 根配置
├── test.py                     # 测试脚本
└── packages/
    ├── ai/                     # 基础包
    │   ├── ai/__init__.py      # name = "py-mono-ai"
    │   └── pyproject.toml      # 无内部依赖
    └── agent/                  # 上层包
        ├── agent/__init__.py   # 导入并暴露 ai.name
        └── pyproject.toml      # 内部依赖: py-mono-ai
```

## 核心配置

### 内部依赖定义（关键）

```toml
# packages/agent/pyproject.toml
[project]
dependencies = ["py-mono-ai"]  # 不写版本号

[tool.uv.sources]
py-mono-ai = { workspace = true }  # 标记为内部包
```

## 测试结果

```bash
$ uv run python test.py

测试 1: 导入 ai 包
  ✅ ai.name = 'py-mono-ai'

测试 2: 导入 agent 包（会触发内部依赖导入）
  ✅ agent.name = 'py-mono-agent'
  ✅ agent.dependency = 'py-mono-ai'

🎉 Workspace 测试通过！内部依赖工作正常。
```

## 关键命令

```bash
# 安装所有包（包括 workspace 内部）
uv sync --all-packages

# 查看依赖树（确认 editable 安装）
uv tree

# 运行测试
uv run python test.py
```

## 结论

uv workspaces 内部依赖机制：
1. **配置简单**: `dependencies` + `[tool.uv.sources]`
2. **自动链接**: 内部包以 editable 模式安装
3. **实时生效**: 修改 ai 包代码，agent 立即感知
