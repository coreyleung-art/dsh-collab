#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-gate v1.0 — 黑板通讯写入门 (Lean4 逻辑门 · R006-⑩ 范式)

把通讯管理从规则声明升级为结构不可绕过的门：
  G1 域权写入门  can_write(role, key)          —— 越权域拒
  G2 JSON 格式门 is_valid_json_body(body)      —— 非 JSON 拒 (R003)
  G3 双写触发门  should_mirror(key, role)      —— 设备自域消息镜像中枢
  G4 状态闭环门  task_needs_ack(value)         —— 任务须回写确认
  G5 静默检测门  heartbeat_stale(ts, now, max) —— 心跳超时告警

用法:
  bb-gate check <role> <key>                  # 门校验 (写前调用, exit 0=放行)
  bb-gate put <role> <key> <json-body>        # 走门写入 (本机黑板 + 可选镜像中枢)
  bb-gate put-file <role> <key> <json-file>
  bb-gate --lean4-check                       # 断言矩阵证明门生效
  bb-gate --whoami <key>                      # 域权矩阵查询

纯函数不依赖网络 → 可单测/自检同源 (生产路径与 lean4-check 同调纯函数)。
"""
import json
import sys
import os
import urllib.request

# ═══════════ 域权矩阵 (G1) ═══════════
# 单源: comm_domains.py (与 sync 层/发现层同源; i9 白名单 notes/mbp/ 2026-09-06 用户批)
from comm_domains import can_write, should_mirror, ROLE_DOMAINS  # noqa: F401
from comm_domains import collab_broadcast_ok, collab_writable  # v1.1 §3.1 结构门

# ═══════════ JSON 格式门 (G2 · R003) ═══════════
def is_valid_json_body(body: str) -> bool:
    """G2: body 必须是合法 JSON 对象 (纯文本 → 空壳根因)"""
    if not body or not body.strip():
        return False
    try:
        v = json.loads(body)
        return isinstance(v, (dict, list))
    except Exception:
        return False


# ═══════════ 状态闭环门 (G4) ═══════════
def task_needs_ack(value: dict) -> bool:
    """G4: task 类型消息须回写确认 (无验证完成=未完成, R030)"""
    if not isinstance(value, dict):
        return False
    t = value.get("type", "")
    if t not in ("task", "urgent"):
        return False
    # 已有 reply_to/status=done 视为将闭环或已闭环
    if value.get("reply_to") or value.get("status") in ("done", "ack"):
        return False
    return True


# ═══════════ 静默检测门 (G5) ═══════════
def heartbeat_stale(ts: float, now: float, max_age: float = 90.0) -> bool:
    """G5: 心跳超时判定 (fresh=False → 静默故障检测)"""
    if not ts:
        return True
    return (now - ts) > max_age


# ═══════════ lean4-check 自检 ═══════════
def lean4_check() -> int:
    print("== R006-⑩ Lean4 约束门自检 (bb-gate 通讯写入门) ==")
    ok = True

    def gate(label, cond):
        nonlocal ok
        print(f"  [{'✅' if cond else '❌'}] {label}")
        ok = ok and cond

    # G1 域权
    gate("G1 越权域拒: i9 写 notes/mac-mini/ → 拒", not can_write("i9", "notes/mac-mini/x"))
    gate("G1 越权域拒: mbp 写 nodes/i9/ → 拒", not can_write("mbp", "nodes/i9/x"))
    gate("G1 自域放行: i9 写 notes/i9/x → 放", can_write("i9", "notes/i9/x"))
    gate("G1 协调者跨域: coordinator 写 notes/i9/x → 放", can_write("coordinator", "notes/i9/x"))
    gate("G1 未知角色拒: ghost 写任何 → 拒", not can_write("ghost", "notes/collab/x"))
    # G2 格式
    gate("G2 纯文本拒: body='hello' → 拒", not is_valid_json_body("hello"))
    gate("G2 空 body 拒", not is_valid_json_body(""))
    gate("G2 合法 JSON 放行", is_valid_json_body('{"a":1}'))
    gate("G2 list body 放行(黑板实测支持)", is_valid_json_body("[1,2]"))
    gate("G2 非 JSON 拒: 'not json'", not is_valid_json_body("not json"))
    gate("G2 数字 body 拒: '123' → 拒", not is_valid_json_body("123"))
    # G3 双写
    gate("G3 i9 写 notes/i9/ → 镜像", should_mirror("notes/i9/x", "i9"))
    gate("G3 mbp 写 notes/mbp/ → 镜像", should_mirror("notes/mbp/x", "mbp"))
    gate("G3 i9 写 notes/collab/ → 不镜像(sync-up 管)", not should_mirror("notes/collab/x", "i9"))
    gate("G3 mac-mini 写 → 不镜像(本机主)", not should_mirror("notes/i9/x", "mac-mini"))
    # G4 状态闭环
    gate("G4 task 无 reply → 需 ack", task_needs_ack({"type": "task", "content": "x"}))
    gate("G4 已 reply 不重复要求", not task_needs_ack({"type": "task", "reply_to": "y"}))
    gate("G4 非 task 不需 ack", not task_needs_ack({"type": "status"}))
    # G5 静默
    gate("G5 心跳新鲜(30s) 不 stale", not heartbeat_stale(100, 130))
    gate("G5 心跳超时(120s > 90) stale", heartbeat_stale(100, 220))
    gate("G5 无心跳 ts → stale", heartbeat_stale(None, 100))
    # G6 §3.1 collab 广播语义门 (2026-09-09 · 设备内消息不得进广播域)
    gate("G6 无标记治理卡(a review) 禁 collab", not collab_writable("coordinator", "notes/collab/x", {"type": "review"}))
    gate("G6 守护信封(bus-envelope) 落 collab 放行", collab_writable("coordinator", "notes/collab/x", {"type": "bus-envelope", "_bus": {"task_id": "t"}}))
    gate("G6 显式 broadcast- 动作放行", collab_writable("coordinator", "notes/collab/x", {"action": "broadcast-note"}))
    gate("G6 coordinator 无标记卡也禁 collab(域权≠广播语义)", not collab_writable("coordinator", "notes/collab/x", {"type": "r008-verdict"}))
    gate("G6 mbp 无 collab 域权(G1 先行拒)", not collab_writable("mbp", "notes/collab/x", {"type": "bus-envelope"}))
    gate("G6 collab_broadcast_ok 非 dict 拒", not collab_broadcast_ok("plain-text"))

    print("")
    print(f"  结果: {'✅ GATE OK — 通讯写入门全生效' if ok else '❌ GATE FAIL'}")
    return 0 if ok else 1


# ═══════════ 写入门 CLI (走门写入) ═══════════
LOCAL_BB = os.environ.get("LOCAL_BB", "http://127.0.0.1:8792")
CENTRAL_BB = os.environ.get("CENTRAL_BB", "http://xingqiao.meetfunbp.com:8792")


def bb_put(url, key, val):
    req = urllib.request.Request(f"{url}/{key}", data=json.dumps(val, ensure_ascii=False).encode(),
                                 headers={"Content-Type": "application/json"}, method="PUT")
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode())


def cmd_put(role, key, body, mirror_central=None):
    """走门写入: G1 域权 → G2 JSON → G4(§3.1 collab 语义) → 本机 PUT → G3 镜像中枢"""
    if not can_write(role, key):
        print(f"❌ G1 域权拒绝: 角色 '{role}' 无权写 '{key}'")
        return 2
    if not is_valid_json_body(body):
        print("❌ G2 JSON 格式拒绝: body 非合法 JSON 对象")
        return 2
    val = json.loads(body)
    # G4(2026-09-09 · §3.1 结构门): 写 notes/collab/ 须带广播语义
    # (设备内治理/回执/评审卡禁落广播域——防上行中枢被 i9/mbp 读到, 明鉴泄漏同类根因)
    if key.startswith("notes/collab/") and not collab_broadcast_ok(val):
        print(f"❌ G4 广播语义拒绝: '{key}' 无广播标记(bus-envelope/broadcast-*/scope)——"
              f"设备内消息写本机角色域(§3.1, G-C39)")
        return 2
    # G4 提示: task 需 ack
    if task_needs_ack(val):
        print("  ℹ️ G4: task 消息应带 reply_to/后续回写闭环 (R030)")
    # 本机写入
    try:
        r = bb_put(LOCAL_BB, key, val)
        print(f"✅ 本机写入: {key}")
    except Exception as e:
        print(f"❌ 本机写入失败: {e}")
        return 3
    # 双写中枢
    if should_mirror(key, role) if mirror_central is None else mirror_central:
        try:
            bb_put(CENTRAL_BB, key, val)
            print(f"✅ 镜像中枢: {key}")
        except Exception as e:
            print(f"⚠️ 镜像中枢失败: {e}")
    return 0



# ═══════════ E2 注册表查询 (R-ERR4 · data/discovery/agents/) ═══════════
def cmd_registry(args):
    """registry: 查询全局发现层 (服务器 data/discovery/agents/<device> 逐个查, list 端点不含 data/)"""
    devices = ["mac-mini", "i9", "mbp"]
    try:
        import urllib.request as ur
        print("== 全局发现层 (data/discovery/agents) ==")
        found = False
        for dev in devices:
            try:
                with ur.urlopen(f"http://xingqiao.meetfunbp.com:8792/data/discovery/agents/{dev}", timeout=5) as r:
                    d = json.loads(r.read().decode())
                val = d.get("value", {})
                if not val:
                    print(f"  {dev:<10} ⚠️ 空注册")
                    continue
                found = True
                sessions = val.get("sessions", [])
                roles = ", ".join(s.get("role", "?") for s in sessions[:5])
                print(f"  {val.get('device', dev):<10} online={val.get('status','?')} | {len(sessions)} sessions | {roles[:60]}")
            except Exception:
                print(f"  {dev:<10} — 未注册 (心跳代理未部署)")
        if not found:
            print("  (仅 mac-mini 有 hb-fwd 注册器)")
        return 0
    except Exception as e:
        print(f"❌ 发现层查询失败: {e}")
        return 1


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 0
    if args[0] == "--lean4-check":
        return lean4_check()
    if args[0] == "check":
        # 只校验不写
        role, key = args[1], args[2]
        r = can_write(role, key)
        print(f"{'✅ 放行' if r else '❌ 拒绝'}: role={role} key={key}")
        return 0 if r else 2
    if args[0] == "put":
        role, key, body = args[1], args[2], args[3]
        return cmd_put(role, key, body)
    if args[0] == "registry":
        return cmd_registry(args[1:])
    if args[0] == "put-file":
        role, key, path = args[1], args[2], args[3]
        with open(path, encoding="utf-8") as f:
            return cmd_put(role, key, f.read())
    if args[0] == "--whoami":
        key = args[1]
        print("域权矩阵查询:")
        for role, domains in ROLE_DOMAINS.items():
            mark = "✅" if can_write(role, key) else "·"
            print(f"  {mark} {role}: {', '.join(domains[:3])}...")
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
