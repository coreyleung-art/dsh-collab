# 跨设备桥 · 统一日志规范（logging-sop）

> 维护者：mac-mini 中枢 ｜ 更新：2026-08-27
> 目的：所有工具/插件/守护的日志与审计**统一位置、统一格式、统一归档**，可追溯、可审计。

## 一、日志目录结构

```
~/dsh-collab/logs/
├── README.md            # 本索引
├── tools/               # Rust 工具运行日志
│   ├── dsh-tools/       #   dsh-tools 各子命令输出（bb-read/agent-msg/deploy-check）
│   ├── node-bridge/     #   node-bridge 运行日志（mac-mini 实例）
│   └── rust-blackboard/ #   黑板 8792/8803 日志
├── plugins/             # DSH 插件运行日志
│   ├── agent-bus/       #   agent-bus 插件日志
│   └── central-inbox/   #   central-inbox 注入日志
├── bridge/              # 跨设备桥核心审计
│   ├── llm-ledger.jsonl      #   node-bridge LLM 执行器调用台账（追加式）
│   └── llm-dead/             #   LLM 死信（重试耗尽消息，防丢失）
├── audit/               # 合规审计
│   ├── agentsend-violations.jsonl  # agent_send v2.3 违规记录（>200字无黑板引用）
│   ├── deploy-check/             # deploy-check 部署审查报告
│   └── verify-watch/             # 跨设备重启验证记录
└── archive/             # 归档（按月）
    └── YYYY-MM/
```

## 二、日志格式规范

所有 jsonl 审计日志统一字段：

```json
{"ts": 1787773055123, "node": "mac-mini", "tool": "agent-msg", "action": "send", "detail": "...", "ok": true}
```

- `ts`: epoch 毫秒（非 `%N` 字符串——macOS date 不支持 %N，用 python int(time.time()*1000)）
- `node`: 节点名（mac-mini/mbp/i9）
- `tool`: 工具名（dsh-tools/node-bridge/central-inbox/agent-bus/...）
- `action`: 动作（send/recv/exec/check/inject/...）
- `detail`: 详情（字符串）
- `ok`: 成功/失败

## 三、各日志来源与写入点

| 日志 | 写入者 | 位置 | 格式 |
|------|--------|------|------|
| LLM 调用台账 | node-bridge llm.rs | logs/bridge/llm-ledger.jsonl | jsonl（追加） |
| agent_send 违规 | agent-send-gate.py | logs/audit/agentsend-violations.jsonl | jsonl（追加） |
| verify-watch | verify-watch.py | ~/.dsh/logs/verify-watch.{out,err}.log | 文本 |
| bb-sub inbox | bb-sub-daemon.py | ~/.dsh/inbox/bb/<agent>.jsonl | jsonl（append-only，[NEW] 标记） |
| 迭代报告 | 各智能体 | 黑板 data/iterations/* | 黑板 KV |
| registry | 中枢 | 黑板 data/mac-mini/registry/* | 黑板 KV |
| 部署审查 | deploy-check | 终端输出 / logs/audit/deploy-check/ | 文本/JSON |

## 四、归档规则

1. **每月归档**：每月 1 日把 logs/{tools,plugins,bridge,audit} 中 >30 天的 jsonl/日志移入 logs/archive/YYYY-MM/
2. **保留策略**：llm-ledger 保留 6 个月（成本审计需要）；agentsend-violations 保留 6 个月；其余 3 个月
3. **黑板痕迹**：重要事件（部署/注入验证/版本升级）同步写黑板 data/iterations/ + data/mac-mini/registry/

## 五、审计入口

- 成本审计：llm-ledger.jsonl（token 消耗可查）→ HR 成本审计 §六 引用
- 合规审计：agentsend-violations.jsonl（通道规范执行情况）
- 部署审计：deploy-check 报告 + verify-watch 记录（重启验证）
- 版本审计：tools-registry.md（全量版本台账）

## 六、硬约束（写日志时遵守）

- macOS `date +%s%3N` 输出 `%N` 字面量 → 时间戳用 `python3 -c "import time; print(int(time.time()*1000))"`
- 不写临时日志到 /tmp（重启丢失）；统一 logs/ 目录
- launchd 守护的 stdout/stderr 重定向到 ~/.dsh/logs/（不进 /tmp）
