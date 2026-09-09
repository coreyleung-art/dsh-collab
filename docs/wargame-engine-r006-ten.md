# wargame-engine · 商业沙盘模拟器独立引擎 — R006 十项合规

> 明鉴 · 2026-09-09 · v1.0.0 · 独立可操作 APP(API+GUI, :8813)
> 铁律: 模拟 vs 现实【双向隔离】——现实(人物/蓝图)只读引用, 模拟数据仅写 wargame 域
> 位置: ~/dsh-collab/scripts/wargame-engine.py (引擎) + wargame.py (CLI 同源)

## 十项达标矩阵

| # | R006 项 | 达标 | 实现 |
|---|---------|------|------|
| ① | CLI 形态 | ✅ | --port/--host/--selfcheck/--lean4-check/--tool-version |
| ② | TCC 检测 | ✅ | --selfcheck (模拟域/现实只读清单/反向污染门) |
| ③ | CLD 自适应 | ✅ | 纯 stdlib HTTP 服务 |
| ④ | dsh 版本自适应 | ✅ | 不依赖 dsh API |
| ⑤ | 文档化 | ✅ | 本文档 + docstring 设计铁律 |
| ⑥ | 版本管理 | ✅ | --tool-version v1.0.0 |
| ⑦ | 统一日志 | ✅ | logs/wargame-engine.log (轮次/写操作审计) |
| ⑧ | 自动落链 | ✅ | asset-map 登记 + 模拟域 data/wargame/<dom>/ |
| ⑨ | CLI 治理 | ✅ | argparse 规范 |
| ⑩ | Lean4 约束门 | ✅ | 反向污染防火墙: 写必经 _assert_sim_path, 现实路径=拒绝 |

## 反向污染防火墙(核心, 用户指定)

```
现实数据(只读白名单):           模拟数据(唯一可写):
  meeting-identity-graph.json      data/wargame/<domain>/ (simulation/routes/axes…)
  data/blueprint/**                引擎任何写操作经 _assert_sim_path() 强制落此域
  data/meeting-notes/**            越界写(现实路径) → PermissionError 拦截
  relationships.json
  SystemGraph :8798 (API 只读)
```

实测: 写 meeting-identity-graph.json → 🚫 拦截; 写 wargame 域 → ✅ 放行

## API

| 端点 | 类型 | 功能 |
|---|---|---|
| / | GET | 沙盘 GUI(人物/蓝图/推演三栏) |
| /api/health | GET | 健康+隔离边界 |
| /api/context/people | GET | 现实人物(REG+identity-graph 合并, 只读) |
| /api/context/orgs | GET | 现实组织(只读) |
| /api/context/blueprints | GET | 现实蓝图(SystemGraph 8798, 只读) |
| /api/context/relations | GET | 人物关系边(Network, 只读) |
| /api/sim/status | GET | 模拟状态 |
| /api/sim/history | GET | 推演历史 |
| /api/sim/round | POST | 追加对抗(正方/反方/中立方→定稿) |

## 对抗推演协议(三立场)
- 正方: 推进最强论证 → 反方: 最尖锐攻击(red team) → 中立方: 独立裁决
- 每轮输出: 胜负判定(逐条) + 修正后路线 + 行动项(行动: 前缀,P1-P4 提取) + 下一步议题 + 残余风险
- 记录: simulation.json append-only; CLI(wargame.py simulate)与引擎共享同源

## 验证命令
```bash
python3 ~/dsh-collab/scripts/wargame-engine.py --lean4-check   # 反向污染门
python3 ~/dsh-collab/scripts/wargame.py --domain flowernet simview  # 历史
curl http://127.0.0.1:8813/api/sim/history
```

---
*wargame-engine R006 · 明鉴 · 2026-09-09*
