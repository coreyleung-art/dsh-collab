#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lint-inventory —— 【既有 lint/gate 清单器】（供派子代理时随提示词下发）。

★ 立据（2026-10-12 实测）：本仓 `tools/` 下已有 10 个 lint/gate 正好管着当晚所有坑
  （漏退出码被管道吞 ⇒ `evidence-channel-guard`；判据从未红过 ⇒ `csx-canfail-check`；
   用字面串当判据 ⇒ `text-assertion-lint`；绝对断言无观测面 ⇒ `absolute-claim-lint` …），
  ★★ 而当晚 20 个子代理【一个都没引用它们】—— **零引用**（逐条实测）。
★★ ⇒ 故本工具的目的不是「再查一遍」，而是【让下一批派工不再重造】：
  用法：python3 tools/lint-inventory.py            # 人读表
        python3 tools/lint-inventory.py --prompt   # 可直接粘进子代理提示词的一段
        python3 tools/lint-inventory.py --json     # 机器可读
        python3 tools/lint-inventory.py --check "<提示词文本>"  # ★ 门：提示词是否含清单

★ 三态：`--check` 在【提示词未含清单】时 exit 1（★ 可红，不是恒绿）。
"""
import io, os, re, sys, json, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = ["tools", "scripts"]

# ★ 【坑 → 工具】对照表（★ 逐条有 docstring 依据；★ 新增条目须附立据）
CATALOG = [
    ("★★★ 退出码被管道吞", "evidence-channel-guard.py",
     "★ docstring 逐字：「用 `| tail` 取 `$?` 拿到的是 tail 的退出码 ⇒ 红显示成绿」"),
    ("★★★ 判据从未红过", "csx-canfail-check.py",
     "★ docstring 逐字：「一个判据若没有能让它失败的输入，它就不是判据，是日志」"),
    ("★★ 用字面串当判据", "text-assertion-lint.py",
     "★ docstring：「在自证里用源码文本当证据」"),
    ("★ 绝对断言无观测面", "absolute-claim-lint.py",
     "★ docstring：「绝对断言须同句给观测面」"),
    ("★ 悬空引用（文件:行号）", "report-claim-check.py",
     "★ docstring：报告里的 `文件:行号` 是否悬空"),
    ("★ 版本铉", "version-pin-lint.py",
     "★ docstring：点值判据必须返回 version X"),
    ("★ 否定性结论无观测面", "absence-claim-lint.py",
     "★ docstring：否定性结论必须同卡附「观测面声明」"),
    ("★ 声明有效性", "declaration-validity-scan.py",
     "★ tool 名 · `--selfcheck`"),
    ("★ 静默截断", "lint-silent-truncation.py",
     "★ tool 名 · `--group`"),
    ("★ 原则落地", "principle-landing-check.py",
     "★ docstring：原则落地真跑（stderr 留痕）"),
    # ★★ 2026-10-12 新建四条（★ 当晚白名的四个未覆盖面）
    ("★★ 非原子写关键文件", "atomic-write-guard.py",
     "★ 立据：`open(p,\"w\")` 先截断 + 写入失败 ⇒ **634 KB 台账被清空**"),
    ("★★ 数字无口径", "denominator-declare.py",
     "★ 立据：S-1 分母两判定相反 · §18 条数四值互异"),
    ("★★ 更正账手工拼", "correction-ledger-gen.py",
     "★ 从台账自动生成（★ v7 §0.0 原为手工）"),
    ("★★ 照拄旧读数", "live-read-guard.py",
     "★ 立据：§3.1 那句在 v4/v5/v6/v6.1 **四代逐字继承、无一版重测**"),
    ("★★★ 派子代理无清单", "subagent-work-checklist.py",
     "★ 立据：V2 审查两次皆空 · R2 首次零产出 · 20 代理零引用"),
    ("★★ SLO 目标是形容词", "slo-target-form.py",
     "★ 立据：14 个指标中 3 条判不可判，根因同一个——目标是形容词/架构性质"),
    ("★★ 队列待投遂无超时标", "bus-pending-age.py",
     "★ 立据：111/122 pending、最老 50.8 天、而 **expired = 0**"),
    ("★★ 审查/调研目录非空（★ 防空目录被读成已审）", "beacon-check.py",
     "★ 立据：`research/v7-review-V2/` 存在但空，而两次审查代理均零产出（★ D-257/D-258）"),
    ("★★ 假结果形态（.status/​None当绿/​硬编码时间）", "false-result-patterns.py",
     "★ 立据：一晚八次「结果看上去对而实为假」（★ v7 §0.2.1）"),
    ("★★★ 自证里的恒真负例", "selftest-audit.py",
     "★ 立据：`gcr-gate` 旧版五条负例全是恒真（`0 == 0`）⇒ 可信负控 = 0；"
     "★★ `--run` 四分类 + 串行复核（★ 防并发伪失败）"),
]

def find_tool(name):
    for d in SCAN:
        p = os.path.join(ROOT, d, name)
        if os.path.exists(p):
            return os.path.join(d, name)
    return None

def inventory():
    out = []
    for gap, tool, why in CATALOG:
        rel = find_tool(tool)
        out.append({"gap": gap, "tool": tool, "path": rel, "why": why, "present": bool(rel)})
    return out

def render_table(items):
    L = []
    L.append("  %-30s %-32s %s" % ("★ 坑", "★ 既有工具", "★ 在位"))
    for it in items:
        L.append("  %-30s %-32s %s" % (it["gap"], it["tool"], "✓" if it["present"] else "✗ 缺"))
    return "\n".join(L)

def render_prompt(items):
    """★ 可直接粘进子代理提示词的一段。"""
    L = []
    L.append("# ★★★ 本仓【既有 lint/gate 清单】—★★ **建任何新判据前必先查这里（J44：复用而非新造）**")
    L.append("")
    L.append("| ★ 坑 | ★既有工具 | ★ 它管什么 |")
    L.append("|---|---|---|")
    for it in items:
        t = ("`%s`" % it["path"]) if it["present"] else ("★ **%s**（**本机未找到 — 请先核**）" % it["tool"])
        L.append("| %s | %s | %s |" % (it["gap"], t, it["why"]))
    L.append("")
    L.append("> ★★ **若你要新建一条判据，先问「上表里有没有对口的」。**")
    L.append("> ★ **有 ⇒ 复用或扩展；无 ⇒ 新建，且在提交里写明「已查上表，无对口」。**")
    L.append("> ★ 生成命令：`python3 tools/lint-inventory.py --prompt`")
    return "\n".join(L)

def check_prompt(text):
    """★ 门：提示词是否含【既有 lint 清单】。"""
    hits = [m for m in ("lint-inventory", "既有 lint", "evidence-channel-guard",
                        "csx-canfail-check", "text-assertion-lint") if m in text]
    return (len(hits) > 0), hits

def selfcheck():
    """★ 真调被测判据（不是恒真）。"""
    ok = 0
    tot = 0
    # 正控：清单非空 ⇒ 必须有条目
    tot += 1
    items = inventory()
    if len(items) >= 5:
        ok += 1; print("  ✅ 正控：清单非空（%d 条）" % len(items))
    else:
        print("  ❌ 正控：清单只有 %d 条" % len(items))
    # 正控：至少一个工具在位
    tot += 1
    if any(i["present"] for i in items):
        ok += 1; print("  ✅ 正控：至少一个工具在位")
    else:
        print("  ❌ 正控：一个都没在位")
    # ★★ 负控：空提示词 ⇒ 必须报「未含清单」
    tot += 1
    r, _ = check_prompt("")
    if r is False:
        ok += 1; print("  ✅ 负控：空提示词 ⇒ 判「未含清单」（可红）")
    else:
        print("  ❌ 负控：空提示词居然判通过")
    # ★★ 负控：含一个关键词 ⇒ 必须通过
    tot += 1
    r, h = check_prompt("请先跑 csx-canfail-check")
    if r is True:
        ok += 1; print("  ✅ 负控：含关键词 ⇒ 判「已含」（hits=%s）" % h)
    else:
        print("  ❌ 负控：含关键词却未认出")
    # ★ 正控：--prompt 输出含表头
    tot += 1
    if "既有 lint/gate 清单" in render_prompt(items):
        ok += 1; print("  ✅ 正控：--prompt 输出可直接粘用")
    else:
        print("  ❌ 正控：--prompt 输出异常")
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("lint-inventory 1.0.0"); return 0
    if a.selftest:
        return selfcheck()
    items = inventory()
    if a.json:
        print(json.dumps(items, ensure_ascii=False, indent=1)); return 0
    if a.prompt:
        print(render_prompt(items)); return 0
    if a.check is not None:
        ok, hits = check_prompt(a.check)
        if ok:
            print("\u2705 \u63d0\u793a\u8bcd\u5df2\u542b\u65e2\u6709 lint 清\u5355\uff08hits=%s\uff09" % hits); return 0
        print("\u274c \u63d0\u793a\u8bcd\u3010\u672a\u542b\u3011\u65e2\u6709 lint 清\u5355 \u21d2 \u8bf7\u5148\u8dd1 `python3 tools/lint-inventory.py --prompt` \u5e76\u7c98\u5165")
        return 1
    print("== lint-inventory 1.0.0 \u00b7 \u65e2\u6709 lint/gate \u6e05\u5355 ==")
    print(render_table(items))
    print()
    n_present = sum(1 for i in items if i["present"])
    print("  \u2605 \u5728\u4f4d %d/%d \u00b7 \u7528 `--prompt` \u53d6\u53ef\u7c98\u7247\u6bb5 \u00b7 `--check <\u63d0\u793a\u8bcd>` \u5f53\u95e8" % (n_present, len(items)))
    return 0

if __name__ == "__main__":
    sys.exit(main())
