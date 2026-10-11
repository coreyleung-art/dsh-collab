# R006 内容索引（自动生成，勿手改）

> 规格：`/Users/coreyleung/dsh-collab/docs/R006-插件化工具化标准-v3.0.md` · sha256(前16) `9dbe7085eba53fc2` · 305 行 · KB `r006-tooling-standard-kb`
> 重新生成：`python3 /Users/coreyleung/dsh-collab/scripts/r006-index.py` · 自校验加 `--verify`

## 章节速查

| 节 | 锚点 | 关键词 | 摘要 |
|---|---|---|---|
| 0 · 一句话与适用范围 | `#0-·-一句话与适用范围` | lean4-check, comm-layer, bus-bridge, bb-sub, --lean4-check, /opt/comm-layer, 一句话, 十项全达标才交付 | 一句话：凡新做插件或工具，十项全达标才交付；第 ⑩ 项要求"不该发生的路径"在结构上不可绕过，并自带 --lean4-check 证明。 |
| 1 · 为什么有这条标准（历史事故，全部有实据） | `#1-·-为什么有这条标准历史事故全部有实据` | central-inbox, restart-guard, R035, PATH, type:module, ReferenceError, 规律, 缺一项可机械核验的标准 | | 事故 | 缺哪一项 | 后果 | |
| 2 · 十项逐项规格 | `#2-·-十项逐项规格` | 十项逐项规格 | > 每项给出：定义 / 验收标准（可机械核验）/ 自检命令 / 反例。 |
| ① dsh 插件形态 | `#①-dsh-插件形态` | package.json, cordis.patch.yml, lib/index.js, ERR_MODULE_NOT_FOUND, dsh-tools, UNSUPPORTED_SCHEMA, ./lib/index.js, ~/dsh-plugin-openpencil | 定义：以 dsh 插件形式交付，可被宿主挂载（而非裸脚本）。 |
| ② TCC 检测（能力边界自检） | `#②-tcc-检测能力边界自检` | selfcheck.js, --selfcheck, <tool> --selfcheck, 定义, 能力边界, 不能做什么, 验收标准, 自检 | 定义：工具必须能自报能力边界——它能做什么、不能做什么、哪些路径"不该发生"。 |
| ③ CLD 自适应 | `#③-cld-自适应` | --selfcheck, 定义, 验收标准, 自检, 反例, CLD, 自适应 | 定义：不依赖 CLD/宿主内部 API 才能工作；在无 CLD 环境下可独立运行（降级或拒绝，而非崩溃）。 |
| ④ dsh 版本自适应 | `#④-dsh-版本自适应` | dsh-runtime, peerDependencies, --selfcheck, node_modules, 定义, 验收标准, 明确降级行为, 自检 | 定义：不锁死某个 dsh/宿主内部 API 版本；peer 依赖走正式声明并被解析。 |
| ⑤ 文档化 | `#⑤-文档化` | package.json, r006.documented, 定义, 独立复现, 验收标准, 自检, 反例, 文档化 | 定义：一个读者能据此独立复现的文档。 |
| ⑥ 版本管理 | `#⑥-版本管理` | CHANGELOG, tool-version, CHANGELOG.md, package.json, VERSION, --tool-version, .py, <tool> --tool-version | 定义：版本号单一来源，改动有 CHANGELOG。 |
| ⑦ 统一日志 | `#⑦-统一日志` | ~/dsh-collab/logs, print, 定义, 验收标准, 失败也留痕, 自检, 反例, 统一日志 | 定义：结构化、可追溯、落盘固定路径。 |
| ⑧ 自动落链 | `#⑧-自动落链` | RULES.md, data/registry/, GET /data/registry/<key>, knowledge_search, 定义, 检索到, 验收标准, 自检 | 定义：产出必须被登记，别人能检索到它。 |
| ⑨ CLI 治理 | `#⑨-cli-治理` | dry-run, json-out, README, CHANGELOG, 成功 ·, 失败/门失效 ·, 用法或 IO 错误 ③ 存在, --json | 定义：CLI 行为规范、可预测、可脚本化。 |
| ⑩ 约束前置 · 不可绕过（Lean4 逻辑门） | `#⑩-约束前置-·-不可绕过lean4-逻辑门` | lean4-check, --lean4-check, <tool> --lean4-check, 定义, 不该发生的路径, 结构上不可绕过, 验收标准, 没有那个入口 | 定义：工具若涉及"不该发生的路径"（违规写 / 越权 / 跳步 / 非法引用 / 为局部目标杀全局），约束必须结构上不可绕过，并自带证明。 |
| 3 · 交付物模板 | `#3-·-交付物模板` | tool-or-plugin, package.json, cordis.patch.yml, index.js, selfcheck.js, R014, gate.js, cli.js |  |
| 3.1 `package.json` 最小字段 | `#31-packagejson-最小字段` | dsh-plugin, lib/index.js, ./cordis.patch.yml, deepseek-ai, dsh-tools, mac-mini, docs/README.md, ~/dsh-collab/logs | json |
| 3.2 `selfcheck.js`（② 的落地） | `#32-selfcheckjs②-的落地` | ~/.dsh/profiles, ~/.dsh/plugin-selfcheck, selfcheck.js, **★ 血泪条**：不给, ★ 血泪条, 假失败, `selfcheck, js` | js |
| 4 · ⑩ 约束门的四种门型与 `--lean4-check` 六项模板 | `#4-·-⑩-约束门的四种门型与---lean4-check-六项模板` | 约束门的四种门型与, `--lean4-check`, 六项模板 |  |
| 4.1 四种门型（按场景选，可叠加） | `#41-四种门型按场景选可叠加` | JSON, enum, required, idle→running→done, 类型锁, 入口门, Schema 门, 状态机 | | 门型 | 机制 | 适用 | |
| 4.2 `--lean4-check` 六项模板（全绿才交付） | `#42---lean4-check-六项模板全绿才交付` | dry-run, GateError, --dry-run, Object.isFrozen(...), | 源码无危险原语 |, | 正例可用 | 合法输入必须能通过（, ） |
|, 外部状态实测一致 | | 项 | 证明内容 | 实现要点 | |
| 5 · 验收流程（三步，可复制） | `#5-·-验收流程三步可复制` | lean4-check, tool-version, package.json, dry-run, RULES.md, data/registry/, r006, 收尾 | bash |
| 6 · 常见坑（全部有实据） | `#6-·-常见坑全部有实据` | cld-voice, PATH, ~/CLAUDE.md, cld, 门太宽, 先精确白名单命中，再对非白名单输入判禁用词, 扫描器误伤自己, 空洞通过 | | # | 坑 | 表现 | 修法 | |
| 7 · 参考实现（已达标实例） | `#7-·-参考实现已达标实例` | CHANGELOG, phi-user-sovereignty, dsh-plugin-cldvoice-activate, ~/dsh-collab/devices/dsh-plugin-cldvoice-activate, UNSUPPORTED_SCHEMA, dsh-plugin-agent-way, agent-bus, ~/dsh-plugin-agent-bus | > - §7 参考实现 / §8 补课排期 / §9 检索索引 = 清单·排期·检索类，非规范性 → 编排者（星桥）可自主增补，但须在本文件 CHANGELOG 记明"非规范性增补 |
| 8 · 存量工具补课排期（按影响面） | `#8-·-存量工具补课排期按影响面` | cloudbase-handshake.sh, device-daemon.py, cldvoice-activate.sh, export-marker.py, deliver.py, red-team.py, unit-review.py, stance-auditor.py | 优先级 P0（涉及"不该发生路径"）：部署/重启类（cloudbase-handshake.sh、device-daemon.py、cldvoice-activate.sh）、发布 |
| 8.1 真挂载冒烟存量补课（2026-09-11 用户裁定：**全部 32 个都补**） | `#81-真挂载冒烟存量补课2026-09-11-用户裁定全部-32-个都补` | ~/dsh-plugin-openpencil, tests/client.test.mjs, dsh-plugin-reflect-collect, lib/selfcheck.js, dsh-plugin-reflect-dispatch, cli.js, dsh-plugin-cldvoice-activate, deepseek-ai | 盘点基线（同日实测，判据见 §2 ① 第 5 项；登记口径：只认"带接收者的 .apply( 调用 + import 痕迹"，关键词与函数定义不算）： |
| 9 · 检索与索引（怎么在 10 秒内找到本文件） | `#9-·-检索与索引怎么在-10-秒内找到本文件` | ~/dsh-collab/docs/R006-index.json, r006-tooling-standard-kb, ~/dsh-collab/rules-registry/RULES.md, R006, ~/CLAUDE.md, 机器索引, 知识库, 规则账本 | 机器索引：~/dsh-collab/docs/R006-index.json（结构化：section → anchor → keywords → 摘要） |
| 快速查询话术（给任何会话） | `#快速查询话术给任何会话` | R006, -v3.0.md, r006-tooling-standard-kb, 锚点速查, 快速查询话术, 给任何会话 |  |
| 附 · CHANGELOG | `#附-·-changelog` | dsh-plugin-cldvoice-activate, UNSUPPORTED_SCHEMA, package.json, json-out, README, CHANGELOG, bb-write.py, R006 | v3.1.1-a（2026-09-13，星桥 · 非规范性更正 §7 清单）：§7 参考实现表里 dsh-plugin-cldvoice-activate 原写"十项全达标" —— |

## 快速话术

- **要做插件/工具 → 需要满足什么** → §2 十项逐项规格 + §3 交付物模板
- **约束门怎么写** → §4 四种门型 + --lean4-check 六项模板
- **交付前怎么验收** → §5 验收流程（三条命令）
- **踩过的坑** → §6 常见坑（7 条）
- **照抄哪个实例** → §7 参考实现
- **还要补哪些工具** → §8 存量工具补课排期

## 历史文档（已并入 v3.0，保留作证据）

- `/Users/coreyleung/dsh-collab/docs/labforge-r006-alignment.md`
- `/Users/coreyleung/dsh-collab/docs/meeting-verify-r006-ten.md`
- `/Users/coreyleung/dsh-collab/docs/plugin-eval-rule-v1.md`
- `/Users/coreyleung/dsh-collab/docs/plugin-selfcheck-spec-v1.md`
- `/Users/coreyleung/dsh-collab/docs/r006-proposal-lean4-gate-v1.md`
- `/Users/coreyleung/dsh-collab/docs/wargame-engine-r006-ten.md`
- `/Users/coreyleung/dsh-collab/docs/wargame-r006-ten.md`

## 参考实现

- **dsh-plugin-cldvoice-activate** — `~/dsh-collab/devices/dsh-plugin-cldvoice-activate/`
- **dsh-plugin-agent-way (agent-bus)** — `~/dsh-plugin-agent-bus/`
- **wargame-engine** — `~/dsh-collab/scripts/wargame-engine.py`
