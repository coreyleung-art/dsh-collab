# CLD-Voice 内嵌插件设计（悬浮球形态 · 快速语音会议记录）

> 2026-09-10 · mbp-bus · 实测工作版本 v0.3.9
> 复用 A(独立 App) 已验证的 Seeduplex 全双工能力 → 内嵌进 CLD 会话

## 形态（最终落地）
**悬浮球**（不是老的 dock/overlay 组合——那些会挤压 conversation 布局，G6 教训）。

- 🎤 悬浮球：`ReactDOM.createPortal(..., document.body)` 挂载 → **脱离布局流**，fixed 可拖拽，不遮挡。
- 点击展开「语音会议记录」面板：●说话 / ⏹停止 / ✅完成注入。
- ✅完成注入 → `inputActions.setDraft + submit` 把成稿作为消息发进当前活跃会话（无需黑板/agentBus 中转，已实证）。

## 架构（当前工作状态）
```
CLD 悬浮球 🎤 ──ws──▶ voice-service:8905 ──▶ 火山 Seeduplex 全双工
   ├─ 转写/文本流式 → 面板显示 (portal 挂 body)
   └─ ✅完成注入 → host /voice/draft → 8902 成稿 → inputActions.setDraft+submit 进当前会话
```

## 关键组件
| 部分 | 内容 |
|------|------|
| host (`lib/index.js`) | `POST /voice/draft`(转发 8902 成稿) + `/voice/health` + `/voice/test`(诊断). `inject:['webServer']` + `webServer.register({kind:'exact',path,handler})` |
| client (`lib/client.js`) | 悬浮球组件 + 全双工引擎. `inject:['slots']` + `createPortal` 挂 body |

## 客户端引擎要点（v0.3.x 踩坑已修）
1. **逐片解码**：每个 `audio_delta` 分片的 base64 各自带 `=` padding，整段拼接后一次 `atob` 会抛 `Invalid character` 丢 40万+ 字节 → 改为**每片单独解码**累积 Float32。
2. **单 buffer 无缝播放**：不再按 2s 切块多 `start()`（会产生接缝/异音感，用户听到"多把声音"）；整段一次性播放，仅超长(>45s)才切块。
3. **打断即停**：`transcript_delta`(用户又说话) 时若仍在播 → `_stopPlayback()` + 给桥发 `{"type":"cancel"}`；`flushAi` 开播前也先停旧源（防叠音）。
4. **播放前 resume**：`ensurePlay()` 在用户手势(点●)里同步 `create+resume`；`flushAi` 播放前再 resume 一次兜底 autoplay。
5. **回声**：用 `getUserMedia({echoCancellation,noiseSuppression,autoGainControl})` 硬件 AEC，**不**给模型送静音（送静音会干扰模型对用户语音的判断，诱发"只回文字没语音"）。
6. **诊断面板**：实时显示 `收KB / 播次 / ctx状态 / ⚠错误`，便于二分定位。

## 桥端口
- **voice-service.py :8905**（产品化内核，WS）+ :8906（HTTP 健康/stats）。
- duplex_bridge.py 现在是 voice-service 的内核（`core.pump`），**不再独立监听 8904** 作为主入口（旧端兼容可后补）。

## 依赖
- 火山 `VOLC_ASR_API_KEY`（Seeduplex 1.2.6.0 全双工）
- Python venv：`~/.dsh-collab/cld-voice/backend/venv`（websocket-client）
- launchd：`com.dsh.voice-service`(8905) + `com.dsh.cld-voice`(8902) 常驻

## 开发门（G1–G6）
对照先例 → 严格模拟 → R006 补齐 → 沙箱试载 → 才碰真实 CLD → 真机布局核验（G6 新增：防止浮层/组件挤压布局）。
