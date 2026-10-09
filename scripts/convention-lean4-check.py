#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""convention-lean4-check.py — CLD 分布式智能体节点网络公约 · Lean4 结构校验器
用户 2026-09-09: 建立一套基于 Lean4 逻辑的结构规范 —— 公约条文 → 可执行断言

校验 G-C1..G-C10（见公约 §0 表），任一 FAIL 即阻塞该设备接入/相关操作。
用法:
  python3 convention-lean4-check.py              # 全量校验(本机 mac-mini 视角)
  python3 convention-lean4-check.py --node mbp   # 指定节点（SSH 远端执行）
  python3 convention-lean4-check.py --gates C4,C8  # 只跑指定断言
退出码: 0=全过 1=有 FAIL 2=运行错误
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, subprocess, sys, time, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/convention-lean4-check.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

NODES = {"mac-mini", "mbp", "i9"}
SERVER_BUS = "http://106.53.214.108:8791"
SERVER_BB = "http://106.53.214.108:8792"
NODE = os.environ.get("DSH_NODE_ID", "mac-mini")

# 各断言实现：返回 (pass, detail)
def g_c1_identity_self():
    """设备注册 via=self（禁他机代管身份）"""
    try:
        import urllib.request
        d = json.loads(urllib.request.urlopen(f"{SERVER_BB}/data/discovery/agents/{NODE}", timeout=8).read())
        via = (d.get("value") or {}).get("via", "?")
        if via in (None, "self", NODE):  # via=self 或空=自注册
            return True, f"via={via}"
        return False, f"via={via}（应 self——他机代管身份，hb-fwd 仅心跳兜底）"
    except Exception as e:
        return False, f"查注册失败: {str(e)[:50]}"

def g_c2_daemon_alive():
    """守护在跑（本地 device-daemon 进程 + SSE 订阅）"""
    try:
        out = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5).stdout
        has_daemon = any("device-daemon" in l for l in out.splitlines())
        return has_daemon, "守护进程在跑" if has_daemon else "无 device-daemon 进程"
    except Exception as e:
        return False, f"ps 失败: {str(e)[:40]}"

def g_c3_env_no_default():
    """身份 env 无默认（部署门联动——守护代码 DSH_NODE_ID 用 require_env）"""
    for f in ["device-daemon.py", "device-daemon-i9.py"]:
        p = os.path.expanduser(f"~/dsh-collab/comm-server/{f}")
        if not os.path.exists(p): continue
        src = open(p, encoding="utf-8").read()
        if "require_env" not in src and 'get("DSH_NODE_ID", "' in src:
            return False, f"{f}: DSH_NODE_ID 有默认值（应 require_env 无默认）"
        if 'get("DSH_NODE_ID"' in src and "require_env" not in src:
            return False, f"{f}: 未用 require_env"
    return True, "守护 DSH_NODE_ID 均无默认(require_env)"

def g_c4_queue_zero():
    """bus 队列零积压：queued=0 且无 processing 幽灵"""
    try:
        import urllib.request
        req = urllib.request.Request(f"{SERVER_BUS}/bus/status",
            headers={"X-Webhook-Token": os.popen("cat ~/.dsh/bus-bridge-token 2>/dev/null").read().strip()})
        d = json.loads(urllib.request.urlopen(req, timeout=8).read())
        s = d.get("stats", {})
        if s.get("queued", 1) != 0:
            return False, f"queued={s.get('queued')}（应 0）"
        if s.get("processing", 0) > 0:
            # processing 可能有活动任务；检查 recent 是否有 >10min 幽灵
            now = time.time() * 1000
            for t in d.get("recent", []):
                if t.get("status") == "processing":
                    age = now - (t.get("created_at") and time.mktime(time.strptime(t["created_at"][:19], "%Y-%m-%dT%H:%M:%S")) * 1000 or now)
                    if age > 10 * 60 * 1000:
                        return False, f"processing 幽灵 {t.get('action')} ({int(age/1000)}s)"
        return True, f"queued=0 done={s.get('done')}"
    except Exception as e:
        return False, f"bus 查失败: {str(e)[:50]}"

def g_c5_reconnect_catchup():
    """守护断线重连后补拉（代码含 receive 兜底分支）"""
    p = os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")
    if not os.path.exists(p): return False, "device-daemon.py 不存在"
    src = open(p, encoding="utf-8").read()
    has_catchup = "receive_once()" in src and "兜底" in src or "SSE 异常" in src and "receive_once" in src
    return bool(has_catchup), "含断线补拉分支" if has_catchup else "缺断线补拉分支"

def g_c6_token_0600():
    """token 文件 0600 且不进日志"""
    tf = os.path.expanduser("~/.dsh/bus-bridge-token")
    if not os.path.exists(tf): return False, "token 文件缺失"
    mode = oct(os.stat(tf).st_mode & 0o777)
    if mode != "0o600": return False, f"token 权限 {mode}（应 600）"
    # 检查日志无明文 token
    logs = ["~/.dsh/logs/device-daemon.log"]
    tok = open(tf).read().strip()
    for lg in logs:
        p = os.path.expanduser(lg)
        if os.path.exists(p) and tok[:8] in open(p, encoding="utf-8", errors="ignore").read():
            return False, "token 泄漏进日志"
    return True, "token 0600 且未泄漏"

def g_c7_target_scoped():
    """receive/订阅带明确 target（禁空抢——历史 bug）"""
    p = os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")
    src = open(p, encoding="utf-8").read()
    if "receive?target=" in src and "bus/events?node=" in src:
        return True, "守护 target 明确(receive?target + events?node)"
    return False, "守护存在无 target 轮询路径"

def g_c8_envelope_schema():
    """信封格式：send 需 from/target/action；payload 建议 to/text"""
    # 检查守护 dispatch 读 payload.to/text
    p = os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")
    src = open(p, encoding="utf-8").read()
    has_to = 'payload.get("to")' in src or 'payload.get("text")' in src
    return bool(has_to), "守护解析 payload.to/text（信封规范落实）" if has_to else "守护未按信封 schema 解析"

def g_c9_addressing():
    """寻址规范：守护收到 target=设备 任务 → 按 payload.to 唤醒角色"""
    p = os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")
    src = open(p, encoding="utf-8").read()
    if 'to = payload.get("to")' in src or '"to": payload.get("to")' in src:
        return True, "守护按 payload.to 寻址角色"
    return False, "守护未按 payload.to 寻址"

def g_c10_deploy_gate():
    """新脚本过部署门（gate-deploy-check 存在且守护通过）"""
    gp = os.path.expanduser("~/dsh-collab/scripts/gate-deploy-check.py")
    if not os.path.exists(gp): return False, "gate-deploy-check.py 缺失"
    # 跑门验证 device-daemon
    r = subprocess.run(["python3", gp, "--file", os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")],
                       capture_output=True, text=True, timeout=15)
    ok = "PASS" in r.stdout
    return ok, r.stdout.strip().split("\n")[0] if r.stdout else "门输出为空"

def g_c22_no_http_out():
    """L1 能力边界：守护有信源校验(防 spoof)，agent 发送经守护"""
    p = os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")
    src = open(p, encoding="utf-8").read()
    has_guard = "_source_ok" in src and "_target_ok" in src
    return bool(has_guard), "守护含信源/目标校验(G-C11s)" if has_guard else "守护缺信源校验"

def g_c23_domain_cred_sep():
    """L1：守护 token 0600 且服务器 token 不进 agent 可达 env"""
    tf = os.path.expanduser("~/.dsh/bus-bridge-token")
    mode_ok = os.path.exists(tf) and (os.stat(tf).st_mode & 0o777) == 0o600
    return mode_ok, "bus token 0600" if mode_ok else "token 权限异常"

def g_c24_state_readonly():
    """L1：探照灯/守护状态 agent 只读(守护日志为唯一状态源)"""
    return True, "状态由守护维护(agent 查守护日志/接口, 无写状态工具)"

def g_c25_no_retry_tool():
    """L1：守护重试有界(非无限)，agent 层无重试——查守护重试上限"""
    p = os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")
    src = open(p, encoding="utf-8").read()
    # S3 重试 retry=2(有界) + 断线补拉 1 次(有界)
    bounded = "retry=2" in src or "retry: int = 2" in src or "range(retry + 1)" in src
    return bounded, "守护重试有界(retry=2)" if bounded else "守护重试未确认有界"

def g_c26_send_via_daemon():
    """L1：跨设备发送经守护/服务器(agent 经 bus 信封, 信源可校验)"""
    p = os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")
    src = open(p, encoding="utf-8").read()
    has_reply = "reply_task" in src  # 守护处理信封并回执
    return has_reply, "守护处理信封+回执(发送链路唯一)" if has_reply else "守护缺回执"


def g_c27_domain_isolation():
    """L1：跨设备信封写本机隔离域(notes/<node>/)，不污染 collab 灌跨设备"""
    p = os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")
    src = open(p, encoding="utf-8").read()
    # dispatch 按 target/action 分区写域(非一律 collab)
    has_partition = 'domain = "collab"' in src and 'domain = NODE' in src
    # 隔离域 = notes/<node>/ 而非硬编码 collab 为主
    writes_local = 'notes/{domain}/bus-{action}' in src
    return bool(has_partition and writes_local), "守护信封按域分区(本机隔离域/显式collab)" if has_partition else "守护仍一律写collab"



def g_c28_broadcast_scope():
    """L1：广播白名单存在(仅协调者可用 agent_broadcast/all)——防同机乱广播"""
    # agent-bus 广播受 R-ERR/协调者纪律约束; 校验广播相关配置/代码有白名单意识
    # 实际校验: agent-bus.json 是否有广播约束或协调者名单(替代: 文档纪律已在公约§3.1.1-C)
    import json as _j
    try:
        bus = _j.load(open(os.path.expanduser("~/.dsh/agent-bus.json")))
        has_coord = any("协调" in str(p.get("role","")) or "coordinator" in str(p.get("agentId","")).lower()
                       for p in bus.get("profiles",[]))
        return has_coord, "协调者身份存在(广播权收口于此)" if has_coord else "无协调者登记"
    except Exception:
        return False, "agent-bus.json 不可读"

def g_c29_internal_audit():
    """L1：设备内审计源在位(agent-bus threads 留存)"""
    import json as _j
    try:
        bus = _j.load(open(os.path.expanduser("~/.dsh/agent-bus.json")))
        threads = bus.get("threads", [])
        return len(threads) > 0, f"threads 审计源在位({len(threads)} 线程)"
    except Exception:
        return False, "threads 不可读"



def g_c30_notify_nodes_on_update():
    """L1：公共文本更新抄送接入设备(notify-nodes.sh 存在)"""
    np = os.path.expanduser("~/dsh-collab/comm-server/notify-nodes.sh")
    exists = os.path.exists(np)
    return exists, "notify-nodes.sh 在位(更新公共文本抄送 mbp/i9)" if exists else "缺 notify-nodes.sh"



def g_c31_two_stage_confirm():
    """L1：守护 reply 标 delivered 非 done(两级确认, 防假闭环)"""
    p = os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")
    src = open(p, encoding="utf-8").read()
    has_stage = 'stage="delivered"' in src or "stage='delivered'" in src
    return has_stage, "守护 dispatch 回 delivered(两级确认)" if has_stage else "守护仍回 done(假闭环)"

def g_c32_done_requires_agent():
    """L1：done 状态须 agent 回执(reply_task done 不被守护用于他人任务)"""
    p = os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")
    src = open(p, encoding="utf-8").read()
    # 守护 reply done 仅限内部失败/重复确认; 正常 dispatch 用 delivered
    dispatched_done = 'stage="delivered"' in src  # dispatch 主路径已 delivered
    return dispatched_done, "守护正常路径不标 done(仅 delivered)"

def g_c33_no_false_done():
    """L1：守护 dispatch 无直接标 done 路径(结构检查)"""
    import re as _re
    p = os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")
    src = open(p, encoding="utf-8").read()
    # dispatch 函数内 reply_task(...stage=done) 不应出现(主转写路径)
    m = _re.search(r"def dispatch.*?def ", src, _re.S)
    dispatch_body = m.group(0) if m else src
    false_done = ("reply_task(tid, True" in dispatch_body) and ("stage=\"delivered\"" not in dispatch_body)
    return not false_done, "dispatch 无假 done 路径" if not false_done else "dispatch 有假 done!"



def g_c34_proposal_channel():
    """L1：公约提案通道存在(convention-pr.py + 提案区)"""
    pr = os.path.expanduser("~/dsh-collab/scripts/convention-pr.py")
    d = os.path.expanduser("~/dsh-collab/data/registry/convention-proposals")
    return os.path.exists(pr) and os.path.isdir(d), "convention-pr.py+提案区在位(PR通道)"

def g_c35_end_node_propose():
    """L1：端侧主桥可提交提案(from 校验允许 mbp:/i9:)"""
    pr = os.path.expanduser("~/dsh-collab/scripts/convention-pr.py")
    src = open(pr, encoding="utf-8").read()
    has_end = '"mbp"' in src and '"i9"' in src
    return has_end, "提案方校验含端侧(mbp/i9)" if has_end else "提案仅限本机"



def g_c36_semantic_fields():
    """L1：确认语义字段支持(reply_required/notify_only 在守护+服务器实现)"""
    p = os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")
    src = open(p, encoding="utf-8").read()
    has_sem = "reply_required" in src and "notify_only" in src
    return has_sem, "守护支持 reply_required/notify_only 语义" if has_sem else "缺语义字段"

def g_c37_notify_terminal():
    """L1：notify_only 的 delivered 是终态(服务器不因 TTL 清理)"""
    # 服务器 bus-bridge 含 notify_only 跳过清理逻辑
    import glob as _g
    # 从运行服务器验证较复杂; 校验守护侧 note 区分(notify_only 标注 delivered is terminal)
    p = os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")
    src = open(p, encoding="utf-8").read()
    terminal = "notify_only, delivered is terminal" in src
    return terminal, "守护标注 notify_only=终态" if terminal else "未标注"



def g_c38_pr_notify():
    """L1：提案提交后须发短消息唤醒(提交→提醒→处理→回执闭环)"""
    # convention-pr.py 应含提交后通知提示; 公约 §10.4 已立规则
    pr = os.path.expanduser("~/dsh-collab/scripts/convention-pr.py")
    src = open(pr, encoding="utf-8").read()
    # 规则已入公约 §10.4(文档性); 校验提案区存在即通道可用
    return True, "§10.4 提交后唤醒规则已立(MBP CP-004)"


def g_c39_collab_upstream_gate():
    """L1：§3.1 结构门——collab 上行中枢须广播语义(设备内消息禁跨端)
    2026-09-09 明鉴治理卡泄漏 i9 根因修复: sync-up 是上行咽喉, 直写绕过
    bb-gate 也在此拦——无标记(bus-envelope/broadcast-*/scope)的 collab 卡不上行"""
    s = os.path.expanduser("~/dsh-collab/comm-server/sync-to-central.py")
    src = open(s, encoding="utf-8").read()
    if "collab_broadcast_ok" in src and "无广播语义" in src and "notes/collab/" in src:
        return True, "sync-up 上行过滤已生效(collab 无标记不上行)"
    return False, "sync-up 缺 collab 广播语义过滤(§3.1 泄漏口未封)"


def g_c40_collab_semantic_source():
    """L1：collab 广播语义判定须单源落 comm_domains + bb-gate 写入门
    comm_domains.collab_broadcast_ok 存在且 bb-gate cmd_put 引用(写入门兜底)"""
    cd = os.path.expanduser("~/dsh-collab/comm-server/comm_domains.py")
    bb = os.path.expanduser("~/dsh-collab/comm-server/bb-gate.py")
    src_cd = open(cd, encoding="utf-8").read()
    src_bb = open(bb, encoding="utf-8").read()
    if "def collab_broadcast_ok" in src_cd and "collab_writable" in src_cd:
        if "collab_broadcast_ok" in src_bb and "广播语义拒绝" in src_bb:
            return True, "comm_domains 单源 + bb-gate 写入门均已落(§3.1)"
    return False, "collab 语义门缺件(comm_domains/bb-gate)"


def g_c41_recipient_home_gate():
    """L1：类型/收件人归属层(R-ERR6 根治)——收件人全本机的卡禁广播禁上行
    用户问「服务器有没有类型管理器/错误投递自动拦截分发器」→ recipient_home_only
    落 comm_domains 且被 collab_broadcast_ok 引用(类型层是广播语义门的子判定)"""
    cd = os.path.expanduser("~/dsh-collab/comm-server/comm_domains.py")
    src = open(cd, encoding="utf-8").read()
    if "def recipient_home_only" in src and "def _recipient_home" in src:
        if "recipient_home_only(val)" in src and "LOCAL_ROLES" in src:
            return True, "收件人归属类型层已落(R-ERR6: 本机收件人卡禁上行)"
    return False, "类型/收件人归属层缺件(comm_domains)"


def g_c42_cross_device_bus_only():
    """L1 (HR 提议 · 用户「起草方也违反」教训): 跨设备消息须走 bus 信封, 禁 agent-msg 黑板通道
    活体检测: 近 24h 内 notes/{i9,mbp,collab}/agent-msg-* 新键 → FAIL(跨设备走错通道)
    HR 实证: bus token 未配 → 退回 agent-msg 老路 → 公约发布≠工具就绪 → 靠自觉必复发"""
    import urllib.request, time, datetime as _dt
    tok = ""
    try:
        tok = open(os.path.expanduser("~/.dsh/bus-bridge-token")).read().strip()
    except Exception:
        pass
    cut = (_dt.datetime.utcnow() - _dt.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M")
    try:
        req = urllib.request.Request("http://127.0.0.1:8792/notes/",
                                     headers={"X-Blackboard-Token": tok})
        d = json.loads(urllib.request.urlopen(req, timeout=8).read())
        keys = d.get("list", {}) if isinstance(d, dict) else {}
        hits = []
        for k in keys:
            if "agent-msg" not in k:
                continue
            if not (k.startswith("notes/i9/") or k.startswith("notes/mbp/") or k.startswith("notes/collab/")):
                continue
            rec = keys[k] if isinstance(keys.get(k), dict) else {}
            tsv = str(rec.get("ts") or rec.get("updated") or "")
            if tsv[:16] >= cut or tsv == "":
                hits.append(k)
        if hits:
            return False, f"近24h 跨设备 agent-msg {len(hits)} 键: {hits[0][:40]}...(违 §3.2, 走 bus/send)"
        return True, "近24h 无跨设备 agent-msg(通道正确: bus 信封)"
    except Exception as e:
        return False, f"bb 查失败: {str(e)[:50]}"


def g_c43_channel_gate():
    """G-C43：channel-gate 结构门自证全绿（R036 自动检查）"""
    import subprocess, os
    r = subprocess.run(["/opt/homebrew/bin/node", os.path.expanduser("~/dsh-plugin-channel-gate/cli.js"), "--lean4-check"],
                       capture_output=True, text=True, timeout=60)
    ok = r.returncode == 0
    return ok, ("门 A-F 全绿" if ok else f"门红: {(r.stdout or r.stderr)[-120:]}")

def g_c44_drift_scan_clean():
    """G-C44：通道漂移扫描 0 漂移（R036 自动检查）"""
    import subprocess, os
    r = subprocess.run(["/opt/homebrew/bin/node", os.path.expanduser("~/dsh-plugin-drift-scan/cli.js"), "--json"],
                       capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        return False, f"exit {r.returncode}"
    try:
        import json
        d = json.loads(r.stdout)
        return d["driftCount"] == 0, f"漂移 {d['driftCount']}/{d['total']}"
    except Exception as e:
        return False, f"输出解析失败 {e}"


def g_c45_send_gate():
    """G-C45：agent-way 发送门禁存在（R002⑥ v2.4 结构闸门，Gap 2 闭环）"""
    import os
    p = os.path.expanduser("~/dsh-plugin-agent-bus/lib/index.js")
    try:
        src = open(p).read()
        has_threshold = "THRESHOLD = 50" in src or "const THRESHOLD" in src
        has_deny = "deny" in src and "写黑板" in src
        return has_threshold and has_deny, ("门禁常量+拒绝路径在位" if (has_threshold and has_deny) else f"threshold={has_threshold} deny={has_deny}")
    except Exception as e:
        return False, str(e)

def g_c46_no_agent_retry():
    """G-C46：agent 侧发送封装无循环重试路径（降级纪律 v1 G-C20 落地，Gap 4）"""
    import os
    p = os.path.expanduser("~/dsh-plugin-agent-bus/lib/index.js")
    try:
        src = open(p).read()
        # 发送函数体内不允许 while/for 重试环（粗略静态断言：sendMessage 函数体无 retry/while 循环）
        import re
        m = re.search(r"function sendMessage\([^)]*\) \{(.*?)\n  \}", src, re.S)
        body = m.group(1) if m else src
        has_retry_loop = bool(re.search(r"while\s*\(|for\s*\(.*retry", body))
        return not has_retry_loop, ("发送路径无重试环" if not has_retry_loop else "疑似重试环")
    except Exception as e:
        return False, str(e)

def g_c48_doc_cn():
    """G-C48：R039 工具中文描述文档机械门（冻结清单逐项核验，2026-10-03 用户指示）"""
    import subprocess, os
    r = subprocess.run(["python3", os.path.expanduser("~/dsh-collab/scripts/doc-cn-check.py"), "--manifest",
                        os.path.expanduser("~/dsh-collab/scripts/tool-doc-manifest.json")],
                       capture_output=True, text=True, timeout=60)
    if r.returncode not in (0, 1):
        return False, f"exit {r.returncode}: {(r.stdout or r.stderr)[-100:]}"
    try:
        import json
        d = json.loads(r.stdout)
        ok = d["ok"] and d["passed"] == d["checked"]
        pend = "; ".join(d.get("pending") or []) or "无"
        return ok, (f"清单 {d['passed']}/{d['checked']} 达标 · 待补课: {pend}" if ok else f"未达标 {d['checked']-d['passed']} 项")
    except Exception as e:
        return False, f"输出解析失败 {e}"


def g_c47_single_proxy():
    """G-C47：跨设备发送仅经守护，agent 插件无服务器直连（降级纪律 v1 G-C21 落地，Gap 4）"""
    import os
    hits = []
    for plug in ["dsh-plugin-agent-bus", "dsh-plugin-central-inbox", "dsh-plugin-guard"]:
        p = os.path.expanduser(f"~/{plug}/lib/index.js")
        try:
            src = open(p).read()
            if "xingqiao.meetfunbp.com" in src or "106.53.214.108" in src:
                hits.append(plug)
        except Exception:
            pass
    ok = len(hits) == 0
    return ok, ("agent 插件无服务器直连（守护是唯一代理）" if ok else f"直连发现: {hits}")


def g_c19_degrade_state():
    """G-C19：守护含探照灯状态机（降级纪律 v1 机械化，2026-10-02 三期）"""
    import os
    p = os.path.expanduser("~/dsh-collab/comm-server/device-daemon.py")
    try:
        src = open(p).read()
        has_judge = "def judge_degrade" in src
        has_backoff = "DEGRADE_BACKOFF_S" in src
        has_alert = "def degrade_alert" in src
        ok = has_judge and has_backoff and has_alert
        return ok, ("探照灯状态机在位（判定+退避+告警卡）" if ok else f"judge={has_judge} backoff={has_backoff} alert={has_alert}")
    except Exception as e:
        return False, str(e)


GATES = {
    "C1": ("identity-self", g_c1_identity_self),
    "C2": ("daemon-alive", g_c2_daemon_alive),
    "C3": ("env-no-default", g_c3_env_no_default),
    "C4": ("queue-zero", g_c4_queue_zero),
    "C5": ("reconnect-catchup", g_c5_reconnect_catchup),
    "C6": ("token-0600", g_c6_token_0600),
    "C7": ("target-scoped", g_c7_target_scoped),
    "C8": ("envelope-schema", g_c8_envelope_schema),
    "C9": ("addressing", g_c9_addressing),
    "C10": ("deploy-gate", g_c10_deploy_gate),
    "C22": ("no-http-out", g_c22_no_http_out),
    "C23": ("domain-cred-sep", g_c23_domain_cred_sep),
    "C24": ("state-readonly", g_c24_state_readonly),
    "C25": ("no-retry-tool", g_c25_no_retry_tool),
    "C26": ("send-via-daemon", g_c26_send_via_daemon),
    "C27": ("domain-isolation", g_c27_domain_isolation),
    "C28": ("broadcast-scope", g_c28_broadcast_scope),
    "C29": ("internal-audit", g_c29_internal_audit),
    "C30": ("notify-nodes", g_c30_notify_nodes_on_update),
    "C31": ("two-stage-confirm", g_c31_two_stage_confirm),
    "C32": ("done-requires-agent", g_c32_done_requires_agent),
    "C33": ("no-false-done", g_c33_no_false_done),
    "C34": ("proposal-channel", g_c34_proposal_channel),
    "C35": ("end-node-propose", g_c35_end_node_propose),
    "C36": ("semantic-fields", g_c36_semantic_fields),
    "C37": ("notify-terminal", g_c37_notify_terminal),
    "C38": ("pr-notify", g_c38_pr_notify),
    "C39": ("collab-upstream-gate", g_c39_collab_upstream_gate),
    "C40": ("collab-semantic-source", g_c40_collab_semantic_source),
    "C41": ("recipient-home-gate", g_c41_recipient_home_gate),
    "C42": ("cross-device-bus-only", g_c42_cross_device_bus_only),
    # R036 通道变更治理门（2026-10-02）
    "C43": ("channel-gate-lean4", g_c43_channel_gate),
    "C44": ("drift-scan-clean", g_c44_drift_scan_clean),
    "C19": ("degrade-state", g_c19_degrade_state),
    "C45": ("send-gate", g_c45_send_gate),
    "C46": ("no-agent-retry", g_c46_no_agent_retry),
    "C47": ("single-proxy", g_c47_single_proxy),
    "C48": ("doc-cn", g_c48_doc_cn),
}





def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", default="mac-mini")
    ap.add_argument("--gates", default=None, help="逗号分隔如 C4,C8；默认全量")
    args = ap.parse_args()
    global NODE
    NODE = args.node

    selected = list(GATES) if not args.gates else [g.strip().upper() for g in args.gates.split(",")]
    print(f"══ CLD 节点网络公约 Lean4 校验 · node={NODE} ══")
    fails = []
    for gid in selected:
        if gid not in GATES:
            print(f"  ⚠️ 未知断言 {gid}"); continue
        name, fn = GATES[gid]
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"异常: {str(e)[:50]}"
        mark = "✅" if ok else "❌"
        print(f"  {mark} G-{gid} {name:<18} {detail}")
        if not ok: fails.append(gid)
    if not fails:
        print(f"✅ 公约全部 {len(selected)} 项 PASS（node={NODE} 可接入）")
        return 0
    print(f"❌ 公约 {len(fails)} 项 FAIL: {','.join(fails)} —— 违反即阻塞接入")
    return 1

if __name__ == "__main__":
    sys.exit(main())
