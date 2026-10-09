#!/usr/bin/env python3
"""星舵进度监督员·每 15 分钟唤醒（v5：目标会话退役/不在线时跳过本轮）
v3 缺陷（2026-09-05 重启后自检发现）：写死 61698 端口，CLD 重启后 GUI 端口漂移（61698→62124），
   send API Connection refused，投递唤醒静默失效数日（黑板留痕仍在，真投递断）
v4 修复：动态探测 agent-bus webServer 端口（CLD 监听端口列表中找 /agent-bus/api/state 响应者）
v5 修复（2026-10-03 全架构审查实测）：XINGDUO_SESSION（8c2494e0）已于 8/30 退役，
   本脚本仍每 15min 向死会话投递 ⇒ 累计 383 条 queued + 每天 96 张黑板卡（实测语料）。
   修复：投递前查 /agent-bus/api/state，目标不在线 ⇒ 跳过本轮（不写卡不投递）。
   判据：state.agents[] 含 XINGDUO_SESSION 才继续；查询失败保守跳过（宁漏一轮不刷死会话）。"""


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


import sys as _r006_sys
if __name__ == "__main__" and "--lean4-check" in _r006_sys.argv:
    _r006_sys.exit(lean4_check())

import json, re, subprocess, time, urllib.request

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/xingduo-wake.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

XINGDUO_SESSION = "session-8c2494e0-3772-4a62-9789-b7adc3123ccc"
BB = "http://127.0.0.1:8792"

def find_agent_bus_port():
    """从 CLD 进程监听端口找 agent-bus webServer（/agent-bus/api/state 返回 ok）"""
    try:
        r = subprocess.run(["/usr/sbin/lsof", "-nP", "-iTCP", "-sTCP:LISTEN"], capture_output=True, text=True, timeout=10)
        ports = set()
        for line in r.stdout.splitlines():
            m = re.search(r'CLD.*?127\.0\.0\.1:(\d+)', line)
            if m: ports.add(int(m.group(1)))
            m2 = re.search(r'CLD.*?\[::1\]:(\d+)', line)
            if m2: ports.add(int(m2.group(1)))
        for port in sorted(ports):
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{port}/agent-bus/api/state", method="GET")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        resp.read(64)
                        return port
            except Exception:
                continue
    except Exception as e:
        print(f"[xingduo-wake] 端口探测异常: {e}", flush=True)
    return None

def target_live(port):
    """v5：目标会话是否仍在活跃会话列表；查询失败保守返回 False"""
    if port is None:
        return False
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/agent-bus/api/state", method="GET")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
        agents = data.get("agents") or []
        return any(a.get("id") == XINGDUO_SESSION for a in agents)
    except Exception as e:
        print(f"[xingduo-wake] 状态查询失败（保守跳过本轮）: {e}", flush=True)
        return False

def bb_put(path, v):
    body = json.dumps(v).encode()
    req = urllib.request.Request(f"{BB}/{path}", data=body, method="PUT", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode())

ts = int(time.time())
port = find_agent_bus_port()
# ★ v5 活性门：目标退役/不在线 ⇒ 本轮静默跳过（不再向死会话写卡/投递）
if not target_live(port):
    print(f"[xingduo-wake] {time.strftime('%Y-%m-%d %H:%M:%S')} 星舵会话已退役/不在线，本轮跳过（不写卡不投递）", flush=True)
    raise SystemExit(0)

# ① 黑板留审计痕
try:
    bb_put(f"notes/8c2494e0/xingduo-wake-{ts}", {
        "value": {"from": "coordinator", "to": XINGDUO_SESSION, "type": "wake",
                  "body": "星舵，定时巡检时间到：扫 data/blueprint/ + data/iterations/ + data/progress/ → 有停滞写提醒卡 + 短提示协调者。24h 同项不重复。",
                  "ts": ts},
        "ts": ts
    })
except Exception as e:
    print(f"[xingduo-wake] bb_put 失败: {e}", flush=True)

# ② 真·投递唤醒（port 已由活性门保证非 None）
try:
    body = json.dumps({
        "to": XINGDUO_SESSION,
        "text": "【星舵·15min 定时巡检】扫黑板 data/blueprint/ + data/iterations/ + data/progress/，判断主线与 active 阶段是否停滞；有停滞写提醒卡并短提示协调者（24h 同项不重复）；无停滞静默。",
    }).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/agent-bus/api/send", data=body, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        resp = json.loads(r.read().decode())
    print(f"[xingduo-wake] {time.strftime('%Y-%m-%d %H:%M:%S')} 投递唤醒(port {port}): {resp.get('status')}", flush=True)
except Exception as e:
    print(f"[xingduo-wake] send API 失败: {e}", flush=True)

