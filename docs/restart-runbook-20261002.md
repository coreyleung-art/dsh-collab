# 重启操作卡 · 通信底座架构改造（2026-10-02）

> 给你（用户）的一张卡：照做 → 看数 → 不达标怎么回滚。
> 代码已全部就位并过闸门（三插件预检 GO、五个自检 exit=0），**只差一次 CLD 重启生效**。

---

## 1. 为什么必须重启

本机插件是 `link:` 部署——**源码即部署**，但 Node 的 ESM 模块缓存使**常驻进程看不到新代码**（已实测确认：改动后进程行为不变，重启才加载）。重启只是"加载新代码"，不动任何数据。

## 2. 重启后会发生什么（预期数字，重启前实测推算）

| 现象 | 原因 | 预期 |
|---|---|---|
| queued **2059 → ≈302** | A2：超 7 天的排队消息在启动清扫时标记为 `expired`（不删除，可回放） | 回收 **≈1771 条** |
| 历史消息 `from` 被归一化 | I1 迁移：展示名+id 形态（`老登 session-aa528267 (mac-mini)` 等）恢复为身份 | 修复 **≈1284 条** |
| 新消息带 `acked: sent→received→claimed` + `idleAt` | I3/I4：订阅官方 `agent/inbox/*` 事件 | 第一条新消息起可见 |
| 「看黑板…」通知不再唤醒对方 | I7：指针式通知走官方 `inject`（不唤醒） | 消息带 `wake:inject` |
| 写盘不再有撕裂风险 | I5：官方 `writeFileAtomic`（tmp+rename） | 无感 |
| 发给自己的消息被拦 | A6 v2：`from∩to` 自回声判定 | 返回 `status:'self-echo'` |

## 3. 照做（三步）

1. **重启 CLD**（GUI 退出重开，几秒级）。
2. 打开本会话（我）任意说一句"验收"（或直接发一条消息给我）。
3. 我会跑：`python3 ~/dsh-collab/scripts/post-restart-acceptance.py` —— 预期 **6/6**；并重跑审计矩阵，把 PENDING/GAP 落成 PASS。

## 4. 如果没达标（回滚点都在）

| 问题 | 回滚 |
|---|---|
| 插件起不来 | `~/dsh-collab/guard/backups/…bak-good-2026-10-01-{16-1,17-0,19-3,19-4}` 共 15+ 份（agent-way / central-inbox / guard / 共享模块 / 9 个 plist），`cp` 回去再重启 |
| 只想撤 1.5.5/1.5.6 新机制 | agent-way 回滚到 `…agent-bus__lib__index.js.bak-good-2026-10-01-16-1`（A 批基线） |
| node-bridge/bb-sub 异常 | dist 内旧二进制仍在（v1.4.0 / v1.12.0）；plist 备份在 guard/backups/…19-3 / 19-4 |

## 5. 重启后还需要你批的两件事（不阻塞验收）

- **清淤清单** `~/dsh-collab/docs/cleanup-candidates-list-20261002.md`（Gen1 死目录/孤儿脚本/旧二进制）—— 按节说「批/留」。
- **安全处置** `~/dsh-collab/docs/security-node-bridge-plaintext-token-20261002.md`（两处 plist 明文凭据：node-bridge + wecom-inbox）—— 四步（轮换/迁移 0600/清备份/审计）。

## 6. 一句话状态

**代码侧与验收侧 100% 就绪；跨设备两个通道的修复已部署生效（日志 62GB/天→0、订阅日志 205MB→16MB）；这次重启让 agent 通道侧的五项机制落地。**
