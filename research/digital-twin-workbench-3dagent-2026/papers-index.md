# 论文 / 技术报告台账（数字孪生 + 3D 打印/设计智能体）

> 数据调查员 4787d717 · 2026-09-09 · 落盘本地
> 状态说明：多数 arXiv/Elsevier 正文抓取受本机网络限制（403/SSL/超时），下表为**标题 + 主题归纳 + 原文 URL**；标注【待补全文】=需有网/数据库环境拉取 PDF。
> ✅ **2026-09-09 VPN 后已下载 3 篇 arXiv 核心论文 PDF 至 `papers/`**：
> - `CADDesigner-2508.01031.pdf`（16 页）
> - `CAD-Assistant-2412.13810.pdf`（15 页）
> - `Physics-in-Loop-2605.19717.pdf`（10 页）
> - ScienceDirect 系（LLM-3Dprint/AutoMEX/3DprintMIND）仍为订阅墙，仅存 URL/DOI。DOI/来源已尽量给全便于后续补齐。

## A. 3D 打印 / 制造 智能体（LLM-Agent in AM）

| 论文 | 主题 | 来源/DOI | 状态 |
|---|---|---|---|
| LLM-3D print: Large Language Models to monitor and control 3D printing | LLM 监控与控制 3D 打印过程 | ScienceDirect 2025, [S2214860425003926](https://www.sciencedirect.com/science/article/pii/S2214860425003926) | 摘要级·待补 |
| AutoMEX: Streamlining material extrusion with AI agents powered by LLM and knowledge graphs | LLM+知识图谱 材料挤出(FDM)自动化 agent | ScienceDirect [S0264127525000644](https://www.sciencedirect.com/science/article/pii/S0264127525000644) | 摘要级·待补 |
| 3DprintMIND: AI-Agent system using LLMs and dynamic manufacturing knowledge graphs for smart manufacturing | LLM+动态制造知识图谱 智能制造 agent | ScienceDirect [S0736584525002686](https://www.sciencedirect.com/science/article/abs/pii/S0736584525002686) | 摘要级·待补 |
| Agentic Additive Manufacturing Alloy Discovery | 智能体自主增材合金发现 | [scilit](https://www.scilit.com/publications/0754048e46d41a86254147ce6bb9d98d) | 摘要级·待补 |

## B. 3D / CAD 设计 智能体（LLM-Agent in CAD/3D Design）

| 论文 | 主题 | 来源/DOI | 状态 |
|---|---|---|---|
| CAD-Assistant: Tool-Augmented VLLMs as Generic CAD Task Solvers | 工具增强多模态 VLLM 做通用 CAD 任务 | ICCV 2025, [arXiv 2412.13810](https://arxiv.org/abs/2412.13810) | 摘要级·arxiv 待补 |
| CADDesigner: Conceptual CAD Model Generation with a General-Purpose Agent | 概念 CAD 生成通用 agent | [arXiv 2508.01031](https://arxiv.org/abs/2508.01031) | 摘要级·arxiv 待补 |
| ShapeCraft: LLM Agents for Structured, Textured and Interactive 3D Modeling | LLM agent 做结构化/纹理/交互 3D 建模 | NeurIPS 2025, [HKUST](https://researchportal.hkust.edu.hk/en/publications/shapecraft-llm-agents-for-structured-textured-and-interactive-3d-) | 摘要级·待补 |
| Physics-in-the-Loop: A Hybrid Agentic Architecture for Validated CAD Engineering Design | 物理在环混合 agent 架构做经验证 CAD 设计 | [arXiv 2605.19717](https://arxiv.org/pdf/2605.19717.pdf) | 摘要级·arxiv 待补 |
| (RL) Autonomous layout method for 3D printing parts using small-parameter VLM | RL+小参数 VLM 自主 3D 打印排版 | ScienceDirect [S0278612526001524](https://www.sciencedirect.com/science/article/abs/pii/S0278612526001524) | 摘要级·待补 |

## C. 数字孪生 / 相关（技术报告 / 开源项目）

| 报告/项目 | 主题 | 来源 | 状态 |
|---|---|---|---|
| PhanLong (Trepo TUNI) Digital Twin 硬件 9 components | 数字孪生搭建 9 大硬件部件清单 | [trepo.tuni.fi PDF](https://trepo.tuni.fi/bitstream/handle/10024/229544/PhanLong.pdf) | 待补全文 |
| Twinmodel Digital Twin for Line-Follower Robot | 开源数字孪生（MATLAB+Unity+ESP32, PID, UDP/TCP, HTTP dashboard） | [GitHub](https://github.com/Twinmodel/Design-and-Implementation-of-Digital-Twin-for-a-Line-Follower-Robot/) | 开源可拉 |
| Digital-twin Smart Shipping Workstation (Omniverse) | Omniverse 数字孪生工作台 + Arduino | [Hackster](https://www.hackster.io/kutluhan-aktar/digital-twin-enabled-smart-shipping-workstation-w-omniverse-049792) | 可读 |
| PiLiDAR | 开源 LiDAR 项目 | [GitHub](https://github.com/PiLiDAR/PiLiDAR) | 开源可拉 |
| 树莓派本地数字孪生原型教程 | ESP32+传感器→3D 可视化 | [CSDN 专栏](https://wenku.csdn.net/column/9k042jx5p1c) | 已抓要点 |

> 补充：CAD 龙头 Autodesk AU2025 发布 "neural CAD"（[Engineering.com](https://www.engineering.com/autodesk-introduces-neural-cad-at-au-2025/)，403 待补）——CAD 原生 AI 方向，建议纳入论文级持续跟踪。

## 补全文指引（待有网/库环境）
```bash
# arXiv 原文（本机网络暂不可达时可用）
# https://arxiv.org/pdf/<id>
# DOI 原文（需订阅/机构库）
# LLM-3Dprint: doi:10.1016/j.addma.2025.xxx (S2214860425003926)
# CAD-Assistant: https://arxiv.org/pdf/2412.13810
```
