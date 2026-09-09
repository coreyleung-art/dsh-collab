# 文件/文档管理增强 — 交付物（session-3b5efeef，2026-08-16）

> 跨会话协作成果物（约定 v1）。调研报告本体在 Obsidian `wiki/research/file-doc-management.md`，本文件为可执行结论与验证记录。

## 背景与结论

本机 DSH 文件管理底层（沙箱 workspace-write / fs 工具 / 先读后改观察策略）已对齐 Anthropic 级设计，缺口在**二进制文档解析（PDF/DOCX/XLSX 进 agent 上下文）**与**原生知识库/RAG**。采用 DSH 社区三个插件补齐，全部本地化、零外部服务。

## 已安装与配置（web profile）

| 插件 | 版本 | 安装源 | 工具 | 说明 |
|---|---|---|---|---|
| dsh-files | 0.2.0 | GitHub clone → `file:` 本地源（`~/dsh-plugin-files`） | `read_document` + 上传 | PDF/DOCX/XLSX，内容嗅探不信任扩展名，UTF-16/UTF-8/GB18030 编码链，LRU 缓存 |
| dsh-knowledge | 0.1.0 | npm | 12 个 `knowledge_*` | 知识库/RAG：分组、多格式导入、标题感知分块、混合检索 BM25+向量+RRF、管理面板 |
| dsh-doc | 0.1.1 | npm | `dshdoc_extract` / `dshdoc_health` | Docling 结构解析；macOS 用 `engine: node` + `defaultOcr: false` |

配置要点（`~/.dsh/profiles/web/cordis.patch.yml`）：
- patch 条目必须用显式 `- id: <行id>` 形式（简写 `- <id>:` 在本版本不生效——顺带修复了 web-runtime trustedHosts 简写失效的历史问题）。
- `knowledge` 行 embedding 指向本机 Ollama（nomic-embed-text，与 research 流水线同款）。
- `pnpm-workspace.yaml` 放行了 `onnxruntime-node` / `protobufjs` postinstall。

## 验证结果（崩溃恢复后实测）

- `dshdoc_health` → xberg-node 引擎 ready（OCR unavailable 符合 macOS 配置预期）
- `knowledge_create_base` → 入库 → `knowledge_search`：hybrid 检索命中（建库 fdm-smoke-test，1 文档）
- `read_document`（文本）正常；`dshdoc_extract` 解析 wiki 报告成功

## 发现并修复的 bug：dsh-files 嗅探 8192B 窗口截断

**现象**：`detect.js` 固定 8192 字节探测窗口，窗口边界截断多字节 UTF-8 字符时 fatal 解码失败 → 误判「unrecognized file content」→ 所有 >8KB 中文文本文件无法读取（实测复现，如 `wiki/research/file-doc-management.md`）。

**修复**：`lib/detect.js` 的 `looksLikeUtf8` 增加窗口边界容忍（文件仍有后续字节时接受）；`looksLikeGb18030` 增加逐字节回退重试。双处补丁：
- 运行实例：`~/.dsh/profiles/web/node_modules/dsh-files/lib/detect.js`
- 源克隆：`~/dsh-plugin-files/lib/detect.js`（重装不丢）

**验证**：node 直接加载补丁后模块实测——目标文件识别为 text ✅，EOF 真截断仍正确拒绝 ✅。**下次 CLD 重启后对运行实例生效**（模块已在内存中）。上游未修，可考虑提 PR。

## CLD 崩溃调查结论（15:36）

与本次安装**无关**：根因是当日 00:28 app.asar 被替换（CLD 服务器模式修复）后未重新签名，ad-hoc 签名资源封口破损（`codesign -v` 报 "code has no resources but signature indicates they must be present"），dyld 加载时报 Code Signature Invalid。本会话改动仅限 `~/.dsh`，profile 内新增原生二进制全部 `codesign -v` 通过。CLD 已自恢复；建议 `codesign --force --deep --sign - /Applications/CLD.app`（由协调方在重启窗口评估，等用户确认）。

## 落库

- 调研报告：`Obsidian/wiki/research/file-doc-management.md`（10 来源 + 实施记录 + 崩溃调查）
- 原始资料：`Obsidian/raw/research/2026-08-16-file-doc-management/`
- ChromaDB research 集合：135+ 文件 / **9904 块（bge-m3 1024 维；含 cross-session-intel-r1 89 块及协作文档增量；dsh-docs 集合为 nomic 768 维 2990 块，playbook 27 块已入）**，语义检索命中验证通过
- 操作日志：`Obsidian/wiki/log.md`（15:22 实施 / 15:45 验证+排障）

## 重启待办清单（重启窗口统一生效）

1. 三件套工具上线（read_document / knowledge_* / dshdoc_*）
2. dsh-files 嗅探补丁生效（可 @本会话验证）
3. agent-bus 常驻版（session-fa1f9150 的 dsh-plugin-agent-bus）
4. CLD.app 重签评估（协调方，等用户确认）
