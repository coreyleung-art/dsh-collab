#!/usr/bin/env python3
"""comm-server 心跳镜像转发器（本机 → 中枢）v1.1

v1.1（2026-10-02）修复两处「伪新鲜」缺陷（下钻实测定根因）：
  1) fwd 写时变更：设备自报 ts 未变则不 PUT。此前每 30s 无脑重镜像，服务器键体 ts
     伪新鲜、version 空转（~2880 次/天×3 键），把真实心跳断档（MBP 睡眠 18min/7min）
     完全掩盖。
  2) E2 注册表 status 按 G5 判定：读本机心跳载荷 ts，<90s=online / >=90s=offline /
     读失败=unknown。此前写死 online，断档时也显示在线；另加 hb_age_s 审计字段
     （读侧可复算判据）。注册表写入同样写时变更：仅 status 变化或 age 跨 60s 桶时写。
  3) 单次执行模式：launchd StartInterval 30s 拉起、跑完即退；跨实例记忆放
     ~/.dsh/hb-fwd-state.json（原子写：tmp+rename，I5）。
  4) --check 干跑：只打印每节点决策，不写任何键（对照实验用）。

协议 v1.0 通道不变：nodes/<node>/heartbeat · data/discovery/agents/<dev>
"""
import json, os, sys, time, urllib.request

LOCAL_BB = os.environ.get("LOCAL_BB", "http://127.0.0.1:8792")
CENTRAL_BB = os.environ.get("CENTRAL_BB", "http://xingqiao.meetfunbp.com:8792")
FORWARD_NODES = ("mbp", "i9", "mac-mini")
ONLINE_MAX_AGE_S = 90  # G5：心跳载荷 ts < 90s = online
STATE_PATH = os.path.expanduser("~/.dsh/hb-fwd-state.json")


def log(m):
    print(f"[hb-fwd] {time.strftime('%H:%M:%S')} {m}", flush=True)


# ── 原子读写 state（I5：tmp + rename）──
def load_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_PATH)


def read_local(key):
    with urllib.request.urlopen(LOCAL_BB + "/" + key, timeout=5) as r:
        return json.loads(r.read())


def _bb_auth():
    """黑板写认证 token（~/.dsh/blackboard-token 0600；无则不带头——兼容 token=off 期）"""
    try:
        with open(os.path.expanduser("~/.dsh/blackboard-token")) as f:
            return f.read().strip()
    except Exception:
        return ""

def put_local(key, val):
    # ★ 2026-10-04 MBP 558 残留修复：本机板显式写（R036 双写）+ 本机板 token
    body = json.dumps(val).encode()
    headers = {"Content-Type": "application/json"}
    try:
        with open(os.path.expanduser("~/.dsh/board-token")) as f:
            headers["Authorization"] = "Bearer " + f.read().strip()
    except Exception:
        pass
    req = urllib.request.Request(LOCAL_BB + "/" + key, data=body, method="PUT", headers=headers)
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status

def put_central(key, val):
    body = json.dumps(val).encode()
    headers = {"Content-Type": "application/json"}
    tok = _bb_auth()
    if tok:
        headers["Authorization"] = "Bearer " + tok  # ★ A1 写端鉴权预备（flip 后生效；当前 token=off 无害）
    req = urllib.request.Request(CENTRAL_BB + "/" + key, data=body, method="PUT", headers=headers)
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status


# ── 载荷时间解析（epoch 数字为主，兼容 ISO 字符串）──
def payload_ts(val):
    ts = val.get("ts")
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return int(ts)
    s = str(ts)
    if s.isdigit():
        # 纯数字字符串（node-bridge json! 把 epoch 写成字符串，实测）
        return int(s)
    import datetime
    try:
        return int(datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp())
    except Exception:
        return None


def age_s(val, now=None):
    ts = payload_ts(val)
    if ts is None:
        return None
    return max(0, int((now or time.time()) - ts))


def g5_status(age):
    """G5 活性判定：<90s=online；>=90s=offline；读不到=unknown"""
    if age is None:
        return "unknown"
    return "online" if age < ONLINE_MAX_AGE_S else "offline"


# ═══════════ 心跳镜像：写时变更 ═══════════
def fwd_once(check=False):
    state = load_state()
    changed = False
    for node in FORWARD_NODES:
        try:
            d = read_local(f"nodes/{node}/heartbeat")
            val = d.get("value") or {}
            if not val:
                log(f"fwd {node}: 本地心跳值为空，跳过")
                continue
            ts = payload_ts(val)
            if ts is not None and ts == state.get(node):
                if check:
                    print(f"[check] fwd {node}: 载荷 ts 未变（{ts}），跳过 PUT（写时变更）")
                continue
            val2 = dict(val)
            val2["_mirror"] = "mac-mini-fwd"
            if check:
                print(f"[check] fwd {node}: 载荷 ts {ts}（{age_s(val2)}s 前），将 PUT")
            else:
                st = put_central(f"nodes/{node}/heartbeat", val2)
                log(f"fwd {node} 心跳 → 中枢 (HTTP {st}, ts={ts})")
            if ts is not None:
                state[node] = ts
                changed = True
        except Exception as e:
            log(f"fwd {node} 失败: {str(e)[:60]}")
    if changed and not check:
        save_state(state)


# ═══════════ E2 注册表：G5 判定 + 写时变更 ═══════════
REGISTRY_SESSIONS = [
    {"session_id": "session-fa1f9150-c949-401f-ba8c-d265f6221676", "role": "星桥(协调者)"},
    {"session_id": "session-a190c54c-ca73-4845-9a65-9dc002d45044", "role": "明鉴(SystemGraph架构)"},
    {"session_id": "session-2a15e6b1-32a9-48b3-a167-8fe0a28e8d82", "role": "HR司库"},
]


def collect_services(dev="mac-mini"):
    """Gap 3（2026-10-02）本机组件版本采集 + R038 缺位约定（2026-10-03 MBP 提议）：
    本机（mac-mini）→ 全量采集；远端设备 → node-bridge 版本从该设备心跳 payload ver 取，
    其余必需组件写 "absent"（键在位，省略会被读侧误读为漏报）。"""
    import subprocess, glob as _glob, json as _json
    svc = {"hb-fwd": "v1.2"}
    try:
        d = read_local(f"nodes/{dev}/heartbeat")
        v = (d.get("value") or {}).get("ver")
        if v: svc["node-bridge"] = "v" + str(v)
    except Exception:
        pass
    if dev != "mac-mini":
        for label in ["dsh-tools", "agent-way", "central-inbox", "bb-card-send", "launchd-scan", "channel-gate", "drift-scan"]:
            svc.setdefault(label, "absent")
        return svc
    try:
        out = subprocess.run(["ps", "-axo", "args="], capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            m = None
            if "dsh-tools-macos-arm64" in line:
                import re
                m = re.search(r"dsh-tools-macos-arm64-v([\d.]+)", line)
            if m: svc["dsh-tools"] = "v" + m.group(1); break
    except Exception:
        pass
    for pkg, label in [("dsh-plugin-agent-bus", "agent-way"), ("dsh-plugin-central-inbox", "central-inbox"),
                       ("dsh-plugin-bb-card-send", "bb-card-send"), ("dsh-plugin-launchd-scan", "launchd-scan"),
                       ("dsh-plugin-channel-gate", "channel-gate"), ("dsh-plugin-drift-scan", "drift-scan")]:
        try:
            with open(f"{os.path.expanduser('~')}/{pkg}/package.json") as f:
                svc[label] = "v" + _json.load(f).get("version", "?")
        except Exception:
            pass
    return svc


def registry_register(check=False):
    state = load_state()
    # ★ 2026-10-04 MBP 277 修正（R035）：只写**本机** discovery 键；远端设备由其本节点心跳代理**自报**。
    #   旧实现替远端写键并把 services 标 "absent" —— 把「我观测不到」写成「它不存在」= R035 违规
    #   （我无法 SSH 出向 MBP，观测面天然不可用 ⇒ 只能自报，不能代写）。
    regs = [
        ("mac-mini", REGISTRY_SESSIONS, "self"),
    ]
    changed = False
    for dev, sessions, via in regs:
        age = None
        hb_ts = None
        try:
            d = read_local(f"nodes/{dev}/heartbeat")
            v = d.get("value") or {}
            age = age_s(v)
            hb_ts = payload_ts(v)
        except Exception as e:
            log(f"E2 {dev} 心跳读取失败: {str(e)[:50]}")
        status = g5_status(age)
        reg_key = f"reg:{dev}"
        prev = state.get(reg_key, {})
        # 写时变更：status 变化 或 心跳载荷 ts 变化。
        # 健康期心跳每 60s 变化 → 注册表随之刷新（hb_age_s 保持新鲜）；
        # 断档期心跳 ts 不变、age 增长至 >=90s → status online→offline 变化 → 落 offline；
        # offline 持续断档或读失败持续：均无变化 → 不写（不空转）。
        if prev and prev.get("status") == status and prev.get("hb_ts") == hb_ts:
            if check:
                print(f"[check] E2 {dev}: status={status} 心跳 ts={hb_ts} 均未变，跳过 PUT")
            continue
        val = {
            "device": dev, "schema": "v1", "status": status,
            "sessions": sessions,
            "heartbeat_ref": f"nodes/{dev}/heartbeat",
            "via": via, "writer_id": "hb-fwd-mac-mini", "ts": int(time.time()),
        }
        if age is not None:
            val["hb_age_s"] = age
        val["services"] = collect_services(dev)  # Gap 3 + R038 缺位约定（远端键在位值 absent）
        if check:
            print(f"[check] E2 {dev}: 心跳 {('%.0fs' % age) if age is not None else '读不到'} → status={status}，将 PUT")
        else:
            try:
                st = put_central(f"data/discovery/agents/{dev}", val)
                log(f"E2注册 {dev} → 中央发现层 (HTTP {st}, status={status}, age={age})")
            except Exception as e:
                log(f"E2注册 {dev} 中央失败: {str(e)[:60]}")
            try:
                st2 = put_local(f"data/discovery/agents/{dev}", val)
                log(f"E2注册 {dev} → 本机发现层 (HTTP {st2})")
            except Exception as e:
                log(f"E2注册 {dev} 本机失败: {str(e)[:60]}")
        state[reg_key] = {"status": status, "hb_ts": hb_ts}
        changed = True
    if changed and not check:
        save_state(state)


if __name__ == "__main__":
    if "--check" in sys.argv:
        fwd_once(check=True)
        registry_register(check=True)
    else:
        # 单次执行（launchd StartInterval 30s 拉起，跑完即退）
        fwd_once()
        registry_register()
