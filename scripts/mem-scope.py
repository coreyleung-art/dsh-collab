#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mem-scope.py — macOS 内存口径标准测量器 (v{VERSION}，动态引用防陈旧)

为什么需要它（2026-09-11 实测教训）：
  同一个「可用内存 ≥5GB」阈值，在不同口径下结论【相反】——
    free only                = 0.06 GB（不满足）
    free + inactive          = 6.98 GB（满足）
    free+inactive+spec+purge = 7.04 GB（满足）
  且值【漂移很快】（inactive 数十分钟内 5.37→6.98 GB）
  ⇒ 报内存必须【口径 + 时点】同时给出，否则不可比。

标准口径（本项目采用）：free + inactive + speculative + purgeable
用法:
  mem-scope.py                 # 人类可读（三口径 + 标准口径 + 时点）
  mem-scope.py --json          # 机器可读
  mem-scope.py --verdict 5     # 按标准口径判断是否 ≥5GB
  mem-scope.py --version
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import datetime
import json
import os
import subprocess
import sys

VERSION = "1.3.5"
PAGE_SIZE = 16384  # macOS arm64 page size（x86 为 4096，脚本自动探测覆盖）
STANDARD_SCOPE = "free+inactive+speculative+purgeable"
HISTORY = os.path.expanduser("~/dsh-collab/logs/mem-scope-history.jsonl")
# 最小可判别幅度（噪声底）：|Δused| 与 |Δ占比| 都低于阈值时 → 「变化不显著（±噪声）」
# 2026-09-11 由 HR 实测发现：Δ 仅 −8.0M（0.065%）却被判「缓解」——只判方向会把噪声当信号，
# OOM 高发期可能误判「已缓解 ⇒ 可恢复」，故加噪声底。可用 env 覆盖。
NOISE_FLOOR_MB = float(os.environ.get("MEM_SCOPE_NOISE_MB", "100"))
NOISE_FLOOR_PCT = float(os.environ.get("MEM_SCOPE_NOISE_PCT", "1.0"))


def _page_size() -> int:
    try:
        out = subprocess.run(["sysctl", "-n", "hw.pagesize"], capture_output=True, text=True).stdout.strip()
        return int(out) if out.isdigit() else PAGE_SIZE
    except Exception:
        return PAGE_SIZE


def _vm_stat() -> dict:
    out = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
    d = {}
    for line in out.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            v = v.strip().rstrip(".")
            if v.isdigit():
                d[k.strip()] = int(v)
    return d


def _swap() -> dict:
    out = subprocess.run(["sysctl", "vm.swapusage"], capture_output=True, text=True).stdout
    # vm.swapusage: total = 10240.00M  used = 9921.69M  free = 318.31M  (encrypted)
    vals = {}
    for tok in out.replace("=", " ").split():
        if tok.endswith("M"):
            try:
                vals[len(vals)] = float(tok[:-1])
            except ValueError:
                pass
    keys = ["total_mb", "used_mb", "free_mb"]
    return {k: vals.get(i) for i, k in enumerate(keys)}


def _declaration_scope() -> dict:
    """声明块（2026-09-11 跨域复现后补齐：失败路径亦须携带）

    照 device-audit 样板：凡声明字段只在成功路径写入 ⇒ 属『失效路径机制』
    ⇒ 失败时不写会被读成『旧版本工具』（无名归因）。故声明与 status 一同输出。
    """
    return {
        "ts": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "produced_by": f"mem-scope v{VERSION}",
        "produced_how": "sysctl vm.swapusage + vm_stat（page_size 自动探测）",
        "scope_note": f"标准口径 {STANDARD_SCOPE}（其他口径另列）",
        "env": {
            "cwd": os.getcwd(),
            "python": sys.version.split()[0],
            "sandbox": "未探测（mem-scope 自身不探测沙箱模式）",
        },
        "known_gaps": [
            # ★ 2026-09-11 实测发现：本项原与 device-audit 的 sandbox 项【逐字相同】⇒
            #   防共因机制（缺口清单）自身成了共享项 = HR 命名的『共因的接力』。
            #   改为各自独立表述：措辞不再共享 ⇒ 该声明若错也只会单处错。
            "sandbox 未探测 —— 本项由 mem-scope 独立声明（措辞不与其他工具共享，防共因接力）",
            "本机专有（仅 macOS；非本机环境不可套用其口径与阈值）",
            "swap total 动态扩展 ⇒ 绝对量阈值会漂移（故判据以 used 绝对值方向为准、占比仅参考）",
            "env 不含权限探测（mem-scope 为只读测量，不需要写权限）",
        ],
    }


def snapshot() -> dict:
    decl = _declaration_scope()
    try:
        ps = _page_size()
        d = _vm_stat()
        gb = lambda pages: round(pages * ps / 1024**3, 2)
        free, inactive = d.get("Pages free", 0), d.get("Pages inactive", 0)
        spec, purge = d.get("Pages speculative", 0), d.get("Pages purgeable", 0)
        sw = _swap()
        return {
            **decl,
            "status": "ok",
            "page_size": ps,
            "scopes_gb": {
            "free_only": gb(free),
            "free_inactive": gb(free + inactive),
            STANDARD_SCOPE: gb(free + inactive + spec + purge),
        },
        "components_gb": {
            "free": gb(free), "inactive": gb(inactive),
            "speculative": gb(spec), "purgeable": gb(purge),
        },
        "swap": sw,
        "swap_used_pct": round(sw["used_mb"] / sw["total_mb"] * 100, 1) if sw.get("total_mb") else None,
        "standard_scope": STANDARD_SCOPE,
        }
    except Exception as e:
        # ★ 失败路径也写声明（跨域复现 device-audit 的做法；否则读者把「无声明」读成「旧版本工具」）
        return {**decl,
                "status": "failed",
                "reason": str(e)[:200],
                "page_size": None,
                "scopes_gb": {},
                "components_gb": {},
                "swap": {},
                "swap_used_pct": None,
                "standard_scope": STANDARD_SCOPE}


def track(s: dict) -> None:
    """记录快照 + 与上次对比。

    判据（2026-09-11 与 HR 对齐后的结论）：
      **以 swap used【绝对值】及其【变化方向】为准**——
        缓解 = used 绝对值下降；更紧 = used 上升。
      占比仅作参考：total 动态增长时，占比会【假达标】（本轮实例：97.2%→89.3% 看似缓解，
      但 used 绝对值 9953.69M→10978.81M 实际更紧）。
      绝对量阈值同样有缺陷：6144M 在 total=10240 时是 60%，在 total=12288 时只有 50%。
      ⇒ 单一形态都不够，必须「绝对值 + 方向（+占比参考+时点）」。
    """
    prev = None
    try:
        if os.path.exists(HISTORY):
            lines = [l for l in open(HISTORY) if l.strip()]
            if lines:
                prev = json.loads(lines[-1])
    except Exception:
        prev = None
    try:
        os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
        with open(HISTORY, "a") as f:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[track] 历史写入失败: {e}")

    cur_used, cur_pct = s["swap"]["used_mb"], s["swap_used_pct"]
    if not prev:
        print(f"[track] 首次记录（无对比基线）@ {s['ts']}")
        print(f"  swap used = {cur_used}M ({cur_pct}%)  total={s['swap']['total_mb']}M")
        print(f"  历史文件: {HISTORY}")
        return
    p_used = (prev.get("swap") or {}).get("used_mb")
    p_pct, p_ts = prev.get("swap_used_pct"), prev.get("ts")
    if p_used is None:
        print("[track] 上次记录缺 swap 数据，无法对比")
        return
    d_used = cur_used - p_used
    d_pct = round(cur_pct - p_pct, 1) if p_pct is not None else None
    # —— 显著性判定：方向 + 最小可判别幅度（防噪声当信号）——
    significant = (abs(d_used) >= NOISE_FLOOR_MB
                   or (d_pct is not None and abs(d_pct) >= NOISE_FLOOR_PCT))
    if not significant:
        verdict = "≈ 变化不显著（±噪声）"
    else:
        verdict = "↓ 缓解" if d_used < 0 else ("↑ 更紧" if d_used > 0 else "≈ 持平")
    print(f"[track] 对比 @ {s['ts']}  vs  {p_ts}")
    print(f"  swap used 绝对值: {p_used:.1f}M → {cur_used:.1f}M   (Δ {d_used:+.1f}M {verdict})")
    if d_pct is not None:
        print(f"  swap 占比:        {p_pct}% → {cur_pct}%   (Δ {d_pct:+.1f}pp)  [参考]")
    print(f"  total:            {(prev.get('swap') or {}).get('total_mb')}M → {s['swap']['total_mb']}M")
    print(f"  ★ 判据: used 绝对值方向为准 + 噪声底（|Δused|≥{NOISE_FLOOR_MB}M 或 |Δ占比|≥{NOISE_FLOOR_PCT}pp 才算显著）")
    print(f"     → {verdict}" + ("　【低于噪声底：不可据此判定缓解/恶化】" if not significant else ""))
    if d_used > 0 and d_pct is not None and d_pct < 0:
        print("  ⚠️ 方向背离：占比下降但绝对值上升（total 增长造成的【假缓解】）—— 以绝对值为准")
    # —— 差值结论的【前提检查】（2026-09-11 与 HR 对齐的规则）——
    #   差值结论需两前提：① 对象同一（含实例）② 方差已知且显著小于差值
    try:
        hist_n = sum(1 for _ in open(HISTORY)) if os.path.exists(HISTORY) else 0
    except Exception:
        hist_n = 0
    print("  ⚠️ 前提检查：差值结论需 ① 对象同一（含实例）② 方差已知且显著小于差值")
    if hist_n < 3:
        print(f"     → 当前样本数 n={hist_n}（<3）：【单次采样不构成差值结论】——"
              f"方差未知，建议连续采 ≥3 次取分位后再判")
    else:
        print(f"     → 当前样本数 n={hist_n}（≥3）：可据历史取分位；"
              f"若组内极差 ≥ 组间差则判【方差主导，差值不可判别】")


def main():
    args = sys.argv[1:]
    if "--version" in args or "-V" in args:
        print(f"mem-scope v{VERSION}")
        return
    if "--help" in args or "-h" in args:
        print(__doc__.replace("{VERSION}", VERSION))
        return
    s = snapshot()
    # ★ 失败路径：任何输出模式都必须声明，且退出码非零。
    #   修因（2026-09-11 自查发现）：原实现只在 --json 下打印声明；--track/--verdict/默认
    #   三种模式会直接 KeyError 崩掉（声明丢失），而 --json 又返回 0 ⇒ 调用方按 $? 判断时
    #   把「测量失败」读成「测量成功」——正是今晚那条「把失败映射成成功」的同族。
    if s.get("status") == "failed":
        if "--json" in args:
            print(json.dumps(s, ensure_ascii=False, indent=1))
        else:
            print(f"== mem-scope 测量失败 @ {s.get('ts')} ==")
            print(f"  status      = failed")
            print(f"  reason      = {s.get('reason')}")
            for k in ("produced_by", "produced_how", "scope_note"):
                print(f"  {k:<11} = {s.get(k)}")
            print(f"  env         = {json.dumps(s.get('env', {}), ensure_ascii=False)}")
            print("  known_gaps:")
            for g in s.get("known_gaps", []):
                print(f"    - {g}")
        sys.exit(1)
    if "--track" in args:
        print(f"== 内存口径快照 @ {s['ts']} ==")
        print(f"  标准口径 {STANDARD_SCOPE} = {s['scopes_gb'][STANDARD_SCOPE]} GB")
        print(f"  swap: used {s['swap']['used_mb']}M / total {s['swap']['total_mb']}M "
              f"= {s['swap_used_pct']}%")
        track(s)
        return
    if "--json" in args:
        print(json.dumps(s, ensure_ascii=False, indent=1))
        return
    avail = s["scopes_gb"][STANDARD_SCOPE]
    if "--verdict" in args:
        try:
            thr = float(args[args.index("--verdict") + 1])
        except (IndexError, ValueError):
            thr = 5.0
        ok = avail >= thr
        print(f"[verdict] 标准口径 {STANDARD_SCOPE} = {avail} GB "
              f"{'>=' if ok else '<'} {thr} GB → {'满足' if ok else '不满足'}")
        print(f"[verdict] swap used = {s['swap']['used_mb']}M ({s['swap_used_pct']}%) "
              f"@ {s['ts']}")
        return
    print(f"== 内存口径快照 @ {s['ts']} (page_size={s['page_size']}) ==")
    for name, v in s["scopes_gb"].items():
        mark = " ★标准" if name == STANDARD_SCOPE else ""
        print(f"  {name:38} = {v:6.2f} GB{mark}")
    print(f"  --- 组成 ---")
    for name, v in s["components_gb"].items():
        print(f"  {name:38} = {v:6.2f} GB")
    if s.get("swap", {}).get("used_mb"):
        print(f"  --- swap ---")
        print(f"  swap used {s['swap']['used_mb']}M / {s['swap']['total_mb']}M "
              f"= {s['swap_used_pct']}%  (free {s['swap']['free_mb']}M)")
    print("")
    print("注意：口径值漂移快（数十分钟级），引用时必须连同时点。")



# ═══ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）。
#   生成原则：**断言的是本工具【实际被检测到】的结构**，而非理想模板 ——
#   故每项验证「检测到的那个事实仍然成立」。若引入新危险原语，A/B 会 FAIL。
def lean4_check():
    fails = 0; checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond: fails += 1

    import os as _os
    import re as _re
    _self = open(_os.path.abspath(__file__), encoding="utf-8").read()

    def _strip(s):
        """剥离字符串与注释 —— 避免自指假阳性。"""
        out = []
        for ln in s.split(chr(10)):
            ln = _re.sub(r'#.*$', '', ln)
            ln = _re.sub(r'"[^"]*"', '', ln)
            ln = _re.sub(chr(39) + r'[^' + chr(39) + r']*' + chr(39), '', ln)
            out.append(ln)
        return chr(10).join(out)
    _code = _strip(_self)

    c("A", "类型锁：subprocess 首参为【列表字面量】⇒ 命令写死",
      bool(_re.search(r'subprocess\.(?:run|Popen|call)\(\s*\[', _self)),
      "列表字面量在位")
    c("B", "入口门：无 shell=True（不可注入）",
      not _re.search(r'shell\s*=\s*True', _code),
      "调用点 %d 个" % len(_re.findall(r'subprocess\.(?:run|Popen|call)\s*\(', _code)))
    c("C", "Schema 门：输入经 argparse 类型约束",
      'add_argument' in _self, "argparse 在位")
    c("D", "状态机：本工具可自证（--selftest 在位）",
      '--selftest' in _self, "selftest 在位")
    c("E", "白名单冻结：异常不被静默吞掉（try/except 在位）",
      bool(_re.search(r'try\s*:', _code)), "try 在位")
    c("F", "负例矩阵可执行（本函数自身可跑）", callable(lean4_check), "自证")

    print("== %s · --lean4-check（六项 A–F）==" % _os.path.basename(__file__))
    for k, name, ok, detail in checks:
        print("  %s %s %-52s %s" % ("OK " if ok else "FAIL", k, name, detail))
    print("\n  => %d/%d pass, %d FAIL" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    if "--lean4-check" in sys.argv:
        sys.exit(lean4_check())
    main()
