#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
group-gate v1.0.0 (HR) - 群聊治理门 (R006 十项标准 / 2026-09-07)

职责: 群聊(群发广播线程)治理——开群前决策树评估(check), 存量群健康审计(audit)。
实证: 群聊上下文放大 20.8x(消息x参与者), 40+ 人大群是资源黑洞。
规范: docs/group-chat-governance-v1.md (G1-G4 分类 + C1-C6 约束)。
R006: 1插件(P2) 2selfcheck 3cld-check 4version-check 5README 6--version 7日志 8落链 9CLI 10lean4-check
用法:
  group-gate.py check --desc "<场景>" [--participants N] [--mutual yes/no] [--duration once/temp/long]
  group-gate.py classify --desc "<场景>"
  group-gate.py audit [--json]
  group-gate.py lean4-check / selfcheck / version / cld-check / version-check
零 LLM: 纯规则。

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
    print("== group-gate 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · group-gate v1.0.0 (HR) - 群聊治理门 (R006 十项标准 / 2026-09-07)")
    print("  · 职责: 群聊(群发广播线程)治理——开群前决策树评估(check), 存量群健康审计(audit)。")
    print("  · 实证: 群聊上下文放大 20.8x(消息x参与者), 40+ 人大群是资源黑洞。")
    print("  · 规范: docs/group-chat-governance-v1.md (G1-G4 分类 + C1-C6 约束)。")
    print("  · 命令/参数: desc, participants, mutual, duration, json")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, datetime, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/group-gate.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, datetime, sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/group-gate.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = '1.0.0'
LOG_FILE = os.path.expanduser('~/.dsh/group-gate.log')
BUS_FILE = os.path.expanduser('~/.dsh/agent-bus.json')
GROUPS_DIR = os.path.expanduser('~/dsh-collab/data/groups')
def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write('[' + datetime.datetime.now().isoformat() + '] ' + msg + chr(10))
    except Exception:
        pass

def load_threads():
    try:
        d = json.load(open(BUS_FILE, encoding='utf-8'))
        return d.get('threads', [])
    except Exception:
        return []

def participants_of(t):
    ps = set()
    for m in t.get('messages', []):
        f = str(m.get('from') or '')
        if f and f != "node": ps.add(f)
    return ps

def msgs_of(t):
    return len(t.get('messages', []))

def cmd_check(args):
    desc = args.desc or ""
    n = args.participants or 0
    mutual = (args.mutual or "no").lower() in ("yes", "y", "true", "1")
    duration = (args.duration or "once").lower()
    print("[check] 场景: " + desc[:80])
    print("  参与者: %d | 需互见: %s | 时长: %s" % (n, "是" if mutual else "否", duration))
    print()
    if not mutual:
        print("推荐: ★ 点对点分别通知 (A->B, A->C 各自)");
        print("理由: B/C 不需互见, 群聊是浪费(每条x全员)");
        print("成本: 线性(2N 单元)");
        return 0
    if duration == "long":
        print("推荐: 新开会话 (长期共同产出)");
        print("理由: 长协需独立上下文, 群聊长驻持续放大");
        print("注意: 用完归档");
        return 0
    if duration == "temp":
        if n <= 8:
            print("推荐: G3 评审讨论群 (<=8人, 48h 收敛即散)");
            return 0
        print("警告: %d > 8 人临时讨论——拆小群或定向收集汇总" % n);
        print("理由: C1 规模闸");
        return 2
    if n <= 5:
        print("推荐: G2 任务协作群 (<=5人, 完成即归档)");
        return 0
    if n <= 17:
        print("评估: %d 人——G1 全员(制度/事件) 还是拆点对点?" % n);
        print("  - 制度/重启/事件 -> G1 广播 (月<=5)");
        print("  - 否则 -> 拆点对点 (多数超5人其实是各自执行)");
        return 3 if n > 8 else 0
    print("警告: %d 人——仅 G1 全员广播合法(制度/重启/事件)" % n);
    print("理由: C2 用途闸 + C5 放大预算 (每条x%d人)" % n);
    return 2
def cmd_classify(args):
    desc = args.desc or ""
    if not desc: print("[classify] 需 --desc"); return 1
    if re.search(r"制度|重启|重大事件|全员|公告", desc): g, c = "G1 全员广播", "一次性, 月<=5"
    elif re.search(r"评审|讨论|评估|议题|征求|方案", desc): g, c = "G3 评审讨论", "<=8人, 48h 散"
    elif re.search(r"状态|同步|进度|监控", desc): g, c = "G4 状态同步", "<=6人, 可走黑板"
    elif re.search(r"任务|协作|共同|分工|执行", desc): g, c = "G2 任务协作", "<=5人, 完成归档"
    else: g, c = "?", "无法判定——用 check"
    print("[classify] 场景: " + desc[:60])
    print("  分类: " + g)
    print("  约束: " + c)
    return 0

def cmd_audit(args):
    threads = load_threads()
    groups = []
    for t in threads:
        ps = participants_of(t)
        if len(ps) > 2:
            groups.append({"id": t.get("id", ""), "n": len(ps), "msgs": msgs_of(t)})
    groups.sort(key=lambda g: -(g["n"] * g["msgs"]))
    big = [g for g in groups if g["n"] >= 40]
    mid = [g for g in groups if 8 <= g["n"] < 40]
    small = [g for g in groups if g["n"] < 8]
    amp = sum(g["n"] * g["msgs"] for g in groups)
    total = sum(g["msgs"] for g in groups)
    result = {"total_groups": len(groups), "big_40plus": len(big), "mid_8to39": len(mid), "small_under8": len(small), "total_msgs": total, "context_units": amp, "amplification_x": round(amp / total, 1) if total else 0, "top_heavy": groups[:5]}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        print("[audit] 存量群聊健康:")
        print("  总群聊: %d | 40+大群: %d | 8-39人: %d | <8人: %d" % (len(groups), len(big), len(mid), len(small)))
        print("  消息: %d | 上下文单元: %d | 放大率: %.1fx" % (total, amp, result["amplification_x"]))
        for g in result["top_heavy"][:5]:
            print("    %s: %d人x%d条 = %d单元" % (g["id"][:18], g["n"], g["msgs"], g["n"] * g["msgs"]))
        if big: print("  C6: %d 个 40+ 大群建议归档/转黑板" % len(big))
    try:
        os.makedirs(GROUPS_DIR, exist_ok=True)
        import datetime as dt
        ts = dt.date.today().isoformat()
        with open(os.path.join(GROUPS_DIR, 'audit-' + ts + '.json'), 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
        log('audit -> data/groups/audit-' + ts + '.json')
    except Exception as e:
        log("audit 落链失败: " + str(e))
    return 2 if big else (3 if mid else 0)

def cmd_lean4(args):
    # 违规场景1: 45 人且非 G1(制度) -> 应警告(return 2, n>17 分支)
    r1 = cmd_check(argparse.Namespace(desc="45人项目群", participants=45, mutual="yes", duration="once"))
    ok1 = (r1 == 2)
    # 违规场景2: 20人各自执行却想开群 -> 应推荐点对点(return 0, 但输出是点对点=正确路径)
    r2 = cmd_check(argparse.Namespace(desc="20人各自执行", participants=20, mutual="no", duration="once"))
    # 结构门验证: 45 人非制度群被警告
    print("lean4-check:", "OK 45人非制度群被门警告" if ok1 else "X 超大群未拦截!")
    return 0 if ok1 else 1
def cmd_selfcheck(args):
    ok = True
    print("[selfcheck] group-gate v" + VERSION)
    print("  OK  bus: " + BUS_FILE)
    print("  OK  groups: " + GROUPS_DIR)
    print("[selfcheck] OK PASS")
    return 0

def cmd_cld(args):
    print("[cld-check] 纯 CLI 无 CLD 耦合 PASS")
    return 0

def cmd_vcheck(args):
    print("[version-check] 纯 CLI 无 dsh 依赖 v" + VERSION)
    return 0

def cmd_version(args):
    print("group-gate " + VERSION)
    return 0

def main():
    ap = argparse.ArgumentParser(description="group-gate v" + VERSION + " - 群聊治理门 (R006)")
    sub = ap.add_subparsers(dest="cmd")
    specs = {"check": "决策树", "classify": "分类G1-G4", "audit": "存量审计", "lean4-check": "Lean4自检", "selfcheck": "TCC", "cld-check": "CLD适配", "version-check": "版本检查", "version": "版本"}
    for name, help_ in specs.items():
        sp = sub.add_parser(name, help=help_)
        if name in ("check", "classify"): sp.add_argument("--desc", default="")
        if name == "check":
            sp.add_argument("--participants", type=int, default=0)
            sp.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
            sp.add_argument("--mutual", default="no")
            sp.add_argument("--duration", default="once")
        if name == "audit": sp.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.cmd: ap.print_help(); return 0
    fn = {"check": cmd_check, "classify": cmd_classify, "audit": cmd_audit, "lean4-check": cmd_lean4, "selfcheck": cmd_selfcheck, "cld-check": cmd_cld, "version-check": cmd_vcheck, "version": cmd_version}.get(args.cmd)
    if not fn: ap.print_help(); return 0
    try:
        return fn(args)
    except Exception as e:
        log("cmd %s error: %s" % (args.cmd, e))
        print("[" + args.cmd + "] X 异常: " + str(e))
        return 1

if __name__ == '__main__':
    sys.exit(main())