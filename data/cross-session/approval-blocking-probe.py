#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
approval-blocking-probe.py — 跨设备统一口径的「审批阻塞」取证探针

背景：MBP(session-20b800d4) 调查审批阻塞时我先用了 `grep` 按字节匹配
      `approval/asked`，结果把"我自己写的散文"（文档/消息里讨论审批的文本）
      也算成了事件，虚高到 32 次未裁决；正确口径只有 1 次。
      ⇒ 本探针**只解析 JSON 顶层 `type` 字段**，不做字节匹配。

用法:
    python3 approval-blocking-probe.py            # 自动找 ~/.dsh/sessions
    python3 approval-blocking-probe.py <sessions目录>

输出：可直接回贴的一段报告（含口径声明，避免各机口径不一致）。
依赖：仅标准库。.zstd 日志需要 zstd 可执行文件；没有则跳过该文件并声明。
"""
import json, os, sys, glob, collections, datetime, subprocess, shutil

ZSTD_CANDIDATES = ["zstd", "/opt/homebrew/bin/zstd", "/usr/local/bin/zstd",
                   r"C:\Program Files\zstd\zstd.exe"]

def find_zstd():
    for c in ZSTD_CANDIDATES:
        if os.path.sep in c or "\\" in c:
            if os.path.exists(c): return c
        else:
            w = shutil.which(c)
            if w: return w
    return None

def iter_lines(path, zstd):
    """流式产出日志行（内存安全：绝不整文件读入）"""
    if path.endswith(".zstd"):
        if not zstd: return
        p = subprocess.Popen([zstd, "-dc", path], stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL)
        try:
            for line in p.stdout: yield line
        finally:
            p.stdout.close(); p.wait()
    else:
        with open(path, "rb") as f:
            for line in f: yield line

def scan(path, zstd):
    c = collections.Counter(); asks = {}; decided = set(); last_policy = None
    for raw in iter_lines(path, zstd):
        if b"approval/" not in raw and b"turn/" not in raw:
            continue                      # 廉价预筛（真正的判据在下面）
        try:
            o = json.loads(raw)
        except Exception:
            continue
        t = o.get("type", "")
        if not isinstance(t, str): continue
        if not (t.startswith("approval/") or t.startswith("turn/")):
            continue                      # ★ 只认顶层 type，杜绝散文误计
        c[t] += 1
        d = o.get("data") or {}
        if t == "approval/asked":
            asks[d.get("id")] = (o.get("time"), d.get("toolName"), d.get("callId"))
        elif t == "approval/decided":
            decided.add(d.get("id"))
        elif t == "approval/policy":
            last_policy = d.get("policy")
    unpaired = [v for k, v in asks.items() if k not in decided]
    return c, len(asks), len(decided), unpaired, last_policy

def header_meta(path, zstd):
    """读首行拿 delegationDepth / parentSession（判断根会话 vs 子代理）"""
    for raw in iter_lines(path, zstd):
        try: return json.loads(raw)
        except Exception: return {}
    return {}

def main():
    base = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.dsh/sessions")
    zstd = find_zstd()
    if not os.path.isdir(base):
        print("目录不存在: %s" % base); return 2
    files = []
    for root, dirs, fs in os.walk(base):
        for f in fs:
            if f.startswith("session.jsonl"):
                files.append(os.path.join(root, f))
    files.sort(key=lambda p: -os.path.getsize(p))

    print("=" * 78)
    print("审批阻塞取证 · 口径声明")
    print("=" * 78)
    dev = os.uname().nodename if hasattr(os, "uname") else os.environ.get("COMPUTERNAME", "?")
    print("设备      : %s" % dev)
    print("会话目录  : %s" % base)
    print("日志文件  : %d 个" % len(files))
    print("zstd      : %s" % (zstd or "缺失（.zstd 日志将被跳过）"))
    print("★ 统计口径 : 解析每行 JSON 的顶层 `type` 字段；")
    print("            不按字节匹配关键词（否则会把'讨论该日志的散文'误计为事件）。")
    print()

    tot = collections.Counter(); per = []
    for p in files:
        c, na, nd, unp, pol = scan(p, zstd)
        if not c: continue
        tot.update(c)
        meta = header_meta(p, zstd)
        per.append({"sid": os.path.basename(os.path.dirname(p)),
                    "depth": meta.get("delegationDepth"),
                    "parent": meta.get("parentSession"),
                    "size_mb": os.path.getsize(p) / 1e6,
                    "asked": na, "decided": nd, "unpaired": unp,
                    "policy": pol,
                    "turn_start": c.get("turn/start", 0),
                    "turn_end": c.get("turn/end", 0)})

    print("【全局】approval/asked = %d ; approval/decided = %d ; 未裁决 = %d"
          % (tot.get("approval/asked", 0), tot.get("approval/decided", 0),
             tot.get("approval/asked", 0) - tot.get("approval/decided", 0)))
    print("【全局】turn/start = %d ; turn/end = %d ; 未闭合 = %d"
          % (tot.get("turn/start", 0), tot.get("turn/end", 0),
             tot.get("turn/start", 0) - tot.get("turn/end", 0)))
    print("【全局】approval/policy 事件 = %d" % tot.get("approval/policy", 0))
    pol = collections.Counter(x["policy"] for x in per if x["policy"])
    print("【全局】会话最终策略分布 = %s" % dict(pol))
    print()

    print("-" * 78)
    print("【★ 关键判据】有'审批未裁决'或'回合未闭合'的会话")
    print("-" * 78)
    hit = [x for x in per if x["asked"] or x["turn_start"] - x["turn_end"] != 0]
    hit.sort(key=lambda x: -(x["unpaired"] if isinstance(x["unpaired"], int) else 0))
    if not hit:
        print("  （无）→ 本机**没有**可观测的审批阻塞痕迹")
    for x in hit[:15]:
        print("  %s  depth=%s parent=%s" % (x["sid"][:44], x["depth"], "有" if x["parent"] else "无"))
        print("     asked=%d decided=%d 未裁决=%d | turn start=%d end=%d 未闭合=%d | policy=%s | %.1fMB"
              % (x["asked"], x["decided"], len(x["unpaired"]),
                 x["turn_start"], x["turn_end"], x["turn_start"] - x["turn_end"],
                 x["policy"], x["size_mb"]))
        if x["unpaired"]:
            tm = [u[0] for u in x["unpaired"] if u and u[0]]
            tools = collections.Counter(u[1] for u in x["unpaired"] if u)
            if tm:
                print("       未裁决时间: %s → %s | 工具=%s"
                      % (datetime.datetime.fromtimestamp(min(tm)/1000),
                         datetime.datetime.fromtimestamp(max(tm)/1000), dict(tools)))
    print()
    print("【判读指引】")
    print("  · 未裁决 > 0 或 未闭合 > 0 ⇒ 存在审批阻塞痕迹，请附具体会话 id 与时间")
    print("  · 全为 0 ⇒ 本机无审批阻塞（请一并回报，'没有'同样是有效情报）")
    print("  · 策略=never 请注明是根会话还是子代理（子代理默认 never 属设计使然）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
