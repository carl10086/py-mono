# SessionManager 设计文档

> py-mono SessionManager 架构与设计说明

---

## 1. 核心问题：SessionManager 解决什么问题？

### 1.1 一句话解释

**SessionManager = 对话历史的"时光机"**

解决的问题：
- 对话数据持久化（关闭不丢失）
- 支持分支探索（同时讨论多个方向）
- 长对话压缩（控制 Token 消耗）

### 1.2 为什么需要它？

```
没有 SessionManager：
用户: "帮我写排序算法"
AI: "好的，这是代码..."
关闭程序 → 对话丢了！重新打开是空的！

有 SessionManager：
用户: "帮我写排序算法"
AI: "好的，这是代码..."
关闭程序 → 保存到文件 → 重新打开 → 对话还在！
```

---

## 2. 核心概念：Header 和 Entry

SessionManager 只有两个核心数据结构：

### 2.1 Header（文件头）

每个会话文件的第一行，包含元数据：

```json
{
  "type": "session",
  "version": 3,
  "id": "abc123",
  "timestamp": "2024-01-01T10:00:00",
  "cwd": "/home/user/project",
  "parent_session": null
}
```

| 字段 | 说明 |
|------|------|
| `type` | 固定为 "session" |
| `version` | 文件格式版本（当前 v3） |
| `id` | 会话唯一标识符（UUID） |
| `timestamp` | 创建时间 |
| `cwd` | 工作目录路径 |
| `parent_session` | 父会话路径（fork 时设置） |

### 2.2 Entry（条目）

Header 之后的所有行都是 Entry，每行一个 JSON：

```jsonl
{"type": "session", "id": "abc123", ...}           ← Header（第1行）
{"type": "message", "id": "msg1", "parent_id": null, "message": {...}}
{"type": "message", "id": "msg2", "parent_id": "msg1", "message": {...}}
{"type": "compaction", "id": "cp1", "parent_id": "msg2", "summary": "...", "first_kept_entry_id": "msg5"}
{"type": "message", "id": "msg6", "parent_id": "cp1", "message": {...}}
```

### 2.3 Entry 的树形结构

每个 Entry 都有 `id` 和 `parent_id`，形成树：

```
Header (session, id=null)
└── Message 1 (id=1, parent_id=null)
    └── Message 2 (id=2, parent_id=1)
        └── Message 3 (id=3, parent_id=2)
            └── ...
```

**为什么用树？** 因为对话可以分支：

```
Header
└── Message 1 (root)
    ├── Message 2a (分支 A) ← "Python 怎么做？"
    │   └── Message 3a
    └── Message 2b (分支 B) ← "JavaScript 怎么做？"
        └── Message 3b
```

### 2.4 Entry 的 9 种类型

| 类型 | 作用 | 参与上下文？ |
|------|------|------------|
| `message` | 对话消息 | ✅ |
| `thinking_level_change` | 思考级别变更 | ❌ |
| `model_change` | 模型切换 | ❌ |
| `compaction` | 压缩记录 | ✅（生成摘要消息） |
| `branch_summary` | 分支摘要 | ✅（生成摘要消息） |
| `custom` | 扩展数据 | ❌ |
| `custom_message` | 扩展消息 | ✅ |
| `session_info` | 会话名称 | ❌ |
| `label` | 条目标签 | ❌ |

---

## 3. 核心问题解答

### Q1: 如何追踪当前在哪个节点？（leaf_id）

**A: 内存中的 `_leaf_id` 指针**

```python
class SessionManager:
    _leaf_id: str | None  # 当前叶子节点 ID（内存，非持久化）
```

**工作原理：**
1. 每次追加新 Entry，新 Entry 的 `parent_id` = `_leaf_id`
2. 然后更新 `_leaf_id` = 新 Entry 的 `id`
3. 这样就追踪到树的末端

**重要特性：`leaf_id` 不持久化**

重新打开会话时：
- 没有 `leaf_id` → 使用最后一个 Entry 作为叶子
- 这是合理的设计：因为文件最后一条记录就是"当前状态"

```
会话文件：
{"type": "session", ...}
{"type": "message", "id": "msg1", ...}
{"type": "message", "id": "msg2", ...}  ← 最后一条 = 当前叶子

重新打开：
leaf_id = msg2（从文件末尾推断）
```

### Q2: 压缩（Compaction）是什么？如何恢复？

**A: 压缩是用摘要替换旧消息，控制 Token 数量**

```
压缩前（100条消息）：
msg1, msg2, msg3, msg4, msg5, ..., msg100

压缩后：
compaction (summary="用户问了 Python 基础、列表操作、文件读写...",
           first_kept_entry_id="msg95")
msg95, msg96, msg97, msg98, msg99, msg100
```

**CompactionEntry 结构：**

```python
class CompactionEntry(BaseModel):
    type: Literal["compaction"] = "compaction"
    id: str                           # 压缩条目 ID
    parent_id: str | None             # 父节点
    summary: str                      # 压缩摘要
    first_kept_entry_id: str          # 从这个 ID 开始保留
    tokens_before: int                # 压缩前的 token 数
```

**恢复上下文时（build_session_context）：**

```python
# 1. 找到 compaction 条目
# 2. 在路径中找到 first_kept_entry_id
# 3. 只添加：
#    - 压缩摘要消息（CompactionSummaryMessage）
#    - first_kept_entry_id 之后的条目
```

**没有 Snapshot！每次都从头重建：**

```python
def build_session_context():
    # 每次调用都执行完整遍历
    path = []
    current = leaf_entry
    while current:
        path.insert(0, current)
        current = parent_id_lookup(current)  # 从头查树
    # 然后根据 compaction 过滤
```

这意味着：
- ❌ 没有"快照"加速恢复
- ✅ 每次都得到正确的结果（简单可靠）
- ⚠️ 长对话恢复略慢，但可接受（毕竟只是内存遍历）

### Q3: 为什么要用 JSONL 格式？

**A: 追加友好 + 损坏局部化**

| 格式 | 追加写入 | 损坏恢复 | 人类可读 |
|------|---------|---------|---------|
| JSON 文件 | ❌ 需重写 | ❌ 全部损坏 | ✅ |
| 数据库 | ✅ | ✅ | ❌ |
| **JSONL** | ✅ 追加即可 | ✅ 只丢坏行 | ✅ |

```
~/.pi/agent/sessions/--home-user-project--/
├── 2024-01-01T10-00-00-000000_abc123.jsonl
├── 2024-01-02T14-30-00-000000_def456.jsonl
└── 2024-01-03T09-15-00-000000_ghi789.jsonl
```

---

## 4. 实际使用场景

### 场景 1：基本对话

```python
from coding_agent.session import SessionManager

# 创建会话
manager = SessionManager.create(cwd="/project")

# 对话
manager.append_message({"role": "user", "content": "Hello"})
manager.append_message({"role": "assistant", "content": "Hi!"})

# 构建上下文（发送给 AI）
context = manager.build_session_context()
# → [{"role": "user", ...}, {"role": "assistant", ...}]
```

**为什么需要 build_session_context？**
- 从内存/文件树结构构建 AI 需要看到的信息
- 处理压缩、过滤非上下文条目

### 场景 2：分支讨论

```python
# 当前在 msg3，想开新话题
manager.branch(msg1.id)  # 回到 msg1

# 新开分支
manager.append_message({"role": "user", "content": "换个话题"})

# 原分支保留，可以切回
manager.branch(msg3.id)
```

**为什么需要分支？**
- 用户问了一个问题，AI 给了一个方案
- 用户想"如果用另一种方式会怎样？"
- 分支让你同时探索多个方向，不丢失任何一个

### 场景 3：继续上次会话

```python
import asyncio

async def main():
    # 列出所有会话
    sessions = await SessionManager.list_all()
    
    # 加载最近的
    manager = SessionManager.open(sessions[0].path)
    
    # 构建上下文
    context = manager.build_session_context()
    
    # 恢复 Agent 状态
    agent.replace_messages(context.messages)
```

### 场景 4：压缩长对话

```python
# 当对话太长时（比如 100 轮）
# AI 调用 append_compaction()

manager.append_compaction(
    summary="用户问了 Python 基础、列表操作、文件读写、异常处理...",
    first_kept_entry_id=msg95_id,
    tokens_before=50000
)

# 之后的上下文自动只包含：
# 1. 压缩摘要
# 2. msg95 之后的消息
```

**为什么需要压缩？**
- LLM 有上下文长度限制（4K/16K/200K tokens）
- 超过限制会导致错误或额外费用
- 压缩用廉价模型生成摘要，保留最近消息

### 场景 5：Fork 会话

```python
# 从其他项目复制会话
manager = SessionManager.fork_from(
    source_path="/old/project/.pi/sessions/xxx.jsonl",
    target_cwd="/new/project"
)

# 结果：
# - 新会话在 /new/project/.pi/sessions/
# - 包含源会话的完整历史
# - Header.parent_session 指向源会话
```

---

## 5. API 参考

### 5.1 创建和打开

| 方法 | 说明 |
|------|------|
| `create(cwd, session_dir?)` | 创建新会话 |
| `open(file_path)` | 打开现有会话 |
| `in_memory(cwd?)` | 创建内存会话（测试用） |
| `continue_recent(cwd)` | 继续最近会话或创建新会话 |
| `fork_from(source, target_cwd)` | 从其他会话分叉 |

### 5.2 追加条目

| 方法 | 说明 |
|------|------|
| `append_message(message)` | 追加对话消息 |
| `append_thinking_level_change(level)` | 变更思考级别 |
| `append_model_change(provider, model_id)` | 变更模型 |
| `append_compaction(summary, first_kept_id, tokens)` | 追加压缩记录 |
| `append_branch_summary(from_id, summary)` | 追加分支摘要 |
| `append_custom_entry(type, data)` | 追加自定义数据 |
| `append_custom_message(type, content, display)` | 追加自定义消息 |
| `append_session_info(name)` | 追加会话名称 |
| `append_label_change(target_id, label)` | 追加标签 |

### 5.3 查询

| 方法 | 说明 |
|------|------|
| `get_entries()` | 获取所有条目（不含 Header） |
| `get_entry(id)` | 获取指定 ID 的条目 |
| `get_leaf_entry()` | 获取当前叶子条目 |
| `get_branch(from_id?)` | 获取从根到指定节点的路径 |
| `get_children(parent_id)` | 获取子节点 |
| `get_tree()` | 获取完整树结构 |
| `build_session_context(leaf_id?)` | 构建 LLM 上下文 |
| `get_session_name()` | 获取会话名称 |

### 5.4 分支管理

| 方法 | 说明 |
|------|------|
| `branch(branch_from_id)` | 切换到指定节点的分支 |
| `reset_leaf()` | 重置叶子到根之前 |
| `branch_with_summary(branch_from_id, summary)` | 分支并添加摘要 |

---

## 6. 数据结构

### 6.1 内存结构

```python
class SessionManager:
    _file_entries: list[FileEntry]    # 所有条目（按文件顺序）
    _by_id: dict[str, SessionEntry]    # ID → 条目 索引
    _leaf_id: str | None              # 当前叶子节点 ID（内存）
    _labels_by_id: dict[str, str]     # ID → 标签
```

### 6.2 文件格式

```
# JSONL 格式，每行一个 JSON 对象
{"type": "session", "id": "...", "cwd": "...", ...}  ← Header
{"type": "message", "id": "...", "parent_id": null, ...}
{"type": "message", "id": "...", "parent_id": "...", ...}
{"type": "compaction", "id": "...", "parent_id": "...", ...}
```

---

## 7. FAQ

### Q: 为什么 leaf_id 不存文件？

A: 因为不需要。文件最后一条记录就是当前状态，无需额外存储。

### Q: 压缩会丢失消息吗？

A: 不会真正丢失。压缩时：
1. 生成摘要描述旧消息
2. `first_kept_entry_id` 标记保留点
3. 旧消息仍在文件中，只是上下文不包含

### Q: 没有 Snapshot，恢复会不会很慢？

A: 不会。树遍历是内存操作，1000 条记录毫秒级完成。

### Q: 分支之间如何切换？

A: 用 `branch(leaf_id)` 改变 `_leaf_id` 指针。文件内容不变，只改内存状态。

### Q: 关闭程序时数据会丢吗？

A: 不会。追加消息时先写内存，`flush()` 时刷盘。

---

## 8. 与 pi-mono 对比

| 特性 | pi-mono | py-mono |
|------|---------|---------|
| Entry 类型 | 9 种 | 9 种 |
| 树结构 | ✅ | ✅ |
| 压缩 | ✅ | ✅ |
| 分支 | ✅ | ✅ |
| 叶子追踪 | `_leafId` | `_leaf_id` |
| Snapshot | 无 | 无 |
| Header leaf_id | 不存 | 不存 |

---

## 9. 测试验证

```bash
cd packages/coding-agent
uv run pytest tests/test_session_manager.py -v
```
