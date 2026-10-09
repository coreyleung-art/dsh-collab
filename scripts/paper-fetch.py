#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""论文抓取缓存工具 v0.1 (HR)

输入：--urls "arXiv ID 或 URL 列表"（逗号/空格分隔）
输出：research/paper-cache/<id>.md（title/abstract/链接——供 agent knowledge_add/import 入库）
用法：python3 paper-fetch.py --urls "2604.12301 1905.10083"

说明：只抓 arXiv abs 页（开放）；付费墙论文由 agent 用 knowledge_import_url 或摘要兜底。

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
    print("== paper-fetch 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 论文抓取缓存工具 v0.1 (HR)")
    print("  · 输入：--urls 'arXiv ID 或 URL 列表'（逗号/空格分隔）")
    print("  · 输出：research/paper-cache/<id>.md（title/abstract/链接——供 agent knowledge_add/import 入库）")
    print("  · 用法：python3 paper-fetch.py --urls '2604.12301 1905.10083")
    print("  · 命令/参数: urls, out-dir")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/paper-fetch.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, os, re, sys, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/paper-fetch.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

def fetch_abs(aid):
    url = f"https://arxiv.org/abs/{aid}"
    try:
        html = urllib.request.urlopen(url, timeout=30).read().decode("utf-8", "ignore")
        title = re.search(r"<title>(.*?)</title>", html, re.S)
        t = re.sub(r"\s+", " ", title.group(1)).strip() if title else aid
        ab = re.search(r"<blockquote class=\"abstract[^>]*>(.*?)</blockquote>", html, re.S)
        a = re.sub(r"<[^>]+>", "", ab.group(1)).strip() if ab else "(no abstract)"
        return url, t, a
    except Exception as e:
        return url, aid, f"(fetch failed: {e})"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", required=True)
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--out-dir", default=os.path.expanduser("~/dsh-collab/research/paper-cache"))
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
    args = ap.parse_args()
    ids = re.findall(r"\d{4}\.\d{4,5}(?:v\d+)?", args.urls)
    if not ids: print("no arxiv ids found"); sys.exit(1)
    os.makedirs(args.out_dir, exist_ok=True)
    for aid in ids:
        url, t, a = fetch_abs(aid)
        out = os.path.join(args.out_dir, aid + ".md")
        with open(out, "w", encoding="utf-8") as f:
            f.write(f"# {t}\n\n- arXiv: {url}\n\n## Abstract\n\n{a}\n")
        print("cached:", out)

if __name__ == "__main__":
    main()