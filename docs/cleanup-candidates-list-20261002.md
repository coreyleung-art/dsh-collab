# 清淤候选清单（破坏性项 · 待批准）

> 2026-10-02 · mac-mini · 星桥（session-fa1f9150）
> **原则**：本清单**只列不动**。任何删除/移动都等用户批准；批准后按「移入 `~/dsh-collab/guard/archive/`」执行（保留溯源，可回滚），而非直接 rm。

---

## 1. Gen1 已死目录（最后活动 25 天+，有明确 Gen2 替代）

| 目录 | 大小 | 最后活动 | 处置建议 |
|---|---|---|---|
| `~/.dsh/bus-bridge/` | 28K / 2 文件 | 2026-09-06 | 归档。Gen1 HTTP 任务桥，已被 node-bridge 取代 |
| `~/.dsh/bus-queue/` | 144K / 36 文件 | 2026-09-06 | 归档。Gen1 任务队列实盘 |
| `~/.dsh/outbox/` | 0B | — | 归档。已空 |
| `~/.dsh/exlink-blackboard/` | 4K / 1 文件 | 2026-08-26 | 归档。外链黑板架构 Gen1 |
| `~/.dsh/capture/` | 28M / 2 文件 | 2026-08-18 | 归档（28M 是 events jsonl 历史） |
| `~/.dsh/queue-drain-backups/` | 14M / 4 文件 | 2026-08-31 | **先留**——是 08-31 事故的 bus 快照，考古价值，等本文档获批后单独处理 |

## 2. 孤儿脚本（35 个，无人引用）——按信心分级

- **A 级 · 确信死（Gen1 时代 + 明确替代）**：`cahac-replay-v0.1/v0.2/week/daily.py`、`blackboard-server-v0.5.py`（v0.6 在跑）、`i9-chat-10min.py`、`i9-poll-seconds.py`、`panel-event-adapter.py`、`research-sink.py`、`archived-daily-review-group.py`
- **B 级 · 疑似手动工具（有 R006/治理价值，建议归档到 guard/archive 而非删除）**：`gate-auditor.py`、`gate-conformance.py`、`gate-repairer.py`、`gate-j23-lean4.py`、`gate-j24-lean4.py`、`gateway-security-check.py`、`tier-gate-test.py`、`pitfalls-cli.py`、`dev-sandbox.py`、`table-integrity-check.py`
- **C 级 · 待人工确认**：`bb-blueprint-content-check/dialog/integrity.py`、`bb-proxy.py`、`bb-recon.py`、`bb-gallery-gate.sh`、`backup-chain-retest.sh`、`cldvoice-activate.sh`、`gen-zhaoshang-ppt.py`、`merge-wg100.py`、`start-blueprint-gallery.sh`、`waimai-replay.py`、`weekly-summary.py`、`xingduo-wake.py`
- **注意**：本判据是「脚本名未被任何脚本/plist/插件引用」——**手动工具不会被引用**，故 B/C 级大概率是误判为孤儿；A 级才建议归档。

## 3. dist 二进制版本堆积（不删，只标基线）

| 目录 | 版本数 | 当前基线 | 建议 |
|---|---|---|---|
| `rust-bridge/dist/` | 16 个（v1.0.0→v1.4.2 含 .bak） | **v1.4.2**（今日部署） | 保留最近 3 版 + 全部 .bak 入 archive；写一个 `CURRENT.txt` 标基线 |
| `rust-tools/dist/` | 多个 | **v1.12.2**（今日部署） | 同上 |
| `rust-blackboard/dist/` / `rust-blackboard-mcp/dist/` | 多个 | v0.6.8 / v0.8.4 | 同上 |

## 4. 惰性残骸（profile node_modules，preflight C 项已识别，不判红）

- `~/.dsh/profiles/node_modules/@deepseek-ai/*.bak-*/` 与 `*.pnpmcopy-*` 共 **100 个目录**。
- 建议：移入 archive；**不动**任何裸包名目录（C 项真遮蔽判据依赖它们解析正确）。

## 5. 明确**不清理**的（防止误伤）

| 对象 | 原因 |
|---|---|
| `~/.dsh/inbox/.processed/`（8,609 文件/34MB） | node-bridge **llm_loop 的消费台账**仍在用（防 LLM 消息重复执行），轮转修复后增长已受控 |
| `~/.dsh/inbox/bb/*.jsonl` | 订阅台账，v1.12.2 已轮转有界 |
| `~/dsh-collab/datasets/`、`learning/`、`research/` | 业务资产 |
| `~/.dsh/backups/`（623M） | 历史回滚点，清理需单独评估 |
| `queue-drain-backups/` | 见 §1，考古价值 |

## 6. 批准方式

用户对每一节说「批」/「留」即可；批准项移入 `~/dsh-collab/guard/archive/YYYYMMDD-<name>/`（mv 而非 rm），并在此文档下方记录执行结果。
