# 星台 App Funnel 链路验证清单（三期③ · 待用户手机配合）

现状：Funnel /sb 代理 127.0.0.1:8820（星台桥）返回 401=鉴权在岗 ✓；根路径 200 ✓。
验证步骤（手机上）：
1. 星台 App 打开 → 发一条测试消息给「星桥」
2. 预期：App 消息 → Funnel /sb → 星台桥 8820 → mobile-inbox → central-inbox → 我的会话
3. 判据：我侧 agent-bus 出现 from=手机侧消息（wake=inject）；App 收到回复
4. 若不通：查 8820 桥日志 + /sb 401 是否 App 侧 token 过期

## 执行记录（2026-10-03 09:2xZ · 星桥）

- **服务端实证全通过**：/api/chat（POST，22ms，自测消息经全链到达协调者会话 ✅）、/api/reply（200 有历史回复）、/api/devices、/api/queue、/api/morning-brief、/api/pending-decisions 全部 HTTP 200（均经 Funnel 公网 URL 实测）。
- **App 配置核验**：StarBridgeApp/BridgeConfig.swift baseURL=https://coreymac-mini.taild3fd86.ts.net/sb、token 与桥 .token 逐字符一致 ✅。
- **用户报告「星台提示 app 不再可用」→ 初步判定手机侧网络**：数据线连 mac ≠ 手机有网；App 走公网 Funnel，需 WiFi/蜂窝。待用户确认网络状态与 App 报错文字；若网络正常仍失败，查 App 旧 build 重装。
- 判据状态：服务端链路 ✅ / 手机终端 UI 实证 ⏳（等用户两答）。

## 后续项（2026-10-03 登记）

- **mobile-reply 自动化缺口**：当前「我回复手机消息 → notes/mac-mini/mobile-reply/latest-main」靠协调者手工写卡（历史先例：恢复核验回复）。自动化候选：central-inbox 注入 mobile-inbox 卡时携带来源标记（from:sb-mobile），agent-way reply-guidance 分支（1.5.9+）识别该标记 → 自动写 mobile-reply 卡。排入下一版本批次（1.5.12/0.2.11 或独立小补丁），不在当前已发批次内加塞（防包churn）。

## 星台「App 不可用」根因判定（2026-10-03 09:5xZ）

- 用户报告手机上 App 直接显示「App 不可用」。服务端全链此前已实测全通（/api/chat 22ms 达协调者会话、/api/reply 可取到新回复卡）⇒ 排除链路。
- 判定：**iOS 侧载签名过期**（免费开发者账号 7 天窗口）。依据：①「App 不可用」为 iOS 系统级提示（Apple 拦截未通过校验的 App，非 App 内文案——Swift 源码无此字符串）②项目配置 DEVELOPMENT_TEAM=XS7SMKFS42、bundle=com.starbridge.mobile（免费侧载典型）③时间吻合：桥 9-24 重启后装过 App，10-03 恰超 7 天 ④「之前能用、现在不能」。
- 修法（用户侧）：Xcode（/Applications/Xcode.app 在位）打开 StarBridge.xcodeproj → 选手机 → ⌘R 重签重装 → 如提示信任：设置→通用→VPN与设备管理→信任。
- 长期方案：Apple Developer 付费（1 年签名）或 TestFlight。
- 待确认：用户重装后打开 App 应看到 17:37 的【星台回复测试】消息 → 全链收口。

## 自动化重签重装 SOP（2026-10-03 实测成功）

```
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
cd ~/sb-mobile/ios/StarBridge
xcodebuild -project StarBridge.xcodeproj -scheme StarBridge \
  -destination 'id=00008140-00042D413C09801C' -configuration Debug \
  -allowProvisioningUpdates -derivedDataPath /tmp/sb-dd build
xcrun devicectl device install app --device 00008140-00042D413C09801C \
  /tmp/sb-dd/Build/Products/Debug-iphoneos/StarBridge.app
```
- 实测：构建成功（签名 coreyleung@me.com L65PW2JJCW + Team Profile com.starbridge.mobile）→ devicectl 安装 0 失败。
- 手机端一次性信任：设置→通用→VPN 与设备管理→信任开发者（每台设备重签后一次）。
- 7 天窗口：下次到期（约 10-10）直接重跑本 SOP，无需 GUI。

## 星台↔xingqiao 通道规范审查结果（2026-10-03 10:3xZ · 用户反馈触发）

6 处违规/缺陷（详见本轮汇报表）：①bus-mrole 角色信封无人消费 ②角色离线→to=null 死排队 ③星桥通道回复键不匹配（main vs 完整id）④to=null 存量 207 条 ⑤信封缺 reply_required/notify_only/subject ⑥session 值双轨。
- 已补救：回复双键写入 ✅ · 「测试」代投数据调查员（实时送达+唤醒）✅。
- 下批次（0.2.11 + bridge v-next，与 mobile-reply 自动化合并）：①role-mapped-offline 改排完整 id 待唤醒投递 ②桥 /api/reply 加 latest-<session>→latest-main fallback ③桥星桥通道统一 session='main' ④信封补语义字段 ⑤bus-mrole 消费逻辑归位（central-inbox 专用解析或 agent-way 角色路由）。
- 现网临时约定：用户向某角色发消息前确认其在线；离线角色消息改走星桥通道由协调者代转。

## 收口（2026-10-03 10:51Z · 用户 App 实证）

用户 App 发「看到你的信息」（17:51:46Z，星桥通道，session=fa1f9150）→ 协调者会话收到 ⇒ App→服务端 ✅；用户确认看到我的双键回复 ⇒ 服务端→App ✅。星台「不再可用」事项正式收口（根因=签名过期，重签重装+信任+启动+双键回复全链实证）。

## 打包 SOP 修订（2026-10-03 MBP 部署陷阱回执）

- ★ 包必须含 cordis.patch.yml（package.json files 声明了它；漏带=事故#3/#4 形态：rsync --delete 会删线上那份 → 下次重启 boot fatal）。
- 发布卡附 sha256（tar.gz 前 16 位），对端解包前先校验。
- 部署侧：cp -R 覆盖、不 --delete；读回断言 cordis.patch.yml 仍在位。

## 打包 SOP 再修订（2026-10-03 MBP 可复现打包教训）

- ★ tar 必须可复现：TarInfo 规范化（mtime=0/uid=gid=0/uname/gname 空/条目排序）+ gzip mtime=0 ⇒ 同内容同 sha256（普通 tar czf 哈希不可复现=哈希校验被架空）。
- 交付协议：PUT 后冻结不再重发；重发必须标 version=N，对端按 version 取；卡文哈希与板值必须一致。
- 发货走 publish-package.py（自举发包器，规范化打包+双板回读）。

## 三包完整哈希登记（2026-10-03 MBP 实算核准）

- agent-way-1512.tgz:    ce0891a51eb23a97442b8ab20aa1772c036374affc7e627b8298bfd9f29c8355
- central-inbox-0210.tgz: 7f47aed6eafc7e69317fc83c03e3e9de102ad4f64bfc801bcc95813b7ad4a154
- bb-card-send-112.tgz:   f174a1295c57017bb5fdd141af20d5150d450337498f37391e0ee7419041a2b2
- 哈希约定：卡上给完整 64 位（16 位前缀只识别不校验）；打包可复现（见上节）；PUT 冻结+版本取用。
