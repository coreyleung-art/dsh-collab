# 跨设备黑板服务器 · 设计方案 v1.0

> 设计：2026-08-21 · HR · 用户推动（「跨设备的黑板服务器逻辑可以更新起来」）· CAHAC §6 正式实现 + 跨设备化
> **部署形态决策（2026-08-22 用户确认）**：现阶段=**Tailscale 内网共享账本 + 命名空间隔离**（nodes/<节点>/、data/<域>/，权限=信任内部）——完全够用，不引入多租户复杂度；**多租户升级路径（公网投放门店/员工时启用）**：① 命名空间加租户层 data/<门店>/* ② 云网关 ABAC 按角色（论文 2605.18414 已入库）③ 企微身份认证 ④ 员工操作 J45 自动升级审批 ⑤ 审计加租户维度
> 定位：本地文件黑板（registry/台账）→ **跨设备黑板服务器**（HTTP API + 订阅 + 审计），i9/mac-mini/MBP 统一接入

## 一、为什么（现状→目标）

| 现状 | 问题 | 目标 |
|---|---|---|
| 黑板=本地文件（registry.md 等） | 仅本机可读，跨设备不可见 | 黑板服务器：所有节点 HTTP 读写 |
| 订阅无推送（A/B 级靠值班 agent 代发） | 投递层依赖 agent 回合 | 订阅 webhook 回调：变更→POST 通知订阅者 |
| i9 Docker/Ollama 状态本机自管 | 手动 Reset/排查 | 节点经 HTTP 上报状态+心跳→总线可见 |
| bus-bridge 8791 未跑 / 8790 推送已有 | 服务分散 | 黑板服务器=状态中枢，8790 保留推送 |

## 二、架构

```
                    ┌─────────────────────────────┐
                    │  跨设备黑板服务器（HTTP :8792）│
                    │  PUT/GET/LIST/SUBSCRIBE/AUDIT │
                    │  topic=registry|nodes|events  │
                    │  + 变更广播（webhook 回调）    │
                    └──────┬──────────┬──────────┬──┘
                           │          │          │
                  Tailscale 内网（9ms 级）        │
                           │          │          │
              ┌────────────▼──┐  ┌───▼──────────┐ │
              │ MBP 节点       │  │ mac-mini 节点 │ │
              │ agent/脚本读写 │  │ 8790 推送保留 │ │
              └───────────────┘  └───┬──────────┘ │
                          ┌──────────▼───────────┐│
                          │ i9 节点（Windows）      ││
                          │ 执行器：Docker/Ollama  ││
                          │ 状态上报+心跳+命令接收  ││
                          └──────────────────────┘│
```

## 三、API（CAHAC §6.2 六操作）

| 操作 | 语义 | 示例 |
|---|---|---|
| PUT(topic, key, value) | 写状态（version 递增） | PUT nodes/i9-ollama {status:ok, models:11} |
| GET(topic, key) | 读 | GET nodes/i9-ollama |
| LIST(topic, prefix) | 列出 | LIST nodes/ |
| SUBSCRIBE(topic, callback_url) | 注册回调：变更→POST 通知 | SUBSCRIBE nodes/i9* → mac-mini 回调 |
| DELETE(topic, key) | 删除 | DELETE events/xxx |
| AUDIT(topic, since) | 审计日志 | AUDIT registry/ 近 7 天 |

## 四、传输与部署

| 项 | 方案 |
|---|---|
| 服务端 | Node（复用 bus-bridge 同栈）或 Python HTTP，跑在 mac-mini（Tailscale 常在线） |
| 端口 | **8792**（避开 8790 webhook/8791 bus-bridge），Tailscale 内网绑定 |
| 认证 | 现有 x-webhook-token 模式（BUS_ALLOWED_FROM 白名单延续） |
| 节点接入 | i9 执行器（node 脚本）：心跳 60s + 状态上报 + 命令轮询 |
| 持久化 | append-only JSONL + version 文件（重启恢复） |

## 五、订阅/事件（跨设备唤醒的关键）

- 订阅者注册 callback_url → 黑板变更时 POST {topic,key,version,summary} 通知（替代值班 agent 轮询）
- 现有 event-bus.py 发布侧 → 黑板事件 topic（events/）统一
- 回调失败重试 3 次 + 死信日志（可靠投递）

## 六、与现有体系衔接

| 现有 | 衔接 |
|---|---|
| registry/台账（本地文件） | 黑板服务器权威 + 本地文件=镜像视图（脚本双向同步） |
| event-bus.py / blackboard-subscribe | 事件源改走黑板服务器 topic（保留本地回退） |
| 8790 external-link（企微推送） | 保留（推送出口），黑板订阅回调可指向它 |
| 设备协调 5a5368af | 黑板 nodes/ 域=设备状态权威源（心跳/资源/健康） |
| 节点总线（i9 方案） | 黑板服务器=节点总线状态中枢（一体两面） |
| 值班消费协议 | 保留为回退（黑板 webhook 优先，agent 轮询兜底） |

## 七、成本

- 零 LLM（Node/Python 本地 HTTP + 文件）
- 部署：mac-mini 常驻 node 服务（<50MB 内存）
- 首个用例：i9 Ollama/Docker 状态上报 + 心跳 → 视觉节点状态全网络可见

## 八、PoC 计划（确认后）

1. MBP 起黑板服务器 v0.1（8792，六 API + 订阅回调）
2. mac-mini 接入（registry 镜像 + 8790 回调测试）
3. i9 执行器接入（心跳 + Ollama/Docker 状态上报）——**顺便解决视觉节点可见性**
4. 首个真实用例：i9 Reset Docker 后 Ollama 状态自动上报黑板 → 总线可见 → 视觉部署推进
5. 验证：跨设备 GET nodes/i9* 实时返回；订阅回调触发通知

---
*跨设备黑板 v1.0 设计 · HR · 2026-08-21 · 待用户确认后 PoC*