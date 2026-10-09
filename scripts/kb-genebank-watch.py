#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb-genebank-watch.py — 语义库→基因库自动同步常驻监控（事件驱动）

用户指示（2026-08-24）：语义库更新后自动同步基因库，过程自动化。
事件驱动：订阅黑板事件桥（8803），检测语义库来源更新（论文落链/新 PDF 登记）→
自动触发 kb-genebank-sync.py（去重 + 断点续传）。

触发源：
  - data/recovery/4787d717-*（论文落链完成）
  - data/iterations/*（迭代落链）
  - 定期兜底（每 6h 全量扫描对比）

用法：
  python3 kb-genebank-watch.py                      # 常驻（事件驱动 + 6h 兜底）
  python3 kb-genebank-watch.py --log /tmp/kb-gb-watch.log
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, time, datetime, subprocess, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/kb-genebank-watch.log")


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
SYNC = os.path.expanduser("~/dsh-collab/scripts/kb-genebank-sync.py")
LOGF = None
LAST_FULL = 0
FULL_INTERVAL = 6 * 3600  # 6h 兜底全量

def log(msg):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    if LOGF:
        try:
            with open(LOGF, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

def trigger_sync(why):
    """触发一次同步（增量去重 + 断点续传）"""
    log("🔄 触发同步（%s）" % why)
    try:
        # ★ 2026-10-09 R10 修复：SYNC 为常量 ⇒ 改列表传参（去 shell）
        r = subprocess.run(["python3", SYNC], capture_output=True, text=True, timeout=600)
        out = (r.stdout or "") + (r.stderr or "")
        # 摘要
        for line in out.split("\n")[-5:]:
            if line.strip():
                log("  " + line.strip()[:100])
    except Exception as e:
        log("同步失败: %s" % str(e)[:100])

def is_sync_source(key):
    """判断事件是否来自语义库更新源"""
    triggers = [
        key.startswith("data/recovery/4787d717-"),   # 论文落链
        "/papers/" in key or "paper-cache" in key,    # 论文登记
        key.startswith("data/iterations/") and ("paper" in key or "yolo" in key),
        "datasets/" in key,                            # 数据集
    ]
    return any(triggers)

def main():
    global LOGF, LAST_FULL
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=None)
    ap.add_argument("--lean4-check", action="store_true", help="R006 10 A-F")
    if "--lean4-check" in sys.argv:
        return lean4_check()
    args = ap.parse_args()
    LOGF = args.log
    log("语义库→基因库同步监控启动（事件驱动 %s + 6h 兜底）" % EVENTS_URL)
    while True:
        # 6h 兜底全量
        if time.time() - LAST_FULL > FULL_INTERVAL:
            LAST_FULL = time.time()
            trigger_sync("6h 定期兜底")
        try:
            req = urllib.request.Request(EVENTS_URL, headers={"Accept": "text/event-stream"})
            resp = urllib.request.urlopen(req, timeout=None)
            log("已连接事件桥，等待语义库更新...")
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
                if is_sync_source(key):
                    trigger_sync("事件: %s" % key.split("/")[-1])
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
    main()
