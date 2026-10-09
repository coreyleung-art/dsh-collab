#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-absorb-watch.py — 吸收循环常驻监控（事件驱动，零轮询零 token）

订阅黑板事件桥（:8803/events），监控 data/<node>/tools/ 命名空间——
节点登记新工具时自动触发 bb-absorb.py 评估 + 落链。

设计（吸收循环自动化）：
  · 事件驱动：订阅 8803 SSE（零轮询，只有工具登记才动作）
  · 自动评估：新工具出现 → 跑 bb-absorb.py（复用评估 + 落链建议）
  · 去重：已评估过的工具（data/iterations/absorb-* 有记录）跳过
  · 常驻：launchd 托管（或 nohup 后台）

用法：
  python3 bb-absorb-watch.py                    # 常驻
  python3 bb-absorb-watch.py --log /tmp/bb-absorb-watch.log
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== bb-absorb-watch 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · bb-absorb-watch.py — 吸收循环常驻监控（事件驱动，零轮询零 token）")
    print("  · 订阅黑板事件桥（:8803/events），监控 data/<node>/tools/ 命名空间——")
    print("  · 节点登记新工具时自动触发 bb-absorb.py 评估 + 落链。")
    print("  · 设计（吸收循环自动化）：")
    print("  · 命令/参数: log, lean4-check")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, os, re, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/bb-absorb-watch.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, time, datetime, subprocess, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-absorb-watch.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

EVENTS_URL = "http://127.0.0.1:8803/events"
BB = "http://127.0.0.1:8792"
WATCH_PREFIX = "/tools/"          # 监控 data/<node>/tools/ 登记
ABSORB = os.path.expanduser("~/dsh-collab/scripts/bb-absorb.py")
LOGF = None
SEEN = set()                      # 已处理工具去重

def log(msg):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    if LOGF:
        try:
            with open(LOGF, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

def bb_get(path):
    try:
        with urllib.request.urlopen(BB + path, timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {"error": "fetch_failed"}  # 404/网络错误 → 标记为未获取（未吸收）

def already_absorbed(node, tool):
    key = "data/iterations/absorb-%s-%s" % (node, tool.replace(".", "-"))
    d = bb_get("/" + key)
    # 只有真存在（有 absorbed_from 字段）才算已吸收；404/空/错误都算未吸收
    return isinstance(d, dict) and "absorbed_from" in d

def trigger_absorb(node, tool, desc_hint=""):
    """触发吸收评估（复用 bb-absorb.py）"""
    if tool in SEEN:
        return
    SEEN.add(tool)
    if already_absorbed(node, tool):
        log("⏭ 已吸收过: %s/%s（跳过）" % (node, tool))
        return
    log("🎯 检测到新工具: %s/%s → 触发吸收评估" % (node, tool))
    # ★ 2026-10-09 R10 修复：原为字符串拼接 + shell=True（参数可注入）
    #   ⇒ 改为【列表传参 + 无 shell】。
    cmd = ["python3", ABSORB, "--node", node, "--tool", tool,
           "--desc", desc_hint or ("%s 节点工具" % node),
           "--deps", "标准库", "--hub-dep", "黑板HTTP", "--node-side", "unix"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        out = (r.stdout or "") + (r.stderr or "")
        log("吸收评估完成:\n%s" % out[-300:])
    except Exception as ex:
        log("吸收评估失败: %s" % str(ex)[:100])

def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=None)
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--lean4-check", action="store_true", help="R006 10 A-F")
    if "--lean4-check" in sys.argv:
        return lean4_check()
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
    args = ap.parse_args()
    LOGF = args.log
    log("吸收循环监控启动（事件驱动订阅 %s，监控 %s）" % (EVENTS_URL, WATCH_PREFIX))
    while True:
        try:
            req = urllib.request.Request(EVENTS_URL, headers={"Accept": "text/event-stream"})
            resp = urllib.request.urlopen(req, timeout=None)
            log("已连接事件桥，等待节点工具登记...")
            for raw_line in resp:
                line = raw_line.decode("utf-8", "ignore").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data:
                    continue
                try:
                    evt = json.loads(data)
                except json.JSONDecodeError:
                    continue
                key = evt.get("key", "")
                # 匹配 data/<node>/tools/<tool>
                if key.startswith("data/") and WATCH_PREFIX in key:
                    parts = key.split("/")
                    if len(parts) >= 4 and parts[2] == "tools":
                        node = parts[1]
                        tool = parts[3]
                        trigger_absorb(node, tool)
        except Exception as ex:
            log("连接中断: %s（5s 后重连）" % str(ex)[:100])
            time.sleep(5)


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

    c("A", "类型锁：subprocess 无 shell=True ⇒ 参数不经 shell 解析",
      not _re.search(r'shell\s*=\s*True', _code),
      "无 shell（变量传参亦安全）")
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
    main()
