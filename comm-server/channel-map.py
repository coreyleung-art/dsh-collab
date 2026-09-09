#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""channel-map.py — 设备间通道路径测绘（区分 Tailscale / 服务器 / 本机）
用户 2026-09-08 指出：一直混淆设备间走 TS 还是服务器路径 → 需工具清晰区分。

输出：每对设备 × 每条通道 = {路径: tailscale|server|local, 端点, 用途}
路径判定依据（实测, 非猜测）：
  tailscale: 对端 IP 属 100.x 网段 (tailnet)
  server:    对端 = xingqiao 106.53.214.108 (公网)
  local:     127.0.0.1 (本机回环)

用法:
  python3 channel-map.py           # 全量测绘
  python3 channel-map.py --live    # 含当前 ESTABLISHED 连接实测
"""
import os, re, socket, subprocess, sys

TS_RE = re.compile(r"100\.(?:1[0-9]{2}|[1-9][0-9]?)\.")
SERVER_IP = "106.53.214.108"
# mac-mini 黑板/SSE/星台桥/SystemGraph
MAC_MINI = {"bb": 8792, "sse": 8803, "bus": 8791, "sb": 8820, "sg": 8798}

def classify(ip):
    if ip.startswith("127."): return "local"
    if ip.startswith("100."): return "tailscale"
    if ip == SERVER_IP: return "server"
    return "other(" + ip + ")"

def route_to(ip, port):
    """实测到某 IP:port 走哪个接口"""
    try:
        r = subprocess.run(["route", "-n", "get", ip], capture_output=True, text=True, timeout=5)
        for line in r.stdout.split("\n"):
            if "interface" in line: return line.split(":")[-1].strip()
    except Exception: return "?"
    return "?"

def live_connections():
    """当前 ESTABLISHED 跨设备连接（区分 TS/服务器）——只保留关键设备流量"""
    rows = []
    # 关键进程：黑板/SSE/桥/守护/同步
    key_procs = re.compile(r"rust-blac|node|dsh-tools|device-daemon|sync-|central|bb-sub|Python|CLD", re.I)
    key_ips = re.compile(r"100\.1[0-9]{2}\.|106\.53\.|coreymac")
    noise = re.compile(r"rapportd|identitys|Universal|AweSun|WeType|Coze|WeChat|Chrome|Google|Spotify|Dropbox")
    try:
        out = subprocess.run(["lsof", "-nP", "-iTCP", "-sTCP:ESTABLISHED"],
                             capture_output=True, text=True, timeout=10).stdout
        for line in out.split("\n")[1:]:
            parts = line.split()
            if len(parts) < 9: continue
            proc = parts[0]
            if noise.search(proc): continue
            if not key_procs.search(proc): continue
            conn = parts[8] if len(parts) > 8 else ""
            if "->" not in conn: continue
            remote = conn.split("->")[1]
            if ":" not in remote: continue
            rip = remote.rsplit(":", 1)[0].strip("[]")
            rport = remote.rsplit(":", 1)[1]
            if rip.startswith("127."): continue
            if not key_ips.search(rip): continue
            rows.append((proc, parts[1], rip, rport, classify(rip)))
    except Exception as e:
        rows.append(("lsof-error", str(e)[:60], "", "", ""))
    return rows

def probe_conn(name, ip, ports, note):
    """对端连通性探测"""
    rows = []
    for pname, port in ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            sock.connect((ip, port))
            rows.append((name, f"{ip}:{port}", pname, "可达", classify(ip), route_to(ip, port)))
        except Exception as e:
            rows.append((name, f"{ip}:{port}", pname, "不可达(" + str(e)[:15] + ")", classify(ip), route_to(ip, port)))
        finally:
            sock.close()
    return rows

def main():
    live = "--live" in sys.argv
    print("=" * 78)
    print("设备通道测绘 channel-map  v1 · 路径: tailscale(100.x) / server(106.53) / local(127)")
    print("=" * 78)

    # 1. 设计通道表（按架构定, 谁该走哪）
    print("\n【设计通道】(架构应然)")
    print(f"{'通道':<38}{'路径':<12}{'端点'}")
    design = [
        ("i9/MBP → mac 实时(黑板SSE)", "tailscale", "100.120.203.20:8803"),
        ("i9/MBP → mac 直连黑板", "tailscale", "100.120.203.20:8792"),
        ("全设备 → 服务器信封bus", "server", "106.53.214.108:8791"),
        ("全设备 → 服务器黑板", "server", "106.53.214.108:8792"),
        ("心跳转发(hb-fwd)", "server", "mac-mini→106.53.214.108:8792"),
        ("Funnel 公网入口", "tailscale", "coreymac-mini.taild3fd86.ts.net"),
        ("本机 agent 互通", "local", "127.0.0.1:8792"),
    ]
    for name, path, ep in design:
        print(f"{name:<38}{path:<12}{ep}")

    # 2. 实测连通
    print("\n【实测连通】")
    rows = []
    # mac-mini 到服务器（公网）
    rows += probe_conn("mac-mini→server", SERVER_IP, {"bus": 8791, "bb": 8792, "sse": 8803}, "")
    # 本机黑板
    rows += probe_conn("mac-mini→local", "127.0.0.1", MAC_MINI, "")
    print(f"{'链路':<22}{'端点':<28}{'服务':<6}{'结果':<20}{'路径':<12}{'接口'}")
    for r in rows:
        print(f"{r[0]:<22}{r[1]:<28}{r[2]:<6}{r[3]:<20}{r[4]:<12}{r[5]}")

    # 3. 实时连接（--live）
    if live:
        print("\n【当前 ESTABLISHED 跨设备连接】")
        lc = live_connections()
        if not lc or lc[0][0] == "lsof-error":
            print("  (无或 lsof 不可用)")
        for p, pid, rip, rport, path in lc:
            print(f"  {p:<12} pid={pid:<7} → {rip}:{rport:<6} [{path}]")

    print("\n" + "=" * 78)
    print("判读: 实时消息(SSE/黑板直连)=tailscale; 信封队列/心跳/注册=server; 本机agent=local")
    print("注意: 守护轮询 server 为短连接(5s), 非 ESTABLISHED 常态——看设计表即可")
    print("=" * 78)

if __name__ == "__main__":
    main()
