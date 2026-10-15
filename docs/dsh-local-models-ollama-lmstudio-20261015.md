# DSH 接入本地模型（Ollama + LM Studio）· 2026-10-15

把本机模型接成 DSH 可选模型，**只接这台机器真跑得动的**，切换即用，不需要重启 CLD。

设备：**Mac mini M4 / 24 GB 统一内存**（`hw.model = Mac16,10`）。

---

## 一、最终结果

| 路由 id | 显示名 | 实际接入 | 说明 |
|---|---|---|---|
| `lmstudio-local` | LM Studio 本地 | **3 个** | `qwen3.5-2b`(121088) · `glm-4.6v-flash`(40960) · `olmocr-2-7b`(40960) |
| `ollama` | Ollama 本地 | **0 个**（路由已移除） | 全部候选装不下 DSH 基线提示词，见第五节 |
| `lmstudio` | MCP Station Vision | 1 个（原有） | 修好了缺失的 `Authorization` 头 |

被排除的：

| 模型 | 排除原因 |
|---|---|
| `qwen/qwen3.8-27b` | **本设备跑不动**：能加载（占 17.74 GB），但每次推理都返回 `Compute error`；换最小上下文 2048 重载照样失败 |
| `bge-m3`、`nomic-embed-text`、`text-embedding-nomic-embed-text-v1.5` | 只能做 embedding，接进对话选单是坏选项 |
| `qwen2.5:3b`（Ollama） | 服务端实际只给 4096 上下文 < DSH 基线 34316 |
| `Qwen3.5-9B-GGUF`（磁盘 6.1 GB） | **僵尸文件**：在 `~/.lmstudio/.internal/model-index-cache.json` 里有记录，但 `lms ls` 与 API 都不认它（`lms load` 报 Model not found）。需要你在 LM Studio 里重新扫描/重下才能用 |

---

## 二、判据：「能运行」不等于「能接」

对 DSH 来说，一个模型能用的充要条件是**三条全过**，缺一条都会在实跑时炸：

1. **能加载**（显存装得下）；
2. **能推理**（不是加载成功就算数 —— 27B 就是加载成功但推理 500）；
3. **实际上下文 ≥ DSH 基线提示词**。

第 3 条是本机最容易被忽略的。实测方法：从会话日志 `request/header` 里取出 `system` 与 `tools` 原样发一次请求，读 `usage.prompt_tokens`：

```
DSH 基线提示词 = 34316 token
  ├─ 系统提示词       4,731 token（15,467 字符）
  └─ 153 个工具      29,585 token（92,195 字符 JSON）
```

⇒ 默认门槛取 **40960**（基线 + 约 20% 余量留给对话）。低于它的模型，DSH 一发请求就是
`The number of tokens to keep from the initial prompt is greater than the context length`
（glm 在 8192 下的实测报错原文）。

> ⚠ 这个基线是**本 profile 的**数字：工具数随启用的插件变化。换 profile 或大改插件集后，
> 基线要重新测（脚本里的 `DSH_BASELINE_TOKENS` 常量）。

---

## 三、关键发现：8192 是「配出来的」，不是硬件上限

排查中最有价值的一条。LM Studio 的模型个个只加载到 8192，最初以为是显存自动缩水，**不是**：

```jsonc
// ~/.lmstudio/settings.json
"defaultContextLength": { "type": "custom", "value": 8192 }   // ← 全局默认被固定成 8192
```

而 `qwen3.5-2b` 之所以能到 121088，是因为它**单独有一份按模型覆盖**：

```jsonc
// ~/.lmstudio/.internal/user-concrete-model-default-config/lmstudio-community/Qwen3.5-2B-GGUF/Qwen3.5-2B-Q4_K_M.gguf.json
{ "preset": "", "operation": { "fields": [] },
  "load": { "fields": [ { "key": "llm.load.contextLength", "value": 120898 } ] } }
```

**⇒ 所以要抬高某个模型的上下文，写这份覆盖即可**（等价于 GUI 里该模型的 Context Length 设置）。
本次给 `glm-4.6v-flash` 与 `olmocr-2-7b` 各写了一份 `llm.load.contextLength = 40960`，
路径分别是 `user-concrete-model-default-config/zai-org/glm-4.6v-flash.json` 与
`.../allenai/olmocr-2-7b.json`（= 模型 `path` 字段 + `.json`）。

**验证两件事都成立**：
- 不带 `-c` 参数重新加载 → `lms ps` 显示 CONTEXT=40960（覆盖持久生效，不是一次性参数）；
- 卸载全部模型后由 **DSH 自己发请求触发加载** → `/api/v0/models` 报 `loaded_context_length = 40960`。
  （这一步是必须的：DSH 走 API 触发 JIT 加载，如果只在命令行传 `-c` 是不生效的 —— 实测过，不传就又回到 8192。）

### 速度：冷启动很慢，但只付一次

glm-4.6v-flash 处理 34k 基线提示词的实测：

| | 耗时 |
|---|---|
| 第 1 次（冷） | **349.3 秒** |
| 第 2 次（同前缀） | **0.7 秒** |
| 第 3 次（同前缀） | **0.4 秒** |

前缀缓存命中后快到可忽略。一个会话只在**第一次请求 + 模型被卸载后**付这个代价。

---

## 四、另外两个不修就不通的坑

### 坑 1：本地端点也要「有 key」

`pi-ai` 的 `openai-completions`（`dist/api/openai-completions.js:31`）：

```js
if (apiKey) return apiKey;
if (hasHeader(headers, "authorization") || ...) return "unused";
throw new Error(`No API key for provider: ${provider}`);
```

Ollama / LM Studio 都不校验密钥，但**不给 `Authorization` 头就直接抛异常**。
⇒ 两条路由都加了 `headers: { Authorization: "Bearer local" }`。

**实证**：修复前 `vision_analyze` 报 `No API key for provider: lmstudio`；修复后正常识别图片颜色。

### 坑 2：pi-ai 会把不认识的地址当 OpenAI 本身

官方 `providers.zh.md` 明确：会发 `role: "developer"` 与 `max_completion_tokens`，本地端点多数拒绝。
⇒ 两条路由都声明：

```yaml
      compat:
        supportsDeveloperRole: false
        maxTokensField: max_tokens
```

---

## 五、Ollama 为什么一个都没接上

`OLLAMA_CONTEXT_LENGTH` 未设 ⇒ 服务端默认 **4096**（实测 `ollama ps` 的 CONTEXT 列 = 4096，
且 `llama-server` argv 里就是 `-c 4096`）。4096 连 DSH 的 153 个工具都装不下 ⇒ 该路由下没有模型能过门槛。

修法（一条命令 + 重启 Ollama）：

```bash
launchctl setenv OLLAMA_CONTEXT_LENGTH 40960
# 然后退出并重开 Ollama.app（环境变量在服务启动时读取）
python3 ~/dsh-collab/scripts/dsh-local-models-sync.py --apply    # 重跑，ollama 路由会自动回来
```

★ 这一步改的是**全局环境变量 + 需要重启 Ollama 服务**，而该 Ollama 还在给 knowledge 插件做嵌入，
所以没有擅自执行。

---

## 六、日常用法

```bash
S=~/dsh-collab/scripts/dsh-local-models-sync.py

python3 $S                       # 预演（含实跑探测）
python3 $S --apply               # 写入（自动备份，保留最近 3 个）
python3 $S --reprobe --apply     # 无视缓存，全部重新实跑一遍
python3 $S --no-probe            # 跳过实跑（快，但不校验跑不跑得动）
python3 $S --min-ctx 20480       # 放宽/收紧上下文门槛
python3 $S --json                # 机器可读输出（进度走 stderr，stdout 是纯 JSON）
```

**什么时候重跑**：`ollama pull` 之后、LM Studio 下载/删除模型之后、改了模型上下文之后、启用/停用了一批插件（工具数变了，基线跟着变）之后。

**脚本保证**：只重写托管路由与视觉路由的鉴权头，其余 provider 与**全部注释原样保留**；
默认 dry-run；写前备份；保留原文件 0600 权限；无模型通过的路由**整条移除**而不是留过期清单；
探测结果按「模型体积」缓存 7 天，体积变了自动失效。

探测结果缓存：`~/.dsh/local-models-probe.json`。

---

## 七、还有一处隐患

`dsh-plugin-mcp-station` 的 `saveVision()` 会**整段替换** route 的 profile。
你在 MCP Station 面板点一次「保存」，视觉路由的鉴权头就会丢，视觉链路再次失效。
本脚本每次运行会把鉴权头补回来；根治需把该函数改成合并语义（host 侧插件，改动要重启 CLD 生效）。

---

## 八、回滚

```bash
cp ~/.dsh/settings.yaml.bak-models-sync-20261015-125119 ~/.dsh/settings.yaml   # 热重载，无需重启
rm ~/.lmstudio/.internal/user-concrete-model-default-config/zai-org/glm-4.6v-flash.json
rm ~/.lmstudio/.internal/user-concrete-model-default-config/allenai/olmocr-2-7b.json
```

（删掉两份 LM Studio 覆盖即回到原来的 8192 默认；目录里原有的 `google/`、`lmstudio-community/` 两份是用户自己的，本次未动。）

---

## 九、证据锚点

| 结论 | 依据 |
|---|---|
| DSH 基线 34316 token | 会话日志 `request/header` 的 system+tools 原样实测 `usage.prompt_tokens` |
| 系统 4731 / 工具 29585 | 同上，分开测 |
| catalog 不自动刷新 | `dsh-llm-pi-ai/README.zh.md:209` |
| 无 key 即抛异常 | `pi-ai/dist/api/openai-completions.js:31-37` + 实测报错原文 |
| `headers` 随请求下发 | `dsh-llm-pi-ai/lib/index.js:1744` |
| compat 两开关合法 | `dsh-llm-pi-ai/lib/index.js:884-905` + `COMPLETIONS_COMPAT_GATE`（均 `offer`） |
| 热重载 | `dsh-settings-file/lib/index.js` chokidar `watch` / `debounceMs:100` |
| 27B 跑不动 | `Compute error`，2048 上下文重载仍复现 |
| LM Studio 全局 8192 | `~/.lmstudio/settings.json` → `defaultContextLength` |
| 按模型覆盖生效 | 重载后 `lms ps` CONTEXT=40960；DSH 触发加载后 `/api/v0/models` 报 40960 |
| 前缀缓存 | 349.3s → 0.7s → 0.4s（同前缀三次） |
| Ollama 4096 | `ollama ps` CONTEXT 列；`llama-server ... -c 4096` |
