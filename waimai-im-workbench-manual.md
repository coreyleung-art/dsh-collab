# 美团商家 IM 工作台操作手册（DOM 结构 · 选择器 · 采坑实录）

> 作者：session-de7b29de（外卖门店多平台管理）· 日期：2026-08-16
> 来源：真实环境实测（6 美团店双窗口 + IM 会话遍历 + 方向分类 + 消息清洗全链路）
> 用途：供 Dify KB 收录 / ChromaDB 索引 / 其他会话做美团 IM 自动化时取用

## 1. 环境与入口

- **IM 工作台 URL**：`https://shangoue.meituan.com/imworkbench/home?appId=4&clientType=150006#/im/page/workbench/reception`
- 商家首页：`https://shangoue.meituan.com/`（闪购商家端）
- 登录态：与商家首页同 profile 同 cookie，同一 Chrome 实例内可直接打开
- **双窗口模型**（本项目实践）：商家首页 + IM 工作台各自独立窗口（`Target.createTarget(url, {newWindow:true})`），同登录态并行监控——商家页管订单快照，IM 页管客户消息

## 2. DOM 结构

### 2.1 会话列表（「全部接待」tab）

```
sessionListItemContainer_*          ← 会话项容器（可点击）
└─ sessionListItemNormal_*          ← 正常态（Active 时带 sessionListItemActive）
   ├─ userinfoTopinfo_*             ← 首行：订单标识 + 客户名
   │  ├─ userinfoUsername_*         ← 「8.13#13单 L**」（唯一 key，稳定）
   │  ├─ userTag_*                  ← 「已下1单」标签
   │  └─ userinfoChattime_*         ← 「21:08」
   └─ userinfoBottominfo_*          ← 末行：最后消息预览
      └─ userinfoLastchat_*         ← 「好的」（预览文本）
```

### 2.2 消息气泡（点开会话后）

```
message-wrapper left-message        ← 客户消息（左侧）
└─ ... im-card_text-message-wrapper
   └─ im-card_text-message          ← 纯文本内容

message-wrapper right-message       ← 店员/商家消息（右侧）
└─ ... im-card_text-message-wrapper
   └─ im-card_text-message          ← 纯文本内容
```

- 系统提示（非气泡）：`im-card_event-message`（如「用户长时间未回复，会话已自动结束」）
- 时间戳：`im-card_timestamp-message`
- 已读标记：`message-read`

## 3. 关键选择器（config.json selectors.im）

```json
{
  "im": {
    "messages": "[class*='im-message'], [class*='chat-bubble'], [class*='message-item'], [class*='im-msg']",
    "session": "[class*='sessionListItemContainer'], [class*='sessionListItemNormal'], [class*='session-item'], [class*='conversation-item']",
    "tab_all": "全部接待"
  }
}
```

注意：类名带 hash 后缀（`_ZL2hpS`），**每次发版可能变**——用 `[class*='语义名']` 前缀匹配而非全类名。

## 4. 采坑实录（重要）

### 4.1 点击会话后列表重排 → 必须用 key 匹配，禁止下标
点开会话后列表会重排（活跃会话置顶/移走），`items[i]` 索引会错位——第二次取 `[i]` 可能还是同一个会话。
✅ 方案：用 `userinfoUsername` 文本（如「8.13#13单 L**」）做会话 key，点击前按 key 查找。

### 4.2 气泡方向 = message-wrapper 的 left/right，自动回复标记在外层
- 方向：`message-wrapper` 的 class 含 `left-message`（客户）/ `right-message`（店员）
- **自动回复 `[自动回复]` 标签在外层 wrapper 的 innerText，不在内层 text-message**——只取内层文本会丢失 auto 标记，导致「自动回复被误判为人工回复」

### 4.3 会话预览带前缀与噪声
- 预览文本：`「今日#28单 J**:您的花花做好啦…」`——需剥离 `今日/昨日/昨天/前天 #N单 客户名:` 前缀
- 平台通知：`「您有一条发票申请超过24h未处理～」`——非客户消息，应过滤（关键词：发票/申请超过/系统通知/自动回复/配送通知/物流/未处理～等）
- 波浪号是全角 U+FF5E（～），正则匹配注意字符集

### 4.4 空气泡（图片/引用/系统卡）无 text-message 内层
`querySelector("[class*='text-message']")` 返回 null 的气泡直接跳过，否则会把客户名（如 `k**`）当成消息内容。

### 4.5 遍历会话的性能与干扰
- 逐会话点开读气泡：每个约 1.4s 等待渲染，20 会话 ≈ 28s——**必须分批**（本项目每 tick 3 个，游标轮转覆盖全部）
- 事件流与详情采集分离：列表预览（不点开）做事件信号，详情按需点开——避免互相干扰

### 4.6 Chrome 保渲染
- 窗口**移出屏幕**（`Browser.setWindowBounds left:-4000`）而非最小化——最小化冻结真实页面渲染，截图会超时
- `--no-startup-window` + `Target.createTarget(newWindow:true)` 创建页面；关窗保活 `--enable-background-mode`

## 5. 消息清洗规范（cleanMsg 流程）

1. 剥离日期前缀：`今天/昨天/前天 HH:MM(:SS)`、`YYYY-MM-DD HH:MM`、`MM-DD HH:MM`、`HH:MM(:SS)`
2. 剥离称呼前缀：`客户/顾客/客人/用户/对方/买家/店主/商家：`
3. 剥离 `[自动回复]` 括号标签
4. 剥离尾部 `未读`
5. 剥离会话预览前缀：`(今日|昨日|昨天|前天|MM-DD)#N单 客户名 [状态] HH:MM`
6. 过滤平台通知句式（发票/申请超过/系统通知/自动回复/配送通知/物流/未处理～等）
7. 截断 200 字符

## 6. 事件模型（本项目消费方）

| 事件 | 触发 | payload |
|---|---|---|
| customer_msg | 会话预览变化（8s 节流） | `{msgs:[纯消息], count, last}` |
| sound_alert | 页面音频 | `{src, kind:customer/order/notice, msg:最后客户消息}` |
| im_sessions（表） | 每 tick 分批采集 | `{session_key, last_client_msg, last_staff_msg, status: pending/replied/done, detail.timeline}` |

## 7. 扩展建议（给后续会话）

- **自适应选择器**：DOM 语义锚点（角色/文本特征）优先，hash class 兜底；留存历史版本快照
- **待回复判定**：客户最后消息之后无**人工**回复（自动回复不算）→ pending
- **精确方向数据**：`/api/im/replies` 的 `detail.timeline` 带 `{dir: client/staff, auto}` 标记
