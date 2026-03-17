"""
AI 核心类型定义 - 完全对齐 pi-mono TypeScript 实现

提供统一的消息、工具、模型类型，支持多模态内容、工具调用和流式事件。
使用 Pydantic v2 进行类型验证和序列化。

设计决策：
- 类型别名使用 Python 3.10+ 的 X | Y 语法
- 内容类型统一使用 Tagged Union（通过 Literal[type] 区分）
- AssistantMessage 使用统一 content 数组（而非分离的 tool_calls/thinking 字段）
- 所有消息包含 timestamp（Unix 毫秒时间戳）
- Usage 包含完整的成本计算结构
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal, Protocol, TypeAlias, runtime_checkable

from pydantic import BaseModel, Field

# ============================================================================
# API 和 Provider 类型
# ============================================================================

KnownApi: TypeAlias = Literal[
    "openai-completions",
    "mistral-conversations",
    "openai-responses",
    "azure-openai-responses",
    "openai-codex-responses",
    "anthropic-messages",
    "bedrock-converse-stream",
    "google-generative-ai",
    "google-gemini-cli",
    "google-vertex",
]

# 使用 str 扩展允许自定义 API 标识符
type Api = KnownApi | str

KnownProvider: TypeAlias = Literal[
    "amazon-bedrock",
    "anthropic",
    "google",
    "google-gemini-cli",
    "google-antigravity",
    "google-vertex",
    "openai",
    "azure-openai-responses",
    "openai-codex",
    "github-copilot",
    "xai",
    "groq",
    "cerebras",
    "openrouter",
    "vercel-ai-gateway",
    "zai",
    "mistral",
    "minimax",
    "minimax-cn",
    "huggingface",
    "opencode",
    "opencode-go",
    "kimi-coding",
]

type Provider = KnownProvider | str

# ============================================================================
# 思考和预算类型
# ============================================================================

type ThinkingLevel = Literal["minimal", "low", "medium", "high", "xhigh"]
type CacheRetention = Literal["none", "short", "long"]
type Transport = Literal["sse", "websocket", "auto"]
type StopReason = Literal["stop", "length", "toolUse", "error", "aborted"]


class ThinkingBudgets(BaseModel):
    """思考等级的 Token 预算配置（仅用于基于 token 的 provider）"""

    minimal: int | None = None
    low: int | None = None
    medium: int | None = None
    high: int | None = None


# ============================================================================
# 内容类型 - 统一使用 type 字段作为 Tagged Union 标签
# ============================================================================


class TextSignatureV1(BaseModel):
    """文本签名 V1（用于 OpenAI responses 等）"""

    v: Literal[1] = 1
    id: str
    phase: Literal["commentary", "final_answer"] | None = None


class TextContent(BaseModel):
    """文本内容块"""

    type: Literal["text"] = "text"
    text: str
    # 用于 OpenAI responses 的元数据（遗留 ID 字符串或 TextSignatureV1 JSON）
    text_signature: str | None = None


class ThinkingContent(BaseModel):
    """思考/推理内容块（如 Claude 3.7+ 的 extended thinking）"""

    type: Literal["thinking"] = "thinking"
    thinking: str
    # 用于 OpenAI responses 的 reasoning item ID
    thinking_signature: str | None = None
    # 当为 true 时，思考内容被安全过滤器审查，加密负载存储在 thinkingSignature
    redacted: bool = False


class ImageContent(BaseModel):
    """图像内容块（base64 编码）"""

    type: Literal["image"] = "image"
    # base64 编码的图像数据
    data: str
    # MIME 类型，如 "image/jpeg", "image/png"
    mime_type: str


class ToolCall(BaseModel):
    """工具调用内容块 - 在 pi-mono 中作为 content 数组的一部分"""

    type: Literal["toolCall"] = "toolCall"
    id: str
    name: str
    arguments: dict[str, Any]
    # Google 专用：用于复用思考上下文的不透明签名
    thought_signature: str | None = None


type ContentItem = TextContent | ThinkingContent | ImageContent | ToolCall

# ============================================================================
# 消息类型
# ============================================================================


class UserMessage(BaseModel):
    """用户消息

    content 可以是字符串（便捷写法）或内容块数组
    """

    role: Literal["user"] = "user"
    content: str | Sequence[TextContent | ImageContent]
    timestamp: int  # Unix 时间戳（毫秒）

    def __init__(self, **data: Any) -> None:
        """自动设置时间戳，支持便捷构造"""
        if "timestamp" not in data:
            import time

            data["timestamp"] = int(time.time() * 1000)

        # 支持 UserMessage(text="hello") 便捷构造
        if "text" in data:
            text = data.pop("text")
            data["content"] = text if isinstance(text, str) else text

        super().__init__(**data)


class AssistantMessage(BaseModel):
    """助手消息 - 核心差异：content 统一数组

    与当前实现的关键区别：
    - content 包含 TextContent | ThinkingContent | ToolCall 的混合数组
    - 不再分离 tool_calls 和 thinking 字段
    - 包含完整的元信息（api, provider, model, usage, stopReason）
    - 包含 timestamp 和可选的 errorMessage
    """

    role: Literal["assistant"] = "assistant"
    content: Sequence[TextContent | ThinkingContent | ToolCall]
    api: Api
    provider: Provider
    model: str
    usage: Usage
    stop_reason: StopReason
    timestamp: int
    error_message: str | None = None

    def __init__(self, **data: Any) -> None:
        """自动设置时间戳"""
        if "timestamp" not in data:
            import time

            data["timestamp"] = int(time.time() * 1000)
        super().__init__(**data)


class ToolResultMessage(BaseModel):
    """工具执行结果消息

    关键差异：
    - 使用 camelCase 字段名（toolCallId, toolName）
    - content 是内容块数组，支持文本和图像
    - 包含 details 字段用于 provider 特定数据
    - 包含 timestamp
    """

    role: Literal["toolResult"] = "toolResult"
    tool_call_id: str
    tool_name: str
    content: Sequence[TextContent | ImageContent]
    details: Any | None = None  # provider 特定的详细信息
    is_error: bool = False
    timestamp: int  # Unix 时间戳（毫秒）

    def __init__(self, **data: Any) -> None:
        """自动设置时间戳"""
        if "timestamp" not in data:
            import time

            data["timestamp"] = int(time.time() * 1000)
        super().__init__(**data)


type Message = UserMessage | AssistantMessage | ToolResultMessage

# ============================================================================
# 工具定义 - TypeBox 兼容
# ============================================================================


@runtime_checkable
class TSchema(Protocol):
    """TypeBox JSON Schema 协议

    Python 中使用 Pydantic 模型时，可以通过 model_json_schema() 生成。
    为了与 TypeBox 兼容，工具参数使用 Protocol 定义，允许任何提供
    JSON Schema 的对象。
    """

    def __call__(self) -> dict[str, Any]:
        """返回 JSON Schema 字典"""
        ...


class Tool(BaseModel):
    """工具定义（用于 LLM function calling）

    与 TypeScript 版本一致，使用 TypeBox 风格的 TSchema。
    在 Python 中，parameters 可以是 Pydantic 模型类，调用时通过
    model_json_schema() 获取 schema。
    """

    name: str
    description: str
    parameters: Any  # TSchema - 实际使用时可以是 Type 或 dict


# ============================================================================
# Token 使用和成本
# ============================================================================


class UsageCost(BaseModel):
    """成本明细（美元）"""

    input: float
    output: float
    cache_read: float
    cache_write: float
    total: float


class Usage(BaseModel):
    """Token 使用和成本

    与当前 TokenUsage 的关键区别：
    - 字段名使用 camelCase（input, output, cacheRead, cacheWrite）
    - 包含 totalTokens 和完整的 cost 结构
    - cost 计算基于百万 token 价格
    """

    input: int
    output: int
    cache_read: int
    cache_write: int
    total_tokens: int
    cost: UsageCost


# ============================================================================
# 流式选项
# ============================================================================


class StreamOptions(BaseModel):
    """流式请求的基础选项"""

    temperature: float | None = None
    max_tokens: int | None = None
    signal: Any | None = None
    api_key: str | None = None
    # 传输方式偏好（仅部分 provider 支持）
    transport: Transport | None = None
    # Prompt 缓存保留偏好（默认: "short"）
    cacheRetention: CacheRetention | None = Field(default="short")
    # Session ID（用于支持 session 缓存的 provider）
    session_id: str | None = None
    # Payload 检查/替换回调
    onPayload: Any | None = None  # Callable
    # 自定义 HTTP 头
    headers: dict[str, str] | None = None
    # 最大重试延迟（毫秒）
    max_retry_delay_ms: int = Field(default=60000)
    # 请求元数据（如 Anthropic 使用 user_id 进行滥用追踪）
    metadata: dict[str, Any] | None = None


class SimpleStreamOptions(StreamOptions):
    """streamSimple() 和 completeSimple() 使用的统一选项"""

    reasoning: ThinkingLevel | None = None
    # 自定义思考等级的 token 预算
    thinking_budgets: ThinkingBudgets | None = None


# ProviderStreamOptions = StreamOptions & Record<string, unknown>
# 在 Python 中使用 StreamOptions 的扩展，允许额外字段
type ProviderStreamOptions = StreamOptions


# ============================================================================
# OpenAI 兼容配置
# ============================================================================


class OpenRouterRouting(BaseModel):
    """OpenRouter 路由偏好"""

    only: list[str] | None = None  # 仅使用的 provider slug 列表
    order: list[str] | None = None  # 按顺序尝试的 provider 列表


class VercelGatewayRouting(BaseModel):
    """Vercel AI Gateway 路由偏好"""

    only: list[str] | None = None
    order: list[str] | None = None


class OpenAICompletionsCompat(BaseModel):
    """OpenAI 兼容 completions API 的配置覆盖"""

    supports_store: bool | None = None
    supports_developer_role: bool | None = None
    supports_reasoning_effort: bool | None = None
    reasoning_effort_map: dict[ThinkingLevel, str] | None = None
    supports_usage_in_streaming: bool = True
    max_tokens_field: Literal["max_completion_tokens", "max_tokens"] | None = None
    requires_tool_result_name: bool | None = None
    requires_assistant_after_tool_result: bool | None = None
    requires_thinking_as_text: bool | None = None
    thinking_format: Literal["openai", "zai", "qwen", "qwen-chat-template"] = "openai"
    open_router_routing: OpenRouterRouting | None = None
    vercel_gateway_routing: VercelGatewayRouting | None = None
    supports_strict_mode: bool = True


class OpenAIResponsesCompat(BaseModel):
    """OpenAI Responses API 的兼容性配置（预留）"""

    pass


# ============================================================================
# 模型定义
# ============================================================================


class ModelCost(BaseModel):
    """模型定价（每百万 token 美元）"""

    input: float
    output: float
    cache_read: float
    cache_write: float


class ModelCapabilities(BaseModel):
    """模型能力标识"""

    reasoning: bool = False
    # 支持的输入类型: "text", "image"
    input: list[Literal["text", "image"]] = Field(default_factory=lambda: ["text"])


class Model(BaseModel):
    """统一模型定义

    与当前 Model 的关键区别：
    - 字段名使用 camelCase
    - api 是泛型参数化的 Api 类型
    - cost 使用嵌套 ModelCost 结构
    - 包含 headers 和 compat 配置
    """

    id: str
    name: str
    api: Api
    provider: Provider
    base_url: str | None = None
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities)
    cost: ModelCost
    context_window: int
    max_tokens: int
    headers: dict[str, str] | None = None
    compat: OpenAICompletionsCompat | OpenAIResponsesCompat | None = None


# ============================================================================
# 上下文
# ============================================================================


class Context(BaseModel):
    """对话上下文

    关键变化：
    - messages 类型改为 Message（而非特定子类型列表）
    - tools 改为 Tool 类型（使用 TypeBox 风格）
    """

    system_prompt: str | None = None
    messages: Sequence[Message]
    tools: Sequence[Tool] | None = None


# ============================================================================
# Provider 配置
# ============================================================================


class ProviderConfig(BaseModel):
    """Provider 配置（用于 Client 初始化）"""

    api_key: str | None = None
    base_url: str | None = None
    timeout: float = 60.0
    max_retries: int = 3


# ============================================================================
# 流式事件协议（Event Protocol）
# ============================================================================

# 这些类型在 stream.py 中定义，这里声明用于类型引用
type AssistantMessageEvent = Any  # 前置声明，实际定义在 stream 模块


# 导入延迟引用以避免循环导入
def get_assistant_message_event_stream_type() -> type:
    """获取 AssistantMessageEventStream 类型（延迟导入）"""
    from ai.stream import AssistantMessageEventStream

    return AssistantMessageEventStream


# ============================================================================
# StreamFunction 类型（在 stream.py 中实际定义）
# ============================================================================

# Contract:
# - 必须返回 AssistantMessageEventStream
# - 调用后，请求/模型/运行时失败应编码在返回的流中，而不是抛出
# - 错误终止必须产生 stopReason 为 "error" 或 "aborted" 的 AssistantMessage
#   并包含 errorMessage，通过流协议发出
