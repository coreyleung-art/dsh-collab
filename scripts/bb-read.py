#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-read.py — 看黑板技能（最小上下文：本地模型摘要）

配合「agent_send 短提醒 + 本地模型看黑板」模式：
  ① 其他方只发提醒：agent_send "看黑板 notes/mac-mini/xxx"
  ② 会话调本脚本：本地 qwen2.5:3b 读黑板内容 → 一行摘要（≤30字）
  ③ 只有需要决策的内容才带进上下文（或提示用户/中枢）

用法:
  python3 bb-read.py notes/mac-mini/recovery-todo        # 单键摘要
  python3 bb-read.py --prefix notes/mac-mini/ --last 5   # 前缀下最近 N 条摘要
  python3 bb-read.py --full notes/mac-mini/recovery-todo # 全文输出（不摘要）
  python3 bb-read.py --scan ~/.dsh/inbox/bb/hr.jsonl     # 本地订阅 inbox 摘要

参数:
  key/--prefix  黑板键或前缀
  --last N      最近 N 条（配 prefix 用，默认 5）
  --full        输出全文（不摘要，用于决策内容）
  --model       本地模型（默认 qwen2.5:3b，零 API 成本）
  --bb          黑板地址（默认 127.0.0.1:8792）

资源特性:
  · 默认摘要模式：本地模型推理（~2s，~10-30 tokens），API 成本 = 0
  · 上下文开销：仅摘要文本进上下文（~30 tokens），不是全文（~1200 tokens）
  · --full 仅用于明确需要全文决策的场景（谨慎使用）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, urllib.request

BB = "http://127.0.0.1:8792"
OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5:3b"

def get_bb(path):
    try:
        req = urllib.request.Request(BB + "/" + path.lstrip("/"))
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}

def summarize(text, model=MODEL):
    """本地模型摘要（零 API 成本）"""
    prompt = f"这是黑板消息内容：{text}。请用一行中文摘要（≤30字），只输出摘要本身。"
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    try:
        req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
            return d.get("response", "").strip()[:60]
    except Exception as e:
        return f"[本地模型不可用: {str(e)[:40]}]"

def extract_text(value):
    """从黑板 value 提取可摘要文本"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(str(x) for x in value)[:500]
    if isinstance(value, dict):
        # 优先 content/content 数组，其次 subject，其次整个 JSON
        for k in ("content", "subject", "summary", "note"):
            if k in value:
                v = value[k]
                if isinstance(v, list):
                    return " ".join(str(x) for x in v)[:500]
                return str(v)[:500]
        return json.dumps(value, ensure_ascii=False)[:500]
    return str(value)[:500]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key", nargs="?", help="黑板键（如 notes/mac-mini/recovery-todo）")
    ap.add_argument("--prefix", help="前缀（如 notes/mac-mini/）")
    ap.add_argument("--last", type=int, default=5)
    ap.add_argument("--full", action="store_true", help="全文输出不摘要")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--bb", default=BB)
    ap.add_argument("--scan", help="本地订阅 inbox 文件")
    args = ap.parse_args()

    entries = []

    if args.scan:
        # 本地订阅 inbox：读 jsonl 尾部 N 条
        try:
            lines = open(args.scan, encoding="utf-8").read().strip().split("\n")
            for line in lines[-args.last:]:
                if line.strip():
                    entries.append(("inbox", json.loads(line)))
        except Exception as e:
            print(f"读取失败: {e}")
            sys.exit(1)
    elif args.prefix:
        d = get_bb(args.prefix)
        if "error" in d:
            print(f"黑板错误: {d['error']}")
            sys.exit(1)
        lst = d.get("list", d) if isinstance(d, dict) else d
        # 按 ts 排序取最近 N
        items = [(k, v.get("ts",""), v.get("value")) for k, v in lst.items() if k.startswith(args.prefix)]
        items.sort(key=lambda x: x[1], reverse=True)
        for k, ts, val in items[:args.last]:
            entries.append((k, {"key": k, "value": val, "ts": ts}))
    elif args.key:
        d = get_bb(args.key)
        if "error" in d:
            print(f"黑板错误: {d['error']}")
            sys.exit(1)
        entries.append((args.key, d))

    if not entries:
        print("无内容")
        return

    for name, evt in entries:
        value = evt.get("value") if isinstance(evt, dict) else None
        ts = evt.get("ts", "")[:19]
        if args.full:
            print(f"=== {name} [{ts}] ===")
            print(json.dumps(value, ensure_ascii=False, indent=1)[:800] if value else "(无)")
            print()
        else:
            text = extract_text(value)
            if not text:
                print(f"· {name} [{ts}]: (空)")
                continue
            summ = summarize(text, args.model)
            print(f"· {name} [{ts}]: {summ}")

if __name__ == "__main__":
    main()
