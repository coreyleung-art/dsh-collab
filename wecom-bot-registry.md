# 企微机器人通道登记表（汇总管理）

外链通讯员 92623479 · 2026-08-21 · 维护

## 一、已连接机器人清单

| # | 机器人名 | Bot ID | 通道模式 | 职责 | 关联服务 | 状态 |
|---|---|---|---|---|---|---|
| 1 | **CLD-Mac** | aibLaCPfTgYtVzD3OyEsyUyzlyyGDglchIU | 长连接（openws） | 外链主通道：单聊/群聊消息采集 + 确认回复 + 办公模块（todo/日历/文档）+ 外发推送 | wecom-inbox.js（长连接监听）+ wecom-cli（@wecom/cli v1.1.0）+ external-link-mcp（8910） | ✅ 运行中 |

## 二、通道配置详情（CLD-Mac）

| 项 | 值 |
|---|---|
| Bot ID | aibLaCPfTgYtVzD3OyEsyUyzlyyGDglchIU |
| 长连接 Secret | ~/.config/wecom/credentials.enc（AES-256-GCM + .encryption_key，0600） |
| 长连接端点 | wss://openws.work.weixin.qq.com |
| 监听进程 | wecom-inbox.js（PID 50028，单聊 J38 确认 + 群模式 A/B/C/X） |
| CLI | @wecom/cli v1.1.0（办公模块 todo/calendar/doc 等，绕过 853006） |
| MCP | external-link-mcp 8910（channel.send/status + bus.send + office.* 6 工具） |
| 用户单聊 chat_id | woObL9WAAARafD5zf5gFiLz_Ry3JUsnw（梁振宇 Corey） |
| 已接入群 | AI广播测试群（wrObL9WAAA...，模式 A 仅@回复） |

## 三、多机器人协调规则

### 1. 职责划分（一机器人一主职责）
| 机器人 | 主职责 | 副职责 |
|---|---|---|
| CLD-Mac | 外链统一通道（消息/群聊/办公/推送） | 群聊监听（四态模式） |

> 新增机器人时：明确主职责，避免两个机器人监听同一会话导致重复响应。

### 2. 长连接互斥
- 每个机器人同一时间**只能一个长连接**（新连接踢旧连接）——确保每个机器人只有一个 wecom-inbox 实例
- 多机器人并行 = 多个独立长连接，互不干扰

### 3. 消息路由
- 外部消息到达 → 按内容/来源路由对应 agent（预订单→运营 aa528267、客服类→b193c782、业务咨询→用户本人确认）
- 机器人收到消息 → 先确认（J38）→ 路由处理 → 结果回发

### 4. 凭据管理（安全）
- 每机器人独立凭据（Bot ID + Secret），0600 私有文件，不跨网明文
- 新增机器人：credentials.enc 增加条目或独立文件

### 5. 新增机器人接入流程（J42/J44）
1. 后台创建机器人 → 开 API 模式 + 长连接
2. `wecom-cli auth init` 配置凭据
3. 登记本表（名称/Bot ID/职责/服务）
4. 挂载对应服务（wecom-inbox 实例 / CLI 调用）
5. 验证（auth show + 模块实测）→ QA

## 四、其他通道（非企微）

| 通道 | App ID | 状态 | 说明 |
|---|---|---|---|
| 飞书 | cli_aa0842c3b1b99cb1 | ⏳ bound 待 secret | secret 待用户本人扫码（keychain） |

## 五、更新日志

- 2026-08-21：建表，登记 CLD-Mac（主通道）+ 协调规则 5 条
