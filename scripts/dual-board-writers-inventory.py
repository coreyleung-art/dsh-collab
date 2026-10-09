#!/usr/bin/env python3
"""★ 产出「双板写入器」可核清单（星桥说 4 个；我实测更多）
判据：同一文件内【同时】出现本地板与中央板地址，且含写操作（PUT/POST）⇒ 视为双板写入器候选。
同时给出语言（决定「抽共享 helper」是否可行）。
★ 只读扫描，不改任何文件。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import os, re, glob


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/dual-board-writers-inventory.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

LOCAL_PAT = re.compile(r"127\.0\.0\.1:8792|localhost:8792")
CENTRAL_PAT = re.compile(r"106\.53\.214\.108:8792|xingqiao\.meetfunbp\.com:8792")
WRITE_PAT = re.compile(r"\bPUT\b|['\"]PUT['\"]|method=['\"]PUT|method\s*=\s*['\"]PUT|do_put|put_json|requests\.put|urllib.*Request\(.*PUT", re.I)

ROOTS = [os.path.expanduser("~/dsh-collab")]
EXTS = (".py", ".sh", ".js", ".mjs", ".ts")
SKIP = ("node_modules", "/.git/", "/dist/", "/target/", "/logs/", "/audits/", "/venv/", "/.venv/")

seen = set()
rows = []
for root in ROOTS:
    for dirpath, dirnames, filenames in os.walk(root):
        if any(s in dirpath + "/" for s in SKIP):
            dirnames[:] = []
            continue
        if dirpath.count("/") > 6:
            dirnames[:] = []
            continue
        for fn in filenames:
            if not fn.endswith(EXTS):
                continue
            p = os.path.join(dirpath, fn)
            if p in seen:
                continue
            seen.add(p)
            try:
                if os.path.getsize(p) > 400_000:
                    continue
                src = open(p, errors="replace").read()
            except Exception:
                continue
            has_l = bool(LOCAL_PAT.search(src))
            has_c = bool(CENTRAL_PAT.search(src))
            has_w = bool(WRITE_PAT.search(src))
            if has_l and has_c:
                lang = {"py": "Python", "sh": "Shell", "js": "Node", "mjs": "Node", "ts": "TS"}[fn.rsplit(".", 1)[-1]]
                rows.append((p.replace(os.path.expanduser("~"), "~"), lang, has_w))

rows.sort()
print(f"=== 同时含【本地板】与【中央板】地址的文件（{len(rows)} 个）===")
print(f"{'语言':<8}{'含写操作':<9}文件")
for p, lang, w in rows:
    print(f"  {lang:<8}{'★是' if w else '否':<9}{p}")

by_lang = {}
for _, lang, w in rows:
    by_lang.setdefault(lang, 0)
    by_lang[lang] += 1
print(f"\n  语言分布: {by_lang}")
writers = [r for r in rows if r[2]]
print(f"  ★ 疑似双板【写入器】（含写操作）= {len(writers)} 个")
for p, lang, _ in writers:
    print(f"      [{lang}] {p}")
print("""
  ⇒ 判读：跨语言（Python 与 Node）⇒ **无法共享同一份 helper**
     可行选项：① CLI 子进程调用同一实现 ② 各语言各写同语义 helper（需同判据同验收）
              ③ 下沉到板/服务层（成本最高）""")
