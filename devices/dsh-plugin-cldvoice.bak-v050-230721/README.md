# dsh-plugin-cldvoice

CLD-Voice 内嵌版（悬浮球形态 · 快速语音会议记录）。

## 能力
| 部分 | 说明 |
|------|------|
| host (`lib/index.js`) | `/voice/draft` 语音成稿(转发 8902 CLD-Voice 后端) + `/voice/health` + `/voice/test`(诊断页) |
| client (`lib/client.js`) | 悬浮球: click 弹出 → 全双工语音记录(你说→8905 voice-service→AI文字流式)→✅完成注入 setDraft+submit 进当前会话 |

## 交互（悬浮球）
- 🎤 悬浮球 fixed 右下角, **按住可拖动**, 不遮挡 conversation 区域
- 点击 → 展开「语音会议记录」面板
- ●说话 / ⏹停止（全双工, AI 实时回应上屏）
- ●说话时画面浮现**科技感语音浮点球**（canvas 动画, 随麦克风能量缩放/波动, 可拖拽, 默认星云样式）
- 面板提供**球样式切换**（🌌星云 / 🌟极光 / ☯太极图 / 🔵科技环 / 🌊声波雷达），自选并记住
- 面板提供**🔊 音量滑块**（30%~250%），AI 语音音量可调并记住
- ✅ 完成注入 → `/voice/draft` 成稿 → 自动填入当前会话输入框并发送
- 用完后点 ✕ 或完成注入自动收起（浮点球随之消失）

## 依赖
- CLD-Voice 后端: **8905** voice-service（全双工内核）+ 8902 asr_server/draft（成稿）launchd 常驻
- 火山语音 key: VOLC_ASR_API_KEY（桥用）

## 架构
```
CLD 悬浮球 🎤 ──ws──▶ voice-service:8905 ──▶ 火山 Seeduplex 全双工
   ├─ 转写/文本流式 → 面板显示 (portal 挂 document.body, 固定悬浮)
   ├─ 麦克风能量(RMS) → 🟢 科技感浮点球动画 (说话时浮现, 可拖拽)
   └─ ✅完成注入 → host /voice/draft → 8902 成稿 → inputActions.setDraft+submit 进当前会话
```

## 版本
- v0.1.0: 初版(三层 bug 致崩, 星桥修复为 host-only)
- v0.2.0: 规范 client(对照 ui-commands/voice, exports ./client + dsh.client + ctx.inject slots)
- v0.3.0: 悬浮球形态(portal 挂 body 避免布局挤压 G6); 桥 target 明确 8905; 注入直连 inputActions
- v0.3.1: 修复成稿注入带 role(区分用户/AI) + AI语音复用共享 playCtx(手势解锁)
- v0.3.2: 真·修"没声音"——ensurePlay() 移到点●手势内同步解锁(原在 ws.onopen 异步回调里被 autoplay 挂起)
- v0.3.3: 音频多层兜底——播放前 resume + 分片播放 + 全局 pointerdown 解锁 + 🔊/⏳ 状态指示
- v0.3.4: 音频诊断行——面板实时显示 收KB/播次数/ctx状态/错误, 定位"没声音"
- v0.3.5: 真·根因修复——audio_delta 分片 base64 各自带 padding, 改逐片解码(整段 atob 会抛错导致无声)
- v0.3.6: 修打断叠音——播放源追踪+停止(flushAi 播前 stop), 用户插话即停播+发 cancel
- v0.3.7: 修一句话多次回应/录入(回声自我循环)——AI TTS 播放时麦克风改送静音(micOff), 模型听不到自己
- v0.3.8: 修"多把声音"——播放改单 buffer 无缝(不再 2s 切块), 避免接缝/异音感; 超长才切块
- v0.3.9: 弃用 micOff 送静音(会诱发"只回文字没语音") → 改硬件回声消除(echoCancellation/noiseSuppression)让模型持续感知真实语音

## 开发门(G1-G6)
对照先例 → 严格模拟 → R006 补齐 → 沙箱试载 → 才碰真实 CLD → 真机布局核验
