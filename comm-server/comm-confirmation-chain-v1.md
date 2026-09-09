# 通讯闭环证明链（Lean4 防「投递=完成」假闭环）v1 · 2026-09-09 星桥
> 用户指出：把「守护收到」当「端侧完成」= 假闭环，导致 i9 双方互等
> Lean4 解法：两级确认证明链——让「未确认的完成」在状态机上不可表达

## 一、问题（实测教训）

```
当前状态机: queued → processing → done
                 └──── 守护 dispatch 后 reply_task(True) 即 done ← 假闭环!
守护只能声明「已转写黑板」，却冒充「agent 处理完成」→ done 无证明
后果: i9 守护收到(received_by:i9-daemon)被我当「完成」，实际 i9 agent 未处理未回签
      → 双方互等死锁（我在等回签，i9 在等我确认）
```

## 二、Lean4 设计：两级确认证明链

### 2.1 状态机（让假 done 不可表达）
```
queued ──receive──→ processing ──守护送达──→ delivered ──agent处理──→ done
                                                    └─agent处理完+回执─→ done
失败路径: queued/received/delivered 超时 → failed(带阶段标注: failed@delivered)
```
**不变量（Lean4）**：
- `done ⟹ 已 delivered ∧ 已 agent-processed`（done 必须两级证明齐全）
- 守护**只能**声明 delivered（它只证明转写动作存在）
- agent 处理完回执才是 done（证明「端侧真的响应了」）
- 违反即类型错误：守护代码里 `reply_task(done)` 根本编译不过（结构不可表达）

### 2.2 实现（bus-bridge + 守护改造）
- **bus-bridge**: 状态加 `delivered`; `/bus/reply` 的 ok 分两级——`{ok:true, stage:'delivered'}` 标 delivered;
  `{ok:true, stage:'done'}` 才标 done（须来自 agent 侧或带 agent 回执字段）
- **守护 dispatch**: reply 改标 `delivered`（不再 done）; 附 `delivered_by:<daemon>`
- **agent 处理**: 任务若 `reply_required:true` → agent 处理完回执 `stage:done`（agent 主动回）
- **纯通知类**(不需 agent 响应): 显式 `notify_only:true` → delivered 即算终态(设计上排除假闭环——不是漏确认, 是明确无需确认)

### 2.3 Lean4 断言（convention-lean4-check.py）
| 断言 | 校验 |
|---|---|
| G-C31 two-stage-confirm | 守护 reply 标 delivered 非 done(代码含 stage 区分) |
| G-C32 done-requires-agent | done 状态须 agent 回执(reply_required 任务未 agent 回→GATE FAIL) |
| G-C33 no-false-done | 守护代码无「dispatch 后直接 done」路径(结构检查) |

## 三、落地优先级
- P0: 守护 dispatch reply 改 delivered（立即消除假 done 源）
- P0: bus-bridge 状态机加 delivered（服务端支持两级）
- P1: 签署类/需确认类任务带 reply_required → 强制 agent 级确认
- P1: 纯通知 notify_only 显式标注（排除假闭环嫌疑）

## 四、验证
- [ ] 守护 dispatch 后任务状态 = delivered(非 done)
- [ ] i9 类端侧无 agent 处理 → 任务滞留 delivered 可见(不再假 done)
- [ ] 协调者看到 delivered 未 done → 知道「送达未处理」→ 不再误判完成
- [ ] 假闭环在状态机上不可表达(守护无 done 权限给他人任务)

---
*星桥 2026-09-09 · Lean4 两级确认 · 防投递=完成假闭环*
