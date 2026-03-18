class AgentLoopConfig(SimpleStreamOptions):
    """Agent Loop 配置

    继承 SimpleStreamOptions 以获得流式选项支持
    """

    model: Model | None = None

    # 消息转换函数
    convert_to_llm: Callable[[list[AgentMessage]], Awaitable[list[Message]]] | None = None

    # 上下文转换（可选）
    transform_context: Callable[[list[AgentMessage], Any], Awaitable[list[AgentMessage]]] | None = (
        None
    )

    # API Key 动态获取
    get_api_key: Callable[[str], Awaitable[str | None]] | None = None

    # Steering 消息获取
    get_steering_messages: Callable[[], Awaitable[list[AgentMessage]]] | None = None

    # Follow-up 消息获取
    get_follow_up_messages: Callable[[], Awaitable[list[AgentMessage]]] | None = None

    # 工具执行模式
    tool_execution: ToolExecutionMode = "parallel"

    # 工具调用钩子
    before_tool_call: BeforeToolCallHook | None = None
    after_tool_call: AfterToolCallHook | None = None
