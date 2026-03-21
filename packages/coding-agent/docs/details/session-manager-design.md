# SessionManager 设计文档

> py-mono SessionManager 架构与设计说明

---

## 1. 灵魂拷问：SessionManager 是什么？

### 1.1 一句话解释

**SessionManager = 对话历史的"时光机"**

它能：
- **记住**你跟 AI 聊过的所有对话
- **保存**到文件（不会丢）
- **恢复**到任何时间点的状态
- **分支**（像 Git 一样开新分支讨论不同话题）

### 1.2 痛点：没有它会怎样？

```
❌ 没有 SessionManager：
对话 1： 用户: "帮我写个排序算法"
        AI: "好的，这是代码..."
        
关闭程序后...对话丢了！重新打开是空的！

✅ 有 SessionManager：
对话 1： 用户: "帮我写个排序算法"  
        AI: "好的，这是代码..."
        
关闭程序 → 保存到文件 → 重新打开 → 对话还在！
```

---

## 2. 核心概念

### 2.1 对话 = 树形结构

不是线性列表，而是**树**！

为什么用树？因为对话可以**分支**：

```
                        分支点
                           │
        ┌──────────────────┴──────────────────┐
        ▼                                     ▼
    分支 A                                  分支 B
(问 Python 排序)                        (问 JavaScript 排序)
        │                                     │
        ▼                                     ▼
   AI 回答 Python                      AI 回答 JavaScript
```

### 2.2 叶子节点 = 当前讨论位置

```
会话树：
Root
└── Message 1 (user): "排序算法怎么做？"
    └── Message 2 (assistant): "我给你讲两种..."
        └── Message 3 (user): "Python 怎么做？"  ← 当前叶子
            └── Message 4 (assistant): "用 sorted() 函数..."
            
叶子节点 = Message 4 = 当前对话位置
新消息会作为 Message 4 的子节点
```

### 2.3 分支 = 开新话题

```
当前在 Message 3，想开新话题：

1. branch(Message 1)  ← 回到 Message 1（分支点）
2. append_message("JavaScript 怎么做？")

结果树：
Root
└── Message 1: "排序算法怎么做？"
    ├── Message 2: "我给你讲两种..."
    │   └── Message 3: "Python 怎么做？"  ← 旧分支（保留）
    │       └── Message 4: "用 sorted()..."
    └── Message 5: "JavaScript 怎么做？"  ← 新分支！
        └── Message 6: "用 Array.sort()..."
```

---

## 3. 存储格式：JSONL

### 3.1 什么是 JSONL？

每行一个 JSON 对象，像这样：

```jsonl
{"type": "session", "id": "abc123", "cwd": "/project", "timestamp": "2024-01-01T10:00:00"}
{"type": "message", "id": "msg1", "parent_id": null, "message": {"role": "user", "content": "Hello"}}
{"type": "message", "id": "msg2", "parent_id": "msg1", "message": {"role": "assistant", "content": "Hi!"}}
```

### 3.2 为什么用 JSONL？

| 格式 | 追加写入 | 损坏恢复 | 人类可读 |
|------|---------|---------|---------|
| JSON 文件 | ❌ 需重写整个文件 | ❌ 全部损坏 | ✅ |
| 数据库 | ✅ | ✅ | ❌ |
| **JSONL** | ✅ 追加即可 | ✅ 只丢坏行 | ✅ |

### 3.3 文件示例

```
~/.pi/agent/sessions/--home-user-project--/
├── 2024-01-01T10-00-00-000000_abc123.jsonl   ← 会话 1
├── 2024-01-02T14-30-00-000000_def456.jsonl   ← 会话 2
└── 2024-01-03T09-15-00-000000_ghi789.jsonl   ← 会话 3
```

---

## 4. 核心功能详解

### 4.1 创建会话

```python
manager = SessionManager.create(cwd="/home/user/project")
```

```
1. 创建会话文件
   ~/.pi/agent/sessions/--home-user-project--/2024-01-01_abc123.jsonl

2. 写入文件头
   {"type": "session", "id": "abc123", "cwd": "/home/user/project", ...}

3. 内存中创建空树
   Root (session header)
```

### 4.2 追加消息

```python
msg1 = {"role": "user", "content": "Hello"}
manager.append_message(msg1)

msg2 = {"role": "assistant", "content": "Hi there!"}
manager.append_message(msg2)
```

```
追加后文件：
{"type": "session", "id": "abc123", ...}
{"type": "message", "id": "msg1", "parent_id": null, "message": {...}}
{"type": "message", "id": "msg2", "parent_id": "msg1", "message": {...}}

树结构：
Root
└── msg1 (user: "Hello")
    └── msg2 (assistant: "Hi there!")  ← 叶子
```

### 4.3 分支管理

```python
# 1. 创建分支（回到之前的节点）
manager.branch(msg1.id)

# 2. 在新分支上追加消息
msg3 = {"role": "user", "content": "Different topic"}
manager.append_message(msg3)
```

```
分支后：
Root
└── msg1 (user: "Hello")
    ├── msg2 (assistant: "Hi there!")  ← 旧分支保留
    └── msg3 (user: "Different topic")  ← 新分支，msg1 的子节点
```

### 4.4 压缩（长对话优化）

当对话太长时，AI 会自动压缩：

```python
# 原始对话可能有 100 条消息
# 压缩后变成：
# - 1 条摘要消息："用户问了 Python 基础、列表操作、文件读写..."
# - 最近 10 条消息保留
```

```
压缩前：msg1, msg2, msg3, msg4, msg5, ... msg100
压缩后：[压缩摘要] msg95, msg96, msg97, msg98, msg99, msg100
```

### 4.5 构建上下文（核心！）

```python
# 获取发送给 AI 的消息列表
context = manager.build_session_context()

# 返回：
# {
#     "messages": [msg1, msg2, msg3, ...],  # AI 需要看的消息
#     "thinking_level": "high",              # 思考级别
#     "model": {"provider": "kimi", ...}     # 使用的模型
# }
```

---

## 5. 实际问题场景

### 场景 1：用户关闭程序后重新打开

```
1. 保存：对话自动保存到 JSONL 文件
2. 重新打开：SessionManager.open(session_file)
3. 恢复：build_session_context() 获取消息
4. 继续：用户可以继续问"上文提到的代码怎么优化？"
```

### 场景 2：用户想尝试不同方向

```
1. 当前：讨论 Python 排序
2. 用户：想试试 JavaScript 排序
3. 操作：branch() 回到分支点，追加新消息
4. 结果：两个方向的讨论都保留，可以随时切换
```

### 场景 3：长对话需要压缩

```
1. 对话进行到 100 轮
2. AI 检测到上下文快满了
3. 自动压缩：生成摘要 + 保留最近消息
4. 对话继续，但 Token 消耗减少
```

---

## 6. API 参考

### 6.1 创建和打开会话

| 方法 | 说明 | 示例 |
|------|------|------|
| `create(cwd, session_dir?)` | 创建新会话 | `SessionManager.create("/project")` |
| `open(file_path)` | 打开现有会话 | `SessionManager.open("/path/to/session.jsonl")` |
| `in_memory(cwd?)` | 创建内存会话（测试用） | `SessionManager.in_memory()` |

### 6.2 追加条目

| 方法 | 说明 |
|------|------|
| `append_message(message)` | 追加用户/AI 消息 |
| `append_thinking_level_change(level)` | 变更思考级别 |
| `append_model_change(provider, model_id)` | 变更 AI 模型 |
| `append_compaction(summary, first_kept_id, tokens)` | 追加压缩记录 |
| `append_branch_summary(from_id, summary)` | 追加分支摘要 |
| `append_custom_entry(type, data)` | 追加自定义数据 |
| `append_session_info(name)` | 追加会话名称 |
| `append_label_change(target_id, label)` | 追加标签 |

### 6.3 查询

| 方法 | 说明 |
|------|------|
| `get_entries()` | 获取所有条目（不含头部） |
| `get_branch(from_id?)` | 获取从根到指定节点的路径 |
| `get_entry(id)` | 获取指定 ID 的条目 |
| `get_leaf_id()` | 获取当前叶子 ID |
| `get_leaf_entry()` | 获取当前叶子条目 |
| `get_children(parent_id)` | 获取指定节点的直接子节点 |
| `get_tree()` | 获取完整树结构（用于 UI） |
| `build_session_context()` | 构建发送给 AI 的上下文 |
| `get_session_name()` | 获取会话名称 |

### 6.4 分支管理

| 方法 | 说明 |
|------|------|
| `branch(branch_from_id)` | 切换到指定节点的分支 |
| `reset_leaf()` | 重置叶子到根之前 |
| `branch_with_summary(branch_from_id, summary)` | 分支并添加摘要 |

### 6.5 会话管理

| 方法 | 说明 |
|------|------|
| `fork_from(source_path, target_cwd)` | 从其他会话分叉 |
| `continue_recent(cwd, session_dir?)` | 继续最近会话 |
| `list(cwd, session_dir?, on_progress?)` | 列出指定目录的会话 |
| `list_all(on_progress?)` | 列出所有会话 |

---

## 7. 数据结构

### 7.1 内存结构

```python
class SessionManager:
    _file_entries: list[FileEntry]    # 所有条目（按添加顺序）
    _by_id: dict[str, FileEntry]      # ID → 条目 索引
    _leaf_id: str | None              # 当前叶子节点 ID
    _labels_by_id: dict[str, str]     # ID → 标签
```

### 7.2 条目类型

| 类型 | 说明 |
|------|------|
| `session` | 文件头（第一个条目） |
| `message` | 对话消息 |
| `thinking_level_change` | 思考级别变更 |
| `model_change` | 模型变更 |
| `compaction` | 压缩摘要 |
| `branch_summary` | 分支摘要 |
| `custom` | 扩展自定义（不参与上下文） |
| `custom_message` | 扩展自定义（参与上下文） |
| `session_info` | 会话信息（如名称） |
| `label` | 条目标签 |

---

## 8. 与 Agent 集成

### 8.1 Agent 状态恢复（switchSession）

当用户选择"继续上次会话"时：

```python
async def switch_session(self, session_path: str) -> None:
    # 1. 断开当前 agent
    await self.abort()
    
    # 2. 加载会话文件
    self.session_manager.set_session_file(session_path)
    
    # 3. 重建上下文
    context = self.session_manager.build_session_context()
    
    # 4. 恢复 Agent 状态（关键！）
    self.agent.replace_messages(context.messages)
    
    # 5. 恢复模型和思考级别
    if context.model:
        self.agent.set_model(context.model)
    if context.thinking_level:
        self.agent.set_thinking_level(context.thinking_level)
```

### 8.2 事件钩子

```
用户输入 → Agent 处理 → 事件触发 → SessionManager 保存

message_end 事件 → 自动保存消息
agent_end 事件 → 检查是否需要压缩
```

---

## 9. 架构设计

### 9.1 追加模式

**首次写入前（无 assistant 消息）**：
- 所有条目写入内存，不刷盘
- 原因：用户可能只问一句就走，没必要创建文件

**首次写入后**：
- 追加模式：只在末尾添加新条目
- 高效！

### 9.2 延迟刷盘策略

```
用户: "Hello"
    → 写入内存，不刷盘

用户: (等待 AI 回复中...)
    → AI 回复到达

用户: "Thanks"
    → 现在才真正刷盘！
```

---

## 10. 文件结构

```
session/
├── __init__.py           # 导出
├── manager.py            # SessionManager 类
├── types.py             # 条目类型定义
├── parser.py            # JSONL 解析
└── context.py           # 上下文构建
```

---

## 11. 使用示例

### 11.1 基本对话

```python
from coding_agent.session import SessionManager

# 创建会话
manager = SessionManager.create(cwd="/project")

# 对话
manager.append_message({"role": "user", "content": "Hello"})
manager.append_message({"role": "assistant", "content": "Hi!"})

# 查询
branch = manager.get_branch()
for entry in branch:
    if entry.type == "message":
        print(entry.message)
```

### 11.2 继续上次会话

```python
import asyncio

async def main():
    # 列出所有会话
    sessions = await SessionManager.list_all()
    for s in sessions:
        print(f"{s.name} - {s.modified}")
    
    # 继续某个会话
    # 1. 加载会话
    manager = SessionManager.open(sessions[0].path)
    
    # 2. 构建上下文
    context = manager.build_session_context()
    
    # 3. 恢复 Agent 状态
    agent.replace_messages(context.messages)

asyncio.run(main())
```

### 11.3 分支讨论

```python
# 当前在 Message 3
manager.branch(Message_1_id)  # 回到 Message 1

# 新开分支
manager.append_message({"role": "user", "content": "另一个话题"})

# 稍后可以切回原分支
manager.branch(Message_3_id)
```

---

## 12. 测试验证

```bash
cd packages/coding-agent
uv run pytest tests/test_session_manager.py -v
```

**当前测试覆盖**：

| 测试 | 说明 |
|------|------|
| test_in_memory_session | 内存会话创建 |
| test_persistent_session | 持久化会话创建 |
| test_open_session | 打开现有会话 |
| test_append_message | 追加消息 |
| test_branch_and_reset_leaf | 分支导航 |
| test_build_session_context | 构建上下文 |
| test_fork_from | 分叉会话 |
| test_list_sessions | 列出会话 |
| ... | 共 26 个测试 |

---

## 13. 实施计划

### ✅ Phase 1: 核心修复
- [x] 修复 `_parse_entry` 支持所有条目类型
- [x] 实现 `build_session_context()`

### ✅ Phase 2: 压缩支持
- [x] 添加 `append_compaction()`
- [x] 添加 `append_branch_summary()`

### ✅ Phase 3: 分支支持
- [x] 添加 `branch()` / `reset_leaf()`
- [x] 添加 `get_tree()` / `get_children()`

### ✅ Phase 4: 会话管理
- [x] 添加 `fork_from()` / `continue_recent()`
- [x] 添加 `list()` / `list_all()`

### ✅ Phase 5: Agent 集成
- [x] 实现 `switchSession()` - Agent 状态恢复
- [ ] 事件钩子集成（待实现）

---

## 14. 总结

SessionManager 是 AI 编程助手的**记忆系统**：

| 功能 | 作用 |
|------|------|
| 持久化 | 对话不丢失 |
| 树结构 | 支持分支讨论 |
| 压缩 | 长对话不爆 Token |
| 上下文构建 | 恢复对话状态 |
| 分支管理 | 尝试不同方向 |

**核心目标**：让 AI 记住你的所有讨论，随时可以继续。
