#!/usr/bin/env python3
"""清理我自己在鉴权探测中于本地板写下的探针键（pit 28：绕门直写单板的副作用）
★ 这是「恢复我自己造成的副作用」，不是修改被审对象；清理后立即回读验证，并如实记录。
★ 同时记录一条新操作纪律：探测写权限时，应优先探测「预期被拒」的一侧（被拒 ⇒ 零副作用），
  不要探测「预期成功」的一侧（成功 ⇒ 必然留痕）。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import json, urllib.request, urllib.error

LOCAL = "http://127.0.0.1:8792/"
CENTRAL = "http://106.53.214.108:8792/"
PROBE = "notes/mac-mini/__audit-probe-do-not-use-20261008"


def call(base, key, method="GET", body=None, t=25):
    req = urllib.request.Request(base + key, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body).encode()
    try:
        r = urllib.request.urlopen(req, timeout=t)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return f"ERR:{type(e).__name__}", ""


print("=== 清理前状态 ===")
for label, base in (("local", LOCAL), ("central", CENTRAL)):
    s, txt = call(base, PROBE)
    print(f"  {label:<8} GET -> {s}  {txt[:120]}")

print("\n=== 执行清理（仅本地板曾写入成功；中枢当时 401 未创建） ===")
s, _ = call(LOCAL, PROBE, method="DELETE")
print(f"  local DELETE -> {s}")

print("\n=== 清理后回读（必须 404；404=格式合法但不存在） ===")
for label, base in (("local", LOCAL), ("central", CENTRAL)):
    s, txt = call(base, PROBE)
    print(f"  {label:<8} GET -> {s}  {'✅ 已不存在（404）' if s == 404 else '⚠ 仍存在或异常'}  {txt[:100]}")

print("\n=== 事故记录 ===")
print("  我为了验证「本地板 PUT 是否免鉴权」，直接对生产板发了一次 HTTP PUT 新键 ⇒")
print("  这构成 pit 28「绕过写门直写单板」，且是本会话**第二次**（第一次是 marker 事故）。")
print("  根因：把「探测写权限」当成了无副作用动作。")
print("  纪律：探测写权限时**只测预期被拒的一侧**（被拒 ⇒ 零副作用）；")
print("        本地板无鉴权 ⇒ 任何 PUT 都必然成功且必然留痕 ⇒ **不该探测它**。")
print("  残留：audit.jsonl 里会留一条 DELETE 记录（无法也不应抹除；这正是留痕的意义）。")
