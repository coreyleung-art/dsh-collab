# 星台（StarBridge Mobile）· SwiftUI 原生技术路径 v0.2

> 用户决策：iOS 先 / SwiftUI 原生 / 命名「星台」/ TTS=P0 系统 AVSpeechSynthesizer（P1 火山升级）

## 架构（与 v0.1 同，UI 层换 SwiftUI 原生）

```
iPhone App（SwiftUI 原生聊天 UI）
  │  Tailscale（Funnel https://coreymac-mini.taild3fd86.ts.net/ 或直连 100.120.203.20）
  ▼
mac-mini 对话桥 :8820（Node）—— token 鉴权/写黑板/读回复/ASR 转发
  ▼
黑板 notes/mac-mini/mobile-inbox + mobile-reply
  ▼
bb-sub.coordinator → 星桥会话（已订阅，链路现成）
```

## 组件
| 组件 | 实现 |
|------|------|
| App | SwiftUI 原生（iOS 17+，Xcode 26）：聊天列表/消息气泡/按住说话/录音波形/回复播放 |
| 对话桥 | ~/sb-mobile/server.js（Node 零依赖，复用 laodeng asr-server 模式） |
| 语音输入 | AVFoundation AVAudioEngine 录音 → webm/wav → POST 桥 → 火山 ASR（key 留 mac） |
| 语音回复 | P0: AVSpeechSynthesizer（系统 TTS 零成本）→ P1: 火山 TTS 音色 |
| 注入链路 | 黑板 notes/mac-mini/ → bb-sub → 星桥（现成） |
| 网络 | Tailscale Funnel/直连 |

## 步骤（SwiftUI 原生版，P0 ≈ 4-5 天）
### Step 1 · 对话桥 server.js（0.5 天）——不依赖 UI，先做
- POST /api/chat（token+text）→ 写黑板 inbox → {ok}
- GET /api/reply?since → 读 reply（App 轮询 1s 或 SSE）
- POST /api/asr（音频→火山→文本）
- POST /api/tts（文本→音频，P1 火山预留；P0 App 端系统 TTS 不需要）
- launchd 托管（bootstrap 验证——kickstart 教训）

### Step 2 · 注入-回复闭环验证（0.5 天）
- curl 模拟 App：POST chat → 验证 bb-sub 注入星桥 → 我回复 → GET reply 读到
- 端到端（R021）

### Step 3 · SwiftUI 聊天 UI（1.5-2 天）
- Xcode 工程：星台.xcodeproj（iOS 17，无 Storyboard 纯 SwiftUI）
- 视图：MessageList（气泡/时间）/ Composer（TextField+录音按钮按住说话）/ 连接状态
- 网络层：URLSession POST chat + 轮询 reply；ASR/回复播放集成
- Tailscale 直连 URL 配置（Info.plist ATS 放行 https）

### Step 4 · 语音链路（0.5 天）
- AVAudioEngine 录音 → POST /api/asr → 文本入对话
- AVSpeechSynthesizer 播报我的回复

### Step 5 · 真机实测（0.5-1 天）
- 模拟器（iPhone 17）+ 真机（Apple 证书，老登 device 构建模式）
- 语音「查今天评价」→ 星台 → 星桥 → 分派老登 → 回复 + 语音播报

## P1（火山 TTS 音色 + 结果推送 + 确认卡）
