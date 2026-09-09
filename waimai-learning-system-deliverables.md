# 外卖门店多平台管理 · 学习系统成果物（a3bc8cba ⇄ 各会话）

> 落盘：2026-08-16 · 来源：session-a3bc8cba（学习系统/知识库推进）· 项目：~/meituan-multi
> 定位：**实时采集端**（de7b29de watcher/events）与**历史沉淀端**（本会话 comm.db + KB）互补。

## 一、核心交付物清单

| 成果 | 位置 | 说明 |
|------|------|------|
| comm.db 独立学习库 | `MTM_DATA_DIR/data/comm.db` | 客户/会话/消息/订单 4 表，与 app.db 运行监控分离 |
| 知识库同步管道 | `lib/kb-sync.js` | outbox → Obsidian raw/dsh + changelog + manifest + 归档（幂等 sha256） |
| 客户沟通学习 | `lib/learning/im.js` | imManage 帧 + IM 气泡 + IM 客服工作台（独立窗口 sessionId 访问） |
| 历史会话范本聚类 | `lib/learning/im-history.js` | 会话消息级读取 → 问答配对 → 场景聚类（7 类） |
| 批量归档采集 | `lib/comm-archive.js` | 工作台全量会话 + 实时 im_sessions 导入 + 订单时段遍历 |
| 客户会话订单学习数据 | `docs/manuals/18-客户会话订单学习数据.md` | 报告 + DSH KB 文档 38 |

## 二、comm.db 数据契约（供消费端会话使用）

**表结构**：
- `comm_customers`：store_id / client_key(脱敏) / label / order_count / msg_count / scene_tags(JSON)
- `comm_sessions`：store_id / client_key / session_date / status(done|timeout|pending) / last_msg / detail(完整消息流JSON)
- `comm_messages`：session_id / direction(client|staff) / auto(自动回复标记) / content / msg_ts
- `comm_orders`：store_id / order_no / amount / status / items(JSON)

**当前数据**（守白鲜花 + 4 店实时监控）：86 客户 / 117 会话 / 685 消息 / 0 订单（沙箱店无历史订单）

**查询 API**（`lib/comm-db.js`）：stats / customerPortrait / sessionDetail / sceneDistribution / orderStats

**边界说明**：
- client_key 为平台脱敏昵称（i**/池**），非真实用户标识，不可用于外呼
- 消息方向按气泡 x 坐标判定（顾客左/商家右），自动回复带 auto 标记
- scene_tags 为规则聚类（款式/价格/配送/售后/订单/闲谈/主动回复），非 LLM 语义标签

## 三、与其他会话的协作点

- **de7b29de（采集端）**：events 表 customer_msg 实时流 → 本会话 im_sessions 历史会话 → comm.db 沉淀；建议实时→历史衔接（定期 archive 合并）
- **aa528267（场景引擎）**：scanScenes 可扩展读 comm_messages 做历史场景分析（不再只依赖实时 events）
- **App 开发会话**：面板可加「学习库」tab 展示 comm.db 画像/分布

## 四、快捷命令

```bash
MTM_DATA_DIR=~/Library/Application\ Support/外卖门店多平台管理 node mtm.js comm-archive <店> --all   # 批量归档
node mtm.js learn-im-history <店> --max 30    # 历史会话范本聚类
node mtm.js kb-sync status                     # 知识库同步状态
node mtm.js learn-im <店>                      # 客户沟通学习（含管理指南）
```
