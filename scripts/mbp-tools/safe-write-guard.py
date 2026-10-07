#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
safe-write-guard —— 覆盖式写入护栏（防「目标独有内容被静默冲掉」）

【为什么存在】
2026-10-03 事故 #5：脚本生成 JSON 覆盖 `data/ops/resource-constraints.json`，
把**手写、用户定案**的 RC-001（微信/企业微信禁动清单）整条冲掉。
同类历史事故：`rsync --delete` 部署删掉源包未带的 `cordis.patch.yml`（事故 #3/#4）。

共同形态（归类 A）：**覆盖式写入默认「目标只能是源里也有的东西」** ——
而现实中目标常含**源里没有、又必须保留**的内容（手写条目、配置文件、独有字段）。

为什么原有的护栏没拦住：
  · `write`/`edit` 工具的「写前必读」策略**只约束工具调用**；
    脚本内 `open(path,"w")` / `json.dump(...)` **完全绕过**该策略。
  · 「我记得先读」属**纪律**，不是**结构** ⇒ 换一个会话/一次上下文压缩即失效。

【做什么】fail-closed：目标存在且有「新内容里没有」的内容 ⇒ **拒绝写入**，
除非显式 `preserve_target_only=True`（承认并自行保全）或 `allow_clobber=True`（显式放弃）。
另：任何写入前**自动留 `.bak-safewrite-<stamp>`**，最坏情况可回滚。

【用法】
  from safe_write_guard import guarded_write
  guarded_write(path, text)                     # 有独有内容则抛 TargetOnlyContentError
  guarded_write(path, text, allow_clobber=True) # 显式放弃（会在结果里留痕）

  CLI:
    python3 safe-write-guard.py --check <target> --new <newfile>   # 只报告，exit 1 = 有独有内容
    python3 safe-write-guard.py --selftest                          # 正负样本自证

【边界（别过度信任它）】
  · 只比「顶层键 / 行」级别的**存在性**，不判语义 → 内容是「同一键但语义变了」它**无判别力**。
  · 非 UTF-8 / 二进制文件走字节比对，仅报告大小差异。
  · 它不是「内容正确性」判据 —— 只回答一个问题：**这次写会不会让目标独有的东西消失**。
"""

import json
import os
import re
import sys
import shutil
import datetime

STAMP_FMT = "%Y%m%d-%H%M%S"


class TargetOnlyContentError(RuntimeError):
    """目标含新内容里没有的内容 —— fail-closed 拒绝写入。"""

    def __init__(self, path, only_json_keys, only_lines):
        self.path = path
        self.only_json_keys = only_json_keys
        self.only_lines = only_lines
        parts = ["拒绝覆盖 %s：目标独有内容会被冲掉（fail-closed）" % path]
        if only_json_keys:
            parts.append("  JSON 顶层独有键(%d): %s" % (len(only_json_keys), ", ".join(only_json_keys[:12])))
        if only_lines:
            parts.append("  文本独有行(%d)，示例: %s"
                         % (len(only_lines), " | ".join(l.strip()[:60] for l in only_lines[:5])))
        parts.append("  → 若要继续：显式 allow_clobber=True（放弃），或读入后自行合并（推荐）")
        super().__init__("\n".join(parts))


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (UnicodeDecodeError, OSError):
        return None


def target_only_content(path, new_text):
    """返回 (json独有键列表, 文本独有行列表)。文件不存在 ⇒ ([], [])。"""
    if not os.path.isfile(path):
        return [], []
    old_text = _read_text(path)
    if old_text is None or new_text is None:
        return [], []
    if old_text == new_text:
        return [], []

    old_j = new_j = None
    try:
        old_j = json.loads(old_text)
        new_j = json.loads(new_text)
    except Exception:
        pass
    if isinstance(old_j, dict) and isinstance(new_j, dict):
        only = [k for k in old_j if k not in new_j]
        # dict 型 JSON：顶层键就是判据，不再叠加行比对（避免噪声）
        return only, []

    old_lines = set(l for l in old_text.splitlines() if l.strip())
    new_lines = set(l for l in new_text.splitlines() if l.strip())
    only_lines = sorted(old_lines - new_lines)
    return [], only_lines


def guarded_write(path, text, preserve_target_only=False, allow_clobber=False,
                  backup=True, encoding="utf-8", quiet=False):
    """覆盖式写入护栏。返回 dict（含是否留备份、被拦/放行原因）。"""
    path = os.path.abspath(os.path.expanduser(path))
    existed = os.path.isfile(path)

    keys, lines = ([], []) if allow_clobber else target_only_content(path, text)
    if (keys or lines) and not (preserve_target_only or allow_clobber):
        raise TargetOnlyContentError(path, keys, lines)

    bak = None
    if existed and backup:
        bak = "%s.bak-safewrite-%s" % (path, datetime.datetime.now().strftime(STAMP_FMT))
        shutil.copy2(path, bak)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding=encoding) as f:
        f.write(text)

    # 写后读回（R030：声明必须有读回证据）
    with open(path, "r", encoding=encoding) as f:
        back = f.read()
    ok = (back == text)
    res = {"path": path, "existed": existed, "backup": bak, "bytes": len(text.encode(encoding)),
           "readbackOk": ok, "targetOnlyKeys": keys, "targetOnlyLines": len(lines),
           "clobbered": bool(keys or lines) and not preserve_target_only}
    if not ok:
        raise RuntimeError("写后读回不一致：%s" % path)
    if not quiet:
        print("✅ 写入 %s（%d bytes，读回一致）%s" % (path, res["bytes"],
              "  备份=%s" % os.path.basename(bak) if bak else "  （新建文件）"))
        if res["clobbered"]:
            print("   ⚠️ 本次为 allow_clobber，目标独有内容已放弃：%s%s"
                  % (keys[:8], "..." if len(keys) > 8 else ""))
    return res


# ─────────────────────────── 正负样本自证（类别 C 纪律）───────────────────────────
def _selftest():
    import tempfile
    ok = True
    tmp = tempfile.mkdtemp(prefix="swg-selftest-")

    def case(name, fn, expect_raise):
        nonlocal ok
        try:
            fn()
            raised = False
        except TargetOnlyContentError:
            raised = True
        good = (raised == expect_raise)
        ok = ok and good
        print("  %s %-52s 期望%s / 实际%s"
              % ("✅" if good else "❌", name,
                 "拒绝" if expect_raise else "放行", "拒绝" if raised else "放行"))

    # ── JSON 层 ──────────────────────────────────────────────────────────
    def neg_json_preserved():
        p = os.path.join(tmp, "a.json")
        json.dump({"schema": "v1", "constraints": [1], "ledgerIndex": {"keys": []}},
                  open(p, "w", encoding="utf-8"))
        # 新内容把旧的两个独有键都保留
        guarded_write(p, json.dumps({"schema": "v1", "constraints": [1],
                                     "ledgerIndex": {"keys": [2]}}, ensure_ascii=False), quiet=True)

    def pos_json_clobber():
        p = os.path.join(tmp, "b.json")
        json.dump({"schema": "v1", "constraints": [{"id": "RC-001"}]},
                  open(p, "w", encoding="utf-8"))
        # 复刻事故 #5：新内容没有 constraints 键
        guarded_write(p, json.dumps({"schema": "v1", "ledgerIndex": {"keys": []}}), quiet=True)

    # ── 文本层 ───────────────────────────────────────────────────────────
    def pos_text_clobber():
        p = os.path.join(tmp, "c.md")
        open(p, "w", encoding="utf-8").write("# 标题\n## 手写章节：用户定案\n正文\n")
        guarded_write(p, "# 标题\n## 自动生成章节\n正文\n", quiet=True)

    def neg_text_superset():
        p = os.path.join(tmp, "d.md")
        open(p, "w", encoding="utf-8").write("# 标题\n正文\n")
        guarded_write(p, "# 标题\n正文\n新增行\n", quiet=True)

    def neg_new_file():
        guarded_write(os.path.join(tmp, "e.txt"), "全新内容", quiet=True)

    def neg_identical():
        p = os.path.join(tmp, "f.txt")
        open(p, "w", encoding="utf-8").write("同一内容\n")
        guarded_write(p, "同一内容\n", quiet=True)

    # ── 逃生门必须真的能开（否则护栏会变成「一律拒绝」的假判据）────────────
    def neg_allow_clobber():
        p = os.path.join(tmp, "g.json")
        json.dump({"old": 1}, open(p, "w", encoding="utf-8"))
        guarded_write(p, json.dumps({"new": 2}), allow_clobber=True, quiet=True)

    def neg_preserve_flag():
        p = os.path.join(tmp, "h.json")
        json.dump({"old": 1}, open(p, "w", encoding="utf-8"))
        guarded_write(p, json.dumps({"new": 2}), preserve_target_only=True, quiet=True)

    # ── 备份与读回必须真实发生 ───────────────────────────────────────────
    def pos_backup_created():
        p = os.path.join(tmp, "i.txt")
        open(p, "w", encoding="utf-8").write("v1\n")
        r = guarded_write(p, "v1\nv2\n", quiet=True)
        assert r["backup"] and os.path.isfile(r["backup"]), "未留备份"
        assert r["readbackOk"], "读回不一致"

    def pos_backup_contents():
        p = os.path.join(tmp, "j.txt")
        open(p, "w", encoding="utf-8").write("原始内容\n")
        r = guarded_write(p, "原始内容\n追加\n", quiet=True)
        assert open(r["backup"], encoding="utf-8").read() == "原始内容\n", "备份内容不对"

    print("safe-write-guard 自证（正负样本，防「无论如何都通过」）")
    print("── 应拒绝（正样本）──")
    case("JSON：新内容缺旧独有键（=事故#5 复刻）", pos_json_clobber, True)
    case("文本：新内容缺旧独有行", pos_text_clobber, True)
    print("── 应放行（负样本，防过杀）──")
    case("JSON：旧独有键全部保留", neg_json_preserved, False)
    case("文本：新内容是旧内容的超集", neg_text_superset, False)
    case("目标不存在（新建）", neg_new_file, False)
    case("内容完全相同", neg_identical, False)
    case("显式 allow_clobber 逃生门", neg_allow_clobber, False)
    case("显式 preserve_target_only 逃生门", neg_preserve_flag, False)
    print("── 写后证据必须真实（R030）──")
    case("写入后留 .bak 且读回一致", pos_backup_created, False)
    case("备份内容 = 写入前内容", pos_backup_contents, False)

    shutil.rmtree(tmp, ignore_errors=True)
    print()
    print("⇒ %s" % ("全部通过" if ok else "存在失败项"))
    return 0 if ok else 1


PROTECTED = [
    "rules-registry/rules.json",
    "rules-registry/RULES.md",
    "data/ops/resource-constraints.json",
    "hazards/INDEX.md",
    "hazards/rules.md",
    "hazards/patterns/00-总表.md",
]

_RAW_WRITE = re.compile(
    r"""(?:io\.open|open)\s*\([^)]*['"]w['"]"""
    r"""|json\.dump\s*\("""
    r"""|\.write_text\s*\(""")


def audit_protected_writes(root=None, tools_dir=None):
    """扫描脚本目录，找出「把裸写真正作用到受保护文件上」的脚本。

    返回 [(脚本, 行号, 行内容, 命中文件), ...]

    ★ 判据边界（避免退化成"白名单式自查"那种无效判据）：
      本审计**只覆盖 PROTECTED 里列出的文件**，对其它文件的裸写**不报**。
      ⇒ 它证明的是「**受保护集合**内没有被裸写」，**不是**「全仓无裸写」。

    ★★ v2 修正（**初版是个坏判据，已废弃**）：
      初版规则是「该行提到受保护文件名 + 该文件里存在任一裸写」⇒ 实测在真实仓库上
      报了 **40+ 处**，绝大多数是 `print("rules.json ...")`、注释、路径常量声明。
      噪声判据 = 恒报警 ⇒ **会训练人忽略它**（与类别 C′「恒失败的自测」同型）。
      ⇒ 改为**按变量绑定精确定位**：
        ① 先扫出 `VAR = ...<受保护文件名>...` 的绑定；
        ② 只在「裸写调用」行里出现**这些变量**（或直接出现受保护路径字面量）时才报。
      ⇒ 报的是「**这条写入语句的落点就是受保护文件**」，而不是「这个文件提到过它」。
    """
    import glob as _glob
    root = root or os.path.expanduser("~/dsh-collab")
    tdir = tools_dir or os.path.join(root, "tools")
    bases = {os.path.basename(p): p for p in PROTECTED}
    hits = []
    for ext in ("*.py", "*.mjs", "*.js", "*.sh"):
        for f in sorted(_glob.glob(os.path.join(tdir, "**", ext), recursive=True)):
            if os.path.basename(f) == "safe-write-guard.py":
                continue
            src = _read_text(f)
            if src is None:
                continue
            uses_guard = ("safe_write_guard" in src or "safe-write-guard" in src
                          or "guarded_write" in src)
            if uses_guard:
                continue
            lines = src.splitlines()

            # ① 变量绑定：VAR = ...<受保护文件名>...
            #    ★ 必须**按 `;` 拆开复合赋值**：实测 `JP = os.path.join(R,"rules.json"); MP =
            #      os.path.join(R,"RULES.md")` 写在一行时，旧的逐 base 覆盖会把 JP 错标成
            #      RULES.md（后匹配者覆盖）⇒ 文件标签张冠李戴，triage 会指错对象。
            var2prot = {}
            for ln in lines:
                for frag in ln.split(";"):
                    m = re.match(r"\s*([A-Za-z_]\w*)\s*=\s*(.+)$", frag)
                    if not m or _RAW_WRITE.search(frag):
                        continue
                    var, rhs = m.group(1), m.group(2)
                    for base, full in bases.items():
                        if base in rhs:
                            var2prot[var] = full
                            break            # 只认第一个命中，不再覆盖

            # 临时副本识别（降噪）：脚本若用 mkdtemp/tempfile，其命中可能是**临时副本**
            _tmpish = ("mkdtemp" in src or "tempfile" in src)

            # ② 裸写调用行：必须**真正**指向受保护文件
            for i, ln in enumerate(lines, 1):
                s = ln.strip()
                if s.startswith("#") or not _RAW_WRITE.search(ln):
                    continue
                target = None
                for base, full in bases.items():
                    if base in ln:                       # 直接字面量
                        target = full; break
                if target is None:
                    for var, full in var2prot.items():
                        if re.search(r"\b%s\b" % re.escape(var), ln):
                            target = full; break
                if target:
                    # 高/低置信分开报：含 tempfile 的脚本**可能**写的是临时副本，不许冒充确证
                    conf = "低置信(疑似临时副本)" if _tmpish else "确证"
                    hits.append((f, i, s[:110], target, conf))
    return hits


def _main(argv):
    if "--selftest" in argv:
        return _selftest()
    if "--audit" in argv:
        root = None
        if "--root" in argv:
            root = argv[argv.index("--root") + 1]
        hits = audit_protected_writes(root=root)
        print("受保护写入审计（覆盖 %d 个文件；★ 只覆盖这个集合，不等于全仓无裸写）" % len(PROTECTED))
        for p in PROTECTED:
            print("    · %s" % p)
        print()
        if not hits:
            print("✅ 未发现「引用受保护文件 + 裸写 + 未接线」的脚本")
            return 0
        conf_hits = [h for h in hits if h[4] == "确证"]
        low_hits = [h for h in hits if h[4] != "确证"]
        print("⚠️ 发现 %d 处裸写（确证 %d / 低置信 %d）"
              "—— 这些脚本若被重跑，不受 guarded_write 保护："
              % (len(hits), len(conf_hits), len(low_hits)))
        for f, i, ln, tgt, conf in conf_hits + low_hits:
            print("    [%s] %s:%d  → %s"
                  % (conf, f.replace(os.path.expanduser("~"), "~"), i, tgt))
            print("       %s" % ln)
        return 1
    if "--check" in argv:
        t = argv[argv.index("--check") + 1]
        n = None
        if "--new" in argv:
            n = _read_text(argv[argv.index("--new") + 1])
        else:
            n = sys.stdin.read()
        keys, lines = target_only_content(t, n)
        if keys or lines:
            print("⚠️ 目标独有内容会被冲掉：")
            for k in keys:
                print("    JSON 键: %s" % k)
            for l in lines[:20]:
                print("    文本行: %s" % l.strip()[:100])
            return 1
        print("✅ 无目标独有内容丢失风险：%s" % t)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
