# Changelog
## 0.4.8 (2026-09-10) 【注入纯总结 + 成稿清洗】
- 用户反馈: 注入的是"语音本身"而非总结文件 → 定位/修复
  - 成稿引擎(8902) content 不再附加原始"讨论留痕"表(只落盘 .md 回溯), 注入 CLD 的只有提炼总结
  - 清洗增强: 折叠 "- -" 嵌套列表 / 删除空小节(含"- 无"占位) / 空节头剔除, 注入更干净
  - 客户端加注入诊断(origin/ok/contentLen/前40字 上屏面板)
- 实测: host /voice/draft(64817) → source=llm, 干净总结(背景/需求/约束/决策), 无原始语音无占位
- 后端验证: 8902 单测 _strip_markers 空节/嵌套全清; py_compile OK
- sandbox: 语法 OK
## 0.4.7 (2026-09-10) 【音量可调】
- 用户反馈"默认声音大小有点低" → 播放路径无增益, 音量=火山默认(偏低)
- 修复: 全局 playGain(默认 1.35 放大补偿), 播放 BufferSource 经增益节点; 面板加"🔊 音量"滑块(30%~250%), localStorage 记住
- sandbox: 默认音量1.35 / playGain创建+连destination / 播放连playGain / 音量滑块 / setPlayVolume存localStorage / 引擎volume 全 OK
## 0.4.6 (2026-09-10) 【默认星云 + 修球被方框约束】
- 默认样式改 **🌌 星云**(存储键改 _v3 重置旧选择)
- 修"球放大到一定大小被约束在方块内": canvas 280→**460**(半宽230 > 最大光晕R*1.5≈216), 球随声音放大不再被边界裁切
  - 同步箱体 460x460, R 计算 baseR58+e*86(最大 R144), 位置 bottom:230 文本框上方
- sandbox: 默认 nebula / v3键 / 460画布 / R计算 / nebula分派 / 无方框约束 全 OK
## 0.4.5 (2026-09-10) 【太极图改线描透底版】
- 用户反馈"太极图不好看, 不要有一部分是白色的", 要透底+半边有/半边无
- 改: 无实心色块(灰白填充全去掉), 只留外圈+标准S曲线(上凸左/下凸右)描边 + 阴阳眼
  - 上眼=实心亮(阳·有), 下眼=空心(阴·无), 象征"一半有/一半无"且整体透底
- sandbox: drawTaiji / S曲线上凸左 true / 下凸右 false / 上实心眼 / 下空心眼 / 无大实心色块 全 OK
## 0.4.4 (2026-09-10) 【默认科技环 + 新增太极图样式】
- 默认样式=**🔵 科技环**(用户要求); 存储键改 `cldvoice_orb_style_v2` 重置浏览器旧"极光"选择 → 重载即回科技环
- 新增 **☯ 太极图** 样式: 阴阳流转, 随能量缩放/缓转, 带阴阳眼
- 样式列表: 科技环(默认)/极光/太极图/声波雷达/星云
- sandbox: taiji 在列表 / 默认 tech / 存储键v2 / taiji 分派 / drawTaiji 函数 / 阴阳眼 / 5样式 全 OK
## 0.4.3 (2026-09-10) 【默认样式=最初那个】
- 默认样式改回 **🔵 科技环**(= v0.4.0 最初那个"光晕渐变+双层圆环+46粒子+中心亮核")
- 用户反馈"花里胡哨"后, 想找回最早样式 → 设为默认
- 若浏览器已存过其他样式(localStorage cldvoice_orb_style), 可在面板"球样式"点🔵科技环切回
## 0.4.2 (2026-09-10) 【光球可换样式】
- 面板新增"球样式"选择器, 4 种风格用户自选:
  - 🌟 极光(有机流动, 更"灵气") / 🔵 科技环(圆环+粒子) / 🌊 声波雷达(脉冲波纹) / 🌌 星云(粒子汇聚)
- 选中即切换(canvas draw 每帧读 orbStyle), localStorage 记住选择, 重载后沿用
- 默认 aurora(极光), 回应"不够灵气"的反馈
- sandbox: ORB_STYLES/4样式/localStorage持久/样式分派/各draw函数/面板选择器/setOrbStyle 全 OK
## 0.4.1 (2026-09-10) 【光球升级 + 修"语音播两次"】
- 光球: 更大(280px, baseR64) + 更快跟随(平滑 0.32, 及时反映语音) + AI说话也动球(aiPulse 生机脉冲)
  - RMS 增益 3.8, 30% 口语≈0.28(平缓正常); 底部居中文本框上方(bottom:200), 仍可拖拽
- 修"一段文字播两次、不同音调"(bridge): 根因=audio_done 把 _run_audio_bytes 清零, response.done 误判"0 音频"→ 兜底 TTS 重复触发
  - 改用 _resp_had_audio 标志(audio_delta 置 True), audio_done 不再清零, response.done 据此判断 → 只有真·无音频才兜底
  - 实测: 有音频轮(404/444/439/405KB)**无**兜底; 0 字节轮**才**兜底(日志确认)
- sandbox: apply+portal slot OK / VisualOrb OK / 280px OK / 0.32 跟随 OK / AI 动球 OK / baseR64 OK / RMS3.8 OK (all pass)
## 0.4.0 (2026-09-10) 【科技感语音浮点球】
- 新功能: 点●说话(rec)时画面浮现 canvas 动画浮点球, 随麦克风能量(RMS)缩放/波动
  - 光晕渐变 + 双层圆环 + 46 粒子呼吸环绕 + 中心亮核, 科技感
  - 能量平滑插值(0.12 lerp), 说话越大球越大; 单独可拖拽, 不遮挡(距浮球左侧 offset)
  - 关掉(⏹/✕/完成注入)自动消失
- sandbox: apply+portal slot OK / VisualOrb 组件 OK / RMS 计算 OK / rec 渲染 orb OK / 拖拽 OK / rAF 动画 OK / 能量插值 OK (all pass)
## 0.3.9 (2026-09-10) 【弃用 micOff 送静音 → 硬件回声消除】
- 症状: 偶发"只回文字没语音"(audio bytes=0), 用户指出其他端到端模型无此问题 → 不该甩锅给模型
- 排查: 链路转发正常(405KB+), 疑点落在 v0.3.7 的 micOff(AI说话时给模型送静音)会干扰模型对用户语音的感知/决定是否开口
- 修复: 移除 micOff/_gateSend, 改用 getUserMedia({echoCancellation,noiseSuppression,autoGainControl}) 硬件回声消除
  - 真实麦克风持续送给模型(不再送静音), 回声由浏览器 AEC 处理 → 模型感知正常语音, 应稳定产语音
- 保留: 打断即停 cancel / 单buffer无缝播放 / 播放前 resume / 诊断面板
- sandbox: apply+portal slot OK / echoCancellation OK / micOff已移除 OK / cancel OK / resume OK / 诊断 OK (all pass)
## 0.3.8 (2026-09-10) 【修"3把不同声音"→ 单 buffer 无缝播放】
- 症状: 一个 AI 回答里听到"3把/多把不同声音" (诊断面板 播3次 = 我上次 2s 切块播了3段)
- 根因: flushAi 把音频切成多段分别 start(), 分段边界产生接缝/异音感, 听起来像不同说话人
- 修复: 改为**单 buffer 无缝播放**(≤45s 一把放), 避免多段 start 的断裂; 仅超长(>45s)才切块
- 模型音色: 当前单一声线 `zh_female_cancan_mars_bigtts`, 非多说话人; 多声感来自播放切块
- sandbox: 语法 OK (node --check)
## 0.3.7 (2026-09-10) 【修"一句话4人回/4次录入"——回声自我循环】
- 用户测出: 说一句话被录入4次, 且有4个AI声同时回
- 根因: AI TTS 声音经扬声器放出 → 麦克风又采样到 → 模型听到自己声音 → 再次回应 → 循环 (bridge 日志可见单会话多次 response.done, 无用户输入)
- 修复(客户端): 
  - micOff 门: audio_delta(AI开始说话) 置 micOff=true, 麦克风 onaudioprocess 改送**静音**(不再送真实音频) → 模型听不到自己
  - audio_done/done 清 micOff → 恢复送麦克风, 用户可继续说话
  - transcript_delta(打断/用户说话) 也清 micOff
  - stopAudio 清 micOff
- 沙箱验证: micOff 送静音 OK / audio_delta置 micOff OK / audio_done/done清 micOff OK / transcript清 OK / stop清 OK
## 0.3.6 (2026-09-10) 【修打断叠音】
- 用户测出: 打断 AI 说话时旧声不停 + 新声开播 → 叠音(两三层/三四声)
- 根因: flushAi 创建 AudioBufferSource 后从不记录/停止, 新回答开播时旧音源仍在播
- 修复: 
  - playSources[] 追踪所有播放中的音源; _stopPlayback() stop+disconnect 全部
  - flushAi 开播前 _stopPlayback() → 新回答不再叠加旧声
  - transcript_delta(用户又开始说话=TTS仍在播/在说) → 立即 _stopPlayback + 发 {"type":"cancel"} 给桥 → 即时停播
  - onended 从 playSources 移除
- 沙箱验证: playSources.push / _stopPlayback 全停 / flushAi 播前 stop / transcript_delta 打断即停 / 发 cancel / onended 移除 全 OK
## 0.3.5 (2026-09-10) 【真·根因修复“没声音”】
- 根因: 每个 audio_delta 分片的 base64 各自带 '=' padding, 客户端**整段拼接后一次 atob** 抛 Invalid character
  - 症状: 面板诊断 收0KB/播0次; 后端+桥收到 400KB+ 音频但客户端解码即崩
  - 复现: `atob(拼接b64)` → Invalid character; `Buffer.from(b64,"base64")` 宽松解码只恢复 4096/412KB(在第一个 padding 停)
  - 实测: 15/15 分片**各自** base64 解码 100% OK(合计 303KB PCM)
- 修复: playAi 改为**逐片解码**累积 Float32(每片=一个独立 audio_delta 的合法 b64); flushAi 拼成整段再按 2s 分段播; 播放前 resume 兜底
- 同时: onBridgeMsg 错误上行到诊断面板(不再空 catch 吞错); playAi 守卫空/非字符串 audio
- 沙箱验证: apply+portal slot OK / 逐片解码(aiSamples.push) OK / flushAi 用 aiSamples OK / 诊断上屏 OK
## 0.3.4 (2026-09-10)
- 加音频诊断(定位"没声音"): 面板实时显示 🔊 收KB/播次数/ctx状态/错误
  - 确认 CLD 主进程 main.js 用默认 webPreferences(contextIsolation/nodeIntegration/sandbox), 无 autoplay 覆盖/无静音 → CLD 本身是正常 Chromium 可播
  - audDbg 记录 rx(收到字节)/played(播放次数)/err(任何异常), 面板显示, 便于二分定位
- WAS: 后端+桥接收音频正常(405-433KB/轮); 剩纯客户端播放 → 靠诊断读数判断是"没收到"还是"收到但没播放"
## 0.3.3 (2026-09-10)
- 音频播放多层兜底(真·修"没声音"):
  1. flushAi 播放前再 `c.resume()`(兜底手势已过期)
  2. 分片播放(每片~2s createBuffer), 避免单次巨大 buffer 卡顿/失败
  3. 全局一次 pointerdown → _primeAudio 解锁 AudioContext(任意交互都能解锁)
  4. 面板加 🔊(播放中)/⏳(音频到达待播) 状态指示, 便于观察是否真的在播
- 实测: bridge(8905) 单轮转发 audio_delta 405-433KB PCM + audio_done + done 全通, backend/桥正常; 纯客户端播放问题
## 0.3.2 (2026-09-10)
- 真·修复"没声音": ensurePlay() 移到 toggleRec(点●)开头, 在用户手势里同步 create+resume playCtx
  - 之前放在 ws.onopen→startMic(异步回调), 不在手势内 → Chromium autoplay 挂起 AudioContext → 静音
  - 实测: bridge(8905) 转发 audio_delta 累计 865468 字节 PCM, backend 生产/转发正常; 问题纯在客户端播放
- sandbox 验证: apply 注册 1 slot OK / toggleRec 手势内 ensurePlay OK / flushAi 复用 playCtx OK
## 0.3.1 (2026-09-09)
- 修复成稿注入: discussion 项补 `role`(user/ai), 否则成稿引擎无法区分用户与AI → 需求提炼乱/留痕无角色
- 修复"听不到声音": AI 语音播放改用共享 playCtx(在用户手势里 new+resume), 不再每次 new AudioContext
  (Chromium autoplay: 无手势新建的 AudioContext 会 suspended → 静音; 现 gesture 内解锁后复用)
- 后端联动: duplex_bridge 修复 `websocket` NameError→`ws_client`(drain 线程不再因会话关闭崩溃)
- sandbox 验证: apply 注册 1 slot OK / disc map 含 role OK / flushAi→ensurePlay 共享 OK / 卸载安全
## 0.3.0 (2026-09-09)
- 交互改版: 从「输入框🎤+浮层+底栏」改为「悬浮球」形态
  - ReactDOM.createPortal 挂 document.body: 一旦脱离布局流, 不再挤压 conversation 区域(G6 教训)
  - 🎤 悬浮球 fixed 可拖拽(按住拖动), 不用时收起, 用完自动关, 用时点击弹出(不遮挡)
  - 点击展开面板 → ●说话/⏹停止 → ✅完成注入 → /voice/draft 成稿 → setDraft+submit 进当前会话
- 引擎: 复用 v0.2 已验证全双工逻辑, 桥 target 明确为 8905 (voice-service 产品化内核, 与 voice-sdk 默认一致)
- 成稿注入直连 inputActions.setDraft/submit, 不依赖 host fill 中转
- sandbox 验证: Electron DOM 加载 OK / portal 挂 body OK / apply 注册 1 slot OK / 卸载安全
## 0.2.0 (2026-09-09)
- client 规范版: exports ./client + dsh.client + __ModuleLoader__ 结构
- apply 用 ctx.inject(['slots'])+slots.register(对照官方 ui-commands)
- 全双工: 🎤→8904→AI 文字流式→📋成稿发送进当前会话
- 沙箱验证: Electron DOM 加载 OK / apply 注册 3 slot OK / 卸载安全
## 0.1.0 (2026-09-09)
- host 版初建(成稿路由); 三层 Cordis bug 致 CLD boot 崩 → 星桥修复 host-only
