# MBP 内存治理资料 · 本地镜像索引（2026-09-06 拉取）

> 来源：MBP 100.112.111.120 ~/dsh-collab（SSH 只读打包拉回）
> 拉取：老登 aa528267 · 2026-09-06 · 原始 tar: research/mbp-memory-gov.tar.gz (1.57MB, 36文件)
> 用途：mac-mini 侧内存治理/CLD OOM/进程优化研究参考 · 已向量化可检索

## 内容地图

| 本地路径 | 原 MBP 路径 | 内容 | 价值 |
|---|---|---|---|
| doc/memory/00-总览.md | ~/dsh-collab/doc/memory/ | MBP 全量考古总览（业务/基础设施/资产大盘） | 节点画像 |
| doc/memory/01-踩坑.md | 同上 | 考古踩坑 + 敏感清单 + mbp-bus 实战沉淀 | ⭐ 运维教训 |
| doc/memory/02-时间轴.md | 同上 | 考古时间轴 | 背景 |
| doc/memory/03-考古报告.md | 同上 | 考古报告 | 背景 |
| doc/memory/值守交接单.md | 同上 | MBP 值守机制（心跳/事件桥/恢复指引） | 运维 |
| archaeology-mbp/历史问题考古报告-20260905.md | ~/dsh-collab/archaeology-mbp/ | **CLD/DSH 历史问题考古**：9次崩溃时间线 + M1-M6 根因模式 + P0-P2 治理 | ⭐⭐⭐ 内存治理主文档 |
| poc/memory-crash-lab/内存崩溃实验室-复现与治理评估报告-20260905.md | ~/dsh-collab/poc/memory-crash-lab/ | **OOM 复现实验**：6会话276MB 512堆 SIGABRT；tail 治理 23x 内存↓/152x 速度↑ | ⭐⭐⭐ 核心证据 |
| poc/memory-crash-lab/全员唤醒实验报告-20260905.md | 同上 | 全员唤醒内存观察实验 | ⭐ 相关 |
| poc/memory-crash-lab/实验计划-全员唤醒观察-20260905.md | 同上 | 实验设计 | 参考 |
| poc/memory-crash-lab/runner/ | 同上 | oom-sim.js / run-lab.js / assertions.js 可复用实验代码 | ⭐ 工具 |
| poc/memory-crash-lab/results/*.lab.json | 同上 | 结构化实验结果 | 数据 |
| rust-tools/dsh-tools-v131/resource-optimization-efficiency-20260827.md | ~/dsh-collab/rust-tools/ | **资源优化评估**：Rust化 152MB→31MB (80%↓)、token 96%↓ | ⭐⭐ 进程瘦身 |
| mtm-from-mac/ | ~/dsh-collab/mtm-from-mac/ | mtm 8787 架构（Chrome多实例隔离/CDP/稳定性六件套） | ⭐ 架构复用 |
| archaeology-mbp/L1-docs/node-own-history.md | ~/dsh-collab/archaeology-mbp/ | 节点自身史 | 背景 |
| archaeology-mbp/vector-kb/mbp-memory-kb.json | ~/dsh-collab/archaeology-mbp/ | bge-m3 向量库 (3.3MB) | 数据 |
| devices/mbp-memory-vectorize.py | ~/dsh-collab/devices/ | MBP 内存向量化工具 | 工具 |

## 核心结论速览（内存治理）

1. **CLD OOM 根因**：多会话全量物化超 V8 堆顶（6会话276MB → 512MB顶 SIGABRT），单会话137MB不崩
2. **治理结构性有效**：帧索引尾部窗口（只解尾部200帧）→ 峰值 768MB→33.9MB（23x）、耗时 23.8s→156ms（152x）
3. **行为治理先行**：会话≤5 + auto-index 卸载 + doctor 错峰 + 日志轮转 = P0/P1 已落地，P1 后 0 崩溃
4. **6 大根因模式**：M1版本遮蔽 / M2全量物化OOM / M3重启竞态 / M4插件协议 / M5凭旧认知 / M6不验证
5. **进程瘦身范本**：Rust 化常驻服务 151.8→31MB（80%↓），事件驱动零轮询

## 待办建议

- [ ] 对照 mtm(8787) Chrome 多实例内存占用，评估 tail/惰性加载方案
- [ ] 拉取 MBP repair-reports 原始 JSON（37+7 份）补案例库
- [ ] mac-mini 侧"同时打开会话数"监控纳入运维 SOP
