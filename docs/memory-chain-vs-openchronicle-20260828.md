# 本机记忆链 vs OpenChronicle · 区别与共性分析

> 记录：2026-08-28 ｜ 中枢 fa1f9150 ｜ 背景：评估 OpenChronicle 吸收为 dsh 插件/工具

---

## 一、本机记忆链全景（现有组件）

| 组件 | 形态 | 记忆内容 | 写入方式 | 读取方式 | 数据位置 |
|------|------|---------|---------|---------|---------|
| **dsh-knowledge 插件** | dsh 插件（cordis）| 知识库文档（base+chunk+embedding）| **主动**（knowledge_add_document / import_url）| knowledge_search（混合 BM25+向量）/ read_document | ~/.chroma（向量）+ SQLite |
| **黑板 rust-blackboard** | Rust 服务（launchd）| notes/ + data/ 跨设备消息与状态 | **主动**（PUT 写入）| GET / notes / SSE 订阅 | ~/dsh-collab/token-monitor/blackboard |
| **agent-bus.json** | dsh 插件持久化 | 线程/档案/锁/审批 | **主动**（agent_send/register）| agent_thread / agent_profiles | ~/.dsh/agent-bus.json |
| **Obsidian vault** | iCloud 目录 | wiki/ + raw/ + 日记（LLM Wiki 三层）| **主动**（ingest）| 全文 + ChromaDB 语义 | iCloud Obsidian |
| **ChromaDB（~/.chroma）** | 向量库 | knowledge + obsidian 的向量索引 | 自动（index 时）| 语义检索 | ~/.chroma |
| **OpenChronicle** | Python+MCP | **屏幕/应用上下文捕获** | **被动自动**（AX Tree 捕获）| 8 个 MCP 工具 | ~/.openchronicle/ |

**共同点**：都服务于「知识复利」——把上下文沉淀为可检索的记忆。

## 二、OpenChronicle 独有特征（本机记忆链没有的）

| 特征 | OpenChronicle | 本机记忆链 |
|------|--------------|-----------|
| **捕获源** | macOS AX Tree（实时屏幕/活跃 app/焦点元素/编辑文本）| 无屏幕捕获（纯主动写入）|
| **写入方式** | **自动被动**（daemon 持续捕获，无需人工/agent 触发）| **主动**（agent 调用工具写入）|
| **原始捕获层** | S1 buffer（search_captures/read_recent_capture 读原始事件）| 无原始层（直接写整理后内容）|
| **LLM 压缩层** | writer/llm.py + session_reducer（自动压缩会话→记忆）| 部分有（agent 自己整理）|
| **时间线** | timeline/（事件聚合→时间线）| 黑板有 timeline（全局 seq），但无 UI 时间线记忆 |
| **用户画像** | user-profile.md + user-preferences.md（自动构建）| 无（agent_profile 是角色档案，非用户画像）|

## 三、区别（维度对比）

### 3.1 记忆来源
- **本机记忆链**：agent/人**主动**投喂（知识库 ingest、黑板写入、档案登记）——记忆 = 我们选择记录的东西
- **OpenChronicle**：系统**被动**捕获（AX Tree 自动感知屏幕/应用状态）——记忆 = 环境自动记录的东西

### 3.2 记忆粒度
- **本机**：文档级（wiki 页 400-1200 词）+ 消息级（黑板 notes/线程）
- **OpenChronicle**：事件级（每次捕获的 AX 快照）→ 聚合为 session → 压缩为 memory

### 3.3 处理深度
- **本机**：向量化（embedding）+ BM25 混合检索
- **OpenChronicle**：LLM 压缩（session_reducer）+ FTS 全文 + 自己的 chroma 向量

### 3.4 时效性
- **本机**：写入即检索（主动时点）
- **OpenChronicle**：持续流式捕获（实时工作上下文）

### 3.5 跨设备
- **本机**：✅ 黑板跨 mac-mini/MBP/i9（Tailscale）
- **OpenChronicle**：❌ 仅 macOS 单机（AX 依赖）

## 四、共性（核心一致）

1. **都遵循「捕获/写入 → 存储 → 索引 → 检索」记忆流水线**
   - 本机：写入(知识库/黑板) → SQLite/Chroma → BM25+向量 → search
   - OpenChronicle：捕获(AX) → Markdown/SQLite → FTS+chroma → search
2. **都用 Markdown + SQLite 双形态**（可检查 + 可查询）
3. **都做 LLM 参与的内容整理**（本机 agent 整理 / OpenChronicle writer 压缩）
4. **都定位「本地优先」**（数据在本机，不上云）
5. **都服务「知识复利」目标**（用户主线：token 越来越省，靠记忆复用）

## 五、互补性判断（吸收价值）

**OpenChronicle 补的是本机记忆链的「自动捕获」空缺**：
- 本机记忆链缺「**被动持续感知工作上下文**」——OpenChronicle 的 AX 捕获正好补上
- 若吸收：agent 能自动知道「用户此刻在做什么」（current_context），无需询问

**但有取舍**：
| 取舍 | 说明 |
|------|------|
| macOS-only | i9 (Windows) 无法部署 → 三端不对称 |
| 数据双轨 | OpenChronicle 独立 chroma/memory 目录 vs 本机 ~/.chroma —— 需归一化 |
| 捕获隐私 | AX Tree 捕获的是「屏幕可见内容」——敏感信息会进记忆（需门控/过滤）|
| 运行成本 | daemon 常驻 + LLM 压缩调用（本地 qwen 零计费可解）|

## 六、结论

**区别本质**：本机记忆链是「**主动记录型**」（我们决定记什么），OpenChronicle 是「**被动感知型**」（环境自动记什么）。两者是记忆的两半——**主动知识（我们在意的）+ 被动上下文（用户实际在做的）**。

**共性**：都遵循同一条「捕获→存储→索引→检索」流水线，都本地优先 + Markdown/SQLite + LLM 整理——**架构同构**，吸收成本低。

**吸收建议（呼应评估报告方案 X1）**：dsh-plugin-openchronicle 桥接 MCP，mac 端部署；数据归一化到 ~/.openchronicle（不并入 ~/.chroma，避免双轨）；AX 捕获加敏感过滤门控。

---
*关联：merge-morphology-openchronicle-eval-20260828.md / 记忆系统论文（MemGPT/AriadneMem）/ OpenChronicle 源码 ~/OpenChronicle*
