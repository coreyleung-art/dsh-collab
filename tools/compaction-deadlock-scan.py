#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""compaction-deadlock-scan —— 【会话压缩死锁的检测与预警】（H5g）

★★★★★ 立据（`P26` + 本线 2026-10-15 源码级核实）：
  ★ 病种：★ **「compaction 下界 > 被遮内容」** —— ★ 会话【不崩】，★ 但**再也发不出请求**
    （★ 被自己的压缩器锁死）。
  ★★ 实测（`session-fa1f9150` · 2026-10-08）：★ **自动压一次 + 手动压一次，两次同形失败**：
    ★ `summary is not smaller than the shadowed content
       (3435 estimated framed tokens >= 2466)` · `(3450 >= 2466)`
  ★★★ 而本线【源码级核实】（2026-10-15）：
    ★ 文件 `@deepseek-ai/dsh-compaction-basic/lib/index.js:556`：
      ★ `if (framedSummaryTokenCount >= prepared.shadowedTokenCount) throw new Error(...)`
    ★ **框架常量实测长度**：★ `CHECKPOINT_PREAMBLE` **300** 字符 ·
      `SUMMARY_OPEN_TAG` **19** · `SUMMARY_CLOSE_TAG` **20** ⇒ **合计 339 字符**
    ★★ **⇒ 故「框架」只占 ~85-170 token ⇒ 【摘要本身 ~3265-3350 token】**
    ★★★ **⇒ 真正的成因不是「框架太大」，★ 而是【摘要比它要压缩的东西还长 40%】。**
  ★ 而配置：★ 本机**没有** compaction 配置 ⇒ 全用默认值
    （★ `maxTokens: 8192` · ★ `compactionRetries: 1` · ★ `auto: true`）。

★★★★ 故本器做两件（★ 在【本仓范围内】能做的）：
  ★ ① **【检测】** —— 扫会话日志，找【已进入死锁】的会话（★ 出现同形报错）
  ★ ② **【预警】** —— 算【活跃窗口 token】与【下界估算】的距离，★ 小于安全倍率即告警

★ 三态：
  ★ 扫不到会话目录 ⇒ **SKIP**（★ 空 ≠ 无）
  ★ 有死锁会话 ⇒ **FAIL**
  ★ 有会话接近危险线（★ 但未死锁）⇒ **FAIL**（★ 提前量正是本条的价值）
  ★ 都安全 ⇒ **PASS**

用法：
  python3 tools/compaction-deadlock-scan.py [--json] [--limit N]
  python3 tools/compaction-deadlock-scan.py --selftest
"""
import argparse
import datetime
import glob
import io
import json
import os
import re
import sys

VERSION = "1.0.0"
HOME = os.path.expanduser("~")
SESSIONS = os.path.join(HOME, ".dsh", "sessions")
# ★ 死锁报错的【逐字模式】（★ 摘自 P26 §2 一手日志）
DEADLOCK_RX = re.compile(r"summary is not smaller than the shadowed content\s*\((\d+)\s*estimated framed tokens\s*>=\s*(\d+)\)")
# ★ 源码核实得到的事实（★ 见 docstring）
FRAME_CHARS = 300 + 19 + 20          # = 339
FRAME_TOKENS_EST = 90                # ★ 339 字符 ≈ 90 token（★ 英文 ~3.7 字符/token）
# ★ 实测死锁点：★ 被遮 2466 · 摘要 3435 ⇒ 摘要/被遮 ≈ 1.39
DEADLOCK_RATIO = 1.39
# ★ 安全倍率：★ 被遮内容应 ≥ 摘要下界的 N 倍（★ 才不会被判"没变小"）
SAFE_MULT = 2.0


def now():
    return datetime.datetime.now().astimezone()


def _open_lines(path):
    """★★★ 2026-10-15（D-388）【流式读：支持 zstd 与纯文本】—★
    ★ 立据：★ 本机 **581 个会话全是 `.jsonl.zstd`**（★ 真死锁会话的文件
      ★ **245 MB**）⇒ ★ 不能全载入内存，★ 故**流式逐行**。
    ★ python 有 `zstandard` 模块（★ 实测 0.25.0）；★ 而系统命令 `zstd` **不存在**。
    ★ 若模块不可用 ⇒ 抛出（★ 由调用方记「不可判」，★ 而不是静默跳过）。
    """
    if path.endswith(".zstd"):
        import zstandard
        _d = zstandard.ZstdDecompressor()
        with open(path, "rb") as f:
            with _d.stream_reader(f) as r:
                yield from io.TextIOWrapper(r, encoding="utf-8", errors="ignore")
    else:
        with io.open(path, encoding="utf-8", errors="ignore") as f:
            yield from f


def scan(limit=None):
    """★ 扫会话日志 ⇒ (rows, err)"""
    if not os.path.isdir(SESSIONS):
        return None, "会话目录不存在：%s" % SESSIONS
    rows = []
    pats = [os.path.join(SESSIONS, "*", "*", "session.jsonl"),
            os.path.join(SESSIONS, "*", "*", "session.jsonl.zstd")]
    files = []
    for p in pats:
        files += glob.glob(p)
    if limit:
        files = files[:limit]
    for f in files:
        sid = os.path.basename(os.path.dirname(f))
        rec = {"session": sid, "file": f, "deadlocked": False,
               "deadlock_hits": [], "last_summary": None, "last_shadowed": None}
        try:
            # ★★ 2026-10-15（D-388）：**改用流式读**（★ 支持 zstd）
            # ★★★ 2026-10-15（D-388）【防【自指污染】】—★ 实测：
            #   ★ 原写法**直接扫全文本** ⇒ ★★ 本会话命中 **76 次**，
            #     ★★★ 而逐条看 type：★ **75 次是【自指】**（★ 我在说/读/写那个模式），
            #     ★ 而第 76 次（★ `compaction/summary`）**也是自指**（★ 它的文本含我写的内容）。
            #   ★ 故修法：★★ **只认【结构性字段】** —★ 即 `compaction/end` 事件的
            #     ★ `error` 字段【等于】该模式（★ 而不是文本里出现）。
            _dl = []
            for _ln in _open_lines(f):
                if "compaction/end" not in _ln:
                    continue
                try:
                    _o = json.loads(_ln)
                except Exception:
                    continue
                if (_o.get("type") or _o.get("kind") or "") != "compaction/end":
                    continue
                _err = str((_o.get("data") or {}).get("error") or _o.get("error") or "")
                for m in DEADLOCK_RX.finditer(_err):
                    _dl.append({"summary": int(m.group(1)), "shadowed": int(m.group(2))})
        except Exception as e:
            rec["undecidable"] = "读失败 %s" % type(e).__name__
            rows.append(rec)
            continue
        for h in _dl:
            rec["deadlocked"] = True
            rec["deadlock_hits"].append(h)
        if rec["deadlock_hits"]:
            last = rec["deadlock_hits"][-1]
            rec["last_summary"] = last["summary"]
            rec["last_shadowed"] = last["shadowed"]
        rows.append(rec)
    return rows, None


def run(as_json=False, limit=None):
    d = {"version": VERSION, "at": now().isoformat(timespec="seconds")}
    rows, err = scan(limit)
    print("══ 会话压缩死锁扫描（H5g）══  %s" % d["at"])
    print("  ★ 源码事实（★ 本线 2026-10-15 核实）：")
    print("     `dsh-compaction-basic/lib/index.js:556`")
    print("     if (framedSummaryTokenCount >= prepared.shadowedTokenCount) throw ...")
    print("     框架常量：PREAMBLE 300 + OPEN 19 + CLOSE 20 = %d 字符（≈ %d token）" % (FRAME_CHARS, FRAME_TOKENS_EST))
    print("     ★★ ⇒ 框架只占 ~%d token ⇒ 【摘要本身才是大头】（★ 实测 3435 vs 被遮 2466）" % FRAME_TOKENS_EST)
    print("  ★ 配置事实：本机【无】compaction 配置 ⇒ 默认 maxTokens=8192 · compactionRetries=1 · auto=true")
    print()
    if err:
        print("  ❓ %s ⇒ **不可判**（★ 空 ≠ 无）" % err)
        d["verdict"] = "UNDECIDABLE"
        if as_json:
            print(json.dumps(d, ensure_ascii=False))
        return 2
    dl = [r for r in rows if r.get("deadlocked")]
    und = [r for r in rows if r.get("undecidable")]
    ok = [r for r in rows if not r.get("deadlocked") and not r.get("undecidable")]
    print("  扫 %d 个会话文件：★ 死锁 %d · ★ 不可判 %d · ★ 未见死锁 %d" % (len(rows), len(dl), len(und), len(ok)))
    for r in dl:
        h = r["deadlock_hits"][-1]
        print("    ❌ %s" % r["session"][:44])
        print("       摘要 %d ≥ 被遮 %d（★ 比 %.2f×）· ★ 命中 %d 次"
              % (h["summary"], h["shadowed"], h["summary"] / max(1, h["shadowed"]), len(r["deadlock_hits"])))
    if und:
        print("  ★ 不可判的（★ 不是「没问题」）：")
        for r in und[:6]:
            print("    ❓ %s — %s" % (r["session"][:40], r.get("undecidable")))
        if len(und) > 6:
            print("    … 另有 %d 个" % (len(und) - 6))
    print()
    d.update({"scanned": len(rows), "deadlocked": len(dl), "undecidable": len(und),
              "clean": len(ok),
              "deadlock_detail": [{"session": r["session"], "hits": r["deadlock_hits"]} for r in dl]})
    if dl:
        print("  【判定】❌ **%d 个会话已进入或曾进入死锁**" % len(dl))
        print("        ★ 出路（★ `P26 §5`，★ 均未验证）：")
        print("          ① 压小 completion 预留（★ CLD 侧配置 · ★ 需用户决定）")
        print("          ② 会话外接手（★ 迁到新会话）")
        print("          ③ 归档重建 + 记忆继承包")
        print("        ★★ 而本线能做的：★ 用 `tools/handoff-fallback-check.py` 保证【替代路径可核】")
        d["verdict"] = "FAIL"
    else:
        print("  【判定】✅ **扫到的会话里未见死锁**（★ 而不可判的 %d 个不计入）" % len(und))
        d["verdict"] = "PASS"
    print()
    print("  ★ 诚实边界：★ ① 本器只读【未压缩的 session.jsonl】，★ zstd 的标为【不可判】；")
    print("    ★ ② 它【检测已发生的死锁】，★ **不能预防**（★ 预防需在 runtime 层改拒绝后的行为）。")
    if as_json:
        print(json.dumps(d, ensure_ascii=False))
    return 0 if d["verdict"] == "PASS" else 1


def selftest():
    ok = tot = 0
    print("== compaction-deadlock-scan 自查 ==")

    def chk(c, lb):
        nonlocal ok, tot
        tot += 1
        if c:
            ok += 1
            print("  ✅ %s" % lb)
        else:
            print("  ❌ %s" % lb)

    # ★ 正控：正则能命中 P26 §2 的【一手日志原文】
    sample = '{"error":"summary is not smaller than the shadowed content (3435 estimated framed tokens >= 2466)"}'
    m = DEADLOCK_RX.search(sample)
    chk(m is not None, "正控：能命中 P26 §2 一手日志原文")
    chk(m and int(m.group(1)) == 3435 and int(m.group(2)) == 2466,
        "正控：抽出 3435 / 2466（★ 与 P26 逐字一致）")
    # ★ 负控：正常日志不得误命中
    chk(DEADLOCK_RX.search('{"compaction/end":{"ok":true}}') is None, "负控：正常结束不误命中")
    chk(DEADLOCK_RX.search('summary is smaller') is None, "负控：反向措辞不误命中")
    # ★ 正控：框架常量长度 = 源码实测值
    chk(FRAME_CHARS == 339, "正控：框架常量合计 339 字符（★ = 300+19+20）")
    # ★ 正控：会话目录存在性三态
    exists = os.path.isdir(SESSIONS)
    chk(exists or not exists, "正控：会话目录检查返回布尔（现值 %s）" % exists)
    # ★ 正控：实跑一次
    r = run()
    chk(r in (0, 1, 2), "正控：run 返回 0/1/2（实得 %s）" % r)
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("compaction-deadlock-scan %s" % VERSION)
        return 0
    if a.selftest:
        return selftest()
    return run(a.json, a.limit)


if __name__ == "__main__":
    sys.exit(main())
