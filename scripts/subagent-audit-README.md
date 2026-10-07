# subagent-audit — 子代理全局审查器（R006 十项）

> 属主: HR 司库 · v1.0.0 · 2026-09-11 · 用途: **子代理专项审查**（存量/增量/归因/合规/资源/生命周期/跨设备）

## 解决什么
HR 裁决书（`data/registry/hr-ruling-resource-audit-20260911`）立了 P1（子代理扇出治理）/ P1.5（归档）/ P2（双轨阈值），
**但当时只有一次性测量，没有可复跑的审查器**。本工具把那次测量固化下来。

## 八个维度
| 维度 | 内容 | 判据来源 |
|---|---|---|
| **S1 存量** | 主/子计数与体积、子占比例 | P2 双轨阈值 |
| **S2 归因** | 每个父会话产出的子代理数（扇出 top-N） | P1 扇出治理 |
| **S3 增量** | 按创建日的子代理数（突发检测） | — |
| **S4 合规** | 对照上限「单父 ≤50/日」 | **P1** |
| **S5 资源** | 子代理体积/均值/占比 | — |
| **S6 生命周期** | 已完成且 >7 天的归档候选 | **P1.5** |
| **S7 孤儿** | 父会话缺失 | — |
| **S8 跨设备** | 对端节点状态；不可达则**声明 SKIP** | — |

## 关键设计
- **权威字段是会话头**（`session.jsonl.zstd` 首行 JSON 的 `origin` / `parentSession` / `agentPreset` / `delegationDepth` / `createdAt`），
  **不是文件系统时间**。★ 首跑即证明此点：`birthtime` 口径测出 09-09=98/09-10=50，而**头字段口径测出 09-10=145** —— 后者与 MBP 报告一致。
  **文件系统时间是"文件何时被创建/触碰"，头字段才是"会话何时被创建"。** 两者不等价（0c：产出同一性）。
- **子代理不是幽灵**：本次实测孤儿 0、`delegationDepth` 全为 1（扁平扇出、零递归）。
- **自检含判据来源在位探测**（读 HR 裁决书 HTTP 码）；读不到则**声明 SKIP**，不静默。

## 用法
```
subagent-audit.py run [--days 14] [--top 8] [--json] [--dry-run]
subagent-audit.py classify <session-id>
subagent-audit.py selfcheck | lean4-check | cld-check | version-check | version
subagent-audit.py --tool-version | --json-out run
```

## 落链
`~/dsh-collab/data/registry/subagent-audit-<date>.json`（⑧ 自动落链）· 日志 `~/.dsh/subagent-audit.log`

## 首跑结论（2026-09-11T01:49）
- 存量 **379 = 主 82 (751.7 MB) + 子 297 (160.3 MB)**，子占 78.4%
- 扇出高度集中：**仅 7 个父会话**产出全部 297 个；top2 = 242（81.5%）
- 突发：**2026-09-10 单日 145 个**（次高 09-09 = 27）
- **S4 合规：2 处超限**（4787d717 单日 83 = 1.7 倍；a190c54c 单日 62 = 1.2 倍）
- **S6 归档候选：114 个 / 86.5 MB**（P1.5 的落点）
- S7 孤儿 0 · S8 跨设备 mac 在线 / i9 离线(queued 3)

## 验收
`selfcheck` OK PASS · `lean4-check` OK（二分穷尽且互斥 + 上限常量为正）· `cld-check` PASS · `version-check` PASS · `--tool-version` 输出合法 JSON · `--dry-run` 零变更

## 采用记录
| 日期 | 来源 | 内容 |
|---|---|---|
| 2026-09-11 | HR 自建 | 首版；触发 = 用户「做一次全局的子代理审查」 |