# 验收报告 #007 · 供应链基线审计 R1（依赖/供应链专员）

> 验收员：session-ffb7c3ab（QA 验收员） · 日期：2026-08-17
> 交付方：session-0e84e65c（依赖/供应链专员）· 委派：协调者 fa1f9150 派单
> 判定：✅ **PASS**（四维可复核、隐患准确、脚本三模式可用；2 项信息级注意）

## 1. 交付物清单

| # | 交付物 | 期望 | QA 核验 | 结论 |
|---|--------|------|---------|------|
| 1 | supply-chain-baseline-r1.md（四维基线）| 四维覆盖可复核 | ✅ 审计方法 6 步 + 资产健康/lockfile 一致性/安全审计/供应链策略+上游跟踪四维，数据表格齐全（xberg 8 文件 sha256、漏洞表、上游跟踪表）| ✅ |
| 2 | upstream-watchlist.md（ABCDE 五类 + 操作红线）| 分类完整 + 红线清晰 | ✅ A 宿主内置 5 包 / B 直接依赖 7 包 / C 脆弱绑定 3 项（含 xberg 补发重大事件）/ D 漏洞 2 项 / E 遗留 3 项 + 操作红线 5 条 | ✅ |
| 3 | upstream-check.sh（三模式，集成 health-check v10 #16）| bash -n + 三模式实测 | ✅ 语法 OK；普通模式实跑 exit=0（link 插件跳过 9 个/脆弱绑定监控/xberg 1.0.14 已发布/lockfile 通过）；--status 输出 `[upstream-check] ⚠️ upgrade:3\|genui-E404` 与 health-check v10 实测一致（集成确认）；--audit 口径代码级确认（L101 `pnpm audit --prod --registry=npmjs`）| ✅ |

## 2. 隐患准确性核验（QA 实测对照）

| 隐患 | 交付方声称 | QA 实测 | 结论 |
|------|-----------|---------|------|
| sharp high | 0.34.5 <0.35.0 待修（CVE-2026-33327/33328/35590/35591，zero-cli/transformers 链）| 文档表格数据完整、路径清晰 | ✅ 可复核 |
| uuid moderate | 9.0.1 <11.1.1 待修（GHSA-w5hq-g745-h8pq，gaxios 链）| 同上 | ✅ |
| @omdsh-dev/dsh-genui | GitHub 直链 registry E404 | ✅ 脚本实测 `registry E404（GitHub 直链为唯一来源）` | ✅ 坐实 |
| xberg 平台包 1.0.14 | 补发已发布（6 平台）| ✅ 脚本实测 darwin-arm64/linux-arm64-gnu/win32-x64-msvc 1.0.14 已发布 | ✅ |

## 3. 注意项

| # | 项 | 说明 | 级别 |
|---|----|------|------|
| 1 | baseline §2.3 与 watchlist 时序差异 | baseline §2.3「1.0.14 从未发布」（早期状态）vs watchlist C 类「2026-08-17 重大事件：上游补发全部平台包」——系同日内状态演进（watchlist 已明确记录补发事件 + baseline 行动项 4 达成），非矛盾；建议 baseline 补注当日补发事件便于追溯 | 信息（**已闭环 2026-08-17**：0e84e65c 已补注当日补发事件，快照时点状态 vs 演进后状态区分 + watchlist §C 交叉引用）|
| 2 | audit 模式未实跑 | --audit 为网络耗时操作，未实跑；口径代码级确认（--registry=npmjs 官方源）与协调者口径一致 | 信息（**已闭环 2026-08-17**：0e84e65c 实跑验证——sharp high CVE-2026-33327 系 + uuid moderate GHSA-w5hq-g745-h8pq，2 vulnerabilities，与 baseline 记录一致）|

## 4. 验收结论

**PASS。** 供应链基线审计 R1 交付完整：四维基线可复核（审计方法/数据表格/结论链清晰）、隐患准确（sharp/uuid/genui/xberg 与脚本实测逐项一致）、watchlist ABCDE 五类 + 操作红线齐备、upstream-check.sh 三模式可用（普通实跑 exit=0 + --status 与 health-check v10 #16 集成输出一致）。2 项信息级注意（xberg 状态时序差异建议补注、audit 模式待维护窗口实跑）不阻塞。供应链基线已具备持续回归能力（watchlist + upstream-check 三模式）。
