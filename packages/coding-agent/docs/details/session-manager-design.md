# SessionManager 设计文档

> py-mono SessionManager 架构与设计说明

---

## 1. 概述

### 1.1 定位

SessionManager 是 **会话持久化层**，负责：
- 将对话历史存储到 JSONL 文件
- 管理会话的树形结构（支持分支）
- 提供上下文重建接口

### 1.2 核心概念

```
会话文件 (JSONL)
├── SessionHeader     # 文件头：会话 ID、工作目录、时间戳
├── MessageEntry     # 消息：user/assistant/tool_result
├── ThinkingLevelChangeEntry  # 思考级别变更
├── ModelChangeEntry # 模型变更
├── CompactionEntry  # 压缩摘要（长会话时）
├── BranchSummaryEntry # 分支摘要（分支导航时）
└── ...
```

**树形结构**：
```
Root (session header)
└── Message 1 (user)
    └── Message 2 (assistant)
        └── Message 3 (user) ← 当前叶子
            └── ... (更多消息)
```

---

## 2. 架构设计

### 2.1 存储格式

**JSONL (JSON Lines)** - 每行一个 JSON 条目：

```jsonl
{"type": "session", "id": "abc123", "version": 3, "timestamp": "...", "cwd": "/project"}
{"type": "message", "id": "msg1", "parent_id": null, "message": {...}}
{"type": "message", "id": "msg2", "parent_id": "msg1", "message": {...}}
{"type": "compaction", "id": "comp1", "parent_id": "msg2", "summary": "..."}
```

**为什么用 JSONL**：
- 追加写入高效
- 损坏可恢复（只丢弃坏行）
- 人类可读，便于调试

### 2.2 核心数据结构

```python
class SessionManager:
    _cwd: str                    # 工作目录
    _session_id: str              # 会话唯一 ID
    _session_file: str | None    # 当前会话文件路径
    _session_dir: str             # 会话目录
    _persist: bool               # 是否持久化

    _file_entries: list[FileEntry]    # 内存中的所有条目
    _by_id: dict[str, SessionEntry]  # ID → 条目 索引
    _labels_by_id: dict[str, str]    # 条目标签
    _leaf_id: str | None         # 当前叶子节点 ID

    _flushed: bool               # 是否已刷新到磁盘
```

### 2.3 追加模式

**首次写入前（无 assistant 消息）**：
- 所有条目写入内存，不刷盘
- 确保 assistant 消息到来后才真正持久化

**首次写入后**：
- 追加模式：只在末尾添加新条目

---

## 3. 核心流程

### 3.1 创建会话

```python
manager = SessionManager.create(cwd="/project")
```

```
1. SessionManager.__init__()
   ├── 创建空内存结构
   └── new_session()
       ├── 生成 UUID 作为 session_id
       ├── 创建 SessionHeader
       └── 设置 _leaf_id = None
```

### 3.2 追加消息

```python
manager.append_message(agent_message)
```

```
1. 创建 SessionMessageEntry
   ├── id = generate_id()  # 8位唯一ID
   ├── parent_id = _leaf_id  # 指向当前叶子
   └── timestamp = now()

2. _append_entry(entry)
   ├── 添加到 _file_entries
   ├── 更新 _by_id 索引
   ├── 更新 _leaf_id = 新条目ID
   └── _persist_entry(entry)

3. _persist_entry(entry)
   ├── 检查是否有 assistant 消息
   │   └── 没有 → return（不刷盘）
   ├── 首次刷盘 → _rewrite_file()（重写整个文件）
   └── 后续追加 → 追加到文件末尾
```

### 3.3 树遍历

```python
branch = manager.get_branch()  # 从根到当前叶子
```

```
1. 从 _leaf_id 开始
2. 沿 parent_id 向回溯
3. 反转得到根→叶子的顺序
```

---

## 4. API 参考

### 4.1 工厂方法

| 方法 | 说明 |
|------|------|
| `create(cwd, session_dir?)` | 创建新会话（持久化） |
| `open(file_path)` | 打开现有会话 |
| `in_memory(cwd?)` | 创建内存会话（测试用） |

### 4.2 追加方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `append_message(message)` | 追加消息 | SessionMessageEntry |
| `append_thinking_level_change(level)` | 思考级别变更 | ThinkingLevelChangeEntry |
| `append_model_change(provider, model_id)` | 模型变更 | ModelChangeEntry |

### 4.3 查询方法

| 方法 | 说明 |
|------|------|
| `get_entries()` | 获取所有条目（不含头部） |
| `get_branch(from_id?)` | 获取从根到指定节点的路径 |
| `get_entry(id)` | 根据 ID 获取单个条目 |
| `get_leaf_id()` | 获取当前叶子 ID |

---

## 5. 与 pi-mono 的差异

详见 [session-manager-compare.md](./session-manager-compare.md)

### 关键缺失

1. **`buildSessionContext()`** - 上下文构建（核心缺失）
2. **`append_compaction()`** - 压缩条目追加
3. **`branch()`** - 分支导航
4. **`get_tree()`** - 树结构获取

### 已知问题

**条目解析不完整**：
```python
# 当前实现只解析 session 类型
def _parse_entry(self, data):
    if entry_type == "session":
        return SessionHeader(**data)
    return None  # message 等类型被忽略！
```

**影响**：重新加载会话时消息丢失

---

## 6. 实施计划

### Phase 1: 核心修复
- [ ] 修复 `_parse_entry` 支持所有条目类型
- [ ] 实现 `build_session_context()`

### Phase 2: 压缩支持
- [ ] 添加 `append_compaction()`
- [ ] 添加 `append_branch_summary()`

### Phase 3: 分支支持
- [ ] 添加 `branch()` / `reset_leaf()`
- [ ] 添加 `get_tree()`

---

## 7. 文件结构

```
session/
├── __init__.py           # 导出
├── manager.py            # SessionManager 类
├── types.py             # 条目类型定义
├── parser.py            # JSONL 解析（独立函数）
└── context.py           # 上下文构建（独立函数）
```

---

## 8. 附录：类型定义

```python
# 条目基类
class SessionEntryBase(BaseModel):
    type: str
    id: str
    parent_id: str | None
    timestamp: str

# 会话头部
class SessionHeader(BaseModel):
    type: Literal["session"]
    version: int = CURRENT_SESSION_VERSION
    id: str
    timestamp: str
    cwd: str
    parent_session: str | None = None

# 消息条目
class SessionMessageEntry(SessionEntryBase):
    type: Literal["message"]
    message: Any  # AgentMessage

# 思考级别变更
class ThinkingLevelChangeEntry(SessionEntryBase):
    type: Literal["thinking_level_change"]
    thinking_level: str

# 模型变更
class ModelChangeEntry(SessionEntryBase):
    type: Literal["model_change"]
    provider: str
    model_id: str
```

---

## 9. 使用示例

```python
from coding_agent.session import SessionManager

# 创建会话
manager = SessionManager.create(cwd="/project")

# 追加消息
msg1 = {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
manager.append_message(msg1)

msg2 = {"role": "assistant", "content": [{"type": "text", "text": "Hi!"}]}
manager.append_message(msg2)

# 查询
entries = manager.get_entries()        # 所有条目
branch = manager.get_branch()         # 从根到叶子
leaf = manager.get_entry(manager.get_leaf_id())  # 当前叶子
```
