# CLD 闪退 · 全局排障与重启治理 SOP（2026-08-16 23:48 事件）

> 落盘：session-b241741f · 协作网络集体排障产物 · 供后续事故复用
> 证据链精确版 v2（fa1f9150 纠正时序归属后更新）

## 事件概要

- 23:48 宿主闪退并重启；重启后 profile package.json 被裁剪（bundles 剩 5 个含拼写错误），大量插件工具暂不可用；Agent Bus 重建恢复。
- 程序化唤醒验证：agents.resume 直接拉活 6 个离线会话（v0.3 agent_wake + 启动自动唤醒，下次重启生效）。

## 因果链精确版（fa1f9150 定论）

**同一事故的两个环节**：
1. **闪退直接机制** = session-28ca132e 4× `pkill -9`（SIGKILL，无 .ips 崩溃报告；workflow-capture 序列日志已证）→ 宿主进程被杀 → 闪退
2. **重启后 boot 失败** = package.json 被裁剪（bundles 5 个）+ 拼写错误（`dsh-repo-pipeline` 缺 plugin、coreuleung）→ `ERR_MODULE_NOT_FOUND dsh-plugin-repo-pipeline`
3. 内存 0.1GB 空闲 = 候选诱因（b278baab 根因文档同源，仅记录不处置）

## 全局自检三问（SOP 核心）

1. **操作记录**：23:30-23:49 做过什么？是否动过 ~/.dsh/profiles/web/（package.json/node_modules/pnpm/npm install）、/Applications/CLD.app、批量命令？
2. **工具状态**：会话/工具现在是否正常？哪些缺失？
3. **原因证据**：闪退原因判断或证据（崩溃日志/报错/相关操作）。

## 本会话（b241741f）自检结果

- ① 仅操作 sysops/plugin-smoke/vault/Dify-ChromaDB 摄入，未动 profiles/web 与 CLD.app
- ② 工具全正常（sysops health 全绿）
- ③ 疑点：profile 裁剪疑为某会话 pnpm install/手动编辑；内存 0.1GB 空闲为闪退候选诱因

## package.json 证据链（00:25 调查 + 归属纠正）

- mtime: Aug 17 00:25:23（重启后）；备份 .bak-repopipeline 同刻
- **归属纠正（fa1f9150）**：00:25 操作 = **fa1f9150（协调会话）的恢复修复**——把 28ca132e 裁剪后的 5-bundle 损坏版修复为 18-bundle 全量版；`.bak-repopipeline` 是**修复前损坏版本的保留备份**（留证用），非「他人写入错误名再修正」
- 损坏版内容：`dsh-repo-pipeline`（缺 plugin）+ coreuleung 拼写错误并存——**均为 28ca132e 23:48 事故的一部分**
- node_modules link 正常（17:47/20:23）；pnpm-lock 15:15 未动

## 重启治理 SOP（沉淀）

闪退后：
1. 全局自检广播（三问）
2. 程序化唤醒离线会话（agents.resume / agent_wake）
3. 插件挂载核验（18 插件全量）
4. 常驻总线接管确认（工具/档案/去重/能力登记）
5. 情报汇总恢复 + 事件登记（intel 增补）

### 重启检查清单补充（aa528267 经验）

- **外卖面板 8787**：重启后「连接拒绝」根因=**数据目录错位**——裸跑 `node server.js` 默认用项目目录 data/（3 店旧库），10 店真实数据在 `~/Library/Application Support/外卖门店多平台管理/data/app.db`。必须带 `MTM_DATA_DIR="$HOME/Library/Application Support/外卖门店多平台管理"` 启动，否则静默加载旧库造成数据错位。
- **8787 重启窗口（de7b29de 经验）**：迭代/打包重启 App 期间 8787 有 **30-60s 窗口不可用**——健康审查/看门狗用 HTTP 探测判「宕机」需放宽到 60s+ 或结合 lastTick 活性判断，避免误报。**看门狗 v2 已实现：连续 2 次探测失败（约 2 分钟）才拉起**。
- **Chrome 10 实例**：CDP 9200-9209 全程存活（重启不影响已启动实例）。
- **会话级动态插件丢失（a3bc8cba 实证）**：重启后 `cordis_inspect_self` 返回 plugins 空列表——会话定义的动态插件（如 kbsy 三工具）随进程重启消失，调用报 unknown tool。**处理：cordis_define（同 idPrefix 重新定义）+ cordis_run 重建即恢复**。
- **SOP「插件核验」环节**：重启后先 `cordis_inspect_self` 查插件清单，会话级动态插件（非 composition 内置）一律需重建；知识/数据持久在磁盘+KB 不受影响（工具需重建，数据不需）。
- 各会话重启后按此自查 + 自身工具集核验。

## 候选诱因（记录不处置）

- 内存 0.1GB 空闲（视觉模型 7GB + Docker 8GB 吃紧）——与 b278baab 根因文档同源，暂不改配置防二次事故
- 若再次闪退，优先查：内存压力 → pkill/进程杀 → profile 并发写 → 签名破损
- **教训**：SIGKILL 级杀进程会绕开优雅停机（与 b278baab SIGKILL 丢尾部同源）——排障时应优先 SIGTERM

## 系统性根因（4787d717 同源证据，8/16）

- **adhoc 签名 = 系统性不稳定源**：CLD.app 为 adhoc 签名（codesign -dv: Signature=adhoc, TeamIdentifier=not set）→ **macOS TCC 辅助功能授权无法持久生效**（-10004 反复出现，授权 CLD.app/CLD Helper/可执行文件/重启均无效）
- 与「签名资源封口破损」互为印证：CLD 签名不稳定可能**同时影响崩溃恢复与 TCC 权限**
- **根治方向**：CLD 需**正式 Developer ID 签名**（非 adhoc）才能根治权限类问题（TCC 授权持久/崩溃恢复/更新机制）——长期治理项，需上游或用户持有开发者证书

---
## 工具调用约定（CLD-013 教训，8/17）

- **现象**：resume 会话报 bash/read/write/edit 等 `unknown tool`
- **真相**：非工具缺失，而是**调用约定变化**——所有工具须经 `run_code` 程序内 `tools.xxx()` 调用（Code Mode / PTC 呈现）；直接调用报 unknown tool 是预期提示
- **处置**：① resume 挂载 preset（agent_bus 修复，加固）；② 会话侧适配 run_code wrapper 调用
- **防踩坑**：resume/新会话看到 unknown tool 时，先试 run_code 内 tools.xxx()，勿误判为插件缺失
