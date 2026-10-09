# CHANGELOG · dsh-plugin-self-report-gate

## Unreleased · S3 内核接入（包尚未挂载进任何 profile ⇒ 未发布，故不占版本号）

- **内核接入（单来源设计）**：`lib/core.js` 实现 `probe / runStatus / gateVersion / gateSelftest / gateCheck`。
  ★ 刻意**不在 JS 侧重实现任何 SRx 判据** —— SR1–SR6 的唯一实现在
  `~/dsh-collab/scripts/self-report-gate.py`；JS 侧只做 ① 定位 ② 校验 ③ 转调 ④ 原样回报。
  理由：重实现会制造两套逻辑各自漂移，而这正是本门要检出的缺陷形状。
- **⑦ 统一日志接入**：`lib/core.js` 的 `logLine()` 追加到
  `~/dsh-collab/logs/dsh-plugin-self-report-gate.log`（路径与 `package.json` 的 `r006.unified_log` 一致）。
  **成功与失败分支都写**（`gate-run` / `check-denied` / `unavailable`）；写失败返回 `logOk:false`，不抛、不静默。
  实测：清基线 0 行 → 触发 3 次 → 3 行，`kind` 分布 `{gate-run:2, check-denied:1}`。
- **工具真实化**：`lib/index.js` 的 `self_report_check` 由骨架占位改为分派
  `status` / `version` / `selftest` / `check`；新增可选参数 `claim_path`。
  action 冻结枚举由 `["status"]` 扩为四值，默认分支为结构上不可达的 `UNREACHABLE_ACTION`。
- **约束门加固**：`lib/gate.js` 由「命令白名单只比首个 token」改为 **basename + 目录双重白名单**
  （修一处真实缺陷：绝对路径 `/usr/bin/python3` 在原实现下会被假拒；同时防「basename 叫 python3 却在任意目录」的绕过）；
  新增 `ALLOWED_PATH_ROOTS` 与 `assertPathAllowed`；负例 4→7 条，正例 2→4 条；禁用原语补 `exec(` / `execSync(` / `shell:true`。
- **③ CLD 自适应**：实测本机 shell 的 `PATH` 只有 `/usr/bin:/bin:/usr/sbin:/sbin`，`node` 不在其中
  （只有 `/opt/homebrew/bin/node`），peer 只在 CLD runtime ⇒ `lib/core.js` 按候选列表探测绝对路径，
  找不到即如实回报 `unavailable`，绝不静默降级。
- **② TCC 三段填实**：`CAPABILITIES` 5 条、`FORBIDDEN_PATHS` 5 条由占位改为真实内容。

### ★ 本轮实测通过（改后 · 逐条可复跑）

| # | 命令 / 触发 | 结果 |
|---|---|---|
| 1 | `cli.js --tool-version` | rc=0 → `1.0.0`（单一来源 package.json） |
| 2 | `cli.js --lean4-check` | rc=0，六项 A–F 全 ok；负例 **7/7 被拒**、正例 **4/4 可用** |
| 3 | `cli.js --selfcheck` | rc=0；capabilities 5 / forbidden 5 填实；peer 2/2 `where:"cld-runtime"` |
| 4 | `cli.js --dry-run` | rc=0；探针工作 `available:true` · python `/usr/bin/python3` · script 在位 |
| 5 | `cli.js --bogus` | **rc=2**「未知旗标」（⑨ CLI 治理） |
| 6 | `gateVersion()` | 现场读到门版本 **`1.1.4`** · assertions `SR1–SR5`（未硬编码） |
| 7 | `gateCheck('../../etc/passwd')` | 本地即拒 `GATE_PATH_DENIED`（含 `..`），**未派生子进程** |
| 8 | `gateCheck(<受控根内>)` | 转调链路通，门被真实调起并返回其判定头 |
| 9 | **⑦ 日志** | `logs/dsh-plugin-self-report-gate.log` 0 → **3 行**，含失败分支 |
| 10 | **⑧ 登记卡** | 双板回读 **HTTP 200 / 200**，value 与写入语义相等（`boardsMatch:true`） |

### ★ 本轮**未达成 / 未修**（如实登记，不粉饰）

1. **真挂载冒烟仍为 `skipped`** —— `import "@deepseek-ai/dsh-tools"` 在本插件目录下**依然解析不到**，
   尽管 peer 已能被**看见**（`dependencyReport` 三级解析）。⇒ **报告层 ≠ 解析层**：
   前者只改自检**输出**，不改变 Node 的模块解析。真修需：插件目录建 `node_modules/@deepseek-ai/*` 链接、
   或设 `NODE_PATH`、或走正式安装流程。**S5 待办。**
2. **⑧ 自动落链只完成三子项中的一项**：登记卡已可回读（②✓），但
   **① `RULES.md` 规则号未挂**、**③ 长文档未入知识库** ⇒ R8 仍为 partial。
3. **`gateCheck` 只证明「转调链路通」，不证明「门的判定正确」** ——
   本次传入的是 R046 声明体（非本门声明格式），门如实回报「合计 0 条」。⇒ 不得读作「检查通过」。

### 第三方工具复核（`plugin_review(deep=true)` · PSTD/1.0.4）

**score 7/10 ·「接近达标（有待证项）」** —— R2/R3/R4/R5/R6/R9/R10 **pass**；
R1 partial（冒烟 skipped）· R7 partial（当时未接日志 → 本版已接，待复跑）· R8 partial（同上）。

★ 该报告自带一条**版本偏差警告**（`judge_version 1.0.4` vs `audited_onDisk 1.0.0`），
**我方判定为误报**：前者是 PSTD **标准**版本，后者是被审**包**版本，属两个不同对象同名并列——
与本门要检出的「同一事实两个来源」同形。已留档，待回执给工具属主。

## 1.0.0

- 由 PSTD PSTD/1.0.4 模式 `P2_bundled_plugin` 生成初始骨架：自述可证性门（R-SR）：SR1 现场重测 / SR2 阳性对照 / SR3 撤回传播 / SR4 写盘自证 / SR5 环境指纹 / SR6 修复路径覆盖
- 含 R006 ①（形态 + 真挂载冒烟）、②（三段自检）、⑨（CLI 治理）、⑩（冻结枚举 + 负例矩阵 + 六项自证）
- ⑦ 统一日志与 ⑧ 落链**刻意留空**：这两项需要真实业务路径与登记动作，骨架不代填

## 纠错复盘（有错就写这里，别改历史）

- **骨架遗留缺陷 1（本轮只修一半 · 报告层已修 / 解析层未修）**：`dependencyReport` 只试包内与 profile 两级 ⇒
  本机两级都没有 `@deepseek-ai/*` ⇒ 冒烟恒 `skipped`。**症状伪装成「peer 未安装」，实为解析路径不全。**
  ★ 加了第三级之后报告变成 `resolved:true`，**看起来像修好了，实际冒烟仍是 `skipped`** ⇒
  **「输出对了」不等于「行为对了」**。
- **骨架遗留缺陷 2（已修）**：`assertCommandAllowed` 用首个 token 直接比白名单 ⇒ 绝对路径调用必被假拒。
  修的时候必须同时收紧（加目录白名单），否则「放宽成 basename 比较」会开一个新旁路。
- ★ **本轮我自己的错误（记录在案）**：初版 CHANGELOG 写了「骨架原两级解析……导致真挂载冒烟恒为 `skipped`」，
  读起来像「已修好」。**实测冒烟仍 skipped** ⇒ 措辞过度声称，已按实测改写。
  **审查工具的作者自己犯「声称已修而实际未修」，这条必须留档。**
- ★ **通讯规范门逐次报错（我未先查 portal）**：发登记卡时被 `comm-standard-v1 §3` 连续拒两次
  （先缺语义声明，补 `notify_only:true` 后再缺 `subject`）。正确做法是**先读
  `docs/agent-comm-portal-20261002.md` 的「门拒绝→正确姿势对照表」再发**，而不是靠报错迭代。
