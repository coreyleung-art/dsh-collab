# session-rebirth — 旧会话死锁重建工具（R006 十项）

> 属主: HR 司库 (session-2a15e6b1) · v1.0.0 · 2026-09-06 · 案例来源: 明鉴 v2→v3 死锁重建

## 定位
会话上下文死锁（CONTEXT_WINDOW_EXCEEDED + 宿主压缩门控 "summary is not smaller than the shadowed content" 连续失败）时，
一键完成 **诊断 → 冷备份 → 记忆提取 → 续接提示词组装** 全流程，让用户/协调者只需开新会话粘贴提示词即可接力。

## 死锁背景知识（为什么需要本工具）
宿主压缩机制 (dsh-compaction-basic) 要求「摘要必须比被遮蔽内容更小」；
当会话上下文逼近上限、可安全遮蔽区间缩小时（如 1870 tokens），LLM 摘要含框架开销天然更大 → 门控反复拒绝 → 死循环。
明鉴 v2 实例: 79.3 万 tokens, 连续 3-4 次失败后任何请求都无法发出。

## 子命令
| 命令 | 作用 |
|---|---|
| diagnose --session <id> | 诊断健康度: 事件数/压缩成功失败/门控死锁判定 (GREEN/YELLOW/RED) |
| backup --session <id> [--name] | 冷备份到 ~/dsh-collab/archives/<name>-<date>/ |
| extract --session <id> [--name] | 提取记忆继承包 (compaction 摘要全文+最近用户指令) 到 docs/ |
| compose --session <id> --role <名> [--abilities A;B] [--resources R1;R2] | 组装续接提示词骨架到 docs/ |
| full --session <id> --role <名> | 一键 backup + extract + compose |
| selfcheck / version / cld-check / version-check | R006 TCC/CLD/版本检查 |
| watchdog | **巡检全部会话**检死锁候选(门控拒>=2→RED) |

## 使用流程 (full 后人工 3 步)
1. `python3 session-rebirth.py full --session session-xxx --name 角色别名`
2. 人工: 打开 docs/<name>-resume-prompt-*.md 按需补充角色专属职责/主线任务 → 给用户开新会话粘贴
3. 新会话就任 (agent_profile 登记) → 通知司库更新 registry (明鉴行换新 session id) → 广播全员切换

## R006 对照
①插件 P2 排期 ②selfcheck ✅ ③cld-check ✅ ④version-check ✅(纯CLI无依赖) ⑤本文档 ✅
⑥--version ✅ ⑦~/.dsh/session-rebirth.log ✅ ⑧产出路径打印(落链指引) ✅ ⑨argparse ✅ ⑩路径安全门(备份越权拒) ✅

## 零 LLM
纯规则 + JSONL 解析。记忆提取复用会话内宿主已生成的 compaction 摘要，不额外耗 token。

## 插件化（dsh-plugin-hr 集成）
session-rebirth.py 已注册进 dsh-plugin-hr 的 /hr/api/run-script（白名单+body.args 透传），
配套 resource-manager preset 会话可经插件调用：diagnose/watchdog/full。

## 死锁事件自动化闭环
launchd/定时调 `session-rebirth.py watchdog` → 检出 RED 候选 → HR 收到通知 →
`full --session <id>` 一键备份+记忆提取+提示词 → 用户开新会话 → 更新 registry + 广播切换。
