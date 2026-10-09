#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""self-report-gate.py — 自述可证性结构门（R-SR · v1.0.0）

对应规则：R-SR 自述可证性 —— agent 对自己作出的陈述，必须在**落盘前**由机器现场取值证成；
          不得以记忆中的读数充当证据。
门语义：输入一份「自述清单」(claims.json)；门**亲自执行**其中声明的命令并取值，与声称比对；
        五类陈述（数字 / 否定 / 环境 / 引用 / 写盘）任一不成立即阻塞落盘。
        ★ 关键设计：**我只许写命令与期望，不许写值** —— 切断「记忆 → 报告」这条通道。
补逻辑：2026-10-09 由**四个真实事故**逼出（非设计推演，每条断言都带 source）：
        · 报 `audit 46,111`，实测 24,382                → SR1 现场重测
        · 报 `writer 非空 = 0`，实则存在非空值            → SR2 阳性对照（同源两次假否定）
        · 表述里仍用已被作者撤回的 `standard.js` 限定词    → SR3 撤回传播
        · 报「本轮未写盘」，磁盘上有 2 个文件             → SR4 写盘自证
        · 一对 `std` 读数跨了**两个**进程边界             → SR5 环境指纹

约束使用对象（scope，先定对象再定工具）：
  · 主体：agent 会话（首发作用域 = session-1ffded95）
  · 产物：**落盘前**的自述性陈述（审查报告 / 板卡 / 声明 JSON）
  · 时机：persist 之前（写文件、发卡、过验收门之前），不是事后审计
  · 强度：硬门（不过即不许落盘）
  · 明确不管：业务断言（rule-judge L2 域）· 源码引用失效（citation-stale-check 域）
              · 卡片否定面 lint（absence-claim-lint 域）· 验收「通过」裁定（R046 域）
              · 风暴背压（floodgate 域）
  ★ 本门独立实现：不 import、不调用、不共享上述任何旧工具的判据集。

用法：
  python3 self-report-gate.py --check CLAIMS.json [--json-out F]
  python3 self-report-gate.py --demo                 # 用今天的真实事故现场跑一遍
  python3 self-report-gate.py --selftest             # 自测：**先跑反例**，再跑正例
  python3 self-report-gate.py --lean4-check          # 结构门自检（断言矩阵，条数运行时算）
  python3 self-report-gate.py --version
退出码：0 全部通过 · 1 存在 ❌ · 2 用法或 IO 错误

设计纪律（沿用本生态既有范式）：
  · selftest **必须先跑反例**（否则假阴性会被读成「全部新鲜」）
  · 断言矩阵条数**由运行时算出**，不写死数字

v1.1.0 修正（2026-10-09）—— **全部来自第三方裁定的实测**（裁定人 session-b250bf9d，裁定「不通过」）：
  · ④ 原声称「输出上限 200 行 ⇒ 防 300s/20MB 挂住」**与实现不符**：原实现是「读完再截断」
    ⇒ 200 行只是**显示上限**，百万行输出仍会先全部读进内存。现改**两层**：
    `MAX_READ_LINES=5000` 为**真读取上限**（超限即终止子进程）；`MAX_LINES=200` 为**显示上限**
    （截断只用于展示、**不参与计数**）。防挂住另靠 `DEF_TIMEOUT=30`。
  · SR3 原用子串互含匹配 ⇒ 第三方实测**双向失真**（短名 `stan` 会命中 `standard.js-*`＝假阳性；
    引用写法与 id 不同者会漏＝假阴性）。现改为**精确匹配**（`id` 或 `aliases` 精确相等）。
  · `--lean4-check` 的 ⑦ 原只测「文件是否存在」⇒ 属**用存在性检查冒充「不可用则 fail-closed」**；
    现改为**真造不可用状态**（把清单路径指向不存在处）再核。★ 被检机制（`sr3_retraction` 的
    `status != "ok" ⇒ 拒`）本身是对的 —— **弱的是检查方法，不是被检对象**。
  · `--lean4-check` 的 ⑧ 原用**行号比较** ⇒ 只是间接证据；现改为**真跑一次 selftest 并读其
    执行痕迹**（`_PHASES`），核的是执行顺序而非文本位置。
  · selftest 正例判据原混用 `ok is True` 与 truthy ⇒ 统一为**身份比较**。
  · ★ 另修一处**第三方未提、我自己发现**的缺陷：`count_hits` 原消费**已截断输出** ⇒ 命中数 >200
    时会**低估**；现 `run_cmd` 返回完整读入文本，截断仅用于展示。

v1.1.1 回归修复（2026-10-09，**修 v1.1.0 自己引入的缺陷**）：
  · v1.1.0 为修裁定 ④ 把 `subprocess.run(timeout=)` 换成了 `Popen + readline`，**丢掉了硬超时**：
    子进程「无输出且不退出」时 `readline` 永久阻塞 ⇒ `deadline` 检查永不执行 ⇒ **门自己挂死**
    （实测：`run_cmd("sleep 20", timeout=3)` 耗时 **20.0s**，应 3s）。
  · 现改用 `selectors.select(timeout=remaining)` **带超时等数据**，超时即 kill 子进程。
  · ★ 并把「门不会自己挂死」**变成用例**（selftest 的 **N7**）——
    此前 selftest/lean4-check/demo 的命令都秒回，**没有任何用例覆盖"命令静默挂住"**，
    所以「修 A 破 B」未被自检发现。**修一处必须同时给它加守护用例**。

v1.1.2（2026-10-09，采纳第三方裁定的**第二轮**逐项意见）：
  · **SR3 过窄方向**：他实测出第二方向 —— 撤回项的 **`id`**（如 `x-writer-is-signature`）竟
    `ok=True` **漏报**，根因同行 `it.get("pattern") or it.get("id")` 让 `id` 被忽略。
    v1.1.0 的精确匹配已同时收 `id`/`pattern`/`aliases`（该方向已修），**但当时缺用例**
    ⇒ 本版补 **N8**（引用 id 必须命中）作守护。
  · **SR2 区分两种成因**：对照 0 命中原是单一结论「载体失效」；现区分
    (a) 对照命令**执行失败**（rc≠0 且无输出）⇒ **载体状态未知**；(b) 正常执行但确实 0 命中
    ⇒ 载体失效。（`grep -c` 无命中时 rc=1 但输出 "0" ⇒ 属 (b)，不误判为失败。）
  · **SR5 收紧为 lstart 必填**：他给的具体点是 **pid 存在 ≠ 同一次启动**（pid 会被复用）
    ⇒ 只给 pid 的声明一律按 fail-closed 拒；补 **N9** 守护。
    `_carrier_pid()` 相应升级为 `_carrier_fp()`（pid + lstart）。
  · **selftest 报用例规模**：「0 FAIL」看不出规模 ⇒ 同时报「反例 N 条 / 正例 M 条」。

v1.1.3（2026-10-09，**第二次修我自己引入的缺陷**）：
  · v1.1.2 的 `_carrier_fp()` 用 `split()` + `" ".join()` 重建 lstart ⇒ 把 `ps` 的
    「Oct  9」（日期对齐用**双空格**）压成单空格 ⇒ SR5 的子串比较**假红**（--demo 的 D3 实测到）。
  · 现 SR5 两侧都**规范化空白**再比；并补 **P5**（用真实载体指纹建 SR5 正例）守护该往返。
  · ★ 与方法学教训同型第二次：**修 A 破 B 而未测 B**。v1.1.0 那次无人发现（命令都秒回）；
    这次被 `--demo` 覆盖到才暴露 ⇒ 再次印证「修一处必须同时加守护用例」。

v1.1.4（2026-10-09，**采纳第三方复验的条件②**；裁定人对 v1.1.1 判「通过（附三项条件）」）：
  · **SR5 两处收紧**：
    (a) `lstart` 由「包含关系」改为**精确相等**（原判据「包含什么？」本身不明）；
    (b) 新增**时序判据** —— 要求 `lstart(pid) ≤ 读数时刻 expect.at`。
        依据 = **我自己的 C7 事件**（pid 35869@02:03:59 → 49281@05:39:29）：原判据靠「pid 不存在」
        抓到载体更换，但「pid **存在**、而其实是【读数之后】才启动的新进程」**抓不到** ——
        那是同一根因的另一半。★ 与 **N9 不重复**（N9 核「现在」，本判据核「读数时刻」），
        第三方明确要求**两条都留**。补 **N10** 守护（用真实指纹 + 过去的读数时刻触发真分支）。
  · `expect.at` 缺省时**仍通过，但 detail 明写「★ 未核时序」** —— 不撒谎、也不假装核过。
  · ★ 条件①（selftest 报用例规模）已于 v1.1.2 采纳（现报「反例 N 条 / 正例 M 条」）。
  · ★ 条件③（L3 语义 groundedness）**仍未实现**，如实登记为未覆盖。
"""
__version__ = "1.1.4"

import argparse
import json
import os
import re
import selectors
import subprocess
import sys
import tempfile
import time


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/self-report-gate.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

HOME = os.path.expanduser("~")
RETRACTIONS = os.path.join(HOME, "dsh-collab", "docs", "retractions.json")
MAX_LINES = 200          # 显示上限：返回/打印时的行数上限（★ 不参与计数）
MAX_READ_LINES = 5000    # ★ 真读取上限：超过即终止子进程（防内存爆炸；2026-10-09 裁定 ④）
DEF_TIMEOUT = 30         # ★ 真防挂住靠它，而非行数上限（同上）


# ───────────────────────────── 基础设施 ─────────────────────────────
def run_cmd(cmd, timeout=DEF_TIMEOUT, cwd=None):
    """执行命令并取值。返回 (rc, out, note)。绝不抛异常到调用方。

    ★ v1.1.0：**读取上限是真的**——流式读，超过 MAX_READ_LINES 行即终止子进程并标注。
      原实现是「读完再截断」⇒ 200 行只是**显示上限**，百万行输出仍会先全部读进内存
      （2026-10-09 第三方裁定 ④：注释声称「防 300s/20MB 挂住」与实现不符）。
    ★ out 返回**完整读入文本**（不截断）；截断只发生在**展示**处 ⇒ 否则 count_hits 会低估。
    """
    try:
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True,
                             cwd=cwd or HOME, errors="replace")
    except Exception as e:
        return None, "", "exec-error:%s" % type(e).__name__
    lines, truncated, deadline = [], False, time.time() + timeout
    sel = selectors.DefaultSelector()
    sel.register(p.stdout, selectors.EVENT_READ)
    try:
        while True:
            remaining = deadline - time.time()
            if remaining <= 0 or not sel.select(timeout=remaining):
                # ★ v1.1.1 回归修复：必须用 select **带超时**等数据。
                #   否则「无输出且不退出」的子进程会让 readline 永久阻塞 ⇒ deadline 检查
                #   永不执行 ⇒ **门自己挂死**。这是 v1.1.0 为修裁定 ④（读取上限）而引入的
                #   回归：我把 subprocess.run(timeout=) 的硬超时换掉了，却只测了「上限生效」、
                #   没测「超时仍生效」⇒ 修 A 破 B 而未测 B。
                p.kill()
                return None, "\n".join(lines), "timeout(%ss)" % timeout
            line = p.stdout.readline()
            if not line:
                break
            if len(lines) < MAX_READ_LINES:
                lines.append(line.rstrip("\n"))
            else:
                truncated = True
                p.kill()          # ★ 超读取上限即终止，不再继续读
                break
    except Exception as e:
        try:
            p.kill()
        except Exception:
            pass
        return None, "\n".join(lines), "read-error:%s" % type(e).__name__
    try:
        rc = p.wait(timeout=max(1, int(deadline - time.time())))
    except Exception:
        try:
            p.kill()
        except Exception:
            pass
        rc = None
    out = "\n".join(lines)
    if truncated:
        out += "\n…[read-limit %d reached — 子进程已终止]" % MAX_READ_LINES
    return rc, out, ""


def count_hits(out):
    """把命令输出读成「命中数」：优先取末行纯数字，否则数非空行。"""
    lines = [l for l in (out or "").splitlines() if l.strip()]
    if not lines:
        return 0
    m = re.match(r"^\s*(\d+)\s*$", lines[-1])
    if m:
        return int(m.group(1))
    return len(lines)


def first_number(out):
    """取输出中最后一个独立数字（wc -l 之类）。"""
    nums = re.findall(r"\b(\d+)\b", out or "")
    return int(nums[-1]) if nums else None


def load_retractions():
    """撤回清单。缺失不致命，但必须如实标注（不得默认「没有撤回」）。"""
    if not os.path.exists(RETRACTIONS):
        return [], "missing-file"
    try:
        with open(RETRACTIONS, encoding="utf-8") as f:
            d = json.load(f)
        items = d.get("retractions") if isinstance(d, dict) else d
        return (items or []), "ok"
    except Exception as e:
        return [], "parse-error:%s" % type(e).__name__


# ───────────────────────────── 断言实现（每条一个纯函数）─────────────────────────────
def sr1_retest(c):
    """SR1 现场重测：门亲自跑 cmd，与声称值比对。"""
    cmd = c.get("cmd")
    if not cmd:
        return False, "缺 cmd —— 数字类自述必须给可执行命令（值由门跑出，不许凭记忆写值）"
    rc, out, note = run_cmd(cmd)
    if note:
        return False, "命令未能取值：%s" % note
    actual = first_number(out) if c.get("assert", {}).get("op", "number") == "number" else None
    claimed = c.get("reported")
    if claimed is None:
        return True, "取值成功（无声称值可对照）：actual=%r" % actual
    try:
        claimed_n = int(str(claimed).replace(",", "").strip())
    except Exception:
        claimed_n = None
    if actual is None:
        return False, "取不到数字：out=%r" % (out[:120],)
    if claimed_n == actual:
        return True, "现场值 = 声称值 = %d" % actual
    return False, "现场值 %d ≠ 声称值 %s ⇒ 引用自觉重测" % (actual, claimed)


def sr2_control(c):
    """SR2 阳性对照：否定类必须附一条必然命中的对照；对照 0 命中 ⇒ 载体失效、否定不成立。"""
    probe = c.get("cmd")
    ctrl = c.get("positive_control")
    if not probe:
        return False, "缺 cmd"
    if not ctrl:
        return False, "否定类自述必须附 positive_control（否则无法区分「真零」与「载体失效」）"
    rc_p, out_p, n_p = run_cmd(probe)
    rc_c, out_c, n_c = run_cmd(ctrl)
    if n_p or n_c:
        return False, "命令未能取值：probe=%s ctrl=%s" % (n_p, n_c)
    # ★ v1.1.2（第三方裁定建议）：对照 0 命中必须**区分两种成因** ——
    #   (a) 对照命令**执行失败**（rc≠0 且无任何输出）⇒ 载体状态**未知**
    #   (b) 对照命令正常执行但**确实 0 命中** ⇒ 载体失效
    #   例：`grep -c` 无命中时 rc=1 但输出 "0" ⇒ 属 (b)，不应误判为执行失败。
    if rc_c not in (0, None) and not (out_c or "").strip():
        return False, ("阳性对照**命令执行失败**（rc=%s 且无输出）⇒ 载体状态未知，"
                       "既不是「载体失效」也不是「真零」：对照=%s" % (rc_c, ctrl[:70]))
    hp, hc = count_hits(out_p), count_hits(out_c)
    if hc == 0:
        return False, ("阳性对照 0 命中 ⇒ **载体失效**（不是「没有」，是「测不到」）"
                       "：对照=%s" % ctrl[:70])
    if hp > 0:
        return False, "探针命中 %d > 0 ⇒ 否定不成立（对照命中 %d，载体有效）" % (hp, hc)
    return True, "探针 0 命中 ∩ 对照 %d 命中 ⇒ 否定在有效载体上成立" % hc


def sr3_retraction(c):
    """SR3 撤回传播：引用的判据若在撤回清单内且未标注重读 ⇒ 拒。

    ★ v1.1.0：改为**精确匹配**（`id` 或 `aliases` 精确相等），**禁止子串互含**。
      原实现 `pat in r or r in pat` 被第三方实测出**双向失真**：
        · 假阳性：短名 `stan` 会命中 `standard.js-narrower-condition`
        · 假阴性：引用写法与 id 不同者会漏
    """
    refs = c.get("refs") or []
    if not refs:
        return True, "无引用项（本断言不适用）"
    items, status = load_retractions()
    if status != "ok":
        return False, "撤回清单不可用（%s）⇒ 无法证「引用未失效」，按 fail-closed 拒" % status
    hit = []
    for r in refs:
        rn = str(r).strip()
        if not rn:
            continue
        for it in items:
            keys = set()
            for k in ("id", "pattern"):
                if it.get(k):
                    keys.add(str(it[k]).strip())
            for a in (it.get("aliases") or []):
                if a:
                    keys.add(str(a).strip())
            keys.discard("")
            if rn in keys:                      # ★ 精确相等，不做互含
                hit.append(rn)
                break
    if not hit:
        return True, "引用 %d 项，撤回清单 %d 项，精确匹配无命中" % (len(refs), len(items))
    if c.get("reread_after_retraction") is True:
        return True, "引用命中撤回清单（%s），但已显式声明按撤回后口径重读" % hit[0][:60]
    return False, "引用了已被撤回的判据且未标注重读：%s" % ", ".join(h[:50] for h in hit[:3])


def sr4_write(c):
    """SR4 写盘自证：凡「我没写」类断言，门亲自扫 mtime。"""
    dirs = c.get("scan") or []
    since = c.get("since")
    if not dirs or not since:
        return False, "写盘类自述必须给 scan(目录) 与 since(ISO 时刻)"
    try:
        t0 = time.mktime(time.strptime(since.replace("T", " ")[:19], "%Y-%m-%d %H:%M:%S"))
    except Exception:
        return False, "since 解析失败：%r" % since
    hits = []
    for d in dirs:
        d = os.path.expanduser(d)
        for root, _dirs, files in os.walk(d):
            if "/node_modules" in root or "/.git" in root:
                continue
            for fn in files:
                p = os.path.join(root, fn)
                try:
                    mt = os.path.getmtime(p)
                except OSError:
                    continue
                if mt >= t0:
                    hits.append((p, mt))
    if not hits:
        return True, "扫描 %d 目录、窗口自 %s ⇒ 0 个新写入，自述成立" % (len(dirs), since)
    hits.sort(key=lambda x: -x[1])
    shown = "; ".join("%s(%s)" % (os.path.basename(p), time.strftime("%m-%d %H:%M", time.localtime(m)))
                      for p, m in hits[:5])
    return False, "声称未写盘，实测 %d 个文件落在窗口内：%s" % (len(hits), shown)


def sr5_env(c):
    """SR5 环境指纹：运行态断言必须带 **pid + lstart**，门亲自核对。

    ★ v1.1.2（第三方裁定给出的「不足」的具体点）：**pid 存在 ≠ 同一次启动**。
      原实现允许只给 pid（仅核存在性）⇒ 若 pid 被复用，新进程会被误认为原载体。
      现要求 **lstart 必填**：只给 pid 的声明一律按 fail-closed 拒。
    """
    exp = c.get("expect") or {}
    if not exp.get("pid"):
        return False, "环境类自述必须带 expect.pid（运行态断言不带指纹 ⇒ 分不开「重启生效」与「热重载生效」）"
    if not exp.get("lstart"):
        return False, ("环境类自述必须带 expect.lstart —— **pid 存在 ≠ 同一次启动**"
                       "（pid 会被复用；只核存在性会把新进程误认为原载体）")
    pid = str(exp["pid"])
    try:
        r = subprocess.run(["ps", "-p", pid, "-o", "pid=,lstart="],
                           capture_output=True, text=True, timeout=10)
    except Exception as e:
        return False, "ps 失败：%s" % type(e).__name__
    line = (r.stdout or "").strip()
    if not line:
        return False, "pid %s 不存在 ⇒ 断言时刻的载体已换（该读数跨了进程边界）" % pid
    # ★ v1.1.3：两侧都要**规范化空白**再比 —— `ps` 的 lstart 是「Oct  9」（日期对齐用双空格），
    #   而调用方给的常是单空格 ⇒ 直接子串比较会**假红**（v1.1.2 实测到）。
    def _norm(s):
        return " ".join((s or "").split())

    # ★ v1.1.4（第三方复验条件②）两处收紧：
    #   (a) lstart 由「包含关系」改为**精确相等** —— 原判据「包含什么？」本身不明。
    #   (b) 新增**时序判据**：要求 lstart(pid) ≤ 读数时刻 expect.at。
    #       依据 = 我自己的 C7 事件（pid 35869@02:03:59 → 49281@05:39:29）：原判据靠
    #       「pid 不存在」抓到载体更换；但「pid **存在**、而其实是【读数之后】才启动的新进程」
    #       抓不到 —— 那是同一根因的**另一半**。
    #       ★ 与 N9 **不重复**：N9 核「现在」，本判据核「读数时刻」（第三方明确要求两条都留）。
    ls_want = _norm(exp["lstart"])
    ls_actual = _norm(line[len(pid):]) if line.startswith(pid) else _norm(line)
    if ls_actual != ls_want:
        return False, "pid %s 存在但 lstart 不精确相等：期望 %r，实测 %r" % (pid, ls_want, ls_actual)
    at = exp.get("at")
    if not at:
        return True, ("载体指纹一致（pid=%s lstart=%s）；★ **未核时序**：缺 expect.at ⇒ "
                      "无法判「该载体在读数时刻是否已存在」" % (pid, ls_want))
    try:
        t_ls = time.mktime(time.strptime(ls_want, "%a %b %d %H:%M:%S %Y"))
        t_at = time.mktime(time.strptime(str(at).replace("T", " ")[:19], "%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        return False, "时序判据无法求值（%s）⇒ fail-closed 拒" % type(e).__name__
    if t_ls > t_at + 2:
        return False, ("★ **载体时刻不符**：pid=%s 的 lstart=%s **晚于**读数时刻 %s ⇒ "
                       "该读数是【读数之后才启动】的进程做的" % (pid, ls_want, at))
    return True, "载体指纹一致且时序成立：pid=%s lstart=%s ≤ 读数时刻 %s" % (pid, ls_want, at)


# ───────────────── SR6 · 修复路径覆盖（独立入口，不属于 claim 的 kind）─────────────────
def _git_diff_paths(base_ref, repo_root):
    """用 git diff 枚举本次修复触及的文件路径。

    ★ 认 M/A/R/D **全部状态** —— 只认 M/A 会把重命名误判为漏标。
    ★ R（重命名）**同时给出 old 与 new 两个路径** —— 否则重命名会被算成
      「漏标旧路径 + 多标新路径」两处错。
    """
    try:
        r = subprocess.run(["git", "diff", "--name-status", base_ref],
                           capture_output=True, text=True, timeout=30, cwd=repo_root)
    except Exception as e:
        return None, "git-diff-error:%s" % type(e).__name__
    if r.returncode != 0:
        return None, "git-diff-rc=%s:%s" % (r.returncode, (r.stderr or "").strip()[:120])
    out = {}
    for line in (r.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        st = parts[0].strip()
        if st.startswith("R") and len(parts) >= 3:
            out[parts[1].strip()] = st
            out[parts[2].strip()] = st
        else:
            out[parts[1].strip()] = st
    # ★ 第四个边界（2026-10-09 实测发现）：**`git diff` 不显示未跟踪文件**。
    #   ⇒ 「本次修复新建的文件」diff 枚举不到 ⇒ 应走**豁免入口**（`why_not_in_diff`）。
    #   ★ 但**不能**把全部未跟踪文件并入 diff 集合：实测本仓库 untracked = 64 个，
    #     其中绝大多数是**历史遗留的未入库产物**（不是本次修复）⇒ 并入会造成大面积假漏标。
    #   ⇒ 处置：untracked **不进判据**，只作**观测面**计数并在判定里输出
    #     （让「有多少未跟踪文件」可见，从而不被无声忽略）。
    global _LAST_UNTRACKED
    _LAST_UNTRACKED = []
    try:
        r2 = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"],
                            capture_output=True, text=True, timeout=30, cwd=repo_root)
        if r2.returncode == 0:
            _LAST_UNTRACKED = [p.strip() for p in (r2.stdout or "").splitlines() if p.strip()]
    except Exception:
        pass
    return out, ""


# ★ 用例登记表：单一来源 = **运行时真实登记**，不是静态解析源码。
#   v1 的教训（2026-10-09，同一形状第四次）：原实现静态解析 `neg = [...]` / `pos = [...]`
#   ⇒ **解析不到内联的用例**（N7 / N10 / P3 / P4 / P5 都不在列表里，是内联检查）
#   ⇒ SR6 会把它们误报为「不存在」＝**假红**。
#   ⇒ 改为由 selftest 在**执行时**登记：**登记即事实**（与「执行它，而不是阅读它」同源）。
CASE_KINDS = {}

# ★ 观测面：上一次 _git_diff_paths 看到的未跟踪文件（**不进判据**，只供输出）
_LAST_UNTRACKED = []


def _register_case(cid, kind):
    """把一条用例及其属性（'fail'=必须被拒 / 'pass'=必须通过）登记进表。"""
    CASE_KINDS[cid] = kind


def _ensure_cases_loaded():
    """确保登记表已填充：为空则**真跑一次 quiet selftest**（登记即事实）。"""
    if not CASE_KINDS:
        try:
            selftest(quiet=True)
        except Exception:
            pass
    return CASE_KINDS


def sr6_fix_coverage(fix, repo_root, src_path):
    """SR6 · 修复路径覆盖（v1 · 2026-10-09）。

    目标形状（今晚双方各实证三次）：**修复引入了【新路径】，而验证只覆盖【旧路径】**。
    本断言不看「我说得对不对」（那是 SR1–SR5），只看：**本次修复触及的每条路径，
    有没有对应的守护用例；且【哪些路径被触及】由 git diff 枚举、不由我列举。**

    ★ v1 粒度限度（如实声明）：差集只做到**文件级**；声明里的「符号名」仅作记录，
      不参与差集（符号级 diff 未做）。另：**不判 path 与 case 的语义相关性**
      （即「这个 case 真能守这条路径吗」不在本版判据内）—— 那是更强的一档，未实现。

    ★★ `base_ref` 的语义（决定 diff 的范围，进而决定「什么算本次修复」）：
      · `base_ref = 本次修复【开始前】的 commit` ⇒ diff **只含修复期间的改动** ⇒ **这是推荐用法**
      · `base_ref = HEAD` ⇒ diff = **工作区全部未提交改动**（可能含**第三方在途改动**）
        ⇒ 此时 SR6 会要求把那些文件也声明或豁免 —— 这不是误报，而是它**如实**报告
        「diff 范围内有未覆盖的路径」。★ 在共享仓库里跑 SR6，请优先用前者。

    判据（四条，全部可机械核）：
      ① 完整性（双向差集）：diff 枚举 vs 声明 ⇒ 漏标 FAIL、多标 FAIL
         （豁免从「漏标」中扣除，但必须逐条列举并计数 —— 防豁免变成新后门）
      ② case 存在：每个 case 名在本门源码里真实存在
      ③ expect 相符：case 的负/正属性必须与声明的 expect 一致（neg↔fail、pos↔pass）
      ④ 不许空集：paths 为空而 diff 非空 ⇒ FAIL（防「本次无需用例」式自免）
    """
    rows = []

    def rec(i, ok, msg):
        rows.append({"id": i, "ok": bool(ok), "detail": msg})

    base = fix.get("base_ref")
    if not base:
        rec("SR6-🔒base_ref", False, "缺 base_ref ⇒ fail-closed 拒（不猜与什么 diff 比）")
        return rows

    paths = fix.get("paths") or []
    exemptions = fix.get("exemptions") or []

    diff_map, err = _git_diff_paths(base, repo_root)
    if diff_map is None:
        rec("SR6-🔒diff", False, "无法取 diff：%s" % err)
        return rows
    diff_files = set(diff_map.keys())

    declared = set()
    for p in paths:
        pf = str(p.get("path") or "").split(":")[0].strip()
        if pf:
            declared.add(pf)

    if not declared and diff_files:
        rec("SR6-④空集自免", False, "paths 为空而 diff 非空（%d 文件）⇒ 拒" % len(diff_files))
    else:
        rec("SR6-④空集自免", True, "paths=%d 文件 · diff=%d 文件" % (len(declared), len(diff_files)))
    # ★ 观测面（**不进判据**）：未跟踪文件数 —— 让「有多少未覆盖的未入库文件」可见。
    #   本次修复若**新建**文件，`git diff` 枚举不到 ⇒ 必须走豁免 `why_not_in_diff`。
    rec("SR6-◻观测:未跟踪文件", True,
        "untracked=%d 个（不进判据；新建文件须走豁免）" % len(_LAST_UNTRACKED))

    exempt_files = set()
    for e in exemptions:
        ef = str(e.get("path") or "").split(":")[0].strip()
        if ef:
            exempt_files.add(ef)
    missing = sorted(diff_files - declared - exempt_files)
    # ★ 豁免的路径同样不算「多标」 —— 否则「豁免一条不在 diff 里的路径」会自相矛盾。
    extra = sorted(declared - diff_files - exempt_files)
    rec("SR6-①a漏标", not missing,
        "OK" if not missing else "diff 触及但未声明（%d）：%s" % (len(missing), "; ".join(missing[:5])))
    rec("SR6-①b多标", not extra,
        "OK" if not extra else "声明了但 diff 未触及（%d）：%s" % (len(extra), "; ".join(extra[:5])))
    # ★ 豁免分两类（实现时发现的第三个边界，2026-10-09）：
    #   (a) **行为级修复**：不在 diff 里 ⇒ 必须给 `why_not_in_diff`（说明为何 diff 枚举不到）
    #   (b) **非本次修复的改动**（如共享仓库里他人的在途改动）：**在 diff 里**但不属本次
    #       ⇒ 用 `not_mine: true` 声明。★ 二者不可混：»与被审对象无关« ≠ »与本次修复无关«。
    #   两类都必须给**具体 reason**；缺则 FAIL。
    def _ex_ok(e):
        if not e.get("reason"):
            return False
        return bool(e.get("why_not_in_diff")) or bool(e.get("not_mine"))

    bad_ex = [e for e in exemptions if not _ex_ok(e)]
    rec("SR6-①c豁免计数", not bad_ex,
        "豁免 %d 条（行为级 %d / 非本次修复 %d），均带具体理由"
        % (len(exemptions),
           sum(1 for e in exemptions if e.get("why_not_in_diff")),
           sum(1 for e in exemptions if e.get("not_mine")))
        if not bad_ex
        else "%d 条豁免理由不成立（需 reason + why_not_in_diff 或 not_mine）" % len(bad_ex))

    kinds = _ensure_cases_loaded()
    if not kinds:
        rec("SR6-②case存在", False, "用例登记表为空（selftest 未能登记）⇒ fail-closed 拒")
        return rows
    neg_ids = {k for k, v in kinds.items() if v == "fail"}
    pos_ids = {k for k, v in kinds.items() if v == "pass"}

    bad_case, bad_expect = [], []
    for p in paths:
        cid = str(p.get("case") or "").strip()
        exp = p.get("expect")
        if not cid:
            bad_case.append("(空)")
            continue
        if cid not in neg_ids and cid not in pos_ids:
            bad_case.append(cid)
            continue
        actual = "fail" if cid in neg_ids else "pass"
        if exp not in ("fail", "pass"):
            bad_expect.append("%s(缺 expect)" % cid)
        elif exp != actual:
            bad_expect.append("%s(声明 %s / 实际 %s)" % (cid, exp, actual))
    rec("SR6-②case存在", not bad_case,
        "%d 个 case 全部存在（neg %d / pos %d）" % (len(paths), len(neg_ids), len(pos_ids))
        if not bad_case else "不存在的 case：%s" % ", ".join(bad_case[:5]))
    rec("SR6-③expect相符", not bad_expect,
        "全部 expect 与用例属性相符" if not bad_expect else "不符：%s" % ", ".join(bad_expect[:5]))
    return rows


ASSERTIONS = [
    ("SR1", "现场重测", "number", sr1_retest, "2026-10-09 audit 46,111 事件"),
    ("SR2", "阳性对照", "negative", sr2_control, "同日两次假否定（端点错 / 中文被 shell 吃掉）"),
    ("SR3", "撤回传播", "ref", sr3_retraction, "standard.js 更窄条件被作者撤回后仍被引用"),
    ("SR4", "写盘自证", "write", sr4_write, "「本轮未写盘」而磁盘上有 2 个文件"),
    ("SR5", "环境指纹", "env", sr5_env, "std 读数跨两个进程边界（3901→50425→35869）"),
]
BY_KIND = {k: fn for _i, _n, k, fn, _s in ASSERTIONS}


# ───────────────────────────── 判定 ─────────────────────────────
def judge(claims):
    rows = []
    for c in claims:
        kind = c.get("kind", "number")
        if kind not in BY_KIND:
            rows.append({"id": c.get("id"), "kind": kind, "ok": False,
                         "detail": "未知陈述种类 %r（L1 契约校验拒）" % kind})
            continue
        try:
            ok, detail = BY_KIND[kind](c)
        except Exception as e:
            ok, detail = False, "断言异常（按 fail-closed 拒）：%s" % type(e).__name__
        rows.append({"id": c.get("id"), "kind": kind, "text": c.get("text", ""),
                     "ok": ok, "detail": detail})
    return rows


def report(rows, title="自述门判定"):
    print("== %s ==" % title)
    bad = 0
    for r in rows:
        mark = "✅" if r["ok"] else "❌"
        if not r["ok"]:
            bad += 1
        print("%s %-6s [%-8s] %s" % (mark, r.get("id"), r.get("kind"), r.get("detail")))
        if r.get("text"):
            print("     自述：%s" % r["text"])
    print("-- 合计 %d 条：✅ %d / ❌ %d --" % (len(rows), len(rows) - bad, bad))
    return bad


# ───────────────────────────── 自检（反例先行）─────────────────────────────
_PHASES = []   # ★ selftest 的**执行痕迹**：lean4_check 的 ⑧ 消费它，而非比较行号


def selftest(quiet=False):
    """自测：**先跑反例**，再跑正例。返回 (rc, phases)。

    ★ v1.1.0：新增 `quiet` 与执行痕迹 `_PHASES` ——
      lean4_check 的 ⑧ 由「行号比较（只算间接证据）」改为「**真跑一次并读执行痕迹**」。
    ★ 判据统一为身份比较（`is True` / `is False`），不再混用 truthy。
    """
    _PHASES.clear()

    def out(*a):
        if not quiet:
            print(*a)

    out("== self-report-gate selftest ==")
    out("【第一段：反例（必须全部被拒）】")
    _PHASES.append("negative")
    bad = 0
    tmp = tempfile.mkdtemp(prefix="srg-selftest-")
    fresh = os.path.join(tmp, "written-now.txt")
    with open(fresh, "w") as f:
        f.write("x\n")
    ancient = os.path.join(tmp, "ancient.txt")
    with open(ancient, "w") as f:
        f.write("y\n")
    os.utime(ancient, (0, 0))  # 1970 ⇒ 必然早于窗口

    neg = [
        ({"id": "N1", "kind": "number", "text": "audit 总行数",
          "cmd": "seq 1 24382 | wc -l", "reported": 46111}, "SR1 声称值与现场值不符"),
        ({"id": "N2", "kind": "negative", "text": "不存在非空 writer",
          "cmd": "printf '' | wc -l",
          "positive_control": "grep -c 'ZZZ_NO_SUCH_TOKEN_ZZZ' /etc/hosts"},
         "SR2 阳性对照 0 命中 ⇒ 载体失效"),
        ({"id": "N3", "kind": "ref", "text": "std = standard.js 最近加载时的 PKG_VERSION",
          "refs": ["standard.js-narrower-condition"]}, "SR3 引用已撤回判据"),
        ({"id": "N6", "kind": "ref", "text": "短名不应误命中撤回项",
          "refs": ["stan"]}, "SR3 假阳性（互含）⇒ 必须不判为命中"),
        ({"id": "N4", "kind": "write", "text": "本轮未写盘",
          "scan": [tmp], "since": "1970-01-02T00:00:00"}, "SR4 称未写盘而窗口内有写入"),
        ({"id": "N5", "kind": "env", "text": "std 读数取自同一进程",
          "expect": {"pid": "999999", "lstart": "Thu Jan  1 00:00:00 1970"}},
         "SR5 载体不存在（pid 已消失）"),
        ({"id": "N8", "kind": "ref", "text": "引用撤回项的 **id** 本身（SR3 过窄方向）",
          "refs": ["x-writer-is-signature"]},
         "SR3 假阴性：引用 id 必须命中（原实现 `pattern or id` 会忽略 id）"),
        ({"id": "N9", "kind": "env", "text": "只给 pid 不给 lstart",
          "expect": {"pid": "1"}},
         "SR5 新判据：pid 存在 ≠ 同一次启动 ⇒ 缺 lstart 必须拒"),
    ]
    neg_n = 0          # ★ v1.1.4：动态计数（原 `len(neg)+1` 在加入 N10 后漏计为 9）
    for c, why in neg:
        neg_n += 1
        _register_case(c["id"], "fail")
        ok, detail = BY_KIND[c["kind"]](c)
        # ★ N6 是**反向负例**：SR3 应当【不命中】⇒ 判 True 才对
        want_false = (c["id"] != "N6")
        good = (ok is False) if want_false else (ok is True)
        out("  %s 负例 %-4s %s" % ("✅" if good else "❌", c["id"], why))
        out("       门判：%s" % detail)
        if not good:
            bad += 1

    # ★ N7（v1.1.1）：静默命令必须**在 timeout 内返回** —— 守护「门不会自己挂死」
    #    这是 v1.1.0 回归的守护用例：Popen+readline 丢掉了 subprocess.run 的硬超时。
    t0 = time.time()
    _rc7, _o7, note7 = run_cmd("sleep 8", timeout=2)
    dt7 = time.time() - t0
    ok7 = (note7.startswith("timeout") and dt7 < 5.0)
    out("  %s 负例 N7 静默命令须在 timeout 内返回 —— dt=%.1fs note=%r（阈值 dt<5s）"
        % ("✅" if ok7 else "❌", dt7, note7))
    neg_n += 1          # N7
    _register_case("N7", "fail")
    if not ok7:
        bad += 1

    # ★ N10（v1.1.4）：**载体时刻晚于读数时刻** ⇒ 必须拒（第三方复验条件②的时序判据）
    #    用**真实**载体指纹 + 一个**过去的**读数时刻 ⇒ 必然触发时序分支（不是伪造 lstart）。
    _fp10 = _carrier_fp()
    neg_n += 1          # N10（无论是否 skipped，都占一条用例位）
    _register_case("N10", "fail")
    if _fp10.get("pid") and _fp10.get("lstart"):
        ok10, d10 = sr5_env({"id": "N10", "expect": {
            "pid": _fp10["pid"], "lstart": _fp10["lstart"], "at": "1970-01-01T00:00:00"}})
        out("  %s 负例 N10 载体时刻晚于读数时刻（真实指纹 + 1970 年的读数时刻）⇒ 必须拒"
            % ("✅" if ok10 is False else "❌"))
        out("       门判：%s" % d10)
        if ok10 is not False:
            bad += 1
    else:
        out("  ⏭ 负例 N10 skipped（取不到真实载体指纹）")

    out("【第二段：正例（必须全部通过）】")
    _PHASES.append("positive")
    pos_n = 0          # ★ 动态计数
    pos = [
        ({"id": "P1", "kind": "number", "cmd": "seq 1 24382 | wc -l", "reported": 24382},
         "现场值=声称值", sr1_retest),
        ({"id": "P2", "kind": "negative", "cmd": "grep -c 'ZZZ_NO_SUCH_TOKEN_ZZZ' /etc/hosts",
          "positive_control": "grep -c 'localhost' /etc/hosts"},
         "探针 0 命中且对照命中>0", sr2_control),
    ]
    # P3 设计为「反向正例」：窗口覆盖写入时刻 ⇒ 必须拒
    pos_n += 1
    _register_case("P3", "fail")   # ★ P3 是「反向正例」⇒ 属性是 fail（要求它被拒）
    ok3, d3 = sr4_write({"id": "P3", "scan": [tmp], "since": "1970-01-01T00:00:00"})
    out("  %s 正例 P3 反向自证：窗口覆盖写入时刻 ⇒ 必须拒" % ("✅" if ok3 is False else "❌"))
    out("       门判：%s" % d3)
    if ok3 is not False:
        bad += 1
    for c, why, fn in pos:
        pos_n += 1
        _register_case(c["id"], "pass")
        ok, detail = fn(c)
        good = (ok is True)
        out("  %s 正例 %-4s %s" % ("✅" if good else "❌", c["id"], why))
        out("       门判：%s" % detail)
        if not good:
            bad += 1
    pos_n += 1
    _register_case("P4", "pass")
    ok4, d4 = sr4_write({"id": "P4", "scan": [tmp], "since": "2030-01-01T00:00:00"})
    out("  %s 正例 P4 窗口在未来（无写入）⇒ 应通过" % ("✅" if ok4 is True else "❌"))
    out("       门判：%s" % d4)
    if ok4 is not True:
        bad += 1

    # ★ P5（v1.1.3）：**lstart 往返**必须一致 —— 守护 `ps` 双空格 vs 单空格造成的假红。
    #    用真实载体指纹建一条 SR5 正例；若本机取不到承载进程，则如实标 skipped（不算 FAIL）。
    _fp = _carrier_fp()
    pos_n += 1
    _register_case("P5", "pass")
    if _fp.get("pid") and _fp.get("lstart"):
        ok5, d5 = sr5_env({"id": "P5", "expect": _fp})
        out("  %s 正例 P5 lstart 往返一致性（pid=%s）" % ("✅" if ok5 is True else "❌", _fp.get("pid")))
        out("       门判：%s" % d5)
        if ok5 is not True:
            bad += 1
    else:
        out("  ⏭ 正例 P5 skipped（本机取不到承载进程指纹 ⇒ 如实例报 skipped，不算 FAIL）")

    # ★ v1.1.2（第三方建议）：只报 FAIL 数看不出用例规模 ⇒ 同时报「N 反例 / M 正例」
    out("\nselftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条（0 FAIL = 门有判别力且正例不误杀）"
        % (bad, neg_n, pos_n))
    return (0 if bad == 0 else 1), list(_PHASES)


def lean4_check():
    """结构门自检证明：断言矩阵 + 判别力矩阵（**条数运行时算出**）。"""
    print("== self-report-gate --lean4-check ==")
    checks = []
    # ① 断言矩阵在场且 kind 互不重叠
    kinds = [k for _i, _n, k, _f, _s in ASSERTIONS]
    checks.append(("① 断言矩阵在场", len(ASSERTIONS) > 0, "条数=%d（运行时算）" % len(ASSERTIONS)))
    checks.append(("② kind 无重复", len(kinds) == len(set(kinds)), "kinds=%s" % ",".join(kinds)))
    # ③ 判定函数均为可调用且是纯函数形态
    checks.append(("③ 每断言一个判定函数", all(callable(f) for _i, _n, _k, f, _s in ASSERTIONS),
                   "全部 callable"))
    # ④ 每条断言带 source（来自真实事故，不许凭空设计）
    checks.append(("④ 每条断言带事故来源", all(bool(s) for _i, _n, _k, _f, s in ASSERTIONS),
                   "sources=%d/%d" % (sum(1 for _i, _n, _k, _f, s in ASSERTIONS if s), len(ASSERTIONS))))
    # ⑤ 缺 cmd 的数字类必被拒（fail-closed）
    o, _d = sr1_retest({"kind": "number"})
    checks.append(("⑤ fail-closed：缺 cmd 即拒", o is False, "sr1(缺cmd)=%s" % o))
    # ⑥ 否定类缺对照必被拒
    o, _d = sr2_control({"cmd": "true"})
    checks.append(("⑥ 否定类缺对照即拒", o is False, "sr2(缺对照)=%s" % o))
    # ⑦ 撤回清单**真不可用**时 ⇒ fail-closed
    #    ★ v1.1.0：原实现是 `o is False or os.path.exists(RETRACTIONS)` ⇒ 只测了**文件存在性**，
    #      根本没造出「不可用」状态（第三方裁定：这属于「检查项写的是 A、实际测的是 B」）。
    #      现改为：把清单路径指向不存在处，**真造不可用态**，再核 sr3 是否 fail-closed。
    global RETRACTIONS
    _saved_retr = RETRACTIONS
    try:
        RETRACTIONS = "/nonexistent/__no_such_retractions__.json"
        o7, d7 = sr3_retraction({"refs": ["anything-at-all"]})
    finally:
        RETRACTIONS = _saved_retr
    checks.append(("⑦ 撤回清单不可用则 fail-closed（真造不可用态，非存在性检查）",
                   o7 is False, "sr3(清单不可用)=%s" % o7))
    # ⑧ selftest 反例先行 —— ★ 由**执行痕迹**证明，而非行号比较
    #    （第三方裁定：行号先后只是间接证据；现真跑一次 quiet selftest 读 _PHASES）
    _rc8, phases = selftest(quiet=True)
    checks.append(("⑧ selftest 反例先行（读执行痕迹，非行号）",
                   phases == ["negative", "positive"],
                   "实测执行顺序=%s；该次 rc=%d" % (phases, _rc8)))
    okall = True
    for name, ok, detail in checks:
        print("  %s %s — %s" % ("✅" if ok else "❌", name, detail))
        okall = okall and ok
    print("-- %d/%d checks pass；断言矩阵 %d 条 --" % (sum(1 for _n, o, _d in checks if o),
                                                       len(checks), len(ASSERTIONS)))
    return 0 if okall else 1


def fix_selftest():
    """SR6 自测：**反例先行**（照本门既有纪律），再跑正例。

    ★ 动态构造：用真实 repo 的 `git diff HEAD` 结果做基准，避免写死路径
      —— 否则一旦仓库状态变化，用例本身就成了假绿来源。
    ★ 返回 (rc, phases)；phases 供 lean4 式自检消费。
    """
    phases = []
    print("== SR6 fix-coverage selftest ==")
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(here)
    src = os.path.abspath(__file__)
    bad = 0

    print("【第一段：反例（必须被拒）】")
    phases.append("negative")

    r = sr6_fix_coverage({"paths": []}, repo, src)
    ok_a = any(not x["ok"] for x in r)
    print("  %s 负例 a 缺 base_ref ⇒ 必须拒（fail-closed，不猜与什么 diff 比）" % ("✅" if ok_a else "❌"))
    if not ok_a:
        bad += 1

    dm, err = _git_diff_paths("HEAD", repo)
    has_diff = bool(dm)
    if not has_diff:
        print("  ⏭ 负例 b–e 与正例 P skipped（`git diff HEAD` 为空 ⇒ 无法构造真实基准）")
    else:
        r = sr6_fix_coverage({"base_ref": "HEAD", "paths": []}, repo, src)
        ok_b = any((not x["ok"]) and ("空集" in x["id"]) for x in r)
        print("  %s 负例 b paths 为空而 diff 非空 ⇒ 空集自免必须拒" % ("✅" if ok_b else "❌"))
        if not ok_b:
            bad += 1

        files = sorted(dm.keys())
        f0 = files[0]
        r = sr6_fix_coverage({"base_ref": "HEAD",
                              "paths": [{"path": "/no/such/file.xyz", "case": "N10", "expect": "fail"}]},
                             repo, src)
        ok_c = any((not x["ok"]) and ("多标" in x["id"]) for x in r)
        print("  %s 负例 c 声明了 diff 未触及的路径 ⇒ 多标必须拒" % ("✅" if ok_c else "❌"))
        if not ok_c:
            bad += 1

        r = sr6_fix_coverage({"base_ref": "HEAD",
                              "paths": [{"path": f0, "case": "Z99", "expect": "fail"}]}, repo, src)
        ok_d = any((not x["ok"]) and ("case存在" in x["id"]) for x in r)
        print("  %s 负例 d case 名不存在（Z99）⇒ 必须拒" % ("✅" if ok_d else "❌"))
        if not ok_d:
            bad += 1

        r = sr6_fix_coverage({"base_ref": "HEAD",
                              "paths": [{"path": f0, "case": "N10", "expect": "pass"}]}, repo, src)
        ok_e = any((not x["ok"]) and ("expect" in x["id"]) for x in r)
        print("  %s 负例 e N10 是负例却声明 expect=pass ⇒ 必须拒" % ("✅" if ok_e else "❌"))
        if not ok_e:
            bad += 1

        print("【第二段：正例（必须通过）】")
        phases.append("positive")
        # ★ 正例必须**声明 diff 里的全部文件** —— 否则 SR6 正确地报「漏标」。
        #   （仓库里常有第三方在途改动；对它们报漏标是 SR6 该有的反应，不是用例该绕过的）
        allp = [{"path": f, "case": "N10", "expect": "fail"} for f in files]
        allp.append({"path": f0, "case": "P5", "expect": "pass"})
        r = sr6_fix_coverage({"base_ref": "HEAD", "paths": allp}, repo, src)
        ok_p = all(x["ok"] for x in r)
        print("  %s 正例 P 全部一致（路径在 diff 内 · case 存在 · expect 相符）⇒ 应通过" % ("✅" if ok_p else "❌"))
        for x in r:
            if not x["ok"]:
                print("       未过：%s — %s" % (x["id"], x["detail"]))
        if not ok_p:
            bad += 1

    print("\nSR6 selftest: %d FAIL ｜ 阶段顺序=%s" % (bad, phases))
    return (0 if bad == 0 else 1), phases


def _carrier_fp():
    """取承载 dsh runtime 的进程指纹（pid + lstart）。★ 由门自己取，不靠调用方传。

    ★ v1.1.2：同时取 lstart —— 按第三方裁定，**pid 存在 ≠ 同一次启动**（pid 会被复用），
      只核存在性会把新进程误认为原载体。
    """
    try:
        out = subprocess.run(
            "ps -eo pid,lstart,command | grep 'dsh/lib/bin.js' | grep -v grep | head -1",
            shell=True, capture_output=True, text=True, timeout=10).stdout.strip()
        if not out:
            return {}
        parts = out.split()
        return {"pid": parts[0], "lstart": " ".join(parts[1:6])}
    except Exception:
        return {}


DEMO = [
    {"id": "D1", "kind": "number", "text": "本地板 audit 总行数（我今天报的是 46,111）",
     "cmd": "cat ~/dsh-collab/token-monitor/blackboard/audit*.jsonl 2>/dev/null | wc -l",
     "reported": 46111},
    {"id": "D2", "kind": "write", "text": "本轮未写盘",
     "scan": ["~/dsh-collab/audits", "~/dsh-collab/scripts"],
     "since": "2026-10-08T12:00:00"},
    {"id": "D3", "kind": "env", "text": "std 读数取自承载我的那个进程（本行演示 SR5 的正确形态：pid + lstart）",
     "expect": _carrier_fp()},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check")
    ap.add_argument("--fix-check", dest="fix_check",
                    help="SR6：校验一份「修复路径覆盖」声明（{base_ref, paths[], exemptions[]}）")
    ap.add_argument("--fix-repo", dest="fix_repo", help="SR6 的 git 仓库根（缺省=本门所在仓库根）")
    ap.add_argument("--fix-selftest", dest="fix_selftest", action="store_true",
                    help="SR6 自测（反例先行）")
    ap.add_argument("--json-out")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()

    if a.version:
        print(json.dumps({"tool": "self-report-gate", "version": __version__,
                          "rule": "R-SR 自述可证性",
                          "assertions": [i for i, _n, _k, _f, _s in ASSERTIONS]}))
        return 0
    if a.fix_selftest:
        rc6, _ph6 = fix_selftest()
        return rc6
    if a.fix_check:
        try:
            with open(os.path.expanduser(a.fix_check), encoding="utf-8") as f:
                fix = json.load(f)
        except Exception as e:
            print("无法读取 %s：%s" % (a.fix_check, e), file=sys.stderr)
            return 2
        _here = os.path.dirname(os.path.abspath(__file__))
        _repo = os.path.expanduser(a.fix_repo) if a.fix_repo else os.path.dirname(_here)
        rows6 = sr6_fix_coverage(fix, _repo, os.path.abspath(__file__))
        bad6 = report(rows6, "SR6 修复路径覆盖（%s）" % a.fix_check)
        if a.json_out:
            with open(os.path.expanduser(a.json_out), "w", encoding="utf-8") as f:
                json.dump({"version": __version__, "sr6": rows6}, f, ensure_ascii=False, indent=1)
        return 1 if bad6 else 0
    if a.lean4_check:
        return lean4_check()
    if a.selftest:
        rc, _phases = selftest()
        return rc

    if a.demo:
        claims = DEMO
        title = "自述门判定（--demo：今天真实事故）"
    elif a.check:
        try:
            with open(os.path.expanduser(a.check), encoding="utf-8") as f:
                d = json.load(f)
        except Exception as e:
            print("无法读取 %s：%s" % (a.check, e), file=sys.stderr)
            return 2
        claims = d.get("claims", d if isinstance(d, list) else [])
        title = "自述门判定（%s）" % a.check
    else:
        ap.print_help()
        return 2

    rows = judge(claims)
    bad = report(rows, title)
    if a.json_out:
        with open(os.path.expanduser(a.json_out), "w", encoding="utf-8") as f:
            json.dump({"version": __version__, "rows": rows}, f, ensure_ascii=False, indent=1)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
