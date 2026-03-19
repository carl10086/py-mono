# Coding Agent 开发计划

> 基于 pi-mono 架构，完全对标实现

## 项目概述

在 `packages/coding-agent/` 中创建全新的 coding agent 模块，提供：
- 代码编辑工具集（read/write/edit/bash/grep/find/ls）
- 会话持久化（JSONL 格式）
- AgentSession 核心抽象
- SDK 支持（程序化调用）

## 任务拆分路线图

---

### Phase 1: 基础设施与工具集

**目标**: 创建基础包结构，实现核心工具集

#### 1.1 创建包结构
- [x] 创建 `packages/coding-agent/` 目录
- [x] 创建 `pyproject.toml`（依赖: ai, agent）
- [x] 创建 `README.md`
- [x] 创建 `PLAN.md`
- [x] 创建 `src/coding_agent/__init__.py`
- **验证**: `cd packages/coding-agent && uv sync` 成功

#### 1.2 路径与文件工具 (path_utils.py)
- [x] `normalize_path()` - 路径规范化
- [x] `is_path_inside()` - 安全检查
- [x] `validate_path()` - 路径验证
- [x] `resolve_to_cwd()` - 解析为绝对路径
- **验证**: `examples/01_path_utils.py` 测试通过

#### 1.3 内容截断工具 (truncate.py)
- [x] `truncate_head()` - 头部截断
- [x] `truncate_tail()` - 尾部截断
- [x] `truncate_line()` - 行级截断
- [x] `format_size()` - 大小格式化
- **验证**: `examples/02_truncate.py` 测试通过

#### 1.4 文件读取工具 (read.py)
- [x] `create_read_tool()` - 工厂函数
- [x] ReadTool 类实现
- [x] 支持 offset/limit 参数
- [x] 自动截断处理
- [x] 图像文件支持 (PNG, JPG, GIF, WebP)
- **验证**: `examples/03_read_tool.py` 测试通过

#### 1.5 文件写入工具 (write.py)
- [x] `create_write_tool()` - 工厂函数
- [x] WriteTool 类实现
- [x] 目录自动创建
- [x] 写入冲突检测
- **验证**: `examples/04_write_tool.py` 测试通过

#### 1.6 文件编辑工具 (edit.py)
- [x] `create_edit_tool()` - 工厂函数
- [x] EditTool 类实现
- [x] 字符串替换逻辑
- [x] diff 格式支持
- [x] 模糊匹配支持 (edit_diff.py)
- **验证**: `examples/05_edit_tool.py` 测试通过

#### 1.7 Bash 执行工具 (bash.py)
- [ ] `create_bash_tool()` - 工厂函数
- [ ] BashTool 类实现
- [ ] 超时控制
- [ ] 输出截断
- **验证**: `examples/06_bash_tool.py` 执行各类命令

#### 1.8 搜索工具 (grep/find/ls)
- [ ] `create_grep_tool()` - 文本搜索
- [ ] `create_find_tool()` - 文件查找
- [ ] `create_ls_tool()` - 目录列表
- **验证**: `examples/07_search_tools.py` 搜索测试

#### 1.9 工具集合 (tools/__init__.py)
- [ ] `create_coding_tools()` - 完整工具集
- [ ] `create_read_only_tools()` - 只读工具集
- [ ] `create_all_tools()` - 所有工具
- **验证**: `examples/08_tool_collections.py` 验证工具集合

---

### Phase 2: 会话管理系统

**目标**: 实现 JSONL 持久化和 SessionManager

#### 2.1 会话条目类型 (session_types.py)
- [ ] `SessionEntry` 基类
- [ ] `SessionMessageEntry` - 消息条目
- [ ] `CompactionEntry` - 压缩条目
- [ ] `BranchSummaryEntry` - 分支摘要
- [ ] `ModelChangeEntry` - 模型变更
- [ ] `ThinkingLevelChangeEntry` - 思考级别变更
- **验证**: `examples/09_session_types.py` 创建各类条目

#### 2.2 会话管理器核心 (session_manager.py)
- [ ] `SessionManager` 类
- [ ] `create_session()` - 创建新会话
- [ ] `load_session()` - 加载会话
- [ ] `append_entry()` - 追加条目
- [ ] `get_entries()` - 获取条目列表
- [ ] 自动目录创建
- **验证**: `examples/10_session_manager.py` 创建并操作会话

#### 2.3 会话解析与迁移 (session_parser.py)
- [ ] `parse_session_entries()` - 解析 JSONL
- [ ] `migrate_session_entries()` - 版本迁移
- [ ] `CURRENT_SESSION_VERSION` 常量
- **验证**: `examples/11_session_parser.py` 解析测试会话文件

#### 2.4 会话上下文 (session_context.py)
- [ ] `build_session_context()` - 构建上下文
- [ ] `get_latest_compaction_entry()` - 获取最新压缩点
- [ ] 支持分支和导航
- **验证**: `examples/12_session_context.py` 构建复杂上下文

#### 2.5 配置与路径 (config.py)
- [ ] `get_agent_dir()` - Agent 目录
- [ ] `get_sessions_dir()` - 会话目录
- [ ] `VERSION` 常量
- **验证**: `examples/13_config.py` 验证路径生成

---

### Phase 3: AgentSession 核心

**目标**: 实现 AgentSession 类，整合所有功能

#### 3.1 消息处理 (messages.py)
- [ ] `convert_to_llm()` - 转换为 LLM 格式
- [ ] `create_custom_message()` - 创建自定义消息
- [ ] `BashExecutionMessage` - Bash 执行消息
- **验证**: `examples/14_messages.py` 消息转换测试

#### 3.2 系统提示构建 (system_prompt.py)
- [ ] `build_system_prompt()` - 构建系统提示
- [ ] 工具描述生成
- [ ] 动态提示模板
- **验证**: `examples/15_system_prompt.py` 生成系统提示

#### 3.3 设置管理 (settings_manager.py)
- [ ] `SettingsManager` 类
- [ ] 配置加载与保存
- [ ] `CompactionSettings` - 压缩设置
- [ ] `RetrySettings` - 重试设置
- **验证**: `examples/16_settings.py` 读写配置

#### 3.4 模型注册表 (model_registry.py)
- [ ] `ModelRegistry` 类
- [ ] `get_available()` - 获取可用模型
- [ ] `cycle_model()` - 循环切换模型
- **验证**: `examples/17_model_registry.py` 模型操作

#### 3.5 Bash 执行器增强 (bash_executor.py)
- [ ] `execute_bash()` - 执行命令
- [ ] `execute_bash_with_operations()` - 带操作回调
- [ ] `BashResult` 类型
- **验证**: `examples/18_bash_executor.py` 执行复杂命令

#### 3.6 AgentSession 核心 (agent_session.py)
- [ ] `AgentSession` 类
- [ ] 构造函数与配置
- [ ] `prompt()` - 发送消息
- [ ] 事件订阅系统
- [ ] 状态管理
- [ ] 工具执行
- [ ] 消息持久化
- **验证**: `examples/19_agent_session.py` 完整会话流程

---

### Phase 4: 压缩与上下文管理

**目标**: 实现长会话的压缩和上下文管理

#### 4.1 Token 估算 (compaction/utils.py)
- [ ] `estimate_tokens()` - 估算 token 数
- [ ] `calculate_context_tokens()` - 计算上下文 token
- **验证**: `examples/20_token_estimation.py` token 估算测试

#### 4.2 压缩逻辑 (compaction/compaction.py)
- [ ] `compact()` - 压缩函数
- [ ] `should_compact()` - 判断是否需要压缩
- [ ] `find_cut_point()` - 找到切割点
- **验证**: `examples/21_compaction.py` 压缩会话数据

#### 4.3 分支摘要 (compaction/branch_summary.py)
- [ ] `generate_branch_summary()` - 生成分支摘要
- [ ] `collect_entries_for_branch_summary()` - 收集条目
- **验证**: `examples/22_branch_summary.py` 生成摘要

#### 4.4 压缩导出 (compaction/__init__.py)
- [ ] 整合所有压缩功能
- [ ] 导出公共 API
- **验证**: `examples/23_compaction_full.py` 完整压缩流程

---

### Phase 5: SDK 与程序化接口

**目标**: 提供易用的 SDK 接口

#### 5.1 SDK 核心 (sdk.py)
- [ ] `create_agent_session()` - 创建会话
- [ ] `create_coding_tools()` - 创建工具
- [ ] `create_read_only_tools()` - 创建只读工具
- [ ] 工具工厂函数
- **验证**: `examples/24_sdk.py` SDK 使用示例

#### 5.2 导出与整合 (__init__.py)
- [ ] 导出所有公共类型
- [ ] 导出所有工具函数
- [ ] 导出 SDK 函数
- **验证**: `examples/25_imports.py` 验证所有导入

---

### Phase 6: 扩展系统 (Extension System)

**目标**: 实现插件化扩展机制

#### 6.1 扩展类型定义 (extensions/types.py)
- [ ] `Extension` 接口
- [ ] `ExtensionContext` - 扩展上下文
- [ ] `ExtensionEvent` - 扩展事件
- [ ] `ToolDefinition` - 工具定义
- **验证**: `examples/26_extension_types.py` 定义扩展

#### 6.2 扩展加载器 (extensions/loader.py)
- [ ] `discover_and_load_extensions()` - 发现扩展
- [ ] 扩展扫描与加载
- **验证**: `examples/27_extension_loader.py` 加载扩展

#### 6.3 扩展包装器 (extensions/wrapper.py)
- [ ] `wrap_registered_tool()` - 包装工具
- [ ] `wrap_registered_tools()` - 批量包装
- **验证**: `examples/28_extension_wrapper.py` 工具包装

#### 6.4 扩展运行器 (extensions/runner.py)
- [ ] `ExtensionRunner` 类
- [ ] 事件发射
- [ ] 命令注册
- **验证**: `examples/29_extension_runner.py` 运行扩展

#### 6.5 扩展导出 (extensions/__init__.py)
- [ ] 整合扩展系统
- [ ] 导出公共 API
- **验证**: `examples/30_extensions.py` 完整扩展测试

---

### Phase 7: Skills 系统

**目标**: 实现可复用的技能 (Skills)

#### 7.1 技能定义 (skills.py)
- [ ] `Skill` 类型
- [ ] `load_skills()` - 加载技能
- [ ] `load_skills_from_dir()` - 从目录加载
- [ ] `format_skills_for_prompt()` - 格式化为提示
- **验证**: `examples/31_skills.py` 加载和使用技能

---

### Phase 8: 高级功能

**目标**: 实现高级功能

#### 8.1 提示模板 (prompt_templates.py)
- [ ] `PromptTemplate` 类型
- [ ] `expand_prompt_template()` - 展开模板
- **验证**: `examples/32_prompt_templates.py` 模板展开

#### 8.2 斜杠命令 (slash_commands.py)
- [ ] 内置斜杠命令定义
- [ ] 命令解析
- **验证**: `examples/33_slash_commands.py` 命令解析

#### 8.3 资源加载器 (resource_loader.py)
- [ ] `ResourceLoader` 接口
- [ ] `DefaultResourceLoader` 实现
- **验证**: `examples/34_resource_loader.py` 加载资源

#### 8.4 包管理器 (package_manager.py)
- [ ] `PackageManager` 接口
- [ ] `DefaultPackageManager` 实现
- **验证**: `examples/35_package_manager.py` 包管理

---

### Phase 9: 认证与授权

**目标**: 实现认证系统

#### 9.1 认证存储 (auth_storage.py)
- [ ] `AuthStorage` 类
- [ ] `FileAuthStorageBackend` - 文件后端
- [ ] `InMemoryAuthStorageBackend` - 内存后端
- [ ] API Key 和 OAuth 凭证管理
- **验证**: `examples/36_auth_storage.py` 存储和读取凭证

---

### Phase 10: 事件总线

**目标**: 实现事件系统

#### 10.1 事件总线 (event_bus.py)
- [ ] `EventBus` 类
- [ ] `create_event_bus()` - 工厂函数
- [ ] 订阅与发布
- **验证**: `examples/37_event_bus.py` 事件发布订阅

---

### Phase 11: 测试与验证

**目标**: 完整的测试覆盖

#### 11.1 单元测试 (tests/)
- [ ] 工具测试
- [ ] 会话管理测试
- [ ] AgentSession 测试
- [ ] 压缩测试
- **验证**: `uv run pytest`

#### 11.2 集成测试
- [ ] 端到端会话测试
- [ ] 工具集成测试
- **验证**: `uv run pytest tests/integration/`

---

## 文件结构

```
packages/coding-agent/
├── pyproject.toml
├── README.md
├── PLAN.md
├── src/
│   └── coding_agent/
│       ├── __init__.py
│       ├── config.py
│       ├── agent_session.py
│       ├── auth_storage.py
│       ├── bash_executor.py
│       ├── event_bus.py
│       ├── messages.py
│       ├── model_registry.py
│       ├── model_resolver.py
│       ├── package_manager.py
│       ├── prompt_templates.py
│       ├── resource_loader.py
│       ├── sdk.py
│       ├── settings_manager.py
│       ├── skills.py
│       ├── slash_commands.py
│       ├── system_prompt.py
│       ├── compaction/
│       │   ├── __init__.py
│       │   ├── compaction.py
│       │   ├── branch_summary.py
│       │   └── utils.py
│       ├── extensions/
│       │   ├── __init__.py
│       │   ├── types.py
│       │   ├── loader.py
│       │   ├── runner.py
│       │   └── wrapper.py
│       ├── session/
│       │   ├── __init__.py
│       │   ├── manager.py
│       │   ├── parser.py
│       │   ├── context.py
│       │   └── types.py
│       └── tools/
│           ├── __init__.py
│           ├── bash.py
│           ├── edit.py
│           ├── find.py
│           ├── grep.py
│           ├── ls.py
│           ├── read.py
│           ├── truncate.py
│           ├── write.py
│           └── path_utils.py
├── examples/
│   └── (验证示例，对应每个任务)
└── tests/
    ├── __init__.py
    ├── test_tools.py
    ├── test_session.py
    ├── test_agent_session.py
    └── integration/
        └── test_e2e.py
```

---

## 依赖关系

```
Phase 1 (工具集)
    ↓
Phase 2 (会话管理)
    ↓
Phase 3 (AgentSession)
    ↓
Phase 4 (压缩) ← 依赖 Phase 2
    ↓
Phase 5 (SDK) ← 依赖 Phase 1,2,3
    ↓
Phase 6 (扩展) ← 依赖 Phase 3
    ↓
Phase 7 (Skills) ← 依赖 Phase 3
    ↓
Phase 8-10 (高级功能) ← 依赖前面所有
```

---

## 验收标准

每个 Phase 完成后应满足：

1. **代码质量**: 通过 `uv run poe check`（lint + typecheck）
2. **功能验证**: 所有 examples 可正常运行
3. **文档**: 关键函数有中文文档字符串
4. **类型安全**: Pyright strict mode 无 errors

---

## 下一步行动

1. 确认计划后开始 **Phase 1.1**（创建包结构）
2. 是否需要调整任务拆分或优先级？
3. 是否有特定功能需要提前实现？
