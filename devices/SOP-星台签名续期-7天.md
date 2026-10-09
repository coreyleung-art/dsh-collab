# 星台（Star-tai）App 签名续期 SOP（付费开发者版）

> 维护人：星桥（mac-mini）｜ 建立：2026-10-04 ｜ 触发：每 7 天（下次到期 ≈ 10-10）
> 背景（2026-10-05 更新）：开发者**付费注册已审核通过**（团队 XS7SMKFS42，Zhenyu Liang）。付费证书有效期 **1 年**，7 天续期魔咒解除；本 SOP 降级为「年检 + 构建参考」。
> 当前版本：v9.15（纠错 + 插入 CLD + 成稿弹层 + 草稿管理 + 朗读开关，实测 200）。

## 前置事实（已验证）
- 设备：iPhone 16 Pro，UDID `00008140-00042D413C09801C`
- 构建链：`DEVELOPER_DIR=Xcode 27` + `xcodebuild`（模拟器与真机签名用）
- 安装/启动：`xcrun devicectl device install` / `xcrun devicectl device launch`
- 星台与 CLD 的通道：**服务器中继主通道** `https://xingqiao.meetfunbp.com/sb`（nginx → 反向隧道 18820 → 本机 8820 桥）；ts.net `https://coreymac-mini.taild3fd86.ts.net/sb` 仅作 App 内备用降级。续期验收的公网探针改打 `https://xingqiao.meetfunbp.com/sb/health`（期望 200）。

## 续期步骤（每次到期的标准动作）
1. **确认到期**：手机上 App 打不开 / 或 `xcrun devicectl device list` 看设备在线。
2. **重建**：
   ```bash
   export DEVELOPER_DIR=/Applications/Xcode-27.app/Contents/Developer  # 按实际路径
   cd <星台工程目录>
   xcodebuild -scheme <主scheme> -destination "id=00008140-00042D413C09801C" build
   ```
3. **安装**：`xcrun devicectl device install app --device 00008140-00042D413C09801C <构建产物.app>`
4. **启动**：`xcrun devicectl device launch --device 00008140-00042D413C09801C <bundle-id>`
5. **验收（必须实测，不只「装了」）**：
   - 本机桥健康：`curl -s http://127.0.0.1:8820/health` ⇒ `{"ok":true,"name":"sb-mobile-bridge"}`
   - 公网可达：`curl -s -o /dev/null -w "%{http_code}" https://coreymac-mini.taild3fd86.ts.net/sb` ⇒ 401（鉴权在=桥活）
   - 手机端实测一条语音/成稿流转（v9.15 关键链路：点 📄 → 成稿层 → 逐字滚出 → 发送/仅插入）
6. **登记**：黑板 `data/registry/` 写续期卡（版本号 + 到期日 + 验收证据），并计算下一次到期日（今天+7）。

## 红线
- 续期前先确认 mac-mini 侧 /sb 桥（8820）与 Funnel 路径活着——App 修好但通道断了等于白修。
- 构建/安装命令的 scheme、bundle-id、工程目录必须当场 `ls` 确认，不凭记忆（M5）。
- 验收要「手机端真实动作」证据，不接受「安装成功」作为完成（R030）。

## 已知坑（预填，后续实测补充）
- 免费签名 7 天到期是**静默型**故障（App 无提示直接打不开）——到期日必须日历化（launchd/黑板书签），不靠人记。
- （待补：Xcode 27 路径若变，先 `xcode-select -p` 确认。）
