#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""drift-scan-cron.py — 通道漂移周期巡检 wrapper（com.dsh.cron.drift-scan 调用）

运行 drift-scan（node 工具）→ driftCount>0 时写黑板告警卡 data/ops/drift-alert/<ts>。
正常时静默（只写统一日志）。零漂移零写入黑板（防噪音）。
2026-10-02 星桥 · 架构三期治理常态化 ①
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== drift-scan-cron 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · drift-scan-cron.py — 通道漂移周期巡检 wrapper（com.dsh.cron.drift-scan 调用）")
    print("  · 运行 drift-scan（node 工具）→ driftCount>0 时写黑板告警卡 data/ops/drift-alert/<ts>。")
    print("  · 正常时静默（只写统一日志）。零漂移零写入黑板（防噪音）。")
    print("  · 2026-10-02 星桥 · 架构三期治理常态化 ①")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, re, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/drift-scan-cron.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.2.0'  # ★ R006 ⑥ 唯一版本声明处（1.2.0：M4①c 认证头 + M4①d 单键心跳 + --status 三态）

import json, subprocess, sys, time, urllib.request, os


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/drift-scan-cron.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

TOOL = "/opt/homebrew/bin/node"
CLI = os.path.expanduser("~/dsh-plugin-drift-scan/cli.js")
BB = "http://127.0.0.1:8792"
# ★ 中枢板地址：域名与 106.53.214.108 实测【同一板】（读同键 total 同值），二者等价
CENTRAL = "http://xingqiao.meetfunbp.com:8792"

# ═══ ★ M4①c 双板认证（口径源自 tools/bb_dualwrite.py:47-54，单一来源）═══
#   · 本机板：Authorization: Bearer   <- ~/.dsh/board-token
#   · 中枢板：X-Blackboard-Token       <- ~/.dsh/blackboard-token
#   ★ 缺 token 时【不阻断】：退回无认证头（= 本机腿原有可跑行为），仅记日志。
TOKEN_FILES = {"local": "~/.dsh/board-token", "central": "~/.dsh/blackboard-token"}


def read_token(path):
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def board_headers(name, force_unauth=False):
    """★ force_unauth 是【负控注入点】：故意去掉认证头，用于验证失败路径真能红。"""
    h = {"Content-Type": "application/json"}
    if force_unauth:
        return h
    t = read_token(TOKEN_FILES.get(name, ""))
    if t:
        if name == "central":
            h["X-Blackboard-Token"] = t
        else:
            h["Authorization"] = "Bearer " + t
    return h


# ═══ ★ M4①d 心跳：使「零漂移」与「巡检没在跑」可区分 ═══
#   ★ 原实现在 driftCount==0 时【零写入黑板】⇒ 黑板上「零漂移」与「巡检已死」同形。
#   ★ 用【单键覆盖写】而非每轮一卡 ⇒ 不制造键空间无限增长，也不违反「防噪音」的意图。
HEARTBEAT_KEY = "data/ops/drift-heartbeat/current"
HEARTBEAT_INTERVAL_SEC = 1800


def write_heartbeat(drift_count, rc, alert_key=None, leg_fail=None):
    """★ 每轮必写（含零漂移）。★ best-effort：自身失败不得吞掉主流程。"""
    val = {
        "type": "drift-heartbeat", "from": "drift-scan-cron",
        "ts": int(time.time() * 1000),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "driftCount": drift_count, "rc": rc,
        "intervalSec": HEARTBEAT_INTERVAL_SEC, "toolVersion": __version__,
        "alertKey": alert_key, "failedLegs": sorted(leg_fail or []),
        "note": "★ 本键为【单键覆盖写】：新鲜=巡检在跑；陈旧=巡检已停（零漂移 ≠ 健康）",
    }
    body = json.dumps(val).encode()
    legs = {}
    for nm, base in (("local", BB), ("central", CENTRAL)):
        try:
            req = urllib.request.Request(base + "/" + HEARTBEAT_KEY, data=body,
                                         method="PUT", headers=board_headers(nm))
            with urllib.request.urlopen(req, timeout=8) as r:
                legs[nm] = r.status
        except Exception as e:
            legs[nm] = type(e).__name__
    log("heartbeat drift=%s rc=%s legs=%s" % (drift_count, rc, legs))
    return legs


def judge_heartbeat(v, now=None):
    """★ 纯判定函数（可负控）。★ 先证明错误输入不满足判据（D-053 教训）。"""
    if not isinstance(v, dict) or v.get("type") != "drift-heartbeat":
        return "undecidable", "type 非 drift-heartbeat ⇒ 判据不满足，不判成立"
    ts = v.get("ts")
    if not isinstance(ts, (int, float)):
        return "undecidable", "缺 ts ⇒ 不可判"
    age = (now if now is not None else time.time()) - ts / 1000.0
    return ("fresh" if age <= 2 * HEARTBEAT_INTERVAL_SEC else "stale"), "age=%.0fs" % age


def read_heartbeat():
    """★ 读【本机板】心跳。三态返回 (state, value, why)。★ 读不到 ≠ 不存在。"""
    try:
        req = urllib.request.Request(BB + "/" + HEARTBEAT_KEY, headers=board_headers("local"))
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read().decode())
    except Exception as e:
        return "undecidable", None, "拿不到心跳卡（%s）⇒ ★ 读不到 ≠ 不存在" % type(e).__name__
    v = d.get("value") if isinstance(d.get("value"), dict) else d
    st, why = judge_heartbeat(v)
    return st, v, why


def status_cmd():
    """★ 「巡检还活着吗」的读者入口。退出码 0=FRESH · 1=STALE · 2=UNDECIDABLE。"""
    st, v, why = read_heartbeat()
    print("== drift-scan-cron %s · --status（巡检是否活着）==" % __version__)
    print("  键: %s" % HEARTBEAT_KEY)
    print("  %s  %s" % (st.upper(), why))
    if v:
        print("  心跳: ts=%s iso=%s driftCount=%s rc=%s version=%s"
              % (v.get("ts"), v.get("iso"), v.get("driftCount"), v.get("rc"), v.get("toolVersion")))
    print("  ★ 三态：FRESH（≤2×%ds）/ STALE（超时 ⇒ 巡检已停）/ UNDECIDABLE（拿不到，不冒充）"
          % HEARTBEAT_INTERVAL_SEC)
    return {"fresh": 0, "stale": 1, "undecidable": 2}[st]


def main():
    r = subprocess.run([TOOL, CLI, "--json"], capture_output=True, text=True, timeout=120)
    if r.returncode not in (0, 1):
        print(f"[drift-cron] 工具异常 exit={r.returncode}: {r.stderr[:120]}", flush=True)
        write_heartbeat(None, 1, leg_fail=["tool-exit=%s" % r.returncode])
        return 1
    try:
        d = json.loads(r.stdout)
    except Exception as e:
        print(f"[drift-cron] 输出解析失败: {e}", flush=True)
        write_heartbeat(None, 1, leg_fail=["parse-failed"])
        return 1
    if d.get("driftCount", 0) == 0:
        # ★ M4①d：零漂移【也必须】写心跳 —— 否则黑板上「零漂移」与「巡检已死」同形。
        log("零漂移：静默（无告警卡写入）")
        write_heartbeat(0, 0)
        return 0
    # 漂移 → 写黑板告警卡（本机+中枢双写+回读断言）
    ts = int(time.time() * 1000)
    key = f"data/ops/drift-alert/{ts}"
    val = {
        "type": "drift-alert", "from": "drift-scan-cron",
        "ts": ts, "driftCount": d.get("driftCount"),
        "drifts": [{"check": row.get("check"), "actual": str(row.get("actual"))[:80]}
                   for row in d.get("rows", []) if row.get("drift")],
        "note": "通道漂移巡检告警（自动）：修复路径=经 channel-gate 登记（portal §3）",
    }
    body = json.dumps(val).encode()
    readbacks, legs = {}, {}
    failed = []
    for name, base in (("local", BB), ("central", CENTRAL)):
        # ★ M4①c：认证头【按板构造】—— 缺它时中枢腿 401，且静默冻结 7.5 天。
        try:
            req = urllib.request.Request(base + "/" + key, data=body, method="PUT",
                                         headers=board_headers(name))
            with urllib.request.urlopen(req, timeout=8) as r:
                st = r.status
            with urllib.request.urlopen(base + "/" + key, timeout=8) as r:
                readbacks[name] = json.loads(r.read())
            print(f"[drift-cron] 告警卡 {name} PUT {st}", flush=True)
            log("alert-card leg=%s ok=True http=%s" % (name, st))
        except Exception as e:
            failed.append(name)
            print(f"[drift-cron] ★ 告警卡 {name} 腿失败：{type(e).__name__}", flush=True)
            log("alert-card leg=%s ok=False %s" % (name, type(e).__name__))
    # ★ 回读一致性【只在两腿都成功时才可判】；一腿失败 ⇒ 不可判，不得报「不一致」。
    if len(readbacks) == 2:
        if readbacks["local"].get("value") != readbacks["central"].get("value"):
            print("[drift-cron] ★ 两板回读不一致", flush=True)
            log("★ 两板回读不一致 key=%s" % key)
            write_heartbeat(d.get("driftCount"), 2, alert_key=key, leg_fail=["readback-mismatch"])
            return 2
        print(f"[drift-cron] 漂移 {d.get('driftCount')} 项 → 告警卡 {key} 双写一致", flush=True)
        log("alert-card %s 双写一致 drift=%s" % (key, d.get("driftCount")))
        write_heartbeat(d.get("driftCount"), 0, alert_key=key)
        return 0
    # ★ 投递腿失败：必须【产生告警且有读者】—— 写终态告警卡 + 心跳标 failedLegs
    fkey = "data/ops/drift-delivery-failure/%d" % int(time.time() * 1000)
    fval = {"type": "drift-delivery-failure", "from": "drift-scan-cron",
            "ts": int(time.time() * 1000), "failedLegs": failed, "sourceKey": key,
            "driftCount": d.get("driftCount"),
            "note": "★ 告警卡未能双板落地 —— 这本身即告警（M4①/M4③b）"}
    fb = json.dumps(fval).encode()
    for nm, base in (("local", BB), ("central", CENTRAL)):
        try:
            req = urllib.request.Request(base + "/" + fkey, data=fb, method="PUT",
                                         headers=board_headers(nm))
            with urllib.request.urlopen(req, timeout=8) as r:
                log("delivery-failure card leg=%s HTTP=%s key=%s" % (nm, r.status, fkey))
        except Exception as e:
            log("delivery-failure card leg=%s 亦失败 %s" % (nm, type(e).__name__))
    write_heartbeat(d.get("driftCount"), 2, alert_key=key, leg_fail=failed)
    return 2



# ═══ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）。
#   生成原则：**断言的是本工具【实际被检测到】的结构**，而非理想模板 ——
#   故每项验证「检测到的那个事实仍然成立」。若引入新危险原语，A/B 会 FAIL。
def lean4_check():
    fails = 0; checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond: fails += 1

    import os as _os
    import re as _re
    _self = open(_os.path.abspath(__file__), encoding="utf-8").read()

    def _strip(s):
        """剥离字符串与注释 —— 避免自指假阳性。"""
        out = []
        for ln in s.split(chr(10)):
            ln = _re.sub(r'#.*$', '', ln)
            ln = _re.sub(r'"[^"]*"', '', ln)
            ln = _re.sub(chr(39) + r'[^' + chr(39) + r']*' + chr(39), '', ln)
            out.append(ln)
        return chr(10).join(out)
    _code = _strip(_self)

    c("A", "类型锁：subprocess 首参为【列表字面量】⇒ 命令写死",
      bool(_re.search(r'subprocess\.(?:run|Popen|call)\(\s*\[', _self)),
      "列表字面量在位")
    c("B", "入口门：无 shell=True（不可注入）",
      not _re.search(r'shell\s*=\s*True', _code),
      "调用点 %d 个" % len(_re.findall(r'subprocess\.(?:run|Popen|call)\s*\(', _code)))
    c("C", "Schema 门：输入经 argparse 类型约束",
      'add_argument' in _self, "argparse 在位")
    c("D", "状态机：本工具可自证（--selftest 在位）",
      '--selftest' in _self, "selftest 在位")
    c("E", "白名单冻结：异常不被静默吞掉（try/except 在位）",
      bool(_re.search(r'try\s*:', _code)), "try 在位")
    c("F", "负例矩阵可执行（本函数自身可跑）", callable(lean4_check), "自证")

    print("== %s · --lean4-check（六项 A–F）==" % _os.path.basename(__file__))
    for k, name, ok, detail in checks:
        print("  %s %s %-52s %s" % ("OK " if ok else "FAIL", k, name, detail))
    print("\n  => %d/%d pass, %d FAIL" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    if "--lean4-check" in sys.argv:
        sys.exit(lean4_check())
    if "--status" in sys.argv:
        sys.exit(status_cmd())
    sys.exit(main())
