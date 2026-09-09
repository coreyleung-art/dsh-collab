# 鲜花图片训练数据集 · Dataset Manifest

> 归集：session-5a5368af（设备协调）· 2026-08-18 · 源：MBP ~/Downloads/鲜花图片训练数据集（rsync 全量传输）
> 摄取：session-55d4d1bd（文档摄取）· 登记：本清单供语义索引（图片/权重本体不入向量库）

---

## 一、数据集概览

| 项 | 值 |
|---|---|
| 名称 | 鲜花图片训练数据集（flower-yolo） |
| 位置 | `~/dsh-collab/datasets/flower-yolo/` |
| 大小 | 3.2 GB（3,088,905,221 字节） |
| 文件数 | 133,472 |
| 来源 | MBP（MacBook-Pro）~/Downloads/鲜花图片训练数据集 |
| 归集方式 | rsync 全量传输（2026-08-18，SSH 通道，exit 0 完整） |
| 用途 | 花卉识别目标检测训练（YOLO 格式） |

## 二、目录结构

```
flower-yolo/
├── 102类花卉识别目标检测数据集_YOLO格式(赠送yolo训练好的模型)/
│   ├── classes.txt               # 102 类英文标签
│   ├── classes_chinese.txt       # 102 类中英对照（UTF-8）
│   ├── dataset_classes/          # 分类图片（按类别）
│   ├── dataset_split/            # train/val/test 划分（images + labels）
│   ├── run/                      # 训练运行记录
│   └── training_charts.png       # 训练图表
├── dataset/
│   ├── classes.txt               # 24 类标签（GBK 编码）
│   ├── gen.py                    # 数据集生成脚本
│   ├── images/                   # 图片集
│   ├── train.txt                 # 训练文件清单（GBK 路径）
│   └── test.txt                  # 测试文件清单
├── dataset(1)/                   # dataset 副本
├── yolov8模型权重（含有训练日志）/
│   └── yolov8n_weights/          # yolov8n 训练权重 + 日志
│       ├── args.yaml             # 训练参数
│       ├── F1_curve.png / PR_curve.png / P_curve.png / R_curve.png
│       ├── confusion_matrix.png / confusion_matrix_normalized.png
│       ├── best.pt / last.pt     # 权重文件
│       └── results.csv           # 训练指标
└── 分类好 flowers/               # 分类图片集（Cyclamen/Hibiscus/rose/tulip 等 10+ 类）
```

## 三、关键元数据

- **主数据集**：102 类花卉识别目标检测（YOLO 格式），含 dataset_split（train/val/test）+ labels
- **赠送权重**：yolov8n 训练好的模型（best.pt/last.pt + 完整训练日志/曲线/混淆矩阵）
- **辅助集**：dataset/（24 类）+ dataset(1)（副本）+ 分类好 flowers/（英文类名目录，如 rose/tulip/sunflower/daisy）
- **中英对照**：classes_chinese.txt（UTF-8，如 pink_primrose=粉红报春花）

## 四、编码注意

- `dataset/classes.txt`、`train.txt`、`test.txt` 为 **GBK 编码**（中文路径乱码）——摄取/使用时需转 UTF-8（`iconv -f GBK -t UTF-8`）
- `102类.../classes_chinese.txt` 为 UTF-8 ✓ 可直接读取

## 五、摄取范围（方案 A+B 约定）

| 内容 | 处理 |
|---|---|
| 图片/权重/模型文件（133,472 中绝大多数） | ✅ 已存数据集目录，**不入向量库**（ChromaDB 不适配图片/权重） |
| 本 manifest（索引） | ➡ 走摄取管道入 research 可检索（「flower-yolo 数据集在哪/有什么」） |
| classes_chinese.txt / args.yaml / 训练说明 | ➡ 可选：轻量摄取（类别清单/训练参数可检索） |

## 六、更新日志

| 时间 | 变更 |
|---|---|
| 2026-08-18 | 首版：MBP 归集完成（rsync 3.2G/133,472 文件），manifest 生成供摄取 |
