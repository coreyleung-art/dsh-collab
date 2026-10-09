#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pstd-restart-observation.py — PSTD ③ 重启观测的**机械双读**（v1.0.0）

依据：裁判 2026-10-08 预登记判别表（写在观测之前，防事后解释）+ 附加前置（同时读磁盘版本，
      排除「磁盘被改」这一替代解释）。

判别表（预注册，非事后解释）：
  std=PSTD/1.0.4 且 磁盘=1.0.4 ⇒ ③ 通过 ∧ 机制假设「std 于模块加载时读盘」成立
  std=PSTD/1.0.3 且 磁盘=1.0.4 ⇒ ③ 不通过 ∧ 机制假设被推翻（转查硬编码/缓存/多包注册）
  std=PSTD/1.0.5             ⇒ 1.0.4 的 ③ 跳过（基准已变）
  其它组合                    ⇒ 不判定（基准已变或读数异常）

用法：python3 pstd-restart-observation.py [--json]
      python3 pstd-restart-observation.py --selftest | --version

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import argparse, json, os, sys, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/pstd-restart-observation.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "1.0.0"
__version__ = VERSION
PKG = os.path.expanduser("~/dsh-plugin-pstd/package.json")


def read_disk_version():
    try:
        with open(PKG, encoding="utf-8") as f:
            v = json.load(f).get("version")
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(PKG), datetime.timezone.utc)
        return {"version": v, "mtime": mt.strftime("%Y-%m-%dT%H:%M:%SZ")}
    except Exception as e:
        return {"version": None, "error": type(e).__name__}


def judge(std, disk):
    """按预登记表判（不事后解释）"""
    if disk != "1.0.4":
        return {"verdict": "基准已变", "note": f"磁盘={disk} ≠ 1.0.4 ⇒ 应重立基线而非直接判 ③"}
    if std == "PSTD/1.0.4":
        return {"verdict": "③ 通过 ∧ 机制假设成立", "note": "在役=磁盘=1.0.4 ⇒ 加载时读盘成立"}
    if std == "PSTD/1.0.3":
        return {"verdict": "③ 不通过 ∧ 机制假设被推翻",
                "note": "磁盘 1.0.4 而在役 1.0.3 ⇒ 非「加载时读盘」⇒ 转查硬编码/缓存/多包注册"}
    if std == "PSTD/1.0.5":
        return {"verdict": "1.0.4 的 ③ 跳过", "note": "包已升 1.0.5 ⇒ 基准已变"}
    return {"verdict": "不判定", "note": f"std={std} 与预登记表不匹配 ⇒ 如实记未证"}


def observe(std_override=None):
    at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    disk = read_disk_version()
    std = std_override or "（需人工/tool 读数：plugin_standard action=norms 的 std）"
    return {"observed_at": at, "std_in_service": std, "disk_package_json": disk,
            "judgement": judge(std if std_override else "", disk.get("version")),
            "protocol": "双读：① 在役 std ② 磁盘 package.json version+mtime（排除「磁盘被改」）",
            "pre_registered_by": "裁判 2026-10-08（写在观测之前）"}


def selftest():
    ok = fail = 0
    def chk(c, l):
        nonlocal ok, fail
        if c: ok += 1; print("  ✅", l)
        else: fail += 1; print("  ❌", l)
    chk(judge("PSTD/1.0.4", "1.0.4")["verdict"].startswith("③ 通过"), "表行1：std=1.0.4 → 通过∧假设成立")
    chk("推翻" in judge("PSTD/1.0.3", "1.0.4")["verdict"], "表行2：std=1.0.3 → 不通过∧假设被推翻（负控）")
    chk("跳过" in judge("PSTD/1.0.5", "1.0.4")["verdict"], "表行3：std=1.0.5 → 跳过")
    chk(judge("PSTD/1.0.4", "1.0.5")["verdict"] == "基准已变", "前置：磁盘≠1.0.4 → 基准已变（不硬判）")
    chk(judge("PSTD/9.9.9", "1.0.4")["verdict"] == "不判定", "负控：表外组合 → 如实标未判定")
    print(f"\nselftest: {ok} PASS / {fail} FAIL")
    return 0 if fail == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--std", help="在役 std（如 PSTD/1.0.4）；省略则只读磁盘并提示需 tool 读数")
    ap.add_argument("--json", action="store_true"); ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version: print(json.dumps({"tool": "pstd-restart-observation", "version": VERSION})); return 0
    if a.selftest: return selftest()
    r = observe(a.std)
    if a.json: print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(f"observed_at={r['observed_at']}")
        print(f"  在役 std      : {r['std_in_service']}")
        print(f"  磁盘 version  : {r['disk_package_json'].get('version')} (mtime {r['disk_package_json'].get('mtime')})")
        print(f"  → 判定        : {r['judgement']['verdict']}")
        print(f"    依据        : {r['judgement']['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
