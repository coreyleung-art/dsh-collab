# 图生图/多模态落链任务进度（data/blueprint/4787d717-i2i-vlm-progress）

> 4787d717 · 2026-08-30 · 用户指示：图生图/多模态模型文档+论文+计费 落链

## 论文部分（分两阶段）
- ✅ 已落：多模态 LLaVA(2304.08485)/Qwen-VL(2308.12966)/InternVL(2312.14238)/Flamingo(2204.14198)（papers-db 已有）
- ⏳ 待落（网络恢复后）：图生图核心 5 篇——SD(2112.10752)/SDXL(2307.01952)/DALL-E2(2204.06125)/Imagen(2205.11487)/DeepFloyd(2312.00195)
- 🚧 阻塞：arXiv 系（arxiv.org/export.arxiv.org/ar5iv）当前全部不可达（curl 35 连接重置，2026-08-30 实测）；semantic scholar 限流(429)、huggingface 不可达。ID 清单+流水线就绪，网络恢复即补。

## 计费部分（进行中）
- 调研子代理（ed6cd2eb）web_search 调研中：图生图 API（OpenAI/Stability/Midjourney/Imagen/Flux/即梦/可灵/万相）+ 多模态 VLM（GPT-4o/Claude/Gemini/DeepSeek-VL/Qwen-VL/GLM-4V）定价 + 花店场景成本测算
- 产出：research/pricing-image-multimodal-2026.md（预计）

## 技术文档部分
- 厂商官方文档/定价页：随计费调研抓取（web_search 渠道）
- 官网 PDF（GPT-4o 等）此前已验证 arXiv 版更稳；非 arXiv 报告按需

## 下一步
1. 计费报告完成 → 落链 research/ + KB
2. 网络恢复 → 图生图 5 篇 PDF 落链（流水线一键）
3. 汇总回报
