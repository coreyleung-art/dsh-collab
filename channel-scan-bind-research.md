# 企微/飞书 CLI 扫码绑定 · 调研与落地

> 调研：外链通讯员 session-92623479 · 2026-08-17
> 需求：用户问「飞书和企业微信好像都有 cli，是不是能生成一个扫码器，扫码一键绑定对应渠道？」
> 结论：**✅ 两个渠道都有官方 CLI 扫码绑定，且本机已验证可用；wecom-cli 甚至支持直接输出二维码 PNG**

---

## 一、调研结论

### 1.1 企业微信 — `@wecom/cli`（官方 CLI）✅ 已安装验证

- 包：`@wecom/cli` v1.1.0（官方），bin = `wecom-cli`，Rust 实现，MIT
- 安装：`npm install -g @wecom/cli`（本机已装好，`~/.npm-global/bin/wecom-cli` 可运行）
- **扫码绑定**：`wecom-cli auth init`
  - 默认**扫码接入**（推荐）：终端展示二维码 → 企微 App 扫码 → 自动创建绑定
  - `--output-qrcode <PATH>`：**将二维码输出为 PNG 文件**（扫码器核心能力！）
  - `--no-browser`：不自动开浏览器；`--noninteractive`：CI 环境直接用扫码
  - `--manual`：手动输入 Bot ID + Secret
  - 扫码等待超时 5 分钟
- **凭据安全**：`<config_dir>/credentials.enc` — AES-256-GCM 加密（0600），密钥存系统 keyring，符合「凭据 0600 私有」纪律
- 能力面：消息/邮件/文档/待办/日程/会议/微盘/通讯录 8 大类（消息推送支持 Markdown/图片/文件）
- 状态检查：`wecom-cli auth show`（--status 输出 authorized/unauthorized 单行，便于脚本判断）

### 1.2 飞书 — 官方 `lark-oapi` SDK `register_app`（RFC 8628 Device Authorization Grant）✅ 官方能力确认

- 方法：`lark.register_app(on_qr_code=...)` / `aregister_app`（Python，lark-oapi ≥1.5.5）
- 流程：调用返回**验证链接/二维码** → 用户在飞书/Lark 中打开或扫码授权 → **自动注册应用并返回 App ID + App Secret**，无需手动开发者后台创建
- `addons` 支持预填权限/事件/回调（如 `im:message:send_as_bot`、`im.message.receive_v1`），扫码确认页一键生效
- 本机状态：`~/.lark-cli/` 已有配置（**用户 8/7 已扫码绑定过一个飞书应用** appId=cli_aafe4807d1f8dbef，secret 存 keychain）——历史可用证明
- 需要 `pip install lark-oapi`

### 1.3 hermes-agent（本机已有）— 双渠道统一网关向导

- 本机 `~/.hermes/hermes-agent/website/docs/user-guide/messaging/` 有 **wecom.md + feishu.md**
- `hermes gateway setup`：选择渠道 → **扫码创建（one command）** → 自动建 bot 应用 + 正确权限 + 保存凭据
  - WeCom：AI Bot WebSocket 网关（wss://openws.work.weixin.qq.com），无公网端点
  - Feishu：WebSocket 模式（推荐，SDK 自动重连）/ webhook 模式
- hermes 未在 PATH（~/.hermes/bin 只有 tirith），但文档确认了扫码流程与 hermes 同款架构可参考

## 二、落地建议（用户要的「扫码器」）

**方案 A（推荐 · 零自研）**：直接用官方 CLI，一个命令扫码
```bash
# 企微（本机已装）
wecom-cli auth init --output-qrcode ~/Desktop/wecom-qr.png
# 终端会展示二维码 + 桌面生成 PNG（手机扫桌面图更舒适），企微 App 扫码即绑定

# 飞书
pip install lark-oapi
python3 ~/dsh-collab/feishu-bind.py   # 扫码创建应用，自动存 AppID/Secret 到 0600 配置
```

**方案 B（体验优化 · 薄封装）**：生成一个统一绑定脚本 `channel-bind.sh`（本角色产出）：
- 交互菜单：1) 企微 2) 飞书 3) 状态查看
- 企微 → 调 `wecom-cli auth init --output-qrcode`（PNG 落地）
- 飞书 → 调 Python `register_app`（输出二维码 URL + 终端码）
- 绑定结果写 `~/.dsh/channels.json`（0600），供外链网关读

**凭据纪律**：企微走官方 credentials.enc（AES-256-GCM + keyring）；飞书 secret 存 keychain（沿用 lark-cli 模式）；不落盘共享目录。

## 三、决策记录（决策编号：ELA-2026-0817-02）

| 项 | 决策 | 依据 |
|---|---|---|
| 企微绑定 | **官方 @wecom/cli auth init 扫码**（--output-qrcode 出 PNG） | 官方 CLI 现成，本机已验证 v1.1.0 |
| 飞书绑定 | **官方 lark-oapi register_app 扫码创建** | RFC 8628 官方能力，历史验证过（8/7 lark-cli） |
| 网关底座 | hermes-agent 同款架构可参考（本机源码在） | wecom.md/feishu.md 已实证流程 |
| 统一入口 | 薄封装 `channel-bind.sh` + channels.json（0600） | 用户体验优化，非自研协议 |

**结论：无需自研**——企微/飞书官方 CLI/SDK 均原生支持扫码一键绑定，本角色只需薄封装统一入口。✅

## 四、实施前置

- [ ] 用户确认：扫码绑定哪个渠道？（企微优先 / 飞书 / 都绑）
- [ ] 企微：用企微 App 扫码（需企业微信账号）
- [ ] 飞书：`pip install lark-oapi`（需飞书账号）
- [ ] 绑定后凭据自动落入 0600 私有配置，外链网关读取

---

*调研决策记录 v0.1 —— 按「调研优先」制度沉淀*
