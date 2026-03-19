# Coding Agent

AI Coding Agent 模块 - 基于 pi-mono 架构的 Python 实现。

## 功能特性

- **代码编辑工具集**: read, write, edit, bash, grep, find, ls
- **会话持久化**: JSONL 格式存储，支持分支和导航
- **AgentSession**: 核心抽象，管理 Agent 生命周期
- **SDK 支持**: 程序化调用接口

## 项目结构

```
coding_agent/
├── __init__.py          # 模块导出
├── config.py            # 配置与路径
├── agent_session.py     # AgentSession 核心
├── auth_storage.py      # 认证存储
├── bash_executor.py     # Bash 执行器
├── event_bus.py         # 事件总线
├── messages.py          # 消息处理
├── model_registry.py    # 模型注册表
├── model_resolver.py    # 模型解析
├── package_manager.py   # 包管理器
├── prompt_templates.py  # 提示模板
├── resource_loader.py   # 资源加载器
├── sdk.py               # SDK 接口
├── settings_manager.py  # 设置管理
├── skills.py            # Skills 系统
├── slash_commands.py    # 斜杠命令
├── system_prompt.py     # 系统提示
├── compaction/          # 压缩与上下文管理
├── extensions/          # 扩展系统
├── session/             # 会话管理
└── tools/               # 工具集
```

## 开发计划

详见 [PLAN.md](./PLAN.md)

## 安装

```bash
cd packages/coding-agent
uv sync
```

## 使用

```python
from coding_agent import create_agent_session, create_coding_tools

# 创建工具
tools = create_coding_tools(cwd="/path/to/project")

# 创建会话
session = create_agent_session(
    cwd="/path/to/project",
    tools=tools
)

# 发送消息
response = await session.prompt("读取 README.md 文件")
```

## 验证

每个功能都有对应的 example 验证：

```bash
cd packages/coding-agent
uv run python examples/01_path_utils.py
```

## 代码质量

```bash
# 格式化与检查
ruff check . --fix
ruff format .

# 类型检查（强制）
pyright .
```

## License

MIT
