#!/usr/bin/env python3
"""
check-key-refs.py — 消息里提到的黑板 key，发出去之前先核它存不存在

★ 由来（2026-09-10，我自己的错，由 HR 核出）：
   我在一条 agent_send 消息里写「看黑板 notes/mac-mini/ack-hr-terminus-close-20260910 已落」——
   **而那张卡我从未写过。** 我是凭记忆写了一个卡名，并把它当成「已落」报了。
   HR 核实：**两实例均 404。**
   ★ 它同时犯了我当天刚立的三条：
     · 指称完整性（存在层）—— 引用了不存在的对象，且没核
     · 自述只能用于定位 —— 我说「已落」，那是自述不是判定
     · 第 0 类 0a —— 我连验证手段都没用，只是凭记忆说了一句

★ 为什么现有机制没挡住：
   · bb-write.py 会回读 —— **但我没用它，我直接发的消息**
   · 候选A 形态②「写入后回读」—— **我没有「写入」这个动作，所以没有触发点**
   · **缺口在「消息里提到一个 key」这个动作上，而没有任何检查覆盖它**

★ 本工具填的就是这个缺口：
   扫一段文本 → 抽出所有「黑板 key 形态」的字符串 → 逐个 GET → 404 则报告。
   **这正是我那次犯错的精确阻挡点。**

用法：
  check-key-refs.py "<文本>" [--base http://127.0.0.1:8792] [--json]
  echo "看黑板 data/registry/xxx" | check-key-refs.py --stdin

退出码：0 全部存在 · 1 有 404（引用无效）· 2 用法错误
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, sys, urllib.request as U, urllib.error

VERSION = "1.0.0"
TOOL = "check-key-refs"
LOG = os.path.expanduser("~/dsh-collab/logs/check-key-refs.log")

# 黑板 key 形态：首段纯小写字母，至少两段
KEY_RE = re.compile(r'\b([a-z]+(?:/[A-Za-z0-9._\-]+)+)\b')


def log(rec):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        import datetime
        rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "tool": TOOL, **rec}
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def probe(base, key):
    try:
        r = U.urlopen(f"{base}/{key}", timeout=8)
        body = r.read()
        try:
            d = json.loads(body.decode("utf-8", "replace"))
            # 空壳检测：键存在但 value 空
            v = d.get("value") if isinstance(d, dict) else None
            if v in (None, {}, [], ""):
                return r.status, "empty-shell"
            return r.status, "ok"
        except Exception:
            return r.status, "non-json"
    except U.HTTPError as e:
        return e.code, ("bad-key" if e.code == 400 else "not-found" if e.code == 404 else "http-error")
    except Exception as e:
        return None, f"ERR:{type(e).__name__}"


def main():
    ap = argparse.ArgumentParser(description="核消息里提到的黑板 key 是否存在")
    ap.add_argument("text", nargs="?", default="")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--base", action="append", default=None,
                    help="黑板实例（可多次；默认核 本机 + 中央 两个）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    a = ap.parse_args()
    if a.tool_version:
        print(VERSION); return 0

    text = sys.stdin.read() if a.stdin else a.text
    if not text:
        print("错误：需要文本（位置参数或 --stdin）", file=sys.stderr); return 2

    # ★ 默认核两实例 —— 由来：我补写新卡后本机 200 而中央 404，
    #   差一点又说「已落」。**只核一个实例 = 只核了一半。**
    bases = a.base or ["http://127.0.0.1:8792", "http://106.53.214.108:8792"]

    keys = sorted(set(KEY_RE.findall(text)))
    # 过滤掉明显不是黑板 key 的（如路径 ~/dsh-collab/...、http://...）
    keys = [k for k in keys if not text.count("//" + k) and not k.startswith(("dsh-collab", "Applications", "Users"))]

    if not keys:
        print("  ✅ 文本中未发现黑板 key 形态的引用")
        return 0

    results = []
    for k in keys:
        per = {}
        for b in bases:
            code, kind = probe(b, k)
            per[b] = {"http": code, "kind": kind}
        ok = all(v["kind"] == "ok" for v in per.values())
        results.append({"key": k, "per_instance": per, "exists": ok,
                        "http": "/".join(str(v["http"]) for v in per.values()),
                        "kind": "/".join(v["kind"] for v in per.values())})

    bad = [r for r in results if not r["exists"]]
    if a.json:
        print(json.dumps({"bases": bases, "total": len(results), "invalid": len(bad), "results": results},
                         ensure_ascii=False, indent=2))
    else:
        print(f"== 黑板 key 引用核验（{len(bases)} 个实例）==")
        for r in results:
            mark = "✅" if r["exists"] else ("⚠️" if r["kind"] == "empty-shell" else "❌")
            print(f"  {mark} {r['key'][:60]:<62} HTTP {r['http']} · {r['kind']}")
        print()
        if bad:
            print(f"  🚫 **{len(bad)} 个引用无效** —— 发出这条消息前请先修正：")
            for r in bad:
                print(f"      · {r['key']} → {r['kind']}")
            print()
            print("  ★ 本检查的由来：我在消息里写「已落」，而那张卡从未存在（两实例 404）。")
            print("    **「我说已落」与「它真的落了」之间，原先没有任何机制挡。**")
        else:
            print(f"  ✅ 全部 {len(results)} 个引用有效")

    log({"action": "check", "total": len(results), "invalid": len(bad)})
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
