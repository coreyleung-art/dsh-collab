# 语音输入与会议模式（dsh-plugin-voice + CLDVoiceIME）

> 登记会话：session-3221f810-25a6-442d-b09c-78fc3c810a9c
> 登记时间：2026-08-16
> 状态：已固化运行中（CLD 重启后静态插件自动接管）

## 交付物路径

| 成果 | 路径 | 说明 |
|------|------|------|
| DSH 静态插件 | `~/dsh-plugin-voice/` | lib/client.js（语音引擎+唤醒词+4个slot）+ lib/index.js（/voice/inbox、/voice/transcript 路由）+ cordis.patch.yml + README.md |
| 系统级语音助手 | `~/CLDVoiceIME/` | Swift 菜单栏 app：⌥⌘空格 录音 → Apple 听写 → 剪贴板上屏；构建 `./build.sh`；已装 `~/Applications/CLDVoiceIME.app` |
| 会议记录产物 | `~/meeting-notes/` | 会议记录 markdown（模型生成 + 转写原文备份） |
| CLD 语音收件箱 | `~/.dsh/voice/inbox/YYYY-MM-DD.md` | 系统助手说「发CLD，…」→ host 路由追加写入 |

## 功能

- 🎤 语音输入：DSH 对话框内语音转文字（Web Speech API，需 Chrome/Edge；CLD 内置 Electron 窗口支持性待验证）
- 📋 会议模式：逐句语音自动发给模型对话 → 结束指令生成结构化会议记录（议题/决议/待办）
- 🎙 唤醒词：设置页可增删改；说唤醒词快速调出新会话并开始语音输入
- 📊 音量指示：Web Audio 电平分析，状态条显示实时音量条 + 声音检测
- 🖥 系统级助手 CLDVoiceIME：任意应用可用（⌥⌘空格），Apple 原生听写，预留 Whisper 接口

## 关键经验（已同步 sysops）

- CLD webServer 端口重启后会变（61109→49771→63866）：脚本勿写死端口
- web 插件固化：`~/.dsh/profiles/web/package.json` 的 `dsh.profile.bundles` + link 依赖 + 重启
- SFSpeechRecognizer.requestAuthorization 非前台上下文会 abort：须用户动作触发
