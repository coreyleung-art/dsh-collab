# 用户终端操作清单（一次性执行 · 2026-08-18）

> 维护：HR 驾驶舱 a17a52f8 · 顺序：**先 A3 补丁 → 再 A4 重签**（同窗口双落地）
> 说明：沙箱无法写 /Applications（OS 硬封锁），以下必须用户在 macOS 终端执行

## ① A3 · CLD-002 看门狗安装（app.asar 替换）

```bash
# 1/3 备份原 asar
cp /Applications/CLD.app/Contents/Resources/app.asar /Applications/CLD.app/Contents/Resources/app.asar.bak-cld002-20260817

# 2/3 替换为 v2.1 看门狗版（来源 ~/CLD/app-cld002.asar）
cp ~/CLD/app-cld002.asar /Applications/CLD.app/Contents/Resources/app.asar

# 3/3 核对
ls -la /Applications/CLD.app/Contents/Resources/app.asar
#   ↑ 应为 92346 字节
shasum -a 256 /Applications/CLD.app/Contents/Resources/app.asar
#   ↑ 应 = fb70a9b89869181bb2c7090b005d8ff0b6d91a295c1c53eefca38921422c35b7
```

## ② A4 · CLD-012 重签（预案 v3，同窗口执行）

```bash
# 1/5 ditto 备份
ditto /Applications/CLD.app /Applications/CLD.app.bak-20260818

# 2/5 清理残留 + 重签
rm -f /Applications/CLD.app/Contents/Resources/app.asar.bak-20260816
xattr -cr /Applications/CLD.app
codesign --force --deep --sign - /Applications/CLD.app
#   ↑ verify 不过则补 --deep

# 3/5 验证
codesign --verify --deep --strict /Applications/CLD.app
spctl -a -vv /Applications/CLD.app

# 4/5 headless 复测
CLD_HEADLESS=1 CLD_PORT=3082 复测
```

## ③ 其他用户终端项（可选/待确认）
- media-hub/forum launchd 常驻：`launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.media.hub.plist` + com.media.forum.plist（54e809ed/582093dd）
- 内存 purge（可选，授权在案）：`sudo purge`（清 ~5GB inactive，缓解 swap 93%）
- dsh-docs 每日同步 launchd（可选，582093dd）

---
*执行完成后回报：A3 → 3d490920 验收（exit-marker/heartbeat + exit-trace）→ 9910d4b2 转 done；A4 → 582093dd verify + 3082 复测 + QA 验收。HR 统一登记闭环。*
