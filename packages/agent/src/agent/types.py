"""
Agent 类型定义 - 对齐 pi-mono TypeScript 实现

提供 Agent 运行时所需的完整类型系统，包括：
- AgentTool: 可执行工具定义，支持自定义工具注入
- AgentEvent: 事件系统，用于监控 Agent 生命周期
- AgentState: 状态管理，跟踪对话历史和运行时状态
- AgentLoopConfig: Loop 配置，控制 Agent 行为

设计原则：
1. 类型安全：所有公共接口都有完整类型注解
2. 可扩展性：通过 Hook 和回调支持自定义行为
3. 事件驱动：通过事件系统实现可观测性

示例：
    >>> from agent.types import AgentContext, AgentState
    >>> context = AgentContext(
    ...     system_prompt="你是一个有帮助的助手",
    ...     messages=[],
    ...     tools=[]
    ... )
    >>> state = AgentState(
    ...     system_prompt="你是一个有帮助的助手",
    ...     model=model,
    ...     messages=[]
    ... )
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Literal, Protocol, TypedDict, runtime_checkable

from ai import AssistantMessageEventStream
from ai.types import (
    AssistantMessage,
    AssistantMessageEvent,
    Context,
    ImageContent,
    Message,
    Model,
    SimpleStreamOptions,
    TextContent,
    ToolCall,
    ToolResultMessage,
)

# ============================================================================
# 自定义消息协议 - 对齐 pi-mono TypeScript 设计
# ============================================================================


class CustomMessage(Protocol):
    """
    自定义消息协议。

    与 pi-mono 的 CustomAgentMessages 接口对齐。
    应用层通过实现此协议来定义自定义消息类型，
    用于在 Agent 消息历史中存储非 LLM 消息（如 UI 状态、进度通知等）。

    协议要求：
        - 必须有 role 属性（str 类型），用于 convert_to_llm 识别消息类型
        - 可以是任何数据结构（dataclass、Pydantic model、dict 等）
        - 完全由应用层定义，Agent 模块不预设任何具体类型

    示例：
        >>> from dataclasses import dataclass
        >>>
        >>> @dataclass
        ... class BashExecutionMessage:
        ...     role: str = "bash_execution"
        ...     command: str = ""
        ...     output: str = ""
        ...
        >>> # 在 convert_to_llm 中处理
        >>> def my_convert(messages: list[AgentMessage]) -> list[Message]:
        ...     for msg in messages:
        ...         if getattr(msg, "role", None) == "bash_execution":
        ...             # 转换为 LLM 能理解的格式
        ...             return [UserMessage(content=[TextContent(text=msg.output)])]
    """

    @property
    def role(self) -> str:
        """
        消息角色标识符。

        用于 convert_to_llm 识别消息类型。
        使用非标准 role 值（非 user/assistant/toolResult）表示自定义消息。

        示例值：
            - "bash_execution": Bash 命令执行结果
            - "progress": 进度通知
            - "notification": 系统通知
        """
        ...


# ============================================================================
# AgentMessage - 联合类型（支持自定义消息）
# ============================================================================

type AgentMessage = Message | CustomMessage
"""
Agent 消息类型 - 支持标准消息和自定义消息。

与 pi-mono 的 AgentMessage = Message | CustomAgentMessages[keyof CustomAgentMessages] 对齐。

类型组成：
    - Message: LLM 兼容的标准消息（user/assistant/toolResult）
    - CustomMessage: 应用层定义的自定义消息（通过 Protocol 约束）

约束：
    - 自定义消息必须有 role 属性（str 类型）
    - 标准 role: "user" | "assistant" | "toolResult"
    - 非标准 role 被视为自定义消息，需要 convert_to_llm 处理
"""


# ============================================================================
# 消息转换函数类型
# ============================================================================

type ConvertToLlm = Callable[[list[AgentMessage]], Awaitable[list[Message]]]
"""
消息转换函数类型。

将 AgentMessage 列表（可能包含自定义消息）转换为 LLM 兼容的 Message 列表。

契约：
    - 必须处理所有可能的 AgentMessage 类型
    - 标准消息（user/assistant/toolResult）直接通过
    - 自定义消息必须转换或过滤
    - 不得抛出异常，错误时返回安全回退值

示例：
    >>> async def convert_to_llm(messages: list[AgentMessage]) -> list[Message]:
    ...     result = []
    ...     for msg in messages:
    ...         # 标准消息直接通过
    ...         if isinstance(msg, Message) and msg.role in ("user", "assistant", "toolResult"):
    ...             result.append(msg)
    ...             continue
    ...
    ...         # 处理自定义消息
    ...         if getattr(msg, "role", None) == "bash_execution":
    ...             result.append(UserMessage(content=[TextContent(text=msg.output)]))
    ...             continue
    ...
    ...         # 未知的自定义消息：跳过
    ...         logger.warning(f"Unknown message role: {getattr(msg, 'role', 'unknown')}")
    ...
    ...     return result
"""


# ============================================================================
# 基础类型
# ============================================================================

type ToolExecutionMode = Literal["sequential", "parallel"]
"""工具执行模式

- "sequential": 顺序执行，每个工具调用完成后再执行下一个
  适用场景：工具之间有依赖关系，需要按顺序执行

- "parallel": 并行执行，所有工具调用同时启动
  适用场景：工具之间相互独立，可以提高执行效率

默认值为 "parallel"

示例：
    >>> # 顺序执行（有依赖关系）
    >>> config.tool_execution = "sequential"
    >>> # 先查询用户信息，再根据用户ID查询订单

    >>> # 并行执行（相互独立）
    >>> config.tool_execution = "parallel"
    >>> # 同时查询天气、新闻、股票价格
"""

type ThinkingLevel = Literal["off", "minimal", "low", "medium", "high", "xhigh"]
"""思考等级 - 控制 LLM 的推理深度

- "off": 关闭思考模式，直接生成回答
- "minimal": 最小化思考，仅处理简单问题
- "low": 低深度思考，适合日常对话
- "medium": 中等深度思考，平衡质量与速度（默认）
- "high": 深度思考，适合复杂推理任务
- "xhigh": 极高深度思考，适合数学证明、代码调试等

注意：并非所有模型都支持所有等级，具体取决于 provider 实现

示例：
    >>> agent.set_thinking_level("high")  # 复杂推理任务
    >>> await agent.prompt("证明勾股定理")

    >>> agent.set_thinking_level("off")   # 简单问答
    >>> await agent.prompt("今天星期几？")
"""

type StreamFn = Callable[
    [
        Model,  # 模型
        Context,  # 上下文
        SimpleStreamOptions | None,  # 选项
    ],
    Awaitable[AssistantMessageEventStream],
]
"""流式调用函数类型

与 ai.stream_simple 兼容的函数签名，用于自定义流式调用逻辑。

参数：
    model: 要使用的模型实例
    context: LLM 上下文，包含消息和工具
    options: 流式选项，包括 temperature、max_tokens 等

返回：
    AssistantMessageEventStream: 事件流，包含 text_delta、tool_call 等事件

契约：
    - 不得抛出异常，错误应编码在返回的流中
    - 必须通过 stop_reason="error" 或 "aborted" 报告失败
    - 支持通过 signal 参数取消执行

示例：
    >>> async def custom_stream_fn(model, context, options):
    ...     # 自定义流式逻辑
    ...     stream = provider.stream_simple(model, context, options)
    ...     return stream
    >>>
    >>> agent = Agent(AgentOptions(stream_fn=custom_stream_fn))
"""


# ============================================================================
# AgentTool - 可执行工具
# ============================================================================


@runtime_checkable
class AgentTool(Protocol):
    """Agent 工具协议 - 可执行工具的标准接口

    实现此协议的对象可以被 Agent 调用执行。工具在以下场景触发：
    1. LLM 生成 toolCall 内容块
    2. Agent Loop 解析 toolCall
    3. 查找匹配的 AgentTool
    4. 调用 execute() 方法执行

    属性：
        name: 工具唯一标识符，用于 LLM 识别和调用
        description: 工具功能描述，帮助 LLM 理解何时使用该工具
        parameters: JSON Schema 格式的参数定义，用于验证输入
        label: 人类可读的标签，用于 UI 显示

    示例：
        >>> class WeatherTool:
        ...     name = "get_weather"
        ...     description = "获取指定城市的天气信息"
        ...     parameters = {
        ...         "type": "object",
        ...         "properties": {
        ...             "city": {"type": "string", "description": "城市名称"}
        ...         },
        ...         "required": ["city"]
        ...     }
        ...     label = "天气查询"
        ...
        ...     async def execute(self, tool_call_id, params, signal, on_update):
        ...         city = params["city"]
        ...         weather = await fetch_weather(city)
        ...         return AgentToolResult(
        ...             content=[TextContent(text=f"{city}天气：{weather}")],
        ...             details={"city": city, "weather": weather}
        ...         )
        >>>
        >>> agent.set_tools([WeatherTool()])
    """

    name: str
    """工具唯一标识符

    命名规范：
    - 使用小写字母和下划线
    - 简洁明了，如 "get_weather", "create_file"
    - 避免与内置工具冲突
    """

    description: str
    """工具功能描述

    这是 LLM 理解工具用途的关键信息。好的描述应该：
    - 说明工具的作用
    - 说明适用场景
    - 说明返回值的格式

    示例：
        "获取指定城市的当前天气信息，包括温度、湿度和天气状况"
    """

    parameters: Any
    """参数定义（JSON Schema 格式）

    必须符合 JSON Schema 规范，用于：
    1. LLM 生成符合 schema 的参数
    2. 运行时验证输入数据
    3. 提供类型提示和自动补全

    示例：
        {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，如 '北京'"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "温度单位"
                }
            },
            "required": ["city"]
        }
    """

    label: str
    """人类可读标签

    用于 UI 显示，如工具列表、执行日志等。
    示例："天气查询", "文件写入"
    """

    async def execute(
        self,
        tool_call_id: str,
        params: dict[str, Any],
        signal: AbortSignal | None = None,
        on_update: AgentToolUpdateCallback | None = None,
    ) -> AgentToolResult[Any]:
        """执行工具

        这是工具的核心方法，由 Agent Loop 在需要时调用。

        参数：
            tool_call_id: 本次工具调用的唯一标识符
                用于关联 toolCall 和 toolResult 消息
            params: 经过 JSON Schema 验证后的参数
                类型和必填项都已验证，直接使用即可
            signal: 取消信号（可选）
                用于支持长时间运行的工具被取消
                检查方式：if signal and signal.cancelled: raise CancelledError()
            on_update: 进度回调（可选）
                用于长时间运行的工具报告进度
                调用方式：on_update(AgentToolResult(...))

        返回：
            AgentToolResult: 工具执行结果
                content: 文本或图像内容，用于 LLM 上下文
                details: 详细数据，可用于后续处理

        异常：
            不应抛出异常。所有错误应封装在 AgentToolResult 中，
            通过 content 报告错误信息。

        示例：
            >>> async def execute(self, tool_call_id, params, signal, on_update):
            ...     try:
            ...         result = await self._do_work(params)
            ...         return AgentToolResult(
            ...             content=[TextContent(text=f"成功：{result}")],
            ...             details={"status": "success", "data": result}
            ...         )
            ...     except Exception as e:
            ...         return AgentToolResult(
            ...             content=[TextContent(text=f"错误：{str(e)}")],
            ...             details={"status": "error", "error": str(e)}
            ...         )
        """
        ...


type AbortSignal = Any
"""取消信号类型

实际为 asyncio.CancelledError 或其他取消机制。
工具应定期检查此信号，优雅地终止执行。

示例：
    >>> async def execute(self, tool_call_id, params, signal, on_update):
    ...     for i in range(100):
    ...         if signal and getattr(signal, 'cancelled', False):
    ...             raise asyncio.CancelledError()
    ...         await do_step(i)
"""


type AgentToolUpdateCallback = Callable[[AgentToolResult[Any]], None]
"""工具进度回调函数类型

用于长时间运行的工具报告中间进度。

参数：
    partial_result: 部分结果
        可以多次调用，每次提供最新进度

示例：
    >>> async def execute(self, tool_call_id, params, signal, on_update):
    ...     for i, chunk in enumerate(large_data):
    ...         processed = process_chunk(chunk)
    ...         if on_update:
    ...             on_update(AgentToolResult(
    ...                 content=[TextContent(text=f"已处理 {i+1}/{len(large_data)}")],
    ...                 details={"progress": (i+1) / len(large_data)}
    ...             ))
"""


# ============================================================================
# AgentToolResult - 工具执行结果
# ============================================================================


class AgentToolResult[TDetails]:
    """工具执行结果

    封装工具执行的输出，包含展示内容和详细数据。

    属性：
        content: 展示内容，用于 LLM 上下文和 UI 显示
            可以是 TextContent 或 ImageContent
        details: 详细数据，任意类型
            用于后续处理，不直接展示给 LLM

    示例：
        >>> # 成功结果
        >>> result = AgentToolResult(
        ...     content=[TextContent(text="北京天气：晴天，25°C")],
        ...     details={
        ...         "city": "北京",
        ...         "temperature": 25,
        ...         "condition": "sunny"
        ...     }
        ... )

        >>> # 错误结果
        >>> error_result = AgentToolResult(
        ...     content=[TextContent(text="错误：城市不存在")],
        ...     details={"error": "CityNotFound", "city": "不存在的城市"}
        ... )

        >>> # 图像结果
        >>> image_result = AgentToolResult(
        ...     content=[ImageContent(mime_type="image/png", data=base64_data)],
        ...     details={"chart_type": "bar", "data_source": "sales_q3"}
        ... )
    """

    content: Sequence[TextContent | ImageContent]
    """展示内容列表

    用于：
    1. 添加到 LLM 上下文作为 toolResult 消息
    2. 在 UI 中展示执行结果

    注意：通常只有一个元素，但复杂工具可能返回多个内容块
    """

    details: TDetails
    """详细数据

    任意类型，用于：
    1. 后续处理（如保存到数据库）
    2. 调试和日志记录
    3. afterToolCall hook 的处理

    注意：此数据不直接发送给 LLM，仅用于程序内部
    """

    def __init__(
        self,
        content: Sequence[TextContent | ImageContent],
        details: TDetails,
    ) -> None:
        """初始化工具结果

        参数：
            content: 展示内容列表
            details: 详细数据
        """
        self.content = content
        self.details = details


# ============================================================================
# AgentToolCall - 工具调用内容块
# ============================================================================

type AgentToolCall = ToolCall
"""工具调用内容块

LLM 生成的工具调用请求，包含：
- id: 唯一标识符
- name: 工具名称
- arguments: 参数（JSON 对象）

示例：
    >>> tool_call = ToolCall(
    ...     id="call_123",
    ...     name="get_weather",
    ...     arguments={"city": "北京"}
    ... )
"""


# ============================================================================
# Hook 结果类型
# ============================================================================


class BeforeToolCallResult:
    """beforeToolCall 钩子返回值

    用于在工具执行前进行拦截或修改。

    属性：
        block: 是否阻止执行
            True: 阻止执行，返回错误结果
            False: 允许正常执行（默认）
        reason: 阻止原因（可选）
            当 block=True 时，此原因会显示在错误结果中

    契约：
        - 返回 block=True 时，工具不会执行
        - 错误结果格式：{"type": "text", "text": reason}
        - 可用于权限检查、参数验证等

    示例：
        >>> async def before_tool_call(ctx, signal):
        ...     # 检查用户权限
        ...     if ctx.tool_call.name == "delete_file":
        ...         if not user_has_permission("write"):
        ...             return BeforeToolCallResult(
        ...                 block=True,
        ...                 reason="没有删除文件的权限"
        ...             )
        ...     return None  # 允许执行
    """

    block: bool
    """是否阻止工具执行"""

    reason: str | None
    """阻止原因

    当 block=True 时显示给用户和 LLM 的消息
    """

    def __init__(
        self,
        block: bool = False,
        reason: str | None = None,
    ) -> None:
        """初始化钩子结果

        参数：
            block: 是否阻止执行，默认 False
            reason: 阻止原因，可选
        """
        self.block = block
        self.reason = reason


class AfterToolCallResult:
    """afterToolCall 钩子返回值

    用于在工具执行后修改结果。

    合并语义（字段级替换）：
    - content: 如果提供，完全替换结果内容
    - details: 如果提供，完全替换详细数据
    - is_error: 如果提供，替换错误标志

    注意：不提供字段保持原值，不支持深度合并

    适用场景：
    - 结果格式化
    - 敏感信息过滤
    - 错误重分类

    示例：
        >>> async def after_tool_call(ctx, signal):
        ...     # 过滤敏感信息
        ...     original_content = ctx.result.content[0].text
        ...     filtered = original_content.replace("密码：xxx", "密码：***")
        ...
        ...     return AfterToolCallResult(
        ...         content=[TextContent(text=filtered)],
        ...         details={**ctx.result.details, "filtered": True}
        ...     )
    """

    content: Sequence[TextContent | ImageContent] | None
    """替换后的内容"""

    details: Any | None
    """替换后的详细数据"""

    is_error: bool | None
    """替换后的错误标志"""

    def __init__(
        self,
        content: Sequence[TextContent | ImageContent] | None = None,
        details: Any | None = None,
        is_error: bool | None = None,
    ) -> None:
        """初始化钩子结果

        参数：
            content: 新内容，None 表示不替换
            details: 新详细数据，None 表示不替换
            is_error: 新错误标志，None 表示不替换
        """
        self.content = content
        self.details = details
        self.is_error = is_error


# ============================================================================
# Hook 上下文
# ============================================================================


class BeforeToolCallContext:
    """beforeToolCall 钩子上下文

    提供工具执行前的完整上下文信息。

    属性：
        assistant_message: 请求工具调用的助手消息
        tool_call: 原始工具调用块
        args: 验证后的参数
        context: 当前 Agent 上下文

    示例：
        >>> async def before_hook(ctx: BeforeToolCallContext, signal):
        ...     print(f"工具：{ctx.tool_call.name}")
        ...     print(f"参数：{ctx.args}")
        ...     print(f"对话历史：{len(ctx.context.messages)} 条")
    """

    assistant_message: AssistantMessage
    """请求工具调用的助手消息

    包含完整的助手响应，包括所有内容块
    """

    tool_call: AgentToolCall
    """原始工具调用块"""

    args: Any
    """验证后的参数

    已经过 JSON Schema 验证，类型安全
    """

    context: AgentContext
    """当前 Agent 上下文

    包含系统提示、消息历史和可用工具
    """

    def __init__(
        self,
        assistant_message: AssistantMessage,
        tool_call: AgentToolCall,
        args: Any,
        context: AgentContext,
    ) -> None:
        """初始化上下文"""
        self.assistant_message = assistant_message
        self.tool_call = tool_call
        self.args = args
        self.context = context


class AfterToolCallContext:
    """afterToolCall 钩子上下文

    提供工具执行后的完整上下文信息。

    属性：
        assistant_message: 请求工具调用的助手消息
        tool_call: 原始工具调用块
        args: 验证后的参数
        result: 执行后的原始结果
        is_error: 当前是否标记为错误
        context: 当前 Agent 上下文

    示例：
        >>> async def after_hook(ctx: AfterToolCallContext, signal):
        ...     if ctx.is_error:
        ...         # 错误处理逻辑
        ...         return AfterToolCallResult(
        ...             content=[TextContent(text="操作失败，请重试")]
        ...         )
    """

    assistant_message: AssistantMessage
    """请求工具调用的助手消息"""

    tool_call: AgentToolCall
    """原始工具调用块"""

    args: Any
    """验证后的参数"""

    result: AgentToolResult[Any]
    """执行后的原始结果

    尚未应用 afterToolCall 覆盖
    """

    is_error: bool
    """当前是否标记为错误"""

    context: AgentContext
    """当前 Agent 上下文"""

    def __init__(
        self,
        assistant_message: AssistantMessage,
        tool_call: AgentToolCall,
        args: Any,
        result: AgentToolResult[Any],
        is_error: bool,
        context: AgentContext,
    ) -> None:
        """初始化上下文"""
        self.assistant_message = assistant_message
        self.tool_call = tool_call
        self.args = args
        self.result = result
        self.is_error = is_error
        self.context = context


# ============================================================================
# AgentContext - Agent 上下文
# ============================================================================


class AgentContext:
    """Agent 上下文 - 单次调用的完整环境

    包含执行所需的所有信息：系统提示、对话历史、可用工具。
    在每次 prompt() 调用时构建，传递给 Agent Loop。

    属性：
        system_prompt: 系统提示词
        messages: 消息历史
        tools: 可用工具列表

    示例：
        >>> context = AgentContext(
        ...     system_prompt="你是一个编程助手",
        ...     messages=[
        ...         UserMessage(text="帮我写个 Python 函数"),
        ...         AssistantMessage(content=[TextContent(text="好的，请问需要什么功能？")])
        ...     ],
        ...     tools=[FileReadTool(), FileWriteTool()]
        ... )
    """

    system_prompt: str
    """系统提示词

    定义助手的行为准则、能力范围、输出格式等
    """

    messages: list[AgentMessage]
    """消息历史列表

    包含 user、assistant、toolResult 消息的完整对话历史
    """

    tools: list[AgentTool] | None
    """可用工具列表

    None 表示无工具，空列表 [] 也表示无工具
    """

    def __init__(
        self,
        system_prompt: str = "",
        messages: list[AgentMessage] | None = None,
        tools: list[AgentTool] | None = None,
    ) -> None:
        """初始化上下文

        参数：
            system_prompt: 系统提示词，默认空字符串
            messages: 消息列表，默认空列表
            tools: 工具列表，默认 None
        """
        self.system_prompt = system_prompt
        self.messages = messages or []
        self.tools = tools


# ============================================================================
# AgentState - Agent 状态
# ============================================================================


class AgentState:
    """Agent 运行时状态

    跟踪 Agent 的完整运行时状态，包括：
    - 配置状态：system_prompt、model、tools
    - 对话状态：messages
    - 运行状态：is_streaming、stream_message
    - 工具状态：pending_tool_calls
    - 错误状态：error

    状态持久化：
    可以通过保存此对象实现会话恢复：
    >>> saved_state = agent.state
    >>> # ... 之后恢复
    >>> agent = Agent(AgentOptions(initial_state=saved_state))

    属性：
        system_prompt: 当前系统提示
        model: 当前使用的模型
        thinking_level: 思考等级
        tools: 可用工具列表
        messages: 消息历史
        is_streaming: 是否正在流式输出
        stream_message: 当前流式消息（如果有）
        pending_tool_calls: 待执行的工具调用ID
        error: 错误信息（如果有）

    示例：
        >>> state = AgentState(
        ...     system_prompt="你是一个有帮助的助手",
        ...     model=kimi_model,
        ...     messages=[],
        ...     is_streaming=False
        ... )
    """

    system_prompt: str
    """当前系统提示"""

    model: Model
    """当前使用的模型实例"""

    thinking_level: ThinkingLevel
    """当前思考等级"""

    tools: list[AgentTool]
    """可用工具列表"""

    messages: list[AgentMessage]
    """消息历史列表"""

    is_streaming: bool
    """是否正在流式输出

    True 表示 LLM 正在生成回复，此时不应发送新 prompt
    """

    stream_message: AgentMessage | None
    """当前流式消息

    is_streaming=True 时，表示正在生成的部分消息
    """

    pending_tool_calls: set[str]
    """待执行的工具调用ID集合

    用于跟踪哪些工具调用正在执行中
    """

    error: str | None
    """错误信息

    上一次执行的错误信息，成功后应清除
    """

    def __init__(
        self,
        system_prompt: str = "",
        model: Model | None = None,
        thinking_level: ThinkingLevel = "off",
        tools: list[AgentTool] | None = None,
        messages: list[AgentMessage] | None = None,
        is_streaming: bool = False,
        stream_message: AgentMessage | None = None,
        pending_tool_calls: set[str] | None = None,
        error: str | None = None,
    ) -> None:
        """初始化状态

        参数：
            system_prompt: 系统提示
            model: 模型实例
            thinking_level: 思考等级，默认 "off"
            tools: 工具列表，默认空列表
            messages: 消息列表，默认空列表
            is_streaming: 是否流式中，默认 False
            stream_message: 流式消息，默认 None
            pending_tool_calls: 待执行工具ID，默认空集合
            error: 错误信息，默认 None
        """
        self.system_prompt = system_prompt
        self.model = model  # type: ignore[assignment]
        self.thinking_level = thinking_level
        self.tools = tools or []
        self.messages = messages or []
        self.is_streaming = is_streaming
        self.stream_message = stream_message
        self.pending_tool_calls = pending_tool_calls or set()
        self.error = error


# ============================================================================
# AgentEvent - Agent 事件
# ============================================================================

# 引入 AssistantMessageEvent 用于 message_update 事件
from ai.types import AssistantMessageEvent


class AgentStartEvent(TypedDict):
    """Agent 开始处理事件"""

    type: Literal["agent_start"]


class AgentEndEvent(TypedDict):
    """Agent 处理完成事件"""

    type: Literal["agent_end"]
    messages: list[AgentMessage]


class TurnStartEvent(TypedDict):
    """Turn 开始事件 - 一个 Turn 是助手回复 + 工具调用/结果"""

    type: Literal["turn_start"]


class TurnEndEvent(TypedDict):
    """Turn 结束事件"""

    type: Literal["turn_end"]
    message: AgentMessage
    tool_results: list[ToolResultMessage]


class MessageStartEvent(TypedDict):
    """消息开始生成事件"""

    type: Literal["message_start"]
    message: AgentMessage


class MessageUpdateEvent(TypedDict):
    """消息内容更新事件（流式）- 仅对助手消息发射"""

    type: Literal["message_update"]
    message: AgentMessage
    assistant_message_event: AssistantMessageEvent


class MessageEndEvent(TypedDict):
    """消息生成完成事件"""

    type: Literal["message_end"]
    message: AgentMessage


class ToolExecutionStartEvent(TypedDict):
    """工具开始执行事件"""

    type: Literal["tool_execution_start"]
    tool_call_id: str
    tool_name: str
    args: Any


class ToolExecutionUpdateEvent(TypedDict):
    """工具执行更新事件"""

    type: Literal["tool_execution_update"]
    tool_call_id: str
    tool_name: str
    args: Any
    partial_result: Any


class ToolExecutionEndEvent(TypedDict):
    """工具执行完成事件"""

    type: Literal["tool_execution_end"]
    tool_call_id: str
    tool_name: str
    result: Any
    is_error: bool


type AgentEvent = (
    AgentStartEvent
    | AgentEndEvent
    | TurnStartEvent
    | TurnEndEvent
    | MessageStartEvent
    | MessageUpdateEvent
    | MessageEndEvent
    | ToolExecutionStartEvent
    | ToolExecutionUpdateEvent
    | ToolExecutionEndEvent
)
"""Agent 事件类型

事件系统用于监控 Agent 的生命周期和状态变化。

事件类型：
    agent_start: Agent 开始处理
    agent_end: Agent 处理结束
    turn_start: 新的 Turn 开始
    turn_end: Turn 结束
    message_start: 消息开始生成
    message_update: 消息内容更新（流式）
    message_end: 消息生成完成
    tool_execution_start: 工具开始执行
    tool_execution_update: 工具执行更新
    tool_execution_end: 工具执行完成

事件格式：
    所有事件都是字典，包含 type 字段：
    {"type": "message_end", "message": AssistantMessage(...)}

订阅方式：
    >>> def on_event(event):
    ...     if event.get("type") == "message_end":
    ...         print(f"消息：{event.get('message')}")
    >>>
    >>> agent.subscribe(on_event)

用途：
    - UI 更新：实时显示生成内容
    - 日志记录：追踪执行流程
    - 状态同步：保存对话历史
    - 调试分析：监控性能指标
"""


# ============================================================================
# AgentLoopConfig - Loop 配置
# ============================================================================

type BeforeToolCallHook = Callable[
    [BeforeToolCallContext, AbortSignal | None],
    Awaitable[BeforeToolCallResult | None],
]
"""beforeToolCall 钩子函数类型

在工具执行前调用，可用于权限检查、参数验证等。

参数：
    ctx: BeforeToolCallContext - 工具调用上下文
    signal: AbortSignal - 取消信号

返回：
    BeforeToolCallResult | None
    - None: 允许执行
    - BeforeToolCallResult(block=True): 阻止执行
"""

type AfterToolCallHook = Callable[
    [AfterToolCallContext, AbortSignal | None],
    Awaitable[AfterToolCallResult | None],
]
"""afterToolCall 钩子函数类型

在工具执行后调用，可用于结果修改、日志记录等。

参数：
    ctx: AfterToolCallContext - 工具调用上下文
    signal: AbortSignal - 取消信号

返回：
    AfterToolCallResult | None
    - None: 使用原始结果
    - AfterToolCallResult: 覆盖指定字段
"""


class AgentLoopConfig(SimpleStreamOptions):
    """Agent Loop 配置

    继承 SimpleStreamOptions 以获得流式选项支持（temperature、max_tokens 等）。

    配置分类：
    1. 核心配置：model、convert_to_llm
    2. 上下文处理：transform_context
    3. 认证：get_api_key
    4. 消息队列：get_steering_messages、get_follow_up_messages
    5. 工具执行：tool_execution、before_tool_call、after_tool_call

    示例：
        >>> config = AgentLoopConfig(
        ...     model=kimi_model,
        ...     convert_to_llm=custom_converter,
        ...     tool_execution="parallel",
        ...     temperature=0.7,
        ...     max_tokens=2000
        ... )
    """

    model: Model | None = None
    """使用的模型实例

    必须提供有效的 Model 实例，用于 LLM 调用
    """

    convert_to_llm: ConvertToLlm | None = None
    """消息转换函数

    将 AgentMessage[] 转换为 LLM 兼容的 Message[]。

    默认实现：
        过滤出 role 为 user/assistant/toolResult 的消息，
        忽略所有自定义消息。

    自定义场景：
        - 处理自定义消息：将非标准消息转换为 LLM 可理解格式
        - 上下文压缩：截断过长的历史
        - 格式转换：修改消息格式
        - 附件处理：转换图像、文件等

    示例：
        >>> async def custom_convert(messages: list[AgentMessage]) -> list[Message]:
        ...     result = []
        ...     for msg in messages:
        ...         if isinstance(msg, Message) and msg.role in ("user", "assistant", "toolResult"):
        ...             result.append(msg)
        ...         elif getattr(msg, "role", None) == "bash_execution":
        ...             # 转换自定义消息
        ...             result.append(UserMessage(content=[TextContent(text=msg.output)]))
        ...     return result
    """

    transform_context: Callable[[list[AgentMessage], Any], Awaitable[list[AgentMessage]]] | None = (
        None
    )
    """上下文转换函数（可选）

    在 convert_to_llm 之前应用，用于上下文修剪、注入外部上下文等。

    执行顺序：
        messages → transform_context → convert_to_llm → LLM

    适用场景：
        - 上下文修剪：Token 数超过限制时删除旧消息
        - 外部上下文：注入检索到的文档
        - 摘要生成：将长历史替换为摘要

    示例：
        >>> async def prune_context(messages, signal):
        ...     total_tokens = estimate_tokens(messages)
        ...     if total_tokens > 8000:
        ...         return messages[-5:]  # 只保留最近 5 条
        ...     return messages
    """

    get_api_key: Callable[[str], Awaitable[str | None]] | None = None
    """API Key 动态获取函数

    每次 LLM 调用前执行，支持动态令牌（如 OAuth）。

    参数：
        provider: 提供商名称，如 "kimi", "openai"

    返回：
        API Key 字符串，或 None（使用环境变量）

    示例：
        >>> async def get_key(provider):
        ...     if provider == "kimi":
        ...         return await refresh_oauth_token()
        ...     return os.getenv("KIMI_API_KEY")
    """

    get_steering_messages: Callable[[], Awaitable[list[AgentMessage]]] | None = None
    """Steering 消息获取函数

    在每次 Turn 开始时调用，获取 steering 消息。
    Steering 消息会在当前 Turn 中优先于 LLM 响应处理。

    用途：
        - 用户中断：插入新指令
        - 系统干预：注入系统消息

    注意：
        - 返回的消息会被添加到上下文
        - 执行后清空队列
    """

    get_follow_up_messages: Callable[[], Awaitable[list[AgentMessage]]] | None = None
    """Follow-up 消息获取函数

    在 Turn 结束时调用，获取 follow-up 消息。
    如果有 follow-up 消息，会启动新的 Turn 继续对话。

    用途：
        - 自动追问：根据上下文生成后续问题
        - 任务链：分解复杂任务为多个步骤

    注意：
        - 返回空列表表示没有 follow-up
        - 会触发新的 Agent Loop 迭代
    """

    tool_execution: ToolExecutionMode = "parallel"
    """工具执行模式，默认并行"""

    before_tool_call: BeforeToolCallHook | None = None
    """工具执行前钩子

    在工具执行前调用，可用于权限检查、参数验证。

    示例：
        >>> async def before_hook(ctx, signal):
        ...     if ctx.tool_call.name == "delete_file":
        ...         # 检查权限
        ...         if not user_can_delete(ctx.args["path"]):
        ...             return BeforeToolCallResult(block=True, reason="权限不足")
        ...     return None
    """

    after_tool_call: AfterToolCallHook | None = None
    """工具执行后钩子

    在工具执行后调用，可用于结果修改、日志记录。

    示例：
        >>> async def after_hook(ctx, signal):
        ...     # 记录工具调用日志
        ...     log_tool_call(ctx.tool_call.name, ctx.result)
        ...     return None
    """
