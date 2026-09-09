# 研究运营工具链 · Runbook v0.1

> 建立：2026-08-19 · HR 驾驶舱 · 目的：把成本治理/论文库/ROI 审查/沉淀过程固化为可复用工具
> ⚠️ 自动化状态：**全部定时调度 DISABLED**（成本治理指令生效中）——工具可手动触发，调度待用户恢复指令后启用

## 工具清单

| 工具 | 输入 | 输出 | 触发方式 | 自动化状态 |
|---|---|---|---|---|
| **cahac-replay.py**（统一回放 CLI v1.0） | aggregate/scenario/week/stream/compare | replays/*.md | python3 cahac-replay.py <子命令> | 手动 |
|---|---|---|---|---|
| scripts/token-roi-review.py | DeepSeek 导出目录 | token-monitor/daily-reviews/当日.md | 手动：python3 scripts/token-roi-review.py | ⛔ launchd 模板就绪未加载 |
| scripts/paper-fetch.py | arXiv ID/URL | research/paper-cache/<id>.md | 手动：python3 scripts/paper-fetch.py --urls "2604.12301" | 手动 |
| scripts/research-sink.py | research/ops-science/*.md | vault 骨架同步清单 | 手动（dry-run 可预览） | ⛔ 周检模板就绪未加载 |
| DSH 知识库 ops-science-research | knowledge_add/import_url | 论文全文库（23 篇） | agent 调用 knowledge_* | 手动/随研究 |
| Obsidian vault 编译页 | research 结论 | wiki/concepts/*.md | agent 编译 | 手动 |

## 每日审查流程（token-roi）
1. 触发：python3 ~/dsh-collab/scripts/token-roi-review.py
2. 输出：日审报告（消耗/环比/异常 🔴>2x / 模型分布）
3. agent 补充：业务产出对碰 → ROI_eff → 优化建议
4. 恢复后：launchctl load ~/dsh-collab/launchd-templates/com.dsh.hr.token-roi.plist（每日 09:00 自动）

## 论文入库流程（paper-fetch + KB）
1. 手动：python3 scripts/paper-fetch.py --urls "<arxiv ids>" → research/paper-cache/
2. agent：knowledge_import_url / knowledge_add_document(baseId=afa7de13-...) 入库
3. agent：更新 research/ops-science/research-paper-library-index.md + registry

## 沉淀流程（research-sink + vault）
1. research-sink.py 生成骨架/清单（dry-run 预览）
2. agent 编译 vault wiki 页（LLM 提炼）+ wiki/log.md 追加
3. registry 登记版本

## 启用自动化前的检查单（恢复指令到达后）
- [ ] 用户/协调者明确恢复定时自动化
- [ ] 配额/硬预算已配置（gov quota ¥75/日/agent 起步）
- [ ] token-roi 脚本 dry-run 通过
- [ ] 与 J37（插件验证）/J34（广播约束）不冲突

---
*工具链由 HR 维护 · 2026-08-19 · 对应 registry v1.0.257*