# 星台迭代计划 v1（2026-09-03 · 用户需求全汇总）

> 星台 = 用户私人多设备对话壳（薄壳：只做入口，星桥/总线处理+指挥全网）
> 原则：R031（本地执行优先/通讯永续）+ human-in-the-loop（语音确认防歧义）

## 版本路线
| 版本 | 内容 | 状态 |
|------|------|------|
| P0 已交付 | 对话桥 + 文字双向 + 三端（mac/iPhone/iPad）+ 队列显示 + 公网通道 | ✅ |
| v9.2 | 语音可编辑（松开填入确认发送）+ 聊天持久化 + 键盘收起 | 🔄 MBP 构建中 |
| v9.3 | 多设备对话目标切换（方案 A 桥路由） | 📋 规划 |
| v9.4 | 队列语义优化/执行结果推送 | 📋 后续 |

## v9.3 · 多设备对话目标切换（方案 A：桥路由）

### 需求（用户原话）
> 星台允许切换不同设备的星桥/总线角色——选择在线的设备总线去对话

### 架构
```
星台 App（加「对话目标」选择器）
  │  Funnel 公网（不变）
  ▼
mac-mini 桥 :8820（加路由层）
  │  目标=mac-mini → 直接本机会话（现状）
  │  目标=MBP/i9 → 转发黑板 notes/<node>/inbox-to-<role> → 目标总线处理 → 回传黑板 → 桥回 App
  ▼
黑板路由 + 设备注册表（nodes/* 心跳活=可选目标）
```

### 实现步骤
1. **设备注册表**：桥 /api/devices 列出在线节点（nodes/* 心跳 <60s = online）+ 各节点总线角色名
2. **桥路由**：POST /api/chat 加 target 字段（默认 mac-mini/星桥）→ 非本机目标转发黑板
3. **目标侧接收**：MBP（mbp-bus）/i9（coordinator）消费 notes/<node>/ 对话消息 → 处理 → 回传
4. **星台 UI**：标题栏/设置加「对话目标」选择器（动态列在线设备总线）
5. **会话隔离**：每目标独立会话（不同目标不同上下文）

### 里程碑
- M1（0.5 天）：桥 /api/devices + 路由层（转发黑板）
- M2（0.5 天）：MBP 侧接收处理（mbp-bus 按协议接对话消息）
- M3（0.5 天）：星台 UI 选择器 + target 参数
- M4（0.5 天）：端到端测（星台 ↔ mac-mini 星桥 / MBP 总线切换）

### 风险
- MBP/i9 总线在线性（离线目标不可选——注册表心跳过滤）
- 各设备总线的「对话处理」语义需对齐（谁收谁回）

## 用户需求记录（全部已纳入/规划）
1. ✅ 文字+语音对话（iPhone/iPad/mac）
2. ✅ 语音按住→实时识别→可编辑→确认发送（防普通话歧义）
3. ✅ 聊天记录持久化（重装不丢）
4. ✅ 键盘可收起
5. ✅ 队列显示（修复为真实负载）
6. ✅ 公网可达（Funnel）
7. 📋 多设备对话目标切换（v9.3）
8. 📋 图标（已生成待装）

---
## v9.3/v9.4 实况登记（2026-09-04 星桥实测）
### v9.3 多设备切换 — 已完成（M1/M2/M3，M4 待装后真机测）
- M1 桥路由层 ✅：/api/devices（nodes/* 心跳 <90s = 在线，含 mac-mini/mbp/i9 实测）+ /api/chat 支持 target（mbp→notes/mbp/sb-dialog-<ts>-task / i9→notes/i9/sb-dialog-<ts>-task）
- M2 MBP 接收 ✅ 意外全通：mbp-bus 泛化消费 -task 任务卡 → 实测回报写 notes/mac-mini/mobile-reply/latest-mbp（含真实回复文本），链路 桥→黑板→MBP→回报→latest-mbp 端到端通
- M3 App UI ✅：标题栏 Menu 设备选择（星桥本机/MBP/i9）+ 每目标独立会话历史（Documents/chat-history.json 分 key）+ 独立轮询（session=target）+ 目标记忆（UserDefaults）
- M4 端到端：待 iPhone/iPad 装 v9.4 后真机验证（桥侧已实测通）
### v9.4 语音 LLM 纠错 — 已完成（用户选定「后端 LLM 纠错」）
- 桥 /api/correct：POST {text} → ollama qwen2.5:3b（127.0.0.1:11434）→ {corrected}
- 领域专名强制纠正：新桥/心桥→星桥；新台→星台；老灯→老登；驿史→驿使
- App：松开语音 → 原文先填入 → Task 调 /api/correct → 纠错文本替换（仍可编辑）
- 实测：新桥→星桥 3.2s ✅；双平台编译 SUCCEEDED
### 待办
- i9 通道确认（probe 已发 notes/i9/sb-dialog-probe-*，等 i9 回复消费机制/回报格式）
- 真机安装 v9.4（iPhone 16 Pro 8E2B135D + iPad A30F685B）——用户指示：等 i9 通道确认后一次性装
- 桥测遗留卡清理（notes/mbp/sb-dialog-* + notes/i9/sb-dialog-* 测试卡，确认 i9 机制后归档）
