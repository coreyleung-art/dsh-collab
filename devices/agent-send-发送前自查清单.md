# agent_send 发送前自查清单（v2.3 · 防违规于未然）

> 用法：**每次调用 agent_send 前**，先跑一遍校验器 + 过自查清单
> 校验器：python3 ~/dsh-collab/scripts/bb-send-check.py --text "要发的消息"

## 一、强制流程（每次发送前）

```
[要发 agent_send]
   │
   ├─ 跑校验器: python3 bb-send-check.py --text "<消息>" --json
   │    │
   │    ├─ verdict=pass → 直接发 ✅
   │    │
   │    └─ verdict=warn → 先做修正：
   │         └─ 内容写黑板（notes/mac-mini/ 或 data/<域>/）
   │              → 再发『看黑板 <key>』
   │
   └─ 自查 3 问：
       ① 这是回报/通知/待办提醒吗？ → 是 → 内容必须写黑板
       ② 内容已在黑板了吗？ → 未在 → 先 PUT 黑板
       ③ 是紧急吗？ → 否 → 短提示；是 → ≤200字 + urgent 标记
```

## 二、自查 3 问（prompt 内嵌版）

**Q1: 这条消息是什么类型？**
- 回报/通知/待办提醒 → 写黑板 + 短提示
- 业务对话（协作讨论）→ 可 agent_send 但尽量简短
- 紧急（立即行动/决策）→ ≤200 字 + urgent

**Q2: 内容是否已在黑板？**
- 未写 → 先 PUT 黑板（notes/<收件人>/ 或 data/<域>/）
- 已写 → 只发『看黑板 <key>』

**Q3: 这条 agent_send 应该多短？**
- 目标 ≤50 字（最短提示）
- 上限 ≤200 字（带一句话提示的短提示）
- >200 字 → 必违规，重写

## 三、违规代价（v2.2 门禁）

- agent-send-gate 每 5 分钟扫：>200 字且无黑板引用 → 违规记录 + 提醒
- 违规 3 次 → 中枢点名 + 强化培训

## 四、校验器速查

```bash
# 校验是否该发
python3 ~/dsh-collab/scripts/bb-send-check.py --text "消息文本"

# 校验 + 指定收件人
python3 ~/dsh-collab/scripts/bb-send-check.py --text "消息" --to session-xxx

# 脚本集成（JSON 输出）
python3 ~/dsh-collab/scripts/bb-send-check.py --text "消息" --json
```

## 五、核心原则

**agent_send = 唤醒通道，不是汇报通道。**
内容在黑板上（可追溯/审计），agent_send 只告诉对方「去看黑板」。
