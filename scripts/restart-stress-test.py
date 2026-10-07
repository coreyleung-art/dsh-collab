#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""restart-stress-test.py — 自动化重启压力测试（沙箱隔离端口，不碰生产 CLD）

目的：反复启动 dsh web（隔离端口），验证：
  · 每次启动不崩溃（稳定性）
  · 三插件自查门每次通过（selfcheck.log 增量 ✅）
  · central-inbox 注入目标正确（node=mac-mini → fa1f9150）
  · 内存/启动时间趋势（资源无泄漏）

用法:
  restart-stress-test.py [--rounds 5] [--hold 10] [--port-start 3090] [--sleep-boot 8]
  restart-stress-test.py --rounds 10 --hold 15   # 10 轮，每轮保持 15s

输出: 每轮结果 + 汇总统计（成功率/平均启动/内存趋势/错误）
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, signal, subprocess, sys, time, datetime

NODE = "/opt/homebrew/bin/node"
BIN = "/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh/lib/bin.js"
SELFCHECK_LOG = os.path.expanduser("~/.dsh/plugin-selfcheck/selfcheck.log")
CENTRAL_LOG = os.path.expanduser("~/.dsh/central-inbox.log")
PLUGINS = ["central-inbox", "agent-way", "openchronicle"]

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def count_selfcheck_ok():
    """统计 selfcheck.log 里各插件 ✅ 次数"""
    counts = {p: 0 for p in PLUGINS}
    try:
        with open(SELFCHECK_LOG) as f:
            for line in f:
                for p in PLUGINS:
                    if f"✅ {p} 自查通过" in line:
                        counts[p] += 1
    except Exception:
        pass
    return counts

def count_central_inject():
    """统计 central-inbox 日志里 node=mac-mini + 注入 fa1f9150 次数"""
    try:
        with open(CENTRAL_LOG) as f:
            txt = f.read()
        return {
            "node_mac_mini": txt.count("node=mac-mini"),
            "inject_fa1f9150": txt.count("注入 session-fa1f9150"),
            "sse_connected": txt.count("SSE 已连接"),
        }
    except Exception:
        return {"node_mac_mini": 0, "inject_fa1f9150": 0, "sse_connected": 0}

def get_mem_kb(pid):
    """进程 RSS KB"""
    try:
        r = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True)
        return int(r.stdout.strip() or 0)
    except Exception:
        return 0

def run_round(round_no, port, hold_sec, boot_wait):
    """单轮重启测试，返回 (ok, boot_time, mem_kb, error)"""
    before_selfcheck = count_selfcheck_ok()
    before_central = count_central_inject()
    log(f"── 轮 {round_no}: 启动 dsh web :{port}（保持 {hold_sec}s）")

    out_log = f"/tmp/dsh-stress-{port}.log"
    if os.path.exists(out_log):
        os.remove(out_log)
    proc = subprocess.Popen(
        [NODE, BIN, "--profile", "web", "--port", str(port)],
        stdout=open(out_log, "w"), stderr=subprocess.STDOUT,
    )
    boot_start = time.time()
    time.sleep(boot_wait)  # 等 boot

    # 判断存活
    alive = proc.poll() is None
    if not alive:
        err = f"进程退出 code={proc.returncode}"
        tail = ""
        try:
            tail = "\n".join(open(out_log).read().strip().split("\n")[-8:])
        except Exception:
            pass
        return False, 0, 0, f"{err}\n{tail}"

    boot_time = time.time() - boot_start
    mem = get_mem_kb(proc.pid)

    # 检查自查门增量
    after_selfcheck = count_selfcheck_ok()
    self_ok = all(after_selfcheck[p] > before_selfcheck[p] for p in PLUGINS)
    self_detail = {p: after_selfcheck[p] - before_selfcheck[p] for p in PLUGINS}

    # 检查 central-inbox 注入配置
    after_central = count_central_inject()
    inject_ok = after_central["node_mac_mini"] > before_central["node_mac_mini"] \
        and after_central["inject_fa1f9150"] > before_central["inject_fa1f9150"]
    central_detail = {k: after_central[k] - before_central[k] for k in after_central}

    # 保持 hold 时间（继续观察稳定性）
    time.sleep(max(0, hold_sec - boot_wait))
    still_alive = proc.poll() is None
    if not still_alive:
        proc.kill()
        return False, boot_time, mem, f"保持期退出 code={proc.returncode}"

    # 清理
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

    errors = []
    if not self_ok:
        errors.append(f"自查门未全通过: {self_detail}")
    if not inject_ok:
        errors.append(f"注入配置异常: {central_detail}")
    ok = len(errors) == 0
    log(f"  结果: {'✅ PASS' if ok else '❌ FAIL'} | boot={boot_time:.1f}s | mem={mem}KB | 自查={self_detail} | 注入={central_detail}")
    if errors:
        log(f"  错误: {errors}")
    return ok, boot_time, mem, "; ".join(errors) if errors else ""

def main():
    ap = argparse.ArgumentParser(description="自动化重启压力测试（沙箱隔离端口）")
    ap.add_argument("--rounds", type=int, default=5, help="测试轮数（默认 5）")
    ap.add_argument("--hold", type=int, default=10, help="每轮保持秒数（默认 10）")
    ap.add_argument("--port-start", type=int, default=3090, help="起始端口（默认 3090）")
    ap.add_argument("--boot-wait", type=int, default=8, help="boot 等待秒数（默认 8）")
    args = ap.parse_args()

    log(f"══ 重启压力测试开始: {args.rounds} 轮 × 保持 {args.hold}s ══")
    log(f"基线自查: {count_selfcheck_ok()} | 基线注入: {count_central_inject()}")

    results = []
    mems = []
    boot_times = []
    for i in range(1, args.rounds + 1):
        port = args.port_start + i - 1
        ok, boot_t, mem, err = run_round(i, port, args.hold, args.boot_wait)
        results.append(ok)
        if mem:
            mems.append(mem)
        if boot_t:
            boot_times.append(boot_t)
        if not ok:
            log(f"  ❌ 轮 {i} 失败: {err}")
        time.sleep(1)  # 轮间间隔（清理）

    # 汇总
    total = len(results)
    passed = sum(results)
    rate = passed / total * 100
    avg_boot = sum(boot_times) / len(boot_times) if boot_times else 0
    avg_mem = sum(mems) / len(mems) if mems else 0
    mem_growth = (mems[-1] - mems[0]) if len(mems) >= 2 else 0

    log("══ 汇总 ══")
    log(f"成功率: {passed}/{total} ({rate:.0f}%)")
    log(f"平均启动: {avg_boot:.1f}s | 平均内存: {avg_mem/1024:.0f}MB | 内存增长(末-首): {mem_growth/1024:.1f}MB")
    log(f"最终自查计数: {count_selfcheck_ok()}")
    log(f"最终注入计数: {count_central_inject()}")
    if rate == 100:
        log("✅ 压力测试全部通过：可安全重启（R011/R013 背书）")
        sys.exit(0)
    else:
        log(f"❌ {total - passed} 轮失败，需排查")
        sys.exit(1)

if __name__ == "__main__":
    main()
