# wargame · 商业沙盘模拟器 — R006 十项合规

> 明鉴 · 2026-09-09 · v1.0.0 · 纯 stdlib Python CLI
> 触发: 用户「把 20 条路线沙盘推演过程工具化插件化」——20 路线力导向图+打分+对抗+收敛 全流程固化
> 位置: ~/dsh-collab/scripts/wargame.py

## 十项达标矩阵

| # | R006 项 | 达标 | 实现 |
|---|---------|------|------|
| ① | CLI 形态 | ✅ | argparse + 7 子命令(init/generate/score/adversary/converge/graph/report) + --run 一键 |
| ② | TCC 检测 | ✅ | --selfcheck (域目录可达/纯stdlib/日志) |
| ③ | CLD 自适应 | ✅ | 纯 stdlib 零第三方依赖 |
| ④ | dsh 版本自适应 | ✅ | 数据路径独立(data/wargame/<dom>) |
| ⑤ | 文档化 | ✅ | 本文档 + docstring 工作流说明 |
| ⑥ | 版本管理 | ✅ | --tool-version v1.0.0 |
| ⑦ | 统一日志 | ✅ | ~/dsh-collab/logs/wargame.log |
| ⑧ | 自动落链 | ✅ | asset-map 登记 + 域数据 data/wargame/<dom>/ |
| ⑨ | CLI 治理 | ✅ | --help/--domain/--run 语义清晰 |
| ⑩ | Lean4 约束门 | ✅ | --lean4-check PASS (写仅 save_json→域目录) |

## 工作流(与"20路线沙盘"手工过程一一对应)

```
① init      初始化域(写目标到 axes.json)
② generate  轴组合穷举路线(或手写 routes.json 语义化路线)
③ score     多维打分(默认5维: 现金流/资本需求/控盘/窗口/护城河; 可配置权重与规则)
④ adversary 对抗检查点修正(checks.json, 命中每条-3)
⑤ converge  簇收敛(clusters.json 显式定义 → result.json)
⑥ graph     d3 力导向图输出(节点着色/分数/边=共享维度)
⑦ report    沙盘报告 md
⑧ --run     一键全流程
```

## 域数据(flowernet 首个应用)
```
data/wargame/flowernet/
  axes.json     目标+6轴定义(引擎/资本/护城河/平台/节奏/变现)
  routes.json   20 条路线(维组合+desc)
  score.json    打分规则(by_dim_value: 资本/节奏/护城河值→分)
  checks.json   对抗检查点(每路线1-2条, 源自 redteam 打穿点)
  clusters.json 收敛簇(簇1现金流/簇2护城河/簇3资本/北极星)
  result.json   收敛结果
  report.md     沙盘报告
```

## 可视化入口
- http://127.0.0.1:8812/route-wargame  (手工版 20 路线)
- http://127.0.0.1:8812/wargame         (wargame.py 产物, 通用域)
- 新域: python3 wargame.py --domain <X> --objective "..." init → 编辑 axes → run

## 方法来源
- LucidWargames 思路(竞对响应+量化风险) — research/business-strategy-agent-and-wargaming-2026.md
- redteam 对抗(flowernet-capital-roadmap-redteam-v1 打穿点)
- 本会话 20 路线实战(flowernet-20routes-wargame-v1.md)

---
*wargame R006 · 明鉴 · 2026-09-09*
