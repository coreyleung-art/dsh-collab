# CLD 重签预案 · 执行版（3d490920 备 · A4 延续）

> 2026-09-02 · 触发：cld-oom plan v5 B 方案（runtime 核心包替换后重签）
> 依据：A4 预案 v3（此前 fa1f9150/75815fa9/43b1a2d3/582093dd 分工矩阵）

## 0. 前置确认
- runtime 核心包替换完成（dsh-runtime 或 app.asar 变更）后执行本预案。
- 变更前后 sha256 清单留档（对照用）。

## 1. 备份/基线（75815fa9 职责）
```bash
ditto /Applications/CLD.app /Applications/CLD.app.bak-resign-$(date +%Y%m%d-%H%M)
codesign -dvvv /Applications/CLD.app 2>&1 | tee /tmp/cld-codesign-baseline.txt
shasum -a 256 /Applications/CLD.app/Contents/Resources/app.asar /Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh/lib/bin.js > /tmp/cld-sha-baseline.txt
```

## 2. 重签（执行方 fa1f9150 或本会话按指示）
```bash
codesign --force --sign - /Applications/CLD.app   # 先不加 --deep
codesign --verify --deep --strict /Applications/CLD.app 2>&1
# 若嵌套组件（Frameworks/dsh-runtime）仍报错 → 补：
codesign --force --deep --sign - /Applications/CLD.app
spctl -a -vv /Applications/CLD.app 2>&1
```

## 3. 复测（3082 headless）
```bash
CLD_BIND_HOST=0.0.0.0 CLD_PORT=3082 CLD_HEADLESS=1 /Applications/CLD.app/Contents/MacOS/CLD &
# 观察 ~/.cld/logs/dsh-web.log：出现 dsh web: http://127.0.0.1:<port> 且无 error 即通过；kill 后清理
```

## 4. 本会话复检职责（重签后）
- app.asar 可读性抽查：Electron 读取器读 main.js 完整 + integrity 通过（命令：ELECTRON_RUN_AS_NODE=1 CLD -e "readFileSync('.../app.asar/main.js')"）。
- 退出留痕冒烟：exit-marker/heartbeat/crash-reason 三文件正常（0600、心跳更新）。
- 若与 CLD-002 同窗：顺序=先装补丁→再重签（seal 封入新 asar）。

## 5. 回滚
```bash
rm -rf /Applications/CLD.app && ditto /Applications/CLD.app.bak-resign-* /Applications/CLD.app
```

## 备注
- 已知态：adhoc/linker-signed（Sealed Resources=none），重签后告警 `code has no resources...` 可能仍存在（此前多会话定论：非阻断）。
- plan v5 文件当前不在盘（data/recovery/ 仅 handshake 文件）——本预案按 A4 既有口径备妥，可随时执行。