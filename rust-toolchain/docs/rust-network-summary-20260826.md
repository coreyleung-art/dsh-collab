# Rust 分布式节点网络 · 全链路落地总结（2026-08-26）

> 沉淀：mac-mini 中枢 · 2026-08-26 · 覆盖 2026-08-25 晚至 08-26 凌晨全部 Rust 化工作
> 定位：从「Python 三件套」到「全 Rust 单二进制网络」的完整升级记录 + 操作手册

---

## 一、一句话总结

**把分布式智能体网络的通讯层从「Python 4 进程」升级为「Rust 2 二进制 + 全 Rust 节点桥」，协议 v1.0 通道一字不改（不砸对讲机），全链路压测稳定，并补上「节点侧双向对话」的最后一块拼图。**

## 二、核心成果（6 项）

### 1. Rust 工具链工程化三件套
```
~/dsh-collab/rust-toolchain/
├── Makefile          # make test/build/release/status/bump
├── manifest.json     # 三项目版本清单（Cargo.toml 唯一事实源）
├── scripts/build.sh  # 流水线：test(38) → build(3×3=9产物) → release(归档+SHA256SUMS)
├── scripts/bump.sh   # 版本递增（patch/minor/major）+ manifest 同步
├── templates/logger.rs  # 统一 JSON 日志模板（双写+5MB轮转）
└── docs/logging-spec-v1.0.md
```

### 2. 黑板/基因库/节点桥全 Rust 化（Python 4 → Rust 2）
| 服务 | Python 原版 | Rust 版 | 产物 |
|---|---|---|---|
| 黑板 + 事件桥 | blackboard-server.py + blackboard-events.py | rust-blackboard（单进程含 SSE）| Win 549K/Linux 642K/macOS 493K |
| 基因库 AI 网盘 | genebank-server.py + http.server 8793 | rust-genebank | Win 468K/Linux 556K/macOS 427K |
| 节点桥 | executor+bb+guard 三件套 | node-bridge | Win 674K/Linux 752K/macOS 591K |

### 3. node-bridge v1.0.7（双向对话打通）
- **outbox 机制**（v1.0.6）：节点会话写 `~/.dsh/outbox/<topic>.json` = 发消息给中枢
- **to 字段跨节点**（v1.0.7）：写 outbox 带 `to:目标节点` → 点对点对话（MBP⇄i9）
- **inbox 落盘**（v1.0.7）：node-bridge 读全部消息 → 落盘 `~/.dsh/inbox/<topic>.json` 供会话读
- **五线程架构**：heartbeat 60s / queue 2s / worker 即时 / notes 5s / outbox 2s

### 4. 通道稳定性评估（🟢 稳定）
- 黑板压测：20/50/100 并发 = 2094/1813/1867 ops/s，0 错误
- 跨节点压测：MBP→i9 20 条全送达（5/5 抽样 + i9 inbox 落盘确认），0 丢失
- 心跳全程稳定（Rust v1.0.7）

### 5. 生产切换 + 守护
- launchd KeepAlive 守护（黑板/基因库/MBP node-bridge），崩溃自拉起实测（kill -9 → 自动拉起）
- 数据无缝迁移：9184 键/22383 基因/seq 无回退

### 6. 测试三层（抓到 3 个真实 bug）
- 单测 38+ 个（HLC 时钟/镜像/校验/outbox）
- 并发压测（3106→1867 ops/s）
- 智能体级测试（真实子代理全链路）
- **抓到 bug**：退订死锁（单测）、SSE HTTP/0.9 裸流（智能体测试）、outbox current_dir 路径（部署实测）

## 三、分布式节点网络拓扑（最终）

```
mac-mini 中枢（Rust 黑板 :8792 + SSE :8803 + 基因库 :8801，launchd 守护）
  ├── MBP → node-bridge v1.0.7（macOS，launchd 自启+崩溃拉起）
  └── i9  → node-bridge v1.0.7（Windows，心跳在线，自启待补）
协议 v1.0：heartbeat 60s / tasks queue / result / notes / outbox / inbox
```

## 四、对话通道全景

| 方向 | 方式 | 状态 |
|---|---|---|
| 中枢→节点 | 写 `notes/<node>/coordinator-*` | ✅ |
| 节点→中枢 | 写 outbox（无 to）| ✅ |
| 节点⇄节点 | 写 outbox（to:目标）→ 对方 inbox | ✅ v1.0.7 |

## 五、遗留（诚实标注）

1. **i9 开机自启**：schtasks 需管理员权限（executor 被拒）——需 i9 侧管理员执行一次（指引在黑板 notes/i9/coordinator-autostart-guide）
2. **Python 残留清理**：MBP search_api/8890 业务服务需确认；i9 python.exe ×3 待会话确认；旧 agent 脚本待删
3. **i9→MBP 方向压测**：待 i9 会话激活后补充
4. **notes 列刷屏**：genebank 8000+ 键挤掉 limit 查询——统计用单键 GET
5. **内存**：黑板 154MB（notes 8667 键全文驻留主导）——后续 notes 归档磁盘优化

## 六、关键路径速查

| 项 | 路径 |
|---|---|
| node-bridge 源码 | ~/dsh-collab/rust-bridge/ |
| 黑板源码 | ~/dsh-collab/rust-blackboard/ |
| 基因库源码 | ~/dsh-collab/rust-genebank/ |
| 工具链 | ~/dsh-collab/rust-toolchain/ |
| 稳定性评估 | ~/dsh-collab/devices/通道稳定性评估-20260826.md |
| 节点发消息指引 | ~/dsh-collab/devices/节点会话发消息-操作指引-v1.0.6.md |
| 协议 v1.0 | ~/dsh-collab/devices/node-channel-file-protocol-v1.0.md |

## 七、变更记录
- 2026-08-26：全链路 Rust 化总结。含工具链/黑板基因库/节点桥/双向对话/稳定性评估/生产切换。
- 2026-08-27：**node-bridge v1.2.0（LLM 执行器三因子门禁版）**——「设备自主互通无需监督」最后拼图。
  - 三因子门禁：模型强制 flash / 日配额 50 / 单会话互斥 + 退避重试 + 死信 + ledger 审计 + 触发收紧（仅 llm:true）
  - 关键 bug 修复（E2E 实测发现）：黑板 GET /notes/<node>/ 返回全量 8777 条不按 node 过滤 → notes_loop 只处理本节点+collab，防 LLM 执行器误处理他节点历史消息（8/26 事故隐藏机制）
  - 防循环双保险：已处理 LLM 消息不再重写 inbox
  - E2E 实测通过：inbox llm:true → 15s 自动处理 → ledger 记账 → 回复路由回发件人
  - 产物：dist/node-bridge-{macos-arm64,win-x64,linux-x64}-v1.2.0 · 24 tests
