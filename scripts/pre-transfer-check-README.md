# pre-transfer-check · 传输前磁盘余量检查器

> 版本：v1.0.0 · 属主：HR 司库 · R006 九标准全达标
> 定位：传输文件到目标设备（i9/MBP）前的**传输门**——防「传输挤爆磁盘导致崩溃」（i9 C 盘事故教训）

## 命令
| 命令 | 说明 |
|---|---|
| check --file <路径> --target <node> | 传输前检查（文件大小 vs 目标余量） |
| check --size <MB> --target <node> | 按大小检查 |
| status --target <node> | 查目标磁盘现状 |
| selfcheck / version | TCC 自检 / 版本 |

## 门判定
- 余量 ≥ 文件 × 1.5（安全系数）→ GATE:PASS
- 余量 < 阈值 → GATE:BLOCK（建议清理）
- 黑板无数据 → GATE:UNKNOWN（放行但标记人工确认）

## R006 九标准
插件形态（预留）/ TCC（selfcheck）/ CLD 自适应（--cld-check）/ dsh 版本自适应（--version-check）/ 文档（本 README）/ 版本（--version）/ 日志（~/.dsh/pre-transfer-check.log）/ 落链（--sediment 预留）/ CLI 治理

## 示例
python3 pre-transfer-check.py check --file deliverables/festival-pipeline-v1.0.0.tar.gz --target i9
python3 pre-transfer-check.py check --size 40 --target i9
python3 pre-transfer-check.py status --target i9

## 注意
- 目标余量从黑板 nodes/<node> 查询（i9 心跳含磁盘信息；若心跳无磁盘字段则 GATE:UNKNOWN）
- 零 LLM：纯规则 + 黑板查询
