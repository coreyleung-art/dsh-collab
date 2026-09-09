# 3D / 数字孪生 AI 市场动态调研（本地落盘 · 2026-09-09）

> 数据调查员 4787d717 · 调研：3D 打印 / 3D 设计智能体的市场玩家、融资、产品形态
> 日期：2026-09-09 · 用途：评估「3D 打印 / 3D 设计智能体」赛道现状与前提条件（用户拟做物理工作台 3D 模拟）
> 数据纪律：金额/轮次/估值来自各源逐字引用，标注来源。

---

## 一、生成式 3D 模型 / 文本转 CAD 智能体（软件侧）

### 1. 腾讯混元3D（国内生成式 3D 代表，Hunyuan3D 3.0）
- **来源**：央广网 / 雷峰网 2025-11-26（[央广](http://tech.cnr.cn/techph/20251126/t20251126_527442464.shtml) / [雷峰](https://m.leiphone.com/category/industrynews/FHKyBolTMwf90rLB.html)）
- 全球最受欢迎 3D 开源模型，社区下载量超 **300 万**；两条路线：Hunyuan3D（物体生成）+ HunyuanWorld（大场景世界模型）
- Hunyuan3D 3.0：首创 3D-DiT 分级雕刻模型，建模精度较前代提升 3 倍，支持 **1536³ 几何分辨率 + 36 亿体素**
- 模式：文生 3D / 图生 3D（2-4 视角）/ 草图生 3D / 3D 智能拓扑；输出 OBJ/GLB，可集成 Unity/UE/Blender
- 150+ 企业经腾讯云接入，含 Unity 中国、**拓竹科技（消费级 3D 打印龙头）**、Liblib
- 落地：游戏/电商（商品点击率+35%）/**3D 打印（图→实体）**/工业设计/教育文旅/珠宝

### 2. Synera（增材制造 AI 代理编排平台，德国）
- **来源**：3D打印派 2026-06-16（[链接](http://wap.dayinpai.com/community/detail/17097)）
- 2026-04 完成 **4000 万美元 B 轮**（Revaia 领投，凯捷 ISAI Cap Venture、宝马 iVentures 跟投）
- 低代码可视化编辑器：模块化节点把 **80+ 种 CAD/CAE/CAM/PLM 工具**串成自动化管线；不替代软件、**编排**它们
- 2025 叠上 **AI 代理**：工作流确定性，代理当"数字工程劳动力"——解释需求、选工作流、无监督持续运转
- **NASA 已用**多个 Synera 代理：需求→已验证零件设计，一小时数百次设计迭代
- 客户：宝马/空客/大众/现代/沃尔沃/赛峰等 60+ 企业（15 国），2025 ARR 翻倍
- 案例：宝马散热器罩 DfAM 数月→数天；现代仿生 B 柱
- **本地部署 + TISAX Level 2**：工程数据/IP 不离开客户基础设施（工业级前提）
- 关键判断：代理必须扎进实际工具链（CAD/仿真/PLM）才有产出；Gartner：86% 制造企计划增生成式 AI 投资，但仅 41% AI 原型能进生产

### 3. Adam（文本转 CAD 消费者→企业，YC W25）
- **来源**：搜狐/环球市场播报 2026-05（[链接](https://www.sohu.com/a/949724489_122014422)）
- **410 万美元种子轮**（TQ Ventures 领投，468 Capital/Pioneer/Transpose 跟投；天使含 YC Trevor Blackwell）
- 文本转 3D App 社媒曝光超 1000 万次；订阅 5.99/17.99 美元月
- 转型："CAD 领域 v0"（Vercel Guillermo Rauch 语）；首款 **Onshape CAD copilot**——融合选中物体对话交互，非纯文本
- 初期聚焦机械工程，帮工程师做重复修改（多个 CAD 文件相同操作），**不取代工程师**
- 竞争：MecAgent 等文本转 CAD 已有竞品

### 4. Meshy（AI 3D 模型生成头部）
- **来源**：3Dnatives 2026-07（[链接](https://www.3dnatives.com/en/meshy-400-million-in-series-b-21072026/)）
- **Series B 近 $400 万（约 400M/4 亿美元）？** 标题"nearly $400 Million" = 约 4 亿美元；估值 **$1.5B（15 亿美元）**
- 已推 3D 打印对应 AI agent + 自动分割功能（ShareLab 日文源佐证：约 637 亿日元 ≈ $4 亿）

### 5. Autodesk "neural CAD"（2025 AU 大会）
- **来源**：[Engineering.com](https://www.engineering.com/autodesk-introduces-neural-cad-at-au-2025/)（403 待补全文）——CAD 龙头入局 AI 原生 CAD

---

## 二、学术/技术前沿（3D 智能体，arXiv 摘要收录）

（正文抓取受网络限制，见 papers 台账 + 下表为已识别关键论文）

| 论文/系统 | 主题 | 来源 |
|---|---|---|
| LLM-3D print | LLM 监控/控制 3D 打印 | [ScienceDirect 2025](https://www.sciencedirect.com/science/article/pii/S2214860425003926) |
| CAD-Assistant | 工具增强 VLLM 通用 CAD 任务求解 | [ICCV 2025 / arXiv 2412.13810](https://arxiv.org/abs/2412.13810) |
| CADDesigner | 概念 CAD 生成通用 Agent | [arXiv 2508.01031](https://arxiv.org/abs/2508.01031) |
| ShapeCraft | LLM Agent 结构化/纹理/交互 3D 建模 | [NeurIPS 2025](https://researchportal.hkust.edu.hk/en/publications/shapecraft-llm-agents-for-structured-textured-and-interactive-3d-) |
| AutoMEX | LLM+知识图谱材料挤出自动化 | ScienceDirect 2025 |
| 3DprintMIND | LLM+制造知识图谱 智能制造 AI-Agent | ScienceDirect 2025 |
| Agentic Additive Manufacturing Alloy Discovery | 智能体增材合金发现 | scilit |
| Physics-in-the-Loop | 物理在环混合 Agent 架构 CAD 验证 | [arXiv 2605.19717](https://arxiv.org/pdf/2605.19717.pdf) |

---

## 三、市场信号小结（对"3D 智能体"赛道）

1. **资本密集入场**：Synera B 轮 $4000 万、Meshy 约 $4 亿/估值 $15 亿、Adam $410 万种子、腾讯自研混元3D 开源 300 万下载。
2. **两条技术路线清晰**：①生成式（文/图/草图→3D 资产，混元/Adam/Meshy）②智能体编排（AI agent 驱动 CAD→仿真→打印全流程，Synera 最典型，NASA/工业在用）。
3. **工业前提 = 本地部署 + 工具链深度集成 + 数据不出域**（Synera TISAX 案例），消费者产品（Adam/Meshy）先爆量再进 B 端。
4. **3D 打印龙头（拓竹）接混元3D** → 生成式 3D 已进入消费级打印闭环，"图→实体"通路打通。
