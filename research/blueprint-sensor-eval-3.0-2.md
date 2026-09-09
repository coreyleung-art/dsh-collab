# 蓝图 3.0-2 传感器方案评估——手套/摄像头/环境传感（花艺工艺数据化）

> 调研：数据调查员子代理 · 2026-08-24 · 方法：web_search ×12（中英） + 本地论文库/研究库交叉验证
> 用户环境：花店生意（鲜花零售+花艺制作），工艺数据化是物理主线 3.0（端侧 IoT 传感）起点；本报告为「重资产先评估」前置产出

---

## 结论（推荐路线）

**推荐分阶段路线：环境传感先铺（成本最低、立刻有损耗收益）→ 摄像头视觉试点（低成本快速拿过程数据）→ 数据手套验证后再投入（高成本高精度，重资产）**

核心判断依据：

1. **工艺数据化能力排序**：数据手套（力+姿态，高精度）＞ 摄像头视觉（姿态/过程/物体，中精度）＞ 环境传感（温湿度光照，与"手法"无关）。
2. **ROI/落地速度排序**：环境传感 ≈ 摄像头 ＞＞ 数据手套。摄像头用现有工位相机 + 本地 i9 算力（本机已具备本地模型/MLX 推理栈），软件成本近零，2-4 周即可出可回放的"过程数据"；商用数据手套单双 4-8 万元且需 SDK 开发与佩戴管理，是典型重资产。
3. **花艺生意的瓶颈变量**：行业鲜花损耗率 30%+，冷柜/工作间温湿度直接影响瓶插期与损耗——环境传感采集的每一条温度记录都可换算成损耗金额，是**最短回本路径**（数月内）；摄像头的工时/步骤数据支撑标准化与培训；手套的力数据目前主要是"示范数据"价值，服务于 4.0 机器人示教，属远期资产。
4. **决策门禁（衔接 ops-science/flower-shop-evolution-research.md）**：本方案是物理 3.0 传感试点，先跑通"数据可回放"，再评估是否进 4.0 半自动；ROI 不达标可逆（摄像头/环境设备均可复用为监控与质检）。

---

## 三方案对比表

| 维度 | ① 环境传感（温湿度/光照） | ② 摄像头视觉（姿态/动作/过程） | ③ 触觉/力传感数据手套 |
|---|---|---|---|
| **采集能力** | 温度、湿度、光照、门开关/冷柜状态、CO₂（可选） | 手部关键点（21 点 MediaPipe）、动作/步骤时序、工具与花材使用、工位视频 | 指尖/掌压力、手部姿态（关节角）、动作序列、触觉反馈（震动） |
| **精度** | 高（±0.3°C / ±3%RH 级别，足够保鲜管理） | 中（手部姿态约 1-5cm 级、动作识别 85-95% 需场景标注；遮挡/花材遮挡手部会掉点） | 高（力分辨率克级到百克级，关节角高精度） |
| **成本（硬件）** | 低：WiFi 温湿度记录仪 ¥50-300/点；HACCP 蓝牙记录仪 ¥200-500/个 | 低-中：工位相机/手机 ¥200-1000/路 + 现有 PC 算力；算力不足加边缘盒子 ¥1-3k | 高：商用 SenseGlove Nova2 ≈ $6,000/双（¥4-5万）；Manus Metagloves Pro ≈ $10,658/双（¥7-8万）；开源 DIY（DOGlove 等）材料 ¥2-8k 但需硬件/固件工程 |
| **部署难度** | 极低：贴装+WiFi 配对，半天完成 | 中：机位选型（俯拍 45-60°）、标定、动作标注（人工标注是主要成本） | 高：佩戴校准、SDK 接入、数据同步、花艺操作中佩戴舒适性/卫生问题 |
| **维护** | 极低：换电池/充电 | 低-中：遮挡与机位漂移需偶尔调整；标注集需随新品迭代 | 高：传感器漂移、线缆/电池、消毒清洁、损耗件 |
| **花艺适配** | ✅ 直接适配（保鲜库/工作间/展台） | ✅ 强适配（工位固定机位即可，非接触不干扰操作） | ⚠️ 适配性存疑：花艺手法多为精细指尖操作，商用 VR 手套为虚拟交互设计，佩戴材质/尺寸/卫生需验证 |
| **产出数据价值** | 损耗控制（直接算钱）、保鲜合规记录、采购/陈列决策 | 工时、步骤序列、工艺标准化基准、培训素材、质检（花壳/花泥插花节拍） | 手感/力轨迹示范数据（4.0 机器人示教）、手部动作的"隐性知识"显性化 |
| **成熟度** | 成熟（冷链/生鲜行业广泛商用） | 成熟（工业装配动作识别有论文与产品实践；MediaPipe/YOLO-Pose 开源） | 研究中（学术+VR/机器人行业，花艺场景无成熟先例） |

---

## 花艺场景可采数据清单

### A. 立即可采（环境层，成本 <¥3k）
| 数据 | 位置 | 用途 |
|---|---|---|
| 冷柜温度/开门时长 | 保鲜冷柜（鲜花/成品） | 损耗归因、制冷故障预警、合规记录 |
| 工作间温湿度 | 花艺制作台区域 | 花材失水速率、夏季高峰空调策略 |
| 光照/紫外线 | 陈列区、窗口 | 陈列翻新节奏（光照加速花色衰退） |
| 陈列柜温度 | 成品展示柜 | 成品瓶插期承诺 |
| 耗材库存环境（备用） | 花泥/包装耗材仓 | 耗材劣化控制 |

### B. 过程层（摄像头视觉，成本 ¥3-10k/2 工位）
| 数据 | 方式 | 用途 |
|---|---|---|
| 制作步骤序列（去叶→剪根→插泥→包扎→包装） | 动作分类模型 + 视频标注 | 标准作业节拍（SOP 工时）、报价/排班依据 |
| 单束/单篮工时 | 事件检测（开始/结束） | 人效、定价、产能预测（参考：上海花店报道 6 手 10 分钟一束花） |
| 手部姿态轨迹 | MediaPipe 21 关键点 | 手法分析、新人培训对照、动作质量评分 |
| 花材/工具使用频率 | 目标检测（花泥/剪/胶带/花材类） | 耗材联动、BOM 校验 |
| 成品质检 | 俯拍 + 规则/视觉检查 | 花泥遮盖、对称度、包装完整度（试点） |

### C. 手感层（数据手套，成本 ¥4-8 万起，先验证后买）
| 数据 | 方式 | 用途 |
|---|---|---|
| 指尖/掌压力曲线 | 力传感器阵列 | 「剪枝力度」「插泥深度/力度」显性化——目前无传感器方案无法采 |
| 手腕/手指关节角 | IMU/弯曲传感器 | 手法轨迹（与摄像头互补，不受遮挡） |
| 动作节奏（时间戳序列） | 事件流 | 手法节奏标准化 |
| 触觉反馈（可选） | 震动马达 | 培训时"引导手型"（MIT smart glove 模式） |

### D. 数据价值分级（值不值得采）
| 优先级 | 数据 | 理由 |
|---|---|---|
| P0 | 冷柜/工作间温湿度 | 直接对损耗（钱），最便宜，回本最快 |
| P1 | 工位视频+步骤/工时 | 支撑 2.0 标准化收尾与培训，摄像头方案便宜可逆 |
| P2 | 手部姿态轨迹 | 与 P1 同源数据，几乎零边际成本，为手法分析蓄水 |
| P3 | 手套力轨迹 | 价值高（隐性手感知识）但当前无明确消费方，等 4.0 机器人/培训产品化后再投 |
| 不急着采 | 环境 CO₂/气压、脑电/心率、3D 重建全场 | 与花店业务指标无直接关联，边际收益低 |

---

## 论文依据（含本地 KB 命中）

### 本地 KB / 研究库命中（已有资产，直接衔接）
- **ops-science/flower-shop-evolution-research.md**（2026-08-19 已建档，蓝图 3.0 传感段）：
  - 物理 3.0 章节引用 *Learning force-conditioned visuomotor diffusion policy from human demonstrations for complex robotic assembly*（SciDirect 2025）——人类示范（含力）→ 机器人学习，即"传感器手套+摄像头采集花艺示范"的理论核心。
  - 同章节引用 *MANUS Metagloves Pro / Cutaneous Feedback Haptic Glove*——触觉手套用于 VR 工业培训与示范采集先例。
  - 4.0 章节引用 *Application of fuzzy control to flower arrangement robot*（BIT）与模糊推理插花机器人（J-Stage）——花艺机器人已有直接研究先例，反向说明工艺数据化的终局消费方存在。
- **paper-cache 本地论文库**（139 篇，偏供应链/LLM/Agent，无触觉手套/动作识别直接论文；环境保鲜有 3 篇可支撑 P0）：
  - `2511.05920` *IoT-based Fresh Produce Supply Chain Under Uncertainty*：IoT 温控反馈可延长生鲜货架期 18%+（对比传统优化）——环境传感→损耗收益的量化证据。
  - `2504.15741` *Stochastic Programming for Dynamic Temperature Control of Refrigerated Road Transport*：托盘级温度信息是冷链质量最关键信息——支持"点位级温湿度采集"价值。
  - `2304.09601` *BioTrak: Food Chain Logistics Traceability*：冷链参数监控+全链可视化是质量合规通用范式——可套用为花材保鲜记录。
- 本地另有 `ai-papers-database.md` 与 `research-paper-library-index.md`（ops-science）为库内索引，经 grep 未发现传感器/动作识别主题论文——**此为本地库缺口，本次用 web 检索补充**。

### Web 检索补充（2026-08 检索，已去重）
**手套/触觉传感**
1. *AI-based smart glove for hand movement recognition and rehabilitation monitoring: a systematic review*（J. Eng. Appl. Sci., 2026）——智能手套传感器类型（flex、电容、磁力、IMU）与手部动作识别系统综述。https://link.springer.com/article/10.1186/s44147-026-01084-6
2. *Adaptive tactile interaction transfer via digitally embroidered smart gloves*（Nature Communications, 2024）——刺绣式柔性触觉手套，可穿戴触觉传感工程化进展。https://link.springer.com/article/10.1038/s41467-024-45059-8
3. *Towards Hand-based Skill Imitation Learning: A Custom Data Glove with Hierarchical Tactile and Kinesthetic Sensing*（IEEE, 2025）——**工艺技能模仿学习专用数据手套**，触觉+动觉分层感知，与本任务最直接相关。https://ieeexplore.ieee.org/document/11661583
4. *DOGlove: Dexterous Manipulation with a Low-Cost Open-Source Haptic Force Feedback Glove*（arXiv:2502.07730）——低成本开源力反馈手套（材料级成本路径）。https://arxiv.org/abs/2502.07730
5. *MIT smart glove teaches new physical skills*（MIT Schwarzman College of Computing, 2024）——智能手套用于技能引导（振动引导手型），培训场景先例。https://computing.mit.edu/news/smart-glove-teaches-new-physical-skills/
6. *Le Cerfav: Preserving Traditional Glassmaking Skills with MANUS Gloves and XR Motion Capture*（MANUS 官方案例）——**传统工艺（玻璃吹制）技能数字化直接先例**：数据手套+动捕保存匠人手艺。https://www.manus-meta.com/use-cases/preserving-traditional-glassmaking-skills-with-manus-gloves-and-xr-motion-capture
7. 硬件价格：SenseGlove Nova 2 官方/媒体报道 ≈ **$6,000/双**（UploadVR: "SenseGlove Nova 2 Adds Palm Pressure To $6000 VR Gloves"）；Manus Metagloves Pro 渠道报价 **$10,658**（SVRC 商店）。

**摄像头视觉/动作识别**
8. *Self-supervised representation learning for robust fine-grained human hand action recognition in industrial assembly lines*（Machine Vision and Applications, 2024）——工业装配线细粒度手部动作识别，自监督表征降低标注成本——**摄像头工艺动作识别的直接技术依据**。https://link.springer.com/article/10.1007/s00138-024-01638-9
9. *Real-Time Assembly Task Validation Using Deep Learning-Based Object Detection and Operator's Hand-Joints Trajectory Classification*（Uludag Univ.）——目标检测+手关节轨迹分类的实时装配校验，摄像头过程监控可用模式。https://avesis.uludag.edu.tr/yayin/988c0041-a617-412f-9c30-f0985f0cd070/real-time-assembly-task-validation-using-deep-learning-based-object-detection-and-operators-hand-joints-trajectory-classification
10. *基于 MSS-YOLO-MPHands 融合架构的装配手部动作识别研究*（空间电子技术）——YOLO+MediaPipe 融合的装配手部动作识别（中文佐证）。https://mc.spacejournal.cn/cn/article/id/e45e6290-250b-4016-a9ab-0ef153b0fb8a
11. *A New Model for Assembly Task Recognition: A Case Study of Seru Production System*（IEEE Access 2024）——10 种 DL 装配任务识别模型效率对比，含手部姿态方案。https://ieeexplore.ieee.org/document/10731917

**花材保鲜/环境传感**
12. *Wet and dry cooling affect the postharvest life of cut flowers (Lisianthus)*（SciELO）——降温方式影响鲜切花瓶插期，温控与瓶插期关系的实证。https://www.scielo.org.mx/scielo.php?script=sci_abstract&pid=S2007-09342014000700009
13. *Florists & Growers Monitoring System*（Swift Sensors 行业方案）——花店/种植端温湿度无线监控商用方案。https://www.swiftsensors.com/industry/florists/
14. *Flowers Intelligent Bluetooth HACCP temperature and humidity data logger*（Freshliance 案例）——鲜切花冷链蓝牙温湿度记录仪（成本量级 ¥200-500）。https://www.freshliance.com/news/how-to-preserve-cut-flowers-flowers-intelligent-bluetooth-haccp-temperature-and-humidity-data-logger.html
15. *Floriculture cold storage monitoring with temperature, humidity and door status sensors*（Macnman 案例）——冷库温湿度+门状态传感部署先例。https://www.macnman.com/success-stories/success-stories-version/floriculture-cold-storage-monitoring-with-temperature-humidity-and-door-status-sensors

**花店运营/工时佐证**
16. *Time Tracking for Florists: The Hidden Hours*（ClientCasa）——花艺师隐性工时/按束计时的行业痛点。https://www.clientcasa.com/posts/time-tracking-for-florists-the-hours-behind-every-arrangement
17. 解放日报《6 双手，10 分钟，一束花》——上海花店节日赶制节拍（10 分钟/束量级）。https://m.jfdaily.com/wx/detail.do?id=857771
18. 天目新闻《插花 4 次 7500 元》——花艺师手艺定价（人工价值佐证，支持工艺数据资产价值）。https://tidenews.com.cn/news.html?id=650570

### 噪音排除记录（检索过程）
- 淘汰：CSDN 文库/未署名转载（如 OpenCV 手势跟踪通用文）、泛泛 SEO 站（hackster 等仅 demo 无引用价值）、无日期无出处的转贴——均未采信。
- 注意：SenseGlove/Manus 具体到手价因渠道与版本浮动，标注为"渠道报价/媒体报道价"，落地时以正式询价为准。

---

## 成本收益评估（重资产评估）

### 投入（一次性 + 年维护）
| 方案 | 硬件投入 | 部署/集成 | 年维护 | 合计（首年） |
|---|---|---|---|---|
| A 环境传感（5-8 点：冷柜×2、工作间、陈列、门状态） | ¥1,000-2,500 | ¥500（半天，自有） | ¥300-800（电池/换件） | **约 ¥2k-4k** |
| B 摄像头视觉（2 工位：相机+支架+现有 i9 算力+标注） | ¥600-2,000（相机） | ¥3k-6k（标注 100-300 条视频 + 模型调优，可复用本地 MLX/开源栈） | ¥1k-2k | **约 ¥5k-10k** |
| C 数据手套（1-2 双，含 SDK/校准/定制） | ¥4万-8万（商用）；¥3k-8k（DOGlove DIY，含工程） | ¥1万-2万（SDK 集成、数据管线） | ¥5k-1万（维护/耗材/校准） | **约 ¥5万-11万（商用）** |

### 收益（保守假设，花店月流水 ¥10-30 万口径）
| 收益项 | 机制 | 保守量化 | 对应方案 |
|---|---|---|---|
| 损耗降低 | 冷柜温度/开门异常早发现；工作间温湿度合规 | 损耗率 30%+ 中降 2-5 个百分点 → 花材成本（流水 40-50%）月省 **¥1k-8k** | A |
| 工时/报价准确 | 标准节拍数据 → 定价、排班、产能 | 每单报价误差减少 + 人效提升 5-10% → 月 **¥1k-5k** | B |
| 培训/一致性 | SOP 视频+手法对照，新人上手快、品质一致 | 培训周期缩短 + 差评/返工减少 → 年 **¥5k-2万** | B（后期 C） |
| 数据资产 | 工艺/环境/工时数据入库 = 4.0 垂直引擎燃料 | 无法直接现金化，但为机器示教与垂直模型护城河前提 | B+C（远期） |
| 保鲜合规背书 | 温湿度可追溯记录 → 平台/客户信任、大单 | 间接 | A |

**结论**：A 方案首年投入 ¥2-4k，若月省损耗 ≥¥500 即一年内回本（几乎确定）；B 方案首年 ¥5-10k，需要标注投入但设备可复用、可逆；C 方案首年 ¥5-11 万，按当前业务规模**不构成独立回本模型**，应作为"工艺数据资产/示范数据"项目立项，与 4.0 机器人路线绑定后评估——这正是"重资产先评估"的核心结论：**现阶段不值得直接买手套**。

---

## 分阶段建议

| 阶段 | 时间 | 动作 | 投入 | 门禁/产出 |
|---|---|---|---|---|
| **0 环境传感试点** | 第 1-2 周 | 冷柜×2+工作间+陈列 4-6 点温湿度/门状态，接本地面板/表格；建立"温度事件→损耗归因"日志 | ¥2-4k | 连续 30 天数据 + 1 起可归因异常（无异常则记基线）；损耗率基线 |
| **1 摄像头视觉试点** | 第 1-3 月 | 2 工位俯拍 + MediaPipe 手部关键点 + 步骤分类（先人工标注 50-100 条节日订单）；输出标准 SKU 的步骤/工时基线 | ¥5-10k | 3-5 个标准品 SKU 可回放"步骤+工时+手型轨迹"；节拍数据进 ERP 报价/排班 |
| **2 手套可行性验证** | 第 3-6 月 | 租借或 DOGlove 开源原型 1 双，1 名资深花艺师做 5-10 个标准品示范采集（视触对齐）；评估佩戴卫生/舒适与数据质量 | ¥3k-8k（租/DIY） | 示范数据可回放 + 力轨迹与摄像头轨迹对齐；输出"是否值得商用采购"决策 |
| **3 视触融合/4.0 门禁** | 第 6 月+ | 若阶段 2 达标：商用手套+摄像头融合入库，训练示教策略；与 flower-shop-evolution 4.0 门禁（传感数据质量达标）衔接 | 按 4.0 立项 | 数据飞轮启动；否则停在阶段 1 的工艺标准库（已独立有价值） |

**兜底/可逆性**：阶段 0-1 设备全部可复用为日常监控与质检；阶段 2 用租借/开源先验证再买，避免重资产沉没。

---

## 证据来源

### Web（2026-08-24 检索，12 组关键词，交叉验证）
- Springer JEA 2026 智能手套综述：https://link.springer.com/article/10.1186/s44147-026-01084-6
- Nature Comm. 2024 刺绣触觉手套：https://link.springer.com/article/10.1038/s41467-024-45059-8
- IEEE 2025 技能模仿学习数据手套：https://ieeexplore.ieee.org/document/11661583
- DOGlove 开源力反馈手套：https://arxiv.org/abs/2502.07730
- MIT 智能手套教学：https://computing.mit.edu/news/smart-glove-teaches-new-physical-skills/
- Le Cerfav 玻璃工艺数字化（MANUS 案例）：https://www.manus-meta.com/use-cases/preserving-traditional-glassmaking-skills-with-manus-gloves-and-xr-motion-capture
- SenseGlove Nova 2 $6000（UploadVR）：https://www.uploadvr.com/senseglove-nova-2-gloves-palm-feedback/
- Manus Metagloves Pro $10,658（SVRC）：https://www.roboticscenter.ai/store/product/manus-manus-metagloves-pro
- 工业装配手部动作识别（MVA 2024）：https://link.springer.com/article/10.1007/s00138-024-01638-9
- 装配任务实时校验（Uludag）：https://avesis.uludag.edu.tr/yayin/988c0041-a617-412f-9c30-f0985f0cd070/real-time-assembly-task-validation-using-deep-learning-based-object-detection-and-operators-hand-joints-trajectory-classification
- YOLO+MPHands 装配动作识别（空间电子技术）：https://mc.spacejournal.cn/cn/article/id/e45e6290-250b-4016-a9ab-0ef153b0fb8a
- Seru 装配任务识别（IEEE Access）：https://ieeexplore.ieee.org/document/10731917
- 鲜切花降温与瓶插期（SciELO）：https://www.scielo.org.mx/scielo.php?script=sci_abstract&pid=S2007-09342014000700009
- Swift Sensors 花店监控：https://www.swiftsensors.com/industry/florists/
- Freshliance 鲜切花冷链记录仪：https://www.freshliance.com/news/how-to-preserve-cut-flowers-flowers-intelligent-bluetooth-haccp-temperature-and-humidity-data-logger.html
- Macnman 花店冷库温湿度+门状态：https://www.macnman.com/success-stories/success-stories-version/floriculture-cold-storage-monitoring-with-temperature-humidity-and-door-status-sensors
- 花艺师隐性工时（ClientCasa）：https://www.clientcasa.com/posts/time-tracking-for-florists-the-hours-behind-every-arrangement
- 解放日报 6 手 10 分钟一束花：https://m.jfdaily.com/wx/detail.do?id=857771
- 天目新闻 插花 4 次 7500 元：https://tidenews.com.cn/news.html?id=650570

### 本地库（命中并已核对）
- `ops-science/flower-shop-evolution-research.md`（蓝图总纲，3.0 传感段与 4.0 机器人引用）
- `paper-cache/2511.05920.md`（IoT 生鲜供应链，温控延长货架期 18%+）
- `paper-cache/2504.15741.md`（冷链动态温控，托盘级温度信息最关键）
- `paper-cache/2304.09601.md`（BioTrak 冷链可追溯平台）
- 库内索引核对：`ops-science/research-paper-library-index.md`（139 篇，无触觉手套/动作识别主题 → 已用 web 检索补齐）

### 局限与说明
- 商业硬件价格为渠道/媒体报价，落地前需正式询价（SenseGlove/Manus 渠道价差异大）。
- 本报告未执行 research-pipeline 的全文抓取落盘步骤（子代理作用域限制），来源以上述 URL+摘要为准；如需沉淀 raw 可后续补抓。
