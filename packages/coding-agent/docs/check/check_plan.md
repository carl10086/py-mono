# Coding Agent 实现验证计划

> 按照设计文档逐步验证实现与设计的一致性

---

## 验证原则

1. **按顺序进行**：从底层到高层，逐步验证
2. **每个模块都要过**：设计与代码对照
3. **问题及时记录**：发现不一致先记录，不阻塞
4. **运行示例验证**：每个模块都要运行示例验证功能

---

## Phase 1: 基础设施层（Step 1-5）

### Step 1: 验证目录结构和模块组织

**设计文档参考**：`01-overview.md` 第 2 节 + `04-implementation-roadmap.md`

**验证目标**：
```
packages/coding-agent/src/coding_agent/
├── session/           # 会话持久化
├── tools/             # 工具系统
├── compaction/        # 上下文压缩
├── extensions/        # 扩展系统
├── __init__.py        # 统一导出
├── config.py          # 配置管理
├── messages.py         # 消息类型
├── system_prompt.py   # 系统提示
├── settings_manager.py # 设置管理
├── model_registry.py   # 模型注册
├── bash_executor.py    # Bash 执行器
├── agent_session.py    # AgentSession 核心
├── sdk.py             # SDK 接口
├── skills.py          # 技能系统
├── prompt_templates.py # 提示模板
├── slash_commands.py  # 斜杠命令
├── resource_loader.py  # 资源加载
├── package_manager.py  # 包管理器
└── auth_storage.py    # 认证存储
```

**验证方法**：
```bash
ls -la packages/coding-agent/src/coding_agent/
```

**验收标准**：
- [ ] 所有目录和文件都存在
- [ ] 与设计文档的模块划分一致

---

### Step 2: 验证 config.py - 配置管理

**设计文档参考**：`02-components.md` 第 1 节（AgentSession 依赖 SettingsManager）

**验证目标**：
- Path 配置（session、agent、extensions 目录）
- 工作目录管理

**代码检查**：
```python
# 检查 src/coding_agent/config.py
```

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/01_path_utils.py
```

**验收标准**：
- [ ] Path 类正确实现
- [ ] session_dir、agent_dir 等路径配置正确
- [ ] 示例运行通过

---

### Step 3: 验证 session/types.py - 会话数据类型

**设计文档参考**：`03-data-models.md` 第 1 节（9 种 Entry 类型）

**验证目标**：
```
SessionEntry (基类)
├── SessionHeader
├── SessionMessageEntry
├── ThinkingLevelChangeEntry
├── ModelChangeEntry
├── CompactionEntry
├── BranchSummaryEntry
├── CustomEntry
├── CustomMessageEntry
└── LabelEntry
```

**代码检查**：
```python
# 检查 src/coding_agent/session/types.py
```

**验收标准**：
- [ ] 9 种 Entry 类型全部定义
- [ ] 继承关系正确（都继承 SessionEntry）
- [ ] parentId、timestamp 等基类字段存在

---

### Step 4: 验证 session/manager.py - 会话管理器

**设计文档参考**：`02-components.md` 第 2 节（SessionManager 详细设计）

**验证目标**：
- JSONL 持久化
- 树形结构（parentId）
- appendMessage、buildSessionContext 方法
- 分支功能

**代码检查**：
```python
# 检查 src/coding_agent/session/manager.py
```

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/10_session_manager.py
```

**验收标准**：
- [ ] JSONL 文件读写正确
- [ ] 树形结构构建正确
- [ ] buildSessionContext 从叶到根回溯
- [ ] 示例运行通过

---

### Step 5: 验证 session/parser.py + session/context.py

**设计文档参考**：`02-components.md` 第 2.3 节（JSONL 解析）

**验证目标**：
- JSONL 行解析
- 版本迁移（v1 → v2 → v3）
- 上下文构建

**代码检查**：
```python
# 检查 src/coding_agent/session/parser.py
# 检查 src/coding_agent/session/context.py
```

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/11_session_parser.py
cd packages/coding-agent && uv run python examples/12_session_context.py
```

**验收标准**：
- [ ] JSONL 解析正确
- [ ] 版本迁移逻辑存在
- [ ] buildSessionContext 正确
- [ ] 示例运行通过

---

## Phase 2: 工具系统（Step 6-10）

### Step 6: 验证 tools/__init__.py - 工具导出

**设计文档参考**：`01-overview.md` 第 5 节（7 种内置工具）

**验证目标**：
```
工具列表：
- read      # 读取文件
- write     # 写入文件
- edit      # 字符串替换
- bash      # 执行命令
- grep      # 搜索内容
- find      # 查找文件
- ls        # 列出目录
```

**代码检查**：
```python
# 检查 src/coding_agent/tools/__init__.py
```

**验收标准**：
- [ ] 7 种工具都已实现
- [ ] create_read_tool, create_write_tool 等工厂函数存在

---

### Step 7: 验证 tools/read.py - 读取工具

**设计文档参考**：`01-overview.md` 第 5 节（read 工具功能）

**验证目标**：
- 支持路径参数
- 支持内容截断（超出限制时）
- 返回格式正确

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/03_read_tool.py
```

**验收标准**：
- [ ] 可以读取文件内容
- [ ] 超出限制时正确截断
- [ ] 示例运行通过

---

### Step 8: 验证 tools/write.py + tools/edit.py

**设计文档参考**：`details/01-edit-tool.md`, `details/02-write-tool.md`

**验证目标**：
- write: 创建新文件、覆盖文件、自动创建目录
- edit: 精确替换、模糊匹配、换行符保留

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/04_write_tool.py
cd packages/coding-agent && uv run python examples/05_edit_tool.py
```

**pytest 验证**：
```bash
cd packages/coding-agent && uv run pytest tests/test_write_tool.py tests/test_edit_tool.py -v
```

**验收标准**：
- [ ] write 创建和覆盖文件正确
- [ ] edit 替换逻辑正确
- [ ] pytest 单元测试全部通过

---

### Step 9: 验证 tools/bash.py

**设计文档参考**：`details/03-bash-tool.md`

**验证目标**：
- 命令执行
- 超时处理
- 输出截断
- 工作目录切换

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/06_bash_tool.py
```

**pytest 验证**：
```bash
cd packages/coding-agent && uv run pytest tests/test_bash_tool.py -v
```

**验收标准**：
- [ ] 基本命令执行正确
- [ ] 超时处理正确
- [ ] pytest 测试全部通过

---

### Step 10: 验证 tools/grep.py + tools/find.py + tools/ls.py

**设计文档参考**：`01-overview.md` 第 5 节（grep/find/ls 功能）

**验证目标**：
- grep: 搜索文件内容、支持正则
- find: 按模式查找文件
- ls: 列出目录内容

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/07_search_tools.py
```

**验收标准**：
- [ ] grep 搜索功能正确
- [ ] find 查找功能正确
- [ ] ls 列出功能正确
- [ ] 示例运行通过

---

## Phase 3: 压缩系统（Step 11-13）

### Step 11: 验证 compaction/utils.py - Token 估算

**设计文档参考**：`02-components.md` 第 3 节（Compaction System）

**验证目标**：
- estimate_tokens() - 估算 token 数
- calculate_context_tokens() - 计算上下文 token

**代码检查**：
```python
# 检查 src/coding_agent/compaction/utils.py
```

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/20_token_estimation.py
```

**验收标准**：
- [ ] Token 估算逻辑正确
- [ ] 考虑中英文差异
- [ ] 示例运行通过

---

### Step 12: 验证 compaction/compaction.py - 压缩逻辑

**设计文档参考**：`02-components.md` 第 3.2-3.4 节（压缩流程和摘要格式）

**验证目标**：
- should_compact() - 判断是否需要压缩
- find_cut_point() - 找到切割点
- compact() - 压缩函数
- 摘要格式符合设计（Goal/Progress/Next Steps 等）

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/21_compaction.py
cd packages/coding-agent && uv run python examples/23_compaction_full.py
```

**验收标准**：
- [ ] 压缩触发判断正确
- [ ] 切割点计算正确
- [ ] 摘要格式符合设计
- [ ] 示例运行通过

---

### Step 13: 验证 compaction/branch_summary.py - 分支摘要

**设计文档参考**：`02-components.md` 第 3.5 节（压缩恢复）

**验证目标**：
- generate_branch_summary() - 生成分支摘要
- collect_entries_for_branch_summary() - 收集条目

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/22_branch_summary.py
```

**验收标准**：
- [ ] 分支摘要生成正确
- [ ] 示例运行通过

---

## Phase 4: 核心层（Step 14-18）

### Step 14: 验证 messages.py - 扩展消息类型

**设计文档参考**：`03-data-models.md` 第 2 节（Message 类型）

**验证目标**：
- ExtendedMessage 类型
- BashExecutionMessage
- CustomMessage
- BranchSummaryMessage
- CompactionSummaryMessage

**代码检查**：
```python
# 检查 src/coding_agent/messages.py
```

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/14_messages.py
```

**验收标准**：
- [ ] 所有扩展消息类型定义正确
- [ ] 消息转换函数存在
- [ ] 示例运行通过

---

### Step 15: 验证 system_prompt.py - 系统提示构建

**设计文档参考**：`02-components.md` 第 1.2 节（AgentSession 初始化）

**验证目标**：
- build_system_prompt() - 构建系统提示
- TOOL_DESCRIPTIONS - 工具描述

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/15_system_prompt.py
```

**验收标准**：
- [ ] 系统提示构建正确
- [ ] 工具描述完整
- [ ] 示例运行通过

---

### Step 16: 验证 settings_manager.py + model_registry.py

**设计文档参考**：`02-components.md` 第 1.2 节（SettingsManager + ModelRegistry）

**验证目标**：
- SettingsManager - 用户设置管理
- ModelRegistry - 模型注册表

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/16_settings.py
cd packages/coding-agent && uv run python examples/17_model_registry.py
```

**验收标准**：
- [ ] 设置管理正确
- [ ] 模型注册正确
- [ ] 示例运行通过

---

### Step 17: 验证 bash_executor.py + agent_session.py

**设计文档参考**：`02-components.md` 第 1 节（AgentSession 协调中心）

**验证目标**：
- BashExecutor - Bash 执行器
- AgentSession - 会话协调器（简化版）

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/18_bash_executor.py
cd packages/coding-agent && uv run python examples/19_agent_session.py
```

**验收标准**：
- [ ] Bash 执行结果正确
- [ ] AgentSession 基本功能正常
- [ ] 示例运行通过

---

### Step 18: 验证 sdk.py - SDK 接口

**设计文档参考**：`01-overview.md` 第 2 节（SDK 入口）

**验证目标**：
- create_agent_session() - 创建会话
- create_coding_tools() - 创建工具集
- create_read_only_tools() - 创建只读工具集

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/24_sdk.py
cd packages/coding-agent && uv run python examples/25_imports.py
```

**验收标准**：
- [ ] SDK 函数正确导出
- [ ] 工具创建正确
- [ ] 示例运行通过

---

## Phase 5: 扩展系统（Step 19-22）

### Step 19: 验证 extensions/types.py - 扩展类型

**设计文档参考**：`02-components.md` 第 4 节（Extension System）

**验证目标**：
- Extension 接口
- ExtensionContext
- ToolDefinition

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/26_extension_types.py
```

**验收标准**：
- [ ] Extension 接口定义正确
- [ ] 示例运行通过

---

### Step 20: 验证 extensions/loader.py + extensions/wrapper.py

**设计文档参考**：`02-components.md` 第 4.3-4.4 节（扩展加载和工具包装）

**验证目标**：
- discover_and_load_extensions() - 发现扩展
- wrap_registered_tool() - 包装工具

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/27_extension_loader.py
cd packages/coding-agent && uv run python examples/28_extension_wrapper.py
```

**验收标准**：
- [ ] 扩展发现逻辑正确
- [ ] 工具包装正确
- [ ] 示例运行通过

---

### Step 21: 验证 extensions/runner.py

**设计文档参考**：`02-components.md` 第 4.5 节（事件发射）

**验证目标**：
- ExtensionRunner 类
- 生命周期管理（activate/deactivate）
- 命令注册

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/29_extension_runner.py
```

**验收标准**：
- [ ] ExtensionRunner 功能正确
- [ ] 生命周期管理正确
- [ ] 示例运行通过

---

### Step 22: 验证扩展系统完整集成

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/30_extensions.py
```

**验收标准**：
- [ ] 扩展加载正确
- [ ] 工具注册正确
- [ ] 示例运行通过

---

## Phase 6: 高级功能（Step 23-26）

### Step 23: 验证 skills.py - 技能系统

**设计文档参考**：`01-overview.md` 第 9 节（资源加载 - Skills）

**验证目标**：
- Skill 类型
- load_skills() - 加载技能
- format_skills_for_prompt() - 格式化为提示

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/31_skills.py
```

**验收标准**：
- [ ] 支持 JSON 和 Markdown 格式
- [ ] 标签筛选正确
- [ ] 示例运行通过

---

### Step 24: 验证 prompt_templates.py + slash_commands.py

**设计文档参考**：`02-components.md` 第 6.2 节（命令注册）

**验证目标**：
- PromptTemplate - 提示模板
- SlashCommandRegistry - 斜杠命令注册表

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/32_prompt_templates.py
cd packages/coding-agent && uv run python examples/33_slash_commands.py
```

**验收标准**：
- [ ] 模板变量替换正确
- [ ] 命令解析正确
- [ ] 示例运行通过

---

### Step 25: 验证 resource_loader.py + package_manager.py

**设计文档参考**：`01-overview.md` 第 9 节（资源加载）

**验证目标**：
- ResourceLoader 接口
- DefaultResourceLoader + InMemoryResourceLoader
- PackageManager 接口
- DefaultPackageManager + NoOpPackageManager

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/34_resource_loader.py
cd packages/coding-agent && uv run python examples/35_package_manager.py
```

**验收标准**：
- [ ] 资源加载正确
- [ ] 包管理基本功能正确
- [ ] 示例运行通过

---

### Step 26: 验证 auth_storage.py - 认证存储

**设计文档参考**：`02-components.md` 第 7.2 节（AuthStorage）

**验证目标**：
- ApiKeyCredentials + OAuthCredentials
- FileAuthStorageBackend + InMemoryAuthStorageBackend

**运行示例**：
```bash
cd packages/coding-agent && uv run python examples/36_auth_storage.py
```

**验收标准**：
- [ ] 凭证存储正确
- [ ] 文件持久化正确
- [ ] 示例运行通过

---

## Phase 7: 类型检查与 lint（Step 27）

### Step 27: 运行完整类型检查

**验证方法**：
```bash
cd packages/coding-agent && uv run poe check
```

**验收标准**：
- [ ] ruff lint 无错误（或只有可忽略的警告）
- [ ] pyright typecheck 无错误（或只有已知问题）

---

## Phase 8: 最终验收（Step 28-30）

### Step 28: 运行所有示例

**验证方法**：
```bash
cd packages/coding-agent
for i in {01..36}; do
    uv run python examples/${i}_*.py
done
```

**验收标准**：
- [ ] 所有示例运行通过

---

### Step 29: 运行现有 pytest

**验证方法**：
```bash
cd packages/coding-agent && uv run pytest tests/ -v
```

**验收标准**：
- [ ] 所有 pytest 测试通过

---

### Step 30: 生成验证报告

**输出文件**：`docs/check/verification_report.md`

**内容**：
- 每个 Step 的验证结果
- 发现的问题列表
- 与设计文档的不一致之处
- 后续改进建议

---

## 附录：验证进度跟踪表

| Step | 模块 | 状态 | 问题 |
|------|------|------|------|
| 1 | 目录结构 | ⬜ | |
| 2 | config.py | ⬜ | |
| 3 | session/types.py | ⬜ | |
| 4 | session/manager.py | ⬜ | |
| 5 | session/parser.py + context.py | ⬜ | |
| 6 | tools/__init__.py | ⬜ | |
| 7 | tools/read.py | ⬜ | |
| 8 | tools/write.py + edit.py | ⬜ | |
| 9 | tools/bash.py | ⬜ | |
| 10 | tools/grep/find/ls.py | ⬜ | |
| 11 | compaction/utils.py | ⬜ | |
| 12 | compaction/compaction.py | ⬜ | |
| 13 | compaction/branch_summary.py | ⬜ | |
| 14 | messages.py | ⬜ | |
| 15 | system_prompt.py | ⬜ | |
| 16 | settings_manager.py + model_registry.py | ⬜ | |
| 17 | bash_executor.py + agent_session.py | ⬜ | |
| 18 | sdk.py | ⬜ | |
| 19 | extensions/types.py | ⬜ | |
| 20 | extensions/loader.py + wrapper.py | ⬜ | |
| 21 | extensions/runner.py | ⬜ | |
| 22 | 扩展系统完整集成 | ⬜ | |
| 23 | skills.py | ⬜ | |
| 24 | prompt_templates.py + slash_commands.py | ⬜ | |
| 25 | resource_loader.py + package_manager.py | ⬜ | |
| 26 | auth_storage.py | ⬜ | |
| 27 | 类型检查 | ⬜ | |
| 28 | 所有示例 | ⬜ | |
| 29 | pytest 测试 | ⬜ | |
| 30 | 验证报告 | ⬜ | |

---

## 验证完成后

将结果记录到 `docs/check/verification_report.md`，包括：

1. **通过项**：与设计一致的模块
2. **问题项**：需要修复的问题
3. **差异项**：设计与实现有差异的地方
4. **建议项**：后续改进建议
