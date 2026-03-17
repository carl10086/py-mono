# KimiProvider 设计文档

## 概述

KimiProvider 是 py-mono AI 模块的 Kimi API 适配实现。Kimi API 基于 Anthropic Messages API 设计，因此本实现继承自 AnthropicProvider，针对 Kimi 特有功能进行优化。

## 架构决策

### 为什么选择继承 AnthropicProvider？

1. **API 高度兼容**：Kimi API 完全兼容 Anthropic Messages API 格式
2. **功能完整**：支持 thinking、cache control、tools 等全部特性
3. **复用代码**：避免重复实现消息转换、流式解析等通用逻辑
4. **维护简单**：Anthropic SDK 更新时自动受益

### 与直接使用 AnthropicProvider 的区别

| 特性 | AnthropicProvider | KimiProvider |
|------|------------------|--------------|
| 默认 base_url | https://api.anthropic.com | https://api.moonshot.cn |
| 环境变量 | ANTHROPIC_API_KEY | KIMI_API_KEY |
| 模型名称 | claude-3-* | kimi-k2-* |
| thinking 配置 | Budget/Adaptive | 针对 Kimi 优化 |
| 缓存策略 | 通用 | Kimi 特有优化 |

## 核心功能

### 1. Thinking/Reasoning 模式

Kimi K2 系列模型支持 reasoning 功能，配置方式与 Claude 略有不同。

**配置映射**：

```python
# Budget-based thinking（Kimi K2 使用）
minimal -> {"type": "enabled", "budget_tokens": 512}   # 轻量级推理
low     -> {"type": "enabled", "budget_tokens": 1024}  # 基础推理
medium  -> {"type": "enabled", "budget_tokens": 4096}  # 标准推理
high    -> {"type": "enabled", "budget_tokens": 16000} # 深度推理
xhigh   -> {"type": "enabled", "budget_tokens": 32000} # 极致推理
```

**使用示例**：

```python
from ai.providers import KimiProvider

# 创建 provider
provider = KimiProvider(
    model="kimi-k2-turbo-preview",
    default_max_tokens=8192,
)

# 启用 reasoning
provider = provider.with_thinking("medium")

# 流式生成
stream = provider.stream(model, context)
async for event in stream:
    if event.type == "thinking_delta":
        print(f"[思考] {event.delta}", end="")
    elif event.type == "text_delta":
        print(event.delta, end="")
```

### 2. 智能缓存注入

参考 kimi-cli 的实现，缓存注入策略：

**注入点**：
1. **System Prompt** - 完整注入（如果存在）
2. **最后一条消息** - 仅最后一个内容块
3. **Tools** - 仅最后一个工具

**类型判断逻辑**：
```python
match last_block["type"]:
    case "text" | "image" | "tool_use" | "tool_result":
        # 可注入缓存
        last_block["cache_control"] = {"type": "ephemeral"}
    case "thinking" | "redacted_thinking":
        # 跳过 - 临时内容，缓存价值低
        pass
```

**成本考虑**：
- Cache Write（首次标记）：1.25x 成本（比正常贵 25%）
- Cache Read（命中缓存）：0.1x 成本（比正常便宜 90%）
- 只有重复使用时才划算

### 3. 流式事件处理

**支持的事件类型**：

| 事件 | 说明 | 来源 |
|------|------|------|
| `EventThinkingStart` | 思考块开始 | content_block_start (thinking) |
| `EventThinkingDelta` | 思考内容增量 | content_block_delta (thinking_delta) |
| `EventThinkingEnd` | 思考块结束 | content_block_stop |
| `EventTextStart` | 文本块开始 | content_block_start (text) |
| `EventTextDelta` | 文本内容增量 | content_block_delta (text_delta) |
| `EventTextEnd` | 文本块结束 | content_block_stop |
| `EventToolCallStart` | 工具调用开始 | content_block_start (tool_use) |
| `EventToolCallDelta` | 工具参数增量 | content_block_delta (input_json_delta) |
| `EventToolCallEnd` | 工具调用结束 | content_block_stop |

**事件流顺序**：
```
EventStart 
  → EventThinkingStart → EventThinkingDelta* → EventThinkingEnd
  → EventTextStart → EventTextDelta* → EventTextEnd
  → EventToolCallStart → EventToolCallDelta* → EventToolCallEnd
→ EventDone
```

### 4. Token 使用统计

Kimi API 返回的 usage 字段与 Anthropic 略有不同，需要适配：

```python
usage = Usage(
    input=message.usage.input_tokens or 0,
    output=message.usage.output_tokens or 0,
    cache_read=getattr(message.usage, "cache_read_input_tokens", 0) or 0,
    cache_write=getattr(message.usage, "cache_creation_input_tokens", 0) or 0,
)
```

## 接口设计

### KimiProvider 类

```python
class KimiProvider(AnthropicProvider):
    """Kimi Provider - 优化 Kimi API 访问
    
    使用方式：
        export KIMI_API_KEY=your-api-key
        
        provider = KimiProvider(
            model="kimi-k2-turbo-preview",
            default_max_tokens=8192,
        )
        
        # 启用 reasoning
        provider = provider.with_thinking("medium")
        
        response = await provider.complete(context)
    """
    
    name: str = "kimi"
    
    # Kimi 支持的模型配置
    SUPPORTED_MODELS: ClassVar[dict[str, dict[str, Any]]] = {
        "kimi-k2-turbo-preview": {
            "context_window": 256000,
            "max_tokens": 16384,
            "supports_reasoning": True,
        },
        "kimi-k2": {
            "context_window": 256000,
            "max_tokens": 16384,
            "supports_reasoning": True,
        },
    }
    
    def __init__(
        self,
        *,
        model: str = "kimi-k2-turbo-preview",
        api_key: str | None = None,
        base_url: str = "https://api.moonshot.cn",
        default_max_tokens: int = 8192,
        **kwargs: Any,
    ) -> None:
        """初始化 KimiProvider
        
        Args:
            model: 模型名称，如 "kimi-k2-turbo-preview"
            api_key: API 密钥，默认从 KIMI_API_KEY 环境变量读取
            base_url: API 基础 URL，默认 https://api.moonshot.cn
            default_max_tokens: 默认最大生成 token 数
            **kwargs: 其他参数传递给 AnthropicProvider
        """
    
    def with_thinking(self, effort: ThinkingLevel) -> Self:
        """配置 reasoning/thinking 模式
        
        Args:
            effort: 思考强度等级
                - "off": 禁用 reasoning
                - "minimal": 轻量级推理（512 tokens）
                - "low": 基础推理（1024 tokens）
                - "medium": 标准推理（4096 tokens）
                - "high": 深度推理（16000 tokens）
                - "xhigh": 极致推理（32000 tokens）
        
        Returns:
            新的 KimiProvider 实例（不可变更新）
        """
```

### 使用示例

**基础使用**：

```python
import asyncio
from ai.providers import KimiProvider
from ai.types import Context, UserMessage

async def main():
    # 创建 provider
    provider = KimiProvider(
        model="kimi-k2-turbo-preview",
        default_max_tokens=4096,
    )
    
    # 构建上下文
    context = Context(
        system_prompt="你是一个有帮助的助手",
        messages=[
            UserMessage(content="你好，请介绍一下自己"),
        ],
    )
    
    # 流式生成
    stream = provider.stream_simple(
        model=provider.get_model("kimi-k2-turbo-preview"),
        context=context,
    )
    
    # 消费流式事件
    async for event in stream:
        match event.type:
            case "text_delta":
                print(event.delta, end="", flush=True)
            case "done":
                print("\n\n生成完成")

asyncio.run(main())
```

**启用 Reasoning**：

```python
from ai.providers import KimiProvider
from ai.types import Context, UserMessage

async def with_reasoning():
    provider = KimiProvider(model="kimi-k2-turbo-preview")
    
    # 启用 reasoning
    provider = provider.with_thinking("high")
    
    context = Context(
        messages=[UserMessage(content="解这个方程: 2x + 5 = 13")],
    )
    
    stream = provider.stream_simple(
        model=provider.get_model("kimi-k2-turbo-preview"),
        context=context,
    )
    
    thinking = []
    answer = []
    
    async for event in stream:
        match event.type:
            case "thinking_start":
                print("[开始思考]")
            case "thinking_delta":
                thinking.append(event.delta)
                print(event.delta, end="")
            case "thinking_end":
                print("\n[思考结束]")
            case "text_start":
                print("\n[开始回答]")
            case "text_delta":
                answer.append(event.delta)
                print(event.delta, end="")
```

**带工具调用**：

```python
from ai.types import Tool, Context

# 定义工具
calculator_tool = Tool(
    name="calculator",
    description="执行数学计算",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式",
            },
        },
        "required": ["expression"],
    },
)

async def with_tools():
    provider = KimiProvider(model="kimi-k2-turbo-preview")
    
    context = Context(
        messages=[UserMessage(content="计算 123 * 456")],
        tools=[calculator_tool],
    )
    
    stream = provider.stream(
        model=provider.get_model("kimi-k2-turbo-preview"),
        context=context,
    )
    
    async for event in stream:
        match event.type:
            case "toolcall_start":
                print(f"[调用工具] {event.tool_call.name}")
            case "toolcall_end":
                print(f"[工具调用完成] 参数: {event.tool_call.arguments}")
            case "text_delta":
                print(event.delta, end="")
```

## 与 AnthropicProvider 的差异

### 差异 1：默认配置

```python
# AnthropicProvider
AnthropicProvider(
    model="claude-3-sonnet-20240229",
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
    base_url="https://api.anthropic.com",
)

# KimiProvider
KimiProvider(
    model="kimi-k2-turbo-preview",  # 默认 Kimi 模型
    api_key=os.environ.get("KIMI_API_KEY"),  # 不同环境变量
    base_url="https://api.moonshot.cn",  # Kimi API 地址
)
```

### 差异 2：Thinking 配置

```python
# Anthropic：可能支持 adaptive（Opus 4.6+）
provider.with_thinking("high")
# Claude 3.7 Opus 4.6+: {"type": "adaptive"}
# 旧模型: {"type": "enabled", "budget_tokens": 32000}

# Kimi：仅支持 budget-based
provider.with_thinking("high")
# Kimi K2: {"type": "enabled", "budget_tokens": 16000}
```

### 差异 3：模型能力检测

```python
# AnthropicProvider - 通过模型名检测
if "opus-4.6" in model.lower():
    # 支持 adaptive thinking

# KimiProvider - 通过配置检测
if model in self.SUPPORTED_MODELS:
    config = self.SUPPORTED_MODELS[model]
    if config.get("supports_reasoning"):
        # 支持 reasoning
```

### 差异 4：缓存注入策略

KimiProvider 针对 Kimi API 的缓存行为做了特殊优化：

```python
def _inject_cache_control(self, messages, tools, system_prompt):
    # Kimi 特有的优化：
    # 1. 对于大 system prompt，分段注入缓存
    # 2. 对于长对话，智能选择注入点
    # 3. 考虑 Kimi 的缓存过期策略
```

## 实现细节

### 文件结构

```
packages/ai/src/ai/providers/
├── __init__.py          # 导出 KimiProvider
├── anthropic.py         # AnthropicProvider 基类
└── kimi.py              # KimiProvider 实现
```

### 依赖关系

```
kimi.py
  ├── anthropic.py       # 继承 AnthropicProvider
  ├── types.py           # ThinkingLevel, Model 等类型
  └── stream.py          # 事件流类型
```

### 关键代码片段

**初始化**：

```python
def __init__(
    self,
    *,
    model: str = "kimi-k2-turbo-preview",
    api_key: str | None = None,
    base_url: str = "https://api.moonshot.cn",
    default_max_tokens: int = 8192,
    **kwargs: Any,
) -> None:
    # 优先使用 KIMI_API_KEY，回退到 API_KEY
    api_key = api_key or os.environ.get("KIMI_API_KEY") or os.environ.get("API_KEY")
    
    super().__init__(
        model=model,
        api_key=api_key,
        base_url=base_url,
        default_max_tokens=default_max_tokens,
        **kwargs,
    )
```

**Thinking 配置**：

```python
def with_thinking(self, effort: ThinkingLevel) -> Self:
    # Kimi 目前只支持 budget-based
    budgets = {
        "off": None,
        "minimal": 512,
        "low": 1024,
        "medium": 4096,
        "high": 16000,
        "xhigh": 32000,
    }
    
    budget = budgets.get(effort)
    if budget is None:
        thinking_config = {"type": "disabled"}
    else:
        thinking_config = {"type": "enabled", "budget_tokens": budget}
    
    return self.with_generation_kwargs(thinking=thinking_config)
```

## 测试策略

### 单元测试

```python
# tests/providers/test_kimi.py

class TestKimiProvider:
    def test_init_with_env_var(self, monkeypatch):
        monkeypatch.setenv("KIMI_API_KEY", "test-key")
        provider = KimiProvider(model="kimi-k2-turbo-preview")
        assert provider._api_key == "test-key"
    
    def test_with_thinking(self):
        provider = KimiProvider(model="kimi-k2-turbo-preview")
        new_provider = provider.with_thinking("high")
        
        assert new_provider._generation_kwargs["thinking"] == {
            "type": "enabled",
            "budget_tokens": 16000,
        }
    
    def test_thinking_chain(self):
        provider = KimiProvider(model="kimi-k2-turbo-preview")
        p1 = provider.with_thinking("medium")
        p2 = p1.with_thinking("high")
        
        # 链式调用创建新实例，不影响原实例
        assert "thinking" not in provider._generation_kwargs
        assert p1._generation_kwargs["thinking"]["budget_tokens"] == 4096
        assert p2._generation_kwargs["thinking"]["budget_tokens"] == 16000
```

### 集成测试

```python
# tests/providers/test_kimi_integration.py

@pytest.mark.asyncio
async def test_stream_with_thinking():
    provider = KimiProvider(model="kimi-k2-turbo-preview")
    provider = provider.with_thinking("low")
    
    context = Context(
        messages=[UserMessage(content="1+1=?")],
    )
    
    stream = provider.stream(
        model=provider.get_model("kimi-k2-turbo-preview"),
        context=context,
    )
    
    events = []
    async for event in stream:
        events.append(event)
    
    # 验证事件序列
    assert events[0].type == "start"
    assert any(e.type == "thinking_start" for e in events)
    assert any(e.type == "text_start" for e in events)
    assert events[-1].type == "done"
```

## 性能考虑

### Token 预算调整

启用高 thinking budget 时，需要调整 max_tokens：

```python
def _adjust_max_tokens(self, max_tokens: int, thinking_budget: int) -> int:
    """确保 thinking budget 不占用回答空间
    
    如果 max_tokens=4096，thinking_budget=32000，
    会导致回答空间不足（4096 - 32000 = 负数）
    """
    min_output_tokens = 1024  # 至少保留 1024 tokens 用于回答
    adjusted = max(max_tokens, thinking_budget + min_output_tokens)
    return min(adjusted, self.MAX_OUTPUT_TOKENS)
```

### 缓存命中率优化

```python
def _optimize_cache_injection(self, messages: list[dict]) -> list[dict]:
    """优化缓存注入策略以提高命中率
    
    策略：
    1. 静态 system prompt 总是注入
    2. 对于长对话，每隔 N 条消息注入一次
    3. 最后一条消息总是注入（用于后续轮次命中）
    """
```

## 参考文档

- **kimi-cli 实现**: `/Users/carlyu/soft/projects/py-mono/refer/kimi-cli/packages/kosong/src/kosong/contrib/chat_provider/anthropic.py`
- **Kimi API 文档**: https://platform.moonshot.cn/docs
- **Anthropic Messages API**: https://docs.anthropic.com/en/api/messages

## 实现状态

- [x] 设计文档
- [ ] KimiProvider 类实现
- [ ] 单元测试
- [ ] 集成测试
- [ ] 使用示例
- [ ] API 文档
