# 插件化标准对齐 · flower-cockpit v0.2.0

> 1e54d56d · 2026-08-27

## ✅ 已完成
1. **adapt.js**（第4项 dsh 版本自适应）：CJS 版已写入 lib/adapt.js（startAdaptGuard/collectFingerprint/probeCapabilities/logAdapt），apply 里接线（boot-fingerprint 落 ~/.dsh/plugin-adapt/adapt-log.jsonl）
2. **统一文件日志**（第7项）：fileLog 落盘 ~/.dsh/flower-cockpit.log（host ready + API routes registered），CLD stdout 不可见兜底
3. **版本/CHANGELOG**：0.1.0 → 0.2.0，CHANGELOG 记录（adapt + 日志 + ws.register 路由修复）
4. **构建**：tsc 0 错，lib/index.js 7389B（含 adapt/fileLog/appendFileSync）
5. **推送**：git commit 8805d1e + Gitee 推送成功（coreyleung/dsh-plugin-flower-cockpit）

## ⚠️ 待办
- **GitHub 推送受阻**：无可用 PAT（env/keychain/凭据文件均无 GitHub token；gh auth 未登录；repo_pipeline_setup 报 gh 不可用）。Gitee 已推。需用户提供 GitHub PAT 或 gh auth login 后补推。

## 📌 说明
- adapt.js 为 CJS 版（中枢模板 ESM 转 CJS，适配 tsc 构建）
- ws.register 路由修复已在 v0.2.0（重启验证 flower API 真实 JSON）
