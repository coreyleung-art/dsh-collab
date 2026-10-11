#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qk-structure-guard.py — continuity-index 里 Q-K 进度追踪器的**结构不变量**判据（**不改被核对象**；临时写面 = `guard/mutation-work/`）。

★ 立据（星桥 2026-10-10 结构性发现 + 我方实测）：
  **Q-K 进度追踪器住在 `open_questions[10]` 里** —— 也就是"一个有 17 条问题的数组的第 11 个元素"。
  后果：任何「按更全者合并 open_questions」的操作都可能把它**整块压掉**，而外观是"合并成功、两板相等"。
  实测两起：① 07:16 覆盖后 Q-K 丢了 k3/k4/k5 与 5 个 ★ 块（41,328→20,796 字符）；
            ② 星桥 07:27 那次差一点就这么干（自述）。
  ⇒ 需要一条**只读、可复跑**的判据：管住"这个条目**必须还在**、且**内容不得缩水**"。

★ 与 `tools/qk-tracker-drift-check.py` 的分工（不重复造轮子）：
  · 那个门查「台账 §1 ↔ 索引 Q-K」**两处是否一致**（漂移）；
  · 本门查「索引 Q-K 条目**自身结构是否完整**」（被压掉/被截断）。两者互补，缺一不可。

★ 迁移期**三种**形态（把"移出为独立键"的建议编进判据，而不是只写在对话里）：
  · **原位形态**：Q-K 必有完整进度子块（PROGRESS_KEYS）+ 指针元数据 + 5 个 ★ 块；
  · **迁移形态（留桩）**：Q-K 带 `moved_to` ⇒ 允许只剩指针，但**不得**再留进度子块或 ★ 块
    （那就是"两处各留一份"，正是 Q-K 目标里「两处不许漂」要禁的）；
  · **移出形态（条目整个消失）**：**默认红** —— 见下方 ★★。
    ⇒ 只有**根级显式声明** `_qk_moved_to: "<独立键>"` 时才判绿。

★★ 为什么「条目消失」默认红、且**不放宽**（2026-10-10 星桥问「有意还是放宽」的答复，写死在此）：
  条目整个消失时，**「有意移出」与「被压掉」在这张卡上完全同痕**（两者都只表现为"没有 Q-K"）——
  判据**无从区分**。若放宽，07:16 那种覆盖就会从红变绿。
  ⇒ 靠**声明**区分，而不是靠猜：真要有意移出，就在**根级**写 `_qk_moved_to`（根级字段不是
    "合并 open_questions"会顺手产生的东西 ⇒ 它不可能是误压的副产物）。
  ⇒ 这也与本线「未声明 ⇒ 不可判，非 PASS」同一条原则。

退出码：0 = 不变量全过 · 1 = 有违例 · 2 = 用法/环境错误
用法：
  python3 tools/qk-structure-guard.py                      # 直接读板（**不改被核对象**；临时写面 = `guard/mutation-work/`）
  python3 tools/qk-structure-guard.py --from <payload.json>  # 读已存快照（供变异检验/沙箱）
"""
import json
import os
import subprocess
import sys

DEFAULT_URL = "http://127.0.0.1:8792/data/registry/continuity-index"

# ★ 必存键分两类（**M5 反向对照逼出来的修正** —— 第一版把两者混为一谈，导致"迁移后留一个
#   status/tracker 指针"也被判红；而指针元数据本来就该留在 stub 里）：
#   · PROGRESS_KEYS：**进度子块** —— 原位态必须有；迁移态**必须不在**（否则两处各留一份）
#   · STUB_OK_KEYS：**指针元数据** —— 两种形态都允许（原位态亦须有）
PROGRESS_KEYS = ["k1", "k2", "k21", "k3", "k4", "k5", "k6", "k6_wiring"]
STUB_OK_KEYS = ["status", "tracker"]
# ★ 5 个 ★ 块（记录判据/事故/考古，属于最不可再生的内容）
REQUIRED_STAR_PREFIXES = ["★_两处漂移事故与判据", "★_目标逐条核对表", "★_禁令可复跑判据与三处更正",
                          "★_黑板payload保真度实测与回读判据", "★★_考古漏检：本机早有断言集工具链"]
MIN_STAR_CHARS = 200      # ★ 字符出现次数的地板（实测原位形态 236；被压后掉到 30 量级）
STUB_MARKER = "moved_to"


def load(url=None, path=None):
    if path:
        if not os.path.isfile(path):
            return None, f"快照文件不存在：{path}"
        with open(path, encoding="utf-8") as fh:
            return json.load(fh), None
    out = subprocess.run(["curl", "-s", "-m", "10", url or DEFAULT_URL], capture_output=True, text=True).stdout
    try:
        d = json.loads(out)
    except Exception as e:
        return None, f"读板失败或返回非 JSON：{e}"
    return d.get("value", d), None


def check(payload):
    bad, notes = [], []
    if not isinstance(payload, dict):
        return ["payload 不是对象"], []
    qs = payload.get("open_questions")
    if not isinstance(qs, list):
        return ["open_questions 不是数组（结构已变 ⇒ 本判据的输入面失效，不得算通过）"], []
    qk = [x for x in qs if isinstance(x, dict) and x.get("id") == "Q-K"]
    notes.append(f"open_questions 共 {len(qs)} 条 · 命中 Q-K {len(qk)} 个")
    if len(qk) == 0:
        # ★ 「完全移出」与「被压掉」在此同痕 ⇒ 只认**根级显式声明**（见文件头 ★★）
        decl = payload.get("_qk_moved_to")
        if isinstance(decl, str) and decl.strip() != "":
            notes.append(f"形态：**移出形态**（条目已整体移出；根级声明 _qk_moved_to={decl}）")
            notes.append("★ 本门**不核**该独立键的内容（不在本卡上）⇒ 完整性须由该键自己的判据负责")
        else:
            bad.append("Q-K 条目**不存在**，且**无根级 `_qk_moved_to` 声明** ⇒ 与「被压掉」同痕，不得算通过"
                       "（若确系有意移出，请在该卡**根级**写 `_qk_moved_to: \"<独立键>\"`；"
                       "若只想搬迁，也可保留条目并加 `moved_to` 走「迁移形态」）")
        return bad, notes
    if len(qk) > 1:
        bad.append(f"Q-K 条目应**恰好 1 个**，实得 {len(qk)} 个 ⇒ 进度追踪器位置异常（重复块）")
        return bad, notes
    q = qk[0]
    moved = isinstance(q.get(STUB_MARKER), str) and q[STUB_MARKER] != ""

    if moved:
        notes.append(f"形态：**迁移态**（{STUB_MARKER}={q[STUB_MARKER]}）")
        leaked = [k for k in PROGRESS_KEYS if k in q]
        if leaked:
            bad.append(f"迁移态下 Q-K 仍留进度子块 {leaked} ⇒ **两处各留一份**（正是「两处不许漂」要禁的）")
        for p in REQUIRED_STAR_PREFIXES:
            if any(k.startswith(p) for k in q):
                bad.append(f"迁移态下 Q-K 仍留 ★ 块（前缀 {p}）⇒ 同上，内容重复")
    else:
        notes.append("形态：**原位态**（进度追踪器住在 open_questions 里）")
        missing = [k for k in PROGRESS_KEYS + STUB_OK_KEYS if k not in q]
        if missing:
            bad.append(f"Q-K 缺必存键 {missing} ⇒ 条目被压掉/截断（07:16 事故的形态）")
        miss_star = [p for p in REQUIRED_STAR_PREFIXES if not any(k.startswith(p) for k in q)]
        if miss_star:
            bad.append(f"Q-K 缺 ★ 块 {miss_star} ⇒ 不可再生的记录内容丢失")
        star_chars = json.dumps(q, ensure_ascii=False).count("★")
        notes.append(f"Q-K 内 ★ 字符 {star_chars} 次（地板 {MIN_STAR_CHARS}）")
        if star_chars < MIN_STAR_CHARS:
            bad.append(f"Q-K 内 ★ 字符仅 {star_chars} 次 < 地板 {MIN_STAR_CHARS} ⇒ 疑似被截断/覆盖")
    return bad, notes


def main():
    path = None
    if "--from" in sys.argv:
        i = sys.argv.index("--from")
        if i + 1 >= len(sys.argv):
            print("用法错误：--from 后需要文件路径")
            return 2
        path = os.path.expanduser(sys.argv[i + 1])
    payload, err = load(path=path)
    if err:
        print(err)
        return 2
    bad, notes = check(payload)
    print("qk-structure-guard · Q-K 条目结构不变量（**不改被核对象**；临时写面 = `guard/mutation-work/`）")
    print(f"  来源：{path if path else DEFAULT_URL}")
    for n in notes:
        print(f"  · {n}")
    if bad:
        print("\n❌ 违例：")
        for b in bad:
            print("  " + b)
        return 1
    print("\n✅ 通过：Q-K 条目在原位 / 迁移（留桩）/ 移出（根级已声明）三种形态下均结构完整，"
          "无内容缩水、无两处重复")
    return 0


if __name__ == "__main__":
    sys.exit(main())
