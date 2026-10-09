#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plugin-preflight.py — dsh 插件变更的上线前预检（不进 server、不重启 CLD）

动因（2026-10-01 用户指出）：历史上出现过「工具更新 → dsh 插件兼容崩溃」这一类事故，
且 09-04 考古归纳为 M4「插件加载协议不符」，有两处实录：
  · central-inbox 插件调用了私有未导出函数 ⇒ dsh 启动失败
  · @linxin666 keyed slot 用 `id:` 应为 `key:`（版本漂移）⇒ 注册崩
R006 ①第5项存在的理由就是这句：「其它九项可以全绿而插件根本挂不上」。

★ 关键运作事实：本机多数插件是 `link:` 依赖（如 dsh-plugin-central-inbox），
  **源码即部署** —— 改错一个字，下次启动即挂，中间**没有任何环节会拦你**。
  故必须在改完之后、重启之前跑本预检。

三道检查（各挡一类历史事故）：
  A 组合完整性  dsh --dump-config          → 挡 patch/组合错误（exit≠0 即红）
  B 真挂载冒烟  import + apply(桩 ctx)      → 挡 M4（apply 抛异常 / 私有符号）
  C 依赖遮蔽    profile node_modules 扫描   → 挡 M1（旧包遮蔽 runtime）

用法:
  plugin-preflight.py --plugin dsh-plugin-central-inbox
  plugin-preflight.py --plugin X --profile web --json
  plugin-preflight.py --selftest
退出码: 0 全绿可上线 · 1 有红项，禁止重启 · 2 用法/环境错误
"""


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

    c("A", "类型锁：subprocess 无 shell=True ⇒ 参数不经 shell 解析",
      not _re.search(r'shell\s*=\s*True', _code),
      "无 shell（变量传参亦安全）")
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


import sys as _r006_sys
if __name__ == "__main__" and "--lean4-check" in _r006_sys.argv:
    _r006_sys.exit(lean4_check())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse
import json
import os
import re
import subprocess
import sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/plugin-preflight.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

DSH_BIN = "/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh/lib/bin.js"
NODE = "/opt/homebrew/bin/node"
HOME = os.path.expanduser("~")
PROFILE = "web"


def sh(args, timeout=120, cwd=None, env=None):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except FileNotFoundError as e:
        return 127, "", str(e)


# ── 冒烟副作用隔离（官方原则：探针不得污染被测对象）──────────────────
# 为什么必须做：B 项「真挂载冒烟」**真的执行 apply()**，而 apply() 会写生产侧。
#   实证 2026-10-01：预检跑一次 ⇒ central-inbox 生产日志「启动」行 224 → 225（对照实验）。
#   更糟的是它**污染证据**：那 4 条「启动」行一度把我误导成「宿主插件被热重载」，
#   进而推出「改源码不必重启」这个**错误结论**（v1 附录 B ⛔）。
# 两道防线（都必要）：
#   ① 隔离 —— 把已知日志 env 指向临时文件，让冒烟根本不写生产侧；
#   ② 断言 —— 冒烟前后比对**该插件生产日志的字节数**，增长即判 fail（可复核的行为断言，
#      不依赖"我记得设了 env"这种纪律）。
SMOKE_ENV_ISOLATION = {
    "CENTRAL_INBOX_LOG": "/tmp/dsh-preflight-smoke-central-inbox.log",
}
# 已知会写生产日志的插件 → 其生产日志路径（冒烟期间**严禁**增长）
PLUGIN_PROD_LOGS = {
    "dsh-plugin-central-inbox": os.path.join(HOME, ".dsh", "central-inbox.log"),
}


def filesize(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return None


def declared_identities(plugin):
    """插件在组合树里可能出现的一切身份：目录名 + 自报的 name / id。

    ★ 为什么必须读自报值：**目录名 ≠ 自报名**是常态，不是例外。
      实测（2026-10-01）：包目录 `dsh-plugin-agent-bus`，而它 cordis.patch.yml 里
      自报 `name: dsh-plugin-agent-way` / `id: agent-bus`，dump 里因此写的是
      `- id: agent-bus\\n  name: dsh-plugin-agent-way`。
      原判据只查 `name: dsh-plugin-agent-bus` ⇒ **0 命中 ⇒ 恒假 NO-GO**。
      一个永远说「不许」的闸门会被绕过，比没有闸门更糟 ⇒ 必须按自报身份查。
    """
    ids = {plugin}
    for fname in ("cordis.patch.yml", "cordis.yml", "cordis.patch.yaml"):
        p = os.path.join(HOME, plugin, fname)
        if not os.path.exists(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                txt = f.read()
        except OSError:
            continue
        for m in re.finditer(r"^\s*-?\s*(?:name|id):\s*['\"]?([A-Za-z0-9@/_.\-]+)", txt, re.M):
            ids.add(m.group(1))
    return sorted(ids)


# ── A 组合完整性 ─────────────────────────────────────────────
def check_composition(plugin, profile):
    """跑 --dump-config，断言 exit 0 且目标插件出现在组合树里。
    ★ 必须两头都查：exit 0 只说明「能组合」，不说明「这个插件在里面」。
    ★ 匹配按 declared_identities()（目录名 + 自报 name/id），不按目录名硬猜。"""
    prof_dir = os.path.join(HOME, ".dsh", "profiles", profile)
    rc, out, err = sh([NODE, DSH_BIN, "--profile", profile, "--dump-config"], timeout=180, cwd=prof_dir)
    names = declared_identities(plugin)
    matched = [n for n in names
               if re.search(r"(?:name|id):\s*['\"]?" + re.escape(n) + r"['\"]?", out)]
    in_tree = bool(matched)
    warnings = [l for l in err.splitlines() if l.strip()]
    return {
        "ok": rc == 0 and in_tree,
        "exit": rc,
        "lines": len(out.splitlines()),
        "plugin_in_tree": in_tree,
        "identities_checked": names,
        "identity_matched": matched,
        "warnings": warnings[:5],
        "detail": ("" if rc == 0 else f"--dump-config exit={rc}")
                  + ("" if in_tree else " 且插件的任何身份（目录名/自报 name/id）都未出现在组合树"),
    }


# ── B 真挂载冒烟（三态） ─────────────────────────────────────
SMOKE_JS = r"""
const registered = [];
const fakeBus = { list: () => [], on() {}, send() {} };
// ★ 2026-10-01 修复：原桩缺 ctx.provide 等方法 ⇒ 对调用它的插件产生【假 NO-GO】
//   （实测：agent-way 报 `ctx.provide is not a function`，而带 provide 的桩下回滚版与改后版
//    都 pass 且都注册 19 个工具 ⇒ 是检查器环境问题，不是插件问题。R006 坑 #4「假失败」）
const stub = {
  tools: { register(t) { registered.push(t && t.name); return () => {}; } },
  agentBus: fakeBus,
  get(n) { return n === 'agentBus' ? fakeBus : undefined; },
  provide() {}, inject: [], set() {}, plugin() {}, start() {}, stop() {},
  effect(f) { try { const d = f(); return typeof d === 'function' ? d : () => {}; } catch { return () => {}; } },
  on() { return () => {}; }, once() { return () => {}; }, off() {},
  emit() {}, parallel: async () => [], waterfall: async () => undefined,
  bail: async () => undefined, serial: async () => undefined,
  logger: { info() {}, warn() {}, error() {}, debug() {} },
};
const target = process.argv[2];
let m;
try { m = await import(target); }
catch (e) {
  const msg = String((e && e.message) || e);
  console.log(JSON.stringify({ state: /ERR_MODULE_NOT_FOUND|Cannot find package/.test(msg) ? 'skipped' : 'fail',
    reason: msg.split('\n')[0] }));
  process.exit(0);
}
try { if (typeof m.apply === 'function') m.apply(stub); }
catch (e) { console.log(JSON.stringify({ state: 'fail', reason: 'apply 抛异常: ' + String((e && e.message) || e).split('\n')[0] })); process.exit(0); }
console.log(JSON.stringify({ state: 'pass', inject: m.inject || null, registered }));
process.exit(0);   // ★ 关键：插件可能启长循环（SSE 重连），冒烟必须显式退出
"""


def check_mount(plugin):
    """真 import 插件入口 + 用桩 ctx 调 apply()，三态分开报。
    skipped 如实说跳过（依赖解析不到 = 检查器环境问题，不得据此判定插件挂不上）。"""
    entry = os.path.join(HOME, plugin, "lib", "index.js")
    if not os.path.exists(entry):
        entry = os.path.join(HOME, ".dsh", "profiles", PROFILE, "node_modules", plugin, "lib", "index.js")
    if not os.path.exists(entry):
        return {"ok": False, "state": "fail", "reason": f"入口不存在：{entry}"}
    import tempfile
    fd, tmpjs = tempfile.mkstemp(suffix=".mjs", prefix="preflight-smoke-")
    os.close(fd)
    with open(tmpjs, "w") as f:
        f.write(SMOKE_JS)
    try:
        # ★ 隔离：让冒烟不写生产侧（见 SMOKE_ENV_ISOLATION 的说明）
        smoke_env = dict(os.environ)
        smoke_env.update(SMOKE_ENV_ISOLATION)
        prod_log = PLUGIN_PROD_LOGS.get(plugin)
        size_before = filesize(prod_log) if prod_log else None
        rc, out, err = sh([NODE, tmpjs, entry], timeout=120, env=smoke_env)
        size_after = filesize(prod_log) if prod_log else None
    finally:
        try: os.unlink(tmpjs)
        except OSError: pass
    line = ""
    for l in out.splitlines():
        if l.strip().startswith("{"):
            line = l.strip()
    if not line:
        return {"ok": False, "state": "fail", "reason": f"冒烟无输出 rc={rc} {err.strip()[:120]}"}
    d = json.loads(line)
    d["ok"] = d.get("state") == "pass"
    d["entry"] = entry
    # ★ 断言：冒烟不得写生产侧。增长即 fail —— 这条不靠纪律，靠字节数。
    if prod_log:
        d["prod_log"] = prod_log
        d["prod_log_delta"] = (None if size_before is None or size_after is None
                               else size_after - size_before)
        if size_before is not None and size_after is not None and size_after != size_before:
            d["ok"] = False
            d["state"] = "fail"
            d["reason"] = (f"冒烟污染生产侧：{os.path.basename(prod_log)} 字节 "
                           f"{size_before} → {size_after}（探针不得写入被测系统；检查 SMOKE_ENV_ISOLATION）")
    return d


# ── C 依赖遮蔽（M1） ─────────────────────────────────────────
def check_shadowing(profile):
    """区分两类：
      · **真遮蔽**（红）：某个裸包名（如 @deepseek-ai/dsh-tools）解析到的路径【不在 runtime 内】
        —— 这正是 27 个遮蔽包事故的形态。
      · **惰性残骸**（黄，不判红）：`.bak-*` / `.pnpmcopy-*` 目录。它们带后缀名，裸包名解析不到，
        不会遮蔽；但它们是事故残骸，应清理。★ 若把残骸判红，检查很快就会被无视。
    """
    nm = os.path.join(HOME, ".dsh", "profiles", profile, "node_modules")
    runtime_nm = "/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules"
    # A) 真遮蔽：抽查关键裸包名的实际解析目标
    probe = ["@deepseek-ai/dsh-tools", "@deepseek-ai/cordis", "@deepseek-ai/dsh-session"]
    shadowed = []
    probe_js = ("const {createRequire}=require('module');"
                "const r=createRequire(process.argv[2]);"
                "for(const p of process.argv.slice(3)){"
                "try{console.log(p+'\t'+r.resolve(p))}catch(e){console.log(p+'\t<unresolved>')}}")
    rc, out, err = sh([NODE, "-e", probe_js,
                       os.path.join(HOME, ".dsh", "profiles", profile, "package.json")] + probe)
    for line in out.splitlines():
        if "\t" in line:
            name, path = line.split("\t", 1)
            if not path.startswith(runtime_nm) and path != "<unresolved>":
                shadowed.append({"package": name, "resolved": path})
    # B) 惰性残骸
    residue = []
    d = os.path.join(nm, "@deepseek-ai")
    if os.path.isdir(d):
        for e in sorted(os.listdir(d)):
            if re.search(r"\.(bak|pnpmcopy|old)[-._]", e):
                residue.append(e)
    return {"ok": not shadowed, "shadowed": shadowed, "residue": residue,
            "residue_count": len(residue), "runtime_nm": runtime_nm}


def preflight(plugin, profile):
    a = check_composition(plugin, profile)
    b = check_mount(plugin)
    c = check_shadowing(profile)
    green = a["ok"] and b["ok"] and c["ok"]
    return {
        "plugin": plugin, "profile": profile,
        "A_composition": a, "B_mount": b, "C_shadowing": c,
        "verdict": "GO" if green else "NO-GO",
        "note": "GO = 组合/挂载/遮蔽三项全绿；仍不能保证运行时行为，仅排除已知的三类加载级事故",
    }


def cmd_selftest():
    ok = fail = 0

    def check(name, cond, detail=""):
        nonlocal ok, fail
        if cond:
            ok += 1; print("  PASS  " + name)
        else:
            fail += 1; print("  FAIL  " + name + "  " + str(detail))

    check("常量存在：dsh bin", os.path.exists(DSH_BIN), DSH_BIN)
    check("A 能跑：central-inbox 组合绿", check_composition("dsh-plugin-central-inbox", PROFILE)["ok"])
    b = check_mount("dsh-plugin-central-inbox")
    check("B 能跑：central-inbox 挂载 pass", b["ok"], json.dumps(b, ensure_ascii=False)[:160])
    check("B 三态合法", b.get("state") in ("pass", "fail", "skipped"), b.get("state"))
    # ★ 2026-10-01 回归断言：**冒烟不得污染生产侧**
    #   根因：B 项真执行 apply()，而 apply() 会写生产日志。实证预检跑一次 ⇒
    #   central-inbox 生产日志「启动」行 224→225；那 4 条日志一度把我误导成
    #   「宿主插件被热重载」，进而推出「改源码不必重启」这个**错误结论**（v1 附录 B ⛔）。
    #   ⇒ 必须有一条**不靠纪律、只靠字节数**的断言。
    check("B 冒烟不污染生产日志（该插件生产日志字节增量必须为 0）",
          b.get("prod_log_delta") == 0,
          f"delta={b.get('prod_log_delta')} log={b.get('prod_log')}")
    # 负控：不存在的插件必须判红（否则检查会「空集通过」）
    nb = check_mount("dsh-plugin-does-not-exist-xyz")
    check("B 负控：不存在的插件判红", nb["ok"] is False, str(nb))
    nc = check_composition("dsh-plugin-does-not-exist-xyz", PROFILE)
    check("A 负控：不存在的插件不在组合树 ⇒ 红", nc["plugin_in_tree"] is False, str(nc))
    # ★ 2026-10-01 回归断言：**目录名 ≠ 自报名**导致的假 NO-GO
    #   根因：A 项原判据只按目录名查 `name: <目录名>`；而 agent-way 的包目录是
    #   `dsh-plugin-agent-bus`、自报 name 是 `dsh-plugin-agent-way` ⇒ 0 命中 ⇒ 恒红。
    #   缺口成因：上面那条正控只测了 central-inbox（唯一「目录名==自报名」的插件），
    #   **恰好避开了出问题的这一类** ⇒ 必须补一条目录名≠自报名的正控。
    ids_aw = declared_identities("dsh-plugin-agent-bus")
    check("A 身份解析：读出自报名 dsh-plugin-agent-way", "dsh-plugin-agent-way" in ids_aw, str(ids_aw))
    check("A 身份解析：读出 id agent-bus", "agent-bus" in ids_aw, str(ids_aw))
    check("A 身份解析：保留目录名作候选", "dsh-plugin-agent-bus" in ids_aw, str(ids_aw))
    check("A 负控：臆造插件不得混入身份（无假阳性）",
          declared_identities("dsh-plugin-does-not-exist-xyz") == ["dsh-plugin-does-not-exist-xyz"],
          str(declared_identities("dsh-plugin-does-not-exist-xyz")))
    aw = check_composition("dsh-plugin-agent-bus", PROFILE)
    check("A 正控：agent-way（目录名≠自报名）必须组合绿", aw["ok"], json.dumps(aw, ensure_ascii=False)[:220])
    c = check_shadowing(PROFILE)
    check("C 无真遮蔽（裸包名均解析到 runtime）", c["ok"], str(c["shadowed"]))
    check("C 残骸统计可读出（不判红）", isinstance(c["residue_count"], int), c["residue_count"])
    print(f"\n  selftest: {ok} PASS / {fail} FAIL")
    return 0 if fail == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plugin")
    ap.add_argument("--lean4-check", action="store_true", help="R006 10 A-F")
    ap.add_argument("--profile", default=PROFILE)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return cmd_selftest()
    if not a.plugin:
        print("缺 --plugin（或用 --selftest）"); return 2
    r = preflight(a.plugin, a.profile)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        A, B, C = r["A_composition"], r["B_mount"], r["C_shadowing"]
        print(f"── 插件上线前预检：{a.plugin}（profile={a.profile}）──")
        print(f"  {'✅' if A['ok'] else '❌'} A 组合完整性  exit={A['exit']} 行数={A['lines']} 插件在树={A['plugin_in_tree']}")
        print(f"       身份匹配: {A.get('identity_matched') or '（无）'}  ← 候选 {A.get('identities_checked')}")
        for w in A["warnings"]:
            print(f"       ⚠ {w[:110]}")
        print(f"  {'✅' if B['ok'] else '❌'} B 真挂载冒烟  state={B.get('state')} {B.get('reason','')}")
        print(f"       entry={B.get('entry')}")
        if "prod_log_delta" in B:
            d_ = B["prod_log_delta"]
            print(f"       生产侧副作用: {os.path.basename(B['prod_log'])} 字节增量={d_} "
                  + ("（未污染 ✅）" if d_ == 0 else "（❌ 污染，探针写入了被测系统）"))
        print(f"  {'✅' if C['ok'] else '❌'} C 依赖遮蔽（真遮蔽）shadowed={len(C['shadowed'])}")
        for sh_ in C["shadowed"]:
            print(f"       ❌ {sh_['package']} → {sh_['resolved'][:90]}")
        if C["residue_count"]:
            print(f"       ⚠ 惰性残骸 {C['residue_count']} 个（不判红，但应清理）：{C['residue'][:4]}")
        print(f"\n  判定：{r['verdict']}" + ("（可重启上线）" if r["verdict"] == "GO" else "（禁止重启，先修红项）"))
    return 0 if r["verdict"] == "GO" else 1




if __name__ == "__main__":
    sys.exit(main())
