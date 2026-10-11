"use strict";
/**
 * lib/reconcile-orphan.js v1.0.0 — 孤儿 tool_calls 视图修复（labforge 提取产物）
 *
 * 语义来源：dsh-agent-loop 补丁 reconcileOrphanToolCalls（孤儿 tool_calls 续跑卡死修复）。
 * 背景：工具调度器故障/重启竞态会留下"assistant 声明了 tool_calls 但 tool/result 从未写入"
 * 的历史 → 续跑重放时 LLM API 400 拒绝（"assistant message with 'tool_calls' must be
 * followed by tool messages"）→ 会话永久卡死。
 * 本函数在"发给模型的消息视图"上给孤儿补合成 error tool-result，使序列合法。
 * 纯函数：不改日志、不改会话、健康历史零副作用（pending 全被 tool-result 清空→空转）。
 *
 * 用法:
 *   const { reconcileOrphanToolCalls, findOrphanCalls } = require("./lib/reconcile-orphan.js");
 *   const fixed = reconcileOrphanToolCalls(derivedMessages);
 *   const orphans = findOrphanCalls(derivedMessages);   // [{callId, assistantIdx}]
 */
const VERSION = "1.0.0";

/** 从折叠消息数组中找出"assistant 声明但无配对 tool-result"的孤儿调用。 */
function findOrphanCalls(messages) {
  const orphans = [];
  let pending = [];
  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];
    const content = msg?.content;
    const isToolResult = Array.isArray(content) && content.some((b) => b?.type === "tool-result");
    if (isToolResult) {
      for (const b of content) {
        if (b?.type === "tool-result" && b.toolCallId !== undefined) {
          pending = pending.filter((c) => c.callId !== b.toolCallId);
        }
      }
      continue;
    }
    if (msg?.role === "assistant") {
      // 上一条 assistant 的未闭合调用在此断掉 → 孤儿
      for (const c of pending) orphans.push(c);
      pending = [];
      if (Array.isArray(content)) {
        for (const b of content) {
          if (b?.type === "tool-call" && b.id !== undefined) {
            pending.push({ callId: b.id, assistantIdx: i });
          }
        }
      }
      continue;
    }
    // user/其它消息到达而 pending 未清 → 孤儿
    for (const c of pending) orphans.push(c);
    pending = [];
  }
  for (const c of pending) orphans.push(c); // 尾部未闭合
  return orphans;
}

/** 合成一条 tool error 结果消息（模拟调度器中断）。 */
function syntheticToolError(callId, note) {
  return {
    role: "user",
    source: { kind: "tool", callId },
    content: [{
      type: "tool-result",
      toolCallId: callId,
      content: [{
        type: "text",
        text: note || "Error: tool execution was interrupted before a result was recorded (scheduler failure or process restart). No result is available for this call; retry or continue."
      }],
      isError: true,
    }],
  };
}

/**
 * 视图级孤儿修复：返回新数组（不 mutate 原消息）。
 * 每个孤儿 tool_call 在其 assistant 消息后补合成 error 结果，闭合 API 契约。
 */
function reconcileOrphanToolCalls(messages, note) {
  const out = [];
  let pending = [];
  const flushPending = () => {
    for (const c of pending) {
      out.push(syntheticToolError(c.callId, note));
    }
    pending = [];
  };
  for (const message of messages) {
    const content = message?.content;
    const isToolResult = Array.isArray(content) && content.some((b) => b?.type === "tool-result");
    if (isToolResult) {
      for (const b of content) {
        if (b?.type === "tool-result" && b.toolCallId !== undefined) {
          pending = pending.filter((c) => c.callId !== b.toolCallId);
        }
      }
      out.push(message);
      continue;
    }
    if (message?.role === "assistant") {
      flushPending();
      out.push(message);
      if (Array.isArray(content)) {
        for (const b of content) {
          if (b?.type === "tool-call" && b.id !== undefined) pending.push({ callId: b.id });
        }
      }
      continue;
    }
    flushPending();
    out.push(message);
  }
  flushPending();
  return out;
}

module.exports = { reconcileOrphanToolCalls, findOrphanCalls, syntheticToolError, VERSION };
