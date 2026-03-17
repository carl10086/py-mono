# AI 模块源码深度解析

> 目标：理解 `packages/ai` 的架构设计、核心机制和实现细节

---

## 第一步：核心类型系统

### 1.1 基础标识类型

```typescript
export type KnownApi =
  | "openai-completions"
  | "mistral-conversations"
  | "openai-responses"
  | "azure-openai-responses"
  | "openai-codex-responses"
  | "anthropic-messages"
  | "bedrock-converse-stream"
  | "google-generative-ai"
  | "google-gemini-cli"
  | "google-vertex";

export type Api = KnownApi | (string & {});
export type Provider = KnownProvider | string;
```

**设计要点**：
- 使用联合类型确保类型安全
- `(string & {})` 技巧允许自定义值同时保留类型提示

### 1.2 内容块系统

统一所有 LLM 返回的内容格式：

| 类型 | 用途 | 关键字段 |
|------|------|---------|
| `TextContent` | 文本内容 | `type: "text"`, `text: string` |
| `ThinkingContent` | 推理过程 | `type: "thinking"`, `redacted?: boolean` |
| `ImageContent` | 图像数据 | `type: "image"`, `data: base64` |
| `ToolCall` | 工具调用 | `type: "toolCall"`, `id`, `name`, `arguments` |

**为什么这样设计？**
- OpenAI、Anthropic、Google 的原始格式不同
- 都可以归约为这 4 种基本块
- 上层代码只需处理统一格式

### 1.3 Message 类型层次

```typescript
UserMessage          → 用户输入
├── role: "user"
├── content: string | (TextContent | ImageContent)[]
└── timestamp: number

AssistantMessage     → AI 响应
├── role: "assistant"
├── content: (TextContent | ThinkingContent | ToolCall)[]
├── api: Api                    # 来自哪个 API
├── provider: Provider          # 来自哪个 Provider
├── model: string               # 具体模型 ID
├── usage: Usage                # Token 使用情况
├── stopReason: StopReason      # 停止原因
└── errorMessage?: string       # 错误信息

ToolResultMessage    → 工具执行结果
├── role: "toolResult"
├── toolCallId: string          # 对应 ToolCall.id
├── toolName: string
├── content: (TextContent | ImageContent)[]
├── details?: TDetails          # 泛型扩展信息
└── isError: boolean
```

### 1.4 事件协议设计

流式处理的核心事件类型：

```typescript
AssistantMessageEvent =
  | { type: "start", partial: AssistantMessage }
  | { type: "text_start", contentIndex: number, partial: AssistantMessage }
  | { type: "text_delta", contentIndex: number, delta: string, partial: AssistantMessage }
  | { type: "text_end", contentIndex: number, content: string, partial: AssistantMessage }
  | { type: "thinking_start", contentIndex: number, partial: AssistantMessage }
  | { type: "thinking_delta", contentIndex: number, delta: string, partial: AssistantMessage }
  | { type: "thinking_end", contentIndex: number, content: string, partial: AssistantMessage }
  | { type: "toolcall_start", contentIndex: number, partial: AssistantMessage }
  | { type: "toolcall_delta", contentIndex: number, delta: string, partial: AssistantMessage }
  | { type: "toolcall_end", contentIndex: number, toolCall: ToolCall, partial: AssistantMessage }
  | { type: "done", reason: StopReason, message: AssistantMessage }
  | { type: "error", reason: StopReason, error: AssistantMessage }
```

**生命周期**：
```
start → text_start → text_delta → ... → text_end → toolcall_start → ... → toolcall_end → done
```

**关键设计**：每个事件携带 `partial: AssistantMessage`
- UI 层可以随时渲染最新状态
- 无需累积 deltas 再计算

### 1.5 Model<TApi> 接口

```typescript
export interface Model<TApi extends Api> {
  id: string;
  name: string;
  api: TApi;                      # 泛型绑定
  provider: Provider;
  baseUrl: string;
  reasoning: boolean;             # 是否支持推理
  input: ("text" | "image")[];    # 支持的输入类型
  cost: {
    input: number;                # 每百万 token 成本（美元）
    output: number;
    cacheRead: number;
    cacheWrite: number;
  };
  contextWindow: number;
  maxTokens: number;
  compat?: TApi extends "openai-completions"
    ? OpenAICompletionsCompat     # 根据 API 类型自动推断
    : ...;
}
```

**泛型的好处**：`Model<"openai-completions">` 自动获得 `compat: OpenAICompletionsCompat`

---

## 第二步：事件流系统

### 2.1 类结构

```typescript
class EventStream<T, R = T> implements AsyncIterable<T> {
  private queue: T[] = [];                                       # 积压事件队列
  private waiting: ((value: IteratorResult<T>) => void)[] = [];  # 等待消费者的回调
  private done = false;                                          # 流是否已结束
  private finalResultPromise: Promise<R>;                        # 最终结果 Promise
  private resolveFinalResult!: (result: R) => void;              # 延迟初始化的 resolve
}
```

**核心设计**：`queue` 和 `waiting` 互斥
- 有积压事件 → 存 queue
- 有等待消费者 → 存 waiting
- 两者不会同时有数据

### 2.2 构造函数

```typescript
constructor(
  private isComplete: (event: T) => boolean,     # 判断是否是结束事件
  private extractResult: (event: T) => R,        # 从结束事件提取结果
) {
  this.finalResultPromise = new Promise((resolve) => {
    this.resolveFinalResult = resolve;
  });
}
```

**延迟初始化模式**：`resolveFinalResult` 在构造时赋值，用 `!` 告诉编译器"相信我"。

### 2.3 push 方法

```typescript
push(event: T): void {
  if (this.done) return;

  // 检查是否是结束事件
  if (this.isComplete(event)) {
    this.done = true;
    this.resolveFinalResult(this.extractResult(event));
  }

  // 交付策略：优先给等待中的消费者
  const waiter = this.waiting.shift();
  if (waiter) {
    waiter({ value: event, done: false });
  } else {
    this.queue.push(event);
  }
}
```

**执行顺序**：
1. 检查结束事件 → 设置 `done` 标志
2. 尝试交付给等待者
3. 无人等待则积压

### 2.4 异步迭代器实现

```typescript
async *[Symbol.asyncIterator](): AsyncIterator<T> {
  while (true) {
    if (this.queue.length > 0) {
      // 情况1：有积压事件，直接消费
      yield this.queue.shift()!;
    } else if (this.done) {
      // 情况2：流已结束且队列空，退出
      return;
    } else {
      // 情况3：无事件且未结束，等待新事件
      const result = await new Promise<IteratorResult<T>>(
        (resolve) => this.waiting.push(resolve)
      );
      if (result.done) return;
      yield result.value;
    }
  }
}
```

**拉模式精髓**：
- 消费者 `yield` 等待
- 实际上把 `resolve` 回调留给生产者调用
- 生产者 `push` 时调用 `resolve`，消费者恢复执行

### 2.5 end 方法

```typescript
end(result?: R): void {
  this.done = true;
  if (result !== undefined) {
    this.resolveFinalResult(result);
  }
  // 唤醒所有等待中的消费者
  while (this.waiting.length > 0) {
    const waiter = this.waiting.shift()!;
    waiter({ value: undefined as any, done: true });
  }
}
```

**为什么唤醒所有等待者？**
- 流结束时可能有多个消费者挂起在 `await iterator.next()`
- 发送 `{ done: true }` 让它们正常退出

### 2.6 AssistantMessageEventStream 特化

```typescript
class AssistantMessageEventStream extends EventStream<AssistantMessageEvent, AssistantMessage> {
  constructor() {
    super(
      (event) => event.type === "done" || event.type === "error",
      (event) => {
        if (event.type === "done") return event.message;
        if (event.type === "error") return event.error;
        throw new Error("Unexpected event type");
      },
    );
  }
}
```

**类型实例化**：
- `T = AssistantMessageEvent`（输入）
- `R = AssistantMessage`（输出）

---

## 第三步：API 注册系统

### 3.1 类型定义

```typescript
export interface ApiProvider<TApi extends Api, TOptions extends StreamOptions> {
  api: TApi;
  stream: StreamFunction<TApi, TOptions>;
  streamSimple: StreamFunction<TApi, SimpleStreamOptions>;
}

interface ApiProviderInternal {
  api: Api;
  stream: ApiStreamFunction;
  streamSimple: ApiStreamSimpleFunction;
}
```

**为什么分两个接口？**
- `ApiProvider`：外部注册用的泛型接口（类型安全）
- `ApiProviderInternal`：内部存储用的统一接口（简化处理）

### 3.2 wrapStream 类型转换

```typescript
function wrapStream<TApi extends Api, TOptions extends StreamOptions>(
  api: TApi,
  stream: StreamFunction<TApi, TOptions>,
): ApiStreamFunction {
  return (model, context, options) => {
    if (model.api !== api) {
      throw new Error(`Mismatched api: ${model.api} expected ${api}`);
    }
    return stream(model as Model<TApi>, context, options as TOptions);
  };
}
```

**作用**：
1. 运行时检查 `model.api` 是否匹配注册的 `api`
2. 类型转换：将具体类型转为通用类型存入 Map

### 3.3 注册表操作

```typescript
const apiProviderRegistry = new Map<string, RegisteredApiProvider>();

// 注册
export function registerApiProvider<TApi extends Api, TOptions extends StreamOptions>(
  provider: ApiProvider<TApi, TOptions>,
  sourceId?: string,                    # 用于批量卸载
): void {
  apiProviderRegistry.set(provider.api, {
    provider: {
      api: provider.api,
      stream: wrapStream(provider.api, provider.stream),
      streamSimple: wrapStreamSimple(provider.api, provider.streamSimple),
    },
    sourceId,
  });
}

// 查询
export function getApiProvider(api: Api): ApiProviderInternal | undefined {
  return apiProviderRegistry.get(api)?.provider;
}

// 批量卸载（用于扩展模块）
export function unregisterApiProviders(sourceId: string): void {
  for (const [api, entry] of apiProviderRegistry.entries()) {
    if (entry.sourceId === sourceId) {
      apiProviderRegistry.delete(api);
    }
  }
}
```

**设计亮点**：
- `sourceId` 支持扩展模块批量注册和卸载
- 内部用 Map 存储，O(1) 查询复杂度

---

## 第四步：OpenAI Provider 实现

这是**最复杂的 Provider 实现**，展示了如何将真实的 LLM API 转换为 EventStream。

### 4.1 整体架构

```
streamOpenAICompletions(model, context, options)
├── 创建 AssistantMessageEventStream
├── 启动异步IIFE（立即执行函数）
│   ├── 初始化 output（累加器）
│   ├── 创建 OpenAI 客户端
│   ├── 构建请求参数
│   ├── 调用 OpenAI API 获取流
│   ├── 遍历流式响应 chunks
│   │   ├── 解析 usage（token使用）
│   │   ├── 解析 finish_reason（停止原因）
│   │   └── 处理 delta（增量内容）
│   │       ├── 文本内容（text）
│   │       ├── 思考内容（reasoning）
│   │       └── 工具调用（tool_calls）
│   ├── 结束当前块
│   ├── 推送 done 事件
│   └── 错误处理
└── 立即返回 stream（还没数据）
```

### 4.2 核心数据结构：output 累加器

```typescript
const output: AssistantMessage = {
  role: "assistant",
  content: [],           // 内容块数组（TextContent | ThinkingContent | ToolCall）
  api: model.api,
  provider: model.provider,
  model: model.id,
  usage: {               // Token 使用统计
    input: 0,
    output: 0,
    cacheRead: 0,
    cacheWrite: 0,
    totalTokens: 0,
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
  },
  stopReason: "stop",
  timestamp: Date.now(),
};
```

**设计要点**：
- `output` 是**累加器**，随着流式数据到达逐步填充
- 每个 chunk 处理后都推送到 `stream`，附带 `partial: output`
- 消费者始终看到最新完整状态

### 4.3 内容块管理：currentBlock

```typescript
let currentBlock: TextContent | ThinkingContent | (ToolCall & { partialArgs?: string }) | null = null;
const blocks = output.content;
const blockIndex = () => blocks.length - 1;
```

**为什么需要 currentBlock？**

OpenAI 的流式格式是**扁平的**，但我们需要构建**结构化的块**：

```json
// OpenAI 流式输出（扁平）
{"delta": {"content": "Hello"}}
{"delta": {"content": " world"}}
{"delta": {"tool_calls": [{"index": 0, "function": {"name": "calc"}}]}}
{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{\"x\": "}}]}}
{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "1}"}}]}}

// 目标结构（分块）
[
  { "type": "text", "text": "Hello world" },
  { "type": "toolCall", "id": "call_xxx", "name": "calc", "arguments": {"x": 1} }
]
```

**块切换逻辑**：

```typescript
// 当发现新的内容类型时，结束当前块，开始新块
if (!currentBlock || currentBlock.type !== "text") {
  finishCurrentBlock(currentBlock);  // 结束旧块（推送 end 事件）
  currentBlock = { type: "text", text: "" };  // 创建新块
  output.content.push(currentBlock);
  stream.push({ type: "text_start", contentIndex: blockIndex(), partial: output });
}
```

### 4.4 finishCurrentBlock：块结束处理

```typescript
const finishCurrentBlock = (block?: typeof currentBlock) => {
  if (block) {
    if (block.type === "text") {
      stream.push({
        type: "text_end",
        contentIndex: blockIndex(),
        content: block.text,
        partial: output,
      });
    } else if (block.type === "thinking") {
      stream.push({
        type: "thinking_end",
        contentIndex: blockIndex(),
        content: block.thinking,
        partial: output,
      });
    } else if (block.type === "toolCall") {
      // 关键：解析累积的 JSON 参数字符串
      block.arguments = parseStreamingJson(block.partialArgs);
      delete block.partialArgs;  // 清理临时字段
      stream.push({
        type: "toolcall_end",
        contentIndex: blockIndex(),
        toolCall: block,
        partial: output,
      });
    }
  }
};
```

**关键点**：
- `partialArgs` 是临时字段，用于累积 JSON 字符串
- 块结束时用 `parseStreamingJson` 解析为对象
- 每个块类型都有对应的 `*_end` 事件

### 4.5 文本内容处理

```typescript
if (choice.delta.content?.length > 0) {
  if (!currentBlock || currentBlock.type !== "text") {
    finishCurrentBlock(currentBlock);
    currentBlock = { type: "text", text: "" };
    output.content.push(currentBlock);
    stream.push({ type: "text_start", contentIndex: blockIndex(), partial: output });
  }

  if (currentBlock.type === "text") {
    currentBlock.text += choice.delta.content;  // 累积文本
    stream.push({
      type: "text_delta",
      contentIndex: blockIndex(),
      delta: choice.delta.content,  // 增量内容
      partial: output,
    });
  }
}
```

**事件序列**：
```
text_start → text_delta("Hello") → text_delta(" world") → text_end
```

### 4.6 思考内容处理（Reasoning）

处理多种字段名（兼容不同提供商）：

```typescript
const reasoningFields = ["reasoning_content", "reasoning", "reasoning_text"];
let foundReasoningField: string | null = null;
for (const field of reasoningFields) {
  if ((choice.delta as any)[field]?.length > 0) {
    foundReasoningField = field;
    break;
  }
}

if (foundReasoningField) {
  if (!currentBlock || currentBlock.type !== "thinking") {
    finishCurrentBlock(currentBlock);
    currentBlock = {
      type: "thinking",
      thinking: "",
      thinkingSignature: foundReasoningField,  // 记录来源字段
    };
    output.content.push(currentBlock);
    stream.push({ type: "thinking_start", contentIndex: blockIndex(), partial: output });
  }

  if (currentBlock.type === "thinking") {
    const delta = (choice.delta as any)[foundReasoningField];
    currentBlock.thinking += delta;
    stream.push({
      type: "thinking_delta",
      contentIndex: blockIndex(),
      delta,
      partial: output,
    });
  }
}
```

### 4.7 工具调用处理（最复杂）

```typescript
if (choice?.delta?.tool_calls) {
  for (const toolCall of choice.delta.tool_calls) {
    // 关键：检测新的工具调用（通过 ID 变化）
    if (!currentBlock ||
        currentBlock.type !== "toolCall" ||
        (toolCall.id && currentBlock.id !== toolCall.id)) {
      finishCurrentBlock(currentBlock);
      currentBlock = {
        type: "toolCall",
        id: toolCall.id || "",
        name: toolCall.function?.name || "",
        arguments: {},
        partialArgs: "",  // 用于累积 JSON 字符串
      };
      output.content.push(currentBlock);
      stream.push({ type: "toolcall_start", contentIndex: blockIndex(), partial: output });
    }

    if (currentBlock.type === "toolCall") {
      if (toolCall.id) currentBlock.id = toolCall.id;
      if (toolCall.function?.name) currentBlock.name = toolCall.function.name;

      let delta = "";
      if (toolCall.function?.arguments) {
        delta = toolCall.function.arguments;
        currentBlock.partialArgs += toolCall.function.arguments;  // 累积
        currentBlock.arguments = parseStreamingJson(currentBlock.partialArgs);  // 实时解析
      }

      stream.push({
        type: "toolcall_delta",
        contentIndex: blockIndex(),
        delta,
        partial: output,
      });
    }
  }
}
```

**为什么需要 partialArgs？**

OpenAI 的工具调用参数是**分片传输的 JSON**：

```
Chunk 1: {"arguments": "{\"x\":"}
Chunk 2: {"arguments": "1,"}
Chunk 3: {"arguments": "\"y\":"}
Chunk 4: {"arguments": "2}"}

累积过程：
partialArgs = "{\"x\":"        → parseStreamingJson → {x: undefined}
partialArgs = "{\"x\":1,"      → parseStreamingJson → {x: 1}
partialArgs = "{\"x\":1,\"y\":" → parseStreamingJson → {x: 1, y: undefined}
partialArgs = "{\"x\":1,\"y\":2}" → parseStreamingJson → {x: 1, y: 2}
```

**实时解析的价值**：
- UI 可以显示部分解析的参数（比如 `{x: 1}`）
- 用户提前知道工具要做什么
- 即使 JSON 未完成，也能展示有效字段

### 4.8 错误处理与资源清理

```typescript
} catch (error) {
  // 清理临时字段
  for (const block of output.content) delete (block as any).index;

  // 设置错误状态
  output.stopReason = options?.signal?.aborted ? "aborted" : "error";
  output.errorMessage = error instanceof Error ? error.message : JSON.stringify(error);

  // 提取额外元数据（OpenRouter 等提供商）
  const rawMetadata = (error as any)?.error?.metadata?.raw;
  if (rawMetadata) output.errorMessage += `\n${rawMetadata}`;

  // 推送错误事件并结束流
  stream.push({ type: "error", reason: output.stopReason, error: output });
  stream.end();
}
```

**设计要点**：
- 无论成功失败，都推送事件并结束流
- 消费者总能收到 `done` 或 `error` 事件
- 临时字段（如 `partialArgs`）在结束前清理

### 4.9 streamSimple 包装器

```typescript
export const streamSimpleOpenAICompletions: StreamFunction<"openai-completions", SimpleStreamOptions> = (
  model,
  context,
  options,
): AssistantMessageEventStream => {
  const apiKey = options?.apiKey || getEnvApiKey(model.provider);
  if (!apiKey) {
    throw new Error(`No API key for provider: ${model.provider}`);
  }

  const base = buildBaseOptions(model, options, apiKey);
  const reasoningEffort = supportsXhigh(model) ? options?.reasoning : clampReasoning(options?.reasoning);
  const toolChoice = (options as OpenAICompletionsOptions | undefined)?.toolChoice;

  return streamOpenAICompletions(model, context, {
    ...base,
    reasoningEffort,
    toolChoice,
  } satisfies OpenAICompletionsOptions);
};
```

**Simple 版本的职责**：
- 统一处理 API Key 获取
- 转换 `reasoning`（思考级别）为 `reasoningEffort`
- 处理 `supportsXhigh` 特殊逻辑
- 委托给完整版 `streamOpenAICompletions`

### 4.10 关键设计总结

| 设计 | 实现 | 价值 |
|------|------|------|
| **累加器模式** | `output` 对象逐步填充 | 消费者始终看到完整状态 |
| **块管理** | `currentBlock` + `finishCurrentBlock` | 处理混合内容类型（文本+工具） |
| **实时解析** | `parseStreamingJson` | 工具参数可预览 |
| **容错设计** | 多级 try-catch | 即使解析失败也返回空对象 |
| **类型擦除** | `as any` 用于提供商特定字段 | 兼容多种 OpenAI 兼容 API |
| **延迟返回** | 先创建 stream，再启动异步处理 | 调用方立即获得流对象 |

### 4.11 与 EventStream 的协作

```typescript
const stream = new AssistantMessageEventStream();  // 1. 创建流

(async () => {
  // 2. 异步处理（可能耗时数秒）
  for await (const chunk of openaiStream) {
    stream.push(event);  // 3. 推送事件
  }
  stream.push({ type: "done", ... });  // 4. 结束
  stream.end();
})();

return stream;  // 5. 立即返回（此时还没数据）
```

**为什么立即返回？**

调用方需要流对象来设置监听器：

```typescript
const stream = ai.stream(model, context);  // 立即获得流

// 立即设置消费
for await (const event of stream) {
  console.log(event);
}
```

如果等 OpenAI 请求完成再返回，就无法实现真正的流式处理了。

---

## 第五步：模型注册表

（待补充：models.ts 的详细解析）

---

## 第六步：消息转换机制

（待补充：transform-messages.ts 的详细解析）

---

## 第七步：工具调用系统

（待补充：Tool 定义、生命周期、执行流程）

---

## 第八步：环境变量和认证

（待补充：env-api-keys.ts 的详细解析）
