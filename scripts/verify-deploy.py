#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交付验证器 · verify-deploy.py
===============================
解决「只看 HTTP 200 就认为上线了」的问题：200 只说明有东西在，
不能说明线上就是**你手上的这一版**（真实事故：线上 95,645B，本地 52,302B）。

给一份「本地文件 → URL」映射，逐个拉取线上内容并**逐字节比对（sha256）**：

用法：
    verify-deploy.py --map deploy-map.json [--timeout 25] [--json]

deploy-map.json：
    {
      "base": "https://example.com",
      "pairs": [
        { "local": "/abs/path/index.html",         "url": "/flowernet/" },
        { "local": "/abs/path/welcome/index.html", "url": "/flowernet/welcome/" }
      ]
    }

行为要点：
  ✓ 比对用 hashlib.sha256(local_bytes) vs sha256(remote_bytes) —— 不只看大小
    （大小相同、内容不同的情况真实存在，只看 size 会漏放行）
  ✓ URL 一律加 `?t=<epoch>` 时间戳参数绕过 CDN 缓存（已有 query 时用 &）
  ✓ 逐条超时隔离：单条失败/超时/404 不影响其他条
  ✓ 发送 Accept-Encoding: identity，避免服务端压缩导致「字节不同但内容相同」的假不一致
  ✓ url 可写相对路径（拼 base）或完整 http(s) URL（直接用）

退出码：
    0 = 全部一致
    1 = 有不一致或错误（404/超时/本地缺失）
    2 = 用法或 IO 错误（map 文件缺失/格式错、pairs 为空）

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
    print("== verify-deploy 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 交付验证器 · verify-deploy.py")
    print("  · 解决「只看 HTTP 200 就认为上线了」的问题：200 只说明有东西在，")
    print("  · 不能说明线上就是**你手上的这一版**（真实事故：线上 95,645B，本地 52,302B）。")
    print("  · 给一份「本地文件 → URL」映射，逐个拉取线上内容并**逐字节比对（sha256）**：")
    print("  · 命令/参数: map, timeout, json")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, hashlib, json, os, socket, ssl, sys, time, urllib")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/verify-deploy.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）


import argparse
import hashlib
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/verify-deploy.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

SEP = "=" * 64
SUBSEP = "-" * 64
HOME = os.path.expanduser("~")
SIZE_WIDTH = 6          # 与示例对齐：本地 803022B / 本地  52290B / 本地   8903B


def setup_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def abbrev(path):
    ap = os.path.abspath(path)
    if ap == HOME:
        return "~"
    if ap.startswith(HOME + os.sep):
        return "~" + ap[len(HOME):]
    return ap


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def join_url(base, url):
    """相对路径拼 base；完整 URL 原样使用。"""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if not base:
        return url
    return base.rstrip("/") + "/" + url.lstrip("/")


def with_cache_buster(url, stamp):
    sep = "&" if "?" in url else "?"
    return "{}{}t={}".format(url, sep, stamp)


def fmt_size(n):
    return "{:>{w}}B".format(n, w=SIZE_WIDTH) if isinstance(n, int) else " " * SIZE_WIDTH + "-"


def fetch(url, timeout):
    """拉取 URL。返回 (status, data, error_text)。成功时 error_text 为 None。"""
    req = urllib.request.Request(url, headers={
        "User-Agent": "verify-deploy/1.0 (byte-compare deliverable check)",
        "Accept-Encoding": "identity",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }, method="GET")
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return getattr(resp, "status", resp.getcode()), resp.read(), None
    except urllib.error.HTTPError as exc:      # 404/403/500...
        body = b""
        try:
            body = exc.read()
        except Exception:
            pass
        return exc.code, body, "HTTP {}".format(exc.code)
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, socket.timeout):
            return None, None, "超时（{}s）".format(timeout)
        return None, None, "网络错误：{}".format(reason)
    except (socket.timeout, TimeoutError):
        return None, None, "超时（{}s）".format(timeout)
    except Exception as exc:                    # 兜底：单条异常不影响其他条
        return None, None, "拉取异常：{}: {}".format(type(exc).__name__, exc)


def check_pair(pair, base, timeout, stamp):
    """逐条验证，任何异常都收敛成一条结果，不向外抛。"""
    url = pair.get("url") or ""
    local = pair.get("local") or ""
    full = with_cache_buster(join_url(base, url), stamp)   # 带时间戳绕 CDN
    result = {
        "url": url,
        "full_url": full,
        "local": abbrev(local) if local else "",
        "status": "error",
        "http_status": None,
        "local_size": None,
        "remote_size": None,
        "local_sha256": None,
        "remote_sha256": None,
        "error": None,
    }

    # 1) 本地
    if not local:
        result["error"] = "映射缺少 local 字段"
        return result
    abs_local = os.path.abspath(os.path.expanduser(local))
    if not os.path.isfile(abs_local):
        result["error"] = "本地文件不存在：{}".format(abbrev(abs_local))
        return result
    try:
        with open(abs_local, "rb") as fh:
            local_bytes = fh.read()
    except OSError as exc:
        result["error"] = "本地读取失败：{}".format(exc)
        return result
    result["local_size"] = len(local_bytes)
    result["local_sha256"] = sha256_bytes(local_bytes)

    # 2) 线上
    status, remote_bytes, err = fetch(full, timeout)
    result["http_status"] = status
    if err is not None:
        result["error"] = err
        return result

    result["remote_size"] = len(remote_bytes)
    result["remote_sha256"] = sha256_bytes(remote_bytes)

    # 3) 比对（sha256，不是 size）
    if result["local_sha256"] == result["remote_sha256"]:
        result["status"] = "consistent"
    else:
        result["status"] = "mismatch"
        if result["remote_size"] > result["local_size"]:
            result["note"] = "线上是旧版"
        elif result["remote_size"] < result["local_size"]:
            result["note"] = "线上体积更小"
        else:
            result["note"] = "大小相同、内容不同"
    return result


def render(results, base):
    width = max(26, max((len(r["url"]) for r in results), default=0) + 3)
    lines = ["交付验证 · {} 条路径 · base={}".format(len(results), base), SEP]
    for r in results:
        col = r["url"].ljust(width)
        if r["status"] == "consistent":
            lines.append("✅ {}本地 {}  线上 {}   cmp 一致".format(
                col, fmt_size(r["local_size"]), fmt_size(r["remote_size"])))
        elif r["status"] == "mismatch":
            lines.append("⚠️ {}本地 {}  线上 {}   cmp 不一致（{}）".format(
                col, fmt_size(r["local_size"]), fmt_size(r["remote_size"]),
                r.get("note", "内容不同")))
        else:
            lines.append("❌ {}本地 {}  {}".format(
                col, fmt_size(r["local_size"]), r["error"]))

    lines.append(SUBSEP)
    total = len(results)
    ok = sum(1 for r in results if r["status"] == "consistent")
    bad = sum(1 for r in results if r["status"] == "mismatch")
    err = sum(1 for r in results if r["status"] == "error")
    if ok == total:
        lines.append("结论：{}/{} 全部一致 ✅".format(ok, total))
    else:
        parts = ["{}/{} 一致".format(ok, total), "{} 条不一致".format(bad)]
        if err:
            parts.append("{} 条错误".format(err))
        lines.append("结论：" + " · ".join(parts))
    return "\n".join(lines)


def main(argv=None):
    setup_stdout()
    parser = argparse.ArgumentParser(
        prog="verify-deploy.py",
        description="交付验证：拉线上内容与本地文件逐字节（sha256）比对",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="退出码：0=全部一致 / 1=有不一致或错误 / 2=用法或 IO 错误",
    )
    parser.add_argument("--map", dest="map_path", required=True, help="deploy-map.json 路径")
    parser.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    parser.add_argument("--timeout", type=float, default=25, help="单条请求超时秒数（默认 25）")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON（不输出人读报告）")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.map_path):
        sys.stderr.write("错误：映射文件不存在：{}\n".format(args.map_path))
        return 2
    try:
        with open(args.map_path, "r", encoding="utf-8") as fh:
            spec = json.load(fh)
    except Exception as exc:
        sys.stderr.write("错误：映射文件解析失败：{}\n".format(exc))
        return 2
    if not isinstance(spec, dict):
        sys.stderr.write("错误：映射文件必须是对象：{\"base\": ..., \"pairs\": [...]}\n")
        return 2
    pairs = spec.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        sys.stderr.write("错误：pairs 必须是非空数组\n")
        return 2

    base = spec.get("base") or ""
    stamp = int(time.time())

    results = []
    for idx, pair in enumerate(pairs):
        if not isinstance(pair, dict):
            results.append({"url": "pairs[{}]".format(idx), "full_url": "", "local": "",
                            "status": "error",
                            "http_status": None, "local_size": None, "remote_size": None,
                            "local_sha256": None, "remote_sha256": None,
                            "error": "pairs[{}] 不是对象".format(idx)})
            continue
        results.append(check_pair(pair, base, args.timeout, stamp))

    total = len(results)
    ok = sum(1 for r in results if r["status"] == "consistent")
    bad = sum(1 for r in results if r["status"] == "mismatch")
    err = sum(1 for r in results if r["status"] == "error")

    if args.json:
        payload = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "base": base,
            "timeout": args.timeout,
            "total": total,
            "consistent": ok,
            "mismatch": bad,
            "error": err,
            "all_consistent": ok == total,
            "results": results,
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(render(results, base) + "\n")

    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
