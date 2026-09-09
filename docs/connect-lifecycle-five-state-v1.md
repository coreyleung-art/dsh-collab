# 连接生命周期 · 五态状态机 + 分层呈现 v1

> 作者: 明鉴 v2 · 2026-09-05 · 用户提出
> 洞察: 连接不是一条线到底 — 应分生命周期(候选→确认→通知→协作→并入), 已落地完成的从实验室移除、进正式关系图。
> 用户定案: 五态 + 完成后彻底从实验室移除(实验室=纯可能性视图)。

## 一、五态生命周期
| 状态 | 触发 | 呈现 | 数据 |
|------|------|------|------|
| P0 候选 | 引擎发现(孤岛×枢纽) | 实验室虚线(黄/绿) | candidates.json(排除已确认) |
| P1 已确认 confirmed | 五步门 approve | 实线紫(实验室内) | confirmed-links.json status=confirmed |
| P2 已通知 notified | 执行器发黑板两端 | 实线紫+徽标『沟通中』 | 同 status=notified(+ts通知) |
| P3 协作中 collab | 双方认领/落地 | 实线+徽标『落地中』 | 同 status=collab |
| P4 已并入 merged | 写入正式 relations 源 | 实验室移除 → 正式关系图出现 | relations + confirmed status=merged |

## 二、图层分离(用户核心要求)
- **🧪 实验室层**: 只呈现 P0(可能性候选虚线) + P1-P3(推进中的线带状态徽标) + 无 P4(完成后消失)
- **🗺 正式关系图**: 蓝图 relations(源数据)—— P4 merged 的真实落点
- 候选池(candidates)在引擎生成时**排除**已确认/推进中的连接(不重复建议)

## 三、状态推进
```
confirmed(五步门) → notified(execute工具发黑板) → collab(人工标/双方认领) → merged(写回relations)
```
- 状态字段: confirmed-links.json link.status
- API: /api/link-status?from&to&status=notified|collab|merged (更新状态)
- merged 动作: 把边写入黑板 data/blueprint/relations(正式源, 带 desc/type), 并从候选/推进移除

## 四、呈现
- 图: P1 紫实线; P2 加『📣沟通中』tag; P3 加『🤝落地中』tag; P4 在图外(正式关系)
- 实验室列表: P1-P3 显示状态徽标+可推进按钮; P4 不显示

## 五、验收
| # | 标准 |
|---|------|
| A1 | confirmed-links 每条带 status 字段 |
| A2 | 五步门 confirm → status=confirmed |
| A3 | execute 工具通知后 → status=notified |
| A4 | /api/link-status 更新 collab/merged |
| A5 | merged → 写 relations + 实验室消失 |
| A6 | 候选池排除 P1-P4 连接 |
