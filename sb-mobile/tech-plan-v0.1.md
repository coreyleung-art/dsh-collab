# 星桥移动壳 · 完整技术实现路径（v0.1）

> 定位：用户私人星桥对话通道——手机 App 语音/文字连回星桥（mac-mini），星桥理解后指挥全网智能体
> 原则：薄壳（App 只做对话入口，调度全在星桥）+ 只连星桥 + Tailscale 私有网络 + 复用现有组件

## 一、总体架构

```
手机 App（WKWebView 壳 或 SwiftUI）
  │  Tailscale（Funnel https://coreymac-mini.taild3fd86.ts.net/ 或 直连 100.120.203.20）
  ▼
mac-mini 星桥对话桥（轻量 Node 服务 :8820）
  │  ① token 鉴权 ② 写黑板 ③ 读回复（SSE/轮询）
  ▼
黑板 notes/mac-mini/mobile-inbox/<ts>.json（消息入）
  ▼
bb-sub.coordinator（已订阅 notes/mac-mini/）→ SSE 注入星桥会话
  ▼
星桥（我）收到 → 理解 → 指挥（agent-bus/黑板 分派老登/明鉴/i9/驿使…）
  ▼
回复写黑板 notes/mac-mini/mobile-reply/<ts>.json（或直接 SSE 推 App）
  ▼
App 显示 →（可选 TTS 播报）
```

## 二、组件清单与复用

| 组件 | 实现 | 复用/新建 |
|------|------|----------|
| App 壳 | WKWebView 包星桥对话页（老登 ios-shell 同模式：main.swift + Assets + build.sh swiftc 直编） | ✅ 复用 ios-shell 骨架改 URL/图标/名 |
| 对话 UI | HTML 聊天页（消息列表+输入框+语音按钮+流式显示） | 新建（简单单页） |
| 对话桥 | Node HTTP :8820（鉴权→写黑板 inbox→读 reply） | 新建（参照 asr-server 模式） |
| 注入链路 | 黑板 notes/mac-mini/ → bb-sub.coordinator → 星桥 | ✅ 已存在（订阅已含 notes/mac-mini/） |
| 语音 ASR | 手机录音→桥转发→火山 ASR（key 留 mac-mini） | ✅ 复用火山链路（key 在 mac 不落 App） |
| TTS（P1） | 火山 TTS or 系统 AVSpeechSynthesizer | P1 决定 |
| 网络 | Tailscale Funnel（外网）或直连 | ✅ 已通（Funnel 200 实测） |

## 三、实现步骤（P0 MVP：文字+语音输入对话）

### Step 1 · 对话桥（mac-mini，0.5 天）
- 新建 ~/sb-mobile/server.js（Node 零依赖 http）
- API：
  - POST /api/chat {token, text} → 写黑板 notes/mac-mini/mobile-inbox/<ts>.json → 返回 {ok}
  - GET /api/reply?since=<ts>（App 轮询）或 SSE /api/stream → 读 notes/mac-mini/mobile-reply/*
  - POST /api/asr（multipart 音频→转发火山→文本）——或复用老登 asr
- 鉴权：token（0600 配置，App 内存储，Tailscale 内传输）
- launchd 托管（参照 lark-notes 模式，bootstrap 验证注册）

### Step 2 · 注入-回复闭环验证（0.5 天）
- 桥写 inbox → 验证 bb-sub 注入星桥（我会收到）→ 我回复 → 桥读 reply → 闭环
- 关键验证：端到端（桥→我→回复→桥）——R021 教训

### Step 3 · 对话 UI + WebView 壳（1 天）
- HTML 聊天页：消息气泡/输入/录音按钮（MediaRecorder）/流式回复
- iOS 壳：复制老登 ios-shell → 改 app 名（星桥/StarBridge）+ 图标 + URL（https://coreymac-mini.taild3fd86.ts.net/sb/ 指向对话页）
- build.sh sim（模拟器验证）+ device（真机，Apple 证书）

### Step 4 · 语音链路（0.5 天）
- App 录音（MediaRecorder webm）→ 桥 POST 火山 ASR → 文本 → 对话
- 复用老登 asr-server 火山逻辑（key 0600）

### Step 5 · 端到端实测（0.5 天）
- 模拟器/真机：语音「教师节补报决定了吗」→ 桥 → 星桥收到 → 分派 → 回复显示
- 安全复核：token 不落库/日志脱敏/Tailscale 设备绑定

**P0 合计：约 3 天**（实际可压缩，复用多）

## 四、P1/P2（后置）
- P1：TTS 语音回复（火山/系统）+ 执行结果主动推送（桥 SSE → App 通知）+ 高险操作确认卡（我分派 L3 前 App 弹确认——R026 精神）
- P2：多会话（App 端线程管理）+ 原生 SwiftUI UI + 安卓（PWA 备选：无 SDK）

## 五、风险与决策点
| 风险 | 缓解 |
|------|------|
| 对话桥写黑板→注入星桥的延迟/失败 | 端到端验证先行（Step 2）+ 桥写后读回确认 |
| 我回复的「上下文」= 单会话累积 | MVP 单会话（我记上下文）；App 发 /clear 重置可选 |
| token 安全 | Tailscale 私有网 + token 0600 + 不落日志 |
| 火山 ASR key | 只存 mac-mini（App 不持 key） |
| Funnel 依赖 mac-mini 在线 | 直连 Tailscale 备选 + 断线提示 |

## 六、需用户决策
1. 命名：星桥移动端 / StarBridge / 星台
2. UI：MVP 用 WebView 包 HTML（快）→ 后续原生？或直接 SwiftUI？
3. 平台：iOS 先（证书有）？安卓 PWA？
4. 语音回复 TTS：P0 还是 P1？
5. P0 目标：3 天可交付——今晚开始？
