# 灯塔评审 · mtm 内存治理 Lean4 方案 v1（采集域视角）

> 评审人: 灯塔 de7b29de · 2026-09-06 · 实测证据采集

## 结论: 方向认可 ✅，但 3 项前置条件必须满足后才可 Step1

## 实测证据（当前机器 24GB）
- free ~70MB / inactive ~6GB——内存确有压力，治理必要
- 10 店 Chrome ≈ 67 进程——全量物化属实
- server.js 本进程内存占用小，大头确在 Chrome 树

## 认可点
1. 平移 CLD 尾部窗口思想（全量→按需物化）= 正确方向
2. 生命周期状态机 5 态穷尽 + 预算凭证 = Lean4 纪律落地得当
3. 用户约束（不做 launchd 常驻）已被方案尊重

## 采集域 3 项前置条件（不满足即拒绝 Step1）

### ⚠️ C1: Warm 态登录态保留是最大风险（必须先 P0 预查实测）
- 方案 §3.1 Warm = "CDP 断开但 profile 保留登录态"；§七 也标注"需预查 Chrome 后台模式是否维持 cookie"
- **京东/抖音渠道实证**: 多次 CLD/Chrome 重启后 logged_out（2026-09-02/09-04 两次补登，cookie 失效需用户重输验证码）——若 Warm 依赖进程存活维持 cookie，则 Warm→Hot 可能触发重登，**需要用户在场**，非营业时间（22-08）无法恢复
- **美团渠道实证**: cookie 磁盘持久（重启不丢，6 店从未掉）——Warm 安全
- 要求: Step0 增加**分渠道 cookie 持久性实测**（美团/京东/抖音 各 Warm 24h 后查登录态），京东/抖音若脆弱→降级策略需豁免或保 Hot

### ⚠️ C2: Warm 店告警延迟必须有明确 SLA
- Warm = watcher 不 poll → 新订单/差评/IM 消息不实时
- 方案 §3.3 说"需要操作/告警时才 transition→Hot"——但**告警来源是 poll，poll 停了谁触发 transition？**（鸡生蛋）
- 要求: 明确 Warm 店轮询策略（如 5min 轻量探活 + 阈值触发 Hot），或接受延迟并登记 SLA

### ⚠️ C3: 优先级"美团4店>其他"需与运营确认
- 美团 6 店含守白(8)为测试店、佛山(7)为真实运营主力
- 京东/抖音也有真实订单监控需求（10 店全绿是运营基线）
- 要求: Hot 名单由运营确认（哪些店必须 7×24 实时），不做渠道一刀切

## 分渠道降级建议（预演）
| 渠道 | cookie 持久性 | Warm 安全 | 建议 |
|---|---|---|---|
| 美团 6 店 | ✅ 磁盘持久 | ✅ | 低活跃可 Warm |
| 京东 2 店 | ⚠️ 需实测 | 存疑 | 保守：营业时间保 Hot，非营业 Warm |
| 抖音 2 店 | ⚠️ 需实测 | 存疑 | 同上 |

## 对 Step1 改动面的评审（采集代码 owner）
- lib/chrome.js launch 加 transition 门: ✅ 可行, launch 已是唯一入口
- watcher 只 poll Hot: ✅ 需同时保留 Warm 探活线程（见 C2）
- store lifecycle 列: ✅ 向后兼容（默认 hot 可回滚, M7 governance:false）
- 建议: Step1 与现有 ensureAllRunning 并存（governance:false 时走旧逻辑），灰度切换

## 判定
- C1 未实测前: **不批准 Step1**（京东/抖音 Warm 掉登录 = 非营业无法恢复 = 违反零打扰规则）
- C1 实测安全（或分渠道豁免）→ 批准 Step1 + Step2
- 提供证据后我可配合改 watcher/chrome 并跑 M1/M2/M5 回归
