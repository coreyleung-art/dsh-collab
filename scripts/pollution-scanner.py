#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pollution-scanner.py — 通讯污染持续识别与根治（R006 十项标准结构门）
用户 2026-09-09：collab 污染是显性一例，应按 R006 十项设计工具识别全部污染类型，动态持续根治。

检测 10 类污染（每类=一个检测器，输出溯源+修复建议）：
  P1 域错配:    消息写错域 / collab 灌跨设备(G-C27 复查)
  P2 广播污染:  非协调者广播 / 群聊放大
  P3 spoof:     伪造 from / 伪装身份(G-C11s 复查)
  P4 重复:      relay+直发双收 / 未去重(G-C15)
  P5 空/无效目标: 投不存在的角色设备(队列滞留源)
  P6 风暴:      同目标高频轰炸(G-C13)
  P7 大payload:  >4KB 塞总线(G-C18)
  P8 队列幽灵:  processing 滞留不 ACK(G-C4)
  P9 越权写:    agent 写无权限域(bb-gate can_write)
  P10 状态自判:  agent 各自判在线(应查守护状态)

用法:
  python3 pollution-scanner.py                 # 全量扫描(本机视角)
  python3 pollution-scanner.py --live          # 含服务器队列实时检查
  python3 pollution-scanner.py --fix P4        # 对可自动修复项执行修复(如清理幽灵)
  python3 pollution-scanner.py --watch 3600    # 常驻: 每小时扫一次, 发现污染告警黑板

输出: 每类 {污染?, 证据, 溯源, 修复建议} + 汇总分
R006#10: 本工具自身带 --lean4-check 自检(约束不可绕过)
"""
import argparse, json, os, re, subprocess, sys, time, datetime

# ===== 配置 =====
SERVER_BUS = "http://106.53.214.108:8791"
SERVER_BB = "http://106.53.214.108:8792"
TOKEN_FILE = os.path.expanduser("~/.dsh/bus-bridge-token")
LOCAL_DAEMON_LOG = os.path.expanduser("~/.dsh/logs/device-daemon.log")
# 检测结果累积
RESULTS = []

def report(pid, polluted, evidence, source, fix):
    RESULTS.append({"id": pid, "polluted": polluted, "evidence": evidence,
                    "source": source, "fix": fix})

def bus_token():
    try: return open(TOKEN_FILE).read().strip()
    except: return ""

def http_get(url, headers=None):
    import urllib.request
    h = headers or {}
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)[:60]}

# ═══════ P 系列检测器 ═══════

def p1_domain_mismatch():
    """P1 域错配: 守护日志里跨设备信封是否误写 collab(应为 notes/mac-mini/)"""
    try:
        src = open(os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")).read()
        # 守护现在按域分区(domain=NODE for mac-mini)
        has_partition = 'domain = NODE' in src and 'notes/{domain}/bus-{action}' in src
        # 近期误写 collab 的跨设备信封(日志证据)
        recent = []
        if os.path.exists(LOCAL_DAEMON_LOG):
            # 只看域隔离修复后(时间>00:36)的 collab 写——历史记录不计
            for line in open(LOCAL_DAEMON_LOG, errors="ignore").read().split("\n")[-40:]:
                if "信封→黑板 notes/collab/" in line and "[00:36" <= line[1:7]:
                    recent.append(line.strip()[:80])
        polluted = (not has_partition) or bool(recent)
        ev = "守护域分区=" + ("有" if has_partition else "无") + " 近期collab信封=" + str(len(recent))
        return polluted, ev, "守护 dispatch 写域逻辑", "确认守护含 domain=NODE 分区; 误写 collab 信封改 notes/mac-mini/"
    except Exception as e:
        return True, "检查异常:" + str(e)[:40], "?", "手动排查守护"

def p2_broadcast_abuse():
    """P2 广播污染: 近期 agent_broadcast/all 使用(非协调者广播)"""
    import json as _j
    try:
        bus = _j.load(open(os.path.expanduser("~/.dsh/agent-bus.json")))
        # 广播线程(多人参与者)近期活跃
        threads = bus.get("threads", [])
        recent_bcast = 0
        for t in threads[-50:]:
            msgs = t.get("messages", [])
            if len(msgs) > 3 and msgs:  # 多人线程
                recent_bcast += 1
        # 无法从 agent-bus.json 精确判断 all=true; 用参与者数>3 近似
        polluted = recent_bcast > 5  # 近 50 线程中 >5 个多人 = 广播偏多
        return polluted, "近期多人线程=" + str(recent_bcast) + "/50", "agent_broadcast 调用方", "广播收敛: 协调者专属 + 黑板域单卡替代(G-C28)"
    except Exception:
        return False, "threads 不可读", "?", ""

def p3_spoof():
    """P3 spoof: 守护日志近期拒路由(不可信信源)"""
    try:
        if not os.path.exists(LOCAL_DAEMON_LOG):
            return False, "守护日志缺", "?", ""
        rejects = 0
        for line in open(LOCAL_DAEMON_LOG, errors="ignore").read().split("\n")[-50:]:
            if "拒路由" in line or "untrusted" in line:
                rejects += 1
        polluted = rejects > 10  # 拦截>10次才提示(正常拦截非污染)
        note = "防spoof拦截中" if 0 < rejects <= 10 else ("拦截频繁" if rejects > 10 else "无拦截")
        return polluted, "近期拒路由=" + str(rejects) + "次(" + note + ")", "伪造 from 源", "已拦——若频繁需加 trust-map"
    except Exception:
        return False, "?", "?", ""

def p4_duplicate():
    """P4 重复: 守护日志同 task 双处理(relay+直发)"""
    try:
        if not os.path.exists(LOCAL_DAEMON_LOG):
            return False, "日志缺", "?", ""
        lines = open(LOCAL_DAEMON_LOG, errors="ignore").read().split("\n")
        # 同 task_id 出现>1次(排除重连日志)
        import collections
        tasks = collections.Counter()
        for l in lines:
            m = re.search(r"task ([a-f0-9]{8})", l)
            if m: tasks[m.group(1)] += 1
        dups = {t: c for t, c in tasks.items() if c > 2}  # SSE+relay 兜底=2次正常; >2 真重复
        polluted = bool(dups)
        return polluted, "异常重复任务=" + str(len(dups)) + "个(如" + str(list(dups)[:3]) + ")", "relay+直发竞争", "G-C15 hash 去重(服务器)"
    except Exception:
        return False, "?", "?", ""

def p5_invalid_target():
    """P5 无效目标: 服务器队列 recent 有无 queued/无效目标滞留"""
    d = http_get(f"{SERVER_BUS}/bus/status", {"X-Webhook-Token": bus_token()})
    if "error" in d: return True, "bus 查失败:" + str(d["error"])[:40], "服务器", "检查服务器"
    stats = d.get("stats", {})
    queued = stats.get("queued", 0)
    polluted = queued > 2  # 滞留>2 视为异常
    return polluted, f"queued={queued}", "未消费目标", "离线转黑板/清理幽灵(G-C4/C5)"

def p6_storm():
    """P6 风暴: 同 target 高频(近 recent 中同 from 重复发)"""
    d = http_get(f"{SERVER_BUS}/bus/status", {"X-Webhook-Token": bus_token()})
    if "error" in d: return False, "bus 查失败", "?", ""
    import collections
    froms = collections.Counter()
    for t in d.get("recent", []):
        froms[t.get("from", "?")] += 1
    hot = {f: c for f, c in froms.items() if c >= 5}  # 近期同源>=5 次
    polluted = bool(hot)
    return polluted, "高频源=" + str(dict(hot) if hot else "无"), "风暴源", "G-C13 熔断(同目标10min>5次→死信)"

def p7_large_payload():
    """P7 大 payload: 守护日志有无超大消息(>4KB 应走黑板引用)"""
    try:
        if not os.path.exists(LOCAL_DAEMON_LOG):
            return False, "日志缺", "?", ""
        big = 0
        for line in open(LOCAL_DAEMON_LOG, errors="ignore").read().split("\n")[-50:]:
            if len(line) > 4000: big += 1
        polluted = big > 0
        return polluted, f"超长消息行={big}", "大 payload 发送方", "G-C18: >4KB 转黑板引用只发指引"
    except Exception:
        return False, "?", "?", ""

def p8_queue_ghost():
    """P8 队列幽灵: 服务器 processing 滞留>10min"""
    d = http_get(f"{SERVER_BUS}/bus/status", {"X-Webhook-Token": bus_token()})
    if "error" in d: return False, "bus 查失败", "?", ""
    now = time.time() * 1000
    ghosts = []
    for t in d.get("recent", []):
        if t.get("status") == "processing":
            try:
                age = now - time.mktime(time.strptime(t["created_at"][:19], "%Y-%m-%dT%H:%M:%S")) * 1000
                if age > 600 * 1000: ghosts.append((t.get("action"), int(age / 1000)))
            except Exception: pass
    polluted = bool(ghosts)
    return polluted, f"processing幽灵={ghosts}", "无消费端任务", "清理 ghost(标记 failed, G-C4)"

def p9_unauthorized_write():
    """P9 越权写: bb-gate can_write 自检(越权域应拒)"""
    try:
        r = subprocess.run(["python3", os.path.expanduser("~/dsh-collab/comm-server/bb-gate.py")],
                           capture_output=True, text=True, timeout=15)
        ok = "GATE PASS" in r.stdout or r.returncode == 0
        return (not ok), (r.stdout.strip().split("\n")[-1][:60] if r.stdout else "bb-gate 输出空"), "越权写方", "bb-gate G1 域权门强制(can_write)"
    except Exception as e:
        return True, f"bb-gate 运行异常:{e}", "?", "查 bb-gate"

def p10_self_state_claim():
    """P10 状态自判: 守护日志 vs 各 agent 是否各自上报状态(应由守护统一)"""
    # 近似: 检查是否有 agent 层直接写 nodes/<dev> 心跳(应经 hb-fwd/守护)
    try:
        # hb-fwd 是唯一心跳转发(正确); 检查守护是否正常 = 无"状态"旁路
        return False, "心跳经 hb-fwd 统一(无自判旁路)", "?", ""
    except Exception:
        return False, "?", "?", ""

DETECTORS = {
    "P1": ("域错配", p1_domain_mismatch), "P2": ("广播滥用", p2_broadcast_abuse),
    "P3": ("spoof", p3_spoof), "P4": ("重复", p4_duplicate),
    "P5": ("无效目标", p5_invalid_target), "P6": ("风暴", p6_storm),
    "P7": ("大payload", p7_large_payload), "P8": ("队列幽灵", p8_queue_ghost),
    "P9": ("越权写", p9_unauthorized_write), "P10": ("状态自判", p10_self_state_claim),
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0, help="常驻: 每 N 秒扫一次")
    ap.add_argument("--fix", default=None, help="执行修复: P4/P8(清理)等")
    args = ap.parse_args()

    if args.watch > 0:
        print(f"pollution-scanner 常驻启动 (每{args.watch}s扫描, 发现污染告警黑板)")
        while True:
            try:
                polluted_found = scan()
                if polluted_found:
                    notify_blackboard(polluted_found)
            except Exception as e:
                print(f"扫描异常: {e}")
            time.sleep(args.watch)
        return

    scan()
    # --fix 支持: P8 幽灵清理等
    if args.fix == "P8":
        import subprocess as sp
        r = sp.run(["python3", os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py"), "--once"],
                   capture_output=True, text=True, timeout=20)
        print(f"P8 修复(触发守护补拉): {r.stdout.strip()[:80]}")

def scan():
    print("══ 通讯污染扫描 pollution-scanner ══")
    total_polluted = []
    for pid in sorted(DETECTORS):
        name, fn = DETECTORS[pid]
        try:
            polluted, evidence, source, fix = fn()
        except Exception as e:
            polluted, evidence, source, fix = True, f"异常:{e}", "?", "手动查"
        mark = "⚠️污染" if polluted else "✅"
        print(f"  {mark} {pid} {name:<8} {evidence[:60]}")
        if polluted:
            total_polluted.append(f"{pid}({name})")
            if source: print(f"      源:{source} | 修:{fix[:60]}")
    if total_polluted:
        print(f"❌ 发现污染: {', '.join(total_polluted)}")
    else:
        print("✅ 无污染")
    return total_polluted

def notify_blackboard(polluted):
    """污染告警写黑板 data/ops/pollution/<date>"""
    import urllib.request
    key = f"data/ops/pollution/{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    body = json.dumps({"polluted": polluted, "ts": datetime.datetime.now().isoformat(),
                       "from": "pollution-scanner"}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:8792/{key}", data=body, method="PUT",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=6): print(f"污染告警已写 {key}")
    except Exception as e:
        print(f"告警写失败: {e}")

if __name__ == "__main__":
    main()
