---
name: pi-mono-refer
description: |
  **先读后做**：实现 py-mono AI 模块前，先读 pi-mono 源码。
  
  触发场景：
  - 实现/修改 types.py、stream.py、registry.py
  - 实现 Anthropic/OpenAI provider
  - 设计 Token 管理、上下文剪枝
  
  工作流程：读源码 → 对比差异 → 汇报用户 → 获得确认 → 按 py312 规范实施
---

# pi-mono-refer：参考优先开发

## 重要：必须同时遵循 py312 规范

读取 pi-mono TypeScript 源码时，**架构逻辑和类型结构**可以参考，但**代码实现必须严格遵守 py312 规范**：

| 方面 | pi-mono（TypeScript）参考 | py312（Python）强制要求 |
|------|-------------------------|----------------------|
| **函数长度** | 不限 | ≤30行，超过必须拆分 |
| **注释语言** | 英文 | 中文文档字符串 |
| **类型注解** | 可省略 | 必须完整，包括 `-> None` |
| **泛型** | 可简化 | 必须完整参数化 `list[str]` |
| **重写方法** | 可选装饰器 | 必须使用 `@override` |


## 注意事项

- **⚠️ 严格遵守 py312**：实现时**必须**按 py312 规范编写代码（函数≤30行、中文注释、完整类型）
- **语言差异正常**：camelCase→snake_case、interface→Protocol 无需汇报
- **关注语义差异**：字段结构、类型组合、职责划分
- **鼓励改进**：如发现 pi-mono 设计问题，明确提出
- **复杂代码要拆分**：TypeScript 长函数/深嵌套在 Python 中必须重构为简洁函数
- **保持简洁**：聚焦关键差异，不纠结风格细节

## 当前状态速查

运行以下命令查看 AI 模块文件：
```bash
ls -la packages/ai/src/ai/
```
