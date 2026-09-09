# 黑板任务卡协议 v1.1：命名约定 + 指令展开细化 + schema 校验

> 日期：2026-08-23 · 协调者 fa1f9150 · 与 i9 总线智能体的黑板通讯契约
> 配套：scripts/task-card-validator.py（schema 校验器，生死线）

## 一、节点命名约定（黑板全域）

| 名称 | 指代 | 角色 |
|---|---|---|
| **mac总线** | mac-mini 中枢（协调者/黑板 8792/派单方） | 派单、下发配置、接收回报、仲裁 |
| **i9总线** | PC-i9 节点侧（DSH 智能体 deepseek-v4-flash/执行方） | 轮询取卡、执行、回报、写状态 |

- 黑板 `notes/mac-mini` 已声明此约定（i9 读 notes 可查）
- mac总线写：`tasks/i9/cmd`（派单）、`data/i9/config`（配置）
- i9总线写：`tasks/i9/result`（回报）、`notes/i9`（状态）
- 命名语义：**总线 = 收发任务卡的智能体**（不是物理设备名）

## 二、指令类型 → 展开模型分级

| 指令类型 | 例子 | 展开模型 | 校验后挂黑板 |
|---|---|---|---|
| **机械**（高频，70%） | 扫描 E 盘 / 查系统信息 / 跑某命令 | 本地 qwen2.5:3b（零订阅） | ✅ schema 校验 |
| **半结构化** | 扫描并按类型归档 / 汇总项目清单 | 本地展开 + 在线复核（低置信才在线） | ✅ schema 校验 |
| **复杂推理** | 分析项目沉淀并给复用建议 | 在线 deepseek-v4-flash | ✅ schema 校验 |

## 三、action 参数 schema（展开细化，校验器同款）

### 1. `shell`（执行命令）
```json
{"task_id":"<id>","action":"shell","payload":{"cmd":"<命令≤2000字符>"}}
```
- 危险命令拦截：format/diskpart/del /rd /s/rm -rf/shutdown/reg delete 等（校验器硬拦截）
- 适用：机械命令执行（dir/wmic/python 调用等）

### 2. `info`（系统信息）
```json
{"task_id":"<id>","action":"info"}
```
- 无 payload，返回 OS/内存/GPU/磁盘

### 3. `ollama`（本地模型推理）
```json
{"task_id":"<id>","action":"ollama","payload":{"model":"qwen2.5:7b","prompt":"<≤4000字符>"}}
```
- model 可选（默认 qwen2.5:7b），prompt 必填
- 适用：i9 本地零订阅推理（GPU 加速）

### 4. `scan`（目录扫描）
```json
{"task_id":"<id>","action":"scan","payload":{"path":"E:\\...","depth":2}}
```
- path 必填，**路径白名单**：E:/D:/C:\Users\admin 前缀；禁扫 C:\Windows 等系统路径
- depth 可选（默认 2）
- 适用：扫描目录 → 结构化清单（数据沉淀前置）

### 5. `数据沉淀`（扫描 + 归档）
```json
{"task_id":"<id>","action":"数据沉淀","payload":{"path":"E:\\...","target":"<归档目标>"}}
```
- path + target 必填，路径白名单同 scan
- target 指归档目标（mac总线侧知识库/目录）
- 适用：i9 项目沉淀 → 结构化 → 回流 mac-mini 知识库

## 四、派单流程（含校验生死线）

```
mac总线指令 → 展开（本地/在线分级）→ 【task-card-validator.py 校验】→ 黑板 tasks/i9/cmd → i9总线轮询取卡 → 执行 → 回报 tasks/i9/result → mac总线收讫
                                    ↑ schema 校验：action 白名单 + payload 类型 + 路径白名单 + 危险命令
                                    非法 → 拒绝挂黑板（不执行）
```

**校验器是生死线**：任务卡是执行指令，本地模型展开可能出错（action 错/参数错/路径错），校验器纯规则拦截，零 LLM 成本。

## 五、轮询配置（data/i9/config 约定）

- 配置放黑板 `data/i9/config`（mac总线写，i9总线读）
- 字段：poll_interval_s（轮询间隔）、timeout_s（任务超时）、heartbeat_interval_s（心跳间隔）、report_format（回报格式）
- 自适应轮询建议：有任务卡高频（10s）、空闲低频（60s+），i9 侧实现，配置给基线值

## 六、超时兜底

- mac总线派单后，`timeout_s` 内未收到 `tasks/i9/result` → 判定超时
- 动作：① 生成「超时提示词」（用户手动复制到 i9 侧确认轮询状态）② 或 i9 侧回报「未取到任务卡」时协调

## 七、关联

- `scripts/task-card-validator.py`（校验器）
- `i9-node-integration-2026-08-23.md`（接入经验）
- `node-relationship-model-v1.0.md`（任务卡协议 v1.0 设计）
- 黑板 `data/i9/config`（轮询配置）

---

# 补充：任务卡队列机制 v1.2（解决单卡槽瓶颈）

> 2026-08-23 · 协调者 · 单卡槽 PUT tasks/<node>/cmd 覆盖丢失 + 串行阻塞 → 队列化

## 问题（单卡槽瓶颈）

- `tasks/<node>/cmd` 单 key：PUT 覆盖（多卡只剩最后一张）
- 串行阻塞：慢任务（scan 5min/ollama）期间后续卡排队但无队列概念
- 无批量/无优先级

## 队列方案

```
中枢派卡（可批量，独立 key 不覆盖）：
  PUT tasks/<node>/queue/<seq>  body=任务卡
  seq = 毫秒时间戳（唯一+递增），如 queue/123456

节点取卡（i9 轮询）：
  GET tasks/<node>/queue/ → LIST 全部
  → 按 seq 排序取最早（最小 seq）
  → 执行 → PUT tasks/<node>/result → DELETE tasks/<node>/queue/<seq>
  → 下轮取次小 seq，依次处理，不丢卡
```

## 兼容

- `tasks/<node>/cmd` 保留为「处理中引用」或直接废弃（i9 完全切 queue）
- 回报 key `tasks/<node>/result` 不变
- 校验器/展开器不变（只改派卡路径）

## 落地

- expander 已改：`PUT /tasks/<node>/queue/<seq>`（seq=毫秒时间戳）
- i9 侧轮询需适配：GET queue/ LIST + 按 seq 取最早 + DELETE
- 黑板 `data/i9/config` 加 queue 说明

---

# 补充：并发增强 v1.3（i9 并行执行多卡）

> 2026-08-23 · 用户确认「可以加并发增强」 · 在队列 v1.2 基础上增强

## 并发机制

```
i9 轮询（30s）：
  GET /tasks/ LIST → 过滤 ^tasks/i9/queue/\d+$ → 按 seq 升序
  → 一次取最早 N 张（N = max_concurrent，config 控制，默认 2）
  → 并行执行（多线程/多进程，各自独立）
  → 各自 PUT tasks/i9/result + DELETE tasks/i9/queue/<seq>
  → 下轮取下一批

max_concurrent 配置：data/i9/config v4
  默认 2（i9 32G 内存可支持）；资源紧张降 1（退化为依次执行）
```

## 收益

- 慢任务（scan 5min/ollama 加载）不再阻塞后续卡（并行）
- 多卡场景吞吐提升（N 倍）
- N 可调，资源成本可控

## 边界

- GPU/Ollama 类任务可能单任务占资源（max_concurrent 建议 ≤2，或对 gpu 类任务限并发 1）
- 回报 key 不变（tasks/i9/result 每次回报覆盖，task_id 区分）

## 落地状态

- 黑板 notes/i9/queue-adapt 已通知 i9（队列适配 + 并发增强）
- config v4：max_concurrent=2

---

# 补充：双向异步并发 v2.0（黑板规则升级）

> 2026-08-23 · 用户提出「双向异步并发接收/回复」 · 黑板从单向任务队列升级为双向异步消息总线

## 一、双向队列（对称）

```
中枢 → 节点（派单）：tasks/<node>/queue/<seq>     （已有）
节点 → 中枢（主动发）：tasks/central/queue/<seq>  （新增，对称）
  - 节点可主动发：状态上报 / 调度请求 / 结果通知 / 异常报告
  - 中枢订阅 tasks/central/queue/ 事件驱动接收（不轮询）
```

验证：i9 → central 队列写卡/读卡 ✅（实测）

## 二、并发回报（解决单 key 覆盖）

```
回报（append-only 历史）：tasks/<node>/results/<seq>  （每回报独立 key，不覆盖）
最新回报引用：tasks/<node>/result  （保留，指向最近一次）
中枢读历史：LIST tasks/<node>/results/ → 全部回报可追溯
```

验证：3 条回报独立 key 共存 ✅（实测）

## 三、异步接收（订阅替代轮询）

```
订阅：POST /subscribe {"topic":"tasks/<node>/queue/","callback":"..."}
  → 新任务卡到达即回调（事件驱动，零轮询）
  → 复用 sse-sub 框架（配置式订阅器，客服已实现）
轮询：降级兜底（订阅不可用时）

中枢订阅：tasks/central/queue/（收节点消息）+ tasks/<node>/results/（收回报）
节点订阅：tasks/<node>/queue/（收派单）
```

验证：SUBSCRIBE 回调触发 ✅（实测收到任务卡内容）

## 四、并发安全

- KV 存储天然并发（不同 key 无冲突）
- ThreadingHTTPServer 并发请求
- seq 毫秒时间戳递增保证顺序
- 订阅/轮询可并存（订阅主用，轮询兜底）

## 五、与现有衔接

- sse-sub 框架（客服）：通用订阅器，直接复用
- 队列 v1.2 / 并发 v1.3：派卡/并发不变
- GeneBank：i9 scan → 基因注册可经双向队列回报中枢

---
*黑板任务卡协议 v1.1 + 队列 v1.2 + 并发 v1.3 + 双向异步并发 v2.0 · 协调者 2026-08-23*
