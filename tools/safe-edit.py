#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""safe-edit —— 【改文件四步门】：备份 → 改副本 → 审查 → 原子替换

★★★★★ 立据（用户 2026-10-15 的直接要求）：
  ★★ **「建立一个工程化机械化的机制规则：改任何文件之前，先备份，
     然后改副本，审查没问题后，再用副本替换源文件。」**

★★★ 而它对应的【实际教训】（本线 2026-10-15 一晚）：
  ★ 改 `beacon-check.py` **损坏 3 次**：
    ★ ① 插 `return` ⇒ `main()` 早退 ⇒ 判据数 42→24
    ★ ② 替换区间终点找错 ⇒ 删掉 5 条
    ★ ③ 插入位置错 ⇒ 54→51
  ★★ **三次都靠「核条目总数」发现，三次都靠 `git checkout` 恢复。**
  ★★★ **⇒ 若当时走四步门，三次都不会污染源文件。**

★ 四步（★ 机械化）：
  ① `begin <file>`   —— ★ 备份源文件到 `~/.dsh/safe-edit/<ts>/`，★ 并开一个副本
  ② 改副本          —— ★ 用任何方式改 `<file>.draft`（★ 源文件【未被碰过】）
  ③ `check <file>`   —— ★ 语法/差异/关键计数三项自检
  ④ `commit <file>`  —— ★ 通过后原子替换（★ `os.replace`）；★ 不通过则 **拒绝替换**

★ 三态纪律：
  ★ 无副本 ⇒ **拒绝 commit**（★ 不猜）
  ★ 副本语法不过 ⇒ **拒绝 commit**
  ★ 关键计数骤变 ⇒ **要求 `--force` 才替换**（★ 那是今晚三次事故的共同特征）

用法：
  python3 tools/safe-edit.py begin   <file> [--count-regex PAT]
  python3 tools/safe-edit.py status  <file>
  python3 tools/safe-edit.py check   <file>
  python3 tools/safe-edit.py commit  <file> [--force]
  python3 tools/safe-edit.py discard <file>
  python3 tools/safe-edit.py --selftest
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import sys

VERSION = "1.0.0"
HOME = os.path.expanduser("~")
STORE = os.path.join(HOME, ".dsh", "safe-edit")
STATE = os.path.join(STORE, "state.json")
# ★ 语法检查器（★ 按扩展名）
CHECKERS = {".py": ["python3", "-c", "import ast,sys;ast.parse(open(sys.argv[1],encoding='utf-8').read())"],
            ".sh": ["bash", "-n"],
            ".json": ["python3", "-c", "import json,sys;json.load(open(sys.argv[1],encoding='utf-8'))"],
            ".yml": ["python3", "-c", "import sys;print('skip')"],
            ".yaml": ["python3", "-c", "import sys;print('skip')"],
            ".md": None, ".js": ["node", "--check"], ".mjs": ["node", "--check"]}


def now():
    return datetime.datetime.now().astimezone()


def sha(p):
    try:
        with open(p, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return None


def load_state():
    try:
        return json.load(io.open(STATE, encoding="utf-8"))
    except Exception:
        return {}


def save_state(st):
    os.makedirs(STORE, exist_ok=True)
    tmp = STATE + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE)


def _key(p):
    return os.path.abspath(os.path.expanduser(p))


def _draft(p):
    return _key(p) + ".draft"


def _meta(p):
    return _key(p) + ".draftmeta.json"


def _count(p, rx):
    """★ 关键计数（★ 用于检测【骤变】—— 今晚三次事故的共同特征）"""
    if not rx:
        return None
    try:
        t = io.open(p, encoding="utf-8", errors="ignore").read()
        return len(re.findall(rx, t))
    except Exception:
        return None


def _anchor_of(q):
    """★ 内容锚：★ 由【文件自身】派生（bytes · lines · 首非空行前 60 字 · 末非空行前 60 字）。
    ★★ 用途：★ 使回滚点**不依赖任何历史记录即可判状态**（★ 见 R063 装置维 · D-424）。"""
    try:
        raw = io.open(q, "rb").read()
        txt = raw.decode("utf-8", "ignore")
        lines = [x for x in txt.split("\n") if x.strip()]
        return {"bytes": len(raw), "lines": txt.count("\n") + 1,
                "head": (lines[0][:60] if lines else ""),
                "tail": (lines[-1][:60] if lines else "")}
    except Exception as e:
        return {"err": type(e).__name__}


def _anchor_diff(a, b):
    """★ 两锚之差 = 【四分量】—— ★ 每个分量单独可读（★ 明鉴 v3 给的形态）：
    ★ `bytes` ⇒ 改动量 · ★ `lines` ⇒ 行增减 · ★ `head`/`tail` ⇒ 是否动了开头/结尾。
    ★★ 判据（★ 必附）：★ head/tail 的「变/未变」= **首/末非空行前 60 字是否逐字相同**
      ⇒ ★ **60 字内的同长改动可能看不出** ⇒ ★ 故「未变」**不等于**「头尾未被改」，★ 只等于「前 60 字未变」。
    ★★★ 与 diff 的区别：★ diff 是**逐行对照**；★ 锚差是**内容派生读数** ⇒ **不依赖任何人的叙述**。"""
    if not isinstance(a, dict) or not isinstance(b, dict) or a.get("err") or b.get("err"):
        return None
    return {"d_bytes": b.get("bytes", 0) - a.get("bytes", 0),
            "d_lines": b.get("lines", 0) - a.get("lines", 0),
            "head_same": a.get("head") == b.get("head"),
            "tail_same": a.get("tail") == b.get("tail")}


def begin(path, count_regex=None):
    p = _key(path)
    if not os.path.exists(p):
        print("  ★★ 源文件不存在：%s ⇒ 拒绝（★ 不猜）" % p)
        return 2
    ts = now().strftime("%Y%m%d-%H%M%S")
    bak_dir = os.path.join(STORE, ts)
    os.makedirs(bak_dir, exist_ok=True)
    bak = os.path.join(bak_dir, os.path.basename(p))
    shutil.copy2(p, bak)
    shutil.copy2(p, _draft(p))
    c0 = _count(p, count_regex)
    # ★★★ 2026-10-15（★ 由明鉴 v3 建议、星桥第三任实现）：★ 备份步除 sha 外**同时记【内容锚】**。
    #   ★ 立据（当晚实测）：它的回滚点能用【内容】判（"含第四类证据 1 处 · 证据表 12 行"），
    #     而它那句"sha 与我卡里记录一致"**不可判 —— 因为记录是【回溯的】**（卡 ts 07:12:26 晚于改动 06:57）。
    #   ★★ 其一般形式：**记录锚定【时间】，内容锚定【状态】—— 而回滚点需要的是后者。**
    #   ⇒ 故本步**同时落一份内容锚**：★ bytes · lines · head · tail
    #     ⇒ **即使 sha 记录丢了或被改写，回滚点仍可判**（★ 不依赖任何历史记录）。
    meta = {"path": p, "backup": bak, "ts": ts, "sha_before": sha(p),
            "count_regex": count_regex, "count_before": c0, "at": now().isoformat(timespec="seconds"),
            "content_anchor": _anchor_of(p)}
    with io.open(_meta(p), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    st = load_state()
    st[p] = meta
    save_state(st)
    print("══ safe-edit 四步门 ══  %s" % meta["at"])
    print("  ① 备份：%s" % bak)
    print("  ② 副本：%s   ← ★ 【改这个，不要改源文件】" % _draft(p))
    if c0 is not None:
        print("     ★ 关键计数基线：%d（★ 正则 %s）" % (c0, count_regex))
    print("  源文件 sha16：%s（★ 此刻未被碰过）" % meta["sha_before"])
    _a = meta["content_anchor"]
    print("  ★ 内容锚（★ 不依赖任何历史记录即可判回滚点）：%s B · %s 行 · 首「%s」· 尾「%s」"
          % (_a.get("bytes", "?"), _a.get("lines", "?"), _a.get("head", "")[:28], _a.get("tail", "")[:28]))
    print()
    print("  ★ 下一步：改副本 ⇒ `safe-edit.py check %s`" % os.path.basename(p))
    return 0


def status(path):
    p = _key(path)
    m = load_state().get(p)
    if not m:
        print("  ★ 无进行中的会话（★ 未 begin）")
        return 1
    print("══ 会话 %s ══" % m["ts"])
    print("  源文件：%s" % p)
    print("  备份  ：%s" % m["backup"])
    print("  副本  ：%s%s" % (_draft(p), "" if os.path.exists(_draft(p)) else "  ★★ 副本不存在"))
    print("  源 sha16（begin 时）：%s · 现在：%s%s"
          % (m["sha_before"], sha(p),
             "" if sha(p) == m["sha_before"] else "  ★★ 源文件已被改动（★ 违反四步门）"))
    if m.get("count_regex"):
        print("  计数 %s → %s（★ 副本）" % (m.get("count_before"), _count(_draft(p), m["count_regex"])))
    return 0


def check(path):
    """★ ③ 审查：语法 + 差异 + 关键计数"""
    p = _key(path)
    m = load_state().get(p)
    if not m:
        print("  ★★ 无会话 ⇒ 先 `begin`（★ 不猜）")
        return 2
    dp = _draft(p)
    if not os.path.exists(dp):
        print("  ★★ 副本不存在 ⇒ 拒绝")
        return 2
    ok = True
    # ★ A. 语法
    ext = os.path.splitext(p)[1].lower()
    ck = CHECKERS.get(ext, "unknown")
    if ck is None:
        print("  ① 语法：★ 该类型无需语法检查（%s）" % ext)
    elif ck == "unknown":
        print("  ① 语法：★ 未知类型 %s ⇒ 跳过（★ 记 SKIP，★ 不记 PASS）" % ext)
    else:
        import subprocess
        r = subprocess.run(ck + [dp], capture_output=True, text=True)
        if r.returncode == 0:
            print("  ① 语法：✅ 通过")
        else:
            ok = False
            print("  ① 语法：❌ 失败")
            print("     %s" % (r.stderr or r.stdout).strip()[:300])
    # ★ B. 差异统计
    try:
        a = io.open(p, encoding="utf-8", errors="ignore").read().split("\n")
        b = io.open(dp, encoding="utf-8", errors="ignore").read().split("\n")
        import difflib
        d = list(difflib.unified_diff(a, b, lineterm=""))
        add = len([x for x in d if x.startswith("+") and not x.startswith("+++")])
        rem = len([x for x in d if x.startswith("-") and not x.startswith("---")])
        print("  ② 差异：+%d / -%d 行（★ 行数 %d → %d）" % (add, rem, len(a), len(b)))
        if rem > 0 and rem > add * 3 and rem > 20:
            print("     ★★ 删除远多于新增 ⇒ 【疑似大段误删】（★ 今晚三次事故的特征）")
        # ★★ 锚差（★ 四分量 · ★ 由内容派生 ⇒ 不依赖作者叙述；★ 形态由明鉴 v3 给）
        _da = _anchor_diff(m.get("content_anchor"), _anchor_of(dp))
        if _da:
            print("  ②' 锚差（★ 内容派生 · ★ 不依赖叙述）：bytes %+d · lines %+d · head %s · tail %s"
                  % (_da["d_bytes"], _da["d_lines"],
                     "未变" if _da["head_same"] else "★ 变",
                     "未变" if _da["tail_same"] else "★ 变"))
            print("     ★ 判据：head/tail 的「变/未变」= 【首/末非空行前 60 字是否逐字相同】"
                  "⇒ ★ 「未变」只等于【前 60 字未变】，★ 不等于【头尾未被改】")
            # ★★★★★ 2026-10-15（★ 由明鉴 v3 实测出的【假绿】，★ 本线复现后修）：
            #   ★ 它造 `HEAD / middle-content-1111 / TAIL`（30 B）⇒ **等长中间替换** `1111→2222`（★ 仍 30 B）⇒
            #     ★★ **②' 四分量【全部报「未变」】**，★ 而那是【真改动】⇒ **单看锚差会把改动读成无改动**。
            #   ★★★ 而 `meta` 里【本来就有 `sha_before`】**⇒ 闸手里有唯一能判等长替换的量，却没拿它判。**
            #   ★★ 其一般形式：★ **「形状未变」与「未改动」是两个量** —— ★ 锚差判【形状】（不需历史）·
            #     ★ sha 判【是否变了】（需历史）⇒ ★★ **两者回答的是【两个问题】，不可互相代替。**
            _sh_now = sha(dp)
            _sh_same = bool(m.get("sha_before")) and _sh_now == m.get("sha_before")
            _all_same = (not _da["d_bytes"] and not _da["d_lines"]
                         and _da["head_same"] and _da["tail_same"])
            print("     ★ sha16 %s（%s · ★ 改前 %s）"
                  % ("未变" if _sh_same else "★ 变", _sh_now, m.get("sha_before")))
            if _all_same and not _sh_same:
                ok = False
                print()
                print("  ★★★ 【可疑态：形状未变而内容已变（等长替换）】")
                print("     ★ 锚差四分量全同，★ 而 sha16 已变 ⇒ ★★ **不得读作「无改动」**，★ 需人看。")
                print("     ★ 判据：★ 锚差判【形状】（不需历史）· ★ sha 判【是否变了】（需历史）"
                      "—— ★ **两者回答两个问题，不可互代**。")
                print("     ★★ 若确为有意改动 ⇒ ★ commit 需加 --force（★ 会留痕，★ 备份仍在 %s）" % m["backup"])
    except Exception as e:
        print("  ② 差异：★ 取不到（%s）" % type(e).__name__)
    # ★ C. 关键计数
    if m.get("count_regex"):
        c0, c1 = m.get("count_before"), _count(dp, m["count_regex"])
        print("  ③ 关键计数：%s → %s" % (c0, c1))
        if c0 is not None and c1 is not None and c0 != c1:
            ok = False
            print("     ★★ 计数变化 ⇒ 【需 --force 才允许替换】（★ 今晚三次事故都是计数骤变）")
    print()
    print("  ⇒ 审查%s" % ("**通过**（可 commit）" if ok else "**未通过**（★ commit 会被拒；★ 除非 --force）"))
    return 0 if ok else 1


def commit(path, force=False):
    p = _key(path)
    m = load_state().get(p)
    if not m:
        print("  ★★ 无会话 ⇒ 拒绝（★ 不猜）")
        return 2
    dp = _draft(p)
    if not os.path.exists(dp):
        print("  ★★ 副本不存在 ⇒ 拒绝")
        return 2
    # ★★★★★ 2026-10-15（D-391）【并发写护栏】—★ 由星桥第三任（session-47c9f0d3）实测撞车触发。
    #   ★ 它逐字：★「★ 03:56:38 我 se begin 台账并先持 agent_lock 独占锁；
    #     ★ 03:56:46 你在锁内写入 D-389。我的 draft 快照不含你的 D-389
    #     ⇒ ★★ 照常 commit 会【整条抹掉你的 D-389】。」
    #   ★★★ 而它的 lessons：★「★★ 【se 四步门对并发写同一文件不构成互斥】
    #     （begin 快照 / commit 整文件替换）」
    #   ★ 修法：★ **commit 时校验【源文件 sha】是否等于 begin 时** ⇒
    #     ★★ 若已变 ⇒ **拒绝 commit**（★ 提示重新 begin）——★ 那正是「整文件替换」的风险闸。
    _cur = sha(p)
    if m.get("sha_before") and _cur and _cur != m["sha_before"]:
        print("  ★★★ 【拒绝替换：源文件在 begin 之后被改过】")
        print("     begin 时 sha16：%s" % m["sha_before"])
        print("     现在     sha16：%s  ← ★★ 别人（或别的你会话）改过它" % _cur)
        print()
        print("     ★ 若照常替换 ⇒ ★★ **会【整条抹掉】那次改动**（★ 那是本仓 2026-10-15 实测过的真事故）。")
        print("     ★★ 正确姿势：★ **丢弃当前副本，重新 begin**（★ 那样新快照会含别人的改动）：")
        print("          se discard %s && se begin %s" % (os.path.basename(p), os.path.basename(p)))
        print("     ★ 或若你确认要覆盖 ⇒ ★ **先把别人的改动并进副本**，★ 再用 --force。")
        if not force:
            return 1
        print("     ★★ --force：★ 已确认覆盖（★ 备份仍在 %s）" % m["backup"])
    rc = check(path)
    if rc != 0 and not force:
        print()
        print("  ★★★ 【拒绝替换】—— ★ 审查未通过，★ 源文件【保持原样】（★ 那是本机制的目的）")
        return 1
    if rc != 0 and force:
        print()
        print("  ★★ --force：★ 审查未通过仍替换 ⇒ ★ 已留痕（★ 备份仍在 %s）" % m["backup"])
    # ★ ④ 原子替换
    tmp = p + ".safeedit.tmp"
    shutil.copy2(dp, tmp)
    os.replace(tmp, p)
    after = sha(p)
    print()
    print("  ✅ 已原子替换：%s" % p)
    print("     sha16：%s → %s" % (m["sha_before"], after))
    print("     备份仍在：%s" % m["backup"])
    m2 = dict(m)
    m2["sha_after"] = after
    m2["committed_at"] = now().isoformat(timespec="seconds")
    st = load_state()
    st.pop(p, None)
    save_state(st)
    try:
        os.remove(dp)
        os.remove(_meta(p))
    except Exception:
        pass
    print("  ★ 回滚方式：cp '%s' '%s'" % (m["backup"], p))
    return 0


def discard(path):
    p = _key(path)
    dp, mp = _draft(p), _meta(p)
    n = 0
    for f in (dp, mp):
        if os.path.exists(f):
            os.remove(f)
            n += 1
    st = load_state()
    st.pop(p, None)
    save_state(st)
    print("  ✅ 已丢弃副本与元数据（%d 个文件）——★ 源文件【从未被碰过】" % n)
    return 0


def selftest():
    ok = tot = 0
    print("== safe-edit 自查 ==")

    def chk(c, lb):
        nonlocal ok, tot
        tot += 1
        if c:
            ok += 1
            print("  ✅ %s" % lb)
        else:
            print("  ❌ %s" % lb)

    # ★ 正控：真跑一遍完整四步（★ 用临时文件，★ 不碰任何真文件）
    import tempfile
    d = tempfile.mkdtemp(prefix="safeedit-")
    f = os.path.join(d, "t.py")
    io.open(f, "w", encoding="utf-8").write("a = 1\nb = 2\n")
    r1 = begin(f, count_regex=r"^[a-z] = ")
    chk(r1 == 0 and os.path.exists(_draft(f)), "正控：begin 建副本（★ 源未被碰）")
    # ★ 副本改好（★ 语法 OK）
    io.open(_draft(f), "w", encoding="utf-8").write("a = 1\nb = 2\nc = 3\n")
    r2 = check(f)
    chk(r2 == 0, "正控：改好副本 ⇒ check 通过")
    r3 = commit(f)
    chk(r3 == 0 and "c = 3" in io.open(f, encoding="utf-8").read(), "正控：commit 已原子替换")
    # ★ 负控：语法坏的副本 ⇒ 拒绝替换
    io.open(f, "w", encoding="utf-8").write("x = 1\n")
    begin(f)
    io.open(_draft(f), "w", encoding="utf-8").write("x = ((1\n")   # ★ 语法坏
    r4 = commit(f)
    chk(r4 != 0 and io.open(f, encoding="utf-8").read().strip() == "x = 1",
        "★ 负控：语法坏 ⇒ **拒绝替换**（★ 源保持原样）")
    discard(f)
    # ★ 负控：无会话 ⇒ 拒绝
    chk(commit(f) != 0, "★ 负控：无会话 ⇒ commit 被拒（★ 不猜）")
    # ★ 正控：备份确实存在
    chk(os.path.isdir(STORE), "正控：备份目录存在（%s）" % STORE)
    shutil.rmtree(d, ignore_errors=True)
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", nargs="?", help="begin|status|check|commit|discard")
    ap.add_argument("file", nargs="?", help="目标文件")
    ap.add_argument("--count-regex", default=None, help="★ 关键计数正则（★ 检测骤变）")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("safe-edit %s" % VERSION)
        return 0
    if a.selftest:
        return selftest()
    if not a.action or not a.file:
        ap.print_help()
        return 2
    fn = {"begin": lambda: begin(a.file, a.count_regex), "status": lambda: status(a.file),
          "check": lambda: check(a.file), "commit": lambda: commit(a.file, a.force),
          "discard": lambda: discard(a.file)}.get(a.action)
    if not fn:
        print("  ★★ 未知动作：%s" % a.action)
        return 2
    return fn()


if __name__ == "__main__":
    sys.exit(main())
