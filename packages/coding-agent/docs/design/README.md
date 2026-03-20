# Coding Agent 架构文档

> Pi-Mono Coding Agent 的高层设计文档集

---

## 📚 文档清单

| 文档 | 内容 | 优先级 |
|------|------|--------|
| [01-overview.md](01-overview.md) | **架构总览** - 分层架构、数据流、核心概念 | ⭐⭐⭐ 必读 |
| [02-components.md](02-components.md) | **组件详解** - AgentSession、SessionManager、Compaction、Extension | ⭐⭐⭐ 必读 |
| [03-data-models.md](03-data-models.md) | **数据模型** - 所有核心类型、状态流转 | ⭐⭐ 重要 |
| [04-implementation-roadmap.md](04-implementation-roadmap.md) | **实现路线图** - 分阶段实施计划 | ⭐⭐ 重要 |
| [05-integration-guide.md](05-integration-guide.md) | **集成指南** - 组件组装、数据流、最佳实践 | ⭐⭐⭐ 必读 |

---

## 🏗️ 架构速览

```
┌─────────────────────────────────────────────────────────────┐
│                        应用层                                │
│   ┌──────────┬──────────────┬──────────────────────────┐   │
│   │   CLI    │  TUI (Rich)  │      RPC Service         │   │
│   └──────────┴──────────────┴──────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                       会话层                                 │
│                    AgentSession                              │
│         (协调中心：状态管理、事件转发、生命周期)              │
├─────────────────────────────────────────────────────────────┤
│                       核心层                                 │
│              Agent (来自 packages/agent)                     │
│              (LLM 双循环：流式处理、工具编排)                 │
├─────────────────────────────────────────────────────────────┤
│                       扩展层                                 │
│   ┌──────────────┬──────────────┬──────────────────────┐   │
│   │   Tools      │  Extensions  │   Model Registry     │   │
│   └──────────────┴──────────────┴──────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                     基础设施层                               │
│   ┌──────────────┬──────────────┬──────────────────────┐   │
│   │ SessionManager│ Compaction  │   AuthStorage        │   │
│   │  (JSONL)     │  System      │   ResourceLoader     │   │
│   └──────────────┴──────────────┴──────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 核心设计思想

### 1. 分层架构

- **应用层**：CLI、TUI、RPC 等不同入口
- **会话层**：AgentSession 统一协调
- **核心层**：复用 packages/agent 的双循环引擎
- **扩展层**：插件化架构支持无限扩展
- **基础设施**：可靠的存储和配置管理

### 2. 事件驱动

所有状态变化通过事件传播，实现松耦合：

```
User Input ──▶ AgentSession ──▶ Agent Loop ──▶ Events
                                  │
                                  ▼
                           ┌─────────────┐
                           │ UI Updates  │
                           │ Extensions  │
                           │ Logging     │
                           └─────────────┘
```

### 3. 不可变历史

- **JSONL 追加写入**：历史永不修改
- **树形结构**：天然支持分支和时间旅行
- **压缩摘要**：解决长会话的上下文限制

### 4. 可扩展性

Extension System 提供丰富的扩展点：
- ✅ 自定义工具
- ✅ 自定义命令
- ✅ 自定义 Provider
- ✅ 事件钩子
- ✅ UI 组件

---

## 🚀 快速开始

### 推荐阅读顺序

**如果你是架构师**：
1. [01-overview.md](01-overview.md) - 理解整体架构
2. [02-components.md](02-components.md) - 理解核心组件
3. [05-integration-guide.md](05-integration-guide.md) - 理解集成方式

**如果你是开发者**：
1. [01-overview.md](01-overview.md) - 理解架构
2. [03-data-models.md](03-data-models.md) - 理解数据模型
3. [04-implementation-roadmap.md](04-implementation-roadmap.md) - 开始实现

**如果你要集成**：
1. [05-integration-guide.md](05-integration-guide.md) - 集成指南
2. [02-components.md](02-components.md) - 组件接口

---

## 📊 关键决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 存储格式 | JSONL | 追加写入、人类可读、树形结构 |
| 架构模式 | 分层 + 事件驱动 | 松耦合、可测试、可扩展 |
| 扩展机制 | Hook + Registry | 简单、灵活、隔离性好 |
| 核心循环 | 复用 packages/agent | 避免重复造轮子 |
| 压缩策略 | LLM 生成摘要 | 保留语义、智能压缩 |

---

## 🔗 相关资源

- **参考实现**: `refer/pi-mono/packages/coding-agent/`
- **核心循环**: `packages/agent/docs/details/`
- **项目根目录**: `/Users/carlyu/soft/projects/py-mono/`

---

## 📝 文档维护

- **创建日期**: 2024-03-20
- **作者**: AI Assistant
- **基于**: Pi-Mono Coding Agent (TypeScript) 源码分析
- **目标**: Py-Mono Coding Agent (Python) 实现参考

---

**有问题？** 参考具体文档或查看源码实现。
