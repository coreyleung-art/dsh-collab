# 黑板投递 · 值班消费协议 v1.0

> 建立：2026-08-20 · HR · 用户批准方案 1（值班 agent 轮询代发）· 解决黑板信号「检测→队列」后投递层不通的问题

## 机制

```
黑板变更/事件 → 脚本检测（5min）→ 队列（wakeup-queue / send-instructions）
  → 值班 agent 回合消费 → agent_send 定向 → 目标 agent 上下文收到小 token 提醒
```

## 值班规则（所有 agent）

1. **每个实质回合**（处理任务/巡检/报告时）先检查待发队列：`python3 ~/dsh-collab/scripts/event-bus.py --status`
2. 有 pending 指令 → 读 send-instructions/*.json → 按 agent 定向 `agent_send`（只发摘要+指针，非全量）→ `--mark-sent <id>`
3. **HR 为默认值班**：每次实质回合代发积压指令（本会话承诺）
4. **daily-brief 22:00 批量兜底**：简报生成推送时顺带消费当日积压（防长周末堆积）
5. 不重复：dedup_key + sent 标记；已过期信号（>24h）归档不发送

## 队列清理

- wakeup-queue/*.jsonl 保留 30 天；send-instructions 保留 30 天
- 每日简报「日常检查」显示待发送 N 条（可视）

## 机械任务零订阅派单（v1.1 补充 · 2026-08-23）

值班 agent 遇到需要 i9 执行的**机械任务**（scan/info/shell 类）时，用本地展开器派单（**零订阅**，省在线模型 token）：

```bash
# 指令 → qwen2.5:3b 本地展开 → schema 校验（生死线）→ 挂黑板 → i9 执行
python3 ~/dsh-collab/scripts/task-card-expander.py "扫描 E:\projects 目录"
```

**规则**：
1. 机械指令（扫描/查状态/跑命令）→ 本地展开器（零订阅）；复杂指令（分析/建议）→ 在线模型
2. **schema 校验器是生死线**（task-card-validator.py）：删除类命令/路径越界/危险操作一律拦截，校验不过不挂黑板
3. 派单后 i9 执行回报，用沉淀回流脚本归档：

```bash
# scan 结果 → 结构化清单文档（自动落盘）
python3 ~/dsh-collab/scripts/deposit-reflow.py
```

4. 超时兜底：派单后超过 timeout_s（黑板 data/i9/config，默认 600s）未收到回报 → 用超时提示词模板（i9-timeout-prompt-template-2026-08-23.md）让用户手动提示 i9 侧
5. 工具链：task-card-expander.py（展开）/ task-card-validator.py（校验生死线）/ deposit-reflow.py（回流归档）

*HR · 2026-08-20 · registry v1.0.309*