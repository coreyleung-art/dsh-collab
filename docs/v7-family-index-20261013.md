# v7 家族索引（★ **19 件** + 家族索引本身）

> **生成**：2026-10-13T01:10:16+08:00 · 星桥第二任
> **★ 用途**：★ 让下一任【十秒内找到该找的那一件】 —— ★ 不必翻会话、不必考古。
> ★ 本索引不主张任何事项已闭合（S3）

---

## 一、★★★ 锚点与骨架（★ 先看这四件）

| 件 | ★ 行 | ★ sha | ★ 是什么 |
|---|---|---|---|
| `docs/distributed-agent-network-governance-plan-v7-20261012.md` | 286 | `85ae0f49b3899e57` | ★★★ **唯一锚点**（★ state_version 7）· 更正账 22+5 · §0.1.2 判据纪律 · §0.1.3 十次实证 · 九模块指针 |
| `docs/v7-progress-table-20261012.md` | 86 | `a5c73bd2223039d2` | ★★ **推进总表**（★ 优先序 ①–⑦ 逐项状态） |
| `docs/v7-skip-register-20261012.md` | 39 | `8ca3935f7cca9f5a` | ★★ **跳过项登记册**（**8 项** · ★ 每项写明「解它需要什么」） |
| `docs/v7-skip-batch-submission-20261013.md` | 61 | `ceec4aec276aafbc` | ★★ **批量呈报**（★ 8 项一页 + **建议裁决顺序**） |

## 二、★ 五份草稿（★ 正文全文 · 共 4,679 行）

| 件 | ★ 行 | ★ sha | ★ 覆盖 |
|---|---|---|---|
| `docs/v7-draft-W1-20261012.md` | 1248 | `198c500f268efc69` | ★ M1 里程碑 + M6 崩溃风险 |
| `docs/v7-draft-W2-20261012.md` | 915 | `8af0f867ab60e37e` | ★ M2 WBS + M5 验收标准 |
| `docs/v7-draft-W3-20261012.md` | 890 | `d5ceddb549c221a0` | ★ M3 协议族 + M7 未决问题 |
| `docs/v7-draft-W4-20261012.md` | 1023 | `f2e3781c492abfeb` | ★ M4 SLO + M9 四维 |
| `docs/v7-draft-W5-20261012.md` | 608 | `fa799520ffe20e19` | ★ M8 最优性评估 |

## 三、★ 裁定 · 建议 · 审查（★ 待裁与外部）

| 件 | ★ 行 | ★ 是什么 |
|---|---|---|
| `docs/v7-ruling-01-methodology-20261012.md` | 76 | ★★ **方法学裁定①**（S-1 拆两条 · SLO 拆分规格） |
| `docs/v7-subject-independence-review-20261012-ext.md` | 305 | ★★ **外部线审查**（★ 主体独立性 · 三层区分） |
| `docs/drift-scan-tightening-proposal-20261012.md` | 161 | ★ **收紧建议单①**（drift-scan 两条判据） |
| `docs/false-result-tightening-proposal-20261013.md` | 73 | ★ **收紧建议单②**（假结果 12 处） |
| `docs/v7-unfinished-inventory-v3-20261012.md` | 118 | ★ 清点件第三版（★ 登记表口径） |
| `docs/v7-outline-revised-20261012.md` | 103 | ★ v7 大纲（修订版） |
| `docs/multi-agent-writing-experience-20261012.md` | 226 | ★ 写作过程经验（★ 13 条教训 + 提示词模板） |

## 四、★ 本线新增工具（★ 11 个 · 自证 68 条）

| 工具 | ★ 自证 | ★ 管什么 |
|---|---|---|
| `tools/false-result-patterns.py` | ★ **6/6** | ★★ 假结果形态（.status/None当绿/硬编码时间） |
| `tools/selftest-audit.py` | ★ **8/8** | ★★ 恒真自证扫查 + `--run` 四分类 + 串行复核 |
| `tools/slo-target-form.py` | ★ **9/9** | ★ SLO 目标是否【可判形态】 |
| `tools/bus-pending-age.py` | ★ **5/5** | ★ 队列待投遂是否被标超时 |
| `tools/lint-inventory.py` | ★ **5/5** | ★★ 既有 lint/gate 清单（**19 条**） |
| `tools/subagent-work-checklist.py` | ★ **5/5** | ★子代理工作安排检查清单 |
| `tools/atomic-write-guard.py` | ★ **5/5** | ★ 非原子写关键文件 |
| `tools/denominator-declare.py` | ★ **8/8** | ★ 数字无口径 |
| `tools/correction-ledger-gen.py` | ★ **6/6** | ★ 从台账生成更正账 |
| `tools/live-read-guard.py` | ★ **5/5** | ★ 照拄旧读数的疑似检测 |

## 五、★ 调研与审查（★ 13 个目录 · 20,128 行）

```
research/v7-health/          research/v7-wbs/            research/v7-alert-reader/
research/v7-negctl/          research/v7-milestone-crash/ research/v7-review-V1/  ★ 已
research/v7-caliber/         research/v7-open-questions/  research/v7-review-V3/  ★ 已
research/v7-ccep/            research/v7-slo-acceptance/  research/v7-review-V4/  ★ 已
                                                          research/v7-review-V2/  ★★ 空
```

---


---


---

## ★ 六、★ 十秒找件指引

| ★ 我要… | ★ 去这 |
|---|---|
| ★ 知道【现在做到哪了】 | `docs/v7-progress-table-20261012.md` |
| ★ 知道【哪些卡着了】 | `docs/v7-skip-register-20261012.md` |
| ★ 知道【上一版哪里错了】 | v7 §0.0 + §0.0.1 |
| ★★ 知道【判据怎么写才不假】 | v7 §0.1.2 + §0.1.3 |
| ★ 看【业界对照】 | `research/v7-ccep/01-业界等价物….md` |
| ★ 看【一个模块的全文】 | `docs/v7-draft-W1..W5` |
| ★ 看【工具清单】 | `python3 tools/lint-inventory.py --prompt` |

★ 本索引不主张任何事项已闭合（S3）。


---

## ★ 七、★★ 今晚的六件新增（★ 2026-10-13 凌晨）

| 件 | ★ 行 | ★ 是什么 |
|---|---|---|
| `docs/v7-family-index-20261013.md` | 80 | ★★ **家族索引**（★ 本件） |
| `docs/v7-skip-batch-submission-20261013.md` | 61 | ★★ **跳过项批量呈报**（★ 8 项 + 建议裁决顺序） |
| `docs/false-result-tightening-proposal-20261013.md` | 73 | ★ **假结果 12 处建议单** |
| `tools/false-result-patterns.py` | 254 | ★★ **假结果形态检查器**（★ 自证 6/6） |
| `tools/selftest-audit.py` | 383 | ★★ **恒真自证扫查**（★ 8/8） |
| `tools/lint-inventory.py` | 181 | ★★ **既有 lint/gate 清单**（★ 19 条） |