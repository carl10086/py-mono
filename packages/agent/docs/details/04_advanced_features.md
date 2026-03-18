# 文档 4：高级功能

> **目标**：掌握 Steering、工具调用、Hooks 等高级特性
> 
> **预计时间**：3-4 小时
> **前置知识**：文档 1-3 的内容

---

## 1. 消息队列系统

### 1.1 为什么需要消息队列？

在 Agent 执行过程中，你可能需要：
- **打断当前生成**：用户改变主意
- **插入系统指令**：动态修改行为
- **自动追问**：任务完成后主动询问

### 1.2 Steering 队列（高优先级）

**概念：** Steering 消息会在当前 turn **立即**处理，中断正常流程。

**使用场景：**
```python
# 场景 1：用户打断
await agent.prompt("详细解释量子力学...")  # Agent 开始长篇大论
agent.steer(UserMessage(text="不用详细了，一句话总结"))  # 用户打断
await agent.wait_for_idle()

# 场景 2：系统干预
# 检测到敏感词，立即插入警告
agent.steer(UserMessage(text="[系统] 请勿讨论敏感话题"))
```

**工作原理：**

```
正常流程：
prompt("解释量子力学") → LLM 生成 → 完成

插入 Steering：
prompt("解释量子力学") → LLM 开始生成...
                              │
                              ▼
                    steer("一句话总结")  ◄── 插入
                              │
                              ▼
                    LLM 停止原生成
                              │
                              ▼
                    处理 steering 消息
                              │
                              ▼
                    生成新回复
```

**代码示例：**

```python
from ai.types import UserMessage

async def handle_interruption():
    # 开始一个长任务
    await agent.prompt("请写一部短篇小说的提纲")
    
    # 模拟用户在 2 秒后打断
    await asyncio.sleep(2)
    print("\n[用户打断]")
    agent.steer(UserMessage(text="不用写了，改为写诗"))
    
    await agent.wait_for_idle()
```

### 1.3 Follow-up 队列（低优先级）

**概念：** Follow-up 消息在当前 turn **完成后**处理。

**使用场景：**
```python
# 场景：自动追问
def on_event(event):
    if event.get("type") == "agent_end":
        # 对话结束，主动询问
        agent.follow_up(UserMessage(text="还有其他问题吗？"))

agent.subscribe(on_event)
```

**工作原理：**

```
正常流程：
Turn 1: prompt("你好") → 完成 → agent_end
                              │
                              ▼
                    检查 follow_up_queue
                              │
                              ▼
                    有消息？→ 启动 Turn 2
                              │
                              ▼
                    处理 follow_up
```

### 1.4 队列模式

**steering_mode**：控制一次取出多少 steering 消息
```python
# one-at-a-time（默认）：每次只处理一条
AgentOptions(steering_mode="one-at-a-time")

# all：一次性处理所有 steering
AgentOptions(steering_mode="all")
```

**使用场景对比：**

| 模式 | 行为 | 适用场景 |
|------|------|---------|
| `one-at-a-time` | 每次取一条 | 用户逐条输入 |
| `all` | 一次取全部 | 批量系统消息 |

---

## 2. 工具调用详解

### 2.1 工具调用流程

```
1. 用户输入
   "北京天气怎么样？"
          │
          ▼
2. LLM 分析
   - 识别需要天气信息
   - 生成 tool_call
          │
          ▼
3. Agent 执行
   - 查找工具（get_weather）
   - 调用 execute()
          │
          ▼
4. 工具执行
   - 查询天气 API
   - 返回结果
          │
          ▼
5. Agent 包装
   - 创建 ToolResultMessage
   - 加入历史
          │
          ▼
6. LLM 生成回复
   - 基于工具结果
   - 生成自然语言回复
```

### 2.2 完整工具示例

```python
import asyncio
from pathlib import Path
from ai.types import TextContent, UserMessage
from agent.types import AgentToolResult

class FileManagerTool:
    """文件管理工具"""
    
    name = "file_manager"
    description = "管理文件系统，支持读取、写入、列出目录"
    label = "文件管理"
    
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "write", "list"],
                "description": "操作类型"
            },
            "path": {
                "type": "string",
                "description": "文件或目录路径"
            },
            "content": {
                "type": "string",
                "description": "写入内容（write 时必填）"
            }
        },
        "required": ["action", "path"]
    }
    
    async def execute(self, tool_call_id, params, signal, on_update):
        action = params["action"]
        path = Path(params["path"])
        
        try:
            if action == "read":
                if not path.exists():
                    return AgentToolResult(
                        content=[TextContent(text=f"❌ 文件不存在: {path}")],
                        details={"error": "FileNotFound", "path": str(path)}
                    )
                
                content = path.read_text(encoding='utf-8')
                return AgentToolResult(
                    content=[TextContent(text=f"📄 {path}:\n```\n{content[:1000]}\n```")],
                    details={"action": "read", "path": str(path), "size": len(content)}
                )
            
            elif action == "write":
                content = params.get("content", "")
                path.write_text(content, encoding='utf-8')
                return AgentToolResult(
                    content=[TextContent(text=f"✅ 已写入: {path} ({len(content)} 字符)")],
                    details={"action": "write", "path": str(path), "size": len(content)}
                )
            
            elif action == "list":
                if not path.exists():
                    return AgentToolResult(
                        content=[TextContent(text=f"❌ 目录不存在: {path}")],
                        details={"error": "DirNotFound", "path": str(path)}
                    )
                
                items = list(path.iterdir())
                files = [f.name for f in items if f.is_file()]
                dirs = [d.name for d in items if d.is_dir()]
                
                result = f"📁 {path}\n"
                if dirs:
                    result += "\n目录:\n" + "\n".join(f"  📂 {d}" for d in dirs)
                if files:
                    result += "\n文件:\n" + "\n".join(f"  📄 {f}" for f in files)
                
                return AgentToolResult(
                    content=[TextContent(text=result)],
                    details={"action": "list", "path": str(path), "files": len(files), "dirs": len(dirs)}
                )
        
        except Exception as e:
            return AgentToolResult(
                content=[TextContent(text=f"❌ 错误: {str(e)}")],
                details={"error": str(e), "path": str(path)}
            )

# 使用
agent.set_tools([FileManagerTool()])
await agent.prompt("列出当前目录的文件")
await agent.wait_for_idle()
```

### 2.3 工具执行模式

**Sequential（顺序执行）**：
```python
AgentOptions(tool_execution="sequential")
```
- 工具 A 完成后才执行工具 B
- 适用：有依赖关系的工具

**Parallel（并行执行，默认）**：
```python
AgentOptions(tool_execution="parallel")
```
- 所有工具同时启动
- 适用：相互独立的工具
- 更快，但结果顺序可能不一致

**对比示例：**

```python
# Sequential：必须按顺序
# 工具 1: 获取用户 ID
# 工具 2: 根据 ID 查询订单（依赖工具 1）
# → 必须用 sequential

# Parallel：可以同时执行
# 工具 1: 查天气
# 工具 2: 查新闻
# 工具 3: 查股票
# → 可以用 parallel，更快
```

---

## 3. Hooks 系统

### 3.1 BeforeToolCall - 执行前拦截

**用途：**
- 权限检查
- 参数验证
- 审计日志

**示例：权限系统**

```python
class PermissionManager:
    def __init__(self):
        self.user_permissions = {
            "user1": ["read"],
            "user2": ["read", "write"],
            "admin": ["read", "write", "delete"]
        }
    
    def has_permission(self, user, action):
        return action in self.user_permissions.get(user, [])

perm_manager = PermissionManager()

async def before_tool_call(ctx, signal):
    """
    权限检查 Hook
    """
    tool_name = ctx.tool_call.name
    args = ctx.args
    
    # 检查危险操作
    dangerous_tools = ["delete_file", "execute_command", "send_email"]
    
    if tool_name in dangerous_tools:
        user = get_current_user()  # 假设有此函数
        
        if not perm_manager.has_permission(user, tool_name):
            return BeforeToolCallResult(
                block=True,
                reason=f"⛔ 您没有使用 {tool_name} 的权限。请联系管理员。"
            )
        
        # 记录审计日志
        log_audit(f"User {user} executed {tool_name} with args: {args}")
    
    # 参数验证示例
    if tool_name == "write_file":
        path = args.get("path", "")
        if ".." in path or path.startswith("/"):
            return BeforeToolCallResult(
                block=True,
                reason="⚠️ 禁止写入系统目录"
            )
    
    # 允许执行
    return None

# 注册
agent = Agent(AgentOptions(
    stream_fn=stream_fn,
    before_tool_call=before_tool_call
))
```

### 3.2 AfterToolCall - 执行后处理

**用途：**
- 结果格式化
- 敏感信息过滤
- 缓存结果

**示例：敏感信息过滤器**

```python
SENSITIVE_PATTERNS = [
    (r"password[:\s]+\S+", "password: ***"),
    (r"api[_-]?key[:\s]+\S+", "api_key: ***"),
    (r"token[:\s]+\S+", "token: ***"),
]

async def after_tool_call(ctx, signal):
    """
    敏感信息过滤 Hook
    """
    import re
    
    original_content = ctx.result.content[0].text
    filtered_content = original_content
    
    # 应用过滤规则
    for pattern, replacement in SENSITIVE_PATTERNS:
        filtered_content = re.sub(pattern, replacement, filtered_content, flags=re.IGNORECASE)
    
    # 如果有修改，返回过滤后的结果
    if filtered_content != original_content:
        print(f"[Filter] 敏感信息已过滤")
        return AfterToolCallResult(
            content=[TextContent(text=filtered_content)],
            details={**ctx.result.details, "filtered": True}
        )
    
    # 未修改，使用原结果
    return None
```

**示例：结果缓存**

```python
class ToolResultCache:
    def __init__(self):
        self.cache = {}
    
    def get_key(self, tool_name, args):
        """生成缓存键"""
        import hashlib
        import json
        key_data = json.dumps({"tool": tool_name, "args": args}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def after_tool_call(self, ctx, signal):
        """缓存 Hook"""
        tool_name = ctx.tool_call.name
        args = ctx.args
        
        # 只对读操作缓存
        if tool_name not in ["read_file", "get_weather", "search"]:
            return None
        
        cache_key = self.get_key(tool_name, args)
        
        # 检查缓存
        if cache_key in self.cache:
            print(f"[Cache] 命中: {tool_name}")
            cached_result = self.cache[cache_key]
            return AfterToolCallResult(
                content=cached_result["content"],
                details={**cached_result["details"], "cached": True}
            )
        
        # 新结果，存入缓存
        self.cache[cache_key] = {
            "content": ctx.result.content,
            "details": ctx.result.details
        }
        
        return None

cache = ToolResultCache()
agent = Agent(AgentOptions(
    after_tool_call=cache.after_tool_call
))
```

---

## 4. 思考模式

### 4.1 什么是思考模式？

让 LLM 在回答前"多想一会儿"，生成更高质量的内容。

**不同等级：**
- `off`：直接回答
- `minimal`：简单思考
- `low`：日常对话
- `medium`：一般任务
- `high`：复杂推理
- `xhigh`：数学证明、代码调试

### 4.2 使用示例

```python
# 简单问答 - 快速响应
agent.set_thinking_level("off")
await agent.prompt("今天星期几？")

# 创意写作 - 中等思考
agent.set_thinking_level("medium")
await agent.prompt("写一首关于秋天的诗")

# 数学问题 - 深度思考
agent.set_thinking_level("high")
await agent.prompt("解方程：2x² + 3x - 5 = 0")

# 代码调试 - 极致思考
agent.set_thinking_level("xhigh")
await agent.prompt("这段代码为什么报错：[代码]")
```

### 4.3 观察思考内容

```python
thinking_parts = []
text_parts = []

def on_event(event):
    if event.get("type") == "message_update":
        msg = event.get("message")
        if msg and msg.content:
            for content in msg.content:
                if content.type == "thinking":
                    thinking_parts.append(content.thinking)
                elif content.type == "text":
                    text_parts.append(content.text)

agent.subscribe(on_event)
agent.set_thinking_level("high")

await agent.prompt("证明勾股定理")
await agent.wait_for_idle()

print("=== 思考过程 ===")
print("".join(thinking_parts))
print("\n=== 最终答案 ===")
print("".join(text_parts))
```

---

## 5. 实战项目：智能文件助手

结合所有高级功能，实现一个智能文件管理助手：

```python
import asyncio
from agent import Agent, AgentOptions
from ai.providers import KimiProvider
from ai.types import UserMessage

async def main():
    provider = KimiProvider()
    
    async def stream_fn(model, context, options):
        return provider.stream_simple(model, context, options)
    
    # 创建带权限和缓存的 Agent
    agent = Agent(AgentOptions(
        stream_fn=stream_fn,
        tool_execution="sequential",
        before_tool_call=permission_check,
        after_tool_call=clean_result
    ))
    
    agent.set_model(provider.get_model())
    agent.set_system_prompt("""你是一个智能文件助手。
你可以帮用户读取、写入、列出文件。
操作前请确认用户的意图。""")
    
    agent.set_tools([FileManagerTool()])
    
    # 打字机效果
    agent.subscribe(create_typewriter_callback())
    
    # 交互循环
    print("🤖 文件助手已启动（输入 'quit' 退出）")
    print("-" * 50)
    
    while True:
        user_input = input("\n你: ").strip()
        
        if user_input.lower() == 'quit':
            break
        
        if user_input.lower() == 'clear':
            agent.reset()
            print("🗑️  对话已清空")
            continue
        
        await agent.prompt(user_input)
        await agent.wait_for_idle()
        
        # 显示工具统计
        if hasattr(agent.state, 'last_tool_stats'):
            stats = agent.state.last_tool_stats
            print(f"\n[使用了 {stats['tool_count']} 个工具]")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 6. 下一步

完成本文档后，你应该能：
- ✅ 使用 Steering 实现用户打断
- ✅ 实现完整的工具调用流程
- ✅ 使用 Hooks 进行权限控制和结果处理
- ✅ 根据场景选择合适的思考等级

**下一步：** [文档 5：源码深度解析](05_source_code_deep_dive.md)

---

## 附录：高级功能速查表

| 功能 | 用途 | 关键 API |
|------|------|---------|
| Steering | 用户打断 | `agent.steer()` |
| Follow-up | 自动追问 | `agent.follow_up()` |
| 工具调用 | 扩展能力 | `AgentTool` Protocol |
| Before Hook | 权限检查 | `AgentOptions.before_tool_call` |
| After Hook | 结果处理 | `AgentOptions.after_tool_call` |
| 思考模式 | 控制推理深度 | `agent.set_thinking_level()` |
| 并行执行 | 性能优化 | `tool_execution="parallel"` |
