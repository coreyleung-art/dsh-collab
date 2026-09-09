# i9 训练论文清单（标注方向 · data/i9/papers-annotation）

> 数据调查员 4787d717 · 2026-08-24 · 第二波（topic=data-annotation：BOM配方卡人机校准GUI v5 + flower-yolo 点监督伪框训练）

## 落链清单（5 篇，已向量化 KB paper-cache，annot- 前缀）
| 方向 | arXiv ID | 本地 PDF | 标题/内容 |
|------|----------|----------|-----------|
| 点监督检测 | 2412.05837 | pdfs/2412.05837.pdf | Tiny Object Detection with Single Point Supervision |
| 众包标注质控 | 2401.09760 | pdfs/2401.09760.pdf | Comparative Study on Annotation Quality of Crowdsourced |
| 伪标签自训练 | 2212.05911 | pdfs/2212.05911.pdf | Adaptive Self-Training for Object Detection |
| 伪标签经典 | 2001.08972 | pdfs/2001.08972.pdf | STAC（Semi-supervised OD 伪标签） |
| 主动学习 | 2507.06537 | pdfs/2507.06537.pdf | Model-agnostic Active Learning（动物检测） |

## 说明
- 覆盖：点监督 1 / 众包聚合质控 1 / 伪标签 2 / 主动学习 1
- 标注复审流程方向：由众包质控（2401.09760）覆盖核心（质控/聚合）；Label Studio 类工具流程为工程实践（非 arXiv，可按需补）
- 全部经流水线（下载→抽取→入库→向量化），全文在 texts/
