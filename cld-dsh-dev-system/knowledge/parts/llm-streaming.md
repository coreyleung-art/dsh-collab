# 部件卡 · dsh-llm-streaming（LLM 流式 / 会话词汇）

> 填卡：2026-09-05 · 依据：官方 subsystems/llm-streaming.md(1059行核心段)
> 状态：learned（registry: llm-streaming）

## 1. 一句话定位
agent-loop 移动的会话词汇声明处：`Message`(不可变 role/source/content) = 类型化 **ContentBlock 数组**；流式原始协议 StreamChunk；失败/定价/用量/适配器契约。新模态进 ContentBlockMap 需 adapter/UI/compaction/durable replay 全支持。

## 2. 概念与定义
- **ContentBlockMap** merge-extensible：text | reasoning(thinking≠可见文本) | image(durable attachment) | tool-call({id:ToolCallId,name,raw-JSON arguments}) | tool-result({toolCallId, 嵌套 content[], isError?})。
- **Message**：identified immutable role/source/content。assistant message 带 AssistantProvenance(provider/model + adapter-private replay data)。ToolResult 与 tool-call 配对(见 compaction toolPairing)。
- **ImageAttachmentAccess**：{readOnlyPath(不可变 normalized bytes 绝对路径, 只读)}——request 序列化期由 attachment provider host path + consumer 当前 tool fs 映射合成；仅该 request 有效，不参与 variantId。
- **StreamChunk**：raw 协议(增量)。**LlmFailure**：失败类型。**ResolvedRetryPolicy**：重试。**TokenUsage**：用量。**BlockAssembler**：chunk→block 组装。**LlmCallConfig + logged header**：request envelope。

## 3. 作用与生命周期
loop 组装 request(Message[] + config) → adapter stream chunks → BlockAssembler → ContentBlock 进消息 → append 回 session log → 下一步派生。pricing(agent 卡)/usage 记录。

## 4. 约束（红线/不可违）
- 新模态必须全路径支持(adapter/UI/compaction/replay)——勿只加类型。
- image 只读路径——调用方不得写。
- Message 不可变；tool-result 嵌套 content。

## 5. 依赖
- 被依赖 agent-loop/compaction(surface)/conversation(UI)。依赖 adapter 契约(provider)。

## 6. 规范要点（标准）
- 会话历史格式理解：events→ContentBlock 判别器(persistence/web-client 卡)；诊断渲染/回放问题按 block type 查。
- mini 环境多 provider(deepseek/minimax) = adapter 契约实例——换 provider 不换会话词汇。

## 7. 关联
- 官方：llm-streaming.md、session.md · 工具箱：T1(历史加载) · 路由：—
- 代码：dsh-llm/dsh-llm-pi-ai 等 adapter

## 8. 待补
- reasoning block 与 text 在 UI 的分流(chat vs trajectory)。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
