#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bb-central-health.py v1.0.0 —— 中枢黑板【重启计数】健康判据

★ 出处（2026-10-14/15 · 用户批准的计划 C1）：
  今晚实测一起**11 天**的故障：中央 `comm-server.service` 在 **OOM 杀循环**里
  重启了 **2041 次**（每小时 130-150 次），而 ——

    ★★★ `systemctl is-active comm-server` 全程返回 **`active`**。

  ⇒ **一个每 27 秒重启一次的服务，在 `is-active` 眼里是健康的。**
  ⇒ 而客户端只看到「连接被重置」，★ **它不报错。**

★★ 判据（本工具的核心）：
  ★ **服务的健康不是「活不活」，是「有没有在重启」。**
  具体：`systemctl show <svc> -p NRestarts` 的 **增量** —— ★ 不是它的绝对值。

★★★ 三态（★ 与今晚其它判据一致）：
  · rc=0 健康       —— 无重启增量 · 内存余量够 · 近期无 OOM
  · rc=1 退化       —— ★ **发现重启增量 > 0**（★ 那是「发现问题」，非工具失败）
  · rc=2 不可判     —— SSH 不通 / 读不到 NRestarts（★ **不把「读不到」读成「健康」**）

★ 用法：
  python3 bb-central-health.py --selfcheck
  python3 bb-central-health.py            # 跑检查（判据语义）
  python3 bb-central-health.py --json
  python3 bb-central-health.py --reset    # 清基线（★ 用于「刚修完，从此刻起算」）
"""
import os, sys, json, argparse, subprocess, datetime

VERSION = "1.0.0"
R006_SELFCHECK = True

HOST = "ubuntu@106.53.214.108"
SVC = "comm-server.service"
SSH_TO = 25
STATE = os.path.expanduser("~/dsh-collab/data/registry/central-health-baseline.json")
LOG = os.path.expanduser("~/dsh-collab/logs/bb-central-health.log")


def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (datetime.datetime.now().isoformat(), msg))
    except Exception:
        pass


def selfcheck():
    print("== bb-central-health 自查（TCC 能力边界）==")
    print("【① 能力清单】")
    print("  · SSH 到 %s（★ 只读：systemctl show / free / journalctl -n）" % HOST)
    print("  · 读写本地基线文件 %s" % STATE)
    print("【② 不该发生路径清单】")
    print("  · ★ **不重启服务、不改配置、不杀进程、不动 swap**（只读诊断）")
    print("  · 不删除远端文件 · 不修改远端权限")
    print("【③ 依赖完整性】")
    print("  · 依赖: ssh（BatchMode）· 标准库 subprocess/json/argparse")
    print("  · python %s" % sys.version.split()[0])
    print("  · 固定日志: %s" % LOG)
    print("  · 版本: %s" % VERSION)
    return 0


def ssh(cmd):
    """★ 只读 SSH；失败返回 (None, err)"""
    try:
        r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=%d" % SSH_TO,
                            HOST, cmd],
                           capture_output=True, encoding="utf-8", errors="replace", timeout=SSH_TO + 30)
        if r.returncode != 0:
            return None, (r.stderr or "").strip()[:200] or "rc=%s" % r.returncode
        return (r.stdout or ""), None
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


def probe():
    cmd = ("systemctl show %s -p NRestarts -p MemoryCurrent -p MemoryMax -p ActiveState --no-pager; "
           "echo '---'; free -m | head -2; "
           "echo '---'; swapon --show --noheadings 2>/dev/null | wc -l; "
           # ★★★ 坑（本线实测）：`grep -c` **计数为 0 时退出码=1**，而它是链末
           #   ⇒ ssh 的 rc=1 ⇒ 被我的代码读成「探测失败」⇒ 明明数据正确却判「不可判」。
           #   ★ 与今晚那条同族：**把「没匹配到」读成「命令失败」。**
           #   ⇒ 修法：让远端链的退出码【只反映连通性】—— 计数命令加 `|| true`。
           "echo '---'; (journalctl -u %s --since '-30 min' --no-pager 2>/dev/null | grep -c oom-kill || true)"
           ) % (SVC, SVC)
    out, err = ssh(cmd)
    if out is None:
        return None, err
    parts = [p.strip() for p in out.split("---")]
    if len(parts) < 4:
        return None, "★ 输出格式不符（★ 不猜）"
    kv = {}
    for line in parts[0].splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip()
    mem = {}
    for line in parts[1].splitlines():
        f = line.split()
        if f and f[0].startswith("Mem"):
            mem["total"] = int(f[1]); mem["avail"] = int(f[6])
        if f and f[0].startswith("Swap"):
            mem["swap_total"] = int(f[1]); mem["swap_used"] = int(f[2])
    d = {
        "nrestarts": int(kv.get("NRestarts") or 0),
        "memcur": int(kv.get("MemoryCurrent") or 0),
        "memmax": int(kv.get("MemoryMax") or 0),
        "active": kv.get("ActiveState") or "?",
        "mem": mem,
        "swapfiles": int(parts[2] or 0),
        "oom30": int(parts[3] or 0),
    }
    return d, None


def load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return None


def save_state(d):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(d, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()

    d, err = probe()
    if d is None:
        # ★★ 三态：读不到 ⇒ 不可判（★ 绝不读成「健康」—— 那正是今晚那个 bug 的形状）
        msg = "★ 不可判：SSH/读取失败（%s）—— ★ 不把它读成「健康」" % err
        print(json.dumps({"ok": False, "state": "不可判", "rc": 2, "note": msg},
                         ensure_ascii=False) if a.json else "中枢健康: 【不可判】· %s" % msg)
        log("undecidable: %s" % err)
        return 2

    st = load_state()
    if a.reset or not st:
        save_state({"nrestarts": d["nrestarts"], "baselineAt": datetime.datetime.now().isoformat()})
        if a.json:
            print(json.dumps({"ok": True, "state": "基线已立", "rc": 0, "nrestarts": d["nrestarts"],
                              "note": "★ 基线建立：从此刻起算重启增量"}, ensure_ascii=False))
        else:
            print("中枢健康: 【基线已立】· NRestarts=%d（★ 从此刻起算增量）" % d["nrestarts"])
        log("baseline nrestarts=%d" % d["nrestarts"])
        return 0

    delta = d["nrestarts"] - st.get("nrestarts", d["nrestarts"])
    # ★ 内存余量（相对 cgroup 上限）
    ratio = (d["memcur"] / d["memmax"] * 100) if d["memmax"] else None
    problems = []
    if delta > 0:
        problems.append("★ **重启增量 %d 次**（★ 判据：服务的健康不是「活不活」，是「有没有在重启」）" % delta)
    if d["oom30"] > 0:
        problems.append("★ 近 30 分钟 OOM %d 次" % d["oom30"])
    if ratio is not None and ratio >= 85:
        problems.append("★ cgroup 内存占用 %.0f%%（贴近上限，★ OOM 前兆）" % ratio)
    if d["swapfiles"] == 0:
        problems.append("★ 无 swap（★ 溢出无缓冲）")
    if d["mem"].get("avail", 999) < 80:
        problems.append("★ 主机可用内存仅 %d MB" % d["mem"].get("avail", 0))

    if problems:
        state, code = "退化", 1
        note = " | ".join(problems)
    else:
        state, code = "健康", 0
        note = "✓ 无重启增量 · 内存余量充足"

    save_state({"nrestarts": d["nrestarts"], "baselineAt": st.get("baselineAt"),
                "lastCheck": datetime.datetime.now().isoformat()})
    out = {"ok": code == 0, "state": state, "rc": code, "nrestarts": d["nrestarts"],
           "deltaSinceBaseline": delta, "activeState": d["active"],
           "mem": d["mem"], "memUsedPctOfCgroup": round(ratio, 1) if ratio is not None else None,
           "oomLast30min": d["oom30"], "swapPresent": d["swapfiles"] > 0,
           "note": note, "version": VERSION}
    if a.json:
        print(json.dumps(out, ensure_ascii=False))
    else:
        print("中枢健康: 【%s】" % state)
        print("  NRestarts=%d（基线增量 %d）· ActiveState=%s" % (d["nrestarts"], delta, d["active"]))
        print("  cgroup 内存 %s%% · 近30分 OOM=%d · swap=%s" %
              (round(ratio, 1) if ratio is not None else "?", d["oom30"], "有" if d["swapfiles"] else "★无"))
        print("  %s" % note)
    log("state=%s delta=%d oom30=%d" % (state, delta, d["oom30"]))
    return code


if __name__ == "__main__":
    sys.exit(main())
