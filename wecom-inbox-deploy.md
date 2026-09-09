# 群聊监听部署文档（wecom-inbox）

> 维护：外链通讯员 session-92623479 · 2026-08-17
> 状态：已批准开工，待「订阅 Secret」后一键启动
> 用户指令：全量静默观察 → 数据沉淀分类 → 进知识库闭环 → 找用户拿判断/人工提权

---

## 一、功能

- WebSocket 长连接（@wecom/aibot-node-sdk v1.0.7）接收企微群/单聊消息
- 全量采集 → SQLite（~/.dsh/wecom-inbox.db）
- 群级四态模式：A 仅@回复 / B 半主动介入 / C 全量参与 / X 静默观察（默认）
- 新群检测 → 发「模式选择」消息（默认 X）
- 模式 X：只收数据不说话（最克制，符合用户「谨慎」价值观）

## 二、数据库

```
~/.dsh/wecom-inbox.db
├── messages    # 全量消息（chat_id/发送者/内容/类型/时间/topic/mode）
└── group_modes # 群级模式（chat_id/mode/asked_at）
```

## 三、启动命令（Secret 注入后）

```bash
cd ~/external-link-mcp
NODE_TLS_REJECT_UNAUTHORIZED=0 \
WECOM_BOT_ID="aibLaCPfTgYtVzD3OyEsyUyzlyyGDglchIU" \
WECOM_SECRET="<订阅Secret，企微后台获取>" \
node wecom-inbox.js
```

> NODE_TLS_REJECT_UNAUTHORIZED=0 必须（沙箱 TLS 证书链问题，与 coze-bridge 同坑）

## 四、订阅 Secret 获取路径（用户操作，1 分钟）

企微 App/后台 → 工作台 → 智能机器人 → 「梁振宇的机器人」→ 编辑 → 订阅/连接配置 → WebSocket 订阅 Secret（或连接密钥）

> ⚠️ 与 wecom-cli 的 CLI 凭据不同源（实测 CLI secret 认证 853000 失败）——必须用后台的订阅 Secret

## 五、模式切换

群里回复：`选 A` / `选 B` / `选 C` / `选 X` 即时切换（群级生效）

## 六、故障排查

| 症状 | 原因 | 修复 |
|------|------|------|
| unable to get local issuer certificate | 沙箱 TLS | NODE_TLS_REJECT_UNAUTHORIZED=0 |
| 853000 invalid bot_id or secret | Secret 不是订阅 Secret | 换后台订阅 Secret |
| 853006 tool not available | 企业规模限制（出向 send 用 aibot 通道绕过） | 无碍监听 |
| WebSocket 断开自动重连 | SDK 内置 | 指数退避，最多 10 次 |

## 七、后续增强（数据沉淀后）

- 话题分类层：message.topic 填充（差评/订单/价格/闲聊）
- 规律摘要：聚合高频话题/时段 → ~/dsh-collab/wecom-intel/
- 人工提权：监察到应介入话语 → 提权卡片 @用户核对
- 知识库闭环：规律摘要 → DSH KB（语义检索）

---

*部署文档 v1.0 —— 待订阅 Secret 即上线*
