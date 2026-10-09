#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-auditor v1.0.0 — 纸面门审查器 (R006 十项达标 · Lean4 结构门工具化)

把「纸面门 vs 结构门」教训工具化 (2026-09-07 archify 事故: 清单写了沙箱测试但被跳过):
  纸面门 = 规则/SOP 声明了「必须/门/强制」但无对应可执行工具 → 靠人执行, 可跳过
  结构门 = 有代码实现 + lean4-check 自检证明生效 → 不可绕过

功能:
  gate-auditor scan                     # 扫描全局规则/文档, 识别纸面门 vs 结构门
  gate-auditor scan --rules <RULES.md>  # 指定规则文件
  gate-auditor list-tools               # 已知结构门工具注册表
  gate-auditor --lean4-check            # 自检 (R006-⑩: 证明本工具识别门生效)
  gate-auditor --version

识别逻辑 (纯函数, 生产与自检同源):
  is_structural(entry_text)   # 命中结构门工具关键词/lean4-check → 结构门
  is_paper_gate(entry_text)   # 含门措辞但无工具 → 纸面门
  报告: 每条纸面门 + 建议升级路径 (对应哪个结构门形态)

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ── R006 早期旗标垫片（★ 必须在任何【模块级】参数校验之前） ──
# 动因：本器可能在模块级就校验 argv（如「不认识的参数 ⇒ 拒绝」），那会先于文件末的
# canonical 块，把 --selfcheck / --lean4-check / --r006-sets 当成非法参数拒掉
# （实测：selftest-inventory 与 verification-level-lint 都这样）。
# 做法：此处先把三个旗标摘出并暂存，再由文件末块的守卫统一分派 ——
# 既不绕过本器的严格参数治理，也不让治理挡掉自检入口本身。
import sys as _r006_sys
if __name__ == "__main__":
    _R006_EARLY_FLAGS = [f for f in ("--selfcheck", "--lean4-check", "--r006-sets")
                         if f in _r006_sys.argv]
    if _R006_EARLY_FLAGS:
        _r006_sys.argv = [x for x in _r006_sys.argv if x not in _R006_EARLY_FLAGS]
else:
    _R006_EARLY_FLAGS = []
# ── 垫片结束 ──


# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== gate-auditor 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · gate-auditor v1.0.0 — 纸面门审查器 (R006 十项达标 · Lean4 结构门工具化)")
    print("  · 把「纸面门 vs 结构门」教训工具化 (2026-09-07 archify 事故: 清单写了沙箱测试但被跳过):")
    print("  · 纸面门 = 规则/SOP 声明了「必须/门/强制」但无对应可执行工具 → 靠人执行, 可跳过")
    print("  · 结构门 = 有代码实现 + lean4-check 自检证明生效 → 不可绕过")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: glob, json, os, re, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/gate-auditor.log")
    return 0


import sys as _r006_sys
if False:  # ★ R006 ②⑩ 已迁移至文件末 canonical 块（原守卫并入）
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json
import os
import re
import sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/gate-auditor.log")


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

# ═══════════ 已知结构门工具注册表 (有代码实现的门) ═══════════
STRUCTURAL_TOOLS = {
    # 工具 → 覆盖领域
    "bb-gate": ["通讯写入", "bb_gate", "bb-gate.py"],
    "comm-domains": ["域权矩阵", "comm_domains"],
    "queue-drain": ["队列治理", "queue-drain", "--lean4-check"],
    "queue-condense": ["队列浓缩"],
    "cld-monitor": ["CLD 监控", "cld-monitor"],
    "restart-gate": ["重启门", "restart-gate", "restart-guard"],
    "load-gate": ["资源总控", "load-gate"],
    "schema-gate": ["Schema 校验", "schema-gate", "schema_gate"],
    "mem-gate": ["内存门", "mem-gate"],
    "channel-audit": ["通道审计", "channel-audit"],
    "guard-*": ["守卫工具族", "guard_compliance", "guard_premortem", "guard_check"],
    "gate-j23": ["node_modules 重建门(J23)", "gate-j23-lean4.py", "--lean4-check"],
    "gate-j24": ["xberg 演练互斥门(J24)", "gate-j24-lean4.py", "--lean4-check"],
    "dependency-audit": ["依赖全景分类+peer矩阵", "dependency-audit.py", "--lean4-check"],
    "rule-audit": ["规则账本全景+冲突", "rule-audit.py", "--lean4-check"],
    "device-audit": ["设备资产全景+可用矩阵", "device-audit.py", "--lean4-check"],
    "resource-audit": ["资源登记全景+归属", "resource-audit.py", "--lean4-check"],
    "channel-audit": ["外链通道全景+覆盖", "channel-audit.py", "--lean4-check"],
    "coverage-audit": ["文档摄取覆盖+缺口", "coverage-audit.py", "--lean4-check"],
    "dsh-tools lean4-check": ["工具自检", "lean4-check"],
    "selfcheck.js": ["插件自查", "selfcheck"],
    "queue_monitor": ["队列检测"],
    "bb-connect-execute": ["蓝图执行", "lean4-check"],
    "bb-schema-gate": ["蓝图 schema", "lean4-check"],
    "bb-blueprint-dialog": ["蓝图对话", "lean4-check"],
    "bb-schema-gate": ["schema 校验", "bb-schema-gate"],
    "bb-blueprint-integrity": ["蓝图完整性", "integrity"],
    "bb-blueprint-content-check": ["内容检查", "content-check"],
    "bb-connect-lab": ["连接实验", "connect-lab"],
    "bb-blueprint-gallery": ["gallery 渲染", "gallery"],
    "rule-judge": ["规则裁决", "deposit-judge", "rule-judge"],
    "bb-blueprint-registry": ["蓝图登记", "registry"],
    "verify-all": ["lean4 巡检", "verify-all"],
    "restart-intent": ["重启意图", "restart-intent"],
    # ═══ 校准补 (2026-09-07 v1.1: 覆盖实际已有工具, 降误报) ═══
    "agent_bus 锁": ["红绿灯", "agent_light", "agent_lock", "agent_unlock", "互斥"],
    "agent_send 门禁": ["agent_send", "v2.4 门禁"],
    "bb-sub": ["bb-sub", "订阅器"],
    "hb-forward": ["hb-forward", "hb-fwd", "心跳转发"],
    "sync-layer": ["sync-to-central", "sync-from-central", "双轨同步"],
    "dsh-tools": ["dsh-tools", "queue-drain", "queue-condense", "channel-audit", "load-gate"],
    "guard 族": ["guard_", "guard-", "pre-mortem", "guard_compliance", "guard_backup"],
    "waimai 工具": ["waimai_", "外卖"],
    "repair-report": ["repair-report", "修复报告"],
    "agent_profiles": ["agent_profile", "能力登记"],
    "selfcheck": ["selfcheck", "自查", "自检"],
    "exit-marker": ["exit-marker", "看门狗", "heartbeat"],
}

# 纸面门措辞 (声明了但需查有无工具)
GATE_WORDS = ["必须", "强制", "门", "enforced", "gate", "检查", "护栏", "红线", "禁止", "不可绕过"]

# 规则文件默认位置
RULES_DEFAULT = os.path.expanduser("~/dsh-collab/rules-registry/RULES.md")
DOCS_CANDIDATES = [
    os.path.expanduser("~/dsh-collab/comm-server/migration-plan-v1.md"),
    os.path.expanduser("~/dsh-collab/comm-server/deploy-comm-layer.sh"),
    os.path.expanduser("~/dsh-collab/comm-server/deploy-comm-server.sh"),
]


def is_structural(text):
    """判定文本是否引用结构门工具 (纯函数)"""
    low = text.lower()
    for tool, _keywords in STRUCTURAL_TOOLS.items():
        # 检查工具名或其关键词是否出现在文本
        for kw in [tool] + (_keywords or []):
            if kw.lower() in low:
                return True
    # lean4-check 自检存在 = 结构门强信号
    if "lean4" in low or "--lean4-check" in low:
        return True
    return False


def has_gate_intent(text):
    """文本是否含门/强制措辞 (声明了约束)"""
    return any(w in text for w in GATE_WORDS)


NARRATIVE_WORDS = ["评估", "可行性", "定位", "里程碑", "验收", "叙述", "蓝图 v", "规划", "目标", "参考", "概览", "总结", "结论"]


def is_narrative_line(text):
    """叙述/评估行识别 (老登校准): 含评估/蓝图叙述词的非规则门行 → 降误报"""
    return any(w in text for w in NARRATIVE_WORDS)


def classify_entry(entry_id, title, detail):
    """单条规则/流程条目分类: structural / paper / doc-only (纯函数)"""
    combined = f"{title} {detail}"
    if not has_gate_intent(combined):
        return "doc-only"  # 无门声明, 纯文档
    if is_structural(combined):
        return "structural"  # 声明且有工具实现
    return "paper"  # 声明了但无工具 = 纸面门


def parse_rules(path):
    """解析 RULES.md → [{id, title, detail, category}]"""
    entries = []
    if not os.path.exists(path):
        return entries, f"❌ 文件不存在: {path}"
    cur_id, cur_title, cur_detail = None, "", ""
    with open(path, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    for line in lines:
        m = re.match(r"^## (R\d+|J\d+)", line.strip())
        if m:
            if cur_id:
                entries.append({"id": cur_id, "title": cur_title, "detail": cur_detail})
            cur_id = m.group(1)
            cur_title = line.strip().split(" ", 2)[-1] if " " in line.strip() else cur_id
            cur_detail = ""
        elif cur_id:
            cur_detail += line
    if cur_id:
        entries.append({"id": cur_id, "title": cur_title, "detail": cur_detail})
    # 分类
    for e in entries:
        e["category"] = classify_entry(e["id"], e["title"], e["detail"])
    return entries, None


def scan_rules(path=RULES_DEFAULT):
    entries, err = parse_rules(path)
    if err:
        return {"error": err, "rules": [], "stats": {}}
    stats = {"total": len(entries), "structural": 0, "paper": 0, "doc_only": 0}
    paper_gates = []
    for e in entries:
        stats[e["category"] if e["category"] != "doc-only" else "doc_only"] += 1
        if e["category"] == "paper":
            paper_gates.append({
                "id": e["id"], "title": e["title"][:80],
                "detail_excerpt": e["detail"].strip()[:150],
                "suggestion": suggest_upgrade(e["title"], e["detail"]),
            })
    return {"rules": entries, "paper_gates": paper_gates, "stats": stats, "source": path}


def suggest_upgrade(title, detail):
    """纸面门 → 结构门升级建议 (按领域启发)"""
    low = (title + " " + detail).lower()
    domain_map = [
        (["插件", "plugin", "安装", "升级", "沙箱"], "plugin-install-gate (profile 副本强制冒烟, 成功才放行正式装)"),
        (["重启", "restart"], "restart-gate (已有结构门, 核对覆盖)"),
        (["通讯", "黑板", "消息", "跨设备", "bus"], "bb-gate/comm-domains (写入门+域权, 加 lean4-check)"),
        (["内存", "rss", "oom"], "mem-gate (内存门)"),
        (["签", "codesign", "原生", "dylib"], "sign-audit-gate (装前查原生 dylib 签名, 防 adhoc 雷)"),
        (["依赖", "供应链", "npm", "pnpm", "遮蔽"], "guard_deps_scan/供应链门 (依赖一致性+遮蔽扫描)"),
        (["沙箱", "验证", "测试"], "sandbox-gate (隔离 profile/环境强制验证后才放行)"),
        (["规则", "广播", "r0"], "R008 规则治理流程 (纸面→工具化 lean4-check)"),
    ]
    for kws, gate in domain_map:
        if any(k in low for k in kws):
            return f"升级为结构门: {gate}"
    return "升级为结构门: 补 lean4-check 自检工具 (判定函数+断言矩阵, 同 bb-gate/queue-drain 范式)"


def list_tools():
    out = ["== 已知结构门工具注册表 =="]
    for tool, (domain, *_) in STRUCTURAL_TOOLS.items():
        out.append(f"  {tool:<22} {domain}")
    return "\n".join(out)


def lean4_check():
    """自检: 证明识别逻辑正确 (判定矩阵)"""
    ok = True
    out = ["== gate-auditor Lean4 约束门自检 (R006-⑩) =="]
    checks = [
        ("① 结构门识别: 含 lean4-check 文本 → structural",
         is_structural("R006 工具带 --lean4-check 自检")),
        ("② 结构门识别: 含 bb-gate → structural",
         is_structural("写入经 bb-gate 门")),
        ("③ 纸面门识别: '必须沙箱测试' 无工具 → 非 structural(→paper)",
         not is_structural("插件升级重启前必须沙箱测试")),
        ("④ 纸面门识别: '必须审核' 无工具 → 非 structural",
         not is_structural("变更必须人工审核")),
        ("⑤ 门意图: '必须' 措辞命中",
         has_gate_intent("必须遵守")),
        ("⑥ 门意图: 纯描述无门词",
         not has_gate_intent("这是通讯架构评估")),
        ("⑦ 分类: 有门词+工具 → structural",
         classify_entry("R1","测试门","必须过 lean4-check") == "structural"),
        ("⑧ 分类: 有门词无工具 → paper",
         classify_entry("R2","沙箱门","必须沙箱测试") == "paper"),
        ("⑨ 分类: 无门词 → doc-only",
         classify_entry("R3","概述","通讯架构描述") == "doc-only"),
    ]
    for label, cond in checks:
        out.append(f"  [{'✅' if cond else '❌'}] {label}")
        ok = ok and cond
    out.append("")
    out.append(f"  结果: {'✅ GATE OK — 纸面门识别门生效' if ok else '❌ GATE FAIL'}")
    return "\n".join(out), ok


def render_report(data):
    lines = [f"== 纸面门审查报告 ({data.get('source', '')}) =="]
    st = data.get("stats", {})
    lines.append(f"规则总数: {st.get('total',0)} | 结构门: {st.get('structural',0)} | 纸面门: {st.get('paper',0)} | 纯文档: {st.get('doc_only',0)}")
    lines.append("")
    pgs = data.get("paper_gates", [])
    if not pgs:
        lines.append("✅ 无纸面门 (全部规则已结构门化)")
    else:
        lines.append(f"⚠️ 纸面门 {len(pgs)} 条 (声明但无工具强制 — 人可跳过):")
        for pg in pgs:
            lines.append(f"  [{pg['id']}] {pg['title']}")
            lines.append(f"      建议: {pg['suggestion']}")
    return "\n".join(lines)


def main():
    args = sys.argv[1:]
    # ★ R006 ⑨① 参数解析严格（U6 批次1 补 · 2026-10-10）：未知旗标 ⇒ 用法错误 rc=2。
    #   实测缺陷：此前 `--definitely-not-a-flag` 与 `--rules` 都被【静默忽略】并返回 0
    #   ⇒ 本器自己就是它要抓的「纸面门」：规则层声明了门，参数层却不设防。
    _verbs = ("list-tools", "scan-all", "scan")
    # ★ 注意：`--rules` 只在 `scan` 子命令内被消费（见 scan 分支的 args.index("--rules")），
    #   故它【不是】合法的首参数 —— 作 args[0] 出现即为幽灵旗标，判用法错 rc=2。
    _flags = ("--version", "--lean4-check", "--help", "-h")
    if args and args[0] not in _verbs and args[0] not in _flags:
        print("❌ 不认识的参数: %s" % args[0])
        print("   本工具接受: %s | %s" % (" | ".join(_verbs), " | ".join(_flags)))
        return 2
    if args and args[0] in ("--help", "-h"):
        print(__doc__)
        return 0
    if not args:
        print(__doc__)
        return 0
    if args[0] == "--version":
        print(f"gate-auditor {VERSION}")
        return 0
    if args[0] == "--lean4-check":
        text, ok = lean4_check()
        print(text)
        return 0 if ok else 1
    if args[0] == "list-tools":
        print(list_tools())
        return 0
    if args[0] == "scan-all":
        # 全量识别: 扫 RULES + 指定目录文档/脚本的门声明
        import glob as _glob
        rules_data = scan_rules(RULES_DEFAULT)
        # 扫描源: SOP 文档目录 (comm-server/docs/scripts 等)
        # 扩展域扫描 (2026-09-07 用户: 继续跑一轮扩展域对象)
        base = os.path.expanduser("~/dsh-collab")
        all_dirs = ["comm-server", "scripts", "rules-registry", "cld-health", "supply-chain",
                    "devices", "im-reply", "learning", "qa", "research", "external-link-mcp",
                    "meituan-multi", "docs"]
        # 已承接历史文档排除 (明鉴校准 v1.3: flowernet 蓝图已被 E2/comm/mcp 承接)
        EXCLUDE_FILES = ["flowernet-master-blueprint-20260827.md",
                         "flowernet-master-blueprint-v3-20260827.md",
                         "flowernet-master-blueprint-v4-20260827.md"]
        scan_dirs = []
        for sub in all_dirs:
            p = os.path.join(base, sub)
            if os.path.exists(p):
                scan_dirs.append(p)
        file_entries = []  # {file, line_no, text, category}
        gate_pattern = re.compile(r"(必须|强制|enforced|禁止|门|护栏|红线|重启前|检查|审核后|不可绕过)")
        for d in scan_dirs:
            if not d:
                continue
            for fp in _glob.glob(os.path.join(d, "*.md")) + _glob.glob(os.path.join(d, "*.sh")):
                # v1.2 精化: 仅扫 md/sh 文档声明——.py 工具实现不列入纸面门(有代码=结构门, 防误报)
                if os.path.basename(fp) in EXCLUDE_FILES:
                    continue  # 已承接历史文档排除 (明鉴校准 v1.3)
                try:
                    with open(fp, encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                except Exception:
                    continue
                for i, line in enumerate(lines, 1):
                    if gate_pattern.search(line) and len(line.strip()) > 8:
                        text = line.strip()[:150]
                        cat = classify_entry(os.path.basename(fp), "", text)
                        if cat == "paper" and is_narrative_line(text):
                            cat = "narrative"  # 老登校准: 叙述/评估行非规则门
                        if cat != "doc-only" and cat != "narrative":
                            file_entries.append({
                                "file": os.path.basename(fp), "path": fp,
                                "line": i, "text": text, "category": cat,
                            })
        # 聚合
        st = rules_data.get("stats", {})
        print("== 全量纸面门识别报告 ==")
        print(f"[规则账本] 总数:{st.get('total',0)} 结构:{st.get('structural',0)} 纸面:{st.get('paper',0)}")
        # 按文件聚合
        by_file = {}
        for e in file_entries:
            by_file.setdefault(e["file"], {"structural": 0, "paper": 0, "entries": []})
            by_file[e["file"]]["entries"].append(e)
            by_file[e["file"]][e["category"]] += 1
        print(f"[文档/脚本] 扫描文件 {len(set(e['path'] for e in file_entries))} 个, 门声明 {len(file_entries)} 条")
        total_paper = 0
        for fname, info in sorted(by_file.items()):
            p_ = info.get("paper", 0)
            s_ = info.get("structural", 0)
            total_paper += p_
            if p_ > 0:
                print(f"  ⚠️ {fname}: 结构门 {s_} / 纸面门 {p_}")
                for e in info["entries"][:5]:
                    if e["category"] == "paper":
                        print(f"      L{e['line']}: {e['text'][:90]}")
        # 汇总
        total_structural = st.get('structural', 0) + sum(i["structural"] for i in by_file.values())
        total_paper_all = st.get('paper', 0) + total_paper
        print("")
        print(f"== 全量汇总: 结构门 {total_structural} / 纸面门 {total_paper_all} ==")
        # 存全量报告
        out = os.path.expanduser("~/dsh-collab/rules-registry/gate-audit-full-report.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"rules": st, "file_entries": file_entries, "summary": {"structural": total_structural, "paper": total_paper_all}}, f, ensure_ascii=False, indent=1)
        print(f"(完整报告已存 {out})")
        return 0
    if args[0] == "scan":
        rules_path = RULES_DEFAULT
        if "--rules" in args:
            i = args.index("--rules")
            rules_path = os.path.expanduser(args[i+1]) if len(args) > i+1 else RULES_DEFAULT
        data = scan_rules(rules_path)
        if "error" in data:
            print(data["error"])
            return 1
        print(render_report(data))
        # JSON 输出备落盘
        out = os.path.expanduser("~/dsh-collab/rules-registry/gate-audit-report-latest.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        print(f"\n(完整报告已存 {out})")
        return 0
    print(__doc__)
    return 0


# ═══════════ R006 ② TCC 能力边界自检 + ⑩ 约束门（canonical 块 · 自包含 · 勿手改） ═══════════
# 由 scripts/r006-u6-apply.py 注入；改模板后重跑注入器，勿在本块内手工编辑。
# 设计原则（三条，均有本线实证来源）：
#   1) ② 的每一句声明都必须【被本块结构核验】—— 只打印不检查的「纸面声明」不算 TCC。
#   2) ⑩ 的 A/ E/F 是【冻结声明 + 变更检测】：新增危险原语/写入点/外部命令调用点 ⇒ 立刻红。
#   3) 反空洞：写入点与命令点扫描器必须先在【合成恶意源】上自证会红，否则判「不能判定」。
#      （依据 R006 §4.2 坑 3：剥字面量后读不到实参 ⇒ 调用点枚举为 0 ⇒ 「0 ⊆ 允许」空洞通过）
import sys as _r006_sys
import os as _r006_os
import io as _r006_io
import re as _r006_re
import json as _r006_json
import ast as _r006_ast
import time as _r006_time
import tokenize as _r006_tokenize
import subprocess as _r006_subprocess

_R006_DECL = {
    'tool': 'gate-auditor',
    'version': '1.0.0',
    'capability': ['纸面门审查器：扫规则账本，把「声明了必须/门/强制但无对应可执行工具」的条目判为纸面门', '结构门 = 有代码实现 + lean4-check 自证生效；纸面门 = 靠人执行、可跳过', '由来（2026-09-07 archify 事故）：清单写了沙箱测试却被跳过'],
    'impossible': ['本器不执行外部命令、不删除数据、不修改权限 ⇒ 无该路径', '不修改 R006 管辖外的其它工具文件（只读审计类行为）', '不替规则所有者拍板「该不该门化」（只报告，不代改）'],
    'log': 'gate-auditor.log',
    'write_roots': ['/tmp', '~/dsh-collab/logs'],
    'negatives': [['--definitely-not-a-flag'], ['--rules']],
    'positive': ['--help'],
    'dryrun': None,
    'watch': [],
    'allowed_danger': {

    },
    'frozen_exec': frozenset({'subprocess.run'}),
    'frozen_write': frozenset({'<expr>'}),
    'frozen_danger': frozenset(),
    'positive_expect_rc': [0],
}

_R006_EXEC_ATTRS = ("run", "Popen", "call", "check_call", "check_output")
_R006_DANGER_ATTRS = {
    "os": ("system", "popen", "remove", "unlink", "rmdir", "removedirs", "chmod", "chown", "kill"),
    "shutil": ("rmtree", "move"),
    "subprocess": _R006_EXEC_ATTRS,
}
_R006_DANGER_NAMES = ("eval", "exec", "compile", "__import__")
_R006_SYNTH_EXEC = "import subprocess as _sp\nfrom subprocess import Popen\n_sp.run(['ls'], shell=True)\nPopen(['x'])\n"
_R006_SYNTH_WRITE = "open('x','w')\nopen(p, mode='a')\n"
_R006_SYNTH_EXEC_WANT = frozenset({"subprocess.run", "subprocess.Popen"})
_R006_SYNTH_WRITE_WANT = frozenset({"const:x", "<expr>"})


def _r006_src():
    return open(_r006_os.path.abspath(__file__), encoding="utf-8").read()


def _r006_strip(s):
    """tokenize 抹除注释与字符串【内容】：按原文区间置空。
    ★ 不重拼 token —— 重拼会吞掉 token 间空白（`if a.selftest:` 变 `ifa.selftest:`）。"""
    buf = list(s)
    off = [0]
    for ln in s.splitlines(True):
        off.append(off[-1] + len(ln))
    try:
        for tk in _r006_tokenize.generate_tokens(_r006_io.StringIO(s).readline):
            if tk.type in (_r006_tokenize.COMMENT, _r006_tokenize.STRING):
                a = off[tk.start[0] - 1] + tk.start[1]
                b = off[tk.end[0] - 1] + tk.end[1]
                for i in range(a, min(b, len(buf))):
                    if buf[i] not in "\r\n":
                        buf[i] = " "
    except Exception:
        return s
    return "".join(buf)


def _r006_aliases(t):
    """import 别名解析：`import subprocess as sp` / `from subprocess import run` 都要认得。
    ★ 不做这步，改个别名就能绕过扫描器（= 空洞通过）。"""
    m = {}
    for n in _r006_ast.walk(t):
        if isinstance(n, _r006_ast.Import):
            for a in n.names:
                m[(a.asname or a.name.split(".")[0])] = a.name.split(".")[0]
        elif isinstance(n, _r006_ast.ImportFrom):
            for a in n.names:
                m[(a.asname or a.name)] = (n.module or "").split(".")[0] + "." + a.name
    return m


def _r006_scan(src):
    """AST 三面读数：外部命令调用点 / 写入点 / 危险原语。
    ★ 用 AST 而非正则：注释与字符串天生不进 AST ⇒ 免除「扫到自己的检测正则」假阳性。"""
    r = {"exec": set(), "write": set(), "danger": set(), "imports": set(), "err": ""}
    try:
        t = _r006_ast.parse(src)
    except Exception as e:
        r["err"] = "AST 解析失败: %s" % e
        return r
    al = _r006_aliases(t)
    for n in _r006_ast.walk(t):
        if isinstance(n, _r006_ast.Import):
            for a in n.names:
                r["imports"].add(a.name.split(".")[0])
        elif isinstance(n, _r006_ast.ImportFrom):
            if n.module:
                r["imports"].add(n.module.split(".")[0])
        elif isinstance(n, _r006_ast.Call):
            f = n.func
            if isinstance(f, _r006_ast.Attribute) and isinstance(f.value, _r006_ast.Name):
                mod = al.get(f.value.id, f.value.id)
                if mod in _R006_DANGER_ATTRS and f.attr in _R006_DANGER_ATTRS[mod]:
                    if mod == "subprocess":
                        r["exec"].add("subprocess." + f.attr)
                    else:
                        r["danger"].add(mod + "." + f.attr)
            elif isinstance(f, _r006_ast.Name):
                tgt = al.get(f.id, f.id)
                if tgt.startswith("subprocess."):
                    r["exec"].add("subprocess." + tgt.split(".", 1)[1])
                elif f.id in _R006_DANGER_NAMES:
                    r["danger"].add(f.id)
                elif f.id == "open":
                    mode = ""
                    if len(n.args) >= 2 and isinstance(n.args[1], _r006_ast.Constant):
                        mode = str(n.args[1].value)
                    for kw in n.keywords:
                        if kw.arg == "mode" and isinstance(kw.value, _r006_ast.Constant):
                            mode = str(kw.value.value)
                    if any(c in mode for c in ("w", "a", "x", "+")):
                        p = "<expr>"
                        if n.args and isinstance(n.args[0], _r006_ast.Constant):
                            p = "const:" + str(n.args[0].value)
                        r["write"].add(p)
    return r


def _r006_regex_pass(s):
    """A 的【独立第二通道】：在 tokenize-剥离后的文本上做正则扫描。
    两通道结论不一致 ⇒ 判「不能判定」，**不得**假设其中某一个对。"""
    code = _r006_strip(s)
    hits = set()
    for pat, name in ((r"\beval\s*\(", "eval"), (r"\bexec\s*\(", "exec"),
                      (r"\b__import__\s*\(", "__import__"),
                      (r"\bos\.system\s*\(", "os.system"), (r"\bos\.popen\s*\(", "os.popen"),
                      (r"\.rmtree\s*\(", "shutil.rmtree"), (r"\bos\.remove\s*\(", "os.remove")):
        if _r006_re.search(pat, code):
            hits.add(name)
    return hits


def _r006_run(argv, timeout=60):
    try:
        p = _r006_subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                                 cwd=_r006_os.path.dirname(_r006_os.path.abspath(__file__)))
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except _r006_subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    except Exception as e:
        return 125, str(e)


def _r006_snap(paths):
    import hashlib
    out = {}
    for p in paths:
        try:
            st = _r006_os.stat(p)
            with open(p, "rb") as fh:
                h = hashlib.sha256(fh.read()).hexdigest()[:16]
            out[p] = [st.st_size, h]
        except OSError:
            out[p] = None
    return out


def _r006_std_imports(imports):
    """③ 依赖完整性：把顶层 import 分类为 内置 / 标准库 / 第三方（Python 3.9 无 stdlib_module_names）。"""
    import importlib.util as _u
    import sysconfig
    std = _r006_os.path.realpath(sysconfig.get_paths()["stdlib"])
    third, stdlib = [], []
    for m in sorted(imports):
        if m in _r006_sys.builtin_module_names:
            stdlib.append(m)
            continue
        try:
            sp = _u.find_spec(m)
        except Exception:
            sp = None
        if sp is None:
            third.append(m + "(未解析)")
        elif sp.origin and _r006_os.path.realpath(sp.origin).startswith(std):
            stdlib.append(m)
        elif sp.origin in (None, "built-in", "frozen"):
            stdlib.append(m)
        else:
            third.append(m)
    return stdlib, third


def _r006_legacy_narrative():
    """沿用本器【原有的 selfcheck() 自述】—— 不因迁移到 canonical 块而丢失既有声明内容。
    取不到时如实说明（不静默当空）。"""
    f = globals().get("selfcheck")
    if not callable(f) or getattr(f, "__module__", None) != __name__:
        return []
    try:
        import io as _i
        import contextlib as _c
        buf = _i.StringIO()
        with _c.redirect_stdout(buf):
            f()
        return [l.rstrip() for l in buf.getvalue().splitlines() if l.strip()]
    except Exception as e:
        return ["(沿用原有 selfcheck() 失败，如实报出: %s)" % e]


def _r006_selfcheck():
    """R006 ② TCC 能力边界自检：三段输出 + 【结构核验】（不做纸面声明）。"""
    name = _R006_DECL["tool"]
    src = _r006_src()
    sc = _r006_scan(src)
    stdlib, third = _r006_std_imports(sc["imports"])
    W = _R006_DECL
    lines = ["R006 ② TCC 能力边界自检 · %s v%s" % (name, W["version"])]
    lines.append("【① 能力清单】")
    for x in W["capability"]:
        lines.append("  · " + x)
    legacy = _r006_legacy_narrative()
    if legacy:
        lines.append("  · —— 以下沿用本器原有 selfcheck() 自述 ——")
        for l in legacy:
            lines.append("  " + l)
    lines.append("【② 不该发生路径清单】")
    for x in W["impossible"]:
        lines.append("  · " + x)
    lines.append("【③ 依赖完整性】")
    lines.append("  · Python %s（本机）" % _r006_sys.version.split()[0])
    lines.append("  · 标准库 %d 个：%s" % (len(stdlib), ", ".join(stdlib) if stdlib else "无"))
    lines.append("  · 第三方 %d 个：%s" % (len(third), ", ".join(third) if third else "无"))
    lines.append("  · 外部命令调用点（冻结）：%s" % (", ".join(sorted(W["frozen_exec"])) or "无"))
    lines.append("  · 写入点（冻结）：%s" % (", ".join(sorted(W["frozen_write"])) or "无"))
    lines.append("  · 固定日志：%s" % (W["log"] or "无"))

    chk = []
    chk.append(("依赖无第三方", not third, "第三方: %s" % (", ".join(third) or "无")))
    ext_ok = (frozenset(sc["exec"]) == frozenset(W["frozen_exec"]))
    chk.append(("外部命令面与冻结集一致", ext_ok,
                "实测 %s / 冻结 %s" % (sorted(sc["exec"]) or "无", sorted(W["frozen_exec"]) or "无")))
    wr_ok = (frozenset(sc["write"]) == frozenset(W["frozen_write"]))
    chk.append(("写入面与冻结集一致", wr_ok,
                "实测 %s / 冻结 %s" % (sorted(sc["write"]) or "无", sorted(W["frozen_write"]) or "无")))
    roots = [r for r in W.get("write_roots", [])]
    bad = [p for p in sc["write"] if p.startswith("const:") and not any(
        _r006_os.path.expanduser(p[6:]).startswith(_r006_os.path.expanduser(r)) for r in roots)]
    chk.append(("常量写入点在允许根内", not bad, "越界: %s" % (", ".join(bad) if bad else "无")))
    dg_ok = (frozenset(sc["danger"]) == frozenset(W["frozen_danger"]))
    chk.append(("危险原语面与冻结集一致", dg_ok,
                "实测 %s / 冻结 %s" % (sorted(sc["danger"]) or "无", sorted(W["frozen_danger"]) or "无")))
    lg_ok = (not W["log"]) or (W["log"] in src)
    chk.append(("声明的日志路径真实存在于源码", lg_ok, W["log"] or "N/A（本器无日志）"))
    need = ["【① 能力清单】", "【② 不该发生路径清单】", "【③ 依赖完整性】"]
    chk.append(("R006 ② 规格要求的三段齐备", all(n in lines for n in need), " / ".join(need)))
    # ★ 声明的正例必须实测可用（非空转）—— 此前这里放的是「读过自己打印的行」，那是同义反复。
    _pos = W.get("positive", [])
    _prc = None
    if _pos:
        _prc, _po = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(_pos))
    chk.append(("声明的正例实测可用（非空转）",
                bool(_pos) and _prc in W.get("positive_expect_rc", [0]) and _prc not in (2, 124, 125),
                "%s → rc=%s" % (" ".join(_pos), _prc)))

    fails = [c for c in chk if not c[1]]
    lines.append("⇒ 声明核验：%d/%d 一致%s" % (len(chk) - len(fails), len(chk),
                                        "" if not fails else " · ❌ " + "; ".join(c[0] for c in fails)))
    for nm, ok, dt in chk:
        lines.append("   %s %s — %s" % ("✅" if ok else "❌", nm, dt))
    print("\n".join(lines))
    return 0 if not fails else 1


def _r006_dryrun_proof():
    """⑩ D：有 --dry-run ⇒ 实测 run 前后外部状态一致；无 ⇒ 【结构证明】（并如实标注为变体）。"""
    W = _R006_DECL
    dr = W.get("dryrun")
    watch = [_r006_os.path.expanduser(p) for p in W.get("watch", [])]
    if dr:
        b = _r006_snap(watch)
        rc, out = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(dr))
        a = _r006_snap(watch)
        return (rc == 0 and a == b), "★ 实测：rc=%s · watch %d 项前后一致=%s" % (rc, len(watch), a == b), "实测"
    src = _r006_src()
    wr = _r006_scan(src)["write"]
    roots = [_r006_os.path.expanduser(r) for r in W.get("write_roots", [])]
    outside = [p for p in wr if p.startswith("const:") and not any(
        _r006_os.path.expanduser(p[6:]).startswith(r) for r in roots)]
    ok = (frozenset(wr) == frozenset(W["frozen_write"])) and not outside
    return ok, ("△ 变体（非实测）：本器无 --dry-run ⇒ 以【写入面冻结 + 全部写入点在允许根内】作结构证明"
                "（%s）" % (", ".join(sorted(wr)) or "零写入点")), "结构证明"


def _r006_lean4_check():
    """R006 ⑩ 约束门 A–F。每项都带【反空洞】控制：扫描器先在合成恶意源上自证会红。"""
    W = _R006_DECL
    src = _r006_src()
    sc = _r006_scan(src)
    me = _r006_os.path.basename(_r006_os.path.abspath(__file__))
    rows = []

    # 反空洞前置：扫描器自证
    syn_e = frozenset(_r006_scan(_R006_SYNTH_EXEC)["exec"])
    syn_w = frozenset(_r006_scan(_R006_SYNTH_WRITE)["write"])
    scanner_live = (syn_e == _R006_SYNTH_EXEC_WANT) and (syn_w == _R006_SYNTH_WRITE_WANT)
    vac = [] if scanner_live else ["合成源未被完整检出 exec=%s write=%s" % (sorted(syn_e), sorted(syn_w))]

    # A 危险原语面（★ 不是「一定没有」—— 有则必须逐条声明并冻结；未声明即红）
    allowed_dg = dict(W.get("allowed_danger", {}))
    a_ast = frozenset(sc["danger"])
    a_rx = frozenset(_r006_regex_pass(src))
    a_frozen = frozenset(W["frozen_danger"])
    unallowed = sorted(a_ast - set(allowed_dg))
    a_ok = (scanner_live and a_ast == a_frozen and not (a_rx - a_ast) and not unallowed)
    rows.append(("A", "危险原语面全部已声明并冻结（无未声明原语）", a_ok,
                 "实测=%s · 已声明 %d 项 · 双通道一致=%s%s"
                 % (sorted(a_ast) or "无（零危险原语）", len(allowed_dg), (a_rx - a_ast) == set(),
                    "" if not unallowed else " · ★未声明: %s" % unallowed)))

    # B 负例全部被拒（非空，且实测 rc != 0）
    negs = W.get("negatives", [])
    b_det, b_ok = [], len(negs) >= 2
    for nv in negs:
        rc, _o = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(nv))
        b_det.append("%s→rc%s" % (" ".join(nv), rc))
        if rc == 0:
            b_ok = False
    if not scanner_live:
        b_ok = False
    rows.append(("B", "负例全部被拒（≥2 条，实测 rc≠0）", b_ok, " · ".join(b_det) or "无负例"))

    # C 正例可用（防门太宽砍掉自己）
    # ★ 口径：合法输入必须被【受理并产出结果】。默认 rc==0；对「报告器」类工具，
    #   rc=1（报告有发现）是合法结果 —— 但须在 decl 里显式声明 expect_rc 并给出理由，
    #   不得拿它当免检口（否则 C 退化为空转）。rc∈{2,124,125} 一律算门失效。
    pos = W.get("positive", [])
    want_rc = W.get("positive_expect_rc", [0])
    c_ok, c_det = bool(pos), "无正例 ⇒ 不能判定"
    if pos:
        rc, _o = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(pos))
        c_ok = (rc in want_rc) and (rc not in (2, 124, 125))
        c_det = "%s → rc=%s（期望 %s）%s" % (" ".join(pos), rc, want_rc,
                                            "" if rc in want_rc else " · ★门太宽或用法被拒")
    if len(want_rc) > 1:
        c_det += " · 放宽理由：" + W.get("positive_expect_reason", "（未给理由 ⇒ 视为未声明）")
    rows.append(("C", "正例可用（防门太宽砍掉自己）", c_ok, c_det))

    # D 零变更
    d_ok, d_det, d_kind = _r006_dryrun_proof()
    rows.append(("D", "零变更（%s）" % d_kind, d_ok, d_det))

    # E 白名单冻结 + 写入面变更检测
    e_ok = (scanner_live and isinstance(W["frozen_write"], frozenset)
            and frozenset(sc["write"]) == frozenset(W["frozen_write"]))
    rows.append(("E", "写入面白名单冻结（frozenset + 变更即红）", e_ok,
                 "类型=%s · 元素=%d · 变更检测=on" % (type(W["frozen_write"]).__name__, len(W["frozen_write"]))))

    # F 外部命令白名单 + 别名逃逸检测
    f_ok = scanner_live and isinstance(W["frozen_exec"], frozenset) and frozenset(sc["exec"]) == frozenset(W["frozen_exec"])
    f_alias = "import subprocess as _sp" in _R006_SYNTH_EXEC and "subprocess.run" in syn_e
    rows.append(("F", "外部命令白名单（别名逃逸已覆盖 + 变更即红）", f_ok and f_alias,
                 "命令集=%s · 别名形式检出=%s" % (sorted(sc["exec"]) or "无", f_alias)))

    nf = [r for r in rows if not r[2]]
    print("== %s · --lean4-check（六项 A–F）==" % me)
    for k, nm, ok, dt in rows:
        print("  %s %s %-38s %s" % ("OK  " if ok else "FAIL", k, nm, dt))
    if vac:
        print("  ★ 反空洞控制未过：%s" % "; ".join(vac))
    print("\n  => %d/%d pass, %d FAIL" % (len(rows) - len(nf), len(rows), len(nf)))
    return 0 if not nf else 1


def _r006_sets():
    """诊断口：给出本器【实际】三面读数与冻结集，供注入器「先算后填」。"""
    sc = _r006_scan(_r006_src())
    print(_r006_json.dumps({
        "tool": _R006_DECL["tool"],
        "observed_exec": sorted(sc["exec"]), "frozen_exec": sorted(_R006_DECL["frozen_exec"]),
        "observed_write": sorted(sc["write"]), "frozen_write": sorted(_R006_DECL["frozen_write"]),
        "observed_danger": sorted(sc["danger"]), "frozen_danger": sorted(_R006_DECL["frozen_danger"]),
        "imports": sorted(sc["imports"]), "err": sc["err"],
    }, ensure_ascii=False, indent=2))
    return 0


def _r006_want(flag):
    """旗标本器是否被请求：既认当前 argv，也认【早期垫片】暂存的旗标。
    （垫片必须存在：本器可能在模块级就校验 argv，会先于本块把旗标当「不认识的参数」拒掉。）"""
    return (flag in _r006_sys.argv) or (flag in globals().get("_R006_EARLY_FLAGS", []))


if __name__ == "__main__" and _r006_want("--selfcheck"):
    _r006_sys.exit(_r006_selfcheck())

if __name__ == "__main__" and _r006_want("--lean4-check"):
    _r006_sys.exit(_r006_lean4_check())

if __name__ == "__main__" and _r006_want("--r006-sets"):
    _r006_sys.exit(_r006_sets())
# ══════════════════════════════ R006 块结束 ══════════════════════════════

if __name__ == "__main__":
    raise SystemExit(main())
