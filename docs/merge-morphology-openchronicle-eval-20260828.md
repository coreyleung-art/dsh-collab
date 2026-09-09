# 合并形态 + OpenChronicle 吸收 · 评估报告

> 记录：2026-08-28 ｜ 中枢 fa1f9150 ｜ 待用户拍板
> 背景：① repo-pipeline × dsh-tools version 完全合并的独立形态评估 ② OpenChronicle 记忆系统吸收评估 ③ 相关论文调研已拉本地链

---

## 一、完全合并：距离独立插件/工具/工作流还缺什么

### 1.1 现状盘点

| 组件 | 现状 | 归属 |
|------|------|------|
| 建仓（GitHub/Gitee）| ✅ repo-pipeline setup | node 插件 |
| 推送（SSH/deploy key/insteadOf）| ✅ repo-pipeline | node 插件 |
| 双仓同步 + CI/CD 工作流 | ✅ repo-pipeline | node 插件 |
| 版本管理（bump/CHANGELOG/tag）| ✅ dsh-tools version | Rust 工具 |
| 纪律接入（迭代自动版本化）| ✅ agent-bus-principles | 文档 |

### 1.2 若完全合并为「独立工具」，缺口清单

| # | 缺口 | 说明 | 工作量 |
|---|------|------|--------|
| 1 | **统一入口** | repo-pipeline（node 插件工具）+ version（Rust CLI）两个入口 → 合并为单一命令/工具 | 中 |
| 2 | **自动版本检测**（学术依据 A1）| 当前 version 需手动 --type；论文指出可 ML 自动判断 breaking/non-breaking | 大（ML）|
| 3 | **推送自动化闭环** | version 推送目前手动；需复用 repo-pipeline 的 SSH 机制（insteadOf + deploy key 自动）| 小 |
| 4 | **跨平台发布** | version 是 Rust（三平台 ✅）；repo-pipeline 是 node（插件形态）→ 合并需统一语言或桥接 | 中 |
| 5 | **工作流编排** | 完整「改码→检测→版本化→推送→双仓同步→CI」一条龙工作流（目前各步骤独立）| 中 |
| 6 | **状态/回滚** | 版本发布失败回滚、跨仓一致性校验 | 中 |

### 1.3 三种独立形态对比

| 形态 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **独立 Rust 工具**（dsh-tools 扩展）| 三平台固化、可被任意 agent 调用、性能好 | 需把 repo-pipeline 的 node 逻辑重写为 Rust | ★★★★ |
| **独立 dsh 插件**（新插件）| 与现有插件生态一致、GUI 集成 | node 重写 version 逻辑、重复维护 | ★★★ |
| **独立工作流**（脚本编排）| 组合现有工具最快 | 无统一入口、状态管理弱 | ★★ |

**推荐**：独立 Rust 工具（dsh-tools 扩展）——把 repo-pipeline 的建仓/推送逻辑用 Rust 重写进 dsh-tools，形成 `dsh-tools repo --setup/--push/--sync/--version` 全链路。学术依据：A1 论文（自动版本化）。

---

## 二、OpenChronicle 吸收评估

### 2.1 它是什么

**本地优先、模型无关的记忆层**（Python + MCP，MIT）：
- **捕获**：macOS AX Tree（辅助功能树）实时屏幕上下文 → 结构化事件（活跃 app/焦点元素/编辑文本/URL/交互状态）
- **存储**：Markdown 记忆（可检查）+ SQLite（FTS 索引）
- **时间线**：事件聚合 → 时间线
- **暴露**：8 个 MCP 只读工具（list_memories/read_memory/search/recent_activity/current_context/search_captures/read_recent_capture/get_schema）
- **CLI**: `openchronicle start/stop/pause`（daemon 模式）

**本机现状**：已装（~/.openchronicle/ 有数据目录）但**未运行**。

### 2.2 与我们体系的关系

| 维度 | OpenChronicle | 我们的体系 | 关系 |
|------|--------------|-----------|------|
| 记忆 | 屏幕上下文捕获 → Markdown/SQLite | 知识库（knowledge 插件）+ 黑板 notes/ | **互补**：它是「自动捕获工作上下文」，我们是「主动读写知识」|
| 协议 | MCP（stdio/streamable-http）| dsh 插件（cordis 服务 + 工具）| 需桥接（MCP → dsh 工具）|
| 依赖 | macOS AX（仅 mac）| 跨平台 | **限制**：仅 mac-mini/MBP 可用，i9 (win) 不可 |

### 2.3 吸收方案

**方案 X1（推荐）：OpenChronicle 作为 dsh 插件接入（桥接 MCP）**
- 写一个 `dsh-plugin-openchronicle`：启动/管理 OpenChronicle daemon + 把 8 个 MCP 工具暴露为 dsh 工具（`oc_memories` / `oc_search` / `oc_current_context` 等）
- 复用现有 `knowledge` 插件的向量索引做语义增强
- **学术依据**：MemGPT（B1）层次记忆 + AriadneMem（B2）冲突合并/时间线——OpenChronicle 的 timeline 可升级为「状态迁移边」防重复
- **安全**：MemGPT 警示的「记忆写入门控」——OpenChronicle 只读工具天然安全；若加写入须门控

**方案 X2：吸收进 knowledge 插件**
- 把 OpenChronicle 的捕获/存储能力合并进现有 knowledge 插件（避免新插件）
- 但 knowledge 是 dsh 原生、OpenChronicle 是 Python MCP——桥接复杂度相当

**方案 X3：保留独立，dsh 侧加调用工具**
- dsh 侧加 `oc_call` 工具调 OpenChronicle CLI/MCP
- 最轻，但工具不统一

**关键限制**：macOS-only（AX 依赖）→ 仅 mac-mini/MBP 部署；i9 (Windows) 不可用，需降级为手动记忆。

---

## 三、论文调研（已拉本地链）

| 论文 | 主题 | 位置 | 对我们的价值 |
|------|------|------|-------------|
| Automated Versioning（IEICE 2026）| 版本管理自动化 | papers-local/ + 论文库 | version 工具 v2 升级方向（ML 自动检测）|
| MemGPT（2310.08560）| 层次记忆 OS | 论文库（已有）+ 档案 | OpenChronicle 理论锚点 + 写门控安全 |
| AriadneMem（2603.03290）| 图记忆/状态演化 | papers-local/ + 论文库 | OpenChronicle timeline 升级（状态迁移边）|
| ID-RAG（2509.25299）| 身份记忆检索 | papers-local/ + 论文库 | 多智能体档案（agent_profile）演进 |

**待办**：拉全文 PDF → 编译 wiki 页 → ChromaDB 索引（research-pipeline 3-5 步）

---

## 四、建议路线（等用户拍板）

**合并形态**（问题一）：
- 推荐：**独立 Rust 工具**（dsh-tools 扩展）——repo-pipeline 逻辑重写进 dsh-tools，形成 repo/version 全链路
- 或轻量：先做推送自动化闭环（缺口 3），形态后议

**OpenChronicle**（问题二）：
- 推荐：**方案 X1**（dsh-plugin-openchronicle 桥接 MCP），mac 端部署，Windows 降级
- 学术支撑已就位（MemGPT 层次 + AriadneMem 时间线）

**论文**：已拉本地链（papers-local/ + 论文库），待拉全文

---
*关联：repo-pipeline-vs-version-tool-20260828.md / papers-local/versioning-memory-papers-20260828.md / OpenChronicle 源码 ~/OpenChronicle*
