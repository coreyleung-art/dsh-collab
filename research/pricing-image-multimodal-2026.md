# 图生图 + 多模态 VLM API 计费标准调研（2026）

> 调研目的：花店生意 AI 运营成本测算（AI 配图 + 花材识别/返图分析）
> 调研时点：2026-08（价格以各来源标注时点为准，汇率按 $1 ≈ ¥7.2 估算）
> 说明：OpenAI / Google / Anthropic / 智谱官方定价页存在反爬（403 / SPA），关键价格采用「官方文档镜像 + 第三方定价聚合 + 社区实测」≥2 来源交叉验证；官方价与第三方聚合价已分别标注。

---

## 结论（花店场景成本测算表）

| 场景 | 推荐方案 | 单次/每张成本 | 月成本测算（示例量） |
|---|---|---|---|
| **商品图/活动海报（AI 配图）** | 国内：通义万相 wan2.6（¥0.20/张）或 GPT Image 1 Mini Low（≈¥0.04/张） | **¥0.04–0.6/张**（主流质量 Medium 档 ¥0.2–0.6；批量低清档 ¥0.04–0.15） | 月产 100 张 ≈ **¥4–60**；月产 500 张 ≈ **¥20–300** |
| **多模态识别（花材识别/返图分析）** | 国内：Qwen-VL-Max（≈¥0.002/次）或 GLM-4.6V；海外：Gemini Flash 系列 | **¥0.002–0.04/次**（每张 1024×1024 图 + 短文输出） | 日分析 100 张 ≈ **¥0.2–4**；月 3000 张 ≈ **¥6–120** |
| **短视频/动态海报（视频生成）** | 可灵 / 即梦 / Veo 3.1 Fast | **¥0.7–7/条**（5 秒 720p–1080p） | 月 30 条 ≈ **¥21–210** |
| **重度设计师（订阅制）** | Midjourney Standard $30/月 或 即梦基础会员 ¥79/月 | 折算 ≈ **¥0.2–1/张**（含人工/排队成本） | — |

**一句话结论**：AI 配图成本已降到「每张几毛钱」量级，多模态识别低至「每张几厘钱」，花店月运营 AI 总成本可控制在 **¥50–500** 区间（视图片产量与质量档位）；若用国内 API（万相 + Qwen-VL），成本约为海外同档的 1/3–1/2。

---

## 图生图 API 定价表（官方 API 价）

### OpenAI（按图计费，失败不扣费）

| 模型 | 计费方式 | 单价 | 来源/时点 |
|---|---|---|---|
| GPT Image 2（最新旗舰） | 按张（Low/Medium/High × 3 分辨率） | Low $0.005–0.006 / Medium $0.041–0.053 / High $0.165–0.211 | CostGoat 2026-08-02；OpenAI 官方定价页（反爬） |
| GPT Image 1.5 | 按张 | $0.009–0.20 | CostGoat 2026-08-02 |
| GPT Image 1（⚠️ 2026-10-23 弃用） | 按张 | $0.011–0.25 | CostGoat 2026-08-02 |
| GPT Image 1 Mini（最便宜） | 按张 | $0.005–0.052 | CostGoat 2026-08-02 |
| DALL·E 3 / DALL·E 2 | ~~按张 $0.04–0.18~~ | **已于 2026-05-12 从 API 移除**，新项目用 GPT Image 系列 | CostGoat 2026-08-02；TokenMix 2026 |
| 免费额度 | — | 新用户 $5 免费额度（无卡），Mini Low 可生成约 1000 张 | CostGoat 2026-08-02 |

### Stability AI（积分制：1 credit = $0.01，按成功生成计费）

| 模型 | 计费方式 | 单价 | 来源/时点 |
|---|---|---|---|
| Stable Image Core | 按张（3–4 credits） | **$0.03–0.04** | Puter 2026-06-22；官方 pricing 页 |
| Stable Image Ultra（SD3.5 旗舰） | 按张（8 credits） | **$0.08** | Puter 2026-06-22；官方 2025-07-09 更新公告 |
| SD3.5 Large | 按张（6.5 credits） | $0.065 | Puter 2026-06-22 |
| SD3.5 Large Turbo / Medium | 按张 | $0.04 / $0.035 | Puter 2026-06-22 |
| 编辑/控制（Erase/Inpaint/去背景等） | 按次（5 credits） | $0.05 | Stability 官方 2025-08-01 生效表 |
| 放大 Upscale（Fast/Conservative/Creative） | 按次 | $0.02 / $0.40 / $0.60 | Stability 官方 2025-08-01 生效表 |
| 免费额度 | — | 新账号 Google 登录赠 25 credits；$10 = 1000 credits | Puter 2026-06-22 |

### Black Forest Labs / FLUX（官方 API，积分制 1 credit = $0.01）

| 模型 | 计费方式 | 单价 | 来源/时点 |
|---|---|---|---|
| FLUX.2 [pro] | 按张（像素定价） | 文生图 **$0.03 起** / 图生图编辑 $0.045 起 | BFL 官方 docs.bfl.org.cn 定价页 |
| FLUX.2 [flex] | 按张 | $0.06 起 / 编辑 $0.12 起 | BFL 官方 |
| FLUX.2 [dev] | 免费 | 本地开发（非商用） | BFL 官方 |
| FLUX1.1 [pro] | 按张（4 credits） | **$0.04** | BFL 官方 |
| FLUX1.1 [pro] Ultra / Raw | 按张（6 credits） | **$0.06** | BFL 官方 |
| FLUX.1 Kontext [pro] / [max]（图文混合） | 按张 | $0.04 / $0.08 | BFL 官方 |
| FLUX.1 Fill [pro]（局部重绘） | 按张 | $0.05 | BFL 官方 |
| 批量 | 按张数×单价 | 4 张 Kontext pro = $0.16 | BFL 官方 |

### Google Imagen（Vertex AI，按图计费）

| 模型 | 计费方式 | 单价 | 来源/时点 |
|---|---|---|---|
| Imagen 4.0 Generate | 按张 | **$0.04/张**（另一来源 $0.03，取区间 $0.03–0.04） | Future AGI 2026-08-06；tensorfeed 快照 2026-05-17 |
| Imagen 4.0 Ultra | 按张 | 更高档（未获确切数字） | Lumenfall（未验证数值） |
| 免费额度 | — | Vertex AI 新项目有一次性赠金（各区域不同） | Google Cloud 文档（未逐项验证） |

### Google Veo（视频生成，按秒计费）——花店短视频可参考

| 模型 | 计费方式 | 单价 | 来源/时点 |
|---|---|---|---|
| Veo 3.1 Standard | 按秒（含音） | $0.40/秒（720p/1080p）、$0.60/秒（4K）；Vertex 无声视频 $0.20/秒 | Modellix 转引 Google 官方 2026-07-22 |
| Veo 3.1 Fast | 按秒 | $0.10 / $0.12 / $0.30 秒（720p/1080p/4K） | 同上 |
| Veo 3.1 Lite | 按秒 | $0.05 / $0.08 秒（720p/1080p） | 同上 |
| 8 秒 1080p 一条 | — | Standard ≈ $3.20；Fast ≈ $0.96 | 同上 |
| 状态 | — | Veo 3 已退役（2026-06-30 关停）；API 无免费层 | 同上 |

### Midjourney（订阅制，无公开 API）

| 档位 | 月费 | 权益 | 折算每张 |
|---|---|---|---|
| Basic | **$10/月** | 约 200 张/月（fast GPU）、3 并发、商用授权 | ≈ $0.05/张 |
| Standard | **$30/月** | 15h fast + **无限 relax**、隐身模式 | ≈ $0.03/张（fast） |
| Pro | **$60/月** | 30h fast、12 并发、优先队列 | ≈ $0.033–0.1/张 |
| Mega | **$120/月** | 60h fast、最高优先 | — |
| 免费试用 | — | 2023 年起取消 | WeCompareAI 2026-04-13 |

⚠️ **Midjourney 无公开 API**：官方 API 自 2025 年中为邀请制 alpha（未公开定价）；第三方（fal/replicate 等）有非官方镜像，属第三方聚合价。

---

## 多模态 VLM 定价表（按 token 计费，视觉输入按图折算）

> 折算口径：1024×1024 单图 ≈ Gemini 258 tokens / GPT 765 tokens / Claude 1334 tokens / Qwen-VL 600 tokens（TokenMix 实测 2026-04-29）；Claude 官方文档：小图(<1024px)≈170、中图(≤2048px)≈270、大图(≤8192px)≈1350 tokens。

| 厂商/模型 | 输入价（$/M tokens） | 输出价 | 单图输入成本（1024²） | 来源/时点 |
|---|---|---|---|---|
| **OpenAI GPT-5.x Vision**（GPT-4o 后继） | $2.50 | $10.00 | **≈$0.0019/图** | TokenMix 2026-04-29（实测名 GPT-5.4） |
| GPT-4o（历史档，已逐步退役） | $2.50 | $10.00 | ≈$0.0019/图 | Future AGI / OpenAI 历史定价 |
| GPT-4o mini（历史档） | $0.15 | $0.60 | ≈$0.0001/图 | Future AGI / OpenAI 历史定价 |
| **Anthropic Claude Sonnet 4.5/5** | $3.00 | $15.00 | **≈$0.004/图**（最贵） | 官方定价；TokenMix 2026-04-29；BenchLM 2026-08 |
| Claude Opus 4.x/4.8 | $5.00 | $25.00 | ≈$0.0067/图 | BenchLM 2026-08；Anthropic 官方 |
| Claude Haiku 4.5（轻量） | $1.00 | $5.00 | ≈$0.0013/图 | Anthropic 官方 |
| **Google Gemini 3.1 Pro** | $2.00 | $12.00 | ≈$0.0005/图 | BenchLM 2026-08-29；TokenMix |
| Gemini 3.6 Flash / 3.5 Flash | $1.50 | $7.50–9.00 | ≈$0.0004/图 | BenchLM 2026-08-29 |
| **Gemini 3.5 Flash-Lite / 2.5 Flash（性价比推荐）** | $0.30 | $2.50 | **≈$0.00008/图** | BenchLM 2026-08-29（官方价） |
| Gemini 2.5 Flash-Lite（地板价） | $0.10 | $0.40 | ≈$0.00003/图 | BenchLM 2026-08-29 |
| **DeepSeek（官方 API 仅文本）** | V3: $0.27 / R1: $0.55 | $1.10 / $2.20 | —（官方无视觉模型） | ecomcalctools 2026-05；DeepSeek 官方 |
| DeepSeek-VL2（开源模型） | — | — | 无官方 API，走第三方（SiliconFlow/302.AI 等） | 302.AI / SiliconFlow 聚合页 |

---

## 国内厂商定价

### 图像生成 API（阿里云百炼 / 百度智能云）

| 厂商/模型 | 计费方式 | 单价 | 来源/时点 |
|---|---|---|---|
| 通义万相 wanx-v1（旧版） | 按成功输出张数 | 约 ¥0.10/张 | GitHub 镜像整理 2026 |
| 通义万相 wan2.6-image | 按张 | **¥0.20/张**（新户赠 50 张） | 阿里云官方帮助中心「模型调用计费」搜索摘要 + GitHub 镜像 2026 |
| 通义万相 wan2.7-image | 按张 | 约 ¥0.21/张 | GitHub 镜像 2026 |
| 通义万相 wan2.7-image-pro（4K 旗舰） | 按张 | 约 ¥0.54/张 | GitHub 镜像 2026 |
| 百度 文心一格 AI 作画-高级版 | 按张 | **低至 ¥0.28/张** | 百度智能云官方新闻 |
| 免费额度 | — | 万相新户 50 张（90 天内）；生成失败不扣费 | 阿里云/GitHub 镜像 |

### 国内多模态 VLM（按 token）

| 厂商/模型 | 输入价 | 输出价 | 单图成本（1024²） | 来源/时点 |
|---|---|---|---|---|
| **阿里 Qwen-VL-Max**（中国区） | **$0.229/M（≈¥0.0016/1K tokens）** | $0.573/M | **≈¥0.001–0.002/图** | 阿里云官方文档（英文版，qwen-vl-max-2025-08-13 快照） |
| Qwen-VL-Max（新加坡/国际区） | $0.80/M | $3.20/M | ≈¥0.007/图 | 阿里云官方文档 |
| 智谱 GLM-4.6V（2025-12 发布，降价 50%） | **$0.30/M** | $0.90/M | ≈¥0.003/图 | models.dev（第三方聚合）2026 |
| 智谱 GLM-4.5V | $0.60/M | $1.80/M | ≈¥0.006/图 | models.dev 2026 |
| 智谱 GLM-4V-Flash | 免费 | 免费 | ¥0 | 智谱历史定价（未在本次验证） |

### 国内订阅/积分制（即梦 / 可灵）

| 平台 | 档位 | 价格 | 权益/积分 | 折算 |
|---|---|---|---|---|
| **即梦 AI**（字节，2026 调价后） | 基础会员 | ¥79/月（连续包月 **¥41**） | 1080 积分/月，1080P、去水印 | 图片约 6–12 积分/张 → 约 100–180 张/月，**¥0.2–0.7/张** |
| | 标准会员 | ¥239/月（连续包月 ¥119） | 4000 积分/月，对口型、商用授权 | — |
| | 高级会员 | ¥649/月（连续包年 ¥5199） | 15000 积分/月，4K 导出、无限生成 | — |
| | 免费 | ¥0 | 注册赠约 800 秒视频；每日签到 60–100 积分 | 水印/720P/排队 |
| **可灵 AI**（快手，全球会员） | Standard | 首月 $6.99 / 续费 **$8.80/月** | 660 积分/月（≈33 条 720p 短视频） | 视频 6–12 积分/秒；图片约 10 积分/张 |
| | Pro | 首月 $25.99 / 续费 **$32.56/月** | 3000 积分/月 | 5 秒 1080p 无声 ≈ $0.43/条 |
| | Premier / Ultra | $80.96 / $159.99 续费 | 8000 / 26000 积分/月 | 大产量档 |
| | 免费 | ¥0 | 66 积分/天（24h 过期） | 低清带水印 |
| 可灵积分包 | 单买 | $5–1200 | 330–96000 积分，2 年有效 | 补充用，不月清 |

来源：即梦=游侠手游价目表 2026-05-21（第三方整理）；可灵=Modellix 转引可灵官方会员页/VIDEO 3.0 积分指南 2026-08-14。

---

## 订阅制对比（Midjourney 等）

| 平台 | 月费区间 | 模型 | 计费本质 | 适合花店场景 |
|---|---|---|---|---|
| Midjourney | $10–120/月（年付 8 折） | V7+（MJ 旗舰画质） | GPU 时长+无限 relax，**无公开 API** | 品牌海报/艺术风配图（设计师手动操作） |
| 即梦 AI | ¥41–649/月 | Seedance 2.0 / 图片模型 | 积分制（图片 6–12 积分/张） | 国内可用、视频+图片一体 |
| 可灵 AI | $8.8–160/月 | Kling 2.x/3.0 | 积分制（按秒/按张） | 短视频营销（花束开箱/延时） |
| 对比：官方 API 按张 | — | GPT Image/FLUX/万相 | 按成功输出张数 | 自动化流水线首选（可编程、无排队） |

**关键差异**：订阅制=固定月费+排队/人工操作，适合人工作业；API 按张=弹性计费+可编程，适合自动化批量（花店每日上新 50–100 张商品图强烈建议 API 路线）。

---

## 花店场景成本测算

### 场景 A：AI 配图（商品图/活动海报）

```
单张成本区间（¥）：
  GPT Image 1 Mini Low     0.04  ████████
  万相 wan2.6 / FLUX.2 pro 0.20  ████████████
  GPT Image 2 Medium       0.30  ████████████
  文心一格 / Imagen 4      0.28  ████████████
  FLUX1.1 Ultra            0.43  ██████████████
  GPT Image 2 High         1.20  ████████████████████
  万相 wan2.7-pro (4K)     0.54  ██████████████

月成本（按 100 张，主流 Medium 档 ¥0.2–0.6）：
  低配（Mini Low + 万相）  ≈ ¥4–20
  中配（GPT Image 2 Med）  ≈ ¥30–60
  高配（High/4K 档）       ≈ ¥54–120
```

- 批量重试成本：同图迭代 5–10 次才定稿时，按「成功张数」计费的模型（OpenAI/FLUX/万相）不额外扣费，只有 Stability 编辑/放大链路易叠加（3+5+40=48 credits/张成品）。

### 场景 B：多模态识别（花材识别 / 客户返图分析 / 评价图片质检）

```
单次成本区间（¥/张 1024² + 短文输出）：
  Qwen-VL-Max（中国区）    0.002 ██
  GLM-4.6V                 0.003 ██
  Gemini Flash-Lite        0.0006 █
  GPT-5.x Vision           0.014 ████████
  Claude Sonnet            0.03  ████████████████

月成本（日分析 100 张 → 月 3000 张）：
  国内方案（Qwen-VL/GLM）  ≈ ¥6–10
  海外性价比（Gemini Flash）≈ ¥2–20
  海外高质量（GPT/Claude） ≈ ¥40–100
```

### 场景 C：短视频营销（可选）

- 可灵 Pro 档：5 秒 1080p 无声 ≈ $0.43（≈¥3.1）；月 30 条 ≈ ¥90
- Veo 3.1 Fast：8 秒 1080p ≈ $0.96（≈¥7）；月 30 条 ≈ ¥210
- 即梦基础会员 ¥41/月（连续包月）≈ 免费额度+1080 积分，覆盖轻度视频需求

### 综合建议（花店月预算）

| 方案 | 月成本 | 说明 |
|---|---|---|
| 极简（万相 wan2.6 200 张 + Qwen-VL 3000 次） | **≈ ¥50–80** | 全国内 API，自动化 |
| 标准（GPT Image 2 Medium 200 张 + Gemini Flash 3000 次） | **≈ ¥80–150** | 海外质量+性价比 |
| 高配（GPT Image 2 High + Claude 视觉，含视频） | **≈ ¥300–600** | 品牌级输出+短视频 |

---

## 证据来源

**官方定价页/官方公告**
1. Stability AI 官方 API 价格更新（2025-07-09，2025-08-01 生效）: https://stability.ai/api-pricing-update-25
2. Black Forest Labs 官方定价（积分制全表）: https://docs.bfl.org.cn/quick_start/pricing
3. 阿里云百炼官方 qwen-vl-max 定价（英文，$0.229/$0.573）: https://www.alibabacloud.com/help/en/model-studio/qwen-vl-max
4. 阿里云百炼模型计费（万相 0.20 元/张，反爬仅搜索摘要可读）: https://help.aliyun.com/zh/model-studio/model-pricing
5. 百度智能云「AI作画-高级版 低至 0.28 元/张」: https://cloud.baidu.com/support/news?action=detail&id=3116
6. Google Developers Blog（Veo 3/3 Fast 新定价）: https://developers.googleblog.com/en/veo-3-and-veo-3-fast-new-pricing-new-configurations-and-better-resolution/
7. Google Gemini Developer API 定价（多语言镜像页）: https://ai.google.dev/gemini-api/docs/pricing
8. OpenAI 官方定价页（反爬 403，未直接读取）: https://platform.openai.com/docs/pricing

**第三方定价聚合/实测（交叉验证用）**
9. CostGoat OpenAI GPT Image 定价计算器（2026-08-02）: https://costgoat.com/pricing/openai-images
10. Puter Stability AI API 定价全解（2026-06-22）: https://developer.puter.com/tutorials/stability-ai-api-pricing/
11. TokenMix Vision API 对比实测（2026-04-29，每图 token 数与成本）: https://tokenmix.ai/blog/vision-api-comparison
12. BenchLM Gemini API 定价（2026-08-29）: https://benchlm.ai/google/api-pricing
13. WeCompareAI Midjourney 定价（2026-04-13）: https://www.wecompareai.com/pricing/midjourney
14. Modellix Veo 3.1 定价（转引 Google 官方 2026-07-22）: https://www.modellix.ai/blog/veo-3-1-price/
15. Modellix 可灵定价（转引可灵官方 2026-08-14）: https://www.modellix.ai/blog/kling-ai-pricing-per-month/
16. 游侠手游即梦 AI 收费价目表（2026-05-21）: https://m.ali213.net/news/gl2605/1775059.html
17. 阿里云万相图生图价格解析（GitHub 镜像）: https://github.com/fcb01871/aliyun-wanxiang-pricing
18. Models.dev 智谱 Zhipu 模型定价: https://models.dev/providers/zhipuai/
19. EcomCalcTools DeepSeek API 定价（2026-05）: https://ecomcalctools.com/ai/deepseek-api-cost-calculator/
20. Future AGI Imagen 4.0 Generate 定价（2026-08-06）: https://futureagi.com/llm-cost-calculator/vertex-ai/imagen-4-0-generate-001/
21. 36氪 GPT Image API 上线报道（约 0.15 元/张级）: https://m.36kr.com/p/3263597906689799
22. 智谱 GLM-4.6V 发布与降价 50% 报道（C114）: https://www.c114.net.cn/industry/42931.html
23. OpenAI 开发者社区 GPT Image 发布帖: https://community.openai.com/t/new-gpt-image-model-in-the-api/1239462

---

## 置信度与不可得

### 置信度分级

| 置信度 | 条目 | 依据 |
|---|---|---|
| **高**（官方页/多源一致） | FLUX 全系列、Stability 积分表、Qwen-VL-Max 中国区价、Gemini 全档位、Veo 3.1 按秒价、DeepSeek 文本价、Midjourney 订阅档 | BFL 官方页 / Stability 官方公告 / 阿里云官方文档 / BenchLM+官方镜像 / Modellix 转引 Google / 多源一致 |
| **中**（官方页反爬，靠镜像+聚合） | GPT Image 系列全表、万相各版本、Imagen 4（$0.03 vs $0.04 有出入）、GLM-4.6V、即梦/可灵会员价、文心一格 | CostGoat 2026-08 + 社区；GitHub 镜像 + 阿里云摘要；2 个聚合源 |
| **低**（第三方实测命名，仅供参考） | GPT-5.4/Claude 4.6/Gemini 3.1 Pro 的「单图 token 数」实测、Claude Opus 输入 $3/M（与该文其他数字矛盾，已弃用改用官方 $5/$25） | TokenMix 单源实测；neuralbase 单源 |

### 不可得/未验证项

1. **Midjourney 官方 API 定价**：仅邀请制 alpha（2025 年中起），无公开价目；第三方便宜镜像（fal/replicate）未逐项报价。
2. **OpenAI / Anthropic / Google / 智谱官方定价页正文**：反爬 403 或 SPA 渲染失败，未能直接抓取；以官方文档镜像与第三方聚合替代。
3. **DeepSeek 官方视觉 API**：DeepSeek-VL2 仅开源不自营，官方 API 仅 deepseek-chat/reasoner（文本）。
4. **即梦/可灵官方最新价目**：两家均为 C 端 App 内展示，无公开稳定 API 价目页；本报告采用第三方整理（游侠 2026-05 / Modellix 2026-08），价格 2026 年内已多次调整（即梦单月三次调价），**落地前需以 App 内实时价为准**。
5. **文心一格现行 API 价**：仅拿到「高级版低至 0.28 元/张」官方新闻，未验证现行档位与是否并入千帆/百度智能云新计费。
6. **Imagen 4 Ultra / 4K 档、GPT Image 2 图生图（编辑）价**：编辑价高于文生图（GPT 系约 1.5–2x、FLUX.2 编辑 $0.045–0.12 起），未逐项核实。
7. **人民币汇率**：按 $1≈¥7.2 估算（2026 年浮动 ±3%），未做实时汇率对冲。
