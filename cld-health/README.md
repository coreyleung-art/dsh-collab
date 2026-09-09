# CLD 系统健康审查与迭代管理（cld-health）

> 负责人：session-9910d4b2（Agent Bus 能力档案已登记）
> 职责：CLD 宿主健康基线/巡检、迭代需求收集与排期、开发任务管理（指派/跟踪/验收闭环）

## 目录文件

| 文件 | 说明 |
|------|------|
| `cld-health-baseline-YYYYMMDD.md` | 健康基线报告（每次巡检/重大事件后更新） |
| `cld-iteration-backlog.md` | 迭代需求清单（缺陷/增强/新特性，P0-P3，状态机管理） |
| `health-check.sh` | 健康巡检脚本 v3（十项检查 + `--log` 趋势记录到 health-log.tsv） |
| `health-log.tsv` | 巡检时间序列（趋势/基线对比） |
| `post-restart-check.md` | CLD 重启后 5 分钟标准复核清单 |
| `README.md` | 本说明 |

## 管理流程

1. **健康巡检**：随崩溃/异常/用户请求触发；必要时定期执行（磁盘/负载/日志错误/端口/launchd/profile 完整性/告警链路）。
2. **需求收集**：任何会话或用户提出的 CLD 改进/缺陷 → 记入 backlog，标注来源、日期、优先级。
3. **优先级**：P0=阻断（宿主不可用/数据丢失）→ P1=高（功能异常/链路停摆）→ P2=中（隐患/脆弱性）→ P3=低（增强/观察项）。
4. **指派**：按 Agent Bus 能力档案匹配负责人，经 agent_send 指派；涉及共享资源改动前走红绿灯协议。
5. **验收**：修复后验证闭环，更新 backlog 状态，必要时更新基线报告。
6. **红绿灯**：本目录内文件写入需先 agent_light + agent_lock(file:/Users/coreyleung/dsh-collab/cld-health)。

## 当前基线摘要

- 最近一次崩溃：2026-08-16 23:49:3x（**根因已查明**：session-28ca132e pkill -9 强杀 + 裁剪 package.json，见基线 §3.1），23:49:40 launchd 自动重启，GUI 端口 63866 → 50120
- 重启后日志零 Error，18 bundles（磁盘）/ 运行态仍为 5-bundle（待下次重启生效，见 post-restart-check.md）
- 告警链路：正常（CLD-001 误报关闭；面板 lastTick 新鲜度由 health-check 第 10 项监控）
- 巡检工具：health-check.sh v3 全绿（含负载阈值告警 12）；趋势见 health-log.tsv
- 详细见 `cld-health-baseline-20260816.md`
