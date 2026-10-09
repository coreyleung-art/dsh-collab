# CLD-Voice 协议 v1（WS 文本帧 + 二进制 PCM）

> 2026-09-10 · voice-service :8905 / 成稿引擎 :8902

## 传输
- 服务端：`ws://127.0.0.1:8905`（WebSocket 文本帧为主 + 二进制音频包）
- 鉴权（可选）：`X-Voice-Token` header（服务端 `--token` 配置）

## client → server
| 类型 | 载荷 | 说明 |
|------|------|------|
| 二进制帧 | 16k PCM Int16（~128ms/包） | 麦克风音频（每包 `2048`samples ≈ 128ms） |
| `{"type":"commit"}` | - | 强制端点判定（你说完）→ 模型开口 |
| `{"type":"cancel"}` | - | 打断本轮 `response.cancel` |
| `{"type":"close"}` | - | 结束会话 |

## server → client
| 类型 | 载荷 | 说明 |
|------|------|------|
| `ready` | `{sid}` | 会话建立 |
| `transcript_delta` | `{delta}` | 你说话转写增量（LCP 去重） |
| `text_delta` | `{delta}` | AI 文本流式逐字 |
| `text_done` | `{text}` | AI 文本完成 |
| `audio_delta` | `{audio}` | AI 语音 24k PCM s16le，**base64，每片独立**（勿整段拼接解码） |
| `audio_done` | - | 本轮 TTS 结束 |
| `done` | - | 本轮结束 |
| `err` | `{msg}` | 错误 |
| `closed` | - | 连接关闭 |

## 注意事项（踩坑）
1. **audio_delta 逐片解码**：每片 base64 各自带 `=` padding，整段拼接后一次 `atob` 会抛 `Invalid character`。
2. **回声用硬件 AEC**：`getUserMedia({echoCancellation:true})`，不要给模型喂静音。
3. **播放单 buffer**：避免多段 `start()` 的接缝/异音。超长(>45s)才切块。
4. **打断**：`transcript_delta`(用户又说话) 时若仍在播 → 停旧音源 + 发 `cancel`。
5. **TTS 兜底**: 火山 Seeduplex 偶发只回文字(audio bytes=0)。bridge 已在 `response.done` 时, 若 0 音频但有文字, 自动 `speech_text_buffer.commit` 强制合成语音。兜底 TTS 较慢(~10s 后到达), 客户端需保持会话监听。

## HTTP API（voice-service :8906）
- `GET /v1/health` → `{ok, active_sessions}`
- `GET /v1/stats` → `{active, sessions[]}`

## 成稿引擎（asr_server :8902）
- `POST /api/draft` `{discussion:[{role,ts,text}], title}` → `{success, id, title, content, stats}`（LLM 主动提炼）
- `GET  /api/drafts` → 草稿列表

## 版本
- 协议 v1 · voice-service v1.2.0 · 成稿引擎 v1.1.0
