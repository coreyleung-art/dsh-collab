# d4-2-T1 · flower-yolo 数据源调查（花材检测/识别模型训练数据准备方案）

> 蓝图任务：flower-yolo 花材检测/识别模型的数据准备。调查公开数据集、自采标注方案、标注工具链、数据增强，并给出与 flower-yolo 训练衔接的规模与阶段建议。
> 调研方法：web_search 交叉验证 + 本地 yolo 训练论文（arXiv:2508.15431 小数据集车辆凹痕检测）佐证。

---

## 结论（数据准备方案）

**核心判断：现有公开花卉数据集以「分类」为主、缺乏「目标检测（框标注）」，不能直接喂给 YOLO；必须走「公开集做分类预训练 + 少量自采检测标注 + 点监督/伪标签扩量 + 强增强」的混合路线。**

1. **公开集定位**：Oxford 102 Flowers、iNaturalist、Kaggle 17/5 类等均为**分类数据集（无框）**，适合做 YOLO backbone 的分类预训练/迁移起点，不能直接当检测标注。COCO 80 类里**没有独立 "flower" 类**，只有 "potted plant"（盆栽，id 58），切花/花束无对应，仅能作通用迁移预训练。
2. **可用的检测起点**：Roboflow Universe 的 flower 检测项目、awesome-flowers（CC-BY-4.0）、中文「花卉识别分割 labelme 7111 张/102 类」等有框/分割标注，可转 YOLO 作为**冷启动检测预训练**。
3. **自采是主力**：目标花材（玫瑰/百合/向日葵/康乃馨/绣球/桔梗/满天星/洋桔梗等 SKU）必须自采；用**手机多角度 + 点监督（2412.05837）+ 伪标签（STAC 2005.04757 / Unbiased Teacher 2102.09480）**大幅降低框标注成本。
4. **工具链推荐**：标注主力 **Label Studio（自托管免费 + YOLO 原生导出 + ML backend 预标注）**；有视频/追踪/大量框需求用 **CVAT**；追求开箱即用自动标注（SAM）+ 一键训练导出用 **Roboflow**（免费 3 公开项目）。
5. **增强**：Albumentations（1806.06839）官方 YOLO pipeline 示例直接可用，重点做花材特有的**色彩抖动（花色多变）、遮挡（CoarseDropout/花束互遮）、形变（弹性变换）**。
6. **规模建议**：首期 **20–40 类 × 每类 200–500 张检测框 ≈ 5k–2 万张**，分三阶段（公开集验证 → 自采目标花材 → 点监督/伪标签扩量）。

⚠️ **需纠正的引用**：任务中「2001.08972 伪标签」有误 —— arXiv:2001.08972 实为 **SOLAR: Second-Order Loss and Attention for Image Retrieval**（图像检索，非伪标签）。伪标签半监督检测的正确代表作为 **STAC（2005.04757）**、**Unbiased Teacher（2102.09480）**、经典 Pseudo-Label（2013）。

---

## 公开数据集表

| 数据集 | 规模 | 标注类型 | 许可/版权 | 对 flower-yolo 的用途 |
|---|---|---|---|---|
| **Oxford 102 Flowers** | 102 类，**8189 张**（train/val/test = 1020/1020/6149） | 仅类别标签 + 部分分割 GT，**无检测框** | 网络采集图片，版权不清晰，**商用有风险** | 分类 backbone 预训练；细粒度花种分类 |
| **17 Category Flower Dataset**（Kaggle） | 17 类，约 1360 张（~80/类） | 分类 | 公开，商用谨慎 | 小规模分类预训练/快速验证 |
| **Flower Photos（5 类 / flowers）**（Kaggle） | 5 类（daisy/dandelion/rose/sunflower/tulip），~4323 张 | 分类 | 公开 | 快速原型 |
| **iNaturalist 花卉子集** | iNat2021 全量 2.7M 图 / 1 万种；花卉为 Plantae 子集 | 分类 + 物种级 | **许可混杂（CC-BY-NC 居多，商用受限）**，需按 license 过滤 | 细粒度 backbone 预训练（过滤后） |
| **COCO** | 33 万张 / 80 类 | 检测框 | CC-BY 4.0 | **无独立 flower 类**，仅 "potted plant"（id 58）；作通用迁移预训练 |
| **awesome-flowers**（tudelft-mdp） | 花卉数据集清单 + 图集 | 分类/部分框 | **CC-BY-4.0**（较友好） | 花卉多源汇总，可找检测子集 |
| **花卉识别分割 labelme 7111 张/102 类**（中文公开） | 7111 张 / 102 类 | 分割（labelme） | 公开（教学用，商用需核） | 可转 YOLO-seg/det 作冷启动 |
| **Roboflow Universe flower 项目** | 项目制，规模不一 | 检测框（YOLO 可导出） | 项目作者设定 | **最直接的检测起步点** |

> 关键结论：**「检测框」标注的花卉公开集稀缺**，分类集丰富但不满足 YOLO 检测需求；Roboflow/awesome-flowers/中文分割集是最接近的检测起点。

---

## 自采标注工作流

```
采集 → 预标注（自动/模型）→ 人工校正（框 or 点）→ 导出 YOLO → 训练 → 伪标签回灌
```

1. **采集（手机/摄像头）**
   - 单品花材：正面/侧面/俯视多角度，每 SKU 至少 3 角度 × 5 光照（自然光/暖光/冷光/背光/暗光）
   - 花束/整束：多束组合 + 互相遮挡场景（训练遮挡鲁棒性）
   - 背景：白底（电商图）/ 花店货架 / 包装纸 / 玻璃瓶 等真实销售场景
   - 命名规范：`{sku_id}_{角度}_{光照}_{序号}.jpg`，便于后处理与类别映射
2. **预标注（降人工成本）**
   - 用 Roboflow Annotate 的 **SAM 自动分割/框**，或 CVAT 的 DL 模型 + SAM
   - 用已有 flower 预训练模型（Roboflow Universe / 中文分割集训出的模型）生成**伪标签**
   - 伪标签走 **STAC（2005.04757）半监督框架**：有框集训练 teacher → 无框自采图打伪标签 → 置信度阈值过滤 → 加入训练
3. **人工校正**
   - Label Studio 拉框（YOLO 原生），或用 **单点监督（2412.05837）**：每个目标只点一个中心点，模型自扩框 —— 标注成本从「拉框」降到「点一下」，适合花材密集/遮挡场景
4. **导出与闭环**
   - Label Studio/CVAT/Roboflow 均导出 YOLO txt 格式 → 直接喂 Ultralytics YOLO 训练
   - 训练出的模型回灌做下一轮伪标签，形成 **「标注—训练—伪标签—再训练」闭环**

---

## 标注工具对比

| 维度 | Label Studio | CVAT | Roboflow |
|---|---|---|---|
| 开源/费用 | **开源，自托管免费** | **开源，自托管免费** | SaaS；免费 3 公开项目 |
| 自动化标注 | ML backend（预标注/主动学习） | DL 模型 + **SAM**、视频追踪插值 | **SAM + LLM 自动标注**（免费额度有限） |
| YOLO 导出 | **原生 YOLO 格式** | 经 Datumaro 导出 YOLO | **一键 YOLO + 直接训练/部署** |
| 视频/序列 | 弱 | **强（追踪/插值）** | 中 |
| 适用场景 | 通用、灵活、可编程 | 大规模框/分割、视频 | 开箱即用、边标注边训练 |
| 推荐 | ✅ **花材框标注主力** | 有视频/大量连续帧时 | 快速冷启动 + 自动预标注 |

> 结论：**主 Label Studio + 辅 Roboflow（SAM 预标注）/ CVAT（视频插值）**，三者都能直接产出 YOLO 格式，与 flower-yolo 训练无缝衔接。

---

## 增强策略（花材场景）

衔接 **Albumentations（arXiv:1806.06839，"Fast and Flexible Image Augmentations"）**，官方提供 [YOLO-style pipeline](https://albumentations.ai/docs/examples/example-yolo-style-pipeline/) 与 [bbox 同步变换](https://albumentations.ai/docs/3-basic-usage/bounding-boxes-augmentations/)，Ultralytics 也有 [Albumentations 集成](https://docs.ultralytics.com/integrations/albumentations)。

| 类别 | 花材针对性增强 | 说明 |
|---|---|---|
| 空间 | HorizontalFlip / VerticalFlip / Rotate / ShiftScaleRotate / **ElasticTransform** | 花材形变大，弹性变换贴合花瓣 |
| 色彩 | RandomBrightnessContrast / **HSVShift** / **CLAHE** / RandomToneCurve | 花色多变 + 花店光照不均 |
| 遮挡 | **CoarseDropout** / **GridDropout** / 随机掩码 | 花束互遮、包装遮挡 |
| 混合 | MixUp / **Mosaic**（YOLO 自带）/ CopyPaste | 提升小目标与密集检测 |
| 尺寸 | LongestMaxSize 640 / PadToSquare | 匹配 YOLO 输入 |

> 落地：训练时用 Ultralytics 自带 `hsv_h/s/v`、`flipud/fliplr`、`mosaic` 参数即可覆盖大部分；进阶用 Albumentations 自定义 pipeline 做遮挡与弹性形变。参考 2508.15431（小数据集凹痕检测）——**用实时数据增强弥补小样本**，其 YOLOv8m 变体在仅数百张自采图上达到 mAP@0.5 ≈ 0.60。

---

## 规模与阶段建议

| 阶段 | 目标 | 数据规模 | 标注方式 |
|---|---|---|---|
| **P0 冷启动验证** | 验证 pipeline + 预训练迁移可行性 | 公开集：Roboflow flower + 中文分割集 + Oxford102/iNat（分类预训练） | 现有标注，零成本 |
| **P1 目标花材自采** | 覆盖核心 SKU 检测 | **20–40 类 × 200–500 张/类 = 5k–2 万张** | 框标注为主，密集/遮挡场景用点监督 |
| **P2 扩量** | 提精度 + 长尾覆盖 | 自采无框图 + 伪标签回灌，扩到 **2–5 万张** | STAC 伪标签 + 强增强 |

**建议首期**：先跑通 P0（1–2 天），直接启动 P1 采集 20 类核心花材、每类 300 张（框）+ 100 张（点监督），合计约 6000–8000 张，足够 YOLOv8s/m 训练出可用检测模型；再按需求扩类。

**与 flower-yolo 训练衔接**：
1. 所有标注统一导出 **YOLO txt**（`class x_center y_center w h` 归一化）
2. 建立 `classes.yaml`（SKU ↔ 类别 id 映射，与 `flower-sku-naming-alignment-2026` 命名对齐）
3. 数据目录 `data/flower-yolo/{images,labels}/{train,val,test}`
4. 训练入口接 Ultralytics，增强用 Albumentations 自定义 pipeline 或 YOLO 内置参数

---

## 证据来源

- Oxford 102 Flowers（8189 张/102 类）：[TensorFlow Datasets](https://www.tensorflow.org/datasets/catalog/oxford_flowers102)、[Voxel51/OxfordFlowers102 (HF)](https://huggingface.co/datasets/Voxel51/OxfordFlowers102)
- Flower 检测数据集：[TensorFlow Flower Detection (Zenodo)](https://zenodo.org/records/7768292)、[awesome-flowers (CC-BY-4.0)](https://huggingface.co/datasets/tudelft-mdp/awesome-flowers)
- 花卉分割 7111 张/102 类：[腾讯云 CSDN 文章](https://cloud.tencent.cn/developer/article/2542726)
- COCO 类表（无独立 flower，仅 potted plant）：[Roboflow COCO classes](https://blog.roboflow.com/microsoft-coco-classes/)
- 17/5 类花分类：[Kaggle 17 Flower Dataset](https://www.kaggle.com/datasets/ashfaqsyed/flower-dataset)
- Roboflow 花检测：[flowers_synthetic](https://universe.roboflow.com/yolo-traning/flowers_synthetic)、[Roboflow 导出](https://docs.roboflow.com/datasets/versions/dataset-versions/exporting-data)
- Label Studio YOLO：[YOLO 集成](https://labelstud.io/integrations/computer-vision/yolo/)、[YOLO ML backend](https://labelstud.io/guide/ml_tutorials/yolo)
- 标注工具对比：[Roboflow annotation platforms](https://blog.roboflow.com/data-annotation-platforms/)、[Habr 6000+ 图标注对比](https://habr.com/en/articles/969000/)
- Albumentations：[bbox 增强](https://albumentations.ai/docs/3-basic-usage/bounding-boxes-augmentations/)、[YOLO pipeline](https://albumentations.ai/docs/examples/example-yolo-style-pipeline/)、[Ultralytics 集成](https://docs.ultralytics.com/integrations/albumentations)
- 点监督：Tiny Object Detection with Single Point Supervision（[arXiv:2412.05837](https://arxiv.org/abs/2412.05837)）
- 伪标签（纠正引用）：STAC（[arXiv:2005.04757](https://arxiv.org/abs/2005.04757)）、Unbiased Teacher（2102.09480）；⚠️ 2001.08972 实为 SOLAR 图像检索（[arXiv:2001.08972](https://arxiv.org/abs/2001.08972)）
- 本地参考：Small Dents, Big Impact（[arXiv:2508.15431](/Users/coreyleung/dsh-collab/research/paper-cache/texts/2508.15431.txt)）——小数据集 YOLOv8 训练 + 实时增强方法
