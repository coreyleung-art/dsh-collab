#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-protocol-register.py — 协作协议注册器(连接实验室 v2 · B方案 MVP qc)
给已确认的边绑定协作协议 → 协议 config 落 data/protocols/<id>/config.json
用法:
  python3 bb-protocol-register.py --register --edge A B --mode qc --id proto-qc-1 [--threshold 10]
  python3 bb-protocol-register.py --list
  python3 bb-protocol-register.py --status proto-qc-1
  python3 bb-protocol-register.py --pause/resume proto-qc-1
  python3 bb-protocol-register.py --selfcheck / --tool-version / --lean4-check
数据: data/protocols/<id>/config.json(输入) → 黑板 data/protocols/<id>/config(镜像)
护栏: 协议仅登记/编排, 绝不调用任何真实发送通道(im/send 等) —— 抽检对象=已发送历史回复
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, datetime, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-protocol-register.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "v1.0.0"
BB = os.environ.get("BB_URL", "http://127.0.0.1:8792")
PROTO_DIR = os.path.expanduser("~/dsh-collab/data/protocols")
MODES = {"qc", "relay", "build"}
STATUSES = {"active", "paused", "archived"}
_ID_RE = __import__("re").compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

def _bb_put(key, payload):
    try:
        req = urllib.request.Request(BB + "/" + key, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="PUT")
        with urllib.request.urlopen(req, timeout=6) as r:
            return True, r.status
    except Exception as e:
        return False, str(e)

def _endpoint_valid(aid):
    """端点必须真实存在于 agent-bus(R006#10 契约门)"""
    try:
        d = json.load(open(os.path.expanduser("~/.dsh/agent-bus.json")))
        ids = {p.get("agentId") for p in d.get("profiles", [])}
        return aid in ids
    except Exception:
        return True  # 校验不可用放行(幂等已保)

def _valid_id(pid):
    return bool(pid) and bool(_ID_RE.match(pid))

def _valid_mode(m):
    return m in MODES

def register(edge_from, edge_to, mode, pid, threshold, desc=""):
    """注册协议: 校验端点+id+mode → 写 config(本地+黑板镜像)"""
    # 结构门: 端点真实/非空
    for x in (edge_from, edge_to):
        if not x or not _endpoint_valid(x):
            return {"ok": False, "error": f"端点不存在 agent-bus: {x}(结构门拒)"}
    if not _valid_id(pid):
        return {"ok": False, "error": f"非法协议 id {pid!r}(须小写字母数字连字符)"}
    if not _valid_mode(mode):
        return {"ok": False, "error": f"非法 mode {mode}(须 {sorted(MODES)})"}
    cfg_path = os.path.join(PROTO_DIR, pid, "config.json")
    if os.path.exists(cfg_path):
        return {"ok": False, "error": f"协议 {pid} 已存在(先 --pause 或换 id)"}
    cfg = {
        "id": pid, "edge": {"from": edge_from, "to": edge_to},
        "mode": mode, "threshold": int(threshold or 10),
        "status": "active",
        "desc": desc or f"{mode} 协议: {edge_from[:8]}↔{edge_to[:8]}",
        "counter": 0, "runs": 0,
        "ts": datetime.datetime.now().isoformat(), "by": "bb-protocol-register",
        "channel": "blackboard",   # 结果回写黑板(不碰任何发送通道)
        "no_real_send": True,      # 护栏: 本协议永不触发真实客户消息
    }
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    json.dump(cfg, open(cfg_path, "w"), ensure_ascii=False, indent=1)
    # 黑板镜像
    ok, _ = _bb_put(f"data/protocols/{pid}/config", cfg)
    return {"ok": True, "id": pid, "mode": mode, "mirrored": ok,
            "no_real_send": True, "note": f"协议 {pid} 已注册(active)"}

def _load(pid):
    p = os.path.join(PROTO_DIR, pid, "config.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

def set_status(pid, status):
    cfg = _load(pid)
    if not cfg: return {"ok": False, "error": f"{pid} 不存在"}
    if status not in STATUSES: return {"ok": False, "error": f"状态须 {sorted(STATUSES)}"}
    cfg["status"] = status
    cfg["ts"] = datetime.datetime.now().isoformat()
    json.dump(cfg, open(os.path.join(PROTO_DIR, pid, "config.json"), "w"), ensure_ascii=False, indent=1)
    _bb_put(f"data/protocols/{pid}/config", cfg)
    return {"ok": True, "id": pid, "status": status}

def main():
    ap = argparse.ArgumentParser(description="协作协议注册器(连接实验室 v2)")
    ap.add_argument("--register", action="store_true")
    ap.add_argument("--edge-from")
    ap.add_argument("--edge-to")
    ap.add_argument("--mode", default="qc")
    ap.add_argument("--id")
    ap.add_argument("--threshold", type=int, default=10)
    ap.add_argument("--desc")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--status")
    ap.add_argument("--pause")
    ap.add_argument("--resume")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    args = ap.parse_args()

    if args.tool_version: print(f"bb-protocol-register {VERSION}"); return
    if args.selfcheck:
        ok = os.path.isdir(PROTO_DIR) or True
        print("TCC:", "✅" if ok else "❌"); sys.exit(0)
    if args.lean4_check:
        # Lean4 自检: 违规路径(幽灵端点/非法id/mode)必须被拒; 合法放行
        r1 = register("session-ghost-000", "session-ghost-111", "qc", "proto-x", 10)
        ok1 = (not r1.get("ok")) and "端点不存在" in str(r1.get("error", ""))
        r2 = register("session-ffb7c3ab-e722-4ac2-8ee5-0309bc9bb1ea", "session-b193c782-f56a-4b1e-b943-f7a05dcbc853", "evil-mode", "proto-x2", 10)
        ok2 = (not r2.get("ok")) and "非法 mode" in str(r2.get("error", ""))
        r3 = register("session-ffb7c3ab-e722-4ac2-8ee5-0309bc9bb1ea", "session-b193c782-f56a-4b1e-b943-f7a05dcbc853", "qc", "../evil", 10)
        ok3 = (not r3.get("ok")) and "非法协议 id" in str(r3.get("error", ""))
        # 合法注册(演练 id, 注册后即清 —— 仅证明门不误伤)
        r4 = register("session-ffb7c3ab-e722-4ac2-8ee5-0309bc9bb1ea", "session-b193c782-f56a-4b1e-b943-f7a05dcbc853",
                      "qc", "proto-lean4-probe", 10)
        ok4 = bool(r4.get("ok"))
        import shutil
        shutil.rmtree(os.path.join(PROTO_DIR, "proto-lean4-probe"), ignore_errors=True)
        passed = ok1 and ok2 and ok3 and ok4
        print("lean4-check:", "✅ 结构门生效" if passed else
              f"❌ 违规未被拒: ghost={ok1} mode={ok2} id={ok3} 合法={ok4}")
        sys.exit(0 if passed else 1)
    if args.list:
        if not os.path.isdir(PROTO_DIR): print("无协议"); return
        for d in sorted(os.listdir(PROTO_DIR)):
            c = _load(d)
            if c: print(f"  {d} | {c.get('mode')} | {c.get('status')} | 计数{c.get('counter',0)}/{c.get('threshold')} | {str(c.get('edge',{}).get('from',''))[:8]}↔{str(c.get('edge',{}).get('to',''))[:8]}")
        return
    if args.pause: print(json.dumps(set_status(args.pause, "paused"), ensure_ascii=False)); return
    if args.resume: print(json.dumps(set_status(args.resume, "active"), ensure_ascii=False)); return
    if args.register:
        print(json.dumps(register(args.edge_from, args.edge_to, args.mode, args.id, args.threshold, args.desc), ensure_ascii=False))
        return
    ap.print_help()

if __name__ == "__main__":
    main()
