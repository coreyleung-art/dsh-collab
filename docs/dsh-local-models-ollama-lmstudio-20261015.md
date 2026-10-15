# DSH 接入本地模型（Ollama + LM Studio）· 2026-10-15

把本机 Ollama 与 LM Studio 的模型接成 DSH 可选模型，**切换即用，不需要重启 CLD**。

---

## 一、结果

`~/.dsh/settings.yaml` → `llm-pi-ai.providers` 下现在有两条新路由：

| 路由 id | 显示名 | 指向 | 模型数 |
|---|---|---|---|
| `ollama` | Ollama 本地 | `http://127.0.0.1:11434/v1` | 1 |
| `lmstudio-local` | LM Studio 本地 | `http://127.0.0.1:1234/v1` | 4 |

另修好一条**原本已坏**的既有路由：

| 路由 id | 显示名 | 修了什么 |
|---|---|---|
| `lmstudio` | MCP Station Vision | 缺 `Authorization` 头 ⇒ 每次请求抛 `No API key for provider`，视觉链路整条失效 |

`lmstudio` 路由由 `dsh-plugin-mcp-station` 的 `saveVision()` 拥有，其模型列表**没有动**；
用户自己的本地模型放在独立的 `lmstudio-local` 里，不会被那个函数覆盖。

**排查走的路径**：打开 **设置 → 模型**，模型选择器里应出现「Ollama 本地」「LM Studio 本地」两组。

---

## 二、为什么写在 `settings.yaml`（而不是别处）

1. **DSH 的模型目录不会自我刷新。** `dsh-llm-pi-ai` README 原文：
   > 路由的 catalog 不会自我刷新……这里没有任何环节会去问提供方它服务哪些模型；
   > 路由要多一个模型，得有人写进去。

   ⇒ `ollama pull` 或 LM Studio 新下模型后，**必须重新写入清单**才会出现在选单里。

2. **配置归 settings 缝，不归 cordis 组合层。** 本机 `dsh-settings-file` 监听
   `$DSH_HOME/settings.yaml`；`dsh --profile web --dump-config` 里 `llm-pi-ai` 是**无 config 的裸条目**，
   可证配置不在 `cordis.patch.yml`。（官方 `providers.zh.md` 说模型页写的是 `cordis.patch.yml`，
   那是更新版本的部署形态；本机实测以 settings.yaml 为准。）

3. **改了文件不用重启。** `dsh-settings-file` 用 chokidar 监听该文件（`watch: true`，`debounceMs: 100`），
   外部编辑会热发布进 settings 缝，`llm-pi-ai` 随即**原子替换**自己的路由注册。
   实测：改完立刻调 `vision_analyze` 即已生效，**未重启任何进程**。

---

## 三、两个不修就不通的坑（都踩过了）

### 坑 1：本地端点也要「有 key」

`pi-ai` 的 `openai-completions` 实现（`dist/api/openai-completions.js:31`）：

```js
function getClientApiKey(provider, apiKey, headers) {
    if (apiKey) return apiKey;
    if (hasHeader(headers, "authorization") || hasHeader(headers, "cf-aig-authorization")) return "unused";
    throw new Error(`No API key for provider: ${provider}`);
}
```

Ollama 和 LM Studio 都不校验密钥，但**不给 `Authorization` 头就直接抛异常**。
⇒ 两条路由都加了：

```yaml
      headers:
        Authorization: "Bearer local"
```

**实证**（修复前 / 修复后，同一条 `vision_analyze`）：

```
修复前 → Error: Vision model error: No API key for provider: lmstudio
修复后 → This image is blue.          ← 图是我生成的 RGB(30,120,220)，答对
```

### 坑 2：pi-ai 会把不认识的地址当 OpenAI 本身

官方 `providers.zh.md` 明确：pi-ai 对无法识别的地址按 OpenAI 对待，于是

- 系统提示词以 `role: "developer"` 发出 —— 多数本地端点直接拒绝；
- 输出上限写作 `max_completion_tokens` —— 只认 `max_tokens` 的服务端拒绝。

⇒ 两条路由都加了：

```yaml
      compat:
        supportsDeveloperRole: false
        maxTokensField: max_tokens
```

**实证**：声明 `compat` 后按该形状请求 Ollama，返回 `content='OK'`、`finish_reason=stop`。

> 这两样是「对你端点的断言」，不是检查。换端点若行为变了，就在这里调。

---

## 四、已知限制（写清楚了，别当成 bug）

| 现象 | 原因 | 处置 |
|---|---|---|
| **Ollama 只有 4096 上下文** | `OLLAMA_CONTEXT_LENGTH` 未设，默认 4096。实测 `ollama ps` 的 CONTEXT=4096，且 `llama-server` argv 里是 `-c 4096` | 见下方「放开 Ollama 上下文」 |
| LM Studio 的 `contextWindow` 可能偏大 | 未加载的模型只能报「模型上限」；LM Studio 载入时会按显存自动决定实际值。实测 2B 模型被自动定为 **121088**（上限 262144） | 模型加载后重跑同步脚本，即改取实际值；或用 `--lmstudio-ctx-cap` 设上限 |
| embed 模型没进选单 | `bge-m3`、`nomic-embed-text`（Ollama）与 `text-embedding-nomic-embed-text-v1.5`（LM Studio）只能做 embedding，接进对话选单是个坏选项 | 有意排除。`nomic-embed-text` 已被 knowledge 插件用作嵌入模型（见 `cordis.patch.yml` 的 `knowledge` 段） |
| `allenai/olmocr-2-7b` 名字带「无工具调用」 | LM Studio 报它没有 `tool_use` 能力 | 可作纯对话/OCR 用，**不能**驱动 DSH 的 agent 工具循环 |
| qwen3.5 系列很慢 | 是思考模型。实测问一句 "Say OK" 花掉 **121 个 reasoning token**；`max_tokens=16` 时直接返回空串 | 路由给到 `maxTokens: 8192`。想关思考：`chat_template_kwargs.enable_thinking=false` **实测无效**（LM Studio 忽略该参数），需在 LM Studio 模型设置里关 |

### 放开 Ollama 上下文

```bash
launchctl setenv OLLAMA_CONTEXT_LENGTH 32768   # 全局环境变量，随后需重启 Ollama.app
python3 ~/dsh-collab/scripts/dsh-local-models-sync.py --apply   # 重跑即自动取到新值
```

★ 现状下 3B 模型这条路**实际上跑不动 agent**：DSH 的系统提示词本身就远超 4096 token。
要真用起来，先做上面这一步。

---

## 五、日常用法

```bash
S=~/dsh-collab/scripts/dsh-local-models-sync.py

python3 $S                      # 预演：探测 + 打印将要写入的全文（不落盘）
python3 $S --apply              # 写入（自动备份，保留最近 3 个）
python3 $S --json               # 只输出探测结果，供别的脚本消费
python3 $S --apply --ollama-ctx 32768 --lmstudio-ctx-cap 32768   # 手工覆盖
python3 $S --apply --no-vision-fix                                # 不动 lmstudio 视觉路由
```

**什么时候重跑**：`ollama pull` 新模型之后、LM Studio 下载/删除模型之后、改了上述任一参数之后。

**脚本保证**：
- 只重写 `ollama` / `lmstudio-local` 两条托管路由，**其余 provider 与全部注释原样保留**；
- `lmstudio` 视觉路由只补 `Authorization` 头，模型列表一个不动；
- 默认 dry-run；真写前备份；保留原文件权限（0600）；写失败清理临时文件；
- 探测不到的端点只跳过该条路由并告警，不写出空模型列表（空列表会被适配器判非法）。

**幂等性实证**：写入后 `diff` 备份与新文件 —— **新增 72 行、删除 0 行**，
唯一副作用是 `lmstudio` 与 `pentq` 之间补了一个空行。

---

## 六、手工路径（GUI）

不想跑脚本时，官方入口是 **设置 → 模型 → 添加模型提供商 → 自定义模型 API**：
填 Provider ID（小写开头）、基础 URL、协议选 **OpenAI Chat Completions**、至少一个模型。
**模型目录 → 获取可用模型** 会问端点要 `GET /models` 并给出可勾选的候选框。

GUI 覆盖不到的字段（`headers`、`compat`、`defaultMaxTokens`、每条模型的容量）仍需落在
`settings.yaml`，所以脚本仍是更完整的那条路。

---

## 七、回滚

```bash
cp ~/.dsh/settings.yaml.bak-models-sync-20261015-112506 ~/.dsh/settings.yaml   # 热重载，无需重启
```

更早的良好态另有 `~/dsh-collab/guard/backups/Users__coreyleung__.dsh__settings.yaml.bak-good-2026-10-15-03-2`。

---

## 八、证据锚点

| 结论 | 依据 |
|---|---|
| catalog 不自动刷新 | `dsh-llm-pi-ai/README.zh.md` 第 209 行 |
| 无 key 即抛异常 | `pi-ai/dist/api/openai-completions.js:31-37`；实测报错原文 |
| `headers` 随请求下发 | `dsh-llm-pi-ai/lib/index.js:1744` `headers: requestHeaders(profile.headers)` |
| 热重载 | `dsh-settings-file/lib/index.js` chokidar `watch` / `debounceMs:100` |
| compat 两开关合法 | `dsh-llm-pi-ai/lib/index.js:884-905`、`COMPLETIONS_COMPAT_GATE`（两者均为 `offer`） |
| Ollama 实际 4096 | `ollama ps` CONTEXT 列 = 4096；`llama-server ... -c 4096` |
| LM Studio 实际上下文可变 | `/api/v0/models` 的 `loaded_context_length`（2B 实测 121088，上限 262144） |
