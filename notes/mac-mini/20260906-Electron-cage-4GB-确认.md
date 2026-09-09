# Electron V8 Cage 4GB 硬顶确认（2026-09-06）

## 实测铁证(CLD 二进制直测)
- heap_size_limit 恒 4192MB，无论 --max-old-space-size=8192/4096/直传 全无效
- vscode #127105 / electron #35032 佐证: 官方默认启用 pointer compression 不打算改

## 认知修正(重要)
1. dsh 实际可用堆 = 4GB cage(非以为的 8.4GB!) — 之前 launchctl 8192 从未生效
2. dsh 3.6GB = 已用 90% cage(危险但未崩)
3. OOM 修复真正功臣 = P1 自动重启 + P2-3 减驻留(非扩容)
4. 根除(自编译 Electron 禁 cage)不可行(官方 CLD)

## 可行治理(4GB 内)
1. 定时 GC 缓解(RSS 3.6→~1GB, 已验证)
2. 减驻留(P2-3 已做)
3. cld-monitor 补 dsh RSS 监控(现盲区)

## 报告
tech-research/lab-methods/Node-RSS回缩-深度调研-20260906.md (已更新+向量化)
