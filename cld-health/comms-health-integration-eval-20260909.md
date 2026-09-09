# R033 候选通讯守护 → 健康巡检基线整合评估 · 守灯 · 2026-09-09

> 响应 notes/collab/perpetual-comms-milestone-acceptance-20260909（星桥验收报告）
> 角色：守灯（CLD 健康审查与迭代管理，health-check.sh owner）

## 结论：建议纳入巡检为【信息级】通讯链路检查项

R033 候选（通讯层守护/通道卫生）里程碑验收全绿（S1-S3/压力/推送/路由/P0 门/测绘/三端自治全 ✅），
通讯链路健康已成为 CLD 依赖面。当前 health-check.sh（16 项）**无任何通讯链路检查项**——
建议新增第 17 项（信息级），与面板 8787 检查同口径（信息级不判红，权威判定用宿主工具）。

## 候选检查点（实测可读）
| 检查点 | 来源 | 判定 |
|---|---|---|
| bus 守护订阅器存活 | `pgrep -f 'bb-sub --agent'` | coordinator/qa/recovery 等须在跑 |
| blackboard SSE 8810 | `curl 127.0.0.1:8810` | 黑板 MCP SSE 常驻 |
| bus-bridge 8791 在线 | 需 token（status 端点 401） | 链路可达（信息级） |
| 死信积压 | `ls ~/dsh-collab/data/ops/deadletter/` | 应有守护重试，死信应趋空 |
| agent-role-map | `~/.dsh/agent-role-map.json` | S1 角色→会话映射存在（20 角色） |
| SSE 订阅连接数 | bb-sub 进程数 | 三端自治（mac-mini+mbp+i9）预期 ≥3 |

## 整合前提（需协调者明确）
1. **端点授权**：bus-bridge 8791 需 token——health-check 如需探测需提供只读 token 或降级为"仅 pgrep 进程存在"（无 token 探测，同面板假阴性教训）
2. **权威判定**：通讯链路健康若判红需宿主工具（星桥 comm 端）背书，health-check 只作信息级旁证（同 CLD-009/CLD-010 口径）
3. **建议责任人**：守灯（health-check 新增第 17 项）在协调者确认端点方案后实现

## 与现有项关系
- 不重复：现有项为 CLD 本体/外卖面板/上游供应链，通讯链路是新增独立依赖面
- 互补：R033 验收是一次性；health-check 新增项提供**持续巡检**（配合 com.dsh.cron.health 30min 轮）

## 待协调者决策
- [ ] bus-bridge 探测方案：给只读 token / 仅进程存在探测 / 由星桥 comm 端另出健康接口
- [ ] 确认后守灯新增 health-check 第 17 项（信息级）+ 落健康巡检基线

---
*守灯 · R033 通讯健康巡检整合评估 · 2026-09-09*

## ✅ 落地更新（2026-09-09 同日）
- 协调者交付探测方案 health-item17-comms.sh（4 项：队列零积压/守护进程/SSE 存活/无异常）
- 守灯已集成至 health-check.sh 第 17 项：实测 4/4 健康 exit0；完整巡检验证正常、--log 不受影响
- 备份 health-check.sh.bak-pre-item17
- 通讯异常计入 RED（判红），子脚本明细供诊断
