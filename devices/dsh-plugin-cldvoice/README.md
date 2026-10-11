# dsh-plugin-cldvoice

CLD-Voice 内嵌版（悬浮球形态 · 快速语音会议记录）。

## 能力
| 部分 | 说明 |
|------|------|
| host (`lib/index.js`) | `/voice/draft` 语音成稿(转发 8902 CLD-Voice 后端) + `/voice/health` + `/voice/test`(诊断页) |
| client (`lib/client.js`) | 悬浮球: click 弹出 → 全双工语音记录(你说→8905 voice-service→AI文字流式)→ ✅成稿(结果只进面板内可编辑成稿区, **不自动发送**) → 📋采用(填入输入框, 是否自动发送由开关决定) |

## 交互（悬浮球）
- 🎤 悬浮球 fixed 右下角, **按住可拖动**, 不遮挡 conversation 区域
- 点击 → 展开「语音会议记录」面板
- ●说话 / ⏹停止（全双工, AI 实时回应上屏）
- ●说话时画面浮现**科技感语音浮点球**（canvas 动画, 随麦克风能量缩放/波动, 可拖拽, 默认星云样式）
- 面板提供**球样式切换**（🌌星云 / 🌟极光 / ☯太极图 / 🔵科技环 / 🌊声波雷达），自选并记住
- 面板提供**🔊 音量滑块**（30%~250%），AI 语音音量可调并记住
- **✅ 成稿** → 成稿结果只进面板内**可编辑成稿区**（textarea），不碰输入框、不发送
  - 已有成稿时按钮变 **🔄 重出稿**：带上当前成稿作 `base` ⇒ 后端走**增量修订**（只改你提到的部分，**其余逐字保留**，不覆盖）
  - 修订后可 **↩ 上一版** 回退（保留紧邻上一版）
- **📋 采用** → 把成稿区里（你改过的）文本填入输入框；**是否自动发送**由底部开关「填入后自动发送」决定（**默认关**，记忆于 `localStorage`）
- 采用后**不清空讨论、不关闭面板** ⇒ 可继续 ●说话 提意见（第二轮端到端沟通）或补录（二次录入）
- 清空讨论请用标题栏 🧹 清屏（二次确认）

## 依赖
- CLD-Voice 后端: **8905** voice-service（全双工内核）+ 8902 asr_server/draft（成稿 + 增量修订）launchd 常驻
- 火山语音 key: VOLC_ASR_API_KEY（桥用）

## 架构
```
CLD 悬浮球 🎤 ──ws──▶ voice-service:8905 ──▶ 火山 Seeduplex 全双工
   ├─ 转写/文本流式 → 面板显示 (portal 挂 document.body, 固定悬浮)
   ├─ 麦克风能量(RMS) → 🟢 科技感浮点球动画 (说话时浮现, 可拖拽)
   └─ ✅成稿 → host /voice/draft → 8902 成稿引擎
        ├─ 无 base ⇒ _llm_extract 从零提炼（source=llm）
        └─ 有 base ⇒ _llm_revise 增量修订（source=llm-revise）
                     失败 ⇒ source=revise-failed-keep-base（原样保留底稿，绝不重写）
      → 结果回面板成稿区 →（你编辑）→ 📋采用 → inputActions.setDraft [+ 可选 submit]
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
- v0.6.1: R006 ⑤ 存量对齐补课(selfcheck + CLI)
- **v0.7.0 (2026-10-10)**: 成稿从「一点就发」改为「可看可改可续聊」—— 取消自动注入/自动发送、面板内可编辑成稿区、
  🔄重出稿走**增量修订**(基于原稿补充而非覆盖)、↩上一版回退、「填入后自动发送」开关(默认关)、采用后不清历史不关面板。
  三层改动(client/host/asr_server) + 真实文件渲染测试 `tools/test-draft-iterate.cjs`(31/31) + 端到端 4/4 与安全性质 2/2。

## 开发门(G1-G6)
对照先例 → 严格模拟 → R006 补齐 → 沙箱试载 → 才碰真实 CLD → 真机布局核验
