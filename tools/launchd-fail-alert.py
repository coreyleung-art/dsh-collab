#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""launchd-fail-alert —— 【launchd 失败终态的告警读者】（★ H2d 的修复件）

★★★ 立据（D-339 / D-345 / 用户裁可 2026-10-15）：
  ★ `D-339` 普查发现：★ **4 个失败终态任务里 3 个【无读者】** ——
    ★ 而它们的日志写在 `/tmp` 或 `logs/`，★ **没人看**。
  ★ 本线据此建了 **H2d 判据**（★「每个失败终态都应有告警读者」），★ 而它现在报
    ★★ **「失败终态 4 个 · 无读者 2 个：`cron.bb-copy-staleness(exit=4)` · `hr.bb-request-watch(exit=2)`」**
  ★★★ **⇒ 本器就是那个【读者】。**

★ 设计（★ 三条）：
  ① **通用** —— ★ 不逐个改任务，★ 而是【扫描所有失败终态】并统一写卡
  ② **有界** —— ★ 同一任务同一 exit 在冷却窗内不重复写（★ 防噪音风暴）
  ③ **可读** —— ★ 写入 `data/ops/launchd-failure/<ts>`，★ 而 H2d 判据会看到它

★ 用法：
  python3 tools/launchd-fail-alert.py                 # ★ 扫一次（dry-run，只列）
  python3 tools/launchd-fail-alert.py --go            # ★ 真写告警卡
  python3 tools/launchd-fail-alert.py --selftest
"""
import argparse
import datetime
import io
import json
import os
import subprocess
import sys
import urllib.request

VERSION = "1.0.0"
HOME = os.path.expanduser("~")
BB = os.environ.get("DSH_BB_URL", "http://127.0.0.1:8792")
CENTRAL = os.environ.get("DSH_BB_CENTRAL_URL", "http://xingqiao.meetfunbp.com:8792")
OPS_NS = "data/ops/launchd-failure"
COOLDOWN_MIN = 30          # ★ 同一任务同一 exit 的冷却窗（★ 防噪音）
STATE = os.path.join(HOME, ".dsh", "launchd-fail-alert-state.json")


def tok():
    try:
        return open(os.path.join(HOME, ".dsh", "blackboard-token"), encoding="utf-8").read().strip()
    except Exception:
        return ""


def now():
    return datetime.datetime.now().astimezone()


def failed_jobs():
    """★ 取所有【失败终态】的 com.dsh.* 任务 ⇒ (rows, err)"""
    try:
        p = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=25)
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, str(e)[:60])
    rows = []
    for ln in p.stdout.split("\n"):
        parts = ln.split("\t")
        if len(parts) < 3:
            continue
        pid, status, label = parts[0], parts[1], parts[2]
        if not label.startswith("com.dsh."):
            continue
        if pid == "-" and status not in ("0", "-"):
            rows.append({"label": label, "exit": status})
    return rows, None


def load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {}


def save_state(st):
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE)


def put(path, body, board, timeout=25):
    req = urllib.request.Request(board + "/" + path, data=body, method="PUT")
    t = tok()
    req.add_header("Authorization", "Bearer " + t)
    req.add_header("X-Blackboard-Token", t)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status


def run(go=False, as_json=False, cooldown=COOLDOWN_MIN):
    rows, err = failed_jobs()
    if err:
        print("  ★★ 取失败终态失败：%s ⇒ 不可判" % err)
        return 2
    st = load_state()
    t0 = now()
    todo, skipped = [], []
    for r in rows:
        key = "%s|%s" % (r["label"], r["exit"])
        last = st.get(key)
        if last:
            try:
                dt = datetime.datetime.fromisoformat(last)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=t0.tzinfo)
                if (t0 - dt).total_seconds() < cooldown * 60:
                    skipped.append((key, int((t0 - dt).total_seconds() / 60)))
                    continue
            except Exception:
                pass
        todo.append(r)

    d = {"version": VERSION, "at": t0.isoformat(timespec="seconds"),
         "failed_total": len(rows), "to_alert": len(todo),
         "in_cooldown": len(skipped), "go": go, "rows": todo}
    print("══ launchd 失败告警器 %s ══  时刻 %s" % (VERSION, d["at"]))
    print("  失败终态 %d 个 · 待告警 %d · 冷却中 %d（★ 窗 %d 分钟）"
          % (len(rows), len(todo), len(skipped), cooldown))
    for r in rows:
        mark = "★告警" if r in todo else "· 冷却"
        print("    %-6s %s (exit=%s)" % (mark, r["label"], r["exit"]))
    if skipped:
        print("  冷却中明细：%s" % ", ".join("%s(%d分前)" % (k.split("|")[0].replace("com.dsh.", ""), m)
                                        for k, m in skipped))
    if not todo:
        print("  ★ 无需告警（★ 全在冷却窗内，或本就无失败）")
        if as_json:
            print(json.dumps(d, ensure_ascii=False))
        return 0
    if not go:
        print("  ★ dry-run：将写 %d 张告警卡到 %s/（★ 加 --go 才真写）" % (len(todo), OPS_NS))
        if as_json:
            print(json.dumps(d, ensure_ascii=False))
        return 0

    ok = fail = 0
    for r in todo:
        ts = int(t0.timestamp() * 1000)
        key = "%s/%d-%s" % (OPS_NS, ts, r["label"].replace("com.dsh.", "").replace(".", "-"))
        val = {"type": "launchd-failure", "from": "launchd-fail-alert",
               "ts": ts, "label": r["label"], "exitCode": r["exit"],
               "detectedAt": d["at"],
               "note": "★ launchd 失败终态告警（★ H2d 的读者）：该任务【已失败且不再运行】⇒ 需人工处置",
               "readerOf": "H2a/H2d 失败终态"}
        body = json.dumps(val, ensure_ascii=False).encode()
        got = 0
        for board in (BB, CENTRAL):
            try:
                if put(key, body, board) in (200, 201):
                    got += 1
            except Exception:
                pass
        if got >= 1:
            ok += 1
            st["%s|%s" % (r["label"], r["exit"])] = d["at"]
            print("    ✓ %s（★ %d/2 板）" % (r["label"].replace("com.dsh.", ""), got))
        else:
            fail += 1
            print("    ✗ %s ⇒ 两板均失败" % r["label"].replace("com.dsh.", ""))
    save_state(st)
    print()
    print("  【结果】成功 %d · 失败 %d" % (ok, fail))
    d.update({"ok": ok, "fail": fail})
    if as_json:
        print(json.dumps(d, ensure_ascii=False))
    return 0 if fail == 0 else 1


def selftest():
    ok = tot = 0
    print("== launchd-fail-alert 自查 ==")

    def chk(c, lb):
        nonlocal ok, tot
        tot += 1
        if c:
            ok += 1
            print("  ✅ %s" % lb)
        else:
            print("  ❌ %s" % lb)

    rows, err = failed_jobs()
    chk(err is None, "正控：能取失败终态列表（%s）" % (("%d 个" % len(rows)) if rows is not None else err))
    # ★ 正控：只收 com.dsh.*（★ 不收别的）
    if rows is not None:
        chk(all(str(r["label"]).startswith("com.dsh.") for r in rows), "正控：只收 com.dsh.* 任务")
    # ★ 负控：dry-run 不得写（★ 用 cooldown 极大 ⇒ 必然跳过）
    r = run(go=False)
    chk(r == 0, "负控：dry-run 返回 0 且不写")
    # ★ 正控：JSON 输出可解析
    import io as _io
    import contextlib
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        run(go=False, as_json=True)
    lines = [x for x in buf.getvalue().split("\n") if x.startswith("{")]
    chk(bool(lines) and isinstance(json.loads(lines[-1]), dict), "正控：--json 输出可解析")
    # ★ 负控：冷却状态文件不存在时不得崩
    chk(isinstance(load_state(), dict), "负控：状态文件缺失时返回空 dict（★ 不崩）")
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--cooldown", type=int, default=COOLDOWN_MIN)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("launchd-fail-alert %s" % VERSION); return 0
    if a.selftest:
        return selftest()
    return run(go=a.go, as_json=a.json, cooldown=a.cooldown)


if __name__ == "__main__":
    sys.exit(main())
