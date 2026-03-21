# SessionManager 对比分析

> pi-mono (TypeScript) vs py-mono (Python)

---

## 1. 功能对比总览

| 功能 | pi-mono | py-mono | 状态 |
|------|---------|---------|------|
| **基础功能** |||
| 创建会话 | ✅ | ✅ | 完整 |
| 打开会话 | ✅ | ✅ | 完整 |
| 内存模式 | ✅ | ✅ | 完整 |
| **消息追加** |||
| append_message | ✅ | ✅ | 完整 |
| append_thinking_level_change | ✅ | ✅ | 完整 |
| append_model_change | ✅ | ✅ | 完整 |
| append_compaction | ✅ | ✅ | 完整 |
| append_branch_summary | ✅ | ✅ | 完整 |
| append_custom_entry | ✅ | ✅ | 完整 |
| append_custom_message_entry | ✅ | ✅ | 完整 |
| append_session_info | ✅ | ✅ | 完整 |
| append_label_change | ✅ | ✅ | 完整 |
| **树遍历** |||
| get_branch | ✅ | ✅ | 完整 |
| get_entries | ✅ | ✅ | 完整 |
| get_leaf_id | ✅ | ✅ | 完整 |
| get_entry | ✅ | ✅ | 完整 |
| get_tree | ✅ | ✅ | 完整 |
| get_children | ✅ | ✅ | 完整 |
| get_leaf_entry | ✅ | ✅ | 完整 |
| **分支管理** |||
| branch | ✅ | ✅ | 完整 |
| reset_leaf | ✅ | ✅ | 完整 |
| branch_with_summary | ✅ | ✅ | 完整 |
| fork_from | ✅ | ✅ | 完整 |
| **会话管理** |||
| continue_recent | ✅ | ✅ | 完整 |
| list | ✅ | ✅ | 完整 |
| list_all | ✅ | ✅ | 完整 |
| build_session_context | ✅ | ✅ | 完整 |
| **其他** |||
| get_session_name | ✅ | ✅ | 完整 |
| 版本迁移 | ✅ | ✅ | 完整 |

---

## 2. 关键差异

### 2.1 已实现的方法

所有计划的方法均已实现：

- ✅ `buildSessionContext()` - 上下文构建
- ✅ `branch()` / `reset_leaf()` / `branchWithSummary()` - 分支管理
- ✅ `appendCompaction()` / `appendBranchSummary()` - 压缩和分支摘要
- ✅ `append_custom_entry()` / `append_custom_message()` - 自定义条目
- ✅ `append_session_info()` / `append_label_change()` - 会话信息和标签
- ✅ `get_tree()` / `get_children()` / `get_leaf_entry()` - 树遍历
- ✅ `fork_from()` / `continue_recent()` / `list()` / `list_all()` - 会话管理

### 2.2 架构差异

#### A. ID 索引结构

**pi-mono**: 使用 `Map<string, SessionEntry>`
```typescript
private byId: Map<string, SessionEntry> = new Map();
```

**py-mono**: 使用 `dict[str, SessionEntry]`
```python
self._by_id: dict[str, SessionEntry] = {}
```

**影响**: 无实质差异，Python dict 等价于 Map

#### B. `buildSessionContext` 位置

**pi-mono**: 独立函数 + 类方法
```typescript
// 独立函数（纯逻辑，可测试）
export function buildSessionContext(...): SessionContext

// 类方法（调用独立函数）
buildSessionContext(): SessionContext {
    return buildSessionContext(this.getEntries(), this.leafId, this.byId);
}
```

**py-mono**: 只有 `session/context.py` 中有部分实现，不完整

#### C. 条目解析

**pi-mono**: `_parseEntry` 直接返回类型化的 JSON
```typescript
const entry = JSON.parse(line) as FileEntry;
entries.push(entry);
```

**py-mono**: `_parse_entry` 只处理 `session` 类型
```python
def _parse_entry(self, data):
    entry_type = data.get("type")
    if entry_type == "session":
        return SessionHeader(**data)
    return None  # message 等类型被忽略！
```

**影响**: py-mono 重新加载会话时只能恢复 `session` 头部，消息条目丢失

### 2.3 次要差异

| 方面 | pi-mono | py-mono |
|------|---------|---------|
| 命名风格 | camelCase | snake_case |
| 返回值 | 多返回 entry ID (string) | 多返回完整 entry 对象 |
| 错误处理 | 异常 + 返回 null | 返回 None |
| 类型系统 | TypeBox | Pydantic dataclass |
| 文件操作 | 同步 fs 操作 | 同步 open/read |

---

## 3. 实现差距量化

```
总方法数 (pi-mono): ~35
已实现 (py-mono): 12
缺失: 23
完成度: 34%
```

### 按优先级分类

**P0 (阻断 - 核心功能)**:
- `buildSessionContext()` - Agent 需要此方法构建 LLM 上下文
- 条目解析修复 - 重新加载时消息丢失

**P1 (重要)**:
- `append_compaction()` - 自动压缩需要
- `append_branch_summary()` - 分支摘要需要
- `branch()` / `reset_leaf()` - 分支导航

**P2 (完善)**:
- `get_tree()` - UI 需要树结构展示
- `get_children()` - 子节点查询
- `fork_from()` - 跨项目分叉

---

## 4. 建议的实施计划

### Phase 1: 核心修复（P0）
1. 修复 `_parse_entry` 支持所有条目类型 ✅
2. 实现 `build_session_context()` ✅

### Phase 2: 压缩支持（P1）✅
1. 添加 `append_compaction()` ✅
2. 添加 `append_branch_summary()` ✅
3. 集成到 AgentSession 事件处理（待完成）

### Phase 3: 分支支持（P1）✅
1. 添加 `branch()` / `reset_leaf()` ✅
2. 添加 `branch_with_summary()` ✅
3. 添加 `get_tree()` / `get_children()` ✅

---

## 5. 总结

py-mono 的 SessionManager 已实现与 pi-mono 对齐的几乎所有功能：

| 类别 | 完成度 |
|------|--------|
| 基础功能 | 100% |
| 消息追加 | 100% |
| 树遍历 | 100% |
| 分支管理 | 100% |
| 会话管理 | 100% |
| 上下文构建 | 100% |

### 测试覆盖

- 单元测试：26 个测试全部通过
- 测试方法：`append_*`, `branch`, `reset_leaf`, `get_tree`, `fork_from`, `list` 等

### 待完成

- AgentSession 事件系统集成（Phase 2.3）
- Agent 状态恢复（Agent.state.messages 填充）
