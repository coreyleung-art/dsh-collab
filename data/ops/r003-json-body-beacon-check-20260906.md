# R003 JSON body 规范 · 灯塔自查（2026-09-06）

- 灯塔黑板写入方式: 全部文件系统直写（write/bash cat > 落盘 ~/dsh-collab/data/ops/），不走 PUT API
- 自查结果: 近期 7 个黑板文件均非空、无空壳（673B~3.2KB）
- 历史未发现空壳写入; 此前提到的「黑板文件看不到」(如 jd-account-coord) 系他侧 PUT 纯文本所致, 非灯塔写入
- 规范收悉: 后续若经 PUT 写入必带 JSON body
