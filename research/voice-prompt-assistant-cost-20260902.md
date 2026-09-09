---
title: "语音对话→思路梳理工具 — 成本分析与技术选型"
tags: [research, wiki, report, voice, cost]
updated: 2026-09-02
---

# 语音对话→思路梳理工具 — 成本分析与技术选型

## Summary

面向「语音对话 → 思路梳理 → 结构化 prompt」工具（内部打磨后对外服务外卖商家），语音层选型四候选：字节 SeedRealtime（云 API 全双工）、Qwen2.5-Omni-7B（本地开源）、MiniCPM-o-4.5（本地开源）、Pipecat/LiveKit（对话编排框架）。成本核心结论：本地 7B 级模型（Qwen-Omni INT4≈4-5GB 显存）可将边际成本压到近零，适合多商家规模化；SeedRealtime 效果最好但按「时长+流」计费、成本随并发线性涨。产品核心壁垒不在语音技术而在「引导式梳理→prompt 质量」。

## 结论

1. **本地 7B 级开源模型是成本最优解**：Qwen2.5-Omni-7B（Apache-2.0）FP16≈14GB 显存，INT4 量化可压到 ~4-5GB，消费级 GPU 可跑；推理快（每秒数十 token）、可多实例并发 → 自建边际成本趋近零（仅电费），适合服务大量外卖商家。来源：[[raw/research/2026-09-02-voice-prompt-assistant/01-ai研究-129-qwen2-5-omni-7b-要点-显存-上下文-并发与成本_omnicoder-csdn博客]] + Qwen 官方 README。

2. **字节 SeedRealtime 效果最好但成本结构不同**：音视频全双工（一个模型边听边说），豆包已上线；计费从「按 token」变为「按时长+流量+并发路数」——每路并发持续消耗，规模化成本线性上升。适合「体验优先」的少量高价值会话（如商家 VIP 辅导），不适合大批量低成本。来源：[[raw/research/2026-09-02-voice-prompt-assistant/02-字节全双工-京东流式视频编辑-为什么全模态实时交互会成为下一个-api-新品类-yesapi-pro]]。

3. **MiniCPM-o-4.5（9.37B）是 Qwen-Omni 的竞品候选**：OpenBMB 出品 Apache-2.0，同样本地可部署；选型需实测两者在中文语音对话 + 引导式提问场景的表现（MiniCPM-o 强在多模态理解，Qwen-Omni 强在 OmniBench 全模态基准）。

4. **架构建议分层**：语音层（ASR/TTS 或全双工模型）是「输入管道」，核心价值在「梳理引擎」（LLM 引导式追问 → 攒要素 → 输出结构化 prompt）。语音技术可后接（Phase 2），先用文本对话打磨梳理引擎（Phase 1），避免被语音技术复杂度拖累产品验证。

## 证据与来源

| 来源 | 可信度 | 要点 |
|------|--------|------|
| [[raw/research/2026-09-02-voice-prompt-assistant/01-ai研究-129-qwen2-5-omni-7b-要点-显存-上下文-并发与成本_omnicoder-csdn博客]] | 二手(CSDN) | Qwen2.5-Omni-7B：FP16≈14GB 显存、INT4≈4-5GB、32k 上下文、Apache-2.0、本地免费、多实例并发 |
| [[raw/research/2026-09-02-voice-prompt-assistant/01-raw-githubusercontent-com]] | 一手(Qwen 官方) | Qwen2.5-Omni 官方 README：架构/部署/能力 |
| [[raw/research/2026-09-02-voice-prompt-assistant/02-raw-githubusercontent-com]] | 一手(MiniCPM-o 官方) | MiniCPM-o 官方 README：能力/部署 |
| [[raw/research/2026-09-02-voice-prompt-assistant/02-字节全双工-京东流式视频编辑-为什么全模态实时交互会成为下一个-api-新品类-yesapi-pro]] | 二手(行业分析) | SeedRealtime 全双工特征 + 计费模式变化（按流/时长/并发） |

## 噪音排除记录

- SeedRealtime 定价页（volcengine 产品页）SPA 无法抓取 → 未采信具体单价（待官方定价文档补充）。
- AIxploria 等聚合站返回 403 → 未采信其二手数据。
- 多个 SEO 转载站内容同源 → 保留最原始 CSDN 一篇。

## 局限

- SeedRealtime 具体 API 价格未获取（官方定价页动态渲染）→ 成本对比中该列为「估算/待验证」。
- 未实测 Qwen-Omni vs MiniCPM-o 在本场景（引导式中文对话）的实际表现 → 选型需 Phase 1 后实测。
- 本地部署硬件假设 i9/MBP 现有 GPU 能力未验证（需后续设备实测）。

## Sources

- [[raw/research/2026-09-02-voice-prompt-assistant/_sources]] — 来源台账
