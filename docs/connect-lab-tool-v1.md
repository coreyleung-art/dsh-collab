# 连接实验室 · 工具化(bb-connect-lab.py) v1.1(向量语义)

> 作者: 明鉴 v2 · 2026-09-05 · Φ8 工具化 · R006 九标准
> 从 gallery 内嵌 /api/connect-lab 抽为独立 CLI(数据源直接 agent-bus, 不依赖服务)

## 一、R006 合规
| 标准 | 实现 |
|------|------|
| 插件形态 | 独立 bb-connect-lab.py |
| TCC | --selfcheck(扫 5 候选验证) |
| CLD 自适应 | 纯文件读 agent-bus.json, 无服务依赖 |
| 版本 | --tool-version v1.0.0 |
| 文档 | 本文档 |
| 版本管理 | 纳入 VERSION-MANIFEST(随发布) |
| 统一日志 | --json 输出 |
| 自动落链 | --out 落 data/connect-lab/candidates.json |
| CLI 治理 | --scan/--islands/--json/--out/--selfcheck |

## 二、算法(与 gallery /api/connect-lab 一致)
- 孤岛 = 无共享私有资源边的活跃主会话(session- 前缀, 排除已交接/前任)
- 穷举: 孤岛 × 全节点(排除自反)
- 5 特征打分: 同域 0.28 + 语义 0.36 + 资源共享 0.20 + 互补 0.15 + 设备 0.04
- 分档: ≥0.5 高 / ≥0.38 中 / 弱
- reason: 人读的"为什么可能连"

## 三、与 gallery 的关系
| 用途 | 用哪个 |
|------|--------|
| 管理器内交互(图/虚线/hover/点击) | /api/connect-lab(gallery) |
| CLI 批扫/自动化/CI | bb-connect-lab.py(独立) |
| 候选落盘(确认池) | bb-connect-lab.py --out → data/connect-lab/candidates.json |

## 四、已知差异
- gallery 版孤岛 23 vs CLI 版 26: gallery 从运行态 get_agents(有 updatedAt 活跃性差异), CLI 直读全部 session 档案
- 分档计数略异: 语义 token 化细节 — 后续对齐(同一 _text_sim 已复刻)

## 五、下一步(待办)
- 确认闭环: candidates.json → 人工确认 → 回写 agent-network 关系
- gallery 内嵌改为调本工具? (保持双轨: 交互走 API, 批扫走 CLI)
- ✅ v1.1: Ollama bge-m3 1024 维向量语义(batch 预计算 3s), Jaccard 兜底
