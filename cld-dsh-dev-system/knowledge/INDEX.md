# CLD/DSH 知识库 · 总索引（Knowledge Map）

> 建立：2026-09-04 · 目标：主动学全 CLD/DSH 各部件，不等问题发生。
> 原则：学一个→建卡(parts/)→沉淀标准/工具→双向关联(工具箱/路由表/规范)。
> 机器可读：`registry.json`；查询工具：`guard-knowledge`。

## 域 → 部件 → 卡片/文档/关联

### DSH 核心（runtime @deepseek-ai）
| 部件 | 卡 | 官方文档 | 工具箱 | 路由 |
|---|---|---|---|---|
| session-persistence | ✅ parts/session-persistence.md | subsystems/persistence.md, session.md | T1/T2 | OP-session-data |
| workspace | ✅ parts/workspace.md | subsystems/workspace.md | T1 | OP-restart |
| plugin-loader(树/层) | 学习中 | architecture.md, cordis-api/ | T4/T5/T7 | OP-pnpm/plugin |
| dsh-tools tool 定义/执行 | ✅(实证卡待补) | subsystems/tools.md, core.md | T4 | OP-add-plugin-host |
| scope 作用域 | 学习中 | subsystems/scope.md | T1 | — |
| compaction | todo | subsystems/compaction.md | T2 | — |
| profile-config | ✅(实证) | architecture.md profiles 段 | T5/T7 | OP-pnpm/config |
| storage-domain | todo | subsystems/storage.md | — | — |

### UI / 前端（web profile）
| client-modules(模块加载) | ✅ | client-modules.md | T4 | OP-add-plugin-client |
| slots(插槽/shadow) | ✅ | slots.md | T6 | OP-add-plugin-client |
| web-server | todo | web-server.md, web.md | T5 | — |
| web-client(会话列表UI) | todo | web-client.md | T1 | — |
| session-query | todo | session-query.md | T1 | — |
| session-reference(fileRefs) | todo(关联ui-reference遗留) | session-reference.md | T5 | OP-disable-plugin |

### CLD 壳（app.asar main.js，Electron）
| cld-shell-spawn | ✅ | architecture/CLD-DSH-完整架构梳理 + main.js | T5/T8 | OP-asar/restart |
| cld-shell-watchdog(S1/S5) | ✅ | workflows/CLD壳缺陷修复-P0立项.md | T2/T8 | OP-asar |
| electron-packaging(asar/fuse/签名) | ✅ | electron-docs tutorial | T5 | OP-asar |
| electron-crashreporter | ✅ | crash-reporter.md | T8 | — |

### 治理面（自研）
| dsh-plugin-guard(P0-P8/门锁/监控/路由) | ✅ | guard/tools/* + rules/* | 全部 | — |

### 待学清单（P1/P2，来自 subsystems 47 件 + registry）
agent-core / agent-team / approval / sandbox / filesystem / shell+subprocess+terminal /
jobs+schedule / llm-streaming / system-prompt / session-projection / session-title /
session-telemetry / conversation / goal / plan / skills / todo / token-meter /
user-questions / extensions / credentials / settings / commands / feedback / invariants /
lsp / subagent / webhook / code-runtime / typert / spill / compaction / session-query …

## 双向关联约定
- **新事故** → 工具箱 T# + 路由表 OP → **反向更新对应部件卡**（known坑/标准）→ registry status/updated。
- **学完部件** → 卡毕业 → 若可自动化 → 建工具（如 P6 来自 session-persistence 卡）→ 记 parts/*.md §9。
- **官方更新** → doc-sync 变更报告 → 命中部件卡 → 标注"官方已变，需复审"。

## 完成度
- learned: 39 部件（全景完成） · learning: 0 · todo: 0 —— ✅ P0/P1/P2 全部毕业 (2026-09-05)
- 更新方式：`guard-knowledge`（登记/进度/校验）
