# 部署包变更说明（PACKAGE-CHANGELOG）

> 注意区分：**插件版本**（`dsh-plugin-cldvoice`）与**部署包版本**（本包）是两条版本线。
> 本次包版本 v0.4.9 内含的插件**仍是 v0.4.8**（插件字节未改动）。

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
