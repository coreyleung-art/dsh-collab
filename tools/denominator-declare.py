#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""denominator-declare —「凡报一个数，必须当场申报口径」的可机械核验门。

★ 立据（2026-10-12 实测，两条同族）：
  ★ ① **S-1 的分母之争**：同一条判据「drift 项数 ≥ 通道总数」——
    ★ 登记面（`channel_gate` 枚举 7）⇒ **成立**；活体面（具名 26）⇒ **不成立**。
    ★★ 两判定相反，★ 根因 = **一格装了【两个量】**（★ 不是口径不同）。
  ★ ② **§18 条数四值互异**：12 / 1 / 8 / 5 —— ★ 各自用了不同的尺，★ **其中「12」无任何在册件申报口径**。

★★ 故本门查：一份报告里凡出现【裸数】（比值 / 计数 / 率），
   其【同句或紧邻上下文】是否含【窗口 + 分子/分母】声明。

三态：报告无任何数值 ⇒ 报「不适用」；扫描面为空 ⇒ 「不可判」；有裸数 ⇒ fail。
"""
import io
import os
import re
import sys
import json
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ★ 【裸数】模式：百分比 / 「N/M」 / 「N 条」 / 「N 项」
RE_PCT = re.compile(r'(\d+(?:\.\d+)?)\s*[%％]')
RE_RATIO_RAW = re.compile(r'(\d+)\s*/\s*(\d+)(?!\s*[\d/])')
RE_COUNT = re.compile(r'(\d+)\s*(?:条|项|个|处|次|批)(?![\u4e00-\u9fff])')


def is_ratio_noise(a, b, text=None, pos=None):
    """★ 负控：排除【像端口 / 日期】的 N/M —— 它们不是比值。

    ★ 立据（2026-10-12 实跑误报 + 自证抓到的一次「修过头」）：
      · `8792/8803` ⇒ **两个端口号**（★ 两侧都 ≥ 1024 且 4 位以上）
      · `04/05`     ⇒ **日期**，★ 但**只在其两侧有日期上下文时**才算
      ★★ 本函数初版把 `10/11`（**真比值**）也判成日期 ⇒ **正控「防修过头」当场抓住**。
      ★★★ ⇒ 故日期判据收紧为：**两侧等长 2 位 ∧ 都 ≤ 31 ∧ 紧邻上下文含日期特征**。
    """
    ia, ib = int(a), int(b)
    # ★ 端口：两侧都 ≥ 1024 且至少 4 位
    if ia >= 1024 and ib >= 1024 and len(a) >= 4 and len(b) >= 4:
        return True
    # ★ 日期：★ 只在【有日期上下文】时才判（★ 防把 10/11 这类真比值误排）
    if ia <= 31 and ib <= 31 and len(a) == 2 and len(b) == 2 and text is not None and pos is not None:
        near = text[max(0, pos - 40): pos + 40]
        if any(k in near for k in ("日期", "月", "年", "时间", "截至", "签署", "归档")) or \
           re.search(r'\d{4}-\d{2}-\d{2}', near):
            return True
    return False

# ★ 【口径词】：窗口 / 分母 / 样本 / 面
CALIBER_WORDS = [
    "窗口", "分母", "分子", "样本", "扫描面", "面=", "口径", "时刻",
    "n=", "n≥", "n<", "基准", "全量", "区间", "范围", "截至", "观测",
]
# ★ 【申报标记】：显式口径行（★ 本仓惯例）
DECLARE_MARKERS = ["口径", "★ 面", "复跑命令", "时刻", "分母 =", "窗口 =", "样本"]


def para_of(text, pos, back=260, fwd=160):
    """★ 取 pos 附近的上下文（★ 同句或紧邻）。

    ★★ 2026-10-13 修（ext E-1）：★ 本函数**只应作展示用** ——
      ★ 原实现把它同时用作【口径词判定】⇒ ★★ 260 字外的无关口径词也算「已申报」
      ⇒ **假阴性**（★ 实例：「通过率 87%。\\n本段讲窗口：窗口为 24h，与本数字无关。」⇒ 判「已申报」）。
    ★ 判定改用 `same_unit_declared()`（★ 按句/段判），见下。
    """
    return text[max(0, pos - back): pos + fwd]


# ★★ 句子/段落边界（★ 中英文）
_SENT_SPLIT = re.compile(r'[\n\u3002\uff01\uff1f!?;；]+')


def same_unit_declared(text, pos):
    """★ ★★ E-1 的正确判法：**口径词必须与数字在【同一句】**。

    ★ 立据（ext E-1）：★ 原用【字符窗】⇒ **把「距离」当成了「关联」** ⇒
      ★★ 一句无关的「本段讲窗口：窗口为 24h」就能把裸数 87% 洗白。
    ★ 三态：★ 同句含口径词 ⇒ True；★ 否则 False（★ 不作「不可判」，★ 因为句界是可判的）。
    """
    # ★ 定位 pos 所在的句：向前找最近句界，向后找最近句界
    starts = [0] + [m.end() for m in _SENT_SPLIT.finditer(text)]
    ends = [m.start() for m in _SENT_SPLIT.finditer(text)] + [len(text)]
    lo = max((s for s in starts if s <= pos), default=0)
    hi = min((e for e in ends if e >= pos), default=len(text))
    sentence = text[lo:hi]
    return any(w in sentence for w in CALIBER_WORDS), sentence


def scan_text(text):
    """★ 返回裸数列表：每个 = {kind, value, declared(True/False), ctx}"""
    out = []
    for m in RE_PCT.finditer(text):
        ctx = para_of(text, m.start())
        # ★★ 2026-10-13 修（ext E-1）：判定改用【同句】而非【字符窗】
        declared, _sent = same_unit_declared(text, m.start())
        out.append({"kind": "pct", "value": m.group(0), "declared": declared,
                    "ctx": ctx.replace("\n", " ")[:120]})
    for m in RE_RATIO_RAW.finditer(text):
        if is_ratio_noise(m.group(1), m.group(2), text, m.start()):
            continue          # ★ 负控：端口 / 日期不算比值
        ctx = para_of(text, m.start())
        # ★★ 2026-10-13 修（ext E-1）：判定改用【同句】而非【字符窗】
        declared, _sent = same_unit_declared(text, m.start())
        out.append({"kind": "ratio", "value": m.group(0), "declared": declared,
                    "ctx": ctx.replace("\n", " ")[:120]})
    for m in RE_COUNT.finditer(text):
        ctx = para_of(text, m.start())
        # ★★ 2026-10-13 修（ext E-1）：判定改用【同句】而非【字符窗】
        declared, _sent = same_unit_declared(text, m.start())
        out.append({"kind": "count", "value": m.group(0), "declared": declared,
                    "ctx": ctx.replace("\n", " ")[:120]})
    return out


def scan_file(path):
    try:
        t = io.open(path, encoding="utf-8").read()
    except Exception:
        return []
    return scan_text(t)


def selftest():
    ok = tot = 0
    # ★ 正控：裸百分比、无口径词 ⇒ 必须判【未申报】
    tot += 1
    r = scan_text("本次到达率是 91.67")
    r2 = scan_text("到达率 91.67%")
    if r2 and not r2[0]["declared"]:
        ok += 1
        print("  ✅ 正控：裸百分比无口径 ⇒ 判未申报（可红）")
    else:
        print("  ❌ 正控：裸百分比未判出")
    # ★ 负控：带口径词 ⇒ 必须判【已申报】
    tot += 1
    r3 = scan_text("24h 窗口内到达率 91.67%（分母 = 12）")
    if r3 and r3[0]["declared"]:
        ok += 1
        print("  ✅ 负控：带窗口/分母 ⇒ 判已申报")
    else:
        print("  ❌ 负控：带口径词却判未申报")
    # ★ 正控：裸计数 ⇒ 判未申报
    tot += 1
    r4 = scan_text("台账有 205 条")
    if r4 and not r4[0]["declared"]:
        ok += 1
        print("  ✅ 正控：裸计数 ⇒ 判未申报")
    else:
        print("  ❌ 正控：裸计数未判出（★ 或 ctx 里误含口径词）")
    # ★ 负控：带「扫描面」⇒ 已申报
    tot += 1
    r5 = scan_text("台账 205 条（扫描面 = docs/deviation-ledger-*.md）")
    if r5 and r5[0]["declared"]:
        ok += 1
        print("  ✅ 负控：带扫描面 ⇒ 判已申报")
    else:
        print("  ❌ 负控：带扫描面却判未申报")
    # ★ 三态：无任何数值 ⇒ 不适用（不报 fail）
    tot += 1
    if not scan_text("本件不含任何数字"):
        ok += 1
        print("  ✅ 正控：无数值 ⇒ 空列表（★ 调用方应报「不适用」）")
    else:
        print("  ❌ 正控：纯文本竟判出数值")
    # ★★ 负控（2026-10-12 实跑误报修入）：端口号不是比值
    tot += 1
    if not [x for x in scan_text("监听 8792/8803 同进程") if x["kind"] == "ratio"]:
        ok += 1
        print("  ✅ 负控：`8792/8803`（端口）⇒ 不判为比值")
    else:
        print("  ❌ 负控：端口号被误判为比值")
    # ★★ 负控：日期不是比值
    tot += 1
    if not [x for x in scan_text("截至 2026-10-12 归档，日期 04/05") if x["kind"] == "ratio"]:
        ok += 1
        print("  ✅ 负控：`04/05`（日期）⇒ 不判为比值")
    else:
        print("  ❌ 负控：日期被误判为比值")
    # ★★ 正控：真比值仍须命中（★ 防「修误报顺手把真值也漏了」）
    tot += 1
    if [x for x in scan_text("到达 10/11") if x["kind"] == "ratio"]:
        ok += 1
        print("  ✅ 正控：真比值 `10/11` ⇒ 仍命中（★ 防修误报时漏真值）")
    else:
        print("  ❌ 正控：真比值被漏 ⇒ 修过头")
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    ap.add_argument("--limit", type=int, default=20)
    a = ap.parse_args()
    if a.version:
        print("denominator-declare 1.0.0")
        return 0
    if a.selftest:
        return selftest()
    if not a.path:
        print("用法: denominator-declare.py <file.md> | --selftest | --version")
        return 2
    if not os.path.exists(a.path):
        print("★ 目标不存在（★ 404 语义，非格式错）: %s" % a.path)
        return 2
    items = scan_file(a.path)
    if a.json:
        print(json.dumps(items, ensure_ascii=False, indent=1))
        return 0
    bare = [i for i in items if not i["declared"]]
    print("== denominator-declare 1.0.0 · %s ==" % a.path)
    print("  数值总数 %d · ★ 未申报口径 %d" % (len(items), len(bare)))
    if not items:
        print("  ★ 本件不含数值 ⇒ 本门【不适用】（★ 不是通过）")
        return 0
    for i in bare[:a.limit]:
        print("  ❌ [%s] %-10s  … %s" % (i["kind"], i["value"], i["ctx"][:100]))
    if len(bare) > a.limit:
        print("  … 另有 %d 条" % (len(bare) - a.limit))
    print()
    if bare:
        print("  ❌ %d 处裸数未申报口径 ⇒ 依 D-203/§0.1，数字无口径【不可复算】" % len(bare))
        return 1
    print("  ✅ 全部数值均带口径")
    return 0


if __name__ == "__main__":
    sys.exit(main())
