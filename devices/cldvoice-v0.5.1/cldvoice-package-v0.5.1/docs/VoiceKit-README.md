# VoiceKit · 语音交互内核 v1.1.0

> 产品化形态的 CLD-Voice 内核（L1 服务 + L2 SDK + L3 场景）
> 2026-09-10 · mbp-bus · 源项目: CLD-Voice（~/dsh-collab/cld-voice/）

## 组件
| 组件 | 路径 | 端口 | 说明 |
|------|------|------|------|
| voice-service.py | backend/voice_service.py | **8905** WS / 8906 HTTP | 产品化内核服务(多会话+健康+stats) |
| duplex_bridge.py | backend/duplex_bridge.py | *内核* | Seeduplex 全双工内核, 被 voice-service 复用(core.pump); 不再独立 8904 主入口 |
| asr_server.py | backend/asr_server.py | 8902 | 成稿引擎(LLM 主动提炼)/UI(独立App用) |
| voice-sdk.js | sdk/voice-sdk.js | - | 跨端接入库(浏览器/Electron) |
| demo.html | sdk/demo.html | 8910 | 接入示例 |
| CLD 插件 | ~/.dsh/profiles/web/node_modules/dsh-plugin-cldvoice | - | CLD 内嵌悬浮球形态(v0.3.9) |

> 注：成稿引擎已升级为 **LLM 主动提炼**(v1.1.0)——不再输出占位符模板，由 GLM 从真实对话提炼背景/需求/决策，寒暄对话折叠为一句。

## 快速接入(3 步)
```html
<script src="./voice-sdk.js"></script>
<script>
  const v = new VoiceClient({ url: 'ws://你的服务:8905' });
  v.on('partial', t => ...); v.on('ai_text', t => ...);
  v.start(); // 说话 → v.stop() → AI 回应
</script>
```

## 协议 v1(WS 文本帧 + 二进制 PCM)
client→server:
- 二进制: 16k PCM Int16 音频包(~128ms)
- `{"type":"commit"}` 结束当前段触发 AI
- `{"type":"cancel"}` 打断 AI
- `{"type":"close"}` 关闭

server→client:
- `{"type":"ready","sid":...}` 会话建立
- `{"type":"transcript_delta","delta":...}` 你的话增量(LCP 去重后)
- `{"type":"text_delta","delta":...}` AI 文本流式
- `{"type":"audio_delta","audio":b64}` AI 语音 24k PCM(单字节流, 每片独立 base64)
- `{"type":"audio_done"}` / `{"type":"done"}` 本轮结束
- `{"type":"err","msg":...}`

## HTTP API
- `GET /v1/health` → `{ok, active_sessions}`
- `GET /v1/stats` → 会话统计
- 鉴权(可选): `X-Voice-Token`(服务端 --token 配置)

## 版本
- voice-service v1.2.0 · 成稿引擎(LLM 提炼) v1.1.0 · 协议 v1
- CLD 插件 dsh-plugin-cldvoice v0.4.7

## 日志
- voice-service: ~/dsh-collab/logs/voice-service.log
- 内核桥: ~/dsh-collab/logs/cld-voice-duplex.log

## 依赖
- 火山语音 VOLC_ASR_API_KEY（Seeduplex 1.2.6.0 全双工）
- 成稿 LLM: GLM_API_KEY（~/dsh/.credentials.yaml）
- Python venv: ~/dsh-collab/cld-voice/backend/venv (websocket-client, websockets)

## 架构图
```
┌─ 场景层(L3) ────────────┐
│ CLD插件(悬浮球) / 法拍App│
│ 景鸿问答 / 网页 / 妙搭    │
├─ 接入层(L2) ────────────┤
│ voice-sdk.js (统一API)   │
├─ 内核层(L1) ────────────┤
│ voice-service 8905       │
│  ├ Seeduplex 全双工(duplex内核) │
│  └ 成稿引擎 8902(LLM提炼) │
└─────────────────────────┘
```
