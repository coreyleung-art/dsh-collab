# Changelog
## 0.5.2 (2026-09-10) 【撤回假的方言语音包 —— 用户实测反馈】
- **用户实测反馈**: 选了粤语包，**文字是粤语，但回话的语音是国语**。用户判断正确，我的"验证通过"是错的。
- **我的验证错在哪**: 只验了「文字含粤语特征字」+「音频字节>0」，**从未验证声音本身是不是粤语**。
  我甚至自己写了"我听不到声音"，却照样宣布通过 —— 这是把"无法验证"当成了"验证通过"。
- **客观复核(whisper 转写对照)**:
  | 样本 | 转写 | 结论 |
  |---|---|---|
  | 国语·灿灿 | "聽起來是要做語音相關的開發呀…" | ✅ 准确 |
  | 粤语·灿灿 | "你好呀,想做边类**凯**语音功能**纤**?…" | ❌ 同音字乱码 |
  | 粤语·温柔桃子 | "你好呀,想做**滅類型凱**語音功能**線**…" | ❌ 同音字乱码 |
  | **对照: 真粤语(macOS Sinji)** | "你好呀!想做**哪類型**的語音功能線?**是**聊天還是識別呀?" | ✅ 被**连贯翻译**(係→是、邊→哪) |
  - 规律: 嘅→凯(kǎi)、咩→滅(miē)、先→纤(xiān) —— **全是这些字的普通话读音**。
  - 即：**模型吐粤语文字，TTS 用普通话读音念它**，听感比纯普通话更怪。换温柔桃子音色同样如此。
- **结论**: 通过该 API 路径拿不到"真粤语语音"。火山对**未知音色 ID 不报错、静默回落**，
  无法靠试错发现真音色；官方音色表(docs/6561/1108211)是 JS 渲染，抓不到。
- **本次动作（收敛，不扩范围）**:
  - **撤下全部方言包**（粤语/四川话/东北话/陕西话/温柔桃子）—— 四川话等三种**用户根本没要，是我擅自加的**
  - `VOICE_PACKS` 仅保留 `zh`（国语·灿灿）= 语音行为回到 v0.4.8
  - 客户端：**只有多于 1 个包时才显示选择器** → 面板回到无选择器的原样
  - `DIALECT_PROMPTS` 仅保留 yue 定义并加显著注释，说明实测结论与前置条件（拿到确认可用的粤语音色才启用）
- sandbox: 后端语法 OK / list_packs 仅 1 项 / 移除的包回落默认 / 客户端渲染测试 PASS=17
## 0.5.1 (2026-09-10) 【一键清屏】
- 用户反馈: 每次重新打开面板都还记着上一次的会话内容 → 加"一键清屏"按钮
- 根因: `rows/live/aiLive` 只存在内存(模块级 `eng`, 页面存活期间不消失), **不落 localStorage**;
  原先唯一清空点是"✅完成注入"成功后(`setEng({rows:[],open:false})`) —— 只要不做注入, 关掉面板再开旧记录就还在
- 新增: 标题栏「🧹 清屏」按钮 + 记录条数显示
  - **二次确认**: 第一次点击变「确认清空?」(3.5s 内有效), 第二次点击才真清 —— 避免误删尚未注入的讨论内容
  - 3.5s 未确认自动取消, 不会一直停在待确认态
  - 清空范围: `rows` / `live` / `aiLive` / `userFinal` / `aiBuf` / 音频诊断计数; **不影响已注入到会话的成稿**
  - 清空后仍可继续记录新一轮, 旧内容不复活
- 测试: 新增 `tools/test-clear-button.js` —— **直接加载真实 client.js**(不复制逻辑), 桩掉 React/WebSocket/AudioContext,
  把 FloatBall 组件调起来, 用假桥消息造出历史记录后模拟点击
  - 用例: 渲染按钮 / 初始空态 / WS 带语音包 / 造出记录 / 条数显示 / 一次点击进入待确认且**记录仍在** / 二次点击真清空 / 复位 / 清空后继续记录 / 旧内容不复活 / 超时自动取消且不误清
  - 结果: **PASS=17 FAIL=0**
- sandbox: 语法 OK / 只改 client.js(+host 未动, 仅需 Cmd+R)
## 0.5.0 (2026-09-10) 【可选语音包 · 方言/音色可切换】
- 用户反馈: 文字能理解粤语、也懂用粤语字表达, 但**回话只有国语** → 查机制后确认非模型能力问题
- **机制查证(实测)**: Seeduplex 的"声音"由**两个互相独立**的旋钮决定
  - `audio.output.voice` = 音色(谁在说)
  - `session.instructions` = 语言/方言/风格(说什么)
  - 方言**完全由 instructions 驱动, 无需换音色**: 同一 `zh_female_cancan_mars_bigtts` 在粤语指令下讲出地道粤语(嘅/係/咩/𠮶)
  - 模型能力: 听得懂 18 种方言; **输出支持 4 种**(粤语/四川话/东北话/陕西话)
  - 关键措辞: 方言指令必须"硬性 + 绝对不要用普通话"; 温和表述会被忽略并回落普通话
- **新增语音包(Voice Pack)** = 音色 + 方言指令的预设组合, 面板可切, localStorage 记住
  - 内置 6 个: 国语·灿灿(默认) / 粤语·灿灿 / 四川话·灿灿 / 东北话·灿灿 / 陕西话·灿灿 / 粤语·温柔桃子
- 内核 `duplex_bridge.py`: `BASE_INSTRUCTIONS` + `DIALECT_PROMPTS{}` + `VOICE_PACKS` + `resolve_pack()`;
  `pump(gui_ws, pack, voice, dialect)` 三参全可选 → **不传即 v0.4.8 原行为**(向后兼容)
- 网关 `voice_service.py` v1.3.0: WS 连接 query 读 `?pack=`/`?voice=`/`?dialect=`; 新增 `GET /v1/packs` 返回包清单
- 客户端: 面板加「🗣 语音包」下拉(紧邻音量滑块), 连接时带 `?pack=<id>`, 服务端回告生效包显示在面板
- **本机实测(走网关 8905 端到端, 非直连火山)**:
  - pack=yue 3/3 判定粤语 + 3/3 出声(502KB~588KB); pack=zh 3/3 判定国语, 2/3 出声
  - 受控实验(喂 `say` 合成语音): 对照=国语 / +粤语指令=粤语, 同一音色两种结果 → 机制确证
  - 工具: `cld-voice/tools/seeduplex-dialect-test.py`(直连受控实验) / `voice-pack-e2e.py`(网关端到端)
- 注: 切换语音包后需**重新点 ● 说话**(语音包在建会话时生效, 会话级参数)
- 注: 偶发"只出文字不出声"是**既有问题**(与语音包无关); 数据上粤语包反而比国语包更稳
- sandbox: 语法 OK / resolve_pack 六包+未知包回落 OK / host index.js 未改动(仅需 Cmd+R)
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
