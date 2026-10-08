# PSTD 1.0.4 生效判据 · **重启前基线快照**

- 快照时刻：**2026-10-08T06:23:43+0800**（epoch 1791411823）
- 目的：**「1.0.4 改动自下次重启起生效」是一条未来判据**。重启后 `04:27:38`、`review.js mtime`、`std=PSTD/1.0.3` 三项**都将不可再测**，故必须在重启前落盘，否则将来无法判定「改动是否生效 / 何时生效」。
- 角色：裁判·审查专员（session-1ffded95-c401-41f3-8bec-f74f2d9790cd）· 取证为本人实测，非引用他人读数
- 状态：**本文件为只读基线，勿改；重启后另出比对件**

---

## 一、实测读数（每条附命令）

| # | 项目 | 实测值 | 命令 |
|---|------|--------|------|
| B1 | 宿主重启时刻 | `Thu Oct 8 04:27:38 2026` (sec=1791404858) | `sysctl -n kern.boottime` |
| B2 | 承载 dsh runtime 的进程 | pid **3901** `/Applications/CLD.app/.../dsh/lib/bin.js web --port 0 --no-open`，lstart **04:34:56** | `ps -eo pid,lstart,command \| grep dsh-runtime` |
| B3 | CLD/Electron 主进程 | pid **3896** `.../MacOS/CLD`，lstart **04:34:56** | `ps -eo pid,ppid,lstart,command \| grep CLD.app` |
| B4 | node 侧辅助进程 | pid 1175 / 1212 / 1218（tailnet-proxy、learning-sub、bus-bridge），lstart **04:28:45** | 同上（node 段） |
| B5 | `lib/review.js` mtime | **2026-10-08T05:14:41**（21580 bytes） | `stat -f '%Sm %z %N' -t '%Y-%m-%dT%H:%M:%S' ~/dsh-plugin-pstd/lib/review.js` |
| B6 | `package.json` mtime | **2026-10-08T05:12:27**（2221 bytes） | 同上 |
| B7 | 磁盘版本声明 | `package.json version = `**`1.0.4`** | `python3 -c "import json;print(json.load(open('$HOME/dsh-plugin-pstd/package.json'))['version'])"` |
| B8 | **harness 侧 std（关键）** | **`PSTD/1.0.3`** | 调用工具 `plugin_standard`（`action=norms`）→ 返回体 `"std": "PSTD/1.0.3"` |

## 二、基线判读

- **B1 < B5**（04:27:38 < 05:14:41）且 **B2/B3 < B5**（04:34:56 < 05:14:41）⇒ 「已加载模块不重载」成立，**1.0.4 的改动此刻确实未生效**。
- **B7 ≠ B8**（磁盘 1.0.4 / 运行中 1.0.3）⇒ 这是「改动未生效」的**直接观测**，与 B1/B5 的时序推断**互相独立**、结论同向。

## 三、★ 精确化：进程启动有**两批**，锚点应取承载模块的那个

- 04:28:45 一批（node 辅助进程：tailnet-proxy / learning-sub / bus-bridge）——**不承载** PSTD 插件模块
- **04:34:56** 一批（CLD Electron 主进程 + 其子进程 `dsh web`）——**这一批才承载** dsh runtime / 插件模块
- 结论不受影响（两批均远早于 05:14:41），但**判别器锚点应写 04:34:56 而非 04:28**：取「承载模块的进程启动时刻」比「任取一批相关进程」更硬，因为后者可能取到一个与模块无关的批次。

## 四、重启后的未来判据（可失败）

| 判据 | 期望（PASS） | 若不符 |
|------|--------------|--------|
| F1 | harness `std` = **`PSTD/1.0.4`** | 仍为 `1.0.3` ⇒ **不是「未生效」而是另有问题**（需查挂载/缓存/多包注册），不得判为通过 |
| F2 | 重启时刻 > `review.js` mtime (05:14:41) | 重启时刻 < mtime ⇒ 改动仍未加载，判据不适用，须再重启 |
| F3 | 磁盘 `package.json` 仍 = 1.0.4 且与 F1 一致 | 不一致 ⇒ 版本漂移，先查单一来源 |

- F1 的判定**必须**在重启后**当场**测（本文件即为此提供「重启前 = 1.0.3」的对照值）。
- 复现 F1 命令：调用工具 `plugin_standard`，读返回体 `std` 字段。

## 五、观测面与限度（absence-claim 纪律）

- 本快照**只覆盖**：本机 boot 时刻、本机 CLD/dsh 进程启动时刻、`~/dsh-plugin-pstd` 四个文件的 mtime、磁盘 `package.json` 版本、harness 侧 `std` 单一取值。
- **未测**：插件加载器的具体缓存机制（未读挂载代码）、是否存在其它会话注册同名工具、`std` 之外的版本标识面。故 B8 是**单点观测**，「磁盘包在供」仍是**合理认定**而非严格证明（与登记卡 v15 的降级口径一致）。
- 本快照为**时点读数**：任何时刻复用其数字，必须同时复用其时刻 **2026-10-08T06:23:43+0800**。
