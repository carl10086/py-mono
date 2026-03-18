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

### 5.1 数据来源与结构

模型数据来自**代码生成**（`scripts/generate-models.ts`），生成的文件结构：

```typescript
// models.generated.ts
export const MODELS = {
  "amazon-bedrock": {
    "amazon.nova-lite-v1:0": {
      id: "amazon.nova-lite-v1:0",
      name: "Nova Lite",
      api: "bedrock-converse-stream",
      provider: "amazon-bedrock",
      baseUrl: "https://bedrock-runtime.us-east-1.amazonaws.com",
      reasoning: false,
      input: ["text", "image"],
      cost: {
        input: 0.06,      // $/百万 tokens
        output: 0.24,
        cacheRead: 0.015,
        cacheWrite: 0,
      },
      contextWindow: 300000,
      maxTokens: 8192,
    } satisfies Model<"bedrock-converse-stream">,
    // ... 更多模型
  },
  "anthropic": {
    "claude-4-5-sonnet-20241022": { ... },
    // ...
  }
}
```

**设计决策**：
- 使用 `satisfies Model<Api>` 确保类型安全，同时保留字面量类型
- 成本单位是**每百万 tokens**（$/1M tokens），行业惯例
- 嵌套结构：Provider → ModelId → Model

### 5.2 注册表初始化

```typescript
const modelRegistry: Map<string, Map<string, Model<Api>>> = new Map();

// 模块加载时立即初始化
for (const [provider, models] of Object.entries(MODELS)) {
  const providerModels = new Map<string, Model<Api>>();
  for (const [id, model] of Object.entries(models)) {
    providerModels.set(id, model as Model<Api>);
  }
  modelRegistry.set(provider, providerModels);
}
```

**双层 Map 结构**：
```
modelRegistry: Map<provider, Map<modelId, Model>>

示例：
"anthropic" → Map {
  "claude-4-5-sonnet-20241022" → Model,
  "claude-4-5-haiku-20241022" → Model
}
"openai" → Map {
  "gpt-4o" → Model,
  "gpt-4o-mini" → Model
}
```

**为什么选择双层 Map？**
- O(1) 查询复杂度
- 天然支持按 Provider 枚举模型
- 内存局部性好（同 Provider 模型物理上接近）

### 5.3 类型安全的 getModel

```typescript
type ModelApi<
  TProvider extends KnownProvider,
  TModelId extends keyof (typeof MODELS)[TProvider],
> = (typeof MODELS)[TProvider][TModelId] extends { api: infer TApi }
  ? (TApi extends Api ? TApi : never)
  : never;

export function getModel<
  TProvider extends KnownProvider,
  TModelId extends keyof (typeof MODELS)[TProvider]
>(
  provider: TProvider,
  modelId: TModelId,
): Model<ModelApi<TProvider, TModelId>> {
  const providerModels = modelRegistry.get(provider);
  return providerModels?.get(modelId as string) as Model<ModelApi<TProvider, TModelId>>;
}
```

**泛型的魔力**：

```typescript
// 调用时类型自动推断
const model = getModel("anthropic", "claude-4-5-sonnet-20241022");
// 返回类型：Model<"anthropic-messages">

const model2 = getModel("openai", "gpt-4o");
// 返回类型：Model<"openai-completions">
```

**类型推断过程**：
1. `TProvider = "anthropic"`
2. `TModelId = "claude-4-5-sonnet-20241022"`
3. `(typeof MODELS)["anthropic"]["claude-4-5-sonnet-20241022"]` 查找对应模型
4. 提取其 `api` 字段 → `"anthropic-messages"`
5. 返回 `Model<"anthropic-messages">`

### 5.4 枚举操作

```typescript
// 获取所有 Provider
export function getProviders(): KnownProvider[] {
  return Array.from(modelRegistry.keys()) as KnownProvider[];
}
// 返回：["amazon-bedrock", "anthropic", "openai", ...]

// 获取某 Provider 的所有模型
export function getModels<TProvider extends KnownProvider>(
  provider: TProvider,
): Model<...>[] {
  const models = modelRegistry.get(provider);
  return models ? Array.from(models.values()) : [];
}
```

### 5.5 成本计算

```typescript
export function calculateCost<TApi extends Api>(
  model: Model<TApi>,
  usage: Usage
): Usage["cost"] {
  // 公式：cost = (价格/1M) * token数
  usage.cost.input = (model.cost.input / 1000000) * usage.input;
  usage.cost.output = (model.cost.output / 1000000) * usage.output;
  usage.cost.cacheRead = (model.cost.cacheRead / 1000000) * usage.cacheRead;
  usage.cost.cacheWrite = (model.cost.cacheWrite / 1000000) * usage.cacheWrite;
  usage.cost.total = usage.cost.input + usage.cost.output +
                     usage.cost.cacheRead + usage.cost.cacheWrite;
  return usage.cost;
}
```

**成本计算示例**：
```typescript
const model = getModel("openai", "gpt-4o");
// model.cost = { input: 2.5, output: 10, cacheRead: 1.25, cacheWrite: 0 }

const usage = {
  input: 1000,      // 1k tokens 输入
  output: 500,      // 500 tokens 输出
  cacheRead: 0,
  cacheWrite: 0
};

calculateCost(model, usage);
// cost.input = (2.5 / 1000000) * 1000 = $0.0025
// cost.output = (10 / 1000000) * 500 = $0.005
// cost.total = $0.0075
```

### 5.6 特性检测

```typescript
// 检测是否支持 xhigh thinking level
export function supportsXhigh<TApi extends Api>(model: Model<TApi>): boolean {
  if (model.id.includes("gpt-5.2") || model.id.includes("gpt-5.3") ||
      model.id.includes("gpt-5.4")) {
    return true;
  }
  if (model.id.includes("opus-4-6") || model.id.includes("opus-4.6")) {
    return true;
  }
  return false;
}

// 模型相等性比较
export function modelsAreEqual<TApi extends Api>(
  a: Model<TApi> | null | undefined,
  b: Model<TApi> | null | undefined,
): boolean {
  if (!a || !b) return false;
  return a.id === b.id && a.provider === b.provider;
}
```

### 5.7 设计总结

| 特性 | 实现 | 价值 |
|------|------|------|
| **代码生成** | `models.generated.ts` | 数据来源可自动化更新 |
| **双层 Map** | `Map<provider, Map<id, Model>>` | O(1) 查询，高效枚举 |
| **类型安全** | 泛型推断 `Model<Api>` | 编译时知道模型支持哪些 API |
| **成本追踪** | 基于实际 token 计算 | 精确成本分析 |
| **特性检测** | `supportsXhigh` 等函数 | 运行时决策 |

---

## 第六步：消息转换机制

### 6.1 为什么需要消息转换？

不同 LLM 提供商的消息格式要求不同：

| 提供商 | 特殊要求 |
|--------|---------|
| Anthropic | Tool call ID 只能包含 `^[a-zA-Z0-9_-]+$`（最大 64 字符） |
| OpenAI | 支持更长的 ID，但 Responses API 生成 450+ 字符的 ID |
| 跨模型对话 | 思考块需要特殊处理（加密内容不能跨模型） |
| 流式中断 | 需要处理 orphaned tool calls（有调用无结果） |

### 6.2 核心函数签名

```typescript
export function transformMessages<TApi extends Api>(
  messages: Message[],
  model: Model<TApi>,
  normalizeToolCallId?: (id: string, model: Model<TApi>, source: AssistantMessage) => string,
): Message[]
```

**参数说明**：
- `messages`：原始消息数组
- `model`：目标模型（检查是否同模型对话）
- `normalizeToolCallId`：可选的 ID 规范化函数

### 6.3 两阶段处理架构

```
transformMessages
├── 第一阶段：转换消息内容
│   ├── UserMessage：直接透传
│   ├── ToolResultMessage：规范化 toolCallId
│   └── AssistantMessage：
│       ├── 检查 isSameModel（同模型/跨模型）
│       ├── ThinkingContent：
│       │   ├── 加密内容（redacted）：同模型保留，跨模型删除
│       │   ├── 有签名但空内容：同模型保留
│       │   └── 普通思考：跨模型转为 text
│       ├── TextContent：直接透传
│       └── ToolCall：
│           ├── 删除 thoughtSignature（跨模型）
│           └── 规范化 toolCallId
│   └── 构建 toolCallIdMap（原始 ID → 规范化 ID）
│
└── 第二阶段：插入合成 tool results
    ├── 遍历转换后的消息
    ├── 跟踪 pendingToolCalls（未完成的工具调用）
    ├── 检测 orphaned calls（有调用无结果）
    └── 插入合成 ToolResultMessage（标记 isError: true）
```

### 6.4 同模型 vs 跨模型处理

```typescript
const isSameModel =
  assistantMsg.provider === model.provider &&
  assistantMsg.api === model.api &&
  assistantMsg.model === model.id;
```

**思考块处理差异**：

```typescript
if (block.type === "thinking") {
  // 加密内容只能用于同模型
  if (block.redacted) {
    return isSameModel ? block : [];  // 跨模型直接删除
  }

  // 有签名但空内容（OpenAI 加密推理）
  if (isSameModel && block.thinkingSignature) return block;

  // 空思考块跳过
  if (!block.thinking || block.thinking.trim() === "") return [];

  // 同模型保留思考块
  if (isSameModel) return block;

  // 跨模型转为普通文本（下游模型看不懂 thinking）
  return { type: "text", text: block.thinking };
}
```

**场景示例**：

```typescript
// 同模型对话（Claude → Claude）
[thinking: "让我分析..."]  →  保留为 thinking

// 跨模型对话（Claude → GPT）
[thinking: "让我分析..."]  →  转为 [text: "让我分析..."]
```

### 6.5 Tool Call ID 规范化

**问题场景**：
- OpenAI Responses API 生成 ID：`call_abc|123|xyz...`（450+ 字符，含特殊字符）
- Anthropic API 要求 ID：最大 64 字符，只能字母数字下划线横线

**解决方案**：

```typescript
// 第一阶段：构建 ID 映射
if (!isSameModel && normalizeToolCallId) {
  const normalizedId = normalizeToolCallId(toolCall.id, model, assistantMsg);
  if (normalizedId !== toolCall.id) {
    toolCallIdMap.set(toolCall.id, normalizedId);  // 原始 ID → 规范化 ID
    normalizedToolCall = { ...normalizedToolCall, id: normalizedId };
  }
}

// ToolResultMessage 使用规范化 ID
if (msg.role === "toolResult") {
  const normalizedId = toolCallIdMap.get(msg.toolCallId);
  if (normalizedId) {
    return { ...msg, toolCallId: normalizedId };
  }
}
```

**映射示例**：
```
原始 ID：call_abc|123|xyz...（450字符）
    ↓ normalizeToolCallId
规范 ID：call_abc123xyz（12字符）

消息转换：
AssistantMessage: [toolCall: {id: "call_abc123xyz"}]
ToolResultMessage: {toolCallId: "call_abc123xyz"}  // 同步更新
```

### 6.6 Orphaned Tool Calls 处理

**问题**：流式传输中断时，可能出现 `ToolCall` 但没有对应的 `ToolResultMessage`。

**检测逻辑**：

```typescript
const result: Message[] = [];
let pendingToolCalls: ToolCall[] = [];  // 待处理的工具调用
let existingToolResultIds = new Set<string>();

for (const msg of transformed) {
  if (msg.role === "assistant") {
    // 有新的 assistant 消息，检查之前的 pending 是否已解决
    if (pendingToolCalls.length > 0) {
      for (const tc of pendingToolCalls) {
        if (!existingToolResultIds.has(tc.id)) {
          // 发现 orphaned call，插入合成结果
          result.push({
            role: "toolResult",
            toolCallId: tc.id,
            toolName: tc.name,
            content: [{ type: "text", text: "No result provided" }],
            isError: true,  // 标记为错误
            timestamp: Date.now(),
          });
        }
      }
    }

    // 跟踪当前 assistant 的工具调用
    const toolCalls = msg.content.filter(b => b.type === "toolCall");
    pendingToolCalls = toolCalls;
    existingToolResultIds = new Set();

  } else if (msg.role === "toolResult") {
    existingToolResultIds.add(msg.toolCallId);
    result.push(msg);

  } else if (msg.role === "user") {
    // 用户消息打断工具流，强制解决所有 pending
    if (pendingToolCalls.length > 0) {
      for (const tc of pendingToolCalls) {
        if (!existingToolResultIds.has(tc.id)) {
          result.push({ /* 合成 tool result */ });
        }
      }
      pendingToolCalls = [];
    }
    result.push(msg);
  }
}
```

**场景示例**：

```
原始消息：
1. Assistant: [toolCall: {id: "call_1", name: "search"}]
2. Assistant: stopReason: "aborted"  // 流中断，没有 tool result

转换后：
1. Assistant: [toolCall: {id: "call_1", name: "search"}]
2. ToolResult: {toolCallId: "call_1", content: "No result provided", isError: true}
```

### 6.7 错误/中断消息过滤

```typescript
// 跳过错误和中断的 assistant 消息
if (assistantMsg.stopReason === "error" || assistantMsg.stopReason === "aborted") {
  continue;  // 不加入结果
}
```

**原因**：
- 可能包含不完整内容（只有 reasoning 没有消息）
- 重放会导致 API 错误（如 OpenAI "reasoning without following item"）
- 模型应该从上一个有效状态重试

### 6.8 设计亮点总结

| 设计 | 解决的问题 | 实现方式 |
|------|-----------|---------|
| **同模型检测** | 加密思考块跨模型报错 | 比较 provider/api/model |
| **ID 映射表** | 工具调用 ID 格式不兼容 | Map 存储原始→规范映射 |
| **两阶段处理** | Orphaned calls 检测困难 | 先转换内容，再修复结构 |
| **合成结果** | 流中断导致 API 错误 | 自动插入 isError=true 的 tool result |
| **思考块降级** | 下游模型不理解 thinking | 跨模型时转为 text |
| **错误过滤** | 重放中断消息导致错误 | 跳过 error/aborted 消息 |

---

## 第七步：工具调用系统

### 7.1 Tool 定义

工具是 AI 与外部世界交互的接口：

```typescript
export interface Tool<TParameters extends TSchema = TSchema> {
  name: string;                    // 工具名称（函数名）
  description: string;             // 工具描述（LLM 决定何时使用）
  parameters: TParameters;         // 参数 schema（TypeBox）
}
```

**使用 TypeBox 定义参数**：

```typescript
import { Type } from "@sinclair/typebox";

const calculatorTool = {
  name: "calculator",
  description: "Perform mathematical calculations",
  parameters: Type.Object({
    operation: Type.String({ enum: ["add", "subtract", "multiply", "divide"] }),
    x: Type.Number(),
    y: Type.Number()
  })
};
// 自动生成 JSON Schema：
// {
//   "type": "object",
//   "properties": {
//     "operation": { "type": "string", "enum": ["add", "subtract", ...] },
//     "x": { "type": "number" },
//     "y": { "type": "number" }
//   },
//   "required": ["operation", "x", "y"]
// }
```

### 7.2 工具调用生命周期

```
阶段1: 定义工具
    │
    ▼
阶段2: 传递给 LLM（Context.tools）
    │
    ▼
阶段3: LLM 决定调用 → 生成 ToolCall
    │
    ▼
阶段4: 应用执行工具 → 生成 ToolResultMessage
    │
    ▼
阶段5: ToolResultMessage 传回 LLM
    │
    ▼
阶段6: LLM 继续生成最终回复
```

### 7.3 工具调用数据结构

**ToolCall（LLM 生成）**：

```typescript
export interface ToolCall {
  type: "toolCall";
  id: string;                      // 唯一标识（用于关联结果）
  name: string;                    // 工具名称
  arguments: Record<string, any>;  // 解析后的参数
  thoughtSignature?: string;       // Google 特有：思考上下文签名
}
```

**ToolResultMessage（执行结果）**：

```typescript
export interface ToolResultMessage<TDetails = any> {
  role: "toolResult";
  toolCallId: string;              // 关联 ToolCall.id
  toolName: string;                // 工具名称
  content: (TextContent | ImageContent)[];  // 结果内容（支持图文）
  details?: TDetails;              // 扩展信息（泛型）
  isError: boolean;                // 是否执行失败
  timestamp: number;
}
```

### 7.4 Provider 特定的工具转换

**OpenAI 格式**：

```typescript
// convertTools（openai-completions.ts）
function convertTools(tools: Tool[], compat: OpenAICompletionsCompat) {
  return tools.map(tool => ({
    type: "function",
    function: {
      name: tool.name,
      description: tool.description,
      parameters: tool.parameters,  // TypeBox 直接生成 JSON Schema
      ...(compat.supportsStrictMode !== false && { strict: false }),
    }
  }));
}

// 生成的 OpenAI 请求参数
{
  "tools": [{
    "type": "function",
    "function": {
      "name": "calculator",
      "description": "Perform mathematical calculations",
      "parameters": { /* JSON Schema */ },
      "strict": false
    }
  }]
}
```

**Anthropic 格式**：

```typescript
// convertTools（anthropic.ts）
function convertTools(tools: Tool[], isOAuthToken: boolean): Anthropic.Messages.Tool[] {
  return tools.map(tool => ({
    name: tool.name,
    description: tool.description,
    input_schema: tool.parameters as Anthropic.Messages.Tool["input_schema"],
    // Anthropic 不支持 strict 字段
  }));
}
```

**Google 格式**：

```typescript
// convertTools（google-shared.ts）
export function convertTools(tools: Tool[]) {
  return tools.map(tool => ({
    name: tool.name,
    description: tool.description,
    parameters: {
      type: "object" as const,
      properties: tool.parameters.properties,
      required: tool.parameters.required,
    }
  }));
}
```

### 7.5 工具调用执行流程

**完整示例代码**：

```typescript
import { streamSimple, getModel, Type } from "@mariozechner/pi-ai";

// 1. 定义工具
const tools = [{
  name: "calculator",
  description: "Perform math calculations",
  parameters: Type.Object({
    operation: Type.String(),
    x: Type.Number(),
    y: Type.Number()
  })
}];

// 2. 创建上下文
const context = {
  messages: [{ role: "user", content: "Calculate 23 * 47", timestamp: Date.now() }],
  tools
};

// 3. 调用 LLM
const stream = streamSimple(getModel("openai", "gpt-4o"), context);

// 4. 处理响应
let assistantMessage;
for await (const event of stream) {
  if (event.type === "toolcall_end") {
    // 5. 执行工具调用
    const toolCall = event.toolCall;
    const result = await executeTool(toolCall);  // 你的工具实现

    // 6. 创建 ToolResultMessage
    const toolResult = {
      role: "toolResult" as const,
      toolCallId: toolCall.id,
      toolName: toolCall.name,
      content: [{ type: "text" as const, text: String(result) }],
      isError: false,
      timestamp: Date.now()
    };

    // 7. 添加到上下文
    context.messages.push(event.partial);  // Assistant message with tool call
    context.messages.push(toolResult);      // Tool result

    // 8. 继续对话
    const nextStream = streamSimple(getModel("openai", "gpt-4o"), context);
    assistantMessage = await nextStream.result();
  }
}

async function executeTool(toolCall: ToolCall) {
  switch (toolCall.name) {
    case "calculator":
      const { operation, x, y } = toolCall.arguments;
      switch (operation) {
        case "multiply": return x * y;
        case "add": return x + y;
        // ...
      }
  }
}
```

### 7.6 流式工具调用的关键处理

**问题**：工具调用参数在流式传输中是分片的

```
Chunk 1: {"arguments": "{\"ope"}
Chunk 2: {"arguments": "ration\":\"mult"}
Chunk 3: {"arguments": "iply\",\"x\":23,"}
Chunk 4: {"arguments": "\"y\":47}"}
```

**解决方案**：`parseStreamingJson` + `partialArgs`

```typescript
// OpenAI Provider 中的处理
if (toolCall.function?.arguments) {
  currentBlock.partialArgs += toolCall.function.arguments;  // 累积
  currentBlock.arguments = parseStreamingJson(currentBlock.partialArgs);  // 实时解析
}
```

**实时解析的价值**：
- 即使 JSON 不完整，也能得到部分对象 `{operation: "multiply"}`
- UI 可以提前显示工具调用意图
- 工具执行时可以优雅地处理缺失参数

### 7.7 错误处理与重试

**工具执行错误**：

```typescript
const toolResult: ToolResultMessage = {
  role: "toolResult",
  toolCallId: toolCall.id,
  toolName: toolCall.name,
  content: [{ type: "text", text: "Error: Division by zero" }],
  isError: true,  // 标记为错误
  timestamp: Date.now()
};
```

**LLM 看到错误后的行为**：
- 理解工具调用失败
- 可能重试（修正参数）
- 或向用户解释错误

### 7.8 设计亮点总结

| 设计 | 实现 | 价值 |
|------|------|------|
| **TypeBox Schema** | 参数类型定义 | 编译时类型安全 + 运行时验证 |
| **统一 ToolCall** | 跨提供商一致的结构 | 工具代码可复用 |
| **ToolResultMessage** | 支持图文 + 错误标记 | 丰富的工具表达能力 |
| **实时 JSON 解析** | `parseStreamingJson` | 流式工具调用可预览 |
| **泛型 TDetails** | `ToolResultMessage<TDetails>` | 扩展信息类型安全 |
| **thoughtSignature** | Google 特有字段 | 支持思考链上下文 |

---

## 第八步：环境变量和认证

### 8.1 设计目标

统一处理多提供商的 API 认证：
- **简单场景**：OpenAI、Anthropic 等只需 API Key
- **复杂场景**：AWS Bedrock 多凭证类型、Google Vertex ADC
- **安全场景**：OAuth Token（Anthropic）、动态凭证

### 8.2 核心函数签名

```typescript
/**
 * Get API key for provider from known environment variables
 * Will not return API keys for providers that require OAuth tokens
 */
export function getEnvApiKey(provider: KnownProvider): string | undefined;
export function getEnvApiKey(provider: string): string | undefined;
```

**设计决策**：
- 返回 `string | undefined` 而非抛出错误
- 调用方决定如何处理缺失（使用默认值或报错）
- 支持自定义 provider 字符串（扩展性）

### 8.3 标准 API Key 映射

```typescript
const envMap: Record<string, string> = {
  openai: "OPENAI_API_KEY",
  "azure-openai-responses": "AZURE_OPENAI_API_KEY",
  google: "GEMINI_API_KEY",
  groq: "GROQ_API_KEY",
  cerebras: "CEREBRAS_API_KEY",
  xai: "XAI_API_KEY",
  openrouter: "OPENROUTER_API_KEY",
  "vercel-ai-gateway": "AI_GATEWAY_API_KEY",
  zai: "ZAI_API_KEY",
  mistral: "MISTRAL_API_KEY",
  minimax: "MINIMAX_API_KEY",
  "minimax-cn": "MINIMAX_CN_API_KEY",
  huggingface: "HF_TOKEN",
  opencode: "OPENCODE_API_KEY",
  "opencode-go": "OPENCODE_API_KEY",
  "kimi-coding": "KIMI_API_KEY",
};
```

**使用模式**：
```typescript
const envVar = envMap[provider];
return envVar ? process.env[envVar] : undefined;
```

### 8.4 特殊认证处理

#### Anthropic：OAuth Token 优先

```typescript
if (provider === "anthropic") {
  // ANTHROPIC_OAUTH_TOKEN takes precedence over ANTHROPIC_API_KEY
  return process.env.ANTHROPIC_OAUTH_TOKEN || process.env.ANTHROPIC_API_KEY;
}
```

**原因**：
- Anthropic 支持 OAuth 认证（用户授权）
- OAuth Token 权限更细粒度
- 优先级高于 API Key

#### GitHub Copilot：多 Token 来源

```typescript
if (provider === "github-copilot") {
  return process.env.COPILOT_GITHUB_TOKEN ||
         process.env.GH_TOKEN ||
         process.env.GITHUB_TOKEN;
}
```

**兼容性考虑**：
- `COPILOT_GITHUB_TOKEN`：专用变量
- `GH_TOKEN`：GitHub CLI 用户已配置
- `GITHUB_TOKEN`：通用 GitHub Token

#### Google Vertex：ADC 认证

```typescript
if (provider === "google-vertex") {
  // 1. 优先检查显式 API Key
  if (process.env.GOOGLE_CLOUD_API_KEY) {
    return process.env.GOOGLE_CLOUD_API_KEY;
  }

  // 2. 检查 Application Default Credentials
  const hasCredentials = hasVertexAdcCredentials();
  const hasProject = !!(process.env.GOOGLE_CLOUD_PROJECT || process.env.GCLOUD_PROJECT);
  const hasLocation = !!process.env.GOOGLE_CLOUD_LOCATION;

  if (hasCredentials && hasProject && hasLocation) {
    return "<authenticated>";  // 标记已认证，实际凭证在 ADC 中
  }
}
```

**ADC（Application Default Credentials）检查**：

```typescript
let cachedVertexAdcCredentialsExists: boolean | null = null;

function hasVertexAdcCredentials(): boolean {
  if (cachedVertexAdcCredentialsExists === null) {
    // 异步加载 Node.js 模块（浏览器环境不执行）
    if (!_existsSync || !_homedir || !_join) {
      const isNode = typeof process !== "undefined" &&
                    (process.versions?.node || process.versions?.bun);
      if (!isNode) {
        cachedVertexAdcCredentialsExists = false;
      }
      return false;
    }

    // 检查 GOOGLE_APPLICATION_CREDENTIALS 环境变量
    const gacPath = process.env.GOOGLE_APPLICATION_CREDENTIALS;
    if (gacPath) {
      cachedVertexAdcCredentialsExists = _existsSync(gacPath);
    } else {
      // 默认 ADC 路径：~/.config/gcloud/application_default_credentials.json
      cachedVertexAdcCredentialsExists = _existsSync(
        _join(_homedir(), ".config", "gcloud", "application_default_credentials.json")
      );
    }
  }
  return cachedVertexAdcCredentialsExists;
}
```

**关键设计**：
- **延迟加载**：Node.js 模块异步导入，不阻塞启动
- **浏览器安全**：非 Node 环境返回 `false`
- **缓存结果**：避免重复文件检查

#### Amazon Bedrock：多凭证类型

```typescript
if (provider === "amazon-bedrock") {
  // 支持多种 AWS 认证方式：
  // 1. 命名配置文件
  if (process.env.AWS_PROFILE) return "<authenticated>";

  // 2. IAM Access Key
  if (process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY) {
    return "<authenticated>";
  }

  // 3. Bedrock Bearer Token
  if (process.env.AWS_BEARER_TOKEN_BEDROCK) return "<authenticated>";

  // 4. ECS Task Role
  if (process.env.AWS_CONTAINER_CREDENTIALS_RELATIVE_URI) return "<authenticated>";
  if (process.env.AWS_CONTAINER_CREDENTIALS_FULL_URI) return "<authenticated>";

  // 5. IRSA (IAM Roles for Service Accounts) - EKS
  if (process.env.AWS_WEB_IDENTITY_TOKEN_FILE) return "<authenticated>";
}
```

**AWS 认证链**：
- 不直接返回密钥，返回 `"<authenticated>"` 标记
- 实际凭证由 AWS SDK 的默认凭证链处理
- 支持从 `~/.aws/credentials`、IAM Role、ECS、EKS 等多种来源获取

### 8.5 异步模块加载（浏览器兼容）

```typescript
// NEVER convert to top-level imports - breaks browser/Vite builds (web-ui)
let _existsSync: typeof import("node:fs").existsSync | null = null;
let _homedir: typeof import("node:os").homedir | null = null;
let _join: typeof import("node:path").join | null = null;

// 仅在 Node.js/Bun 环境 eagerly load
if (typeof process !== "undefined" && (process.versions?.node || process.versions?.bun)) {
  dynamicImport(NODE_FS_SPECIFIER).then((m) => {
    _existsSync = (m as typeof import("node:fs")).existsSync;
  });
  // ...
}
```

**为什么这样设计？**

| 问题 | 解决方案 |
|------|---------|
| 浏览器不支持 `node:fs` | 条件导入，只在 Node 环境加载 |
| Vite 打包报错 | 避免顶层 `import "node:fs"` |
| 类型安全 | 显式声明类型 `typeof import(...)` |
| 性能 | 异步加载，不阻塞启动 |

### 8.6 使用模式示例

**基础使用**：

```typescript
const apiKey = options?.apiKey || getEnvApiKey(model.provider);
if (!apiKey) {
  throw new Error(`No API key for provider: ${model.provider}`);
}
```

**分级降级**：

```typescript
const apiKey =
  options?.apiKey ||           // 1. 用户传入
  getEnvApiKey(model.provider) ||  // 2. 环境变量
  config.get(`providers.${model.provider}.apiKey`);  // 3. 配置文件
```

**Vertex 特殊处理**：

```typescript
const apiKey = getEnvApiKey("google-vertex");
if (apiKey === "<authenticated>") {
  // 使用 ADC，无需显式 key
  const client = new VertexAI({
    project: process.env.GOOGLE_CLOUD_PROJECT,
    location: process.env.GOOGLE_CLOUD_LOCATION,
  });
} else if (apiKey) {
  // 使用 API Key
  const client = new VertexAI({ apiKey });
}
```

### 8.7 设计亮点总结

| 设计 | 实现 | 价值 |
|------|------|------|
| **统一接口** | `getEnvApiKey(provider)` | 调用方无需关心提供商差异 |
| **OAuth 优先** | Anthropic OAuth > API Key | 安全性优先 |
| **ADC 支持** | Google Vertex 凭证自动发现 | 符合云原生最佳实践 |
| **AWS 全链路** | 6 种认证方式 | 覆盖所有 AWS 部署场景 |
| **浏览器兼容** | 条件异步导入 | web-ui 可用 |
| **缓存优化** | ADC 结果缓存 | 避免重复文件 IO |
| **返回标记** | `"<authenticated>"` | 区分"有凭证"和"需要凭证" |
