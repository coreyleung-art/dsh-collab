# 重启操作卡 v2 · 架构二期重启窗口（2026-10-02 晚）

> 给你（用户）的一张卡：照做 → 看数 → 不达标怎么回滚。
> 覆盖：A6 第 4 层 / I7a 唤醒 / D2 镜像防回声 / 两工具挂载（挂载待你授权红线）/ 11 个 launchd 恢复。

---

## 1. 本轮重启会落地什么（代码已备好并自检，未重启）

| 改动 | 文件 | 重启前验证 | 重启后验收 |
|---|---|---|---|
| A6 第 4 层（裸标签自回声） | agent-way 1.5.7 + comm-shared 1.0.1（identity-variants.json 20 身份/37 变体/0 分裂） | 等价模拟 8/8；selfcheck A6-variants PASS | 五形态探针 5/5 拦（含「星桥」） |
| I7a reply_required 唤醒 | agent-way 1.5.7 + central-inbox 0.2.2 | 语法+selftest 15 PASS | MBP 发 reply_required:true 卡 → 我无用户输入被唤醒 |
| D2 镜像防回声按 from | sync-from-central.py v1.1（含 --warm） | is_self_from 8/8；正负例实测（d2-pos ✓/d2-neg ✓） | 部署：先 --warm 预热再重启 job |
| 两工具挂载 | dsh-plugin-bb-card-send / dsh-plugin-launchd-scan | 各自 --selfcheck/--lean4-check A-F 全绿 | profile 挂载后会话可见两工具（挂载动作待你授权红线文件写入） |
| 11 个轻量 launchd 恢复 | launchd bootstrap | launchd-scan 扫描 71=56+15 | 扫描变 71=67+4（未恢复的 4 个=需你决策项） |

## 2. 照做（顺序）

1. **授权/执行挂载**（仅当你要两工具进会话）：`~/.dsh/profiles/web/package.json` 的 `dsh.profile.bundles` 加 `dsh-plugin-bb-card-send`、`dsh-plugin-launchd-scan`；`~/.dsh/profiles/web/node_modules/` 下建两个 symlink（包内声明名）→ `~/dsh-plugin-bb-card-send`、`~/dsh-plugin-launchd-scan`。该文件在不可写红线清单，需要你批准或指定通道。
2. **恢复 11 个轻量 job**（你批的清单）：逐个 `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.dsh.<label>.plist`。
3. **部署 sync v1.1**：`kill` 旧 sync-from-central 进程（launchd 会拉起新代码）；先 `python3 sync-from-central.py --warm` 一次（防历史回灌）。
4. **重启 CLD**（GUI 退出重开）。
5. 打开本会话说"验收"，我会跑 `python3 ~/dsh-collab/scripts/post-restart-acceptance.py`（预期含新增 A6-variants 项全过）+ 五形态探针 + A6/I7a 行为复测。

## 3. 回滚点

| 问题 | 回滚 |
|---|---|
| A6/I7a 异常 | agent-way `git`/备份回 1.5.6（guard/backups 有 15+ 份 bak-good）；comm-shared 回 1.0.0 |
| sync v1.1 异常 | `cp` guard 备份 `hb-forward.py` 同目录的 sync 备份；或 kill 进程 + 旧代码在备份中 |
| 挂载失败 | 从 bundles 移除两行 + 删 symlink 再重启 |
| launchd 恢复异常 | `launchctl bootout gui/$(id -u)/com.dsh.<label>` 逐个卸载 |

## 4. 一句话状态

代码侧、验收侧、回滚点全部就位；只差：你批挂载红线操作 + 定重启时间。
