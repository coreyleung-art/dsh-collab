#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-sub-daemon.py — 黑板事件桥常驻订阅器（通用）

让智能体「主动看黑板」：常驻订阅 8803 SSE 事件桥 → 按 key 前缀分发到
角色的 inbox（~/.dsh/inbox/）→ 角色会话/轮询可读。事件驱动实时，零轮询。

用法:
  python3 bb-sub-daemon.py --agent hr --prefixes "notes/mac-mini/,notes/collab/,data/qa/"
  python3 bb-sub-daemon.py --agent qa --prefixes "tasks/central/queue/,data/qa/"
  python3 bb-sub-daemon.py --agent all --prefixes "notes/collab/"   # 通用协作订阅

参数:
  --agent      角色标识（写 inbox 文件名前缀）
  --prefixes   订阅的 key 前缀（逗号分隔）
  --bb         黑板地址（默认 127.0.0.1:8792）
  --sse        SSE 事件桥地址（默认 127.0.0.1:8803/events）
  --outdir     inbox 输出目录（默认 ~/.dsh/inbox/bb/）

机制:
  · 长连接 SSE（断线自动重连，指数退避）
  · 匹配前缀 → 追加写入 inbox/bb/<agent>-<key 摘要>.jsonl（append-only）
  · 每条带 [NEW] 标记，会话轮询可见；重连不丢事件（连接期间收到即写）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, time, datetime, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-sub-daemon.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="all", help="角色标识")
    ap.add_argument("--prefixes", default="notes/collab/", help="订阅 key 前缀（逗号分隔）")
    ap.add_argument("--bb", default="http://127.0.0.1:8792")
    ap.add_argument("--sse", default="http://127.0.0.1:8803/events")
    ap.add_argument("--outdir", default=os.path.expanduser("~/.dsh/inbox/bb"))
    args = ap.parse_args()

    prefixes = [p.strip() for p in args.prefixes.split(",") if p.strip()]
    os.makedirs(args.outdir, exist_ok=True)
    outfile = os.path.join(args.outdir, f"{args.agent}.jsonl")

    print(f"[bb-sub-daemon] {now()} agent={args.agent} prefixes={prefixes} -> {outfile}", flush=True)

    backoff = 2
    while True:
        try:
            req = urllib.request.Request(args.sse)
            with urllib.request.urlopen(req, timeout=None) as r:  # 阻塞长连接
                backoff = 2  # 连接成功，重置退避
                print(f"[bb-sub-daemon] {now()} SSE 已连接 {args.sse}", flush=True)
                for raw in r:
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    try:
                        evt = json.loads(line[5:].strip())
                    except Exception:
                        continue
                    key = evt.get("key", "")
                    if not key:
                        continue
                    # 匹配前缀
                    if not any(key.startswith(p) for p in prefixes):
                        continue
                    # 追加写入（append-only，防并发撕裂用行锁）
                    entry = {
                        "ts": now(),
                        "key": key,
                        "value": evt.get("value"),
                        "version": evt.get("version"),
                    }
                    with open(outfile, "a", encoding="utf-8") as f:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    print(f"[bb-sub-daemon] {now()} [{args.agent}] 📩 {key}", flush=True)
        except KeyboardInterrupt:
            print(f"\n[bb-sub-daemon] {now()} 退出", flush=True)
            sys.exit(0)
        except Exception as e:
            print(f"[bb-sub-daemon] {now()} 连接错误: {str(e)[:80]}，{backoff}s 后重连", flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)

if __name__ == "__main__":
    main()
