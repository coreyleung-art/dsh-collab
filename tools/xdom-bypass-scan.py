#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xdom-bypass-scan —— 【反向判据：找出没走门的跨机操作】

★★★ 立据（明鉴 2026-10-15 的建议 · 本线采纳）：
  ★ 本线原问它：「裸 ssh 在门外，要不要做环境级 wrapper（如 `alias ssh`）？」
  ★★ 它答（逐字）：「★ **我倾向不做环境级 wrapper**，理由：
    ① 环境级失效是**静默的**（★ 无读数）；
    ② 它**确实是错误发生的地方**，但也是**最难验证它还在生效的地方**
    ⇒ ★★ 建议加**反向判据**：**扫日志找出【没经过门】的跨机操作**
       —— ★ **后者才是可核验的**。」
  ★★★ **⇒ 本器就是那个反向判据。**

★ 它问的问题（★ 本器要答）：
  ★ **「过去 N 小时里，有没有【跨机写操作】没走 `xdom-op.sh`？」**

★ 三条设计：
  ① **正向计数**：★ 走门的有几次（★ 从 `logs/xdom-op.log` 读）
  ② **反向找漏**：★ 从**别的来源**找跨机操作痕迹，★ 与走门记录对账
  ③ **三态**：★ 找不全 ⇒ `UNDECIDABLE`（★ 空 ≠ 无）

用法：
  python3 tools/xdom-bypass-scan.py                    # ★ 默认看 24 小时
  python3 tools/xdom-bypass-scan.py --hours 168        # ★ 7 天
  python3 tools/xdom-bypass-scan.py --selftest
"""
import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys

VERSION = "1.0.0"
HOME = os.path.expanduser("~")
ROOT = os.path.join(HOME, "dsh-collab")
GATE_LOG = os.path.join(ROOT, "logs", "xdom-op.log")
SSH_GATE_LOG = os.path.join(ROOT, "logs", "ssh-gate.log")

# ★ 跨机操作的可能痕迹来源（★ 每源都是【可读的本地文件】）
SOURCES = [
    ("shell-history", os.path.join(HOME, ".zsh_history")),
    ("zsh-sessions", os.path.join(HOME, ".zsh_sessions")),
    ("gate-log", GATE_LOG),
    ("ssh-gate-log", SSH_GATE_LOG),
]


def now():
    return datetime.datetime.now().astimezone()


def _read(p, limit=4 * 1024 * 1024):
    try:
        with open(p, "rb") as f:
            return f.read()[-limit:].decode("utf-8", "replace")
    except Exception:
        return None


def scan_history(hours):
    """★从 shell history 里找【跨机 ssh 调用】⇒ (rows, None, None) 或 (None, None, 原因)"""
    since = now() - datetime.timedelta(hours=hours)
    p = os.path.join(HOME, ".zsh_history")
    txt = _read(p)
    if txt is None:
        return None, None, "shell history 读不到：%s" % p
    # ★★★ 2026-10-15（D-366）【写动词正则】—★ 前带分隔符含引号（★ 因 `ssh h '"'"'sudo rm'"'"'` 里引号不是 [:space:] 类）。
    RX_SSH = re.compile(r"(?:^|[;&|\s])ssh\s")
    RX_LOCAL = re.compile(r"ssh\s+(?:-\w+\s+)*\S*@?127\.0\.0\.1")
    RX_TOOLS = re.compile(r"ssh-keygen|ssh-add|ssh-copy-id|ssh-agent")
    RX_WRITE = re.compile('\'(?:^|[;&|\\s\'\\"])(sudo|systemctl|rm|mv|cp|tee|dd|chmod|chown|apt|apt-get|yum|docker|crontab|reboot|shutdown|kill|pkill)\\s\'')
    RX_REDIR = re.compile(r"(^|[^0-9&])>{1,2}[^&]")
    rows = []
    for ln in txt.split("\n"):
        m = re.match(r"^: (\d+):\d+;(.*)$", ln)
        if m:
            ts, cmd = int(m.group(1)), m.group(2)
        else:
            ts, cmd = None, ln
        if ts is not None:
            try:
                if datetime.datetime.fromtimestamp(ts).astimezone() < since:
                    continue
            except Exception:
                pass
        if not RX_SSH.search(cmd):
            continue
        if RX_LOCAL.search(cmd) or RX_TOOLS.search(cmd):
            continue
        rows.append({"cmd": cmd[:160], "ts": ts,
                     "via_gate": "xdom-op.sh" in cmd,
                     "is_write": bool(RX_WRITE.search(cmd) or RX_REDIR.search(cmd))})
    return rows, None, None


def scan_gate_log(hours):
    """★ 从门日志读【确实走了门】的次数"""
    since = now() - datetime.timedelta(hours=hours)
    txt = _read(GATE_LOG)
    if txt is None:
        return None, "门日志读不到（★ 那意味着【门从未被用过】或日志被清）"
    n = 0
    for ln in txt.split("\n"):
        if not ln.strip():
            continue
        m = re.match(r"^(\d{4}-\d{2}-\d{2}T[\d:+\-]+)", ln)
        if m:
            try:
                t = datetime.datetime.fromisoformat(m.group(1))
                if t.tzinfo is None:
                    t = t.replace(tzinfo=now().tzinfo)
                if t < since:
                    continue
            except Exception:
                pass
        if re.search(r"\b(PASS|DENY-RED|DENY-UNKNOWN|EXEC)\b", ln):
            n += 1
    return n, None


def run(hours=24, as_json=False):
    d = {"version": VERSION, "at": now().isoformat(timespec="seconds"), "hours": hours}
    rows, _, err = scan_history(hours)
    n_gate, gerr = scan_gate_log(hours)

    print("══ 跨机操作【旁路扫描】%s ══  时刻 %s" % (VERSION, d["at"]))
    print("  窗口 = 最近 %d 小时" % hours)
    print()
    print("  【正向】走门的操作（★ 从 `logs/xdom-op.log`）")
    if gerr:
        print("    ★★ %s" % gerr)
        d["gate_count"] = None
    else:
        print("    ✅ %d 次（★ PASS/DENY/EXEC 之和）" % n_gate)
        d["gate_count"] = n_gate

    print()
    print("  【反向】shell history 里的 ssh（★ 与走门记录对账）")
    if err:
        print("    ❓ %s ⇒ **不可判**（★ 空 ≠ 无）" % err)
        d["verdict"] = "UNDECIDABLE"
        d["reason"] = err
        if as_json:
            print(json.dumps(d, ensure_ascii=False))
        return 2

    writes = [r for r in rows if r["is_write"]]
    bypass = [r for r in writes if not r["via_gate"]]
    via = [r for r in writes if r["via_gate"]]
    print("    ssh 总调用 %d · **写操作 %d**（★ 走门 %d · **未走门 %d**）"
          % (len(rows), len(writes), len(via), len(bypass)))
    for r in bypass[:8]:
        print("      ✗ %s" % r["cmd"][:110])
    if len(bypass) > 8:
        print("      … 另有 %d 条" % (len(bypass) - 8))

    d.update({"ssh_total": len(rows), "ssh_writes": len(writes),
              "via_gate": len(via), "bypass": len(bypass),
              "bypass_sample": [r["cmd"] for r in bypass[:10]]})
    print()
    if not rows:
        d["verdict"] = "UNDECIDABLE"
        print("  【判定】❓ **不可判** —— shell history 里 **0 条 ssh**")
        print("        ★ 那【不是「没有旁路」】，★ 而是【本器看不到】（★ 空 ≠ 无）")
        print("        ★ 诚实边界：★ 若历史上限很小或 history 被清，本器就看不到。")
    elif bypass:
        d["verdict"] = "BYPASS_FOUND"
        print("  【判定】❌ **发现 %d 条【未走门】的跨机写操作**" % len(bypass))
        print("        ★ 建议：★ 那正是【可核验的】证据 —— ★ 比环境级 wrapper 更可核。")
    else:
        d["verdict"] = "PASS"
        print("  【判定】✅ **窗口内所有跨机写操作都走了门**（★ %d/%d）" % (len(via), len(writes)))
    print()
    print("  ★ 诚实边界：★ shell history **不是完整日志**（★ 有上限、可被清、不记其它 shell）")
    print("    ⇒ ★ 本器是【下界】，★ 不是【全覆盖】。")
    if as_json:
        print(json.dumps(d, ensure_ascii=False))
    return 0 if d.get("verdict") == "PASS" else 1


def selftest():
    ok = tot = 0
    print("== xdom-bypass-scan 自查 ==")

    def chk(c, lb):
        nonlocal ok, tot
        tot += 1
        if c:
            ok += 1
            print("  ✅ %s" % lb)
        else:
            print("  ❌ %s" % lb)

    # ★ 正控：能读 shell history
    txt = _read(os.path.join(HOME, ".zsh_history"))
    chk(txt is not None, "正控：shell history 可读（%s）" % ("有内容" if txt else "空"))
    # ★ 正控：扫出的行是 list
    rows, _, err = scan_history(24 * 365)
    chk(isinstance(rows, list), "正控：scan_history 返回 list（%d 行）" % (len(rows) if rows else 0))
    # ★ 负控：写操作判定必须双向
    def is_write(c):
        return bool(re.search(r"(?:^|[;&|\s'\"])(sudo|rm|systemctl)\s", c)) \
            or bool(re.search(r"(^|[^0-9&])>{1,2}[^&]", c))
    chk(is_write("ssh h 'sudo rm -rf /'"), "负控：sudo/rm ⇒ 判为写")
    chk(not is_write("ssh h 'cat /etc/hostname'"), "负控：cat ⇒ 判为只读")
    # ★ 负控：history 不可读 ⇒ 返回 None（★ 而不得返回空 list 冒充「无旁路」）
    r2, _, e2 = scan_history(24)
    chk((r2 is None) == (e2 is not None), "负控：读不到 ⇒ (None, err) 而非 ([], None)")
    # ★ 正控：门日志读操作不崩
    n, gerr = scan_gate_log(24)
    chk(n is not None or gerr is not None, "正控：门日志读操作返回 (数, None) 或 (None, 原因)")
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("xdom-bypass-scan %s" % VERSION); return 0
    if a.selftest:
        return selftest()
    return run(a.hours, a.json)


if __name__ == "__main__":
    sys.exit(main())
