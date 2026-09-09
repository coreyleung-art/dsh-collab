# 黑板时间轴 v0.3 设计 · Timeline & Global Sequence

> 2026-08-23 · 协调者 · 底座进化（用户指示：建时间轴管理 + 唯一时间戳，让所有设备对齐基线）

## 一、问题

多设备（mac-mini 中枢 / i9 / MBP）各写黑板，但：
1. **本地时钟有偏差**：i9 的 `ts` 是 Windows 本地时间，mac-mini 是 macOS 时间，不可比「谁先谁后」
2. **无全局事件序**：任务卡 seq 是各节点自生成的毫秒时间戳，跨设备无法排序/对齐
3. **重启断点丢失**：设备宕机/重启后，无法知道「错过了哪些事件」——只能全量 LIST 或盲等订阅
4. **同一毫秒冲突**：多写入者同一毫秒生成的 seq 可能相同（历史上发生过覆盖）

## 二、方案：全局唯一时间戳（HLC 风格）+ 时间轴

### 2.1 全局单调 seq（唯一时间戳）
- 黑板是唯一写序权威：**每次 PUT/DELETE 分配全局单调递增 seq**
- seq = `(秒级物理时间戳 * 10^6) + 逻辑计数器`（同秒内计数递增 → 全局唯一且单调）
- 物理时间取**黑板服务器时间**（不是客户端 ts）→ 所有事件统一到黑板时钟轴
- 持久化：seq 随 audit.jsonl 落盘，重启从 audit 恢复最大值（不丢序）

### 2.2 时间轴查询（增量基线）
```
GET /timeline?since_seq=<N>&limit=<M>
  → {"events":[{"seq","op","key","ts","version"}...],
     "latest_seq":<当前最大>, "since_seq":<N>, "total":<命中数>}
```
- 设备记住自己消费到的 `latest_seq` → 重启后用 `since_seq` 增量补漏 → **对齐基线**
- 按 seq 排序返回（全局序），limit 分页防爆

### 2.3 对时（时钟锚点）
```
GET /clock → {"seq":<当前最大>, "ts":"<黑板服务器时间>", "server":"<host>"}
```
- 任何设备可随时对时：拿到黑板权威 seq + 时间 → 校准自己的基线

### 2.4 兼容性
- 现有 API 全不变；PUT 响应**新增 `seq` 字段**（客户端可读，不强制用）
- audit.jsonl 增加 `seq` 字段；旧记录加载时按序补 seq（不回写，仅内存）
- 订阅通知 payload 新增 `seq`（通知带全局序）

## 三、API 速查

| 端点 | 方法 | 用途 |
|---|---|---|
| `GET /clock` | GET | 对时：当前全局 seq + 黑板服务器时间 |
| `GET /timeline?since_seq=N&limit=M` | GET | 增量事件时间轴（按 seq 全局序） |
| `PUT /<ns>/<key>` | PUT | 写（响应带 seq） |
| `POST /subscribe` | POST | 订阅（通知带 seq） |
| `GET /timeline?op=PUT&since_seq=N` | GET | 按操作类型过滤（可选） |

## 四、设备接入方式（建议，不强制）

```
启动时: GET /clock → 记 base_seq
消费:   订阅 or 轮询 → 处理事件 → 记 latest_seq = max(latest_seq, evt.seq)
重启后: GET /timeline?since_seq=<latest_seq> → 补漏未处理事件 → 继续
```

## 五、验证判据

- [ ] 并发 PUT 多次 → seq 全局严格递增、无重复
- [ ] 跨秒/同秒写入 → seq 仍单调（逻辑计数兜底）
- [ ] GET /timeline?since_seq=N → 只返回 N 之后事件，按 seq 排序
- [ ] 重启黑板 → seq 从 audit 恢复继续递增（不重置）
- [ ] /clock 返回黑板权威时间 + 当前 seq
- [ ] v0.1/v0.2 客户端（无 seq 感知）照常工作

---
*v0.3 时间轴设计 · 协调者 2026-08-23*
