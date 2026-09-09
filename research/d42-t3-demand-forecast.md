# 蓝图 d4-2-T3 需求预测模型前置调查 · 花卉零售需求预测

> 调研子代理产出 · 2026-08-31 · 服务对象：垂直引擎数据侧（order_sales 13 个月数据）
> 本地锚定：paper-cache 2608.14106（Forecast Collapse）、2608.14054（RAEF/RAG-forecasting）、2608.14096（OWMS 截断需求）、2608.14198（MINT 零样本预测器）

---

## 结论（推荐路线）

**一句话：13 个月花店数据（259 天、20610 订单行）做预测，主路径是「带节日因子 + 日历/促销特征的梯度提升树」，跨 SKU/跨店共享的时序模型（DeepAR 类）做放大，LLM 只做节日脉冲判断与少样本辅助，不做主预测。**

理由（三条硬约束 + 一条本地论文启示）：

1. **数据量小、仅 1 个年周期**：13 个月 ≈ 只覆盖 1 轮「情人节→七夕→教师节→年节」年季节循环。深度模型（LSTM/Transformer/DeepAR）和 LLM/时序基座模型（Chronos/Moirai/TimesFM）需要多年周期或大量序列才能稳定学到季节与跨年对比；让它们从 259 天里自学习节日脉冲，样本严重不足。
2. **节日脉冲强且稀疏**：鲜花需求由「情人节/七夕/母亲节/教师节/520」等脉冲主导，一年只有 ~10 个脉冲点。稀疏脉冲靠**显式日历因子/节日因子**注入，比让模型从原始序列自学习更可靠、可解释、可外推。
3. **成本-精度比**：13 个月小样本下，LightGBM/XGBoost + 特征工程通常优于或持平深度模型与 LLM（对齐 TUM PlantGrid 结论「ML 优于经典时序 on 园艺销售」）；LLM 每推断一次成本高、且小样本零样本精度无优势。
4. **本地论文启示**：2608.14106 警告「纯 MSE 目标会压平预测振幅（forecast collapse）」——花店节日脉冲恰是需要振幅的场景，训练目标要兼顾**校准 + 振幅/排名**（CalibRank 思路）；2608.14096 提示花店存在**截断需求（censored demand，售罄=真实需求被截断）**，建模时需处理；2608.14054（RAEF）提示少样本/领域适配可走**检索增强**而非重训。

---

## 方法对比表

| 方法族 | 代表模型 | 适用场景 | 最小数据需求 | 小样本精度 | 成本 | 花店适配度 |
|---|---|---|---|---|---|---|
| 统计时序 | ARIMA / ETS | 平稳、无强外生变量 | ≥2 年周期 | 中（弱于 ML） | 极低（CPU） | ★★ 可做基线 |
| 可分解时序 | **Prophet** | 强季节 + 多假日 | ≥1 年，**天生支持假日表** | 中 | 低 | ★★★★ 基线首选 |
| 梯度提升树 | **LightGBM / XGBoost** | 表格特征（日历/促销/价格/滞后） | 1 年可起步 | **高（小样本之王）** | 低（CPU） | ★★★★★ 主模型 |
| 概率深度学习 | **DeepAR** | 跨 SKU/跨店共享、概率分位数 | 多序列（跨 SKU 放大） | 中高（靠 pooling） | 中（GPU） | ★★★★ 数据放大 |
| Patch/全局 Transformer | PatchTST / Moirai | 长序列、跨序列 | 大量序列/长历史 | 中（需微调） | 中高 | ★★★ 需微调 |
| 纯 Transformer | Informer/Transformer | 长序列 | 长历史 | 低-中 | 中 | ★★ |
| 时序基座模型 | Chronos / TimesFM / TimeGPT / Moirai | 零样本/少样本 | 预训练，可零样本 | 中（零样本不稳） | 中-高（API/推理） | ★★★ 节日脉冲难 |
| LLM 重编程 | **Time-LLM** | 文本-时序对齐、少样本 | 冻结 LLM + 小头 | 中 | 高（LLM 推理） | ★★ 实验性 |
| LLM 直接预测 | GPT/Claude 直接给数字 | 无表头场景、人工判断 | 无需训练 | 低（幻觉/校准差） | 最高 | ★ 仅辅助 |
| 检索增强预测 | RAF / RAEF(2608.14054) | 少历史领域适配 | 检索库 + 基座 | 中高（免微调） | 中 | ★★★ 阶段4 备选 |

> 关键结论：**小样本 + 强外生（节日/促销）→ 梯度提升树 > 纯时序 > 深度 > LLM**；深度/基座模型的价值在于「跨 SKU 共享学习」与「概率分位数」，而非单序列精度。

---

## 垂直案例（含 arXiv ID）

**鲜花/园艺/生鲜零售直接对标：**

| 案例 | 出处 | 要点 |
|---|---|---|
| Machine Learning Outperforms Classical Forecasting on Horticultural Sales Predictions | TUM PlantGrid，*Machine Learning with Applications* 7 (2022) 100239；代码 [grimmlab/HorticulturalSalesPredictions](https://github.com/grimmlab/HorticulturalSalesPredictions) | **德国 5 个园艺零售销售数据集，ML 优于经典时序**（SARIMA/ETS）；最直接的可迁移垂直证据 |
| FreshRetailNet-50K（生鲜零售截断需求） | [arXiv:2505.16319](https://arxiv.org/abs/2505.16319) | 生鲜零售**售罄标注的截断需求数据集**，用于潜在需求恢复 + 预测；花店售罄同理 |
| Floro-X：花商库存预测减少损耗 | IIT Sri Lanka（dlib.iit.ac.lk） | 面向花商（florist）的**库存/损耗最小化**预测系统 |
| Anthurium Floriculture 价格预测（火鹤花） | Zenodo 2026 records/20034493 | 鲜切花价格预测 + 可持续评估 |
| 鲜切花价格预测平台（智能算法） | 中国农科院机构知识库 | 鲜切花价格预测设计（国内视角） |
| 情人节鲜花销售分析预测平台 | CSDN（Java+Vue 实现） | 工程落地示例（非学术，作参考） |

**本地 paper-cache 可衔接（无需重查）：**

| arXiv ID | 题目 | 对花店预测的启示 |
|---|---|---|
| 2608.14106 | Forecast Collapse in Time-Series Foundation Models | 纯 MSE 会**压平振幅**；节日脉冲场景需平衡校准与振幅（CalibRank） |
| 2608.14054 | RAEF（Retrieval-Augmented Extended Forecasting） | 少历史领域适配可用**检索增强**替代微调，省算力 |
| 2608.14096 | Resource-Adaptive Primal-Dual Learning for OWMS with Censored Demand | **一仓多店 + 截断需求**的资源自适应学习；花店连锁总仓分货直接相关 |
| 2608.14198 | MINT: A Universal Zero-Shot Predictor | 基座模型零样本预测器（金融交易序列，方法可迁移） |
| 2608.14270 | TimeSage-EV | 时序基座模型**持续演化的在线评测基准**（选型时可参考评测口径） |

**方法论权威锚点（arXiv ID 已交叉核实）：**

| arXiv ID | 模型/工作 |
|---|---|
| 1704.04110 | DeepAR（概率预测 + 自回归 RNN，跨序列共享） |
| 1905.10437 | N-BEATS（纯深度可解释基础扩展） |
| 2211.14730 | PatchTST（补丁式时序 Transformer） |
| 2310.01728 | Time-LLM（LLM 重编程做时序预测） |
| 2310.03589 | TimeGPT-1（Nixtla 首个时序基座模型） |
| 2310.10688 | TimesFM（Google 解码器型时序基座） |
| 2402.02592 | Moirai（Salesforce 通用掩码编码时序基座） |
| 2403.07815 | Chronos（语言式时序 token 化） |
| 2405.02358 | A Survey of Time Series Foundation Models（基座模型综述） |
| 2505.16319 | FreshRetailNet-50K（生鲜截断需求） |

---

## 数据需求与缺口

### 需求预测理想所需数据（对照花店现状）

| 数据项 | 作用 | 现状（order_sales 13 个月） | 缺口 |
|---|---|---|---|
| 历史销量/金额 | 核心目标与滞后特征 | ✅ 有（20610 订单行，259 天，含商品级明细） | 无 |
| 价格（原价/实付/折扣） | 价格弹性、促销影响 | ✅ 有（原价销售额/实付销售额/总补贴/商家/平台补贴） | 无 |
| 促销/活动 | 促销脉冲特征 | ⚠️ 部分有（优惠活动字段、补贴），但活动**强度/类型未结构化** | 需结构化活动标签 |
| 节日/日历 | 节日脉冲 + 星期/月度 | ⚠️ 可由「日期」字段推导（含农历节日需外部历法表） | 需建节日历法表（含农历七夕/春节） |
| 天气 | 生鲜/鲜花需求敏感 | ❌ 无 | **缺**（可接天气 API 回填历史） |
| 流量/曝光 | 漏斗上游、需求先导 | ❌ 无 | 缺（美团流量报表可补） |
| 库存/售罄 | 截断需求修正（censored demand） | ❌ 无 | **缺**（售罄日真实需求被低估，需标注） |
| 多年历史 | 年季节性与跨年对比 | ❌ 仅 1 年 | **缺**（无法稳定学跨年季节） |
| 竞品/商圈 | 外部冲击 | ❌ 无 | 低优先 |

### 13 个月数据够不够？

**结论：够做「周/日级 + 节日因子」的 ML 基线，不够做「深度/基座模型的年季节自学习」，也不够支撑可靠的 LLM 零样本。**

- ✅ 够：日级聚合后 259 个样本点，加日历/促销/价格特征，LightGBM 可起步；Prophet 假日表可显式建模脉冲。
- ⚠️ 边缘：1 个年周期无法交叉验证「今年情人节 vs 去年情人节」；脉冲点每类节日仅 ~1 个样本，**节日效应须靠先验因子而非统计学习**。
- ❌ 不足：深度模型（LSTM/Transformer）需多年周期才稳定；时序基座模型零样本对「强脉冲 + 短历史 + 无天气」场景精度无保障（对齐 2608.14106 的预测塌缩风险）。

### 最优先补数（按 ROI）

1. **售罄/库存标注**（把「卖完下架」日标出来 → 截断需求修正，直接提升节日备货预测）
2. **节日历法表**（含农历七夕/春节/情人节/母亲节/教师节 + 提前 3-7 天预热窗口）
3. **天气历史回填**（13 个月，API 可一次回填）
4. **流量/曝光报表**（漏斗上游先导指标）

---

## 节日效应建模

鲜花行业的脉冲是「提前预热 + 当日爆发 + 尾日回落」三段式，单一哑变量不够。

**推荐建模手段（按优先级）：**

1. **节日哑变量 + 提前/滞后窗口**：对每个目标节日设「节日当天」「节前 -3~-7 天」「节后 +1 天」哑变量，捕获预热与尾日。
2. **Prophet 假日表（holidays）**：`lower_window`/`upper_window` 直接建模脉冲宽度，最适合 1 年数据起步。
3. **Fourier 季节项 + 月度/星期哑变量**：捕获周内（周末花量高）与月度基频，避免模型把节日脉冲误当趋势。
4. **脉冲/干预变量（intervention / transfer function）**：对强脉冲日单独设脉冲变量，显式给定振幅先验。
5. **分位数预测（DeepAR/quantile LightGBM）**：节日备货应输出 P50/P90 而非点预测，用分位数管理「备多 vs 损耗」的库存风险。
6. **跨年锚定**：若后续补足第 2 年数据，用「去年同期节日」作为最强特征（year-over-year lift）。

> 关键点：**节日脉冲必须显式建模，不能让模型从稀疏序列自学习**——这既是精度需要，也是可解释/可外推（新节日如「520」「跨年」）需要。

---

## 分阶段建议

| 阶段 | 目标 | 方法组合 | 产出/里程碑 | 周期 |
|---|---|---|---|---|
| **P1 基线** | 跑通 + 定基准 | Prophet(假日表) + ETS + 周/月/节日因子 | 日级销量基线，MAPE/sMAPE 基准 | 1-2 周 |
| **P2 ML 主模型** | 精度主力 | **LightGBM/XGBoost**：日历(节日窗口/星期/月) + 促销 + 价格 + 滞后 + 滚动统计特征，分位数版输出 | 日级 P50/P90，比基线提升 ≥10-15% | 2-4 周 |
| **P3 跨 SKU 放大** | 数据放大 + 概率 | **DeepAR / PatchTST** 跨 SKU/跨店全局模型；引入售罄标注做截断修正（对齐 2608.14096 OWMS） | 全 SKU 统一概率预测 + 分货建议 | 4-8 周 |
| **P4 LLM 辅助（可选/低优先）** | 少样本/语义增强 | Time-LLM 或 RAEF(2608.14054) 检索增强；LLM 做**节日脉冲强度判断 + 异常日解释** | 节日脉冲辅助信号 + 可解释输出 | 8-12 周，门控 |

**阶段门控原则**：P2 的 LightGBM 未稳定跑赢 P1 基线前，不投入 P3/P4；P4 仅在「跨年数据 + 节日历法 + 售罄标注」补齐后评估，且 LLM 定位为**辅助/解释**而非主预测器（成本与校准风险）。

**评估指标**：sMAPE / MASE（跨店可比）+ 节日日专项 MAPE + 分位数校准（PIT/pinball loss）。警惕纯 MSE 压平振幅（2608.14106），对节日日单独评估振幅与排名。

---

## 证据来源

- TUM PlantGrid 园艺销售预测：https://portal.fis.tum.de/en/publications/machine-learning-outperforms-classical-forecasting-on-horticultur/ · 代码 https://github.com/grimmlab/HorticulturalSalesPredictions
- FreshRetailNet-50K（生鲜截断需求）：https://arxiv.org/abs/2505.16319
- 时序基座模型综述：https://arxiv.org/abs/2405.02358 · Foundation Models for Time Series Analysis（Liang et al.）
- 本地全文：/Users/coreyleung/dsh-collab/research/paper-cache/texts/2608.14106.txt · 2608.14054.txt · 2608.14096.txt · 2608.14198.txt · 2608.14270.txt
- 生鲜/短保需求预测：https://norma.ncirl.ie/9419/ · https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002981076
- 促销/事件效应建模：https://his.diva-portal.org/smash/record.jsf?pid=diva2%3A1709851 · https://www.sciencedirect.com/science/article/abs/pii/S0957417410012261
- M5 竞赛特殊日/日历特征：https://www.unic.ac.cy/el/iff/research/forecasting/m-competitions/m5/
- LLM 时序预测评估/TimeGPT：https://ar5iv.labs.arxiv.org/html/2310.03589 · GIFT-Eval https://ar5iv.labs.arxiv.org/html/2603.22586
- 花商库存系统 Floro-X：https://dlib.iit.ac.lk/xmlui/handle/123456789/3329

> 数据现状核验：order_sales_full_20260831.csv（20610 行，日期 2025-08-01 ~ 2026-08-29，259 天；30 列含商品级明细/补贴/退款，缺天气/流量/售罄标注/多年历史）。
