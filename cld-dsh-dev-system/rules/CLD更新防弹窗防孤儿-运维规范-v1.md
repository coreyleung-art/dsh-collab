# CLD 更新防弹窗/防孤儿实例 · 运维规范 v1

> mbp-ops · 2026-09-06 · 源自 09-06 mac-mini 弹网页事故复盘
> 目的：让每一次 CLD 更新/重启都自动规避两类问题——① dsh 弹浏览器 ② 孤儿实例并存
> 配套：guard-cld-release（版本管理）+ cld-monitor（多实例守护）+ 规则全集

---

## 一、两类问题的根因（先记住为什么）

### 问题 A · 更新后弹浏览器
**根因**：dsh 没收到 `--no-open` 参数。
- v0.6.1 起 main.js **399 行硬编码** `dshArgs = [... "web", "--port", "0", "--no-open"]`（GUI 正常路径必有）
- 但**非 GUI 启动路径**（auto-relaunch plist / 自定义脚本 / 手动 spawn）**绕过 399 行** → dsh 认为该开浏览器
- 判定：dsh-web.log 出现 `opening the default browser; pass --no-open to disable`

### 问题 B · 孤儿实例并存
**根因**：多启动器/自动重启残留旧进程。
- 正常实例（壳 7455 + dsh 7460）+ 孤儿旧实例（ppid=1 被 launchd 收养）并存
- 后果：端口冲突 + 旧实例弹窗 + 版本混乱
- 判定：`pgrep -f "CLD.app/Contents/MacOS/CLD"` 出现 >2 个（壳+多 dsh）

---

## 二、更新/重启后的强制验证清单（C-verify）

**每次 CLD 更新或异常重启后，必跑以下 4 项**（机械执行，可脚本化）：

```
C-v1 进程命令行含 --no-open
     ps -p <dsh_pid> -o command= | grep -- "--no-open"
     期望: 命中（GUI 路径 399 行保证）

C-v2 无浏览器打开
     grep "opening the default browser" ~/.cld/logs/dsh-web.log | tail -1 的时间戳
     期望: 晚于本次启动时间 = 无新弹窗（历史记录不算）

C-v3 单实例（无孤儿）
     pgrep -f "CLD.app/Contents/MacOS/CLD" | wc -l
     期望: ≤2（1 壳 + 1 dsh）；>2 = 有孤儿需清理

C-v4 心跳健康
     tail -1 ~/.cld/logs/heartbeat.json
     期望: pid 匹配当前壳 + uptime 持续增长
```

---

## 三、更新流程规范（含防复发）

### 3.1 启动方式统一（最关键的纪律）
```
✅ 只用 GUI 启动: open -a CLD   （保证走 main.js 399 行 → 带 --no-open）
❌ 不用旧 plist / 自定义 spawn 启动（会绕过 399 行）
```

### 3.2 更新前
1. `guard backup` 全资产（asar/icon）
2. 检查无旧启动器残留：`ls ~/Library/LaunchAgents/ | grep -i cld`（应只剩 .bak 或空）
   - 有 com.dsh.cld-auto-relaunch 等 → 移入 guard/backups/plists/

### 3.3 更新后（重启完立即）
1. 跑 C-v1 ~ C-v4（见上）
2. `guard-cld-release verify` 版本一致
3. cld-monitor 跑一次确认无告警

### 3.4 若弹窗/孤儿出现（应急）
```
弹窗:   ps 查 dsh 命令行 → 无 --no-open → 杀该实例 → open -a CLD 干净重启
孤儿:   pgrep 列全部 → 保留最新壳+dsh, 杀其余(kill -9)
```

---

## 四、工具化保障（已落地）

| 工具 | 防什么 | 状态 |
|---|---|---|
| main.js 399 行 `--no-open` | GUI 路径防弹窗 | ✅ v0.6.1 |
| cld-monitor 多实例守护 | 孤儿实例 → critical 告警 | ✅ 已加(只统计纯壳) |
| guard-cld-release | 版本指纹管理 | ✅ |
| 本规范 C-v1~C-v4 | 更新后启动健康 | 待接入 verify |

### 待办：guard-cld-release verify 扩展
在 `cmd_verify()` 加 C-v1~C-v4 检查（需 dsh 运行态探测），使版本 verify 同时验证"启动健康"。

---

## 五、考古闭环关联
- 根因模式：M3（重启竞态/启动器冲突）
- 本次经验已入：黑板 20260906-弹网页根因-解决.md + 本规范
- 后续任何更新必查本规范 C 清单

---

*基线：2026-09-06 · 配套 guard-cld-release / cld-monitor / 规则全集-v2*
