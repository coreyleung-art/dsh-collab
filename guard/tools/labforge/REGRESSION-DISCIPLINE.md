# 修复→实验卡→回归 纪律（labforge 持续循环）

> mbp-ops · 2026-09-05 · 让每次修复都可被验证、可回归、可沉淀

---

## 一、纪律（对每次实质修复/治理变更强制）

1. **修复后必登记实验卡**：任何 runtime 补丁、配置治理、代码变更 →
   `labforge new <id>` 填 goal/hypothesis/assertions（回收标准）
2. **动生产前必回归**：`labforge regress` 全量跑既有卡（防退化）
3. **动生产后必验证**：变更生效 → 相关卡 `labforge loop <id>` 确认 PASS
4. **沉淀**：结果自动落黑板（labforge-results.md）+ 向量化（guard-recall）
5. **经验回写**：实验暴露的边界/新判断 → 新卡或更新既有卡

## 二、已登记的回归实验卡（当前 4 张）

| 卡 | 类型 | 守护的修复/判断 | 状态 |
|---|---|---|---|
| memory-crash-oom-repro | crash | OOM 根因（多会话全量物化 SIGABRT）+ 帧索引治理 | ✅ pass |
| single-session-governance | crash | 单会话非崩溃源（反向证实多会话叠加）+ 治理收益 | ✅ pass |
| frame-index-perf-regression | perf | P2-1 帧索引提速/解码量（POC 固化） | ✅ pass |
| **orphan-reconcile-regression** | correctness | **孤儿 tool_calls 续跑卡死修复**（生产实证） | ✅ pass |

## 三、变更流程速查

```
修复/变更前:  labforge regress          ← 基线全绿确认
修复/变更后:  labforge loop <相关卡>     ← 断言 PASS
新修复登记:   labforge new <id> → 填卡 → labforge loop <id>
结果沉淀:     自动（黑板 + 向量化）
```

## 四、示例（本次孤儿修复登记）

- 修复：dsh-agent-loop `reconcileOrphanToolCalls` 视图级孤儿闭合（runtime 补丁 sha 5092b508）
- 卡：orphan-reconcile-regression
- 实证：明鉴快照 orphanBefore=1（call_00_uBS2KodkNh5dzhlRASgD4341）→ 修复后 0；
  健康会话 e7bfeea8 零注入（无副作用）→ 2/2 PASS
- 生产确认：明鉴已恢复正常生产运行
