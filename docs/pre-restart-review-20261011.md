# 重启前审查 · M4/W7 批次属主件改动

> **出件**：2026-10-11 · 星桥第二任 `session-e317d6ab`（mac-mini）
> **审查对象**：本次将随 CLD 重启生效的**全部属主件改动**（4 插件 / 11 文件）
> **触发**：用户指示「做一次重启前审查」
> ★ 本件是**审查件**，不是结项声明；★ **不主张任何事项已闭合**（S3）；效力档位 **L1**

---

## 〇、一句话结论

**可以重启。** ★ 前提是**本审查过程中抓到并已修掉的一处回归**（见 §四）已在盘上 —— 它已修。
★ 另有 **1 项「非本线引入」的既有缺陷**（`bus-queue-triage` 内嵌身份表陈旧，见 §九）**不阻塞重启**，但会影响**周度 bus 分诊的正确性**。

---

## 一、★ 最关键的审查项：**我改的那份，到底会不会被加载？**

★ 这是本次审查**优先级最高**的一问 —— 若加载的是别处的副本，则**全部修复重启后不生效**。

实测（逐条）：

    $ ls -la ~/.dsh/profiles/web/node_modules/ | grep -i 'agent-way\|launchd-scan\|guard'
      dsh-plugin-agent-way        -> ../../../../dsh-plugin-agent-bus
      dsh-plugin-launchd-scan     -> ../../../../dsh-plugin-launchd-scan
      dsh-plugin-guard            -> ../../../../dsh-plugin-guard
    $ profile package.json 的 dependencies
      "dsh-plugin-agent-way":  "link:/Users/coreyleung/dsh-plugin-agent-bus"
      "dsh-plugin-launchd-scan": "link:../../../dsh-plugin-launchd-scan"
      "dsh-plugin-guard":      "link:/Users/coreyleung/dsh-plugin-guard"

| 插件 | profile 中的名 | 指向 | 我改的会被加载？ |
|---|---|---|---|
| `agent-bus` | ★ **`dsh-plugin-agent-way`**（**目录名 ≠ 包名**） | 软链 → `~/dsh-plugin-agent-bus` | ✅ **是** |
| `guard` | `dsh-plugin-guard` | 软链 → `~/dsh-plugin-guard` | ✅ **是** |
| `launchd-scan` | `dsh-plugin-launchd-scan` | 软链 → `~/dsh-plugin-launchd-scan` | ✅ **是** |
| `bus-queue-triage` | 不在 profile | ★ **launchd 直调 CLI**（`node ~/dsh-plugin-bus-queue-triage/cli.js`） | ✅ **是**（且已实测生效） |

★★ **本项若不做，有一个真实且严重的误判风险**：`~/.dsh/profiles/web/node_modules` 里**没有** `dsh-plugin-agent-bus` 这个名
（我最初就是这样查的，结论一度是「不在 profile」）—— 因为 profile 用的是**包名 `-way`**、目录是 `-bus`。
★ **必须按 `link:` 目标比对，不能按目录名查。**

---

## 二、变更面（11 文件 · 逐件）

| # | 文件 | 版本 | 改了什么 |
|---|---|---|---|
| 1 | `dsh-plugin-agent-bus/lib/index.js` | 1.5.20→**1.5.25** | B1（expired 不再丢弃 · `boarded-pending` 不被覆盖×2 · HTTP spread）· 审批全广播移除 · 审批自回声守卫 · 唤醒批次排除自己 |
| 2 | `dsh-plugin-agent-bus/lib/selfcheck.js` | — | ★ **审查中修的回归**（见 §四）：`flushExposed` 判据由「钉字面」改「钉契约」 |
| 3 | `dsh-plugin-agent-bus/package.json` | 同上 | 版本 |
| 4 | `dsh-plugin-launchd-scan/lib/core.js` | 1.0.0→**1.0.1** | B4：calendar 兼容 dict + 保留 `Weekday`/`Day` |
| 5 | `dsh-plugin-launchd-scan/package.json` | 同上 | 版本 |
| 6 | `dsh-plugin-guard/lib/index.js` | 0.1.1→**0.1.2** | B3：`total===0 ⇒ ok=null` + `all_ok` 显式 + `unverified` |
| 7 | `dsh-plugin-guard/package.json` | 同上 | 版本 |
| 8 | `dsh-plugin-bus-queue-triage/lib/core.js` | 1.0.0→**1.0.1** | `VERSION` 与 package.json 对齐（治本线当晚实捕的版本不一致） |
| 9 | `dsh-plugin-bus-queue-triage/cli.js` | 同上 | B2：`logLine('finish')` 补 `total`（含 `expired`） |
| 10 | `dsh-plugin-bus-queue-triage/package.json` | 同上 | 版本 |
| 11 | ★ `~/dsh-collab/guard/rollback-m4w7-batch.sh` | 新增 | 一键回滚（§五） |

★ **未改动**：`~/.dsh/profiles/web/cordis.patch.yml`（mtime 仍 **2026-10-08**，`grep webserver` **0 命中** ⇒ A2 **未应用**）·
`~/Library/LaunchAgents/com.dsh.*.plist`（**近 24h 无改动**）· 锚点文件（sha 未变）。

---

## 三、静态与加载面检查

| 检查 | 结果 |
|---|---|
| `node --check`（5 个被改 JS） | ✅ **全部 OK** |
| **import 解析**（重启最可能的崩因） | ✅ agent-bus 12/12 · guard 7/7 · launchd-scan 5/5 · bt 5+6/11 —— ★ **异常 0** |
| `agent-bus --selfcheck` | ✅ **exit 0**（自查 6 项全 PASS） |
| `guard --selfcheck` | ✅ PASS |
| `bus-queue-triage --selfcheck` | ❌ **exit 1**（1 项 FAIL —— ★ **非本线引入**，见 §九） |
| `launchd-scan --json` | ✅ 正常出报告（B4 已实测生效） |
| 四件结构断言 + 负控 | ✅ **`fails=0`**（正控全过 + 拿改前备份当负例**全红**） |

---

## 四、★★ 审查**抓到并已修掉**的一处回归（本线引入）

**现象**：`agent-bus --selfcheck` ⇒ `delivery-guard: FAIL · flushExposed=false`

**根因**（`lib/selfcheck.js:243` 原行）：

    const flushExposed = /flush\s*\(\)\s*\{\s*return\s*flushQueue\(\s*\);\s*\}/.test(src);

★ 该判据**钉的是一行源码的字面写法**，不是**契约** ⇒ 我在 1.5.21 为**保留 `flush()` 的数字契约**
改成 `flushQueue().delivered` 后，正则不再匹配 ⇒ **假红**（契约其实没变）。

**修法**（1.5.25）：改为**契约判据** —— ① `flush()` 体内**确实调用** `flushQueue()`；
② 其返回值是**数字**（`…delivered`）。

**★ 该修复的负控（证明新判据有鉴别力，非「调参让它过」）**：

    用例                                 结果
    正确：调用 flushQueue 且返回数字      PASS
    正确变体：先取变量再返回数字          PASS   ← ★ 原判据会把它判错，新判据接受
    错：不调用 flushQueue                 FAIL ✓
    错：调用但不返回数字                  FAIL ✓
    错：空体                              FAIL ✓

⇒ ★ 新判据**比原判据更贴契约**：接受一个**合法的写法变体**，同时拒绝**真正坏掉的形态**。

---

## 五、★ 回滚完备性（一键脚本，已 dry-run 验证）

**发现**：11 个被改文件里，**3 个原本没有回滚点**（那 3 个插件**不是 git 仓库**）：
`launchd-scan/package.json` · `bus-queue-triage/lib/core.js` · `bus-queue-triage/package.json`
（★ 且 `guard/package.json` 的旧备份是 **10-08** 的，用它会把 3 天内其它字段一并回退 ⇒ 不用它。）
★ 另：`agent-bus` 的 `lib/selfcheck.js` 与 `package.json` 是**本线审查中才发现漏了 `guard_backup`** 的，
已用 `git show HEAD:` 补出改前态。

**已交付**：`guard/rollback-m4w7-batch.sh`

    $ bash guard/rollback-m4w7-batch.sh --dry-run
      ⇒ ★ 缺备份数 = 0
    ★ dry-run 已实测不改任何文件（mtime 未变）。
    ★ 加 --apply 才执行。

★★ **诚实声明**：§A 的 7 个走 `cp <备份>`（**逐字节还原**）；§B 的 4 个走**反向编辑**（**等价还原，非字节还原** ——
本线改动的注释块不会被还原）。★ **不得把 §B 读作字节一致。**

---

## 六、四件套 / beacon（重启前必须自洽）

    锚点 sha 一致: True | 索引 canonical 本地==板: True | state_version: 6 | 指针: 6
    beacon-check --net ⇒ 无 FAIL · 0 WARN · 0 SKIP · 1 项待复核（既有 PEND，非本轮引入）

---

## 七、★ 重启后核验清单（按顺序，五条）

    # ① CLD 起来了吗（若起不来，先跑 §五 的回滚）
    ps -p $(pgrep -f 'MacOS/CLD' | head -1) >/dev/null && echo UP || echo ★DOWN
    # ② B3 是否生效（★ 这是最直观的一条）：C7 应从 {ok:true} 变为 {ok:null, degenerate:true}，all_ok 应变 false
    cld_health_check        # 看 C7_version 有无 degenerate 键、all_ok 值
    # ③ B1 是否生效：expired 应被暴露
    curl -s -X POST http://127.0.0.1:8791/agent-bus/api/flush | head -c 200   # 期望含 expired 键
    # ④ 审批广播是否已停（★ 这条要**发一张真审批单**才能验，可留到最后）
    #    验后注意：本次修复后**不再全广播**；若仍收到全网广播 ⇒ 说明旧代码仍在跑
    # ⑤ 四件套与工具回归
    python3 ~/dsh-collab/tools/beacon-check.py --net          # 期望 exit 0 · FAIL 0 · SKIP 0
    python3 ~/dsh-collab/scripts/verify-m4w7-batch-fixes.py --status   # 期望四件全 PASS
    node ~/dsh-plugin-agent-bus/cli.js --selfcheck            # 期望 exit 0

★ **若 ② 显示 `ok:true` 且无 `degenerate` 键** ⇒ ★ **B3 未生效**（旧代码仍在跑）⇒ 回查 §一 的加载路径。

---

## 八、★ 未测项与风险（**别当已验证**）

| # | 项 | 状态 |
|---|---|---|
| 1 | ★ **B1 / B3 的行为** | **未做行为测试** —— 二者是进程内插件，行为测试须重启；★ 本线**只主张源码结构成立**（有断言脚本） |
| 2 | ★ **`agent-bus` 五处改动的运行时行为** | 同上，**未测**。★ 尤其 `wakeBatch` 的 `selfId` 过滤**从未在运行时跑过** |
| 3 | ★ **`bt` 的 selfcheck 仍 FAIL** | ★ **非本线引入**（§九），**未修** ⇒ 重启后它**仍会红**。★ 不要把它误读成本轮回归 |
| 4 | ★ **重启本身** | ★ **不可逆动作**，按规约**由用户执行**；本线**不触发**任何重载端点（★ portal 附录 B：`:31888/reload` 会触发壳崩溃） |
| 5 | **P26 类风险** | ★ 重启不影响 P26 根因（会话上下文膨胀），那是**另一条线** |
| 6 | ★ **本件全部结论** | **本线自测，无独立 verifier** ⇒ 按 S3 不得记 `closed`。★ 已并入给 Claude 的第三方委托件 |

---

## 九、★ 审查发现但**非本线引入**的既有缺陷（不阻塞重启）

**`bus-queue-triage` 的 `等价断言` FAIL**（`exit 1`）：

    "星桥": 内嵌 {"id":"session-fa1f9150-c949-401f-ba8c-d265f6221676"} 
       vs 规范 {"id":"session-e317d6ab-5302-4b33-b095-947983ba16f4"}

★ **内嵌（vendored）身份表仍把「星桥 / coordinator / star-bridge」映射到 `session-fa1f9150`** ——
★ 那是**首任星桥，已于 2026-10-09 因 P26 bricked**；而**规范模块 `~/dsh-comm-shared/identity.js` 已指向现任（本线）**。

★ **这正是锚点 §18 已登记的「双义星桥」冲突**，且**本工具的自我检查已经把它抓出来了**（`等价断言` 就是为这类漂移设的）。

★ **一处新事实**：`lib/core.js:57` 声明该表 `vendored from dsh-comm-shared/identity-variants.json（20 身份/37 变体，逐字）`，
而该源文件**现在只有 3 条** ⇒ ★ **上游源已换结构/缩小，vendored 副本停在旧版**。

| 项 | 判定 |
|---|---|
| 会不会影响**重启** | ★ **不会** —— `bt` 是 **CLI**（launchd 周跑），**不进 CLD 进程** |
| 会不会影响**功能** | ★ **会** —— 用陈旧表做 `--apply` 时，「星桥」可能被解析到**已死会话** ⇒ 相关消息**永远投不出去** |
| 本线处置 | ★ **不代改**（身份语义属治理层，且**规范模块的属主不是本线**）⇒ **登记并上报** |

---

## 十、复跑块

    # [1] 加载路径（★ 最关键，必须按 link: 目标比对，不能按目录名查）
    ls -la ~/.dsh/profiles/web/node_modules/ | grep -E 'agent-way|launchd-scan|guard'
    /usr/bin/python3 -c "import json;d=json.load(open('/Users/coreyleung/.dsh/profiles/web/package.json'));print({k:v for k,v in (d.get('dependencies') or {}).items() if 'agent-way' in k or 'launchd-scan' in k or 'guard' in k})"
    # [2] 静态面
    for f in ~/dsh-plugin-agent-bus/lib/index.js ~/dsh-plugin-launchd-scan/lib/core.js ~/dsh-plugin-guard/lib/index.js ~/dsh-plugin-bus-queue-triage/cli.js; do node --check "$f" && echo "OK $f"; done
    node ~/dsh-plugin-agent-bus/cli.js --selfcheck > /dev/null; echo "agent-bus selfcheck exit=$?"
    # [3] 不该变的
    grep -c webserver ~/.dsh/profiles/web/cordis.patch.yml          # 期望 0（A2 未应用）
    find ~/Library/LaunchAgents -name 'com.dsh.*.plist' -newermt '2026-10-10 20:00'   # 期望空
    shasum -a 256 ~/dsh-collab/docs/distributed-agent-network-governance-plan-v6.1-20261011.md | cut -c1-24
    # [4] 回滚完备性
    # ★ 修（2026-10-11 复跑入口普查）：原写成 `... | grep -c '★ 缺备份'   # 期望 0` ——
    #   那是【空转绿】：脚本崩了 grep -c 也打印 0 ⇒ 恰好被读成「期望 0 = 通过」。
    #   ★ 同型缺陷已由第三方复核在同批另一处抓出（见 D-042 ③）；本次普查在本文档里又找到一处。
    o=$(bash ~/dsh-collab/guard/rollback-m4w7-batch.sh --dry-run 2>&1); rc=$?
    printf '%s\n' "$o" | grep -c '★ 缺备份'; echo "↑ 缺备份数（期望 0）；★ rc=$rc 非 0 则本行无意义"
    # [5] 断言与四件套
    python3 ~/dsh-collab/scripts/verify-m4w7-batch-fixes.py --selftest | tail -2
    python3 ~/dsh-collab/tools/beacon-check.py --net | tail -1

---

*本件只增不改；更正以新件追加。★ **任何 `closed` 状态必须附独立 verifier**（S3 不可自审）。*
