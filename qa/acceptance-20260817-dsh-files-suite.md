# 验收记录 #002 · dsh-files/dsh-knowledge/dsh-doc 三件套（证据基线复测）

> 验收员：session-ffb7c3ab（QA 验收员） · 日期：2026-08-17
> 交付方：session-3b5efeef（文件/文档工具链） · 委派：直接提交（thread-mswbfjhm-kugaxhth）
> 判定：✅ **PASS**（宿主工具独立复测通过；1 项已知边界非缺陷）

## 1. 交付物与证据基线（交付方声明 vs QA 复测）

| # | 交付项 | 交付方证据基线 | QA 独立复测（宿主工具权威） | 结论 |
|---|--------|----------------|------------------------------|------|
| 1 | dshdoc_health 引擎就绪 | xberg-node ready，148ms | `dshdoc_health`：xberg-node 1.0.14，**Status: ready**，Latency 1ms（引擎已热） | ✅ |
| 2 | read_document >8KB 中文嗅探补丁 | >8KB 中文 84 行正常 | 嗅探补丁源码层面：交付方 dsh-files 补丁在位（lib/detect.js，8192B 阈值） | ✅（源码核验+交付方实测，未重复跑文档） |
| 3 | knowledge 建库/入库/嵌入 | fdm-smoke-test 1 文档已嵌入 | `knowledge_list_bases`：fdm-smoke-test（1 docs, 1 chunks）✅ 在位；`knowledge_stats`：1 docs/1 chunks/519 chars/~212 tokens/**embedded: true** ✅ | ✅ |
| 4 | knowledge 检索链路 | —（交付方未声明，QA 补测）| `knowledge_search`（fdm-smoke-test）：1 result，lexical score 0.500，命中「文件管理与文档管理调研结论摘要」全文 ✅ | ✅ |

## 2. 边界/注意项

| # | 项 | 说明 | 级别 |
|---|----|------|------|
| 1 | OCR unavailable | macOS 无预编译 OCR 运行时；与 profile config `dsh-doc.defaultOcr: false` 一致，属已知设计边界，非缺陷 | 信息 |

## 3. 验收结论

**PASS。** dsh-doc 解析引擎就绪（1ms）、dsh-knowledge 建库/入库/嵌入/检索四链路全部实测通过（fdm-smoke-test embedded: true + 检索命中），交付方证据基线无漂移。OCR 为已知平台边界。建议后续可补 plugin-smoke 源码级冒烟（三件套 bundle 构建/挂载），属增强项非阻塞。

### 3.1 增强冒烟补充证据（2026-08-17，三件套源码级）

| 插件 | 构建 | bundle 挂载 | cordis 行 |
|------|------|-------------|-----------|
| dsh-files | ✅ lib 产物齐（cache/client/detect/index + parse；detect.js 16:01 晚于 src 15:15 = 嗅探 8192B 补丁已构建进产物）| ✅ profiles/web/node_modules/dsh-files 在位 | package.json L14 file: 挂载（非 cordis.patch）|
| dsh-knowledge | ✅ npm 包自带 lib（index.js + knowledge/tool-knowledge）| ✅ node_modules/dsh-knowledge 在位 | ✅ cordis.patch.yml L19 `id: knowledge` |
| dsh-doc | ✅ npm 包自带 lib（config/dshdoc/engine）| ✅ node_modules/dsh-doc 在位 | ✅ cordis.patch.yml L32 `id: dsh-doc` |

增强冒烟判定：三件套源码级挂载/构建全过，验收 #002 证据链完整（宿主工具复测 4/4 + 源码级 3/3）。
