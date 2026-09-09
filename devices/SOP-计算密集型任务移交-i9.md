# SOP：计算密集型任务移交标准流程（mac-mini → i9）

> 版本：v1.0 · 2026-08-27 · 起因：34 图 OCR 因本机内存不足（余量 ~156MB，需 >8GB）无法执行 + LM Studio 视觉模型跑崩
> 适用范围：所有智能体（中枢协调者 / 文档摄取 / learning / QA / 运营 等）

## 一、触发条件（遇到以下任一情况，走本 SOP）

1. **资源不足**：本机内存/CPU 不足以执行任务（如 OCR 需 >8GB，本机不足）
2. **计算密集型**：图片 OCR / 视觉标注 / 图像分析 / 大规模批处理 / 模型推理
3. **平台约束**：macOS 不支持的能力（如 Windows 专属工具/驱动）
4. **已确认能力转移**：i9 有 GPU-CUDA + ollama 视觉/OCR 模型（glm-ocr/moondream/llava），本机无

## 二、默认归属（已确认，2026-08-27）

| 任务类型 | 执行节点 | 原因 |
|---|---|---|
| 图片 OCR（文字提取） | **i9** | GPU + glm-ocr 专用模型 |
| 视觉标注（花型/配色/包装） | **i9** | GPU + moondream/llava |
| 图像分析 / 视觉理解 | **i9** | 同上 |
| 摄取管道 / 归档 / 解析结构化 | mac-mini | 非计算密集 |
| 大模型推理（7B+） | i9 | 本机内存不足（跑崩过） |

## 三、执行步骤（用工具一键完成）

```bash
# 一键移交（打包→任务卡→通知→台账，四步自动）
python3 ~/dsh-collab/scripts/task-handoff.py \
  --name "34图OCR" \
  --files ./images/ ./metadata.csv \
  --to i9 \
  --task-type ocr \
  --priority P2 \
  --desc "34 张图片 OCR（glm-ocr 本地执行）"
```

### 手工步骤（无工具时）
1. **打包**：`tar -czf /tmp/task.tar.gz <数据>` → 复制到 `~/dsh-collab/datasets/shared/`
   - genebank 下载 URL：`http://100.120.203.20:8801/shared/<文件名>`
2. **任务卡**：`PUT /tasks/i9/queue/<ts>-<key>`（含 task_id/desc/数据URL/排期/回报要求）
3. **通知**：`PUT /notes/i9/coordinator-task-<key>`（i9 消息通道）
4. **台账**：`PUT /data/handoffs/<ts>-<key>`（移交记录，可追溯）

## 四、关键通道（i9 可达）

| 通道 | 地址 | 用途 |
|---|---|---|
| 黑板 KV | http://100.120.203.20:8792 | 任务卡/消息/台账 |
| genebank 共享 | http://100.120.203.20:8801/shared/ | 文件交付 |
| i9 消息 | notes/i9/* | 通知/回报 |
| i9 队列 | tasks/i9/queue/ | 任务派发 |

## 五、回报闭环

i9 完成后：
1. 结果放 genebank `/shared/`
2. 写黑板 `notes/mac-mini/`（to: mac-mini）汇报
3. 中枢协调者确认后归档 `data/iterations/`

## 六、边界（不做）

- ❌ 本机不跑 OCR/视觉计算（内存不足，会崩）
- ❌ 本机不加载大模型推理（LM Studio 视觉模型跑崩教训）
- ❌ 计算密集型任务不在本机排队等待（直接移交 i9）

## 七、相关文档

- `视觉模型-禁用决策-20260827.md`（本机不跑视觉模型的决策）
- `notes/collab/coordinator-ocr-to-i9-decision`（OCR 移交决策）
- `notes/collab/coordinator-channel-protocol-ocr-add`（规范追加）
- `task-handoff.py`（一键移交工具）

## 八、版本记录

- v1.0（2026-08-27）：初版。基于 34 图 OCR 移交 + 图片标注移交的实际流程沉淀。
