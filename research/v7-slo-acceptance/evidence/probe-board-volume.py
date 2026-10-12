#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S11 黑板数据体积 / snapshot / DELETE 次数 —— 现测口径

★ 黑板进程实参（现读，不写死）：
  ps -o command= -p $(pgrep -f rust-blackboard | head -1) | tr ' ' '\n' | grep -A1 data-dir
★ DELETE 判据取自 audit*.jsonl 的 action 字段，而不是 grep 文本里的 'DELETE'
  —— grep 'DELETE' 会命中 payload 内容（实测 1140 行命中，而 action 字段里 DELETE = 0）。

★ 2026-10-12 增补（v7 M4-① / W4 报「11/14 无负控」）：
  ★ 本件此前**从未被造坏验证过**。
  ★★ 新增 `--datadir`（★ 注入 data-dir，供负控用）· `--selftest`（★ 真调判据：3 正控 + 3 负控）。
  ★★★ **判据本体未改** —— 尤其【action 字段 vs grep 文本】这条口径原样保留。
"""
import glob
import json
import os
import subprocess
import collections
import sys
import argparse


def find_datadir():
    """★ 现读黑板进程的 --data-dir（★ 不写死路径）。

    ★ 不能用 `pgrep -f 'rust-blackboard .*--port'`：ps 里的进程名被截断成 `rust-blac`，
      但**完整路径**在 argv 里 ⇒ 用更宽的锚 'rust-blackboard-macos'。
    """
    pid = subprocess.run("pgrep -f 'rust-blackboard-macos' | head -1", shell=True,
                         capture_output=True, text=True).stdout.strip()
    if not pid:
        return None, None
    cmd = subprocess.run(["ps", "-o", "command=", "-p", pid],
                         capture_output=True, text=True).stdout
    parts = cmd.split()
    datadir = parts[parts.index("--data-dir") + 1] if "--data-dir" in parts else None
    return pid, datadir


def du(p):
    out = subprocess.run(["du", "-sk", p], capture_output=True, text=True).stdout
    return int(out.split()[0]) * 1024 if out.strip() else 0


def count_actions(audits):
    """★ 纯函数：从 audit 文件列表数 action 字段分布 + 总行数。

    ★★ 判据要点（★ 原样保留）：**只认 JSON 的 `action` 字段**，
      不认【行文本里出现 'DELETE'】—— 因为 payload 内容里也会有。
    """
    acts = collections.Counter()
    lines = 0
    for a in audits:
        try:
            fh = open(a, encoding="utf-8", errors="replace")
        except Exception:
            continue
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            lines += 1
            try:
                o = json.loads(ln)
            except Exception:
                continue
            acts[o.get("action") or o.get("op") or o.get("method")] += 1
        fh.close()
    return acts, lines


def evaluate(datadir):
    """★ 返回 (verdict, payload)。verdict ∈ {PASS, FAIL, UNDECIDABLE}"""
    if not datadir or not os.path.isdir(datadir):
        return "UNDECIDABLE", {"reason": "data-dir 不可读 ⇒ 体积/DELETE 均不可判", "datadir": datadir}
    snap = os.path.join(datadir, "snapshot.json")
    snap_mib = (os.path.getsize(snap) / 1048576.0) if os.path.exists(snap) else -1
    audits = sorted(glob.glob(os.path.join(datadir, "audit*.jsonl")))
    tot = sum(os.path.getsize(a) for a in audits)
    acts, lines = count_actions(audits)
    n_del = acts.get("DELETE", 0)
    return ("FAIL" if n_del == 0 else "PASS"), {
        "datadir": datadir,
        "dir_mib": round(du(datadir) / 1048576.0, 1),
        "snapshot_mib": round(snap_mib, 1),
        "audit_files": len(audits),
        "audit_mib": round(tot / 1048576.0, 1),
        "audit_lines": lines,
        "actions": dict(acts.most_common()),
        "delete_count": n_del,
        # ★ 口径：分子 = action 字段为 DELETE 的行数；分母 = 全部 audit 行数（本窗口内）
        "caliber": "action 字段口径（★ 非 grep 文本口径）",
    }


def report(payload):
    print("data-dir =", payload["datadir"])
    print()
    print("整目录体积 = %.1f MiB" % payload["dir_mib"])
    print("snapshot.json = %.1f MiB" % payload["snapshot_mib"])
    print("audit 文件数 = %d · 合计 %.1f MiB" % (payload["audit_files"], payload["audit_mib"]))
    print()
    print("audit 总行数 = %d" % payload["audit_lines"])
    print("action 字段分布 =", payload["actions"])
    print("★ DELETE 次数（action 口径）= %d" % payload["delete_count"])
    print()
    print("★ 判据  §12「有 GC/TTL」: %s（DELETE = %d）"
          % ("✓" if payload["delete_count"] else "❌", payload["delete_count"]))
    print("★ 口径声明：audit 只覆盖它自己轮转窗口内的行；更早的行已轮转掉 ⇒")
    print("  「DELETE=0」只能读成【本窗口内 0】，不能读成【历史上从未 DELETE】。")


def selftest():
    """★ 3 正控 + 3 负控 —— 全真调 count_actions()。"""
    ok = tot = 0
    import tempfile
    import shutil

    def mk(d, name, rows):
        p = os.path.join(d, name)
        with open(p, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        return p

    # ★ 正控①：有真 DELETE 的 action ⇒ 必须数到
    tot += 1
    d1 = tempfile.mkdtemp(prefix="bv-del-")
    mk(d1, "audit-a.jsonl", [{"action": "PUT"}, {"action": "DELETE"}, {"action": "DELETE"}])
    acts, lines = count_actions(sorted(glob.glob(os.path.join(d1, "audit*.jsonl"))))
    if acts.get("DELETE") == 2 and lines == 3:
        ok += 1
        print("  ✅ 正控①：真 DELETE 行 ⇒ 数到 2（★ 行数 3）")
    else:
        print("  ❌ 正控①：DELETE 未数到（%s）" % dict(acts))
    # ★★ 负控①（★ 本条是本探针的核心判据）：DELETE 只出现在【payload 里】⇒ 必须数到 0
    tot += 1
    d2 = tempfile.mkdtemp(prefix="bv-payload-")
    mk(d2, "audit-a.jsonl", [{"action": "PUT", "payload": {"cmd": "DELETE FROM keys"}},
                             {"action": "PUT", "note": "grep 'DELETE' would hit this"}])
    acts2, lines2 = count_actions(sorted(glob.glob(os.path.join(d2, "audit*.jsonl"))))
    if acts2.get("DELETE", 0) == 0 and lines2 == 2:
        ok += 1
        print("  ✅ 负控①：DELETE 只在 payload 里 ⇒ 数到 0（★ 核心判据：非 grep 文本口径）")
    else:
        print("  ❌ 负控①：payload 里的 DELETE 被计入（%s）" % dict(acts2))
    # ★ 正控②：`op` / `method` 别名也须认（★ 防只认 action）
    tot += 1
    d3 = tempfile.mkdtemp(prefix="bv-alias-")
    mk(d3, "audit-b.jsonl", [{"op": "DELETE"}, {"method": "DELETE"}])
    acts3, _ = count_actions(sorted(glob.glob(os.path.join(d3, "audit*.jsonl"))))
    if acts3.get("DELETE") == 2:
        ok += 1
        print("  ✅ 正控②：`op`/`method` 别名 ⇒ 也认（2 条）")
    else:
        print("  ❌ 正控②：别名未认（%s）" % dict(acts3))
    # ★ 负控②：非 JSON 行不得崩，且计入行数
    tot += 1
    d4 = tempfile.mkdtemp(prefix="bv-bad-")
    with open(os.path.join(d4, "audit-c.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("not json\n" + json.dumps({"action": "DELETE"}) + "\n")
    acts4, lines4 = count_actions(sorted(glob.glob(os.path.join(d4, "audit*.jsonl"))))
    if lines4 == 2 and acts4.get("DELETE") == 1:
        ok += 1
        print("  ✅ 负控②：非 JSON 行 ⇒ 不崩、计入行数、不影响 action 计数")
    else:
        print("  ❌ 负控②：非 JSON 行处理有误（lines=%s acts=%s）" % (lines4, dict(acts4)))
    # ★ 负控③：无 audit 文件 ⇒ 空分布 + 0 行（★ 分母 0 不报通过）
    tot += 1
    d5 = tempfile.mkdtemp(prefix="bv-none-")
    acts5, lines5 = count_actions(sorted(glob.glob(os.path.join(d5, "audit*.jsonl"))))
    if not acts5 and lines5 == 0:
        ok += 1
        print("  ✅ 负控③：无 audit 文件 ⇒ 空分布 · 0 行（★ 分母 0 不报通过）")
    else:
        print("  ❌ 负控③：无文件竟有结果（%s）" % dict(acts5))
    # ★ 正控③：目录不存在 ⇒ evaluate 报 UNDECIDABLE
    tot += 1
    v6, _ = evaluate("/tmp/__no_such_datadir__")
    if v6 == "UNDECIDABLE":
        ok += 1
        print("  ✅ 正控③：data-dir 不可读 ⇒ UNDECIDABLE（★ 不崩、不冒充通过）")
    else:
        print("  ❌ 正控③：不可读目录判 %s" % v6)
    for d in (d1, d2, d3, d4, d5):
        shutil.rmtree(d, ignore_errors=True)
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datadir", default=None, help="★ 注入 data-dir（供负控用）；缺省现读进程")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("probe-board-volume 1.1.0")
        return 0
    if a.selftest:
        return selftest()
    if a.datadir:
        pid, dd = None, os.path.expanduser(a.datadir)
    else:
        pid, dd = find_datadir()
    print("黑板 pid =", pid or "（未找到进程）")
    verdict, payload = evaluate(dd)
    if a.json:
        print(json.dumps({**payload, "verdict": verdict}, ensure_ascii=False, indent=1))
        return 0 if verdict == "PASS" else (3 if verdict == "UNDECIDABLE" else 1)
    if verdict == "UNDECIDABLE":
        print("data-dir =", dd or "（不可判）")
        print("★ data-dir 不可读 ⇒ 体积/DELETE 均【不可判】")
        return 3
    report(payload)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
