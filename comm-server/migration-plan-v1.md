# 通讯层服务器化迁移计划 v1.0（2026-09-06）

> 决策：资源成本评估完成（服务器 529MB available，通讯层全迁仅需 ~130MB）
> 原则：**同步双轨、本地通道维持、备灾不抹旧**（R031 通讯永续 + Φ9 约束前置）
> 服务器：xingqiao.meetfunbp.com（106.53.214.108, Ubuntu 22.04, 1G/40G）

---

## 〇、设计总则（Lean4 不变量）

```
I1 本地通道永不抹除（双轨并行，非替换）——中枢挂→本地照常
I2 任何迁移分两步：服务器先起(验证)→本地降级为备(保留可回切)
I3 无验证成功=未成功（R030）：每阶段迁移后必验证再切
I4 数据分区隔离（Prod/Test）+ 变更可回滚
I5 通讯永续（P3）：迁移窗口不造成三端断连
```

## 一、迁移范围（资源成本实测）

### 阶段 A · 通讯订阅层（最高优先，成本 ~60MB）
| 服务 | 本机内存 | 服务器角色 | 说明 |
|---|---|---|---|
| bb-sub coordinator | 5MB | 常驻订阅 | 星桥核心订阅（collab/mac-mini/queue/i9） |
| bb-sub device/hr/learning/qa/recovery/supply/xingduo | 34MB | 常驻订阅 | 各角色订阅器 |
| bus-bridge 8791 | 14MB | 常驻路由 | 跨设备消息总线 |
| feature-mcp 8811 | 7MB | 常驻 MCP | 学习库特征库 |

### 阶段 B · 外链层（成本 ~66MB）
| 服务 | 本机内存 | 服务器角色 | 说明 |
|---|---|---|---|
| external-link SSE 8910 | 17MB | 公网入口 | 外链 MCP（webhook 双活） |
| external-link webhook | 22MB | 公网入口 | webhook 收消息 |
| wecom-inbox | 14MB | 常驻 | 企微长连（token 迁移评估） |

### 阶段 C · 可选
- verdaccio npm 私服（14MB）——三端同源装包
- cld-monitor 守护看板（服务器 24h 跑健康监控，本机版保留）

## 二、双轨架构（本地主 + 服务器镜像）

```
                 ┌─────────────── 服务器(xingqiao) ───────────────┐
                 │  通讯层：bb-sub×8 + bus-bridge + external-link  │
                 │  24h 常驻 · 公网可达 · 不怕本机重启              │
                 └──────┬──────────────────────┬─────────────────┘
                        │ 双写/镜像             │ 主处理
                 ┌──────┴──────┐       ┌───────┴───────┐
                 │ mac-mini     │       │ MBP / i9      │
                 │ 本地通道保留  │◄─────►│ 本地优先+镜像  │
                 └─────────────┘       └───────────────┘

本地通道角色（保留备灾）：
- mac-mini 本机黑板 :8792 + 本地 bb-sub（若有）+ central-inbox
- MBP node-bridge → 本机黑板（已确认保留）
- i9 notes/i9/ → 本机黑板（已确认保留）
```

## 三、备灾设计（通道降级矩阵）

| 故障场景 | 主通道 | 备灾通道 | 切换 |
|---|---|---|---|
| 服务器挂 | 服务器通讯层 | **本地 bb-sub + 本机黑板照常** | 自动（本地进程独立） |
| mac-mini 挂 | 本地黑板 | **服务器通讯层接管**（i9/MBP 直连中枢） | 需配置 fallback 地址 |
| MBP 挂 | MBP 直连 | 心跳超时 → 星桥人工确认 | 告警 |
| i9 挂 | i9 直连 | 心跳超时 → 星桥人工确认 | 告警 |
| 网络断 | 双轨 | 本地操作不阻塞（异步同步） | 自动（队列缓存） |

### 备灾核心机制
1. **本地 bb-sub 不全撤**：保留 coordinator 一个本地实例，服务器版为主——本地版做兜底订阅
2. **双写关键事件**：任务卡/告警写本机+中枢双份，任一端可读
3. **健康探测**：服务器版 cld-monitor 每 30s 探本机心跳；本机探服务器——互探发现故障
4. **回切预案**：服务器验证 24h → 本地降备（不停进程只降优先级）；出问题一键回切

## 四、执行计划（分阶段，每步验证）

### Step 1 · 服务器通讯层部署（✅ 2026-09-06 完成 · 执行见 deploy-comm-layer.sh）
- [x] 服务器装 node —— 复用 /opt/node v24.20.0（8-26 随 comm-server 部署已装）
- [x] 传二进制/脚本到 /opt/comm-layer/ —— dsh-tools-linux-x64-v1.4.2（bb-sub 子命令 v1.0 起未变，功能等价本地 v1.12.0）+ bus-bridge.js
- [x] systemd 服务化 —— 9 units：comm-bb-sub-{coordinator,device,hr,learning,qa,recovery,supply,xingduo} + comm-bus-bridge，全 active
- [x] 验证（R030 实测）：8×bb-sub SSE 全连中枢(127.0.0.1:8803)；注入 notes/mac-mini/deploy-layer-test → coordinator inbox 4s 收到；device inbox 实时收 i9/mac-mini 心跳镜像(v79)；bus-bridge 全闭环 send→receive→reply→outbox + X-Webhook-Token（无 token 401）
- ⚠️ feature-mcp 8811 **暂缓**：数据源(~/.chroma flower-feature)+embed(本机 ollama)绑定 mac-mini，非无状态订阅层；1G 服务器跑 ollama 不可行，迁移另评
- 📌 服务器 inbox：/home/ubuntu/.dsh/inbox/bb/<agent>.jsonl（中枢事件留痕，本机挂机期间事件不丢）
- 📌 bus-bridge 0.0.0.0:8791 + X-Webhook-Token（root 0600 env）；公网放行留待 Step 3 灰度

### Step 2 · 双轨验证（✅ 2026-09-06 完成 · 不动本地通道）
- [x] 服务器 bb-sub 订阅中枢 SSE，本地 bb-sub 继续订阅本机（双活并行）
- [x] 双写测试：上行 notes/collab/step2-up-test → sync-up 推中枢读回 ✅；下行中枢 notes/i9/step2-down-test → sync-down 拉本机读回 ✅（_via:comm-central 标记）
- [x] **下行实时化升级**：sync-down 由 5min 轮询(--once) → launchd 常驻 SSE（KeepAlive+RunAtLoad，plist 备份 .bak-5min 可回滚）；实测 i9 域写中枢 → 本机 0-1s 镜像（3 次采样 0.0/1.0/1.0s）
- [x] 互探：服务器读中枢 nodes/mac-mini/heartbeat（version 88，_mirror:mac-mini-fwd，age<30s）✅；本机读中枢 1700 键 ✅
- [x] 指标：下行延迟 0-1s（实时）；上行 sync-up 保持 5min 周期（本机自推键可容忍）
- 📌 产出文件：com.dsh.comm-sync-down.plist（常驻版，原 5min 版留 .bak-5min）；日志 /tmp/comm-sync-down.log

### Step 3 · 流量灰度（~1 天观察）
- [ ] 新任务先走服务器通道（灰度 10%→50%→100%）
- [ ] 本地通道保留（兜底订阅），观察稳定性
- [ ] 服务器版 cld-monitor 看板每日报告

### Step 4 · 外链层迁移（⏸ 暂缓 2026-09-07 用户决策）
- [ ] external-link SSE/webhook 部署服务器（公网入口）
- [ ] wecom-inbox token 迁移（安全评估）
- [ ] 域名指向服务器（或保留本机+服务器双入口）
- ⏸ 暂缓原因（用户澄清）：① 企微掉线根因 = 企微平台授权机制(token 定期失效需重授权)——迁服务器不解决（服务器上一样需重授权）② 客服自动回复已 hold(无 24h 客服在线需求) → Step 4 主收益场景不存在
- 📌 保留潜在价值：SSE 8910 供外部智能体公网接入——未来有真实需求时单独评估（不牵企微）
- 📌 已完成不受影响：Step 1-3（通讯订阅层/总线/黑板中枢服务器化）无企微授权依赖

### Step 5 · 备灾演练 + 收尾
- [ ] 演练：停服务器 → 验证本地通道接管；停本地 → 验证服务器接管
- [ ] 文档固化（本计划更新为 v2 实际操作版）
- [ ] 回切预案测试（本地 bb-sub 仍可拉起）

## 五、风险与门（Φ9 约束前置）

| 风险 | 缓解 |
|---|---|
| 服务器 node 环境缺依赖 | 先沙箱验证（deploy 脚本模式） |
| wecom token 泄露 | 凭证 0600 + 仅服务器可读 + 迁移时轮换 |
| 双写数据不一致 | 单写者优先 + 时间戳比对 + 补偿同步 |
| 本地进程误停 | 迁移期间不 kill 本地进程，只加服务器副本 |
| 服务器容量不足 | 已评估（130MB < 529MB available）——但持续监控 |

## 六、待用户确认
1. 阶段 A（通讯订阅层）是否先启动？
2. wecom-inbox token 是否授权迁移（安全敏感）？
3. 本地 coordinator bb-sub 是否保留兜底实例？（建议保留）
