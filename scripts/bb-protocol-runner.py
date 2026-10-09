#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-protocol-runner.py — 协作协议执行器(连接实验室 v2 · B方案 MVP qc)
按协议节奏: 读发送计数 → 达阈值 → 生成抽检任务卡 → 通知验收方(黑板+agent_send 由调度方发)
用法:
  python3 bb-protocol-runner.py --count proto-qc-1              # 计数+1(接真实事件时用)
  python3 bb-protocol-runner.py --mock-events proto-qc-1 N      # MOCK 注入 N 条(沙箱试跑, 不碰真实)
  python3 bb-protocol-runner.py --tick                          # 遍历 active 协议: 计数达阈值→发任务卡
  python3 bb-protocol-runner.py --status proto-qc-1
  python3 bb-protocol-runner.py --selfcheck / --tool-version / --lean4-check
护栏(硬): 本工具永不含任何 /api/im/send 或真实发送调用 —— 只做计数/任务卡/黑板通知

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, datetime, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-protocol-runner.log")


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

def _bb_put(key, payload):
    """黑板写: 超时可能是『已写入但响应丢失』→ 超时后回读确认(不误判失败)"""
    def _do(timeout):
        req = urllib.request.Request(BB + "/" + key, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="PUT")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    try:
        return True, _do(15)
    except Exception:
        # 超时/断连 → 回读验证是否已写入(黑板慢响应时写已生效)
        try:
            with urllib.request.urlopen(BB + "/" + key, timeout=8) as r:
                d = json.loads(r.read().decode())
                v = d.get("value", {})
                if v and isinstance(v, dict) and v.get("ts") == payload.get("ts"):
                    return True, "ok(after-readback)"
        except Exception:
            pass
        return False, "write-failed"

def _load(pid):
    p = os.path.join(PROTO_DIR, pid, "config.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

def _save(cfg):
    json.dump(cfg, open(os.path.join(PROTO_DIR, cfg["id"], "config.json"), "w"),
              ensure_ascii=False, indent=1)

def count_event(pid, n=1):
    """计数 +n(来自真实发送事件或 MOCK). 幂等由调用方 runId 保证"""
    cfg = _load(pid)
    if not cfg: return {"ok": False, "error": f"{pid} 不存在"}
    if cfg.get("status") != "active": return {"ok": False, "error": f"{pid} 非 active({cfg.get('status')})"}
    cfg["counter"] = int(cfg.get("counter", 0)) + n
    _save(cfg)
    return {"ok": True, "id": pid, "counter": cfg["counter"], "threshold": cfg.get("threshold")}

def make_task_card(cfg, reason=""):
    """达阈值 → 生成抽检任务卡(data/protocols/<id>/tasks/<ts>) + 黑板镜像. 返回 task"""
    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S%f")
    task = {
        "id": f"{cfg['id']}-{ts}", "proto": cfg["id"], "mode": cfg.get("mode"),
        "from": cfg["edge"]["from"], "to": cfg["edge"]["to"],
        "action": "抽检最近 1 条已发送历史回复(质量/合规)",
        "source": "qc-threshold", "batch": int(cfg.get("counter", 0)),
        "ts": datetime.datetime.now().isoformat(), "status": "new",
        "channel": "blackboard", "no_real_send": True,
        "reason": reason or "达抽检阈值",
    }
    os.makedirs(os.path.join(PROTO_DIR, cfg["id"], "tasks"), exist_ok=True)
    json.dump(task, open(os.path.join(PROTO_DIR, cfg["id"], "tasks", ts + ".json"), "w"),
              ensure_ascii=False, indent=1)
    _bb_put(f"data/protocols/{cfg['id']}/tasks/{ts}", task)
    # 通知验收方(黑板 notes/<短id>/ —— agent_send 由明鉴回合感知时补)
    _short = str(cfg["edge"]["to"]).replace("session-", "").split("-")[0]
    _nkey = f"notes/{_short}/protocol-task-{cfg['id']}"
    _nval = {"ts": datetime.datetime.now().isoformat(), "proto": cfg["id"],
             "action": task["action"], "by": "bb-protocol-runner", "task_id": task["id"]}
    _note_ok = False
    for _try in range(3):   # 黑板写重试(连续写偶发失败)
        _ok3, _s3 = _bb_put(_nkey, _nval)
        if _ok3:
            _note_ok = True
            break
    task["notify_delivered"] = _note_ok
    # 补写: notify 状态回填任务卡文件(初次写时无此字段)
    json.dump(task, open(os.path.join(PROTO_DIR, cfg["id"], "tasks", ts + ".json"), "w"),
              ensure_ascii=False, indent=1)
    cfg["counter"] = 0; cfg["runs"] = int(cfg.get("runs", 0)) + 1
    _save(cfg)
    return task

def tick():
    """遍历 active 协议: counter >= threshold → 发任务卡"""
    out = []
    if not os.path.isdir(PROTO_DIR): return out
    for d in sorted(os.listdir(PROTO_DIR)):
        cfg = _load(d)
        if not cfg or cfg.get("status") != "active": continue
        if int(cfg.get("counter", 0)) >= int(cfg.get("threshold", 10)):
            t = make_task_card(cfg)
            out.append({"proto": d, "task": t["id"], "counter_was": "threshold 达标"})
    return out

def _no_real_send():
    """护栏(AST): 真实执行代码不含任何对外发送通道调用
    仅允许: 黑板写(_bb_put) + 本地文件 + 打印. 禁: im_send/任何直发.
    (AST Call 节点级检查 —— 注释/docstring 提及发送不影响判定)"""
    import ast as _ast
    src = open(os.path.abspath(__file__)).read()
    tree = _ast.parse(src)
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Call):
            f = node.func
            name = f.attr if isinstance(f, _ast.Attribute) else (f.id if isinstance(f, _ast.Name) else "")
            if name == "im_send" or name.startswith("send_"):
                return False
    return True

def main():
    ap = argparse.ArgumentParser(description="协作协议执行器(沙箱, 永不真发)")
    ap.add_argument("--count", metavar="PID")
    ap.add_argument("--mock-events", nargs=2, metavar=("PID", "N"))
    ap.add_argument("--tick", action="store_true")
    ap.add_argument("--status", metavar="PID")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    args = ap.parse_args()

    if args.tool_version: print(f"bb-protocol-runner {VERSION}"); return
    if args.selfcheck:
        print("TCC:", "✅ 护栏(AST): 无真实发送调用" if _no_real_send() else "❌ 含发送调用!")
        sys.exit(0 if _no_real_send() else 1)
    if args.lean4_check:
        # 自检: AST 级护栏(排除注释/docstring 误报) + 幽灵协议拒
        ok1 = _no_real_send()
        r = count_event("proto-nonexist-xyz")
        ok2 = (r is not None) and (not r.get("ok"))
        print("lean4-check:", "✅ 结构门生效(无发送+幽灵拒)" if (ok1 and ok2) else
              f"❌ 护栏={ok1} 幽灵拒={ok2}")
        sys.exit(0 if (ok1 and ok2) else 1)
    if args.status:
        cfg = _load(args.status)
        if not cfg: print(f"{args.status} 不存在"); return
        print(json.dumps({"id": cfg["id"], "mode": cfg["mode"], "status": cfg["status"],
                          "counter": cfg.get("counter"), "threshold": cfg.get("threshold"),
                          "runs": cfg.get("runs"), "edge": cfg.get("edge")}, ensure_ascii=False))
        return
    if args.mock_events:
        pid, n = args.mock_events
        r = count_event(pid, int(n))
        print(json.dumps(r, ensure_ascii=False))
        if r.get("ok") and r.get("counter", 0) >= r.get("threshold", 10):
            cfg = _load(pid)
            t = make_task_card(cfg, reason="MOCK 沙箱试跑达阈值")
            print(json.dumps({"task_created": t["id"], "batch": t["batch"]}, ensure_ascii=False))
        return
    if args.count:
        print(json.dumps(count_event(args.count, 1), ensure_ascii=False)); return
    if args.tick:
        out = tick()
        print(json.dumps(out, ensure_ascii=False)); return
    ap.print_help()

if __name__ == "__main__":
    main()
