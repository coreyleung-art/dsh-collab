# 部署包变更说明（PACKAGE-CHANGELOG）

> 注意区分：**插件版本**（`dsh-plugin-cldvoice`）与**部署包版本**（本包）是两条版本线。
> 本次包版本 v0.5.0 内含**插件 v0.5.0**（插件也有改动，两条版本线本次对齐）。
> 历史上 v0.4.9 包内含的是插件 v0.4.8（当时插件字节未改）。

---

## v0.5.0 · 2026-09-10 【可选语音包 · 方言/音色可切换】

**性质**：新功能（非修 bug）。插件 + 网关 + 内核三层同步改动。

### 需求来源
用户反馈：**文字层面它能理解粤语、也懂用粤语字表达，但实际回话只有国语**。要求查机制并做成可选语音包。

### 机制查证结论（实测，非推测）
Seeduplex 的"声音"由**两个互相独立**的旋钮决定：

| 旋钮 | 字段 | 决定什么 |
|---|---|---|
| 音色 | `audio.output.voice` | 谁在说（音色/质感） |
| 语言/方言/风格 | `session.instructions` | 说什么（语言、方言、语气、情绪） |

**方言完全由 `instructions` 驱动，无需换音色。** 受控实验（`tools/seeduplex-dialect-test.py`，喂 macOS `say` 合成语音）：

| 组 | 输入 | 指令 | 模型回复 |
|---|---|---|---|
| A 对照 | 国语 | 原指令 | "听起来是要做语音相关的开发呀，你是想做识别、合成，还是交互类的语音功能呀？"（国语） |
| B | 国语 | +粤语指令 | "你好呀，想做边类型**嘅**语音功能先？比如**系**语音识别、播报，还是互动对话**𠮶**类？"（粤语） |
| C | 粤语 | +粤语指令 | "你好呀，想做**嘅**语音功能大概**係**用来做**咩**场景**嘅**？"（粤语） |

- 结论1：**"只回国语"不是模型能力问题，是提示词从未要求粤语。**
- 结论2：同一 `zh_female_cancan_mars_bigtts` 在粤语指令下即讲出地道粤语。
- 结论3：模型听得懂 18 种方言，**输出支持 4 种**（粤语/四川话/东北话/陕西话）。
- 结论4（措辞关键）：方言指令必须用**"硬性 + 绝对不要用普通话"**这类强约束；温和表述（"可以的话用粤语"）会被模型忽略并回落普通话。

> 参考：[端到端实时语音-全双工版本（火山官方）](https://docs.volcengine.com/docs/6561/2549778?lang=zh)、[豆包打电话升级 Seeduplex：4种方言+情绪拉满](https://www.zaowu.world/ai-dry/202607310900-1785488551.html)

### 新增能力
**语音包（Voice Pack）= 音色 + 方言指令的预设组合**，悬浮球面板可切换，localStorage 记住。

| id | 名称 | 方言 |
|---|---|---|
| `zh` | 国语·灿灿（默认） | 普通话 |
| `yue` | 粤语·灿灿 | 粤语 |
| `sichuan` | 四川话·灿灿 | 四川话 |
| `dongbei` | 东北话·灿灿 | 东北话 |
| `shaanxi` | 陕西话·灿灿 | 陕西话 |
| `yue_taozi` | 粤语·温柔桃子 | 粤语（另挂音色） |

### 改动文件
| 文件 | 改动 |
|---|---|
| `plugin/…/lib/client.js` | 面板加「🗣 语音包」下拉；连接带 `?pack=<id>`；显示服务端回告的生效包；+51 行 |
| `plugin/…/package.json` | 0.4.8 → **0.5.0** |
| `backend/duplex_bridge.py` | `BASE_INSTRUCTIONS` + `DIALECT_PROMPTS{}` + `VOICE_PACKS` + `resolve_pack()`；`pump()` 增 `pack/voice/dialect` 三个**可选**参数 |
| `backend/voice_service.py` | v1.2.0 → **v1.3.0**；WS query 读 `?pack=`/`?voice=`/`?dialect=`；新增 `GET /v1/packs` |
| `tools/*.py` | 新增 3 个查证脚本（受控实验 / 网关端到端 / 音色探测） |

**`plugin/…/lib/index.js` 未改动**（md5 仍为 `84ca7d7a4e2f5b58f9cf5a08b596620a`）→ 更新后**只需 Cmd+R，不需要 Cmd+Q**。

### 兼容性
- 不传 `pack` → 行为与 v0.4.8 **完全一致**（默认 `zh`）
- 未知 `pack_id` → 不报错，回落默认包（避免前端传错导致语音整体不可用）
- 老客户端（连接不带 query）继续工作；新增字段全部 optional
- `INSTRUCTIONS` / `VOICE` 旧名保留为别名

### 验证记录
| 项 | 结果 |
|---|---|
| 粤语包（走网关 8905 端到端） | ✅ **3/3 判定粤语 + 3/3 出声**（502KB / 551KB / 588KB） |
| 国语包（对照） | ✅ 3/3 判定国语；2/3 出声 |
| 直连火山受控实验 | ✅ 对照组国语 / 实验组粤语，同音色两种结果 |
| `resolve_pack()` 单测 | ✅ 6 包 + 未知包回落 全 OK |
| `/v1/packs` | ✅ 返回 6 包 + default |
| 服务端 bundle | ✅ 34831B，含选择器与 `/v1/packs` 拉取 |

### 接收端注意事项
1. **切换语音包后必须重新点 ● 说话** —— 语音包在建会话时经 URL query 传给网关，是**会话级参数**，不重连不生效。
2. **偶发"只出文字不出声"是既有问题，与语音包无关**。实测数据上粤语包（4/4 出声）反而比国语包（3/5 出声）更稳。既有兜底 `speech_text_buffer.commit` 不总能救回。
3. 语音包列表由网关 `GET /v1/packs` 提供，前端不硬编码；网关未起来时前端用内置兜底两项。
4. 若只需在 mac-mini 用语音包：**后端必须一起更新**（只更插件无效，方言指令在网关/内核里）。

---

## v0.4.9 · 2026-09-10

**性质**：跨设备首次真实部署（MBP → mac-mini）后回收的**打包缺陷修复版**。插件零改动。

### 修复项

1. **补齐漏打的 `backend/stream_bridge.py`**（严重）
   - v0.4.8 的包内 `backend/` 只有 3 个 .py，缺 `stream_bridge.py`；但 MBP 生产环境该文件存在且 8903 端口在跑。
   - 影响：接收端 `asr_server.py` 启动时 `from stream_bridge import start_bridge` 落到 `except`，**8903 火山流式桥静默缺失**（不报错、不崩，只少一条通道）。
   - 发现方式：mac-mini 安装后端口核对，8903 由另一个遗留服务占用而非本包提供；再对比 MBP 生产目录才发现包内缺文件。
   - 教训：`deploy-check.sh` 只审包内已有文件，**查不出「应该存在但没打进来」的文件**。已在本包 §六 增加"与发包方生产目录比对"要求。

2. **修复 `stream_bridge.py` 凭证解析的缩进兼容性缺陷**（严重）
   - 原实现 `for line in open(...): if line.startswith("VOLC_ASR_API_KEY")` —— **未 `strip()`**。
   - 部分 DSH 安装的 `~/.dsh/.credentials.yaml` 采用 `refs:` 嵌套格式，键带 2 空格缩进：
     ```yaml
     version: 2
     refs:
       VOLC_ASR_API_KEY: xxx      # ← 缩进键，原实现永远匹配不到
     ```
   - 后果：此类设备上 8903 桥取不到 key，连接火山时报「未配置 VOLC_ASR_API_KEY」。
   - 修复：统一为 `_load_key()`，先 `line.strip()` 再匹配，同时兼容
     - 扁平格式 `VOLC_ASR_API_KEY: xxx`
     - 嵌套格式 `refs:\n  VOLC_ASR_API_KEY: xxx`
     - `.env` 格式 `VOLC_ASR_API_KEY=xxx`
     - 并回退读取 `~/.dsh/.env`
   - 注：`duplex_bridge.py` / `asr_server.py` 原本就有 `strip()`，**无此问题**；仅 `stream_bridge.py` 遗漏。

3. **清理 `backend/__pycache__`**
   - 打包时误将字节码缓存带入，已移除（发布包不得含 `__pycache__`）。

### 未改动
- 插件 `plugin/dsh-plugin-cldvoice/`（host `lib/index.js` md5 `84ca7d7a4e2f5b58f9cf5a08b596620a`、client `lib/client.js` md5 `7773a8867cd31b9e351397825e16cfc7`）
- `voice_service.py`、`duplex_bridge.py`、`asr_server.py`
- launchd 模板、SDK、docs（除本文件与 INSTALL.md 说明补充）

### 接收端额外注意事项（非包缺陷，部署时须核对）
- **凭证格式**：接收端 `~/.dsh/.credentials.yaml` 可能是 `refs:` 嵌套格式，脚本/后端均需先 `strip()` 再匹配。
- **`GLM_API_KEY` 可能缺失**：缺则成稿引擎静默降级为关键词模式（`/api/draft` 返回 `stats.source == "keyword"`），功能不断链但质量下降。安装后务必实测一次并确认返回 `"source": "llm"`。
- **8903 端口冲突**：若接收端已存在遗留 `com.dsh.voice-bridge` 服务（同样指向 `stream_bridge.py`），会与本包 `asr_server.py` 内部的 8903 桥抢夺端口并反复重启。应先退役遗留服务，让 `com.dsh.cld-voice` 独占 8903/8904。
- **非交互 SSH 的 PATH**：`deploy-check.sh` 需要 `node`。通过 SSH 非交互执行时 `PATH` 不含 `/opt/homebrew/bin`，会导致 `node: command not found` 进而误报「语法错误」。先 `export PATH="/opt/homebrew/bin:$PATH"` 再自检。

### 验证记录（v0.4.9 之前的 v0.4.8 已在 mac-mini 实测）
| 项 | 结果 |
|---|---|
| 星桥中枢黑板取包 + sha256 校验 | ✅ `fa1a44f5b0a4626cace554adc40159cfc97b8f49e00b29cb1f3756989340106c` |
| 接收端 `deploy-check.sh` | ✅ PASS=10 FAIL=0（补 PATH 后） |
| 插件 host 路由 `/voice/health` | ✅ `{"ok":true,"service":"cldvoice"}` |
| 客户端 bundle 字节比对 | ✅ 31760B, md5 `7773a886...` 与发包方生产一致 |
| 成稿引擎 `/voice/draft` 端到端 | ✅ `stats.source == "llm"`（真 LLM 提炼） |
| 后端端口 8902/8903/8904/8905/8906 | ✅ 全部监听，服务稳定不 crash-loop |

---

## v0.4.8 · 2026-09-10（首次发布）

- 插件 v0.4.8：CLD 内嵌悬浮球语音会议记录（可拖拽、不遮挡、用完即关）
- 成稿走「总结文件」而非原始逐字稿，注入会话输入框
- 后端：`voice_service.py`（8905 WS / 8906 HTTP，多会话全双工内核）、`duplex_bridge.py`（Seeduplex）、`asr_server.py`（8902 成稿引擎）
- 已知：包内缺 `stream_bridge.py`（见 v0.4.9 修复项 1）
