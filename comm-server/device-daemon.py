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

# v0.3.5: 信封文本提取——**禁止静默截断**
# 旧实现：`payload.get("text") or payload.get("msg") or json.dumps(payload, ensure_ascii=False)[:500]`
#   → 无 text/msg 的信封（如 MBP 的 note 型）会把**序列化后的 JSON 从中间砍断**：
#     · 内嵌 JSON 未闭合，接收方无法解析
#     · 尾部内容无声丢失，且**无任何截断标记**——接收方会以为消息是完整的
#   实测（2026-09-11）：卡 `notes/mac-mini/bus-subagent-burst-supplement-v2-6a542782`
#   尾部正好断在「会话固定开销 」，丢掉的恰是「未核验项（诚实标注）」整段。
# 新实现：① 限值放宽到 4000（黑板本身能存数千字符，实测 2382 字符卡完整落盘）
#         ② 确需截断时**在字符串内部截断并附显式标记**，保证落盘 JSON 始终可解析、且读者看得出被截断。
_ENV_TEXT_LIMIT = 4000


def _envelope_text(payload):
    """提取信封正文；不静默截断（详见上方说明）。"""
    t = payload.get("text")
    if t is None:
        t = payload.get("msg")
    if t is not None:
        return t
    try:
        dump = json.dumps(payload, ensure_ascii=False)
    except Exception:
        dump = str(payload)
    if len(dump) <= _ENV_TEXT_LIMIT:
        return dump
    marker = f"…[★已截断: 原文 {len(dump)} 字符, 此处仅存前 {_ENV_TEXT_LIMIT}, 请向发送方索要全文]"
    p2 = dict(payload)
    if isinstance(p2.get("note"), str) and p2["note"]:
        p2["note"] = p2["note"][:max(0, _ENV_TEXT_LIMIT - len(marker))] + marker
    else:
        p2["_truncated_dump"] = dump[:_ENV_TEXT_LIMIT] + marker
    try:
        return json.dumps(p2, ensure_ascii=False)
    except Exception:
        return dump[:_ENV_TEXT_LIMIT] + marker
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

# ===== 受控停机安全闸（deploy-safety-scheme §8，用户明令 2026-09-10）=====
# 背景：MBP 曾未经确认两次远程重启 mac-mini 的 CLD，打断了那边的活跃会话。
# 设计：
#   本机【忙】  → 立即回 allow:false（fail-closed，不写黑板、不唤醒 agent）
#   本机【不忙】→ 走正常链路唤醒本机 agent，由 agent 表态
# 守护**永不代答 allow:true** —— 只有该设备的 agent/人有权说"可以关我"。
RESTART_ACTIONS = ("controlled-restart-request", "shutdown-request", "cld-restart-request")
RESTART_BUSY_MIN = float(os.environ.get("RESTART_BUSY_MIN", "3"))


def _local_activity():
    """本机活跃度探测。返回 (busy, recent, ok)

    **ok 是关键**：ok=False 表示"无法确定"（读不到会话目录/mtime 取不到），
    与"确实没有活跃会话"是两件完全不同的事。
    早期版本把二者混为一谈（读不到就返回空列表）→ 被 guard-verify-gate 查出
    **静默 fail-open**：探测失败反而放行。故显式区分，由调用方 fail-closed。
    """
    import glob
    home = os.path.expanduser("~")
    now = time.time()
    busy, recent = [], []
    sdir = os.path.join(home, ".dsh", "sessions")
    if not os.path.isdir(sdir):
        return [], [], False          # 会话目录都没有 = 环境异常 = 不确定
    ok = True
    try:
        pat = os.path.join(sdir, "*", "*", "session.jsonl.zstd")
        for f in glob.glob(pat):
            try:
                age = (now - os.path.getmtime(f)) / 60.0
            except Exception:
                ok = False            # 拿不到某个 mtime → 整体判为不确定
                continue
            sid = os.path.basename(os.path.dirname(f))
            if age <= 240:
                item = {"id": sid, "age_min": round(age, 1)}
                recent.append(item)
                if age <= RESTART_BUSY_MIN:
                    busy.append(item)
    except Exception:
        ok = False
    recent.sort(key=lambda x: x["age_min"])
    return busy, recent[:8], ok


def _safe_reply(tid, result, stage):
    """回执发送的容错包装。

    回执发不出去（token 坏/网络断/服务异常）**不得影响"拦下"这个决定** ——
    闸门该拦还是要拦，只是通知不到对方而已。早期版本会让异常穿透出去，
    导致闸门既没拦成、也没回执（guard-verify-gate 用例 X3 查出）。
    """
    try:
        reply_task(tid, True, result=result, stage=stage)
        return True
    except Exception as e:
        log(f"⚠️ 受控停机车闸回执发送失败(不影响拦截): {str(e)[:100]}")
        return False


def restart_gate(task):
    """受控停机安全闸【外层保险】。返回 True=已处理(拦截) / False=放行给 agent 表态

    外层只做两件事：① 非停机类动作一律不干预 ② **内部任何异常都 fail-closed**。
    绝不因闸门自身出错而静默放行 —— 这正是 guard-verify-gate 用例 X2/X3 查出的缺陷。
    """
    if task.get("action", "") not in RESTART_ACTIONS:
        return False
    try:
        return _restart_gate_inner(task)
    except Exception as e:
        tid = task.get("task_id", "")
        log(f"⛔ 受控停机车闸内部异常 → fail-closed 拦下: {str(e)[:100]} (task {tid[:8]})")
        _safe_reply(tid, {
            "allow": False, "node": NODE,
            "reason": f"闸门内部异常，按 fail-closed 拒绝: {str(e)[:80]}",
            "internal_error": True,
            "hint": "请在本机排查 device-daemon 日志后再决定",
        }, "denied")
        return True


def _restart_gate_inner(task):
    """受控停机安全闸【主体】

    设计原则（全部经 guard-verify-gate 四象限验证）：
      · 本机【忙】        → 拦下 + 回 allow:false
      · 本机【确定不忙】  → 放行给本机 agent 表态（守护永不代答 allow:true）
      · 本机【无法确定】  → **fail-closed 拦下**（读不到 ≠ 不忙）
      · 闸门自身出任何错  → **fail-closed 拦下**（见外层 restart_gate）
    """
    tid = task.get("task_id", "")
    payload = task.get("payload") or {}
    frm = task.get("from") or payload.get("from") or ""
    action = task.get("action", "")

    # ① 无法确定活跃度 → fail-closed
    try:
        busy, recent, ok = _local_activity()
    except Exception as e:
        ok, busy, recent = False, [], []
        log(f"⚠️ 受控停机车闸活跃度探测异常: {str(e)[:80]}")

    if not ok:
        _safe_reply(tid, {
            "allow": False,
            "node": NODE,
            "reason": "无法确定本机活跃度（会话目录或 mtime 读取失败），按 fail-closed 拒绝",
            "busy": [], "recent_sessions": recent, "unknown_activity": True,
            "hint": "请在本机确认后再决定，或稍后重试",
        }, "denied")
        log(f"🛑 受控停机车闸【拒绝·无法确定活跃度】fail-closed "
            f"(task {tid[:8]}, from={frm}, action={action})")
        return True

    # ② 确定忙 → 拦下
    if busy:
        _safe_reply(tid, {
            "allow": False,
            "node": NODE,
            "reason": f"本机有活跃会话（近 {RESTART_BUSY_MIN} 分钟内仍有写入），拒绝受控重启",
            "busy": busy[:6],
            "recent_sessions": recent,
            "hint": "请等本机空闲后重试，或由用户在本机前手动决定",
        }, "denied")
        log(f"🛑 受控停机车闸【拒绝】{len(busy)} 个活跃会话 "
            f"(task {tid[:8]}, from={frm}, action={action})")
        return True

    # ③ 确定不忙 → 放行给本机 agent 表态（不代答）
    log(f"🛑 受控停机征询【放行待agent表态】本机无明显活跃 "
        f"(task {tid[:8]}, from={frm}) — 守护不代答 allow:true")
    return False


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
    text = _envelope_text(payload)
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
    # 受控停机安全闸（§8）：本机忙 → 立即拒绝；不忙 → 放行给本机 agent 表态
    if restart_gate(task):
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
    text = _envelope_text(payload)
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

# ═══ 探照灯状态机（2026-10-02 架构三期 G-C19：降级纪律 v1 机械化）═══
# 最小实现：SSE/轮询连续失败计数 → >=3 次红灯（告警+写降级卡+退避 60s）→ 成功恢复清零+恢复卡。
# 黄灯（超时但黑板可用）暂并红灯同处理；判据可机械核验：纯函数 judge_degrade(count, fail) 可单测。
DEGRADE_THRESHOLD = 3
DEGRADE_BACKOFF_S = 60

def judge_degrade(consecutive_fails, this_failed, threshold=DEGRADE_THRESHOLD):
    """探照灯判定（纯函数）：返回 (next_count, state)
    state: 'green' | 'red'（红灯=连续失败>=阈值；本次失败且达阈值=刚进红灯）"""
    if this_failed:
        n = consecutive_fails + 1
        return n, ("red" if n >= threshold else "green")
    return 0, "green"

def degrade_alert(action, count):
    """写降级/恢复卡到黑板（双板），失败仅记日志（降级卡本身失败不阻断守护）"""
    try:
        ts = int(time.time())
        key = f"data/ops/server-degrade/{ts}"
        val = {"type": "server-degrade" if action == "red" else "server-recover",
               "from": "device-daemon", "node": NODE, "ts": ts,
               "consecutive_fails": count, "threshold": DEGRADE_THRESHOLD}
        body = json.dumps(val).encode()
        # ★ 修复（2026-10-03 审计 P1）：原引用未定义变量 BB ⇒ 降级/恢复卡 NameError 永不落板
        for name, base in (("local", LOCAL_BB), ("central", CENTRAL_BB)):
            req = urllib.request.Request(base + "/" + key, data=body, method="PUT",
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5).read()
    except Exception as e:
        log(f"降级卡写入失败: {str(e)[:60]}")

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

    fails = 0
    was_red = False
    while True:
        resp = None
        failed_this = False
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
            failed_this = True
            try:
                t = receive_once()
                if t: process_task(t, seen)
            except Exception as e2:
                log(f"补拉失败: {str(e2)[:60]}")
        finally:
            try:
                if resp: resp.close()
            except Exception: pass
        # ★ 探照灯状态机（G-C19）：连续失败≥3 → 红灯（告警+退避）；恢复 → 绿灯+恢复卡
        fails, state = judge_degrade(fails, failed_this)
        if state == "red" and not was_red:
            log(f"🚦 探照灯红灯：连续失败 {fails} 次（阈值 {DEGRADE_THRESHOLD}），写降级卡 + 退避 {DEGRADE_BACKOFF_S}s")
            degrade_alert("red", fails)
            was_red = True
        if state == "green" and was_red:
            log("🚦 探照灯恢复绿灯：服务器重连成功，写恢复卡")
            degrade_alert("recover", 0)
            was_red = False
        wait = args.interval if args.interval > 0 else 3
        if was_red:
            wait = DEGRADE_BACKOFF_S  # 红灯退避，防重试风暴（降级纪律 v1 2.1）
        time.sleep(wait)

if __name__ == "__main__":
    main()
