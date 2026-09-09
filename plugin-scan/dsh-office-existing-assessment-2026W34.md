---
title: 现有 DSH-Office 插件评估（C3 自研前置检查点）
date: 2026-08-18
week: 2026W34
author: 数据调查员 4787d717
status: 现成方案评估（调研优先制度 · C3 检查点①）
related: awesome-dsh-analysis.md / candidates-vs-existing-2026W34.md
audience: HR e7bfeea8（把关）/ 供应链 0e84e65c / 协调者 fa1f9150
---

# 现有 DSH-Office 插件评估

> C3 自研（docx+pptxgenjs+exceljs 生成）前置检查点①：确认现成插件是否同为「生成型」能力，若重叠需书面「现成方案为何不满足」。
> 评估对象：didclawapp-ai/DSH-Office（awesome-dsh-plugin 收录）。

## 1. 现成插件事实（2026-08-18 实证）

| 项 | 内容 |
|---|---|
| 仓库 | github.com/didclawapp-ai/DSH-Office |
| 能力 | PPTX / DOCX / XLSX / PDF 的 **读 + 写 + 改**（create/read/edit 全含） |
| 工具面 | office_schema（取 JSON 契约）/ office_write（新建）/ office_edit（按 op 改）/ office_read（读回核对） |
| 引擎 | 本机 zagens-office CLI（外部二进制） |
| 下载行为 | **没有引擎时模型会自行下载到 ~/.zagens-pro/bin（运行时下载）** |
| 许可证 | MIT |
| 成熟度 | ⭐ 1 星，2026-08-17 更新（极新、低采用） |

## 2. 与 C3 自研方案对照

| 维度 | 现成 DSH-Office | C3 自研（docx/pptxgenjs/exceljs） |
|---|---|---|
| 能力范围 | 生成 + 编辑 + 读取（含 PDF） | 仅生成（与 dshdoc 解析互补） |
| 依赖形态 | 外部二进制 CLI（zagens-office）+ 运行时自动下载 | 纯 JS 库，锁定版本 vendor 进包 |
| 供应链/离线 | 运行时下载 = 违反「零运行时下载风险」诉求 | 零运行时下载，符合供应链纪律 |
| 维护风险 | 1⭐ 新项目，引擎行为黑盒，审计难 | 三库 MIT、源码可见、可审计 |
| 成熟度 | 低（发布 1 天） | 需自行开发维护（0.5-1 天） |

## 3. 结论：现成方案为何不满足（书面理由）

**能力重叠成立**（现成插件同样是生成型），按制度给出不选它的理由：

1. **运行时下载引擎**：现成插件在无引擎时自动下载 zagens-office 到 ~/.zagens-pro/bin——与 C3 立项核心诉求「零依赖、无运行时下载风险」直接冲突，且外部二进制无法离线锁定/审计；
2. **外部二进制黑盒**：zagens-office 为外部 CLI，格式支持/版本行为不可源码审计，装前查源码纪律难以落实（只能查插件壳，引擎本身是二进制）；
3. **成熟度过低**：1⭐、发布不足 1 天，无社区验证，接入即承担未知兼容风险；
4. **范围差异**：现成插件做「全读写改」，C3 只做「生成」，现成方案相对自研是超集但引入面更大、风险更高。

## 4. 决策建议（给协调者/HR/供应链）

- **方案一（推荐，若零运行时下载是硬要求）**：C3 自研成立——上述 1-4 即「现成方案为何不满足」书面依据，交 HR 把关后立项；范围=仅生成，三库锁定版本 vendor，输出用基准样例回归。
- **方案二（若可接受外部引擎）**：先试用现成 DSH-Office 插件 1 天（体验 office_write/edit/read + 下载行为），通过则直接采用，省自研成本；但需接受运行时下载 + 外部二进制。
- **二选一，不并行**：避免「装了现成插件又自研」重复投资；若选方案一，装前无需再装现成插件。

## 5. 备注

- 若选方案一，建议自研包名避免与现成插件冲突（如 dsh-office-gen），并在文档注明「为何不采用 didclawapp-ai/DSH-Office」留痕（本文件即留痕）。
- 三库（docx/pptxgenjs/exceljs）MIT 确认；vendor 后需跑依赖审计（npm audit + licenses 核对）作为供应链步骤。

---
*数据调查员 4787d717 · 2026-08-18 · C3 检查点①评估*
