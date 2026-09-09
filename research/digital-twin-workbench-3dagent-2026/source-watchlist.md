# 3D 打印 / 3D 设计智能体 + 数字孪生 · 信源关注库（Watchlist）

> 数据调查员 4787d717 · 2026-09-09 · 用途：为"物理工作台 3D 模拟 + 3D 智能体"方向建持续跟踪的信源清单
> 评级沿用 source-channels：S=一手权威 / A=高质量二手 / B=需交叉验证
> 可达性：🟢=本环境实测可达 · 🟡=受限 · 🔴=不可达 · （未标=待实测）
> 关联：source-channels-2026.md（学术通道矩阵，通用）+ 本库（本方向聚焦源）

---

## 结论速览
本方向信息源分**五类**：学术（期刊/会议/arXiv）· 行业媒体（国际/中文）· 厂商动态 · 开源/硬件社区 · 市场/数据。最值得常驻关注的是：**行业媒体 3DPrint.com/3Dnatives/南极熊**（技术+市场）、**厂商动态 拓竹/腾讯混元3D/Synera/Autodesk**（3D 智能体落地）、**学术 Additive Manufacturing 期刊 + SIGGRAPH/CVPR 3D 方向**（前沿）。

---

## 连通性实测（2026-09-09 · VPN）

| 结果 | 源 |
|---|---|
| 🟢 可达 200 | **学术**：arxiv.org / alphaxiv / export.arxiv / api.openalex / semanticscholar（VPN 后全通）<br>**媒体**：3dprint / 3dnatives / 3dprintingindustry / engineering.com / sharelab / leiphone / smzdm / 南极熊(慢~20s但200)<br>**厂商**：混元3D(3d.hunyuanglobal) / synera / meshy / revopoint / freecad<br>**开源/市场**：github / omniverse / prusa / qyresearch |
| 🟡 反爬/需浏览器 403 | sciencedirect（订阅墙）· bambulab · autodesk · all3dp |
| 🔴 不可达 000 | **dayinpai（www 域名）** → 建议改走其 wap（wap.dayinpai.com，早前实证可达） |
| ⚪ 429 反爬 | google scholar（已知反爬，不主用） |

**结论**：VPN 后本方向信源绝大多数可达（学术检索通道全通，弥补早前「arXiv 不可达」短板）；仅 Elsevier 订阅墙（sciencedirect）正文受限；打印派需用 wap 域名。详见 `probe_sources.sh`（可重跑）。

---

## 一、学术信源（前沿 + 论文）

| 源 | 类型 | 入口 | 关注什么 | 级别 |
|---|---|---|---|---|
| Additive Manufacturing (Elsevier) | 期刊 | ScienceDirect | 3D 打印技术+LLM/agent 制造（LLM-3D print 即此刊） | S |
| Journal of Manufacturing Systems / R&CIM | 期刊 | ScienceDirect | 制造智能体（AutoMEX/3DprintMIND 在此系） | S |
| arXiv cs.CV/cs.GR/cs.RO | 预印本 | arxiv.org（本环境经 alphaXiv/代理） | 3D 生成(CADDesigner/ShapeCraft)、机器人制造 | S |
| SIGGRAPH / CVPR / ICCV / NeurIPS | 会议 | 各官网 | 3D 生成前沿(CAD-Assistant ICCV25 等) | S |
| CIRP / ASME 制造年会 | 会议 | — | 数字孪生/智能制造工业 | A |
| 3D/数字孪生综述（如 ScienceDirect 各大综述） | 综述 | ScienceDirect | 领域地图/期刊分布 | A |

## 二、行业媒体（技术 + 市场动态）— 常驻关注

### 国际
| 源 | 类型 | 入口 | 关注 | 级别 | 可达 |
|---|---|---|---|---|---|
| 3DPrint.com | 3D 打印综合+年度预测 | 3dprint.com | 市场/AM 软件化趋势 | A | 🟡(部分403) |
| 3Dnatives | 3D 打印+AI | 3dnatives.com | AI 3D 融资(Meshy 等) | A | 🟢 |
| 3D Printing Industry | 3D 打印行业 | 3dprintingindustry.com | Authentise 等 AI 制造软件 | A | 待测 |
| Engineering.com | CAD/工程 AI | engineering.com | Autodesk neural CAD | A | 🟡(403) |
| ShareLab News | 日文 3D 打印+AI | news.sharelab.jp | Meshy 等日文报道 | A | 🟢 |

### 中文
| 源 | 类型 | 入口 | 关注 | 级别 | 可达 |
|---|---|---|---|---|---|
| 南极熊3D打印网 | 中文 3D 打印最大 | nanjixiong.com | "AI 一键 3D 打印"等中文动态 | A | 待测 |
| 打印派 (dayinpai) | 中文 AM 社区 | dayinpai.com | Synera 等 AI 代理制造报道 | A | 🟢 |
| 雷峰网 / 央广 | 科技大媒体 | leiphone/cnr | 腾讯混元3D 等国产 3D AI | A | 🟢 |
| 什么值得买 | 消费硬件选购 | smzdm | 3D 扫描/打印机真实用户评价 | B | 🟢 |

## 三、厂商 / 产品动态（3D 智能体与硬件落地）

| 主体 | 关注点 | 追踪入口 | 级别 |
|---|---|---|---|
| **拓竹 Bambu Lab** | 消费级 FDM 龙头 + 接混元3D | 官网/新闻 | S |
| **腾讯混元3D** | 生成式 3D(3.0 精度×3)开源 | 3d.hunyuanglobal.com | S |
| **Synera** | AI 代理编排 80+ CAD/仿真 工具 | 官网/融资新闻 | S |
| **Autodesk** | neural CAD (AU2025) | engineering.com | A |
| **Meshy / Adam** | AI 3D / 文本转 CAD copilot | 官网/融资 | A |
| Revopoint / Creality | 3D 扫描仪（重建硬件） | 官网+评测 | A |
| FreeCAD / OpenSCAD / Onshape | 参数化 CAD(agent 工具接口) | 官网/GitHub | A |

## 四、开源 / 硬件社区（动手 + 复现）

| 源 | 类型 | 入口 | 关注 | 可达 |
|---|---|---|---|---|
| GitHub (ShapeCraft 系 / PiLiDAR / Twinmodel) | 开源代码 | github.com | 3D 智能体/数字孪生复现 | 🟢 |
| 树莓派 / ESP32 生态 | 硬件 | 官网 | 感知层硬件 | 🟢 |
| NVIDIA Omniverse | 数字孪生平台 | developer.nvidia.com/omniverse | 工业数字孪生 | 🟡 |
| Prusa Blog / All3DP | maker 内容 | prusablog/all3dp | 打印实践 | 待测 |

## 五、市场 / 数据

| 源 | 关注 | 级别 |
|---|---|---|
| QYResearch 便携 3D 扫描市场报告 | 扫描硬件市场规模(Revopoint 头部) | B |
| 3DPrint.com 年度 3D 打印预测 | AM 年度方向(2026 软件化) | A |
| 各大融资新闻（3Dnatives/打印派） | AI 3D 融资动态(Synera/Meshy/Adam) | A |

---

## 常规扫描建议
- **节奏**：行业媒体/厂商动态 = 周级（结合竞品监控 L2 习惯）；学术(期刊/arXiv) = 月级或按需
- **扫描触发**：手动（`web_search` 各源关键词）或用 source-channels 通道 API；暂不挂定时（成本治理）
- **升级机制**：某源曝出重大动向（如 Synera 融资、Autodesk neural CAD 发布）→ 记入方向雷达/升级报告

## 局限
- 部分源可达性未逐个体测（🟢 为本轮实证，其余待测）；Elsevier/ScienceDirect 正文仍订阅墙（摘要级）
- 中文源主要为行业媒体报道，权威性需与厂商/一手交叉
