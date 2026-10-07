#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""守灯 · rules-cli 守卫独立复验套件（v2）
归属：独立复验归守灯（实现归 HR）· 入档域：~/dsh-collab/cld-health/
方法三项（HR 已采纳入方法卡）：
  ① 正向用例 ② 反控（--force 应放行）③ 效果判据（以被保护对象 md5 为准，非日志文本）
覆盖：
  E  条数相同 + id 集合不同     → 应拒（HR 用例 C 的互补面）
  F  表头计数取正文实际         → 应写 N 条
  G1 仅调换字段顺序（v3 修复后）→ 应放行（假阳性已除）
  G2 回归：条数不变 + 改摘要文字 → 应拒并具名（检出力未降）
  G3 跨条移动行（详情行跨条搬移）→ 应拒（独立验证 HR 的"跨条移动仍会被抓到"）
  G4 条内重复行                 → 应拒
  R  反控：--force ⇒ 必须真覆盖
安全：BB 指向不可达端口；全部在 /tmp 伪 HOME，绝不触真板/真文件
"""
import json, os, shutil, subprocess, sys, hashlib

SBX = "/tmp/sbx-shoudeng-v2"
REG = os.path.join(SBX, ".dsh", "rules-registry")
SRC_REG = os.path.expanduser("~/dsh-collab/rules-registry")

shutil.rmtree(SBX, ignore_errors=True)
os.makedirs(REG, exist_ok=True)

cli = open(os.path.join(SRC_REG, "rules-cli.py"), encoding="utf-8").read()
cli = cli.replace('BB = "http://127.0.0.1:8792"', 'BB = "http://127.0.0.1:9"')
open(os.path.join(REG, "rules-cli.py"), "w", encoding="utf-8").write(cli)

data = json.load(open(os.path.join(SRC_REG, "rules.json"), encoding="utf-8"))
data.setdefault("audit", {})["ruleCount"] = 999          # 测表头修复
json.dump(data, open(os.path.join(REG, "rules.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
rules = data["rules"]
with_det = next(r for r in rules if r.get("detail"))
without_det = next(r for r in rules if not r.get("detail"))

def md_for(rule_list, reorder=False):
    out = ["# 规则账本（完整规则本）", "", "> vTEST | %d 条 | 所有总线设备必须服从" % len(rule_list), ""]
    for r in rule_list:
        out.append("## %s ✅ %s" % (r["id"], r["name"]))
        cls = "- 分类: %s | 范围: %s | 状态: %s" % (r.get("category"), r.get("scope"), r.get("status"))
        summ = "- 摘要: %s" % r.get("summary")
        det = ("- 详情: %s" % r["detail"]) if r.get("detail") else None
        body = [cls, summ] + ([det] if det else [])
        if reorder:
            body = list(reversed(body))
        out.extend(body)
        out.append("")
    return "\n".join(out)

def write_md(text):
    p = os.path.join(REG, "RULES.md")
    open(p, "w", encoding="utf-8").write(text)
    return hashlib.md5(open(p, "rb").read()).hexdigest(), p

def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()

def run_sync(force=False):
    env = dict(os.environ, HOME=SBX)
    args = [sys.executable, os.path.join(REG, "rules-cli.py"), "sync"] + (["--force"] if force else [])
    p = subprocess.run(args, capture_output=True, text=True, env=env, timeout=60)
    return p.stdout + p.stderr

results = []
def case(name, md_text, expect_reject, expect_names=None, force=False):
    before, path = write_md(md_text)
    out = run_sync(force=force)
    after = md5(path)
    rejected = "拒绝" in out
    unchanged = (before == after)
    named = all(n in out for n in (expect_names or []))
    ok = (rejected == expect_reject) and (unchanged == expect_reject) and named
    results.append((name, ok, rejected, unchanged, named))
    print("\n=== %s ===" % name)
    print("  期望拒绝=%s | 实际拒绝=%s | 文件未变=%s | 具名=%s" % (expect_reject, rejected, unchanged, named))
    for l in out.splitlines():
        if ("拒绝" in l) or ("独有" in l) or ("不一致条目" in l) or ("规则本:" in l):
            print("   ", l[:105])
    return out

case("E 条数相同+id集合不同（应拒，具名 R999/R001）",
     md_for(rules).replace("## R001 ", "## R999 "), True, ["R999", "R001"])

case("F 完全对齐（应放行）→ 校验表头取正文实际", md_for(rules), False)
written = open(os.path.join(REG, "RULES.md"), encoding="utf-8").read()
hdr = [l for l in written.splitlines() if l.startswith("> ")][:2]
print("   表头:", " / ".join(h.strip()[:80] for h in hdr))
print("   取正文实际条数:", "OK" if (("%d 条" % len(rules)) in written and "999" not in written) else "FAIL")

case("G1 仅调换字段顺序（v3 修复后应放行）", md_for(rules, reorder=True), False)

md_g2 = md_for(rules).replace("- 摘要: ", "- 摘要: 【手改】", 1)
case("G2 条数不变+改摘要文字（检出力回归，应拒且具名）", md_g2, True, ["R"])

md_g3 = md_for(rules)
det_line = "- 详情: %s" % with_det["detail"]
md_g3 = md_g3.replace(det_line + "\n", "", 1)
md_g3 = md_g3.replace("## %s ✅ %s\n" % (without_det["id"], without_det["name"]),
                      "## %s ✅ %s\n%s\n" % (without_det["id"], without_det["name"], det_line), 1)
case("G3 跨条移动行（应拒）", md_g3, True, [with_det["id"], without_det["id"]])

md_g4 = md_for(rules).replace("- 摘要: ", "- 摘要: 【重复行】\n- 摘要: ", 1)
case("G4 条内重复行（应拒）", md_g4, True, ["R"])

# G5: 同一 id 在 MD 出现两次（HR v4 新增；其首版取自 set ⇒ 计数恒 1 ⇒ 死代码）
#     关键：必须用**可失败样例**验证该门**真的会触发**（"永不触发的检查 = 不存在的检查"）
lines = md_for(rules).split("\n")
out_lines, dup_done = [], False
for ln in lines:
    out_lines.append(ln)
    if (not dup_done) and ln.startswith("## R001 "):
        # 把 R001 整段（含其后字段行）复制一份，制造重复 id
        out_lines.append(ln)
        dup_done = True
md_g5 = "\n".join(out_lines)
case("G5 同一 id 重复出现（应拒且具名『重复 id』）", md_g5, True, ["R001"])

before, path = write_md(md_for(rules).replace("## R001 ", "## R999 "))
md5_before = md5(path)
run_sync(force=True)
force_worked = md5_before != md5(path)
print("\n=== R 反控（--force 应真覆盖）===")
print("  md5 变化: %s ⇒ %s" % (force_worked, "覆盖路径可用（前项未覆盖确系守卫拦截）" if force_worked else "覆盖路径异常"))

print("\n" + "=" * 62)
print("独立复验汇总（v2）")
print("=" * 62)
allok = True
for name, ok, rej, unch, named in results:
    print("  %s  %s" % ("PASS" if ok else "FAIL", name))
    allok &= ok
print("  反控 --force 可用: %s" % ("PASS" if force_worked else "FAIL"))
print("\n  总体: %s" % ("ALL PASS" if (allok and force_worked) else "存在失败项"))
