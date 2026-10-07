#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""publish-package.py —— 把本地交付目录打成 tgz → base64 → **发到双板**，并**回读校验**

【为什么需要】（2026-10-03 实测沟通事故）
  我把交付包放在**本机** `~/dsh-collab/data/packages/mbp-tools-20261003/`，
  并在卡里写「交付包已在 <本机路径>」——**对端取不到我的本地文件**（我能 SSH 出向它，反向不通）
  ⇒ 对端去板上找 `data/packages/mbp-tools-20261003` 与 `.tgz-b64` 两个键**均 404**，白等一轮。
  ⇒ **交付通道必须是双方都能到达的地方（黑板键）**，不是"我机器上的某个目录"。
  ★ 与 R036「两板不传播」同源：发东西也一样，**必须显式写入、并逐板回读断言**。

【做法（每一步都可验证）】
  1. `tar czf` 打包目录（排除 `.bak*`、`__pycache__`、`.DS_Store`、AppleDouble `._*`）
  2. 计算 **sha256** 与字节数，base64 编码
  3. **PUT 到双板**（本机板=对端 mac-mini 的板；中枢）
  4. **逐板回读**：GET 回来 → base64 解码 → **重算 sha256 比对**（证明对端拿到的与我发的逐字节一致）
  5. 打印对端可直接复制的取包命令

【用法】
  python3 publish-package.py <目录或文件> [--key data/packages/xxx.tgz-b64] [--note "说明"]
  python3 publish-package.py --selftest          # 打包/校验逻辑自证（不发网）
★ 退出码（R37）：0=成功且回读一致 ／ 1=失败或回读不一致 ／ 2=环境错
"""
import argparse
import base64
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

BOARDS = [
    ("本机板(mac-mini)", "http://100.120.203.20:8792",
     {"Authorization": "Bearer bb-token-20260829-macmini"}),
    ("中枢", "http://xingqiao.meetfunbp.com:8792", None),   # 认证头运行时补
]
EXCLUDE = re.compile(r"(\.bak|__pycache__|\.DS_Store|/\._)")


def _central_headers():
    # ★ 2026-10-04 P0 修复：webhook token 不再硬编码（曾在板包/卡内联泄露）——读 ~/.dsh/webhook-token（0600）
    try:
        _wt = io.open(os.path.expanduser("~/.dsh/webhook-token"), encoding="utf-8").read().strip()
    except Exception:
        _wt = ""
    h = {}
    if _wt:
        h["X-Webhook-Token"] = _wt
    else:
        print("⚠️ 无 ~/.dsh/webhook-token，中央板写将 401（先落该文件再发布）")
    try:
        tok = io.open(os.path.expanduser("~/.dsh/blackboard-token"), encoding="utf-8").read().strip()
        if tok:
            h["X-Blackboard-Token"] = tok
    except Exception:
        pass
    return h


def pack(path, outdir=None):
    """打包 → 返回 (tgz 路径, sha256, 字节数, 文件清单)。排除备份/缓存/AppleDouble。"""
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    outdir = outdir or tempfile.mkdtemp(prefix="pkg-")
    base = os.path.basename(path.rstrip("/")) or "package"
    tgz = os.path.join(outdir, base + ".tgz")

    # ★★ 可复现打包（2026-10-03 实测发现：两次打包 sha256 不同！）
    #   原因： 会写入文件 mtime/uid/gid/uname，**gzip 头还带打包时刻**
    #   ⇒ 同一份内容两次打包哈希不同 ⇒ **「对端校验我给的 sha256」这个前提不成立**。
    #   修法：TarInfo 全部规范化（mtime=0、uid/gid=0、uname/gname 空、排序），
    #         并用 gzip.GzipFile(mtime=0) 自己压 —— 这样**同内容 ⇒ 同 sha256**。
    def _norm(ti):
        if EXCLUDE.search(ti.name):
            return None
        ti.mtime = 0
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = ""
        ti.mode = 0o755 if ti.isdir() else 0o644
        return ti

    import gzip as _gz
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for entry in sorted(os.listdir(path)):
            tf.add(os.path.join(path, entry), arcname=os.path.join(base, entry), filter=_norm)
    with open(tgz, "wb") as fh:
        with _gz.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
            gz.write(buf.getvalue())
    raw = open(tgz, "rb").read()
    names = []
    with tarfile.open(tgz, "r:gz") as tf:
        # ★ 只列**文件**（目录不进清单）：目录条目会让对端逐文件对账时困惑
        names = [m.name for m in tf.getmembers() if m.isfile() and m.name != base]
    return tgz, hashlib.sha256(raw).hexdigest(), len(raw), names


def put_key(key, payload, board_name, base, headers):
    req = urllib.request.Request(
        base + "/" + key,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="PUT",
        headers={**headers, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def get_key(key, base, headers):
    req = urllib.request.Request(base + "/" + key, headers=headers)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def _unwrap(d):
    v = d.get("value") if isinstance(d.get("value"), dict) else d
    return v.get("value") if isinstance(v.get("value"), dict) else v


def _selftest():
    print("publish-package 自证（打包 + 回读校验的判别力）")
    ok = True
    tmp = tempfile.mkdtemp(prefix="pp-selftest-")
    d = os.path.join(tmp, "demo")
    os.makedirs(d)
    io.open(os.path.join(d, "a.py"), "w", encoding="utf-8").write("print(1)\n")
    io.open(os.path.join(d, "x.bak-2026"), "w", encoding="utf-8").write("should be excluded\n")
    os.makedirs(os.path.join(d, "__pycache__"))
    io.open(os.path.join(d, "__pycache__", "c.pyc"), "w", encoding="utf-8").write("x")
    tgz, sha, size, names = pack(d, tmp)

    def chk(name, cond, det=""):
        nonlocal ok
        ok = ok and cond
        print("  %s %-42s %s" % ("✅" if cond else "❌", name, det))

    chk("打包成功且有内容", size > 0, "%d B, sha=%s" % (size, sha[:12]))
    chk("★ .bak 被排除", not any(".bak" in n for n in names), str(names))
    chk("★ __pycache__ 被排除", not any("__pycache__" in n for n in names))
    chk("正常文件被纳入", any(n.endswith("a.py") for n in names))
    # 回读判据：逐字节一致 vs 被篡改
    b64 = base64.b64encode(open(tgz, "rb").read()).decode()
    same = hashlib.sha256(base64.b64decode(b64)).hexdigest() == sha
    chk("回读 sha256 一致（正样本）", same)
    tampered = b64[:-8] + ("AAAAAAAA" if not b64.endswith("AAAAAAAA") else "BBBBBBBB")
    diff = hashlib.sha256(base64.b64decode(tampered)).hexdigest() != sha
    chk("★ 被篡改能被检出（负样本）", diff)
    # ★ 可复现性：同内容两次打包必须同 sha256（否则对端无法用我给的哈希校验）
    import time as _t
    _t.sleep(1.1)
    _tgz2, sha2, _sz2, _n2 = pack(d, tempfile.mkdtemp(prefix="pp-rp-"))
    chk("★ 可复现：两次打包同 sha256", sha2 == sha, "%s vs %s" % (sha[:12], sha2[:12]))
    print()
    print("  ⇒ %s" % ("全部通过" if ok else "存在失败项"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?")
    ap.add_argument("--key")
    ap.add_argument("--note", default="")
    ap.add_argument("--force-inplace", action="store_true",
                    help="显式允许对固定键原地覆盖（默认内容寻址，防卡/板漂移）")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return _selftest()
    if not a.path:
        print("需要 <目录或文件>"); return 2
    try:
        tgz, sha, size, names = pack(a.path)
    except Exception as e:
        print("打包失败: %s" % e); return 2
    base = os.path.basename(tgz)[:-4]
    # ★ 内容寻址键（2026-10-03）：键后缀 = 内容哈希前 8 位
    #   ⇒ 换内容必换键 ⇒ **旧卡不会因为板被覆盖而与板漂移**（对端按卡上的键取即可）
    key = a.key or ("data/packages/%s-%s.tgz-b64" % (base, sha[:8]))
    if a.key and not a.force_inplace and "\u002d" not in a.key:
        print("  ⚠️ 你指定了固定键 `%s`：该键会被后续重发**原地覆盖**，"
              "卡文将与板漂移。若非必要，建议用内容寻址键（默认行为）。" % a.key)
    # ★ 2026-10-04 P0 密钥断言（MBP 同款，fail-closed）：打包内容或 note 含 token 形态一律拒绝发布
    _secscan = b64 + a.note + "".join(names)
    if ("X-Webhook-Token" in _secscan) or ("Authorization: Bearer" in _secscan) or ("bb-token-" in _secscan):
        print("❌ 发布被拒：内容/说明含疑似密钥（X-Webhook-Token / Bearer / bb-token-*）。请先脱敏。")
        return 1
    payload = {"format": "tgz-b64", "package": base, "sha256": sha, "bytes": size,
               "files": names, "ts": int(__import__("time").time()),
               "note": a.note or ("%s 交付包（%d 字节，sha256=%s）" % (base, size, sha[:16]))}
    payload["b64"] = base64.b64encode(open(tgz, "rb").read()).decode()

    print("打包: %s  (%d B, sha256=%s, %d 个文件)" % (base, size, sha[:16], len(names)))
    print("板键: %s" % key)
    # ★ 幂等发布（2026-10-03）：键已存在且**内容哈希一致** ⇒ 跳过 PUT
    #   理由：内容寻址键下重发同内容只会白白抬升板 version（对端比对 version 时会困惑），
    #   而内容一模一样 ⇒ 跳过既安全又减少板端写入。**只有内容变了才写。**
    skipped = []
    for name, url, h in BOARDS:
        hh = dict(h) if h else _central_headers()
        try:
            d0 = get_key(key, url, hh)
            i0 = _unwrap(d0)
            if (i0.get("sha256") or "") == sha:
                skipped.append(name)
        except Exception:
            pass
    if len(skipped) == len(BOARDS):
        print("  ℹ️ 两板均已有**同哈希**内容 ⇒ 跳过重发（幂等，避免抬高 version 造成对端困惑）")
        print("  → 对端仍按卡上的键取；内容未变，哈希未变 ✅")
        print()
    results = []
    for name, url, h in BOARDS:
        if name in skipped:
            results.append((name, "跳过（已存在同哈希内容）"))
            continue
        hh = dict(h) if h else _central_headers()
        try:
            d = put_key(key, payload, name, url, hh)
            results.append((name, "PUT ok v=%s" % d.get("version")))
        except Exception as e:
            results.append((name, "PUT 失败: %s" % str(e)[:60]))
    # ★ 逐板回读 + 逐字节校验
    print("回读校验（证明对端拿到的与我发的逐字节一致）：")
    allok = True
    for name, url, h in BOARDS:
        hh = dict(h) if h else _central_headers()
        try:
            d = get_key(key, url, hh)
            inner = _unwrap(d)
            rb = base64.b64decode(inner.get("b64") or "")
            same = hashlib.sha256(rb).hexdigest() == sha
            allok = allok and same
            print("  %s %-18s sha256 %s（%d B）" % ("✅" if same else "❌", name,
                  (hashlib.sha256(rb).hexdigest()[:16] if rb else "空"), len(rb)))
        except Exception as e:
            allok = False
            print("  ❌ %-18s 回读失败: %s" % (name, str(e)[:60]))
    print()
    for n, r in results:
        print("  PUT %-18s %s" % (n, r))
    print()
    # ★ 生成「可直接粘贴到卡里的片段」——清单由**打包器**产出，杜绝手打漏项
    #   起因（2026-10-03）：我在卡里手写文件清单，漏了 check-hazards-consistency.py（声明≠实际）。
    print("─" * 70)
    print("可粘贴卡片段（清单由打包器生成，请勿手打）：")
    print("  板键: %s  ← **内容寻址（后缀=%s）**" % (key, sha[:8]))
    print("  用法: 对端按**卡上的键**取即可；换内容会自动换键，不会原地覆盖 ⇒ 无卡/板漂移")
    print("  字节: %d ／ sha256: %s" % (size, sha))
    print("  文件(%d): %s" % (len(names), " / ".join(os.path.basename(n) for n in names)))
    print("  ★ 对端请以载荷内 files 字段为准对账（本清单即由它生成）")
    print("─" * 70)
    print("对端取包命令（可直接复制）：")
    print("""  curl -s -H "X-Blackboard-Token: $TOK" -H "Authorization: Bearer $TOK" \\
    "http://xingqiao.meetfunbp.com:8792/%s" -o /tmp/p.json
  python3 -c "import json,base64;d=json.load(open('/tmp/p.json'));v=d.get('value',d);v=v.get('value',v);open('/tmp/%s','wb').write(base64.b64decode(v['b64']))"
  shasum -a 256 /tmp/%s   # 期望 %s""" % (key, base + ".tgz", base + ".tgz", sha))
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
