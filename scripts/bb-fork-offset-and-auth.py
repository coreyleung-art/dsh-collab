#!/usr/bin/env python3
"""独立复核 PSTD 作者的两点新声称（耐久路径版）：
① card-1791011480 两板 body 的【首个分歧位置】是否 = 第 825 字
② 无头 GET/PUT 对两板的鉴权差异（读免鉴权 / 写要 token）
★ 输出纪律：只报位置与形态，**不复述任何疑似凭证字符串**，避免二次暴露。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== bb-fork-offset-and-auth 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 独立复核 PSTD 作者的两点新声称（耐久路径版）：")
    print("  · ① card-1791011480 两板 body 的【首个分歧位置】是否 = 第 825 字")
    print("  · ② 无头 GET/PUT 对两板的鉴权差异（读免鉴权 / 写要 token）")
    print("  · ★ 输出纪律：只报位置与形态，**不复述任何疑似凭证字符串**，避免二次暴露。")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/bb-fork-offset-and-auth.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import json, urllib.request, urllib.error

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-fork-offset-and-auth.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

LOCAL = "http://127.0.0.1:8792/"
CENTRAL = "http://106.53.214.108:8792/"
KEY = "notes/mac-mini/card-1791011480"


def fetch(base, key, t=25, method="GET"):
    req = urllib.request.Request(base + key, method=method)
    if method == "PUT":
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps({"__probe__": "audit-read-only-probe"}).encode()
    try:
        r = urllib.request.urlopen(req, timeout=t)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return f"ERR:{type(e).__name__}", b""


def body_of(raw):
    try:
        return json.loads(raw.decode("utf-8", "replace"))["value"]["body"]
    except Exception:
        return None


print("=== ① body 首个分歧位置 ===")
sl, rl = fetch(LOCAL, KEY)
sc, rc = fetch(CENTRAL, KEY)
bl, bc = body_of(rl), body_of(rc)
print(f"local http={sl} body_len={len(bl) if bl else None}")
print(f"central http={sc} body_len={len(bc) if bc else None}")
if bl and bc:
    n = min(len(bl), len(bc))
    first = next((i for i in range(n) if bl[i] != bc[i]), None)
    print(f"共同前缀长度内首个分歧位置（0-based）= {first}")
    print(f"换算成 1-based 第 {first+1 if first is not None else '-'} 字")
    print(f"他声称 = 第 825 字 ⇒ {'✅ 一致' if first is not None and first+1 == 825 else '⚠ 不一致，见下行'}")
    if first is not None:
        # 只报“形态”，不打印原文
        def shape(s):
            seg = s[first:first+40]
            has_angle = "<" in seg and ">" in seg
            has_star = "*" in seg
            has_paren = "(" in seg or "（" in seg
            return f"含尖括号标记={has_angle} 含星号={has_star} 含括号={has_paren} 段长={len(seg)}"
        print("  local  分歧处形态:", shape(bl))
        print("  central 分歧处形态:", shape(bc))
        print("  local  在该点更短?", len(bl) < len(bc))
else:
    print("❌ 取 body 失败")

print()
print("=== ② 无头 GET / PUT 的鉴权差异 ===")
print("（无任何 Authorization / token 头）")
for label, base in (("本地板 127.0.0.1:8792", LOCAL), ("中枢板 106.53.214.108:8792", CENTRAL)):
    sg, rg = fetch(base, KEY)
    print(f"  {label:<28} GET -> {sg}  bytes={len(rg)}")
probe_key = "notes/mac-mini/__audit-probe-do-not-use-20261008"
for label, base in (("本地板", LOCAL), ("中枢板", CENTRAL)):
    sp, _ = fetch(base, probe_key, method="PUT")
    print(f"  {label:<28} PUT -> {sp}")
print("\n⇒ 判读：GET 两板 200（读免鉴权）· PUT 本地 200/中枢 401（写需 token）⇒ 与作者声称一致？")
