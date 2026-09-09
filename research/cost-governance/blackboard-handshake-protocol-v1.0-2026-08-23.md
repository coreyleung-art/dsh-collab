# 黑板消息握手协议 v1.0 · Handshake Protocol

> 2026-08-23 · 协调者 · 用户指示：黑板中间应加握手逻辑链条——每条信息单独生成密钥，确保不漏发、漏了能补上
> 衔接：v0.3 全局 seq（唯一写入序）+ v0.6 recipient 定向 + v0.2 result 镜像

## 一、要解决的问题

1. **写入 ≠ 送达**：黑板写进即算「存在」，但发送方不知道接收方是否真处理了
2. **无消息级确认**：只有任务卡有回报闭环，通用消息（notes/）无 ACK
3. **漏了靠人工发现**：消息漏读（如 i9 历史 3 次漏唤醒）无自动补漏机制

## 二、协议设计（可靠性三要素）

### 1. 消息唯一 ID + 密钥
- `msg_id = <sender>-<seq>`（seq 为黑板全局唯一序 → 天然唯一不重复）
- `msg_key = sha256(msg_id + recipient)[:16]`（每条独立密钥，可校验来源/完整性）

### 2. 握手落板（发送 → 确认）
- 发送：`PUT notes/<recipient>/handshake/<msg_id>` 
  `{msg_id, msg_key, sender, recipient, seq, payload, ts}`
- 确认：接收方处理完 `PUT data/handshake/acks/<msg_id>` 
  `{msg_id, status:processed, by, ts}`
- 发送方查 acks → 知道哪些已处理、哪些待确认

### 3. 水位 + 补漏
- 接收方记 `data/handshake/watermark/<recipient> = {last_seq}`
- 补漏检查：水位 vs 黑板时间轴 `GET /timeline?since_seq=<水位>`
  → 发现 `notes/<recipient>/handshake/*` 中未 ACK 的消息 = 缺口 → 补处理/重发

## 三、消息流

```
发送方                         黑板                          接收方
  │ PUT notes/<recipient>/handshake/<msg_id>                 │
  │──────────────────────────────→(seq 分配)                 │
  │                                      │(时间轴记录)       │
  │                                      │←── 接收方处理     │
  │                                      │───→ PUT acks/<msg_id> {processed}
  │←── GET acks 查确认 ────────────────  │
  │   (未确认 → 重发/告警)                │
  │                                      │─── watermark/<recipient> {last_seq}
  │── 补漏检查: timeline?since_seq=水位 ──→│
  │   (发现缺口 → 补处理)                 │
```

## 四、实现

- 工具：`scripts/bb-handshake.py`
  - `--send --to <r> --msg '<m>'` 发送（自动拿全局 seq 做 msg_id + 生成密钥）
  - `--ack --msg-id <id> --by <r>` 确认处理
  - `--check --for <r>` 补漏检查（水位 vs 时间轴，找未确认消息）
  - `--watermark --for <r>` 查水位
- 密钥：每条消息独立 `msg_key`（可校验，防伪造/防混淆）

## 五、验证判据

- [x] 发送 → msg_id 唯一（基于全局 seq）+ msg_key 独立
- [x] ACK 后补漏检查 0 缺口
- [x] 不 ACK 的消息被补漏检查发现（模拟漏消息 ✅）
- [ ] 接入 i9/mac 消息（发送方统一带 msg_id，接收方处理回 ACK）

## 六、接入建议

1. 中枢发指令给 i9/角色：用 bb-handshake.py --send（自动 msg_id+密钥）
2. 接收方（i9 执行器/角色）处理完 --ack
3. 定期 --check --for <接收方>（可并入吸收 watcher 周期）
4. 与自治协议衔接：type=request + action_needed + handshake msg_id = 双重保障

---
*黑板消息握手协议 v1.0 · 协调者 2026-08-23 · 用户指示可靠性增强*

## 七、泛化到所有黑板场景（v1.1）

握手协议不只服务定向消息，泛化到所有黑板写入：
1. **所有写入已带可靠性基础**：全局 seq（msg_id）+ writer（X-Writer）+ 时间轴（since_seq）——对任意 key 生效
2. **通用水位**：每个消费方（订阅者/执行器）记 data/handshake/watermark/<消费方> = 已处理到的 last_seq
3. **通用补漏**：bb-handshake.py --check --for <消费方> --prefix <命名空间前缀>
   → 检查该域内所有写入，找未确认（漏处理）的
4. **通用确认**：data/handshake/acks/<msg_id>（按 key）或 acks/seq-<seq>（按 seq）

场景：
- 定向消息：--check --for i9（缺省查 notes/i9/handshake/）
- 节点状态域：--check --for i9 --prefix data/i9/（查 i9 相关所有写入）
- 角色状态域：--check --for <角色> --prefix data/<角色>/
- 任务域：--check --for <节点> --prefix tasks/<节点>/

消费方接入：处理完一批写入 → set_watermark(<消费方>, 最新seq) → 定期 --check 补漏
