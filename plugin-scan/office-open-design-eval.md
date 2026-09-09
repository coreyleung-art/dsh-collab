# DSH-Office 自研评估 + open-design 对接评估（供应链专员）

- 响应：b241741f 决策更新（③ DSH-Office 转自研评估 ④ open-design 直接对接）
- 时间：2026-08-18 · 供应链视角（依赖面/资源/风险）

---

## 一、DSH-Office 自研可行性评估

### 背景
- 用户质疑：DSH-Office 非官方插件，依赖 zagens-office 引擎**运行时下载**（~/.zagens-pro/bin），供应链信任风险
- 本机 dshdoc 已覆盖文档**读取**；缺口是**写/编辑**（PPTX/DOCX/XLSX 生成与修改）

### 开源参考候选（npm 生态实测）

| 库 | 版本 | 能力 | 依赖面 | 适配评估 |
|----|------|------|--------|---------|
| **docx** | 9.7.1 | DOCX 生成（声明式 API） | 零依赖 | ✅ 直接可用（TS 原生） |
| **pptxgenjs** | 4.0.1 | PPTX 生成 | 低 | ✅ 直接可用 |
| **exceljs** | 4.4.0 | XLSX 读写 | 低 | ✅ 直接可用 |
| **docxtemplater** | 3.69.3 | 模板填充（docx/pptx/xlsx） | 低 | ✅ 模板场景优 |
| **officegen** | 0.6.5 | OOXML 流式生成 | 中 | 维护度低，不推荐 |
| **Univer**（dream-num） | 14.1K⭐ | 全栈表格/文档/演示（web+server） | 大 | 重型，超需求 |

### 自研方案（推荐）

**「三库组合 + 薄壳工具」轻量自研**：
- 写入层：`docx`（DOCX）+ `pptxgenjs`（PPTX）+ `exceljs`（XLSX）——均为零/低依赖、TS 友好、npm 稳定
- 读取层：复用现有 dshdoc（已覆盖读取）
- 工具面：`office_write`（生成）/ `office_edit`（按 op 修改）/ `office_read`（读回核对）——与 DSH-Office 同契约，但**无运行时下载**（纯 npm 依赖，供应链可控）
- 依赖面：3 个库合计新增依赖 ~5-8 个（均为纯 JS，无原生编译）

### 供应链对比

| 维度 | DSH-Office（第三方） | 自研（三库组合） |
|------|---------------------|-----------------|
| 引擎 | zagens-office（**运行时下载**，信任风险） | 纯 npm 依赖（install 时锁定） |
| 依赖面 | 零 deps + 外部引擎 | 3 库 + ~5-8 传递依赖 |
| 供应链控制 | 外部下载源不可控 | lockfile 钉死，完全可控 |
| 能力 | PPTX/DOCX/XLSX/PDF | PPTX/DOCX/XLSX（PDF 读取已有 dshdoc） |
| 维护 | 第三方节奏 | 自研可控 |

### 结论：**自研可行且更优**（用户判断正确）
- 三库组合覆盖写/编辑需求，无运行时下载风险
- 工作量：薄壳工具 + cordis 挂载（参照现有插件模式，约 0.5-1 天）
- PDF 写入若需可后补（libreoffice headless 转换或 pdf-lib）

## 二、open-design 对接评估

### 资源占用实测
- **桌面应用**：mac-arm64.dmg **304MB**（v0.19.2），win-x64 330MB
- 运行时：daemon + GUI 常驻，预估内存占用 **300-800MB**（桌面应用常态）
- 当前系统内存 25% 偏紧（协调者记录）——**安装前需内存评估，可能加剧压力**

### 对接方式
- 已原生支持 DSH：`od agent setup deepseek-harness`（官方 dsh CLI 连接组件）
- 但 `od` 命令与系统 `/usr/bin/od`（octal dump）**冲突**——需 PATH 管理或别名（安装后 open-design 的 od 优先）

### 替代开源设计项目候选（可改造为 dsh 插件）

| 项目 | 星数 | 能力 | 改造评估 |
|------|------|------|---------|
| **excalidraw/excalidraw** | 129.9K⭐ | 白板/手绘草图 | ✅ 前端库可嵌入 web GUI 为设计画布 |
| **dream-num/univer** | 14.1K⭐ | 全栈表格/文档/演示 | 🔶 重型，若需 office 编辑可作 DSH-Office 替代基础 |
| **penpot/penpot** | 58.8K⭐ | 开源 Figma 替代（设计系统） | 🔶 服务端重，不适合本地插件 |
| 现有 OpenPencil/ui-spec | — | 本机已有编辑画布 | ✅ 与 open-design 互补已确认 |

### 结论
- **open-design 对接可行但资源重**（304MB + 常驻内存）——建议内存缓解后或用户明确需要设计工作流时再装
- 若目标仅是「设计能力增强」，**excalidraw 嵌入 web GUI** 是轻量替代（纯前端，无 daemon，改造为 dsh 插件成本低）
- Univer 可作 DSH-Office 自研的进阶基础（若需 web 端编辑体验）

---

## 三、建议（转用户）

1. **DSH-Office → 自研**（三库组合 docx+pptxgenjs+exceljs + 薄壳工具）：供应链可控、无运行时下载、工作量 0.5-1 天
2. **open-design**：可对接（已原生支持 DSH）但 304MB+ 常驻内存——建议内存缓解后或需要时再装；轻量替代 = excalidraw 嵌入
3. 自研 Office 若需 web 编辑体验，可基于 Univer 扩展（后期选项）
