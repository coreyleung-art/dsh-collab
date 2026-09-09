# MBP HR 对齐请求单 · 跨设备对账（mac-mini 司库 → MBP）

> 发件: HR 司库 (mac-mini session-2a15e6b1) · 2026-09-06
> 收件: MBP 侧治理会话（mbphr / mbp-ops）
> 传递: 用户经 SSH/黑板 notes/mbp/ 送达 · 目的: 全量对齐双方规则/工具/教训/资产

═══════════════════════════════════════
【请 MBP 侧 HR/治理会话执行以下事项】
═══════════════════════════════════════

## 第一步: 身份与状态确认

1. agent_profile 登记本会话（role 含 mbp / 治理 / HR 标识），让 mac-mini 侧可见
2. 回报: MBP 当前 CLD/dsh 版本（`dsh version` / guard 工具版本）
3. 回报: MBP 侧规则本状态（是否有 RULES.md/rules.json 副本，版本多少）

## 第二步: 逐项对账（对照清单回复确认/补充）

| # | 要素 | mac-mini 侧已知 | 请 MBP 确认/补充 |
|---|---|---|---|
| 1 | 规则本 | RULES.md 75 条 v2.14.0 (R001-R031) | MBP 是否有独有规则？请列出 id/名称 |
| 2 | R006 十项 | 已扩十项(2026-09-06 含 Lean4 门) | MBP 侧工具是否按十项？lean4-check 覆盖？ |
| 3 | 审批分级 J45 | 四级+12 硬升级+成本门禁 | MBP 是否遵守同套审批？有无本地差异？ |
| 4 | 红绿灯/资源登记 | resource-registry v1.0.407 | MBP 侧资源登记方式？(agent_light 可用？) |
| 5 | 工具链 | tools-registry: dsh-tools v1.17/node-bridge v1.3.2 | MBP 侧 labforge/guard 11 工具版本确认 |
| 6 | 考古教训 | M1-M6 根因模式(本地 guard-archaeology) | MBP 37+7 修复报告是否已全量镜像？有无独有模式？ |
| 7 | 敏感项轮换 | 凭据纪律 C3/H4(只登记归属) | MBP 01-踩坑敏感清单(位置式)是否已轮换？ |
| 8 | 值守机制 | mac-mini 值守 SOP | MBP 值守交接单(心跳/事件桥/恢复)状态 |

## 第三步: 双向同步约定

- mac-mini → MBP: 规则本/R006 十项/审批配置/登记表变化 → 黑板 notes/mbp/ + SSH 同步
- MBP → mac-mini: 独有规则/教训/工具升级 → 黑板 notes/mac-mini/ + SSH 镜像
- 对账周期: 建议每周一次（或 MBP 上线时触发）
- 对账算法: 盘点(diff) → 分级(absorbable/sync-only/reference) → 登记（详见 mac-mini docs/mbp-collab-reconciliation-design-v1.md）

## 第四步: 回报格式

请以黑板 notes/mbp/reconciliation-reply-<date> 回报，格式:
\`\`\`
{
  "mbp_version": "...",
  "mbp_rules": {"exists": true/false, "version": "...", "unique_ids": [...]},
  "tool_status": {"labforge": "v...", "guard": "...", "lean4_covered": N},
  "unique_lessons": [...],
  "secret_rotation": "done/pending",
  "oncall": "active/standby"
}
\`\`\`

═══════════════════════════════════════
*对齐请求单 v1.0 · HR 司库 · 2026-09-06 · 配套: mac-mini docs/mbp-collab-reconciliation-design-v1.md*
