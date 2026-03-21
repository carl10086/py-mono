# SessionManager 数据结构详解

> 深入理解 Header、Entry 类型、回溯设计模式

---

## 1. 设计模式：回溯（Backtracking）

### 1.1 什么是回溯？

```
线性结构（链表）：
Head → A → B → C → D → E
                ↑
               当前叶子（只能向前或向后）

树结构（回溯）：
        Root (Header)
         │
    ┌────┴────┐
    │         │
    A         F
    │
┌───┴───┐
│       │
B       C
│
└───┐
    │
    D  ← 当前叶子

特点：
- 可以"回溯"到任意祖先节点
- 从任意节点"开新分支"
- 所有历史都不会丢失
```

### 1.2 为什么要回溯？

```
场景：用户聊着聊着发现之前理解错了

1. 你：帮我写个求和函数 sum([1,2,3]) = 6
2. AI：def sum(arr): return sum(arr)  # 递归实现

3. 你：等等，我要的是迭代版本

4. 你：分支回溯到 Message 1，开新分支
       branch(Message_1)
       
5. 你：我要迭代版本
6. AI：def sum(arr): 
         total = 0
         for x in arr: total += x
         return total

结果：
- 原分支保留（递归版本）
- 新分支继续（迭代版本）
- 用户想要哪个就要哪个
```

---

## 2. Header（会话头）

### 2.1 Header 是什么？

Header 是**会话的元信息**，放在 JSONL 文件的第一行：

```json
{
  "type": "session",
  "version": 3,
  "id": "abc123def456",
  "timestamp": "2024-01-01T10:00:00.000000",
  "cwd": "/home/user/myproject",
  "parent_session": null
}
```

### 2.2 Header 属性详解

| 属性 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `type` | `"session"` | 固定值，标识这是会话头 | `"session"` |
| `version` | `int` | 格式版本号，用于升级迁移 | `3` |
| `id` | `string` | 会话唯一 ID（UUID） | `"abc123def456"` |
| `timestamp` | `ISO8601` | 创建时间 | `"2024-01-01T10:00:00.000000"` |
| `cwd` | `string` | 工作目录（用于识别项目） | `"/home/user/myproject"` |
| `parent_session` | `string \| null` | 父会话路径（fork 时设置） | `null` 或 `"/path/to/parent.jsonl"` |

### 2.3 为什么要这些属性？

```python
# version - 格式演进
if version == 1:
    # 旧格式解析逻辑
elif version == 2:
    # 中间格式解析逻辑
else:  # version == 3
    # 当前格式解析逻辑

# id - 唯一标识
# 用于：
# 1. 会话去重
# 2. fork 时记录亲子关系
# 3. 数据库索引

# cwd - 工作目录
# 用于：
# 1. 区分不同项目的会话
# 2. 会话列表按项目分组

# parent_session - fork 溯源
# fork 时设置，记录"这个会话是从哪个分叉来的"
# 用途：追踪对话历史的来源
```

### 2.4 Header 实战例子

```python
# 创建会话
manager = SessionManager.create(cwd="/project")

# 查看 Header
header = manager._file_entries[0]
print(header.id)          # "abc123def456"
print(header.cwd)         # "/project"
print(header.timestamp)   # "2024-01-01T10:00:00.000000"

# fork（分叉）会话
new_manager = SessionManager.fork_from(
    source_path="/path/to/old.jsonl",
    target_cwd="/new/project"
)

# 新会话的 Header
new_header = new_manager._file_entries[0]
print(new_header.parent_session)  # "/path/to/old.jsonl"
print(new_header.cwd)            # "/new/project"
```

---

## 3. Entry（条目）

### 3.1 Entry 是什么？

Entry 是**会话的每一条记录**，从第二条开始，每行一个：

```json
{"type": "message", "id": "msg001", "parent_id": null, "message": {...}}
{"type": "message", "id": "msg002", "parent_id": "msg001", "message": {...}}
```

### 3.2 Entry 的通用结构

```python
class SessionEntryBase:
    type: str           # 条目类型
    id: str            # 唯一 ID
    parent_id: str | None  # 父节点 ID（形成树的关键！）
    timestamp: str     # 时间戳
```

**`parent_id` 是树结构的核心**：
- `parent_id = null` → 这是根节点的直接子节点
- `parent_id = "msg001"` → 这条是 msg001 的子节点

### 3.3 Entry 类型总览

| 类型 | 说明 | 参与上下文 | 触发刷盘 |
|------|------|-----------|---------|
| `message` | 对话消息 | ✅ | ✅ |
| `thinking_level_change` | 思考级别变更 | ❌ | ❌ |
| `model_change` | 模型变更 | ❌ | ❌ |
| `compaction` | 压缩摘要 | ✅ | ✅ |
| `branch_summary` | 分支摘要 | ✅ | ✅ |
| `custom` | 自定义数据 | ❌ | ❌ |
| `custom_message` | 自定义消息 | ✅ | ✅ |
| `session_info` | 会话信息 | ❌ | ❌ |
| `label` | 标签 | ❌ | ❌ |

---

## 4. 逐个解析 Entry 类型

### 4.1 message（对话消息）

**最重要的 Entry**

```python
class SessionMessageEntry:
    type: Literal["message"]
    id: str                    # "msg001"
    parent_id: str | None      # 指向父节点
    timestamp: str              # "2024-01-01T10:00:00.000000"
    message: AgentMessage       # 实际消息内容
```

**AgentMessage 结构**：
```python
class AgentMessage:
    role: "user" | "assistant" | "tool_result"
    content: str | list[ContentBlock]
    provider: str | None        # "kimi"
    model: str | None          # "moonshot-v1-8k"
    timestamp: int | None      # Unix timestamp
```

**例子**：
```json
{
  "type": "message",
  "id": "msg002",
  "parent_id": "msg001",
  "timestamp": "2024-01-01T10:00:05.000000",
  "message": {
    "role": "user",
    "content": [{"type": "text", "text": "帮我写个排序算法"}],
    "provider": "kimi",
    "model": "moonshot-v1-8k",
    "timestamp": 1704090005000
  }
}
```

**怎么生效的？**
```python
# 追加消息
msg = {"role": "user", "content": "帮我写个排序算法"}
entry = manager.append_message(msg)

# entry.message 就是 AgentMessage 对象
# build_context() 会提取所有 message 条目的 message 属性
# 作为发送给 LLM 的上下文
```

---

### 4.2 thinking_level_change（思考级别变更）

**用于控制 AI 的思考深度**

```python
class ThinkingLevelChangeEntry:
    type: Literal["thinking_level_change"]
    id: str
    parent_id: str | None
    timestamp: str
    thinking_level: "off" | "low" | "high" | "medium"
```

**例子**：
```json
{
  "type": "thinking_level_change",
  "id": "tl001",
  "parent_id": "msg002",
  "timestamp": "2024-01-01T10:05:00.000000",
  "thinking_level": "high"
}
```

**怎么生效的？**
```python
# 追加思考级别变更
entry = manager.append_thinking_level_change("high")

# build_context() 会提取最后一条 thinking_level_change
# 影响 AI 的思考模式：
# - "off": 不思考，直接回答
# - "low": 简单思考
# - "medium": 正常思考
# - "high": 深度思考（更慢但更全面）
```

---

### 4.3 model_change（模型变更）

**切换 AI 模型**

```python
class ModelChangeEntry:
    type: Literal["model_change"]
    id: str
    parent_id: str | None
    timestamp: str
    provider: str           # "anthropic"
    model_id: str           # "claude-3-sonnet-20240229"
```

**例子**：
```json
{
  "type": "model_change",
  "id": "mc001",
  "parent_id": "msg005",
  "timestamp": "2024-01-01T11:00:00.000000",
  "provider": "anthropic",
  "model_id": "claude-3-sonnet-20240229"
}
```

**怎么生效的？**
```python
# 切换模型
entry = manager.append_model_change(
    provider="anthropic",
    model_id="claude-3-sonnet"
)

# build_context() 提取最后一条 model_change
# switchSession() 恢复时调用 agent.set_model()
```

---

### 4.4 compaction（压缩摘要）

**长对话压缩后的摘要**

```python
class CompactionEntry:
    type: Literal["compaction"]
    id: str
    parent_id: str | None
    timestamp: str
    summary: str                    # "用户讨论了：Python基础、列表操作..."
    first_kept_entry_id: str       # 第一个保留的条目 ID
    tokens_before: int              # 压缩前的 token 数
    details: dict | None            # 扩展信息（可选）
    from_hook: bool | None         # 是否由扩展触发
```

**例子**：
```json
{
  "type": "compaction",
  "id": "cp001",
  "parent_id": "msg050",
  "timestamp": "2024-01-01T12:00:00.000000",
  "summary": "用户讨论了：Python基础、列表操作、文件读写、异常处理、单元测试...",
  "first_kept_entry_id": "msg045",
  "tokens_before": 8500,
  "details": {"reason": "context_overflow"}
}
```

**怎么生效的？**
```python
# build_context() 处理压缩的逻辑：
context = manager.build_session_context()

# 1. 找到压缩条目
# 2. 添加压缩摘要消息到上下文
# 3. 从 first_kept_entry_id 开始，只添加保留的条目

# AI 看到的是：
# [压缩摘要消息] msg045, msg046, msg047, ..., msg100
# 不是 msg001 到 msg100 全部！
```

---

### 4.5 branch_summary（分支摘要）

**分支时对被放弃路径的摘要**

```python
class BranchSummaryEntry:
    type: Literal["branch_summary"]
    id: str
    parent_id: str | None
    timestamp: str
    from_id: str                    # "branch-point-id" 或 "root"
    summary: str                     # "用户问了 QuickSort，我们讨论了..."
    details: dict | None            # 扩展信息
    from_hook: bool | None          # 是否由扩展触发
```

**例子**：
```json
{
  "type": "branch_summary",
  "id": "bs001",
  "parent_id": "msg003",
  "timestamp": "2024-01-01T12:30:00.000000",
  "from_id": "msg001",
  "summary": "用户问了排序算法，我们讨论了 QuickSort 的实现和复杂度"
}
```

**怎么生效的？**
```python
# 分支并生成摘要
entry = manager.branch_with_summary(
    branch_from_id=msg1.id,
    summary="用户问了 QuickSort，我们讨论了..."
)

# build_context() 会把 branch_summary 作为特殊消息加入
# AI 看到的是：
# [原始消息...]
# [分支摘要消息] - "用户问了 QuickSort..."
# [新分支的消息...]
```

---

### 4.6 custom（自定义数据）

**扩展用的，不参与上下文**

```python
class CustomEntry:
    type: Literal["custom"]
    id: str
    parent_id: str | None
    timestamp: str
    custom_type: str              # 扩展类型标识
    data: dict | None             # 自定义数据
```

**例子**：
```json
{
  "type": "custom",
  "id": "ct001",
  "parent_id": "msg010",
  "timestamp": "2024-01-01T13:00:00.000000",
  "custom_type": "extension:bookmark",
  "data": {"note": "重要讨论，标记一下"}
}
```

**怎么生效的？**
```python
# 追加自定义条目
entry = manager.append_custom_entry(
    custom_type="extension:bookmark",
    data={"note": "重要讨论"}
)

# build_context() 不会包含 custom 条目
# 只有 UI 或扩展程序读取使用
```

---

### 4.7 custom_message（自定义消息）

**扩展用的，参与上下文（区别于 custom）**

```python
class CustomMessageEntry:
    type: Literal["custom_message"]
    id: str
    parent_id: str | None
    timestamp: str
    custom_type: str              # 扩展类型标识
    content: str | list           # 消息内容
    display: bool                 # 是否在 UI 显示
    details: dict | None          # 扩展元数据
```

**例子**：
```json
{
  "type": "custom_message",
  "id": "cm001",
  "parent_id": "msg015",
  "timestamp": "2024-01-01T13:30:00.000000",
  "custom_type": "extension:system_reminder",
  "content": "别忘了运行测试！",
  "display": true
}
```

**怎么生效的？**
```python
# 追加自定义消息
entry = manager.append_custom_message(
    custom_type="extension:system_reminder",
    content="别忘了运行测试！",
    display=True
)

# build_context() 会转换 custom_message 为消息加入上下文
# AI 会看到这条"系统提醒"
```

---

### 4.8 session_info（会话信息）

**会话的元信息，如名称**

```python
class SessionInfoEntry:
    type: Literal["session_info"]
    id: str
    parent_id: str | None
    timestamp: str
    name: str | None              # 会话显示名称
```

**例子**：
```json
{
  "type": "session_info",
  "id": "si001",
  "parent_id": "msg000",
  "timestamp": "2024-01-01T14:00:00.000000",
  "name": "Python 排序算法讨论"
}
```

**怎么生效的？**
```python
# 设置会话名称
entry = manager.append_session_info(name="Python 排序算法讨论")

# 获取会话名称
name = manager.get_session_name()  # "Python 排序算法讨论"

# 用于 UI 显示、列表排序等
```

---

### 4.9 label（标签）

**给任意条目打标签**

```python
class LabelEntry:
    type: Literal["label"]
    id: str
    parent_id: str | None
    timestamp: str
    target_id: str               # 被标记的条目 ID
    label: str | None            # 标签内容（None = 清除标签）
```

**例子**：
```json
{
  "type": "label",
  "id": "lb001",
  "parent_id": "msg020",
  "timestamp": "2024-01-01T14:30:00.000000",
  "target_id": "msg015",
  "label": "important"
}
```

**怎么生效的？**
```python
# 标记某条消息为重要
entry = manager.append_label_change(
    target_id=msg015.id,
    label="important"
)

# 获取标签
label = manager.get_label(msg015.id)  # "important"

# 用于：
# 1. UI 高亮重要消息
# 2. 快速导航到标记点
# 3. 书签功能
```

---

## 5. 恢复（Restore）机制

### 5.1 什么是恢复？

恢复 = 从文件加载 + 重建内存状态

```python
# 恢复过程
manager = SessionManager.open("/path/to/session.jsonl")

# 1. 读取文件每一行
# 2. 解析为 Entry 对象
# 3. 存入 _file_entries 和 _by_id
# 4. 设置 _leaf_id 为最后一条的 ID
```

### 5.2 每种类型的恢复方式

| 类型 | 恢复后在哪 | 如何使用 |
|------|-----------|---------|
| `message` | `_by_id[id].message` | `build_context()` 提取 |
| `thinking_level_change` | `_by_id[id].thinking_level` | `build_context()` 提取最后值 |
| `model_change` | `_by_id[id].provider/model_id` | `build_context()` 提取最后值 |
| `compaction` | `_by_id[id]` | `build_context()` 识别并处理压缩 |
| `branch_summary` | `_by_id[id]` | `build_context()` 作为特殊消息 |
| `custom` | `_by_id[id].data` | 扩展程序使用，AI 看不到 |
| `custom_message` | `_by_id[id]` | `build_context()` 转换后加入 |
| `session_info` | `_by_id[id].name` | `get_session_name()` 返回 |
| `label` | `_labels_by_id[target_id]` | `get_label()` 返回 |

### 5.3 build_context() 的恢复流程

```python
def build_session_context(self, leaf_id=None) -> SessionContext:
    # 1. 找到叶子节点
    leaf = self._by_id.get(leaf_id or self._leaf_id)
    
    # 2. 从叶子回溯到根，构建路径
    path = []
    current = leaf
    while current:
        path.insert(0, current)  # 头插法，保持顺序
        current = self._by_id.get(current.parent_id)
    
    # 3. 遍历路径，提取信息
    messages = []
    thinking_level = "off"
    model = None
    compaction = None
    
    for entry in path:
        if entry.type == "message":
            messages.append(entry.message)  # 消息加入上下文
        
        elif entry.type == "thinking_level_change":
            thinking_level = entry.thinking_level  # 更新思考级别
        
        elif entry.type == "model_change":
            model = {"provider": entry.provider, "model_id": entry.model_id}
        
        elif entry.type == "compaction":
            compaction = entry
            # 插入压缩摘要消息
            messages.append(CompactionSummaryMessage(...))
        
        elif entry.type == "branch_summary":
            # 插入分支摘要消息
            messages.append(BranchSummaryMessage(...))
        
        elif entry.type == "custom_message":
            # 转换为消息加入
            messages.append(CustomMessage(...))
    
    return SessionContext(
        messages=messages,
        thinking_level=thinking_level,
        model=model
    )
```

---

## 6. 完整示例

### 6.1 完整对话流程

```
文件内容：

Line 1 (Header):
{"type": "session", "id": "sess001", "version": 3, "cwd": "/project", ...}

Line 2:
{"type": "message", "id": "msg001", "parent_id": null, "message": {"role": "user", "content": "Hello"}}

Line 3:
{"type": "message", "id": "msg002", "parent_id": "msg001", "message": {"role": "assistant", "content": "Hi!"}}

Line 4:
{"type": "thinking_level_change", "id": "tl001", "parent_id": "msg002", "thinking_level": "high"}

Line 5:
{"type": "message", "id": "msg003", "parent_id": "msg002", "message": {"role": "user", "content": "Tell me about sorting"}}

Line 6:
{"type": "compaction", "id": "cp001", "parent_id": "msg003", "summary": "...", "first_kept_entry_id": "msg003"}
```

### 6.2 内存结构

```
_by_id 索引:
{
  "sess001": SessionHeader(...),
  "msg001": SessionMessageEntry(message=UserMessage("Hello")),
  "msg002": SessionMessageEntry(message=AssistantMessage("Hi!")),
  "tl001": ThinkingLevelChangeEntry(thinking_level="high"),
  "msg003": SessionMessageEntry(message=UserMessage("Tell me about sorting")),
  "cp001": CompactionEntry(summary="...", first_kept_entry_id="msg003")
}

_leaf_id = "cp001"  # 最后一条的 ID
```

### 6.3 恢复后的上下文

```python
context = manager.build_session_context()

# context.messages = [
#   AssistantMessage("Hi!"),           # msg002
#   CompactionSummaryMessage(...),      # cp001 - 压缩摘要
#   UserMessage("Tell me about sorting") # msg003 - 保留的消息
# ]
#
# context.thinking_level = "high"
# context.model = None
```

---

## 7. 总结

| 概念 | 作用 | 关键属性 |
|------|------|---------|
| **Header** | 会话元信息 | id, cwd, parent_session |
| **message** | 对话内容 | message (role, content) |
| **thinking_level_change** | 思考深度 | thinking_level |
| **model_change** | 模型切换 | provider, model_id |
| **compaction** | 长对话压缩 | summary, first_kept_entry_id |
| **branch_summary** | 分支摘要 | from_id, summary |
| **custom** | 扩展数据 | custom_type, data |
| **custom_message** | 扩展消息 | custom_type, content, display |
| **session_info** | 会话名称 | name |
| **label** | 条目标签 | target_id, label |

**回溯模式的核心**：
- `parent_id` 形成树结构
- `build_context()` 从叶子回溯到根
- 不同类型的 Entry 以不同方式影响 AI 行为
