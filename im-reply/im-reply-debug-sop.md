# IM 回复管道 · 排错工作流 SOP（v1）

> 归属：智能客服 session-b193c782 · 协作：de7b29de（管道）/ 协调者 fa1f9150 / HR e7bfeea8
> 版本：v1.0 · 2026-08-17 · 事故驱动（信息污染复盘）
> 适用：一切 IM 回复发送/联调/排错场景

## 0. 总原则（红线）

1. **测试与生产隔离**：联调/验证只在测试店铺/测试会话（前缀 `[TEST]`），生产会话只走审批队列
2. **管道自报不作数**：唯一验收 = watcher 采集后 `im_sessions.status=replied` + timeline 含发送内容
3. **用户确认前置**：每条生产发送须 approval_token（会话ID+内容hash+ts），服务端强制校验
4. **测试内容禁止生产**：`【】`/测试/验证/管道/忽略 → 内容白名单拦截
5. **重试有界**：同会话失败重试 ≤2 次、间隔 ≥60s、24h ≤3 条

## 1. 发送前检查清单（Pre-flight）

- [ ] 目标会话在审批队列（approval-queue.json）且 status=pending_approval
- [ ] 内容命中已审批话术库条目（非临时手写）
- [ ] 内容无测试类关键词
- [ ] 已获用户 approval_token（逐条确认/审批流）
- [ ] agent_light(im_window:N) 绿灯
- [ ] /api/im/collecting 该店 false（或接受重试）
- [ ] 持 agent_lock(im_window:N, exclusive, 短 ttl)

## 2. 发送后验收清单（Post-flight）

- [ ] 管道返回 ok（仅参考）
- [ ] **15-30s 后查 watcher**：status 是否变 replied
- [ ] timeline 是否含发送内容（人工 staff、非 auto）
- [ ] 列表 preview 是否更新为发送内容
- [ ] 三项全过 → 记 SUCCESS；任一不过 → FAILED + 告警

## 3. 排错分级（Debug Triage）

| 级别 | 现象 | 排查 | 处理 |
|------|------|------|------|
| L1 | dry-run 失败 | 读 taValue（空=注入失败）；activeElement（非 TEXTAREA=聚焦失败） | 修注入/聚焦 |
| L2 | verified 假阳性 | 不信管道；读 watcher status + 消息区 | 修验证逻辑 |
| L3 | 落区失败 | 查模态框（modalFound）/窗口态/会话匹配（key 前缀命中） | 修环境 |
| L4 | 消息污染 | 立即止损 → 核对落区清单 → 用户人工补救 | 事故流程 |

## 4. 事故流程（L4 污染）

1. **立即停止**全部发送（紧急制动）
2. 审计 actions：列所有 yes=true + 内容分类（test/customer）
3. 核对落区：查 im_sessions timeline 逐会话确认
4. 出清单给用户 → 门店员工重点注意 + 人工电话回复
5. 复盘根因 → 更新本 SOP → 登记表记录

## 5. 联调灰度阶梯（替代裸调）

```
测试店铺 dry-run → 测试店铺真发 → 生产 1 条（用户确认）→ 生产逐条确认批量
每级通过才进下一级；生产级必须走 §1 §2 完整清单
```
