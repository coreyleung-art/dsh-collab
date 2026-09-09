# labforge + 内存实验室 · R006 九项标准对齐登记

> mbp-ops · 2026-09-05 · 依 R006（mbp-tools-r006-alignment.md 同款 9 项）
> 9 项：①dsh 插件形态 ②TCC 检测 ③CLD 自适应 ④dsh 版本自适应 ⑤文档化 ⑥版本管理 ⑦统一日志 ⑧自动落链 ⑨CLI 治理
> 适用：脚本/工具类重点 ⑤⑥⑦⑧⑨；插件类全 9 项；本批产物 = CLI 工具（labforge 引擎 + runners），插件化待下一步（见 §四）

## 一、产物清单与 9 项对齐

| 产物 | 类型 | 版本 | 属主 | ①插件 | ②TCC | ③CLD | ④dsh | ⑤文档 | ⑥版本 | ⑦日志 | ⑧落链 | ⑨CLI |
|------|------|------|------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| labforge（引擎） | CLI | v1.1.0 | mbp-ops | - | - | - | - | ✅README | ✅--version | ✅logs/ | ✅results/归档 | ✅9子命令 |
| runner-crash.js | runner | v1.0.0 | mbp-ops | - | - | - | - | ✅头注释 | ✅头戳 | ✅(经labforge) | ✅ | ✅ |
| runner-perf.js | runner | v1.0.0 | mbp-ops | - | - | - | - | ✅头注释 | ✅头戳 | ✅(经labforge) | ✅ | ✅ |
| lib/assert-engine.js | 提取产物 | v1.0.0 | mbp-ops | - | - | - | - | ✅头注释 | ✅头戳 | 回调 | ✅ | 可CLI |
| oom-sim.js | 模拟器 | v1.0.0 | mbp-ops | - | - | - | - | ✅头注释 | - | - | ✅ | ✅ |
| 内存崩溃实验室 | 资产集 | v1.0.0 | mbp-ops | - | - | - | - | ✅报告.md | - | - | ✅ | ✅ |
| 实验卡×3 | 数据 | v1 | mbp-ops | - | - | - | - | ✅ | ✅卡内created | ✅ | ✅results | ✅ |

## 二、本次对齐动作（2026-09-05）

1. **版本管理（⑥）**：labforge v1.1.0（--version）；runners/lib 头戳 v1.0.0；实验卡 created/lastResult 时间戳
2. **文档化（⑤）**：README.md（用法/卡片schema/runner契约/循环工作流/借鉴映射）；本登记表统一归档
3. **统一日志（⑦）**：labforge 运行日志 → `~/dsh-collab/logs/labforge.log`（时间戳追加）
4. **自动落链（⑧）**：每次 run 结果 → `results/<id>.latest.json` + `results/<id>-<ts>.json` 双落链；卡状态自动更新
5. **CLI 治理（⑨）**：new/run/eval/loop/regress/hypotheses/status/design/--version 共 9 子命令

## 三、产物提取清单（从过程沉淀中抽出可复用件）

| 提取物 | 来源 | 用途 |
|---|---|---|
| lib/assert-engine.js | labforge 断言逻辑 | 任意 JSON 产物的通用断言（dig 路径 + op 判定），独立复用 |
| runner-perf.js | P2-1 POC bench | 全量 vs 尾部窗口性能对比，通用 perf 实验 runner |
| runner-crash.js | 内存崩溃实验室 | full vs tail 崩溃/内存对照，通用 crash runner |
| 实验卡模板 ×3 | 内存治理/帧索引 | 可回归断言集（OOM 复现/单会话治理/perf） |
| 卡片 schema | labforge new 模板 | 声明式实验定义（goal/hypothesis/assertions） |

## 四、插件化评估与下一步（对应 ① 及全 9 项）

- **已交付插件工程**（2026-09-05，构建+冒烟通过，产物归档 labforge/plugins/）：
  - P1 `dsh-plugin-labforge-assert`（tool）：模型可直接调用 `labforge_assert` 通用断言（dig 路径+op 判定）；cordis.patch 带 maxAssertions 配置
  - P2 `dsh-plugin-labforge-cmd`（command）：`/labforge run|eval|status|hypotheses|design` 调 CLI；config.labforgeBin/allowRun
- **挂载状态**：⚠️ **未挂载到任何 profile** —— macmini 仅有生产 web profile，新建 dev profile 需处理依赖环境（pnpm store/共享缓存风险），按"不动生产"纪律暂停挂载；插件代码可随时在 dev profile 就绪后 `dsh plugin add`
- **②TCC**：插件化后需补 TCC 检测（同 central-inbox 待办）
- **P3 已完成**：实验结果自动落黑板（notes/mac-mini/labforge-results.md）+ 向量化（guard-recall 104 文档）

## 五、登记提交

- 本表 → tools-registry.md 吸收（mac-mini 维护）；产物已在 `~/dsh-collab/guard/tools/labforge/` + `poc/memory-crash-lab/`
- 已向量化：调研 + labforge README + 实验结果 → guard-recall（检索命中验证 ✅）
