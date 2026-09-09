# 全员唤醒实验完成 + resolveUrl 竞态修复（2026-09-05）

## 实验数据
- RSS: 2172→4532MB 峰值(16:24) → 4.4GB 平台 → 无 OOM
- 0 crash ips；CLD 16:44 被 P1 自动重启(pid 71861→81555)

## 两结论
1. ✅ 治理有效: 4.5GB 峰值不 OOM(P1 8.4GB 扩容生效) vs 修复前 4GB 必崩
2. ⚠️ 发现壳竞态: resolveUrl=null 时 stdout URL 行 → TypeError 崩壳(非 OOM)

## 修复 v0.6.1 (五道闸全过)
- stdout handler 加 if(resolveUrl) 保护(440 行)
- asar sha 20880594794c3355 (182279B) 已部署+重签
- 登记 v0.6.1; 待重启生效

## 建议
- 全员唤醒分批(避免瞬时 4.5GB)
- 重启应用 v0.6.1
- stability-watch 跟踪新进程(301MB)
