# Coding Agent 开发计划

> 基于 pi-mono 架构，实现功能完整的 Coding Agent 模块

## 🎯 项目目标

在 `packages/coding-agent/` 中创建全新的 coding agent 模块，提供：

1. **代码编辑工具集**：read/write/edit/bash/grep/find/ls 等工具
2. **会话持久化**：JSONL 格式的会话管理
3. **AgentSession 核心**：整合 AI 能力的工作流
4. **SDK 支持**：程序化调用接口

---

## 📊 进展日志（倒序，最新在前）

### [2026-03-20] Phase 9 完成：认证与授权 ✓

**已完成模块**：
- ✅ `auth_storage.py` - 认证存储系统
- ✅ `AuthStorageBackend` 接口
- ✅ `FileAuthStorageBackend` - 文件持久化后端
- ✅ `InMemoryAuthStorageBackend` - 内存后端
- ✅ `ApiKeyCredentials` - API Key 凭证类型
- ✅ `OAuthCredentials` - OAuth 凭证类型

**验证示例**：
- ✅ `36_auth_storage.py` - 认证存储测试

**代码统计**：约 4500 行 Python 代码

### [2026-03-20] Phase 8 完成：高级功能 ✓

**已完成模块**：
- ✅ `prompt_templates.py` - 提示模板系统（变量替换、内置模板）
- ✅ `slash_commands.py` - 斜杠命令系统（7个内置命令、自定义注册）
- ✅ `resource_loader.py` - 资源加载器（文件/内存两种实现）
- ✅ `package_manager.py` - 包管理器（pip封装、NoOp模式）

**验证示例**：
- ✅ `32_prompt_templates.py` - 提示模板测试
- ✅ `33_slash_commands.py` - 斜杠命令测试
- ✅ `34_resource_loader.py` - 资源加载器测试
- ✅ `35_package_manager.py` - 包管理器测试

**代码统计**：约 4200 行 Python 代码

### [2026-03-20] Phase 7 完成：Skills 系统 ✓

**已完成模块**：
- ✅ `skills.py` - Skill 类型、加载和格式化
- ✅ 支持 JSON 和 Markdown 格式
- ✅ 多目录加载和覆盖机制
- ✅ 标签筛选和搜索功能

**验证示例**：
- ✅ `31_skills.py` - 技能系统完整测试

**代码统计**：约 3700 行 Python 代码

### [2026-03-20] Phase 6 完成：扩展系统 ✓

**已完成模块**：
- ✅ `extensions/types.py` - 扩展类型（Extension, ExtensionContext, ToolDefinition）
- ✅ `extensions/loader.py` - 扩展加载器（discover_extensions, load_extension）
- ✅ `extensions/wrapper.py` - 工具包装器（wrap_registered_tool, wrap_registered_tools）
- ✅ `extensions/runner.py` - 扩展运行器（ExtensionRunner 类）
- ✅ `extensions/__init__.py` - 统一导出

**验证示例**：
- ✅ `26_extension_types.py` - 扩展类型测试
- ✅ `27_extension_loader.py` - 扩展加载器测试
- ✅ `28_extension_wrapper.py` - 工具包装器测试
- ✅ `29_extension_runner.py` - 扩展运行器测试
- ✅ `30_extensions.py` - 完整扩展系统测试

**代码统计**：约 3500 行 Python 代码

### [2026-03-20] Phase 5 完成：SDK 与程序化接口 ✓

**已完成模块**：
- ✅ `sdk.py` - SDK 核心（create_agent_session, create_coding_tools, create_read_only_tools, 工具工厂）
- ✅ `__init__.py` - 统一导出（所有公共类型、工具函数、SDK函数）

**验证示例**：
- ✅ `24_sdk.py` - SDK 功能测试
- ✅ `25_imports.py` - 导出验证

**代码统计**：约 3000 行 Python 代码

### [2026-03-20] Phase 4 完成：会话压缩系统 ✓

**已完成模块**：
- ✅ `compaction/utils.py` - Token 估算、文件操作追踪、消息序列化
- ✅ `compaction/compaction.py` - compact() 核心、触发检查
- ✅ `compaction/branch_summary.py` - 分支摘要生成
- ✅ `compaction/__init__.py` - 统一导出

**验证示例**：
- ✅ `20_token_estimation.py` - Token 估算测试
- ✅ `21_compaction.py` - 压缩核心测试
- ✅ `22_branch_summary.py` - 分支摘要测试
- ✅ `23_compaction_full.py` - 完整压缩流程测试

### [2026-03-20] Phase 3 完成：AgentSession 核心 ✓

**已完成模块**：
- ✅ `messages.py` - 消息类型（BashExecutionMessage, CustomMessage等）和 convert_to_llm()
- ✅ `system_prompt.py` - 系统提示构建（工具描述、动态指南）
- ✅ `settings_manager.py` - 设置管理（全局/项目设置、压缩/重试配置）
- ✅ `model_registry.py` - 模型注册表（模型列表、循环切换）
- ✅ `bash_executor.py` - Bash 执行器增强（流式输出、取消支持）
- ✅ `agent_session.py` - AgentSession 核心（简化版骨架）

**验证示例**：
- ✅ `14_messages.py` - 消息处理测试
- ✅ `15_system_prompt.py` - 系统提示测试
- ✅ `16_settings.py` - 设置管理测试
- ✅ `17_model_registry.py` - 模型注册表测试
- ✅ `18_bash_executor.py` - Bash 执行器测试
- ✅ `19_agent_session.py` - AgentSession 占位

**代码统计**：约 2500 行 Python 代码

### [2026-03-20] Phase 2 完成：会话管理系统 ✓

**已完成模块**：
- ✅ `session/types.py` - 9种条目类型定义
- ✅ `session/manager.py` - SessionManager 核心（内存/文件模式）
- ✅ `config.py` - 路径配置（Agent目录、会话目录）
- ✅ `session/parser.py` - JSONL 解析与 v1→v2→v3 版本迁移
- ✅ `session/context.py` - 上下文构建（支持压缩处理）

**验证示例**：
- ✅ `09_session_types.py` - 会话类型测试
- ✅ `10_session_manager.py` - 会话管理器测试
- ✅ `11_session_parser.py` - 解析器测试
- ✅ `12_session_context.py` - 上下文测试

**代码统计**：约 1700 行 Python 代码

### [2026-03-19] Phase 1 完成：基础设施与工具集 ✓

**已完成模块**：
- ✅ 包结构（pyproject.toml, README, src/coding_agent/__init__.py）
- ✅ `tools/path_utils.py` - 路径规范化与安全检查
- ✅ `tools/truncate.py` - 内容截断工具
- ✅ `tools/read.py` - 文件读取（支持图片）
- ✅ `tools/write.py` - 文件写入
- ✅ `tools/edit.py` - 文件编辑（含 diff 模糊匹配）
- ✅ `tools/bash.py` - Bash 执行
- ✅ `tools/grep.py` / `find.py` / `ls.py` - 搜索工具
- ✅ `tools/__init__.py` - 工具集合

**验证示例**：
- ✅ `01_path_utils.py` 到 `08_tool_set.py` 全部通过

**代码统计**：约 2000 行 Python 代码

---

## 🗺️ 待完成任务

### Phase 3: AgentSession 核心 ✅ **已完成**

**目标**：实现 AgentSession 类，整合所有功能

#### 3.1 消息处理 (messages.py) ✅
- [x] `convert_to_llm()` - 转换为 LLM 格式
- [x] `create_custom_message()` - 创建自定义消息
- [x] `BashExecutionMessage` - Bash 执行消息
- **验证**: `examples/14_messages.py` ✅

#### 3.2 系统提示构建 (system_prompt.py) ✅
- [x] `build_system_prompt()` - 构建系统提示
- [x] 工具描述生成
- [x] 动态提示模板
- **验证**: `examples/15_system_prompt.py` ✅

#### 3.3 设置管理 (settings_manager.py) ✅
- [x] `SettingsManager` 类
- [x] 配置加载与保存
- [x] `CompactionSettings` - 压缩设置
- [x] `RetrySettings` - 重试设置
- **验证**: `examples/16_settings.py` ✅

#### 3.4 模型注册表 (model_registry.py) ✅
- [x] `ModelRegistry` 类
- [x] `get_available()` - 获取可用模型
- [x] `cycle_model()` - 循环切换模型
- **验证**: `examples/17_model_registry.py` ✅

#### 3.5 Bash 执行器增强 (bash_executor.py) ✅
- [x] `execute_bash()` - 执行命令
- [x] `BashResult` 类型
- **验证**: `examples/18_bash_executor.py` ✅

#### 3.6 AgentSession 核心 (agent_session.py) ✅ **(简化版)**
- [x] `AgentSession` 类（骨架）
- [x] 构造函数与配置
- [x] 事件订阅系统基础
- [ ] 完整的 prompt() 实现（依赖 AI Agent 核心）
- **验证**: `examples/19_agent_session.py` ✅

---

### Phase 4: 压缩与上下文管理

**目标**：实现长会话的压缩和上下文管理

#### 4.1 Token 估算 (compaction/utils.py) ✅
- [x] `estimate_tokens()` - 估算 token 数
- [x] `calculate_context_tokens()` - 计算上下文 token
- **验证**: `examples/20_token_estimation.py` ✅

#### 4.2 压缩逻辑 (compaction/compaction.py) ✅
- [x] `compact()` - 压缩函数
- [x] `should_compact()` - 判断是否需要压缩
- [x] `find_cut_point()` - 找到切割点
- **验证**: `examples/21_compaction.py` ✅

#### 4.3 分支摘要 (compaction/branch_summary.py) ✅
- [x] `generate_branch_summary()` - 生成分支摘要
- [x] `collect_entries_for_branch_summary()` - 收集条目
- **验证**: `examples/22_branch_summary.py` ✅

#### 4.4 压缩导出 (compaction/__init__.py) ✅
- [x] 整合所有压缩功能
- [x] 导出公共 API
- **验证**: `examples/23_compaction_full.py` ✅

---

### Phase 5: SDK 与程序化接口

**目标**：提供易用的 SDK 接口

#### 5.1 SDK 核心 (sdk.py) ✅
- [x] `create_agent_session()` - 创建会话
- [x] `create_coding_tools()` - 创建工具
- [x] `create_read_only_tools()` - 创建只读工具
- [x] 工具工厂函数
- **验证**: `examples/24_sdk.py` ✅

#### 5.2 导出与整合 (__init__.py) ✅
- [x] 导出所有公共类型
- [x] 导出所有工具函数
- [x] 导出 SDK 函数
- **验证**: `examples/25_imports.py` ✅

---

### Phase 6: 扩展系统 (Extension System)

**目标**：实现插件化扩展机制

#### 6.1 扩展类型定义 (extensions/types.py) ✅
- [x] `Extension` 接口
- [x] `ExtensionContext` - 扩展上下文
- [x] `ToolDefinition` - 工具定义
- **验证**: `examples/26_extension_types.py` ✅

#### 6.2 扩展加载器 (extensions/loader.py) ✅
- [x] `discover_extensions()` - 发现扩展
- [x] `load_extension()` - 加载扩展
- [x] 扩展扫描与加载
- **验证**: `examples/27_extension_loader.py` ✅

#### 6.3 扩展包装器 (extensions/wrapper.py) ✅
- [x] `wrap_registered_tool()` - 包装工具
- [x] `wrap_registered_tools()` - 批量包装
- [x] 全局工具注册表
- **验证**: `examples/28_extension_wrapper.py` ✅

#### 6.4 扩展运行器 (extensions/runner.py) ✅
- [x] `ExtensionRunner` 类
- [x] 扩展生命周期管理
- [x] 命令注册
- **验证**: `examples/29_extension_runner.py` ✅

#### 6.5 扩展导出 (extensions/__init__.py) ✅
- [x] 整合扩展系统
- [x] 导出公共 API
- **验证**: `examples/30_extensions.py` ✅

---

### Phase 7: Skills 系统

**目标**：实现可复用的技能 (Skills)

#### 7.1 技能定义 (skills.py) ✅
- [x] `Skill` 类型
- [x] `load_skills()` - 加载技能
- [x] `load_skills_from_dir()` - 从目录加载
- [x] `format_skills_for_prompt()` - 格式化为提示
- [x] `get_skill_by_tag()` - 按标签筛选
- [x] `search_skills()` - 搜索技能
- **验证**: `examples/31_skills.py` ✅

---

### Phase 8: 高级功能

**目标**：实现高级功能

#### 8.1 提示模板 (prompt_templates.py) ✅
- [x] `PromptTemplate` 类型
- [x] `create_prompt_template()` - 创建模板
- [x] `expand_prompt_template()` - 展开模板
- [x] 3个内置模板（code-review, refactoring, debugging）
- **验证**: `examples/32_prompt_templates.py` ✅

#### 8.2 斜杠命令 (slash_commands.py) ✅
- [x] `SlashCommand` 类型
- [x] `SlashCommandRegistry` 注册表
- [x] 7个内置命令（help, clear, exit, model, compact, undo, redo）
- [x] `parse_slash_command()` - 命令解析
- **验证**: `examples/33_slash_commands.py` ✅

#### 8.3 资源加载器 (resource_loader.py) ✅
- [x] `ResourceLoader` 接口
- [x] `DefaultResourceLoader` 文件实现
- [x] `InMemoryResourceLoader` 内存实现
- [x] `ResourceNotFoundError` 异常
- **验证**: `examples/34_resource_loader.py` ✅

#### 8.4 包管理器 (package_manager.py) ✅
- [x] `PackageManager` 接口
- [x] `DefaultPackageManager` pip实现
- [x] `NoOpPackageManager` 空实现
- [x] `PackageInfo` 包信息类型
- **验证**: `examples/35_package_manager.py` ✅

---

### Phase 9: 认证与授权

**目标**：实现认证系统

#### 9.1 认证存储 (auth_storage.py) ✅
- [x] `AuthStorage` 类
- [x] `AuthStorageBackend` 接口
- [x] `FileAuthStorageBackend` - 文件后端
- [x] `InMemoryAuthStorageBackend` - 内存后端
- [x] `ApiKeyCredentials` - API Key 凭证
- [x] `OAuthCredentials` - OAuth 凭证
- **验证**: `examples/36_auth_storage.py` ✅

---

### Phase 10: 事件总线

**目标**：实现事件系统

#### 10.1 事件总线 (event_bus.py)
- [ ] `EventBus` 类
- [ ] `create_event_bus()` - 工厂函数
- [ ] 订阅与发布
- **验证**: `examples/37_event_bus.py`

---

### Phase 11: 测试与验证

**目标**：完整的测试覆盖

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

## 🔑 关键约定（必读）

### 1. 强制使用的 Skills

开发时必须加载以下 skills：

- **`pi-mono-refer`**: 实现 AI 模块前**必须**先阅读 `refer/pi-mono` TypeScript 源码
- **`py312`**: Python 3.12+ 严格规范
  - 函数 ≤ 30 行，超过必须拆分
  - 中文文档字符串
  - 完整类型注解（包括 `-> None`）
  - 使用 `@override` 装饰重写方法

### 2. 开发工作流程

```
1. 读参考源码 (pi-mono-refer)
   ↓
2. 创建验证示例 (examples/XX_*.py)
   ↓
3. 实现功能模块
   ↓
4. 运行验证示例
   ↓
5. 类型检查 (uv run poe typecheck) - 强制！
```

### 3. 验证命令

```bash
# 验证单个示例
cd packages/coding-agent
uv run python examples/09_session_types.py

# 类型检查 - 每次修改后必须运行！
cd packages/coding-agent
uv run poe typecheck

# 完整检查
uv run poe check  # lint + typecheck + test
```

### 4. 依赖管理注意事项

- **必须使用 uv 环境**：不能用系统 Python
- **根目录无 dev 依赖**：pytest 等只在子包安装
- **在子包目录运行测试**：`cd packages/ai && uv run pytest`

### 5. 代码质量要求

- 函数 ≤ 30 行
- 所有函数参数标注类型
- 所有类属性标注类型
- 关键函数必须包含中文文档字符串
- 使用 Pydantic v2 进行数据验证

### 6. 参考项目结构

```
refer/
├── pi-mono/          - 架构参考：monorepo、分层架构
├── kimi-cli/         - 技术栈参考：Python + uv + asyncio
└── opencode/         - 实现参考：Agent 生命周期、工具系统
```

### 7. 当前工作目录

- 包路径：`packages/coding-agent/`
- 源代码：`src/coding_agent/`
- 验证示例：`examples/`

---

## 📁 项目文件结构

```
packages/coding-agent/
├── pyproject.toml
├── README.md
├── PLAN.md                    <- 本文件
├── src/coding_agent/
│   ├── __init__.py
│   ├── config.py              ✅ Phase 2
│   ├── agent_session.py       ⏳ Phase 3
│   ├── auth_storage.py        ⏳ Phase 9
│   ├── bash_executor.py       ⏳ Phase 3
│   ├── event_bus.py           ⏳ Phase 10
│   ├── messages.py            ⏳ Phase 3
│   ├── model_registry.py      ⏳ Phase 3
│   ├── model_resolver.py      ⏳ Phase 3
│   ├── package_manager.py     ⏳ Phase 8
│   ├── prompt_templates.py    ⏳ Phase 8
│   ├── resource_loader.py     ⏳ Phase 8
│   ├── sdk.py                 ⏳ Phase 5
│   ├── settings_manager.py    ⏳ Phase 3
│   ├── skills.py              ⏳ Phase 7
│   ├── slash_commands.py      ⏳ Phase 8
│   ├── system_prompt.py       ⏳ Phase 3
│   ├── compaction/            ⏳ Phase 4
│   │   ├── __init__.py
│   │   ├── compaction.py
│   │   ├── branch_summary.py
│   │   └── utils.py
│   ├── extensions/            ⏳ Phase 6
│   │   ├── __init__.py
│   │   ├── types.py
│   │   ├── loader.py
│   │   ├── runner.py
│   │   └── wrapper.py
│   ├── session/               ✅ Phase 2
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   ├── parser.py
│   │   ├── context.py
│   │   └── types.py
│   └── tools/                 ✅ Phase 1
│       ├── __init__.py
│       ├── bash.py
│       ├── edit.py
│       ├── find.py
│       ├── grep.py
│       ├── ls.py
│       ├── read.py
│       ├── truncate.py
│       ├── write.py
│       └── path_utils.py
├── examples/
│   ├── 01_path_utils.py       ✅
│   ├── 02_truncate.py         ✅
│   ├── 03_read_tool.py        ✅
│   ├── 04_write_tool.py       ✅
│   ├── 05_edit_tool.py        ✅
│   ├── 06_bash_tool.py        ✅
│   ├── 07_search_tools.py     ✅
│   ├── 08_tool_set.py         ✅
│   ├── 09_session_types.py    ✅
│   ├── 10_session_manager.py  ✅
│   ├── 11_session_parser.py   ✅
│   ├── 12_session_context.py  ✅
│   └── (13-37 待实现)
└── tests/
    ├── __init__.py
    ├── test_tools.py          ⏳
    ├── test_session.py        ⏳
    ├── test_agent_session.py  ⏳
    └── integration/
        └── test_e2e.py        ⏳
```

---

## 🔄 依赖关系图

```
Phase 1 (工具集) ✅
    ↓
Phase 2 (会话管理) ✅
    ↓
Phase 3 (AgentSession) [当前]
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
    ↓
Phase 11 (测试)
```

---

## 📌 最后更新

- **更新时间**: 2026-03-20
- **当前阶段**: Phase 3 ✅ 已完成
- **下个任务**: 开始 Phase 4 压缩与上下文管理，或集成 AI Agent 核心完成 AgentSession

---

## 📊 当前代码统计

| Phase | 模块数 | 代码行数 | 状态 |
|-------|--------|----------|------|
| Phase 1 | 9 | ~2000 | ✅ 完成 |
| Phase 2 | 5 | ~1700 | ✅ 完成 |
| Phase 3 | 6 | ~2500 | ✅ 完成 |
| **总计** | **20** | **~6200** | ✅ 前三阶段完成 |
