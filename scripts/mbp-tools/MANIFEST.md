# MBP 侧运维工具包（MANIFEST）

> 来源：MBP（node `mbp`，session-20b800d4）· 20261004 · 由 `publish-toolkit.py` 脱敏打包
> ★ **所有 token 已替换为环境变量占位**，使用前请设：
> ```bash
> export BB_WEBHOOK_TOKEN=<中枢 webhook token>     # 中枢板写权限
> export MACMINI_BB_TOKEN=<mac-mini 板 bearer>     # 本机板(mac-mini) 写权限
> ```
> （`publish-and-point.py` / `verify-delivery.py` 等仍从 `~/.dsh/blackboard-token` **读文件**，不内联密钥。）

## 一、拉起 / 重启 / 进程生命周期（对应 R043、G36、事故 #6）

| 工具 | 用途 | 用法 | 退出码 |
|---|---|---|---|
| `relaunch-cld.sh` | **可靠拉起**：等旧实例真退出 → `open -a` → **读回验证**（argv0 精确相等 + `exit-marker.startedAt` 更新）→ 有界重试（10×5s≈105s）→ 确认无进程才清陈旧 `Singleton*` → 全程日志 | `relaunch-cld.sh [--wait 30 --attempts 10 --verify 20 --since <epoch>]`；`--selftest`（6 场景/5 负控）；`--dry-run` | 0 已拉起 / 1 尝试耗尽 / 2 用法 / 3 自测失败 |
| `restart-with-guard.sh` | 一体化：先起自带验证守护 → **读回验证守护就绪**（日志含本次 `since=`）→ 再 `POST quick-restart`；守护起不来则**取消重启** | `restart-with-guard.sh [countdown=5] [waitSec=60]`；`SWG_DRY=1` 预演 | 0 ok / 2 无端口 / 3 守护未就绪（已取消） |
| `spawn-detached.sh` | **跨代存活**启动器（`setsid`/`start_new_session`）——`nohup &` 会与旧 dsh 同进程组被连坐杀（G36 双边实证） | `spawn-detached.sh <script> [args]`；`SPAWN_VERIFY=3` 存活回读 | 0 ok / 2 用法 / 3 spawn 失败 |
| `verify-post-reload.sh` | 热重载后 8 项验收（P1 壳未退出 / P2 dsh 换代 / P3 生命周期 / P4 无循环 / P5 端口换代 / P6 投递 delivered / P7 装载时序 / P8 新插件装载无错） | `verify-post-reload.sh [delay=45] [expectVersion]` | 0 全过 / 1 有失败 |
| `test-hot-reload.sh` | 早期版热重载验收（5 项；已被 `verify-post-reload.sh` 取代，保留供对照） | `test-hot-reload.sh [delay]` | 0/1 |
| `quick-restart-delayed.sh` | 延迟触发 quick-restart（先说完再重启） | `quick-restart-delayed.sh [delay=20] [countdown=15]` | - |

## 二、门禁 / 沙箱 / 自检

| 工具 | 用途 | 用法 |
|---|---|---|
| `restart-audit.py` | 重启前 11 项审查：①语法 ②依赖可达 ③静态裸符号 ③b 再导出当本地用 ④真 apply 冒烟 ④b 自指环 ④d patch 在位 ⑤包内 .bak ⑤b 幽灵副本 ⑥版本 ⑧bundles↔deps ⑨/⑨b reply-hint ⑩档案自洽 ⑪seen 后置 + boot 沙箱 | `restart-audit.py [--json] [--selftest]`；exit 0=可重启 |
| `sandbox-agent-way.mjs` | **真 apply → 真 `agentBus.send` → 断言 `delivered`**（含阴性对照） | `node sandbox-agent-way.mjs` |
| `sandbox-central-inbox.mjs` | 9 项（含 106 条真实风暴卡 ≥95% 拦截、G30 boot 窗口） | `node sandbox-central-inbox.mjs` |
| `check-hazards-consistency.py` | 归因库自洽门（类别/G 码/规则/事故 双向一致） | `python3 check-hazards-consistency.py` |
| `plugin-boot-sandbox.mjs` | 真顺序 + 真 config 隔离 HOME 的 boot 沉降 | `node plugin-boot-sandbox.mjs --dir <profile>` |

## 三、投递 / 核证 / 重投（对应 R042）

| 工具 | 用途 | 用法 |
|---|---|---|
| `verify-delivery.py` | 读**对端日志结局行**核证送达（delivered/pending/unroutable/unconfirmed） | `verify-delivery.py --key <board key>` |
| `redeliver-card.py` | 从板读回原卡 → **改内容** → 换新键重投（同内容会被判 dup） | `redeliver-card.py <key>` |
| `publish-and-point.py` | 写卡（双板 + 逐板回读断言）+ 发指向**实际 key** 的短提示；内建 R039 发前门 | `from publish_and_point import publish_and_point` |
| `cardfmt.py` | 卡正文占位符填充（**禁用 `%` 格式化**：正文常含 `%`，已两次踩坑） | `cardfmt.fill(tpl, **kw)` |
| `comm-preflight.py` | 发卡前门（字段契约/球权/前缀/唤醒），fail-closed | 由 `publish-and-point` 调用 |

## 四、采纳 / 取包

| 工具 | 用途 | 用法 |
|---|---|---|
| `adopt-agentway.py` | 板取包 → sha256 → 包内/装后 patch 断言 → 备份 → 逐文件读回断言（**双头取包**：漏 `X-Webhook-Token` 会被板端当空前缀列表 ⇒ 误判"键不存在"） | `--version 1.5.20 --key data/packages/... --size N --sha-prefix abc12345` |
| `fetch-plugin-from-mac.py` | 从对端取**插件源码目录**并 `link:` 接入（排除 `.bak/.git`；★ 别排 `node_modules/`——对端可能把 `@deepseek-ai/*` 备在里面） | `--name dsh-plugin-x --dep link:/Users/<user>/dsh-plugin-x [--no-link --no-dep]` |
| `install-from-board.py` | 从板取包并按文件落地（早期工具） | `install-from-board.py <key> <target>` |

## 五、本地约定

- 日志目录：`~/dsh-collab/data/ops/`（`relaunch-cld.log`、`quick-restart-trigger.log`、`post-reload-verify.log`、`hot-reload-test.log`）。
- 退出码语义统一：**0=达成 / 1=判据失败 / 2=用法错 / 3=前置不可用**（禁止"没跑到"被读成"通过"）。
- 所有判据遵守：**期望值先行 → 负控必跑 → 与故障同层 → 读回验证**（章程 §5）。
