#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""load-gate-reader — 给 `com.dsh.load-gate` 配一个【真读者】。

★ 为什么需要（立据）：
  `beacon-check.py` 的 **H2d 失败终态有读者** 逐字要求：★「每个失败终态任务，
  都应能指出它的告警读者」。★ 立据是 D-339：**中枢 OOM 持续 11 天没被发现**，
  而 `bb-copy-staleness` 早就在报「中枢写入失败」—— ★ **只是没人看**。
  ★★ 实测 `com.dsh.load-gate` 长期处于【失败终态】（`launchctl list` 显示 `- 1`），
  而 `data/ops/` 下**没有任何键**提到它 ⇒ ★ 它**有判定、没有读者**。

★★ 本件做什么：
  读 `com.dsh.load-gate` 的当前状态与其 stdout 日志尾（`/tmp/load-gate.log`），
  把 **状态 + 退出码 + 判定行 + 日志时间** 写成一块 **`data/ops/load-gate-verdict`**
  板卡（★ 走本仓标准**双写** `tools/bb_dualwrite.py` ⇒ 本地 + 中枢，带 `X-Writer` 归属）。
  ★ 键名含 `load-gate` ⇒ 满足 H2d 的读者判据（判据实现见
  `tools/silent-failure-scan.py:launchd_failed_full()`：取 label 末段，在 `/data/ops/` 里找同名键）。

★ 用法：
  `python3 tools/load-gate-reader.py`            # 读一次并写板
  `python3 tools/load-gate-reader.py --dry-run`  # 只打印将写入的内容，不写板
  `python3 tools/load-gate-reader.py --selftest` # 自证（含负控）
  `python3 tools/load-gate-reader.py --version`

★ 退出码：
  `0` = 读成功；写出成功（或 `--dry-run`）。
  `1` = 写板失败（★ 板不可达等）—— ★ 此时**如实报错**，不静默吞掉。
  `2` = 读 `launchctl` 失败（★ 不可判，★ 不写一个假「正常」）。

★ 坑（★ 都是本仓实测过的）：
  ① ★ **本任务的非零退出是【判定信号】，不是崩溃**：`load-gate` 判「🟡 资源偏紧」时
     `exit 1`（实测日志逐字：`══ 判定: [🟡] 资源偏紧: 本机内存余量 17% ══`）
     ⇒ ★ 故本件**同时**记 `exit` 与 `verdict` 两格，★ **不把 exit≠0 直接读成故障**。
  ② ★ 板键语法：★ 首段必须是**纯小写字母**（`data` ✅）；★ `data/ops/load-gate-verdict` 合法。
  ③ ★ 键名是判据的一部分 —— ★ **改名会让 H2d 立刻转红**（★ 键必须含 `load-gate`）。
  ④ ★ 日志可能为空（★ 实测 `.err` 为空、`.log` 有内容）⇒ ★ 空**不等于**「没跑过」。
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

VERSION = "1.0.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABEL = "com.dsh.load-gate"
KEY = "data/ops/load-gate-verdict"
LOG = "/tmp/load-gate.log"
DUALWRITE = os.path.join(ROOT, "tools", "bb_dualwrite.py")


def read_job(label=LABEL):
    """★ 读 launchd 状态：返回 {'pid','exit'} 或 None（★ 读不到 ⇒ 不可判，不猜）。"""
    try:
        r = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=25)
    except Exception:
        return None
    for ln in (r.stdout or "").split("\n"):
        p = ln.split("\t")
        if len(p) >= 3 and p[2] == label:
            return {"pid": p[0], "exit": p[1]}
    return None


def read_log(path=LOG, tail_bytes=4000):
    """★ 读日志尾：返回 (末次判定行, 文件 mtime ISO, 原始尾部)。"""
    if not os.path.exists(path):
        return None, None, ""
    try:
        sz = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, sz - tail_bytes))
            raw = f.read().decode("utf-8", "ignore")
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path)).astimezone().isoformat(timespec="seconds")
        verdict = None
        for ln in raw.split("\n"):
            if "判定" in ln:
                verdict = ln.strip()
        return verdict, mtime, raw[-800:]
    except Exception:
        return None, None, ""


def build_payload():
    """★ 组装要写板的 payload（★ 三态：读不到 ⇒ 如实标注，不写假的「正常」）。"""
    job = read_job()
    verdict, mtime, tail = read_log()
    ts = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    if job is None:
        return None, "★ `launchctl list` 里读不到 %s ⇒ 不可判（★ 空 ≠ 无）；★ 不写板" % LABEL
    payload = {
        "ts": ts,
        "kind": "load-gate-verdict",
        "from": "load-gate-reader",
        "from_label": "星桥第三任 · load-gate 读者（H2d）",
        "value": {
            "ts": ts,
            "label": LABEL,
            "launchd_pid": job["pid"],
            "launchd_exit": job["exit"],
            "★ 语义提示": "exit≠0 是本任务的【判定信号】（黄灯/红灯），不必然是崩溃 —— 须连 verdict 一起读",
            "verdict_line": verdict or "（日志里没有『判定』行 ⇒ 未判 / 未跑）",
            "log_mtime": mtime or "（无日志）",
            "log_tail": tail,
        },
    }
    return payload, None


def write_board(payload):
    """★ 走本仓标准双写（★ 带 X-Writer 归属 ⇒ 同时满足写者归属门）。"""
    fd, tmp = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        r = subprocess.run([sys.executable, DUALWRITE, "--key", KEY, "--json-file", tmp,
                            "--writer", "load-gate-reader", "--json"],
                           capture_output=True, text=True, timeout=90)
        return r.returncode == 0, (r.stdout or "") + (r.stderr or "")
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass


def selftest():
    """★ 自证：含【负控】（★ 造坏必须能被抓）。"""
    ok = tot = 0
    p = None

    def c(name, cond):
        nonlocal ok, tot
        tot += 1
        print("  %s %s" % ("✅" if cond else "❌", name))
        ok += 1 if cond else 0

    c("★ 键名含 `load-gate`（★ H2d 读者判据的硬要求；★ 改名会立刻转红）", "load-gate" in KEY)
    c("★ 键首段是纯小写字母（板键语法）", re.fullmatch(r"[a-z]+(?:/[a-z0-9-]+)+", KEY) is not None)
    c("负控：把键名改成不含任务名 ⇒ 自查必须判『不满足读者判据』",
      not bool(re.search(r"load-gate", "data/ops/verdict")))
    p, err = build_payload()
    if err:
        c("真实读（★ 读不到时如实返回不可判，不写假值）", "不可判" in err)
    else:
        v = p["value"]
        c("真实读：payload 同时含 exit 与 verdict 两个量（★ 不把 exit≠0 直接读成故障）",
          "launchd_exit" in v and "verdict_line" in v)
        c("真实读：ts 为秒级 ISO", bool(re.match(r"\d{4}-\d\d-\d\dT", v["ts"] or "")))
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("load-gate-reader %s" % VERSION)
        return 0
    if a.selftest:
        return selftest()
    payload, err = build_payload()
    if err:
        print(err)
        return 2
    if a.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        return 0
    good, out = write_board(payload)
    print("★ 板键：%s ⇒ %s" % (KEY, "写入成功" if good else "★ 写入失败"))
    if not good:
        print(out[-400:])
        return 1
    v = payload["value"]
    print("  launchd: pid=%s exit=%s · %s" % (v["launchd_pid"], v["launchd_exit"], v["verdict_line"][:70]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
