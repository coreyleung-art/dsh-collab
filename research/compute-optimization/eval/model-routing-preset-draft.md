# 模型路由 preset 片段草案（供设备协调侧落地）

> 编制：算力优化调研子代理 · 2026-08-18 · 依据：eval/routing-table-v1.md（PC-i9 4 模型 + mac-mini 2 模型实测）
> 状态：草案，需协调侧按 DSH agent preset（~/.dsh/.agent-presets/ + cordis patch）结构适配落地；task-env-map 联动字段可直接取用

## 一、路由决策表（任务类型 → 模型/端点/参数）

| task 维度 | 首选模型 | 端点 | max_tokens | temperature | 备选 | 避开 |
|---|---|---|---|---|---|---|
| extraction（结构化抽取） | qwen2.5:7b | pc-i9 | 1024 | 0 | mistral:7b / meta-llama-3-8b-instruct | qwen3.5-2b（thinking 无最终 JSON） |
| tool_call（工具调用） | qwen2.5:7b | pc-i9 | 1024 | 0 | deepseek-r1:8b（2048）/ meta-llama-3-8b-instruct | llama3.1:8b（拒单被拒） |
| summary（摘要） | qwen2.5:7b / deepseek-r1:8b | pc-i9 | 1024–2048 | 0.2 | qwen3.5-2b（质量尚可） | —（待 LLM-judge 定论） |
| classification（分类） | deepseek-r1:8b | pc-i9 | 1024 | 0 | qwen2.5:7b（统一标签后） | 直接子串判分；llama3.1:8b |
| reasoning（复杂推理） | deepseek-r1:8b | pc-i9 | 2048+ | 0 | — | — |
| embedding/OCR | bge-m3 / nomic（本机）；glm-4.6v-flash / olmocr-2-7b | mac-mini | — | — | — | 待 OCR 场景评估 |

## 二、YAML 片段草案（cordis 结构示意，需按宿主 mount 适配）

```yaml
# 挂载于 agent preset 的 model-routing 段（或宿主 base.cordis.yml 的 model route 扩展）
model-routing:
  version: v1
  source: dsh-collab/research/compute-optimization/eval/routing-table-v1.md
  default:
    endpoint: http://127.0.0.1:1234/v1      # mac-mini LM Studio
    temperature: 0
  routes:
    - task: extraction
      model: qwen2.5:7b
      endpoint: http://100.118.15.71:11434/v1   # PC-i9 Ollama（Tailscale）
      max_tokens: 1024
      temperature: 0
      fallback: [mistral:7b, meta-llama-3-8b-instruct]
      avoid: [qwen3.5-2b]
    - task: tool_call
      model: qwen2.5:7b
      endpoint: http://100.118.15.71:11434/v1
      max_tokens: 1024
      temperature: 0
      fallback: [deepseek-r1:8b, meta-llama-3-8b-instruct]
      avoid: [llama3.1:8b]
    - task: summary
      model: qwen2.5:7b
      endpoint: http://100.118.15.71:11434/v1
      max_tokens: 2048
      temperature: 0.2
      fallback: [deepseek-r1:8b]
    - task: classification
      model: deepseek-r1:8b
      endpoint: http://100.118.15.71:11434/v1
      max_tokens: 1024
      temperature: 0
      note: 统一标签集 + 宽容匹配后复测；候选受限输出（constrained decoding）
    - task: reasoning
      model: deepseek-r1:8b
      endpoint: http://100.118.15.71:11434/v1
      max_tokens: 2048
      temperature: 0
  env:
    # PC-i9 已生效（路线 A 定案）；mac-mini 按需对齐
    OLLAMA_KV_CACHE_TYPE: q8_0
    OLLAMA_FLASH_ATTENTION: "1"
    OLLAMA_CONTEXT_LENGTH: "8192"
    OLLAMA_MAX_LOADED_MODELS: "1"
```

## 三、task-env-map 联动建议（JSON 映射，可直接入调度逻辑）

```json
{
  "version": 1,
  "defaults": { "endpoint": "http://127.0.0.1:1234/v1", "temperature": 0 },
  "routes": {
    "extraction":    { "model": "qwen2.5:7b", "endpoint": "http://100.118.15.71:11434/v1", "max_tokens": 1024 },
    "tool_call":     { "model": "qwen2.5:7b", "endpoint": "http://100.118.15.71:11434/v1", "max_tokens": 1024 },
    "summary":       { "model": "qwen2.5:7b", "endpoint": "http://100.118.15.71:11434/v1", "max_tokens": 2048, "temperature": 0.2 },
    "classification":{"model": "deepseek-r1:8b", "endpoint": "http://100.118.15.71:11434/v1", "max_tokens": 1024 },
    "reasoning":     { "model": "deepseek-r1:8b", "endpoint": "http://100.118.15.71:11434/v1", "max_tokens": 2048 },
    "embedding":     { "model": "bge-m3", "endpoint": "http://127.0.0.1:11434/v1" }
  },
  "avoid": { "tool_call": ["llama3.1:8b"], "extraction": ["qwen3.5-2b"] }
}
```

## 四、落地注意

1. 端点可达性：PC-i9 需在 DSH 宿主机网络可达（Tailscale 100.118.15.71:11434 已实测 200）；调度前加一次 /v1/models 探活
2. 思考模型参数：deepseek-r1:8b 必须 max_tokens ≥2048（1024 会截断致空输出）；qwen3.5-2b 结构化任务禁用
3. 分类任务：落地时建议先统一标签集（如 [投诉, 咨询, 催单, 其他]）并宽容匹配；后续可加 constrained decoding
4. 0.6B/3B 小模型分流：W35 双端拉取后在本文件补充 routes（预计加 local-fast 档）
5. preset 落地后由设备协调侧回写：model-routing 段 + task-env-map；本文件作为唯一事实来源（routing-table-v1.md 为数据依据）

## 五、与实测核对记录（2026-08-18）

| 路由规则 | 实测依据 | 结果 |
|---|---|---|
| extraction → qwen2.5:7b@PC-i9 | pc-i9-results.csv ext-01/02 = 1.0/1.0 | ✅ 一致 |
| extraction 避开 qwen3.5-2b | macmini-qwen3.5-2b.csv ext-01/02 = 0.0/0.0（无最终 JSON） | ✅ 规避正确 |
| tool_call → qwen2.5:7b@PC-i9 | pc-i9-results.csv tool-01/02 = 1.0/1.0 | ✅ 一致 |
| tool_call 避开 llama3.1:8b | pc-i9-llama3.1-8b.csv tool-02 = 0.0（拒单被拒） | ✅ 规避正确 |
| reasoning → deepseek-r1:8b（≥2048） | pc-i9-deepseek-r1-8b-mt2048.csv 4/4 = 1.0 | ✅ 一致 |
| classification → deepseek-r1:8b（临时） | cls-01 = 0.0（标签口径）/ cls-02 = 1.0 | ⏳ 待统一标签复测后转正式 |
| summary → qwen2.5:7b | sum-01/02 = judge（主观项） | ⏳ 待 LLM-judge |
| embedding → bge-m3@本机 11434 | 模型存在（未做性能评估） | ⚠️ 待补测 |

结论：除 classification（临时）与 summary/embedding（待补环节）外，路由与实测一致；「避开」规则均有 0 分实测背书。核对脚本：eval/results/_verify_routing.py（校验后可删）。

---
*模型路由 preset 片段草案 v1.1（含实测核对）· 2026-08-18 · 算力优化调研子代理*
