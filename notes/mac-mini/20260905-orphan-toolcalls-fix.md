# 孤儿 tool_calls 续跑卡死 · 根因与补丁（2026-09-05）

## 现象
mac-mini 智能体「明鉴 v2」(session-f38244df) 会话无法续跑，每轮报：
`An assistant message with 'tool_calls' must be followed by tool messages responding to each 'tool_call_id'. (insufficient tool messages following tool_calls message)` 400 INVALID_REQUEST

## 根因链（会话日志 seq 级还原）
1. 09-04 19:46 turn 436（重启全员唤醒后）：assistant 发 bash 工具调用 call_00_uBS2KodkNh5dzhlRASgD4341（tool/call seq=1264270 已落盘）
2. 工具执行崩溃：`Cannot read properties of undefined (reading 'prepare')` = `ctx.tools[TOOL_RUNTIME_SCHEDULER]` 未注册（重启竞态，tools 服务未就绪）
3. dsh-agent-loop `runGroup` 注释自认缺口：scheduler failure 不补 synthetic recovery results → **tool/result 永远没写**
4. 09-05 03:02 turn 437 续跑：重放历史得 assistant(tool_calls) 无配对 tool → API 拒 → 每次续跑必失败（孤儿永久留在 committed 区）

## 修复（非破坏，读取侧）
- 位置：`dsh-agent-loop/lib/index.js` step() 的 buildRequest 前
- 新增 `reconcileOrphanToolCalls(messages)`：扫描边界消息，凡 assistant 声明 tool-call 而后续无配对 tool-result 的（孤儿），在原处注入合成 error tool-result（"tool execution was interrupted..."）→ 发给 LLM 的历史满足 API 契约
- 只改发给模型的**消息视图**，不写会话日志、不改任何历史数据；健康历史零副作用
- 对所有会话生效 → 同类重启竞态不再永久卡死

## 文件与校验
| 项 | 值 |
|---|---|
| 补丁前 sha1 | 2b95f481441577c06871963895cd94b822259531 |
| 补丁后 sha1 | 5092b508a1e523605a9b80a2f2d2f7f5d4871287 |
| 原文件备份 | ~/dsh-collab/guard/backups/dsh-agent-loop.index.js.bak-orphan-fix-20260905-034022 |
| fixed 副本 | ~/dsh-collab/guard/backups/dsh-agent-loop.index.js.fixed-orphan-fix.js |
| 重放脚本 | ~/dsh-collab/guard/backups/replay-orphan-fix.sh（CLD 升级后执行） |

## 生效与验证
- 需重启 CLD（runtime 文件启动时加载）
- 重启后：向明鉴会话发消息/续跑，应正常出结果；观察 dsh 进程无 400 INVALID_REQUEST
- 若仍有 400：检查孤儿是否在**多条**历史（reconcile 只处理边界消息；届时再扩到全历史扫描）

## 经验
- 这是重启竞态（tools 服务未注册时唤醒 agent）暴露的官方缺口，与官方 #4416 讨论的「损坏/中断会话可用性」同族
- 可考虑后续向上游提 issue：scheduler failure 时也应 appendSkippedToolCall 式补结果（写侧兜底），而非仅读侧 reconcile

---
## 验证记录（2026-09-05 03:47 重启后）
- CLD 优雅重启（quit → open），新 dsh pid 38298，sha 5092b508 补丁在位
- 明鉴会话续跑成功：seq 从卡死点 1264270 推进至 1269814+，tool/call↔tool/result 正常成对，无 400
- 会话大小 20.66MB→20.76MB（活跃工作），CLD 稳定 >2min
- 结论：✅ 修复生效，会话恢复正常
