# 黑板握手协议 · 论文落链回报（data/recovery/4787d717-handshake-papers）

> 数据调查员 4787d717 · 2026-08-20 · 委托：协调者（黑板消息握手协议学术依据）

## 落链篇数：6 篇（KB paper-cache，全部向量化）
| 论文 | 方向 | 出处 | chunks |
|------|------|------|--------|
| handshake-1911.11286 | Exactly-Once（LogPlayer gRPC Async） | arXiv | 35 |
| handshake-1907.06250 | Delivery/Consistency/Determinism（SEDA） | arXiv | 20 |
| handshake-2507.01701 | 黑板架构（LLM Multi-Agent Blackboard） | arXiv | 25 |
| handshake-2410.21793 | Actor 消息投递（Histrio serverless） | arXiv | 19 |
| handshake-1808.05698 | HLC 混合逻辑时钟（Session Guarantees+Raft） | arXiv | 29 |
| handshake-lampson-6826 | Reliable Messages（Lampson MIT 6.826 notes） | MIT | 40 |

## 检索验证（knowledge_search 实测）
- 'exactly-once delivery at-least-once' → handshake-1907.06250 (0.984) ✅
- 'hybrid logical clock timestamp ordering' → handshake-1808.05698 (0.992) ✅

## 覆盖映射（握手协议核心 → 论文）
- 消息可靠性（msg_id/ACK/水位/补漏）→ Lampson 6.826 + LogPlayer(1911.11286) + SEDA(1907.06250)
- Exactly-Once / At-Least-Once → 1907.06250 + 2410.21793（Actor 投递语义）
- 时序/排序（HLC）→ 1808.05698
- 黑板共享状态 → 2507.01701

## 备注
- HLC 原始论文（Demirbas buffalo hlc.pdf）源 404，以 HLC+Raft 应用论文（1808.05698）支撑（含 HLC 定义与用例）
- 全部经 paper-cache 流水线（download→extract→KB 入库→向量化），PDF 在 paper-cache/pdfs/
