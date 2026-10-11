#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""incident-regression.py — **已知事故回归语料**：跑一遍「每一起已知事故，现在还会不会红」。

★ 立据（星桥 2026-10-10 裁决卡里新增的检查项，逐字）：
  「凡**放宽 / 豁免 / 兜底**类修改，先问：**会不会让已知事故从红变绿**？」
★ 为什么需要它（而不是靠人记得问）：这一问的答案**随代码演进变化**，
  而"放宽"在当下看起来永远像是"修 bug"（把一条闹心的红变绿）。
  ⇒ 把「已知事故」固化成可复跑的语料：**改判据前后各跑一次**，谁把事故放绿了，当场现形。

★ 语料形态：每起事故配一个**自断言 harness**（harness 内部自带"该红的红、该绿的绿"成对判据），
  本件只负责**统一编排 + 汇总矩阵 + 给一个全局退出码**（不重复实现判据 —— 复用既有 harness）。

★ 本件的限度（主动声明不覆盖面，免得被读多）：
  · 它只覆盖**已经写成 harness 的那些事故**；没写进来的事故（例如尚未复现的新形态）**不在覆盖内**。
  · 它**不核**判据本身的正确性，只核"这些已知输入今天仍得到预期判决"。
  · 编排层若超时/环境缺失，**如实报 skipped**，不计入通过（skip ≠ pass）。

退出码：0 = 全部 case 通过 · 1 = 有 case 失败（事故被放绿或 harness 自身异常） · 2 = 编排层错误
"""
import json
import re
import os
import subprocess
import sys
import time

PEAK_LIMIT = 3
HERE = os.path.expanduser("~/dsh-collab")
PY = sys.executable or "python3"

# id · 事故一句话 · 命令 · 期望（harness 自带红/绿成对断言 ⇒ 期望均为 exit 0）
CASES = [
    {
        "id": "INC-01",
        "incident": "continuity-index 被本地旧副本整体覆盖（41,328 → 20,796 字符；Q-K 丢 k3/k4/k5 与 5 个 ★ 块）",
        "cmd": [PY, "tools/qk-structure-mutation.py"],
        "covers": "结构不变量门 + M1–M4 红 / M5·M7 绿",
    },
    {
        "id": "INC-02",
        "incident": "冒烟记录冒充在役记录（日志混 pid 且无区分字段 ⇒ 假绿）",
        "cmd": [PY, "tools/csx-mount-record-mutation.py"],
        "covers": "挂载留痕门 + M1–M8 红（含 M6 删 mode / M8 只有 smoke 却对盘面）",
    },
    {
        "id": "INC-03",
        "incident": "T1 前的文案自相矛盾（同一文件内 csx_status 报 wired、csx_checkpoint 报未接线）",
        "cmd": [PY, "tools/csx-t1-wiring-mutation.py"],
        "covers": "contract-check ④（阶段串 + 接线状态）+ M1/M2 双变异红、原件零接触",
    },
    {
        "id": "INC-04",
        "incident": "退出码经管道被静默替换（`| tail` 取 $? ⇒ 红显示成绿）",
        "cmd": [PY, "tools/evidence-channel-guard.py", "--selftest"],
        "covers": "正控1/正控2 红 + 反控1/反控2 绿",
    },
    {
        "id": "INC-05",
        "incident": "负控 3 投递半被静默升格成「通过」（partial 的原文与原因蒸发）",
        "cmd": [PY, "tools/k6-partial-guard.py"],
        "covers": "状态格必须含 partial + 原因（反控见该门文档内的沙箱用例）",
    },
    {
        "id": "INC-14",
        "incident": "版本判据**钉点值**（必须返回 version 0.12.0）而盘面已推进 ⇒ 字面执行把「已正确换版」判成不通过 ⇒ **误回滚**",
        "cmd": [PY, "tools/version-pin-lint.py", "--selftest"],
        "covers": "判据钉下限不钉点值，**且下限不得单独成立**（须伴同源条款）：正控 3（行内点值 · 表格点值 · **只钉下限 ⇒ 半边判据**）+ 反控 3（下限 · 历史/读数 · 下限+同源）；零命中也打印扫描面",
    },
    {
        "id": "INC-13",
        "incident": "报告声明不可核（「我说我写了」≠「写在了那里」；台账指向不存在的落盘物那一族）",
        "cmd": [PY, "tools/report-claim-check.py", "--selftest"],
        "covers": "一正控（文件不存在 ⇒ 红）+ 一正控（**行号越界** ⇒ 红）+ 一正控（**零引用 ⇒ 红**：叙述不是报告）+ 一反控（真实 `文件:行号` ⇒ 绿）；"
                  "并去重（同路径不得被两类正则各报一次）",
    },
    {
        "id": "INC-12",
        "incident": "「纪律→仪器」映射表只写在文档里、**不可核**（原则靠记性 ⇒ 判决位数到第七次同形的结构性根因）",
        "cmd": [PY, "tools/maxim-map-check.py", "--selftest"],
        "covers": "四条对照：正控（悬空工具 ⇒ 红 · 纪律无引用 ⇒ 红）+ 反控（真工具真卡 ⇒ 绿 · 悬空卡 ⇒ 红或不可判）；"
                  "并对**覆盖率**对账（实测：只覆盖 6/10 却报全绿 ⇒ 部分覆盖不得读成全部）· 空集 ⇒ 红 · "
                  "**索引仪器必须通过自己的 `--selftest`**（坏件不得冒充仪器）；"
                  "★ 如实声明**映射正确性在面外**（实测：换成真实但不相干的件，本件不报 ⇒ 由声明层复审与人工裁决负责）",
    },
    {
        "id": "INC-11",
        "incident": "自证里用**源码文本**当证据（「查字符串」族，第三次复发：is_gate 字面串 / absolute-claim-lint 早期文本级 / RUN_STAMP 断言第一版）"
                    " ⇒ 「源码里有这句话」≠「这段代码真能跑」，且这种判据**永远能绿**",
        "cmd": [PY, "tools/text-assertion-lint.py", "--selftest"],
        "covers": "一正控（自证里查源码、无理由 ⇒ **必红**）+ 三反控（写明豁免理由 ⇒ 绿 · 真跑 ⇒ 绿 · 非自证位置的文本匹配 ⇒ 绿）；"
                  "判据用 **AST 结构**（测试函数内 Compare/In 且证据来自 `.read()` 派生名），**不用行文本**（第一版按行文本 ⇒ 夹具字符串假阳；第二版过宽 ⇒ 把函数返回值也报）",
    },
    {
        "id": "INC-10",
        "incident": "新件不继承已立纪律（观测面五要素 / 双向自证 / 退出码契约 / 入册片段）—— 判决命名的「每个新件只学会了那一次」",
        "cmd": [PY, "tools/gate-scaffold.py", "--selftest"],
        "covers": "四向对照：骨架自身硬项全过 · 缺项件硬项**变红** · new **拒覆盖** · 生成的骨架**可运行且如实报未实现**（exit 3，不是绿）",
    },
    {
        "id": "INC-09",
        "incident": "绝对断言（不可能/一定/全部）同句不给观测面 —— 判决命名的「加限定但不降断言」模式（两轮两现）",
        "cmd": [PY, "tools/absolute-claim-lint.py", "--selftest"],
        "covers": "四条对照：两条正控（含绝对断言且无观测面 ⇒ **必红**）+ 两条反控（降到「未发现」并给观测面 ⇒ 绿；fence 内设计承诺 ⇒ 绿；显式豁免声明 ⇒ 绿）",
    },
    {
        "id": "INC-08",
        "incident": "「当值角色是谁」解析错表：agent_profiles 81 条 vs 活体 5 个 ⇒ 94% 幽灵；两表各半真相且当时无工具交叉",
        "cmd": [PY, "tools/live-role-resolve-harness.py"],
        "user_command": ["tools/live-role-resolve.py", "--role", "裁判"],
        "covers": "★ **现场 harness**（不再用 `--selftest`）：S1 默认路径（不带 `--peers`）⇒ 必须**干净失败**"
                  "（非 0 · 无栈 · 有用法提示）；S2 真实用法（带快照）⇒ 必须**真解析出** unique_live_candidate。"
                  "★ 另保留 `--selftest`（四态夹具）作为**补充**（由 principle-landing-check 执行），"
                  "但**自证夹具不替代现场**（判决 B 的教训）",
    },
    {
        "id": "INC-07",
        "incident": "表面序 ≠ seq 序（任何表面替换之后）⇒ csx_checkpoint 在役 3/3 报同一错（星桥实测）",
        "cmd": ["/opt/homebrew/bin/node", "cli.js", "--checkpoint-check"],
        "cmds": [["/opt/homebrew/bin/node", "cli.js", "--checkpoint-check"],
                 ["/opt/homebrew/bin/node", "cli.js", "--selfcheck", "--allow-apply"]],
        "user_command": ["csx_checkpoint"],
        "cwd": os.path.join(HERE, "devices/dsh-plugin-context-survival"),
        "covers": "① 纯核 W 组（非单调 ⇒ **不抛出** / ok:false / 带位置与两侧 seq / 动作码单列 not_applicable / "
                  "**不产通知** / 单调面负控不被误伤）② ★ **现场**：挂载冒烟里**真调** `csx_checkpoint` 到"
                  "**非单调假会话**上 ⇒ 要求干净降级（action=not_applicable、wrote=false、**不抛栈**）"
                  " —— 补的就是「harness 走的是用户会走的那条命令」。"
                  "★ 本条与 INC-01..06 一样，harness **跑的是盘面**（新进程读盘上代码）——"
                  "而 INC-07 **此刻正在在役发生**（在役 0.12.4 仍报该错，星桥实测第 4 次）。",
    },
    {
        "id": "INC-06",
        "incident": "阶段串被写死在第二处（cli.js 写死 K5 而 lib/index.js 已到 K6，当时无门可发现）",
        "cmd": ["/opt/homebrew/bin/node", "cli.js", "--contract-check"],
        "cwd": os.path.join(HERE, "devices/dsh-plugin-context-survival"),
        "covers": "contract-check ①②③④ 全绿（含 ④ 单一来源）",
    },
]


# ═══ 入册完整性（星桥判决 D：6/6 只管已入册的 6 起 ⇒ 对**未入册**事故结构性无判别力）═══
# ★ 能做的那一半：**「有没有把新门登记进回归网」不该靠记** —— 凡带「退出码契约」的门
#   （docstring 里写了「退出码」且代码里有 sys.exit），必须在 CASES 里，或在 EXEMPT 里
#   **带理由**豁免。⇒ 新门一落地就现形，而不是等下一次事故靠人想起。
# ★ 做不到的那一半（如实写在输出里）：本件**仍不**能对「尚未写成 harness 的新事故」有判别力 ——
#   那要求「事故必须先入册再修」的流程纪律，判据管不了流程。
# ① **间接覆盖**：门被某个已入册的 harness 驱动 ⇒ 算入册，但**必须指名**那个 harness，
#    且该 harness 必须真的在 CASES 里（否则本表本身就是假的 ⇒ 红）。
COVERED_BY = {
    "csx-mount-record-check.py": "csx-mount-record-mutation.py",
    "qk-structure-guard.py": "qk-structure-mutation.py",
    "incident-regression.py": "selftest(__selftest__)",   # 编排器自身：由 --selftest 注入必败 case 对照
}
# ② **真豁免**（带理由，不许空着）
EXEMPT = {
    # ★ 由 EXEMPT_PERMANENT 撤回（其"永久"是我的判断、非第三方可验证 ⇒ 不符合准入判据）
    "principle-landing-check.py": "元判据：核「原则有无落脚件」；其失败面不属事故形态，"
                                  "且答案来自静态标记而非对抗探针 ⇒ 无「该红/该绿」两态可造（**此为一次性豁免，非永久豁免**）",
}
# ③ **DEFERRED（暂时不做）**：决策**未做**，须带**复审日**。
#    ★★ 判据为何要有日期（星桥判决 D 的补充，逐字要点）：
#      「复审日治『陈旧』，治不了『**恒真理由**』——待办项理由全是『他人维护』，
#        而归属不变 ⇒ 该理由**永不失效** ⇒ 与恒真判据同族。」
#    ⇒ 故「暂时不做」**必须带复审日**（到期未决即红），否则它就是一个永不失效的理由。
#    ⚠ 这里刻意**不**用「他人维护」当永久理由：归属不变 ≠ 决定不必做。
DEFERRED = {
    # ★★ 2026-10-10 判决 C/D 重构（逐字要点）：「你命名了『断言强于证据』，却在承认它的同一份输出里又犯一次」
    #   · 原写法 `"他人维护"` = **归属断言**（我其实不知道它属谁）；`"需其维护者决定"` = **第二个断言**（预设了维护者与决策过程）
    #   ⇒ 现只写**事实**：我核了什么、没核什么；归属写「**归属未证**」。
    #   · 原 22 条**同一天**到期 ⇒ 「洪峰 = 无信号」，且复审**没有收件人** ⇒
    #     现每条带 `owner`（未定者写明「待协调者分派」= 可执行的收件人）+ **错开**的复审日。
    #   ★ 错开规则：按**文件名排序**依次 +1 天 —— **不是**按重要性（我无权评重要性）；
    #     本件另有**洪峰检测**：同日 >3 条即红（见 check 里的 PEAK_LIMIT）。
    "acceptance-gate.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-01"},
    "bb-write-verify.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-02"},
    "bb_dualwrite.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-03"},
    "beacon-check.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-04"},
    "build-starbridge-index.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-05"},
    "build-state-registry.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-06"},
    "declaration-validity-scan.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-07"},
    "floodgate.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-08"},
    "freeze-snapshot.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-09"},
    "gcr-gate.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-10"},
    "infopack-check.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-11"},
    "lint-silent-truncation.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-12"},
    "mk-resume-prompt.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-13"},
    "node-claim-gate.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-14"},
    "official-ref-gate.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-15"},
    "qk-prohibition-check.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-16"},
    "qk-tracker-drift-check.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-17"},
    "review-gate.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-18"},
    "sandbox-script.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-19"},
    "self-destruct-gate.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-20"},
    "selftest-starbridge-gates.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-21"},
    "xdom-mail.py": {"owner": "未定（待协调者分派）", "why": "**归属未证** —— 我只核了：文件存在 + 含 `sys.exit(` 代码形状；**未核**归属、未读内容、未问过任何维护者", "recheck_by": "2026-11-22"},
}

# ④ **EXEMPT_PERMANENT（永久豁免）**：**结构性**不适用 —— 理由成立与否**不随归属/时间变化**。
#    ★ 与 DEFERRED 的区别不是"语气"，而是**理由的类型**：这里写的是"结构上不适用于本网"，
#      不是"还没轮到决定"。凡写不出"为何永久"的，一律应归 DEFERRED 并带复审日。
# ★★ 永久豁免的**准入判据**（判决 B 指出「准入判据仍缺位」⇒ 现写成机器可核的两条）：
#   ① `verify`：**第三方可跑的验证**（相对路径 + 必须命中的标记串）——本件每次真跑它；
#      标记消失 ⇒ 豁免**自动失效并变红**（防止"永久"变成"永不复查"）；
#   ② 理由不得是「归属/决策待定」类（那是 DEFERRED），只能是**结构性不适用**。
EXEMPT_PERMANENT = {
    "beacon-cover-check.py": {
        "why": "★ **已废弃件**：其文件头自述 DEPRECATED 并指明判据已归 tools/beacon-check.py 单点持有 ⇒ 结构上无需入网",
        "verify": ("tools/beacon-cover-check.py", "DEPRECATED"),
    },
}
# ⚠ 原先把 principle-landing-check.py 也放进永久豁免 —— **撤回**：
#   它的"永久"是**我的判断**（"元判据无可造红绿两态"），**不是第三方可验证的事实** ⇒ 按准入判据①，
#   它不符合永久豁免，应回到普通 EXEMPT（带理由的一次性豁免），等有可核依据再升级。
EXEMPT_MORE = {
    "csx-canfail-check.py": "插件自身对抗工具（直测七道门能否红）：★ **会在原件树上做临时改写**（备份+还原）"
                            "⇒ 不纳入自动语料，以免中途中断留下脏态；需要时**手动**运行并当场核对还原",
    "csx-constant-mutation.py": "同上（常量变异面，原件树临时改写 + 还原）—— 不入自动语料",
    "csx-mutation-check.py": "同上（纯核变异检验，原件树临时改写 + 还原）—— 不入自动语料；"
                             "★ 若改用**整树副本**（如 tools/csx-t1-wiring-mutation.py 的做法）即可安全入册",
}


# ★★ 声明层复审规矩（星桥判决 D 的通用递归：**以声明代证据的机制，都需「声明表何时复审」的规矩**，
#    否则声明层会变成**新的恒绿层**）。
#    ⇒ 表级复审日期 + 间隔；过期即红（不是提醒，是门 —— 提醒会被忽略，门不会）。
TABLE_REVIEWED_AT = "2026-10-10"     # 本表（EXEMPT / PENDING / COVERED_BY）最近一次人工复审日
REVIEW_INTERVAL_DAYS = 30

CONTRACT_MARK = "退出码"          # 「退出码契约」的**声明串**
CODE_SHAPE = "sys.exit("          # 「是个门」的**代码形状**


def enrollment_gaps():
    """找出「是门、但既未入册、也未间接覆盖、也未带理由豁免」的件。

    ★★ 判据形态（星桥判决 C 指出的缺口：原判据用**两个字面串**同时判"是不是门"，
       于是"用了 sys.exit 但没写『退出码』"的件**隐形** ⇒「0 个无声明」只关于看得见的那批）。
    ⇒ 现改为**两层**：
      · **门的候选面** = 代码形状 `sys.exit(`（**不含**任何文案要求）⇒ 候选面不再依赖作者写了什么字；
      · **契约声明** = docstring 里写「退出码」⇒ 仅用于**分类提示**（缺了 = 如实标注，不算违例，但会被打印）。
    ★ 同时按本项目惯例**把观测面写进输出**（否定性结论必须附观测面：含项 / 排除项 / 工具 / 单位 / 时刻）。
    """
    import glob
    enrolled = set()
    for c in CASES:
        for part in c.get("cmd", []):
            if isinstance(part, str) and part.endswith(".py"):
                enrolled.add(os.path.basename(part))
    gaps, gates, covered_indirectly, no_contract, deferred, permanent = [], 0, [], [], [], []
    for path in sorted(glob.glob(os.path.join(HERE, "tools", "*.py"))):
        name = os.path.basename(path)
        src = open(path, encoding="utf-8", errors="replace").read()
        if CODE_SHAPE not in src:          # ★ 只按**代码形状**判候选面（不再要求文案）
            continue
        gates += 1
        if CONTRACT_MARK not in src:
            no_contract.append(name)       # 用了 sys.exit 却没声明退出码契约 ⇒ 如实列出（提示，不是违例）
        if name in enrolled or ((name in EXEMPT or name in EXEMPT_MORE)
                                and (EXEMPT.get(name, "") + EXEMPT_MORE.get(name, "")).strip()):
            continue
        if name in COVERED_BY:
            harness = COVERED_BY[name]
            if harness == "selftest(__selftest__)" or harness in enrolled:
                continue          # 间接覆盖成立（且被指的 harness 真的入册了）
            gaps.append(f"{name}（声称由 {harness} 覆盖，但那个 harness **不在** CASES 里 ⇒ 声明是假的）")
            continue
        if name in EXEMPT_PERMANENT:
            # ★ 准入判据①：verify 必须能真跑并命中（否则"永久"= 永不复查）
            vrel, mark = EXEMPT_PERMANENT[name].get("verify", (None, None))
            vpath = os.path.join(HERE, vrel) if vrel else None
            if not vpath or not os.path.isfile(vpath):
                gaps.append(f"{name}（EXEMPT_PERMANENT 的 verify 指向不存在的件 {vrel} ⇒ 豁免不成立）")
            elif mark not in open(vpath, encoding="utf-8", errors="replace").read():
                gaps.append(f"{name}（EXEMPT_PERMANENT 的 verify 标记「{mark}」在 {vrel} 里**找不到** ⇒ 豁免自动失效）")
            else:
                permanent.append(name)
            continue
        if name in DEFERRED:
            ent = DEFERRED[name]
            reason, due, owner = ent.get("why", ""), ent.get("recheck_by", ""), ent.get("owner", "")
            if not str(owner).strip():
                gaps.append(f"{name}（DEFERRED **没有收件人** ⇒ 复审无对象：请写 owner，未定者写「待协调者分派」）")
                continue
            if not str(reason).strip():
                gaps.append(f"{name}（DEFERRED 但理由为空 ⇒ 不许空着）")
                continue
            # ★ 复审日：缺失/非法/已过期 ⇒ 红（「暂时不做」不得成为永不失效的理由）
            import datetime as _dt
            try:
                due_d = _dt.date.fromisoformat(due)
                overdue = _dt.date.today() > due_d
            except Exception:
                overdue = True
                due_d = None
            if overdue:
                gaps.append(f"{name}（DEFERRED 复审日 {due} 已到/非法 ⇒ 必须做决定：入册 / 换理由 / 移除）")
                continue
            deferred.append((name, due, owner))
            continue
        gaps.append(name)
    return gates, gaps, covered_indirectly, no_contract, deferred, permanent


def version_gap():
    """盘面版本 vs 在役版本（**算出来的**，不是措辞）。

    ★ 立据（星桥判决 C 逐字要点）：「声明写『在役**可能**是旧版』，实测是『**必然落后且扩大**』
      —— 07:52 差 0，现在差 3」⇒ **「可能」低估事实**；而当天我反复犯的是反方向（断言强于证据）
      ⇒ **同一条纪律两面：措辞须与事实等强**。
    ⇒ 改法：**带两个具体版本号**（且由本函数实时算出 ⇒ 既不会低估，也不会过期）。
      · 盘面版本 ← `devices/dsh-plugin-context-survival/package.json`
      · 在役版本 ← 插件统一日志里**最后一条 `mode=serve` 的 mount 记录**（该版本在服务启动时载入）
      ★ 限度：这是"**上次服务启动时载入的版本**"，不等于"此刻正在跑的代码"（但差距只会随时间扩大）。
    """
    disk, errs = None, []
    pkg = os.path.join(HERE, "devices/dsh-plugin-context-survival/package.json")
    try:
        disk = json.load(open(pkg, encoding="utf-8")).get("version")
    except Exception as e:
        # ★★ 2026-10-10 实测教训：本函数原先 `except: disk=None`，于是"**读不到**"与"**不存在**"
        #    同痕 —— 而实测真正的根因是**本件压根没 import json**（两处读取全被吞成 None，
        #    输出却写成「无 serve 记录」）。⇒ 现把两种成因分开记，并**如实打印**。
        disk = None
        errs.append(f"盘面版本读取失败（{e.__class__.__name__}: {e}）")
    served, ts, pid = None, None, None
    log = os.path.join(HERE, "logs/dsh-plugin-context-survival.log")
    if os.path.isfile(log):
        for ln in open(log, encoding="utf-8", errors="replace"):
            if '"mounted"' not in ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:
                continue
            if r.get("line") == "mounted" and r.get("mode") == "serve":
                served, ts, pid = r.get("version"), r.get("ts"), r.get("pid")
    if served is None and not errs:
        errs.append("日志里没有 `mode=serve` 记录（**不是读不到**，是确实没有）")
    return {"disk": disk, "served": served, "servedAt": ts, "servedPid": pid, "errors": errs}


def _vnum(v):
    try:
        a, b, c = (str(v).split(".") + ["0", "0"])[:3]
        return (int(a) * 10000) + (int(b) * 100) + int(c)
    except Exception:
        return None


def ts():
    """RFC3339 本地时刻（观测面五要素之一）。"""
    import datetime
    x = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    return x[:-2] + ":" + x[-2:]


def table_stale():
    """返回 (是否过期, 已过天数)。表过期 ⇒ 调用方须报红（声明层不得永久免检）。"""
    import datetime
    try:
        d = datetime.date.fromisoformat(TABLE_REVIEWED_AT)
    except Exception:
        return True, -1
    age = (datetime.date.today() - d).days
    return age > REVIEW_INTERVAL_DAYS, age


def run_case(c):
    cwd = c.get("cwd", HERE)
    if not os.path.isdir(cwd):
        return "skipped", f"工作目录不存在：{cwd}"
    t0 = time.time()
    cmds = c.get("cmds") or [c["cmd"]]
    outs = []
    for one in cmds:
        try:
            rr = subprocess.run([str(x) for x in one], cwd=cwd, capture_output=True, text=True, timeout=300)
        except FileNotFoundError as e:
            return "skipped", f"命令不存在（{e}）"
        except subprocess.TimeoutExpired:
            return "timeout", f"超时：{' '.join(str(x) for x in one)}"
        outs.append(rr)
    class _R:
        pass
    r = _R()
    r.returncode = 0 if all(o.returncode == 0 for o in outs) else 1
    joined = "\n".join((o.stdout or "") + (o.stderr or "") for o in outs)
    r.stdout, r.stderr = joined, ""
    if r.returncode != 0:
        for o in outs:
            if o.returncode != 0:
                r.stdout = (o.stdout or "") + (o.stderr or "")
                break
    ms = int((time.time() - t0) * 1000)
    tail = (r.stdout or "").strip().split("\n")
    last = tail[-1] if tail else ""
    return ("pass" if r.returncode == 0 else "fail"), f"exit={r.returncode} · {ms}ms · {last[:110]}"


def selftest():
    """★ 编排层自己的对照：注入一个**必定失败**的假 case，汇总必须报 fail 且总退出码为 1。

    ★ 为什么需要（也正是星桥那条检查项的镜像）：本件是**编排器**，它最可能的失效是
      **把失败 case 吞掉**（汇总恒绿）。harness 各自有红/绿对照，但编排器自己没有 —— 补在此。
    """
    global CASES
    keep = CASES
    CASES = keep + [{"id": "SELFTEST-FAIL", "incident": "注入的假 case（必须是红的）",
                     "cmd": [PY, "-c", "import sys; sys.exit(1)"], "covers": "编排层是否会把失败吞掉"}]
    try:
        code = main(quiet=False)
        if code != 1:
            print(f"  ❌ --selftest 失败：注入必败 case 后总退出码={code}，期望 1 ⇒ 编排层会吞失败")
            return 1
        print("  ✅ --selftest 通过：注入的必败 case 被如实报 fail，总退出码 1")
        return 0
    finally:
        CASES = keep


def main(quiet=False, enrollment=False, strict=False):
    if enrollment:
        gates, gaps, deferred, no_contract, pend, permanent = enrollment_gaps()
        stale, age = table_stale()
        print("incident-regression · --enrollment-check 入册完整性（**不改被核对象**；临时写面 = `guard/mutation-work/`）")
        print(f"  门的候选面（**只按代码形状** `{CODE_SHAPE}`）：{gates} 个 · "
              f"其中已入册/间接覆盖/已豁免：{gates - len(gaps) - len(pend)} 个")
        if no_contract:
            print(f"\n  ⓘ 候选面里**未声明退出码契约**的件（{len(no_contract)} 个，提示性质，不计违例）：")
            for x in no_contract:
                print(f"    {x}")
        print(f"\n  · 声明层复审：TABLE_REVIEWED_AT={TABLE_REVIEWED_AT} · 距今 {age} 天 · "
              f"间隔 {REVIEW_INTERVAL_DAYS} 天 ⇒ {'★ 已过期' if stale else '未过期'}")
        if pend:
            # ★ 洪峰检测（判决 D）：「同一天集体到期 ⇒ 洪峰 = 无信号」
            from collections import Counter
            by_date = Counter(d for _, d, _ in pend)
            peak = [(d, n) for d, n in by_date.items() if n > PEAK_LIMIT]
            print(f"\n⏳ DEFERRED（暂时不做 · **未裁决 · 不等于已覆盖**；共 {len(pend)} 条，各带收件人与复审日）：")
            for x, due, owner in pend:
                print(f"  {x} —— 收件人：{owner} · {DEFERRED[x]['why']}（复审截止 {due}）")
            print(f"  · 到期分布：{len(by_date)} 个不同日期 · 单日最多 {max(by_date.values()) if by_date else 0} 条"
                  f"（洪峰阈值 {PEAK_LIMIT}）⇒ {'★ 有洪峰' if peak else '无洪峰'}")
            if peak:
                gaps.append(f"**洪峰**：{peak} 同日到期 >{PEAK_LIMIT} ⇒ 到期集体变红 = 无信号，请错开复审日")
        if permanent:
            print(f"\n⊘ EXEMPT_PERMANENT（永久豁免 · 理由**结构性**成立，不随归属/时间变化；共 {len(permanent)} 条）：")
            for x in permanent:
                print(f"  {x} —— {EXEMPT_PERMANENT[x]}")
        if stale:
            print(f"\n❌ 声明层已过期（{age} 天 > {REVIEW_INTERVAL_DAYS} 天）⇒ 必须人工复审本表："
                  f"\n   每项要么入册、要么换理由、要么移除；复审后更新 TABLE_REVIEWED_AT。"
                  f"\n   ★ 理由（星桥判决 D）：**以声明代证据的机制若无复审规矩，声明层会变成新的恒绿层**。")
            return 1
        if gaps:
            print("\n❌ 以下「门」既未入册、也未带理由豁免 ⇒ 它们不在回归网内：")
            for g in gaps:
                print("  " + g)
            print("\n  ⇒ 补法二选一：① 在 CASES 里加一条（推荐，附自断言 harness）；"
                  "② 在 EXEMPT 里写**理由**（不许留空）")
            return 1
        print("\n✅ 通过：已入册/间接覆盖/已豁免 + 待办之外，**没有**「既未入册、也无声明」的门")
        print(f"  · 观测面：**含项**=候选面 {gates} 个（判据 `{CODE_SHAPE}`；不要求作者写任何字样）；"
              f"**排除项**=① 不含 `{CODE_SHAPE}` 的件（例如只靠返回值/日志、或纯库件）"
              f"② 非 `tools/*.py` 的件（`scripts/`、插件目录等**未纳入候选面**）"
              f"③ 动态生成的判据（运行期才存在的门）"
              f"；**工具**=python3 静态扫描；**单位**=件；**时刻**={time.strftime('%Y-%m-%dT%H:%M:%S%z')}")
        print("  ★ 但如实声明：本件**仍不能**对「尚未写成 harness 的新事故」有判别力 ——")
        print("     那要求『事故先入册再修』的流程纪律，判据管不了流程。")
        if pend and strict:
            print("\n❌ --strict：待办项亦算未覆盖")
            return 1
        return 0
    print("incident-regression · 已知事故回归语料（编排层只汇总，判据在各 harness 内）")
    # ★★「盘面 vs 活体」声明（星桥判决 B 逐字要求）：本件所有 harness 都是**新进程读盘面**，
    #    故本矩阵是**关于盘面**的话；**在役实例可能是旧版** ⇒ 事故可能正在活体发生而矩阵全绿。
    #    ★ 不得把 N/N 读成「在役无此问题」；核对在役的两条通道见下。
    print("  ★ 矩阵口径：**盘面**（harness 均为新进程读盘上代码）—— **不等于在役**。")
    g = version_gap()
    if g["served"] is None:
        why = "；".join(g.get("errors", [])) or "原因未记录"
        print(f"    实算：盘面 **{g['disk']}** / 在役 **无 serve 记录** ⇒ 在役面**无留痕可判**（原因：{why}）")
    elif g["served"] == g["disk"]:
        print(f"    实算：盘面 **{g['disk']}** / 在役 **{g['served']}**（serve 记录 {g['servedAt']}·pid {g['servedPid']}）"
              f" ⇒ **当前同源**")
    else:
        d1, d2 = _vnum(g["served"]), _vnum(g["disk"])
        gap = "未知" if (d1 is None or d2 is None) else f"差 {d2 - d1} 次修订"
        print(f"    实算：盘面 **{g['disk']}** / 在役 **{g['served']}**"
              f"（serve 记录 {g['servedAt']}·pid {g['servedPid']}）⇒ **{g['served']} → {g['disk']}，{gap}** ——"
              f" ★ 在役**必然落后**（只在**宿主启动**时载入；盘面每改一次，差距就扩大一次），**不是「可能」**")
    print("    判在役请用：① `csx_status` 的 version/stage（「调一下」而非看工具表）"
          "② `tools/csx-mount-record-check.py --expect-current`（只看 mode=serve、且与盘面比）")
    print(f"  语料 {len(CASES)} 起 · 工作根 {HERE}\n")
    rows, bad = [], []
    for c in CASES:
        state, detail = run_case(c)
        rows.append((c["id"], state, detail))
        if not quiet:
            print(f"[{c['id']}] {state.upper():7s} {c['incident'][:46]}")
            print(f"          {detail}")
            print(f"          覆盖：{c['covers']}\n")
        # ★★ 通用形态（判决 B 给的）：「**入册须断言 harness 走的是用户会走的那条命令**」
        uc = c.get("user_command")
        if uc:
            # ★★ 扫描面（判决 B 第七次同形的修复）：不只"命令直接调用的文件"，还要把**被引用到的代码文件**
            #   一并纳入 —— 否则现场写在 shell 脚本/间接模块里时仍会漏。且**本轮扫描面必须打印出来**
            #   （观测面五要素：同一件内部也要继承，这正是它上一轮没继承的地方）。
            hay, scanned_paths = [], []
            cwd_case = c.get("cwd", HERE)
            # ★ 顺引用跟进（follow references / scan roots）—— 判决方 grep「引用·follow·scan_roots」零命中，
            #   根因是**我的标识符没用概念词**（原叫 ref_re/queue）。⇒ 现把概念词写进名字与注释，
            #   让别人按词能找到实现（可核性的一部分：**能被搜到**）。
            FOLLOW_REFERENCES_RE = re.compile(r"[\w./-]+\.(?:py|sh|bash|zsh|js|mjs|cjs|ts|tsx|rb|pl|fish)")
            queue = []
            for one in (c.get("cmds") or [c["cmd"]]):
                for tok in one:
                    if isinstance(tok, str):
                        queue.append(tok)
                hay.append(" ".join(str(x) for x in one))
            seen = set()
            while queue:
                tok = queue.pop(0)
                for base in (cwd_case, HERE):
                    cand = os.path.join(base, tok)
                    if not os.path.isfile(cand):
                        continue
                    rel = os.path.relpath(cand, HERE)
                    if rel in seen:
                        break
                    seen.add(rel)
                    # ★ 扫描面清单只列**源码/文本**件（第一版把解释器二进制也列进去了 ⇒ 声明里出现噪声）
                    if rel.endswith((".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".rb", ".pl")):
                        scanned_paths.append(rel)
                    try:
                        src = open(cand, encoding="utf-8", errors="replace").read()
                    except Exception:
                        break
                    hay.append(src)
                    # 被**文本引用**到的代码文件（若存在）也纳入扫描面 —— 覆盖 shell 脚本/间接入口
                    for m in FOLLOW_REFERENCES_RE.findall(src):
                        if m not in seen and os.path.isfile(os.path.join(HERE, m)):
                            queue.append(m)
                    break
            blob = "\n".join(hay)
            miss = [t for t in uc if t not in blob]
            if miss:
                print(f"      ❌ 场景覆盖核验未过：harness 里找不到用户命令的 {miss}"
                      f" ⇒ **harness 没走用户那条路**（判决 B 的形态）")
                bad.append(f"{c['id']}·场景")
            else:
                print(f"      ✓ 场景覆盖核验：harness 走到用户命令 {uc} 的现场")
            # ★ 扫描面**本轮如实打印**（同一件内部也要继承观测面五要素 —— 判决 B 的第七次）
            print(f"        · 场景核验的扫描面：**含项** = {len(scanned_paths)} 个文件"
                  f"（{', '.join(scanned_paths[:4])}{'…' if len(scanned_paths) > 4 else ''}）"
                  f" + 命令串本身；**排除项** = ① 运行期**动态构造**的路径（拼接/变量）"
                  f"② `import`/`require` 链里未被文本引用的模块 ③ 二进制/非文本件"
                  f"④ 非代码扩展名（.md/.json 等引用不跟进）"
                  f"；**补偿控制** = ① 判据是「用户命令字面必须出现」（宁可假红也不放过）"
                  f"② 缺项时**红**而不是「跳过」 ③ 扫描面每次打印、可被第三方复算"
                  f"；**判据** = 文本包含（正则级）；**单位** = 文件；**时刻** = {ts()}")
        if state != "pass":
            bad.append(c["id"])
    print("=== 汇总 ===")
    for cid, state, _ in rows:
        icon = {"pass": "✅", "fail": "❌", "skipped": "⊘", "timeout": "⏱"}[state]
        print(f"  {icon} {cid} {state}")
    if bad:
        print(f"\n❌ 有 {len(bad)} 起未通过：{bad} ⇒ ★ **在对任何判据做放宽/豁免/兜底之前，先看这里**")
        return 1
    print("\n✅ 全部已知事故今天仍按预期判决（该红的仍红、该绿的仍绿）")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv
             else main(enrollment="--enrollment-check" in sys.argv,
                       strict="--strict" in sys.argv))
