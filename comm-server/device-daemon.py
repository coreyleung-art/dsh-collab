#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""device-daemon.py — mac-mini 设备守护（永续通讯收敛 S2）
桥接：服务器 bus-bridge (xingqiao:8791) 信封队列 → 本机黑板 → central-inbox 唤醒 agent

链路：
  MBP/i9/星台 POST /bus/send {from,target,action,payload}
    → 服务器队列 (target=mac-mini)
    → 本守护轮询 GET /bus/receive?target=mac-mini
    → 转写黑板 notes/collab/（或 notes/<node>/）带 value.to=payload.to（角色名）
    → central-inbox v0.2.1 角色映射 → 精确唤醒目标 agent
    → agent 处理回复 → (守护回收站) 可选回写服务器 outbox

目标约定：
  target=mac-mini      → 本机收（payload.to 决定唤醒谁：角色名/coordinator）
  target=<其他设备>     → 忽略（别的设备守护处理）

用法：
  python3 device-daemon.py --once          # 单轮轮询（测试）
  python3 device-daemon.py --interval 5    # 常驻轮询（launchd）
"""
import argparse, json, os, sys, time, datetime, urllib.request, urllib.error

# ===== 配置 =====
def require_env(name):
    """G-D2 env 契约：关键身份 env 缺失即报错退出（防静默误部署到他机）"""
    v = os.environ.get(name, "").strip()
    if not v:
        sys.stderr.write(f"❌ 缺少必需 env {name}（node-kit 部署门 G-D2）——请设置后重试\n")
        sys.exit(2)
    return v

SERVER_BUS = os.environ.get("SERVER_BUS", "http://106.53.214.108:8791")
LOCAL_BB = os.environ.get("LOCAL_BB", "http://127.0.0.1:8792")
NODE = require_env("DSH_NODE_ID")   # v0.2.2: 无默认，防漏设 env 静默当 mac-mini 跑
TOKEN_FILE = os.path.expanduser("~/.dsh/bus-bridge-token")
SEEN_FILE = os.path.expanduser("~/.dsh/comm-daemon-seen.json")
LOG_FILE = os.path.expanduser("~/.dsh/logs/device-daemon.log")
# 本机角色名白名单（唤醒目标来自 agent-role-map；coordinator=星桥中枢）
BB_TOKEN = os.environ.get("BLACKBOARD_TOKEN", "")
CENTRAL_BB = os.environ.get("CENTRAL_BB", "http://106.53.214.108:8792")  # 中枢黑板（双写用）
RELAY_TARGETS = tuple(os.environ.get("RELAY_TARGETS", "").split(","))  # 代收黑板域设备(默认空=i9已自守护, 防双写)

def log(m):
    line = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f: f.write(line + "\n")
    except Exception: pass

def bus_token():
    try: return open(TOKEN_FILE).read().strip()
    except Exception: return ""

def http_req(url, method="GET", body=None, headers=None, timeout=12):
    h = {"Content-Type": "application/json"}
    if headers: h.update(headers)
    tok = bus_token()
    if tok: h["X-Webhook-Token"] = tok
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode())
        except Exception: return {"ok": False, "errmsg": f"HTTP {e.code}"}
    except Exception as e:
        return {"ok": False, "errmsg": str(e)[:80]}

def bb_put_dual(key, value):
    """双写黑板：本机 + 中枢（i9/MBP 可能读任一库；双写保险）
    本机写失败不阻塞中枢，反之亦然"""
    ok_any = False
    # 本机
    h = {"Content-Type": "application/json"}
    if BB_TOKEN: h["X-Blackboard-Token"] = BB_TOKEN
    try:
        req = urllib.request.Request(f"{LOCAL_BB}/{key.lstrip('/')}",
            data=json.dumps(value, ensure_ascii=False).encode(), method="PUT", headers=h)
        with urllib.request.urlopen(req, timeout=8) as r:
            ok_any = True
    except Exception:
        pass
    # 中枢（CENTRAL_BB，hb-fwd 同款无鉴权写）
    try:
        req = urllib.request.Request(f"{CENTRAL_BB}/{key.lstrip('/')}",
            data=json.dumps(value, ensure_ascii=False).encode(), method="PUT",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            ok_any = True
    except Exception:
        pass
    return ok_any

def bb_put(key, value):
    h = {"Content-Type": "application/json"}
    if BB_TOKEN: h["X-Blackboard-Token"] = BB_TOKEN
    req = urllib.request.Request(f"{LOCAL_BB}/{key.lstrip('/')}",
        data=json.dumps(value, ensure_ascii=False).encode(), method="PUT", headers=h)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        log(f"黑板写失败 {key}: {str(e)[:60]}")
        return None

def load_seen():
    try: return set(json.load(open(SEEN_FILE)))
    except Exception: return set()

def save_seen(s):
    try:
        json.dump(sorted(s), open(SEEN_FILE, "w"))
    except Exception: pass

def receive_once(target=None):
    """取服务器 bus 里任务（断线重连兜底 / 黑板域设备转发用）
    target 缺省=NODE；显式传其它设备(target=i9) = 帮黑板域设备代收转发"""
    tgt = target or NODE
    r = http_req(f"{SERVER_BUS}/bus/receive?target={tgt}")
    if not r.get("ok"): return None
    return r.get("task")

def reply_task(task_id, ok, result=None, error=None, stage="done"):
    """回执服务器。G-C31 两级确认: stage=delivered(守护送达声明, 非完成) / done(agent处理完成)
    Lean4: 守护只能声明 delivered; done 须 agent 回执——防『投递=完成』假闭环"""
    r = http_req(f"{SERVER_BUS}/bus/reply", method="POST",
                 body={"task_id": task_id, "ok": ok, "result": result, "error": error,
                       "stage": stage})
    return r.get("ok", False)

# 可信信源/目标（Lean4 防 spoof：G-C11s —— 陌生 from/to 拒路由）
TRUSTED_DEVS = ("mac-mini", "mbp", "i9", "mac-mini:星桥", "server", "server:coordinator")
KNOWN_ROLES = None  # 懒加载 agent-role-map

def _known_roles():
    global KNOWN_ROLES
    if KNOWN_ROLES is None:
        try:
            m = json.load(open(os.path.expanduser("~/.dsh/agent-role-map.json")))
            KNOWN_ROLES = set(m.get("main", {}).keys()) | {"coordinator", "i9", "mbp", "mac-mini"}
        except Exception:
            KNOWN_ROLES = {"coordinator"}
    return KNOWN_ROLES

def _source_ok(frm):
    """信源校验：from 须为可信设备/角色（防伪造）"""
    if not frm: return False
    # bus:xxx 信封形式
    if frm.startswith("bus:"): frm = frm[4:]
    # 精确可信设备
    if frm in TRUSTED_DEVS: return True
    # device:role 形式 → device 段可信即可（角色映射在设备侧最终校验）
    if ":" in frm:
        dev = frm.split(":", 1)[0]
        return dev in ("mac-mini", "mbp", "i9")
    # 已知角色名（同机）——角色映射表里
    return frm in _known_roles()

def _target_ok_single(c):
    """单候选判定（供 '/' 多候选拆分复用）"""
    if not c: return False
    if c in ("coordinator", "any"): return True
    if c in ("mac-mini", "mbp", "i9"): return True
    if c in TRUSTED_DEVS: return True
    # 角色映射表内（含 星桥/明鉴/…）
    if c in _known_roles(): return True
    # device:role 形式 → device 段可信即可（与 _source_ok 对称）
    if ":" in c:
        return c.split(":", 1)[0] in ("mac-mini", "mbp", "i9")
    return False

def _target_ok(to):
    """目标校验：payload.to 须为已知角色/设备/coordinator（防投到不存在的对象）
    v0.3.4(CP-005/006 前置, i9 多候选修复): 支持 '/' 分隔多候选——
    i9 用 to=星桥/管理员 表达「星桥 或 人工管理员」：OR 语义，任一候选命中即放行
    （命中不代表广播，投递目标=首个命中候选，见 _pick_target）"""
    if not to: return False
    for cand in to.split("/"):
        if _target_ok_single(cand.strip()):
            return True
    return False

def _pick_target(to):
    """从多候选里取首个合法目标作为黑板卡 to（角色映射唤醒用）；全非法→原样返回
    保留完整候选串于 to_full 供审计——避免 星桥/管理员 整串落 to 导致角色映射失配"""
    if not to: return to
    for cand in to.split("/"):
        cand = cand.strip()
        if cand and _target_ok_single(cand):
            return cand
    return to

def dispatch(task, retry=2):
    """把服务器信封转写为黑板卡（触发 central-inbox 唤醒）
    S3: 黑板写失败 → 重试 retry 次 → 仍失败则 ACK failed + 死信告警（不静默丢）
    Lean4(G-C11s): 信源 from 不可信 / 目标 to 未知 → 拒路由 + ACK failed（防 spoof/乱投）
    G-C27 域隔离: 跨设备信封写本机 notes/mac-mini/(不上中枢, 防 collab 污染跨设备)"""
    tid = task.get("task_id", "")
    payload = task.get("payload") or {}
    # 唤醒目标：payload.to（角色名/coordinator）> task.action > 默认 coordinator
    to = payload.get("to") or payload.get("target") or "coordinator"
    # v0.3.4: '/' 多候选（星桥/管理员）→ to=首个合法候选(角色映射唤醒用), to_full=完整候选串(审计)
    to_full = to
    to = _pick_target(to)
    frm = task.get("from") or payload.get("from") or ""
    action = task.get("action", "msg")
    # v0.3.1 确认语义: reply_required(须agent级done) / notify_only(纯通知delivered即终态)
    reply_required = bool(task.get("reply_required") or payload.get("reply_required"))
    notify_only = bool(task.get("notify_only") or payload.get("notify_only"))
    text = payload.get("text") or payload.get("msg") or json.dumps(payload, ensure_ascii=False)[:500]
    ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    # G-C27: 域隔离——跨设备信封统一写本机 notes/mac-mini/（隔离域，不上中枢不灌跨设备）
    # 仅当信封显式 target=collab 或 action 以 collab- 开头才写 notes/collab/
    tgt = (task.get("target") or "").strip()
    if tgt == "collab" or action.startswith("collab-") or action.startswith("broadcast-"):
        domain = "collab"
    else:
        domain = NODE if NODE == "mac-mini" else "collab"  # mac-mini 守护写本机域；其它设备守护仍写 collab(无本地域场景暂留)
    key = f"notes/{domain}/bus-{action}-{tid[:8]}"
    val = {
        "content": f"[bus:{action}] {text}",
        "from": f"bus:{frm}",
        "key": key, "to": to, "to_full": to_full, "ts": ts,
        "type": "bus-envelope", "task_id": tid,
        # v0.3.1: 带确认语义——reply_required 卡须 agent 处理后回 done; notify_only 送达即知悉
        "reply_required": reply_required, "notify_only": notify_only,
        "_bus": {"task_id": tid, "from": frm, "action": action, "domain": domain,
                 "reply_required": reply_required, "notify_only": notify_only},
    }
    # Lean4 防 spoof：信源不可信 → 拒（不写黑板，ACK failed 留痕）
    if not _source_ok(frm):
        reply_task(tid, False, error=f"untrusted-source:{str(frm)[:30]}")
        log(f"⛔ 拒路由 不可信信源 from={str(frm)[:30]} (task {tid[:8]})")
        return None
    if not _target_ok(to):
        reply_task(tid, False, error=f"unknown-target:{str(to)[:30]}")
        log(f"⛔ 拒路由 未知目标 to={str(to)[:30]} (task {tid[:8]})")
        return None
    # S3 重试：黑板写失败重试 retry 次（bb_put 返回非 None=成功）
    wrote = False
    for attempt in range(retry + 1):
        r = bb_put(key, val)
        if r is not None:
            wrote = True
            break
        if attempt < retry:
            time.sleep(1.5 * (attempt + 1))
            log(f"黑板写重试 {attempt+1}/{retry} (task {tid[:8]})")
    if not wrote:
        # S3 死信：ACK failed + 黑板 data/ops/deadletter 告警
        reply_task(tid, False, error=f"blackboard write failed after {retry+1} attempts")
        dl_key = f"data/ops/deadletter/bus-{tid[:12]}"
        bb_put(dl_key, {"task_id": tid, "from": task.get("from"), "action": action,
                        "to": to, "text": text[:200], "ts": ts, "reason": "blackboard-write-failed"})
        log(f"⚠️ 死信: 黑板写失败 {retry+1} 次 (task {tid[:8]}) → {dl_key}")
        return None
    log(f"信封→黑板 {key} to={to} (task {tid[:8]})")
    # 两级确认: 守护只声明 delivered(送达)——agent 处理由 central-inbox 唤醒后完成
    # v0.3.1 语义: reply_required → 卡标注 agent 须回 done; notify_only → 纯通知送达即知悉
    if reply_required:
        note = f"delivered to {to}, reply_required: agent must process and ack done"
    elif notify_only:
        note = f"notified {to} (notify_only, delivered is terminal)"
    else:
        note = f"delivered to {to} via blackboard {key}"
    reply_task(tid, True, result={"note": note}, stage="delivered")
    return key

def sse_subscribe():
    """SSE 长连接订阅服务器 /bus/events?node=<本机> —— 服务器主动推，守护不轮询
    规则(用户 2026-09-08)：服务器转发时主动推给接入设备，本地 agent 不轮询。
    用 urllib 流式读（http.client 短连有 EINPROGRESS 问题）
    """
    url = f"{SERVER_BUS}/bus/events?node={NODE}"
    tok = bus_token()
    headers = {"Accept": "text/event-stream"}
    if tok: headers["X-Webhook-Token"] = tok
    req = urllib.request.Request(url, headers=headers)
    # 流式响应：不 read() 完，逐行迭代（urllib 支持 for line in response）
    resp = urllib.request.urlopen(req, timeout=None)
    log(f"SSE 已连接 {url}（推送模式，免轮询）")
    return resp

def dispatch_to_domain(task, domain):
    """把信封转写到指定黑板域 notes/<domain>/（黑板域设备如 i9 用此通道收）
    与 dispatch 不同：写 notes/<dev>/ 而非 notes/collab/——适配只读黑板域的旧设备"""
    tid = task.get("task_id", "")
    payload = task.get("payload") or {}
    action = task.get("action", "msg")
    text = payload.get("text") or payload.get("msg") or json.dumps(payload, ensure_ascii=False)[:500]
    ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    key = f"notes/{domain}/bus-{action}-{tid[:8]}"
    val = {
        "content": f"[bus:{action}] {text}",
        "from": f"bus:{task.get('from','?')}",
        "key": key, "to": payload.get("to") or domain, "ts": ts,
        "type": "bus-envelope", "task_id": tid,
        "_bus": {"task_id": tid, "from": task.get("from"), "action": action, "relayed_by": NODE},
    }
    r = bb_put_dual(key, val)
    if r:
        reply_task(tid, True, result={"note": f"relayed to blackboard {key} (delivered, not processed)"}, stage="delivered")
        log(f"信封→黑板域 notes/{domain}/ key={key} (task {tid[:8]})")
        return key
    reply_task(tid, False, error="domain-blackboard-write-failed")
    log(f"⚠️ 黑板域转发失败 notes/{domain}/ (task {tid[:8]})")
    return None

def relay_domain_devices():
    """代收黑板域设备（i9/mbp 若未接守护）的 bus 消息 → 转其黑板域
    规则：设备可两种模式接入——SSE 守护(v0.3) 或 黑板域(旧)；未接守护的走此转发"""
    relayed = 0
    for dev in RELAY_TARGETS:
        dev = dev.strip()
        if not dev: continue
        try:
            t = receive_once(target=dev)
            if t:
                dispatch_to_domain(t, dev)
                relayed += 1
        except Exception as e:
            log(f"代收 {dev} 失败: {str(e)[:60]}")
    return relayed

def process_task(t, seen):
    """处理一个任务：去重 + dispatch + 记录"""
    if not t: return
    tid = t.get("task_id", "")
    if tid and tid not in seen:
        dispatch(t)
        seen.add(tid)
        save_seen(seen)
    elif tid:
        # 已处理过但服务器还挂着 → 补 ACK 防积压
        reply_task(tid, True, result={"note": "duplicate-acked"})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=0, help="兜底轮询间隔(秒)；0=纯 SSE 推送不轮询")
    args = ap.parse_args()

    if args.once:
        t = receive_once()
        if t: dispatch(t)
        else: log(f"无待处理任务（target={NODE}）")
        return

    log(f"device-daemon 启动 node={NODE} 服务器 {SERVER_BUS}（SSE 推送模式 v0.3 + 黑板域转发）")
    seen = load_seen()

    # 独立线程：低频兜底代收黑板域设备（i9 已自部署守护则 SSE 实时优先，此仅兜断线窗口）
    import threading
    relay_run = {"stop": False}
    def relay_loop():
        while not relay_run["stop"]:
            try:
                relay_domain_devices()
            except Exception as e:
                log(f"relay 异常: {str(e)[:60]}")
            time.sleep(30)  # 低频兜底：SSE 守护设备实时收，此仅兜未上线/断线窗口
    rt = threading.Thread(target=relay_loop, daemon=True)
    rt.start()
    log(f"relay 线程启动（30s 低频兜底代收 {RELAY_TARGETS}——守护在线时其 SSE 实时优先）")

    while True:
        resp = None
        try:
            resp = sse_subscribe()
            # SSE 流：逐行读（data: {...}\n\n）
            event_buf = ""
            while True:
                line = resp.readline().decode("utf-8", "ignore")
                if not line:
                    raise RuntimeError("SSE 流断开")
                if line == "\n" or line == "\r\n":
                    # 事件边界
                    if event_buf.strip():
                        try:
                            ev = json.loads(event_buf.replace("data: ", "").strip())
                            if ev.get("type") == "new-task":
                                log(f"收到推送 {ev.get('action')} → {ev.get('target')} (task {str(ev.get('task_id'))[:8]})")
                                task = {"task_id": ev.get("task_id"), "from": ev.get("from"),
                                        "action": ev.get("action"), "payload": ev.get("payload")}
                                process_task(task, seen)
                        except Exception as e:
                            log(f"事件解析失败: {str(e)[:60]}")
                    event_buf = ""
                elif line.startswith("data:"):
                    event_buf = line[5:].strip()
                elif line.startswith("data: "):
                    event_buf = line[6:].strip()
        except Exception as e:
            log(f"SSE 异常: {str(e)[:80]} —— 兜底补拉一次后重连")
            try:
                t = receive_once()
                if t: process_task(t, seen)
            except Exception as e2:
                log(f"补拉失败: {str(e2)[:60]}")
        finally:
            try:
                if resp: resp.close()
            except Exception: pass
        wait = args.interval if args.interval > 0 else 3
        time.sleep(wait)

if __name__ == "__main__":
    main()
