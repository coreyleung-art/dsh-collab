# PC-i9 推理栈依赖安装清单（RTX 4060 Ti 8GB）

> 维护：算力优化调研子代理 · 2026-08-18 · 用途：配合 Device Orchestrator 分派前对齐，先远程探测现状，再决定装什么
> 背景：PC-i9 已有 ollama 镜像（约 9GB）+ RTX 4060 Ti 8GB；LM Studio / CUDA 工具链未深测
> 原则：**能不装就不装**——Ollama 自带 CUDA runtime，只要 NVIDIA 驱动够新即可跑 GPU；LM Studio 只是 GUI 评估加分项，非必需

## 一、先探测（由设备协调侧远程执行，只读命令）

| 探测项 | 命令（Windows） | 判断基准 |
|---|---|---|
| 系统/内存 | systeminfo 过滤 OS/内存 | 建议 ≥16GB RAM |
| GPU/驱动 | nvidia-smi | 驱动 ≥ 560（支持 CUDA 12.x）；4060 Ti 8GB 显存确认 |
| CUDA 可用性 | nvidia-smi 看 CUDA 版本 | 驱动自带即可，无需装工具链 |
| Ollama 现状 | ollama --version 与 ollama list | 版本 ≥ 0.32；已拉模型清单 |
| Ollama 服务 | sc query ollama 或任务管理器 | 服务运行中 |
| 磁盘 | wmic logicaldisk get size,freespace | 每模型 4–10GB，预留 ≥50GB |
| 是否 WSL2/容器 | wsl --status | 只影响自建 vLLM 路线，Ollama 原生 Windows 不需要 |

## 二、依赖清单与版本基线

| 组件 | 最小/建议版本 | 用途 | 验证命令 | 备注 |
|---|---|---|---|---|
| NVIDIA 驱动 | ≥ 560（Game Ready/Studio 均可） | GPU 推理基础（Ollama/LM Studio 都依赖驱动，不需要单独装 CUDA Toolkit） | nvidia-smi | 驱动更新需管理员+重启，建议并入下次重启批次 |
| Ollama | ≥ 0.32（与 mac-mini 对齐） | 本地推理服务 | ollama --version | 已有 9GB 镜像，优先复用此路线 |
| Ollama GPU 配置 | OLLAMA_FLASH_ATTENTION=1；OLLAMA_KV_CACHE_TYPE=q8_0 | 长上下文加速 + KV 内存省 50% | ollama show <model> / 日志 | 省显存关键，8GB 卡必开 |
| LM Studio | 最新稳定版（以官网为准） | GUI 评估/对比（可选路线 B） | 界面内 Run 模型 | 若走 Ollama 路线可不装 |
| 模型（评估集用） | Qwen3-0.6B / 3B / 7-8B（GGUF Q4_K_M、Q8） | 下周模型评估基准 | ollama pull <model> | 14B Q4 约 9GB，8GB 显存会 offload，先跑 0.6B/3B/7B |
| Python（仅自建路线 C） | 3.11+ | vLLM/llama.cpp 自建（非必需） | python --version | 默认不做 |

## 三、决策分支（探测结果出来后选一条）

- **路线 A · Ollama（推荐，改动最小）**：确认驱动 ≥560 → 设 OLLAMA_KV_CACHE_TYPE=q8_0 + OLLAMA_FLASH_ATTENTION=1 → 拉评估模型 → 冒烟（ollama run 看 GPU 是否加载：nvidia-smi 显存占用上升即成功）。
- **路线 B · LM Studio（GUI 评估友好，可选）**：装最新 Windows 版 → 首次启动设模型目录（可复用 GGUF）→ 用 CUDA backend 做 A/B。装前确认驱动 ≥560；LM Studio 自带 CUDA runtime，仍无需手动装 CUDA Toolkit。
- **路线 C · vLLM（暂不建议）**：仅当并发吞吐评估需要；需 WSL2 + CUDA Toolkit 12.x + Python 3.11，复杂度高，列入后续按需评估。

## 四、8GB 显存约束（诚实标注）

- 0.6B/3B Q4：完全驻留显存，无压力 ✅
- 7B–8B Q4_K_M：约 5–6GB，可驻留（推荐主力档）
- 14B Q4_K_M：约 9GB，8GB 卡必然部分 offload 到 CPU，速度下降明显 ⚠️
- 27B：仅 CPU/混合跑，评估价值低，默认跳过
- KV cache 量化 q8_0 + 4k–8k 上下文是 8GB 卡的合理基线；16k 以上请实测

## 五、与下周模型评估的对接

1. 分派时随任务附本清单 + 目标机探测结果快照（驱动/ollama 版本/显存占用）
2. 评估集 4 类任务（摘要/抽取/分类/工具调用 × 20 例）先在 mac-mini 跑通基线，再把同一套脚本/模型清单分派到 PC-i9
3. 每任务记录：模型+量化档位 / tokens/s / 显存峰值 / 质量分，汇总进 compute-optimization/eval/ 路由表
4. 输出「每任务最低成本达标模型」时，PC-i9 与 mac-mini 的 tokens/s 差异会换算成统一成本口径（每万 token 处理耗时）

## 六、路线 A 定案与配置指引（2026-08-18 探测后）

**探测结果**：驱动 595.97 ✅（≥560）｜Ollama 0.32.13 ✅（≥0.32）｜实例未运行（需启动 ollama serve）｜本地模型 11 个（mistral:7b / qwen2.5:7b / llama3.1:8b / deepseek-r1:8b / llava:7b / glm-ocr / moondream 等）｜C 盘剩 17.7GB ✅

**定案**：路线 A（Ollama 复用）✅，无需 CUDA Toolkit / LM Studio。

**远程配置步骤（Windows，向日葵 cmd2 可执行）：**

1. 设环境变量（管理员 cmd，setx 仅对新进程生效）：
```bat
setx OLLAMA_KV_CACHE_TYPE q8_0
setx OLLAMA_FLASH_ATTENTION 1
setx OLLAMA_CONTEXT_LENGTH 8192
setx OLLAMA_MAX_LOADED_MODELS 1
setx OLLAMA_KEEP_ALIVE 30m
```
2. 重启 Ollama（先彻底退出再启动）：
```bat
taskkill /IM "ollama app.exe" /F
start "" "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"
```
   若托盘模式启动不了，退路：start /b ollama serve（前台进程，会话结束会停，仅应急）。
3. 验证：
```bat
ollama list            && :: 不再报 could not connect
ollama run qwen2.5:7b "hello"   && :: 首次加载
nvidia-smi             && :: 看 ollama 进程是否占显存
ollama ps              && :: 显示已加载模型与占用
```
4. 质量回退预案：若评估出现质量回退（q8_0 KV），把 OLLAMA_KV_CACHE_TYPE 改回 f16（显存压力增大但更稳）；若某模型 flash attention 报错，先 setx OLLAMA_FLASH_ATTENTION 0 再重启。
5. 约束：8GB 显存主力 7–8B Q4；勿拉 14B（C 盘+显存都不够顺跑）；云模型（minimax-m2.5/glm-5/gpt-oss）不参与本地评估。

---
*PC-i9 推理栈依赖清单 v2（路线 A 定案）· 2026-08-18 · 算力优化调研子代理*
