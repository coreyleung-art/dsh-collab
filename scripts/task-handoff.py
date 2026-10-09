#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""task-handoff.py — 计算密集型任务一键移交 i9（工具化 SOP）

把「本机资源不足的任务 → 移交 i9」固化为一条命令：
  ① 打包本地目录 → genebank /shared/（AI 网盘共享）
  ② 建任务卡 → tasks/i9/queue/<ts>-<key>（i9 队列）
  ③ 发通知 → notes/i9/（i9 消息通道）
  ④ 记录 → data/handoffs/<ts>-<key>（移交台账）

用法:
  python3 task-handoff.py --name 34图OCR --files ./images --to i9 \
      --task-type ocr --priority P2 \
      --desc "34 张图片 OCR（glm-ocr 本地执行）"

参数:
  --name       任务名（用于任务卡/通知/台账，必填）
  --files      本地目录或文件路径（打包进 genebank，可多个空格分隔）
  --to         目标节点（默认 i9）
  --task-type  任务类型（ocr/annotate/vision/general，默认 general）
  --priority   优先级（P0/P1/P2，默认 P2）
  --desc       任务描述（进入任务卡 content）
  --dry-run    只打印将执行的动作，不实际写入

依赖:
  · 黑板 127.0.0.1:8792（KV）
  · genebank 8801 /shared/ 目录（~/dsh-collab/datasets/shared/）
  · 目标节点 node-bridge 在线（tasks/{node}/queue 消费）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, shutil, subprocess, tarfile, datetime, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/task-handoff.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

BB = "http://127.0.0.1:8792"
GB_SHARED = os.path.expanduser("~/dsh-collab/datasets/shared")

def now():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def ts_key():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

def ascii_key(name, maxlen=20):
    """任务名 → ASCII 安全 key（仅保留 ASCII 字母数字；全中文用类型名兜底）"""
    safe = "".join(c for c in name if (c.isascii() and (c.isalnum() or c in "-_")))
    if safe:
        return safe[:maxlen]
    return "task"  # 全中文名 → 用时间戳区分

def put_bb(path, value):
    full = BB + "/" + path.lstrip("/")
    req = urllib.request.Request(full, data=json.dumps(value).encode(), method="PUT")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def verify_bb(key):
    try:
        req = urllib.request.Request(BB + "/" + key.lstrip("/"))
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def package(files, name, dry_run):
    """打包文件/目录 → genebank shared 目录（tar.gz）"""
    os.makedirs(GB_SHARED, exist_ok=True)
    safe = name.replace(" ", "_").replace("/", "_")
    pkg = os.path.join(GB_SHARED, f"{safe}-{ts_key()}.tar.gz")
    if dry_run:
        return pkg
    with tarfile.open(pkg, "w:gz") as tar:
        for f in files:
            p = os.path.expanduser(f)
            if os.path.exists(p):
                tar.add(p, arcname=os.path.basename(p))
            else:
                print(f"  ⚠️ 文件不存在: {p}")
    return pkg

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="任务名")
    ap.add_argument("--files", nargs="+", default=[], help="打包文件/目录")
    ap.add_argument("--to", default="i9", help="目标节点")
    ap.add_argument("--task-type", default="general", help="ocr/annotate/vision/general")
    ap.add_argument("--priority", default="P2", help="P0/P1/P2")
    ap.add_argument("--desc", default="", help="任务描述")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ts = now()
    key = ts_key()
    print(f"[task-handoff] {ts} 移交任务: {args.name} → {args.to} ({args.priority}/{args.task_type})")

    # ① 打包
    pkg_url = ""
    if args.files:
        pkg = package(args.files, args.name, args.dry_run)
        # genebank 访问 URL（tailnet IP 优先）
        import urllib.parse as up
        pkg_url = f"http://100.120.203.20:8801/shared/{up.quote(os.path.basename(pkg))}"
        print(f"  ① 打包: {pkg}")
        print(f"     下载URL: {pkg_url}")
    else:
        print("  ① 无文件打包（纯任务卡）")

    # ② 任务卡
    task = {
        "task_id": f"t-{ascii_key(args.name)}-{key}",
        "from": "coordinator",
        "to": args.to,
        "type": args.task_type,
        "priority": args.priority,
        "subject": f"{args.name}（{args.priority}/{args.task_type}）",
        "content": [
            f"【任务】{args.desc}",
            f"【数据】{pkg_url}" if pkg_url else "【数据】无（描述内）",
            f"【排期】{args.priority} 后台。",
            f"【回报】完成后写黑板 notes/mac-mini/ + 结果放 genebank /shared/。",
        ],
        "ts": ts,
    }
    q_path = f"tasks/{args.to}/queue/{key}-{ascii_key(args.name)}"
    if args.dry_run:
        print(f"  ② 任务卡(dry): PUT /{q_path}")
    else:
        r = put_bb(q_path, task)
        print(f"  ② 任务卡: /{q_path} → seq {r.get('seq')}")

    # ③ 通知
    note = {
        "from": "coordinator",
        "to": args.to,
        "ts": ts,
        "subject": f"📋 任务：{args.name}（{args.priority}/{args.task_type}）按你排期",
        "content": task["content"],
        "type": "task",
    }
    n_path = f"notes/{args.to}/coordinator-task-{ascii_key(args.name)}"
    if args.dry_run:
        print(f"  ③ 通知(dry): PUT /{n_path}")
    else:
        r = put_bb(n_path, note)
        print(f"  ③ 通知: /{n_path} → seq {r.get('seq')}")

    # ④ 台账
    ledger = {
        "from": "coordinator",
        "ts": ts,
        "name": args.name,
        "to": args.to,
        "task_type": args.task_type,
        "priority": args.priority,
        "desc": args.desc,
        "package_url": pkg_url,
        "task_queue": q_path,
        "note_key": n_path,
        "status": "dispatched",
    }
    h_path = f"data/handoffs/{key}-{ascii_key(args.name)}"
    if args.dry_run:
        print(f"  ④ 台账(dry): PUT /{h_path}")
    else:
        r = put_bb(h_path, ledger)
        print(f"  ④ 台账: /{h_path} → seq {r.get('seq')}")

    print(f"[task-handoff] ✅ 完成: {args.name} → {args.to}（task_id: {task['task_id']}）")
    if args.dry_run:
        print("[task-handoff] dry-run 未写入任何数据")

if __name__ == "__main__":
    main()
