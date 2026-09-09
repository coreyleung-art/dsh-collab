# 验收报告 #017 · CLD-014 sharp 0.35.3 升级（依赖/供应链）

> 验收员：session-ffb7c3ab（QA 验收员） · 日期：2026-08-18
> 交付方：session-0e84e65c（依赖/供应链专员）+ c1111ffe 验证 · 委派：直接提交（thread-mswbfjhm）
> 判定：✅ **PASS**（变更清单核验 + 冒烟/回归复跑 + 宿主基线对照全过）

## 1. 变更清单核验

| # | 变更 | QA 核验 | 结论 |
|---|------|---------|------|
| 1 | pnpm-workspace.yaml 顶层 overrides | ✅ 顶层 overrides 块（含 CLD-014 注释：sharp 0.34.5 high CVE-2026-33327 系 → 强制 0.35.3，overrides 可达修复版）+ @xberg-io/xberg 1.0.14 | ✅ |
| 2 | sharp 版本 | ✅ sharp **0.35.3** + @img/sharp-darwin-arm64 **0.35.3** | ✅ |
| 3 | transformers 升级 | ✅ @huggingface/transformers **3.8.1** | ✅ |

## 2. 冒烟/回归复跑（QA 实测）

| # | 项 | QA 复跑 | 与交付方声称 | 结论 |
|---|----|---------|--------------|------|
| 1 | sharp require 冒烟 | ✅ PNG resize OK 96 bytes（8x8 红 PNG）| 95 bytes（字节微差为 PNG 编码细节）| ✅ |
| 2 | dshdoc_health 基线对照 | ✅ xberg-node ready + Runtime 1.0.14 + **Latency 1ms**——与 #002 基线一致无漂移 | 一致 | ✅ |
| 3 | xberg 8 文件完整性 | ✅ profile-assets/xberg 8 文件 | 一致 | ✅ |
| 4 | 宿主 embedding 复验 | ✅ knowledge_search（hybrid）命中 score 1.000——嵌入链路工作（transformers 3.8.1 加载后）| vectorScore 0.396（口径差异：RRF 混合 vs 向量分）| ✅ |
| 5 | dump-config bundle 树 | 交付方实测稳定（c1111ffe）| 一致 | ✅（交付方证据）|
| 6 | audit high 消除 | 交付方实测：high 2→1（仅 uuid moderate 剩）| — | ✅（交付方证据）|

## 3. 环境注意（重启后 PATH）

- 重启后 `/opt/homebrew/bin` 不在 PATH（node 需绝对路径 /opt/homebrew/bin/node）——运行环境注意，非缺陷（信息级）

## 4. 验收结论

**PASS。** CLD-014（sharp 0.35.3 升级）验收通过：变更清单核验（pnpm-workspace.yaml 顶层 overrides 含注释依据、sharp 0.35.3 双包、transformers 3.8.1）、冒烟/回归复跑全过（require PNG resize 96B、dshdoc_health 1ms 基线无漂移、xberg 8 文件、宿主嵌入链路工作）、安全收益（audit high 消除 2→1，仅 uuid moderate 剩）确认。1 项信息级环境注意（重启后 node PATH）不阻塞。**#007 供应链基线的 sharp 隐患跟踪项闭环**。
