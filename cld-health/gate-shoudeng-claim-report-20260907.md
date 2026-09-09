# 守灯域（cld-backlog/restart）纸面门 15 条 · 三态核查报告

> 守灯（CLD 健康审查与迭代管理）· 2026-09-07 · 纸面门轮 2 分派（守灯 15：cld-backlog/restart）· gate-auditor 识别
> 结论：15 条分派中 **误报 12 / annotate 2 / scaffold 1（观察项）** —— 域内大部分为叙述/数据/文档行，非现行门声明

---

## 〇、候选来源与判定口径

候选来自 `~/dsh-collab/cld-health/` 的 `cld-iteration-backlog.md`（cld-backlog 域）+ `post-restart-*.md` / `CLD-002-*.md` / `health-check.sh` / `r006-v2-selfcheck`（restart/看门狗域）。
gate-auditor 对叙述行/数据行/注释行会误标 paper（它扫的是"门措辞"，非语义）。三态口径：
- **annotate** = 声明的门已有对应工具/流程实现（缺文档标注）
- **scaffold** = 确为现行门声明且无工具实现，需新建
- **误报登记** = 叙述/历史/数据/文档行，非门声明（登记即可，不加固）

## 一、三态分类（按文件）

### A. annotate（2 条）— 门声明已有工具，补文档标注
| 条目 | 声明 | 已有实现 | 动作 |
|---|---|---|---|
| `cld-iteration-backlog.md:66/68` CLD-008 | 运维高危操作（pkill/kill/bootout/写 profile）需护栏 | ✅ `agent_light`/`agent_lock` 红绿灯（baseline:37 协调者已背书）+ 宿主 guard 工具族（guard_check_writable/guard_backup/guard_compliance） | backlog 标注"护栏=红绿灯+guard 工具族" |
| `cld-iteration-backlog.md:39` CLD-008 遗留 | profile 配置纳入自动备份 | ✅ `guard_backup`（P2 备份工具，宿主工具面） | 同上标注 |

### B. scaffold（1 条 · 观察项）— 现行缺口但属他域/待装
| 条目 | 声明 | 现状 | 动作 |
|---|---|---|---|
| `CLD-002-watchdog.md:24` node --check | 看门狗安装验证（CLD-002） | 安装实施在 3d490920 域 + 用户终端命令 + codesign 重签（A3/A4 已批），守灯侧为验收方 | 不新建；由实施方完成后守灯按验收标准关闭 CLD-002 |

### C. 误报登记（12 条）— 叙述/数据/文档/已实现行
| 条目 | 类型 | 登记理由 |
|---|---|---|
| `cld-iteration-backlog.md:13/17` CLD-009 | 经验教训/需求描述 | 已实现于 health-check.sh 面板 lastTick 检查（#10 面板项）+ CLD-009 记录 |
| `cld-iteration-backlog.md:141` sharp CVE | 供应链记录 | 供应链域（0e84e65c），非门声明 |
| `post-restart-20260904.md:14/15` | 巡检数据（swap/Data 卷） | 数据记录，非门；红线阈值已实现在 health-check.sh |
| `README.md:12` | 文档表格 | 文档行 |
| `r006-v2-selfcheck-20260906.md:6/9/12/13/30` | 自查文档 | 描述已实现的结构门（health-check.sh lean4 门），文档行 |
| `CLD-002-wecom-alert-spec.md:33` | 建议行 | 模板建议，非门 |
| `CLD-002-watchdog.md:24`（部分重叠见上）| 验证记录 | 见 scaffold 观察项 |
| `cld-health-baseline-20260816.md:71` CLD-008 表行 | backlog 行 | 同 annotate CLD-008 |
| `cld-rss-monitor.sh:5` | 注释行 | 用法注释 |
| `health-check.sh` 注释行（8/19/21/23/26/36/86/212/233 等） | 代码注释 | 描述**已实现**的 push 结构门（R006 v2 #10，本域 09-06 补）——注释行被误扫为 paper |

## 二、建议动作

1. **登记误报为主**：12/15 条为叙述/数据/文档行或已实现行——不为历史/文档造门（同明鉴 flowernet 结论口径）
2. **annotate 2 条**：CLD-008 相关在 backlog 标注"护栏 = agent_light/lock 红绿灯 + guard 工具族（guard_check_writable/guard_backup/guard_compliance）"
3. **scaffold 观察 1 条**：CLD-002 看门狗安装属 3d490920 实施域（已在推进，非守灯新建）
4. **审计器建议**：对 `cld-health/*.md` 叙述行/数据行加排除或降权——防轮 3 重扫（同 flowernet 对旧规划文档的处理）

## 三、回报（登记用）
- 15 条分派：误报 12 / annotate 2 / scaffold 0（另有 CLD-002 观察 1 条属他域在装）
- 本域确无现行门缺工具；结构性已由 health-check.sh（含 R006 v2 lean4 门）+ guard 工具族 + 红绿灯覆盖

---
*核查报告 · 守灯 · 2026-09-07 · cld-backlog/restart 15 条三态*
