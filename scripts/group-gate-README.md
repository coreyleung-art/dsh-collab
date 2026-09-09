# group-gate — 群聊治理门(R006 十项)

> 属主: HR 司库 · v1.0.0 · 2026-09-07 · 规范: docs/group-chat-governance-v1.md

## 定位
群聊(群发广播线程)治理: 开群前决策树评估(check)+存量群健康审计(audit)。
实证: 群聊上下文放大 20.8x(消息×参与者), 40+ 人大群是资源黑洞(明鉴死锁教训同源)。

## 子命令
| 命令 | 作用 |
|---|---|
| check --desc <场景> [--participants N] [--mutual yes/no] [--duration once/temp/long] | 决策树→推荐通道(点对点/会话/G1-G4) |
| classify --desc <场景> | 场景分类(G1 广播/G2 协作/G3 评审/G4 状态) |
| audit [--json] | 存量群健康扫描(大群/放大率/建议)→ data/groups/ |
| lean4-check | R006#10 自检(45 人非制度群应被警告) |
| selfcheck / version / cld-check / version-check | R006 辅助 |

## 决策树逻辑(核心)
1. B/C 不需互见 → ★点对点分别通知(最省, 线性成本)
2. 需互见+长期 → 新开会话
3. 需互见+临时 ≤8人 → G3 评审群(48h 散)
4. ≤5人任务 → G2 协作群(完成归档)
5. 制度/重启/事件 → G1 广播(月≤5)
6. >17人非制度 → 警告(C2 用途闸+C5 放大)

## R006 对照
①插件 P2 ②selfcheck ✅ ③cld-check ✅ ④version-check ✅ ⑤README ✅ ⑥--version ✅ ⑦~/.dsh/group-gate.log ✅ ⑧audit→data/groups/ ✅ ⑨argparse ✅ ⑩lean4-check ✅
