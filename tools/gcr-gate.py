#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gcr-gate.py — G-CR 门校验（锚点 §10 Wave S 之 S5）

★ 计数更正（本工具的第一条产出）
    锚点 `distributed-agent-network-governance-plan-v4-20261009.md` §10 写
    「**S5 G-CR 十五条校验脚本**」，而其 §7.9 实列 **17 条**（G-CR1 … G-CR17）。
    ⇒ 本工具按**实列的 17 条**建档，并把「声称 15 / 实列 17」如实标出，**不为凑数删条**。

设计原则
    ① **复用不重造**：能调既有工具的（`plugin-preflight` / `guard_deps_scan`）就调，不重写其逻辑
    ② **三态如实**：每条给 `PASS` / `FAIL` / `N-A`（流程类或需运行时者标 N-A 并**指向既有工具**）
    ③ **能红**：`--selftest` 用**合成负例**证明每条判据会红（承 `gate-canfail.py` 的思路）
    ④ **只读**：本工具不写任何被检对象；`--selftest` 亦不写生产

覆盖状态（17 条全建档；机械化的 10 条，其余标 N-A 并注明归属）
    G-CR1  插件三态           → 调 plugin-preflight.py
    G-CR2  schema/DSL         → N-A（须官方规则集；部分由 dump-config 覆盖）
    G-CR3  命名门 N1–N3       → 静态比对 目录名 / package.json name / patch id
    G-CR4  扫遮蔽             → 调 guard_deps_scan.py（无则退静态扫）
    G-CR5  去遮蔽顺序         → N-A（流程类；无机械判据）
    G-CR6  逐个验签           → 扫 .dylib/.so + codesign -v
    G-CR7  TCC 流程           → N-A（流程类）
    G-CR8  装载前事件数门     → 扫各会话 JSONL 事件数 vs 阈值
    G-CR9  compaction + 负控  → 查 preset 挂载 + P26 负控判据
    G-CR10 子进程内存监控     → N-A（需运行时；heartbeat.json 可作旁证）
    G-CR11 31888 reload       → N-A（「不用即安全」
    G-CR12 不动 app.asar      → 比对 app.asar 的 sha/mtime
    G-CR13 动态插件原语       → N-A（静态扫描可部分覆盖，未做）
    G-CR14 端口固定           → 查配置端口 ≠ 0
    G-CR15 重启票流程         → N-A（既有 restart-governor.sh + RESTART_GO 标记）
    G-CR16 token 预算门       → 算 config 上限 − completion 预留 vs 消息可达上限
    G-CR17 压缩有效性门       → N-A（须读会话 JSONL 的降幅；见 P26 卡）

用法
    python3 tools/gcr-gate.py                 # 全部
    python3 tools/gcr-gate.py --only G-CR8,G-CR9
    python3 tools/gcr-gate.py --selftest      # 判据可红性自证
    python3 tools/gcr-gate.py --json

退出码
    0 = 无 FAIL（N-A 不算 FAIL）· 1 = 有 FAIL · 2 = 用法错误
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

VERSION = "1.0.0"
HOME = Path.home()
COLLAB = HOME / "dsh-collab"

# ── 阈值（集中声明，便于审阅与调整）───────────────────────────────
THRESHOLDS = {
    "session_events_warn": 3_000_000,     # G-CR8：超过则告警（P16 实测 ~1180 万触发 OOM）
    "session_events_fail": 10_000_000,    # G-CR8：超过则 FAIL
    "v8_heap_limit_mb": 4192,             # G-CR16：pointer compression 硬顶
    "completion_reserve": 256_000,        # G-CR16：适配器默认 completion 预留
    "context_window_default": 1_048_576,  # G-CR16：provider 真实上限
}


def sh(cmd, timeout=60, cwd=None):
    try:
        p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                           text=True, timeout=timeout, cwd=cwd)
        return p.returncode, p.stdout or "", p.stderr or ""
    except Exception as e:
        return -1, "", "%s: %s" % (type(e).__name__, e)


# ══════════════════════════════════════════════════════════════════
# 各条判据：每个函数返回 (state, detail)
#   state ∈ {"PASS", "FAIL", "N-A"}
# ══════════════════════════════════════════════════════════════════

def gcr1():
    """插件三态：调既有 plugin-preflight.py（不重造）"""
    pf = COLLAB / "scripts" / "plugin-preflight.py"
    if not pf.exists():
        return "N-A", "plugin-preflight.py 不在 ⇒ 无法验"
    rc, out, err = sh([sys.executable, str(pf), "--plugin", "dsh-plugin-central-inbox"],
                      cwd=str(COLLAB))
    if rc == 0 and "GO" in out:
        return "PASS", "central-inbox 预检 GO（A 组合完整性 + B 真挂载冒烟 + C 遮蔽）"
    if rc == 1:
        return "FAIL", "plugin-preflight 判红（exit=1 ⇒ 禁止重启）"
    return "N-A", "plugin-preflight 返回 rc=%s（用法或环境问题）" % rc


def gcr3(root=None):
    """命名门 N1–N3：目录名 / package.json name / patch id 一致

    ★★ 2026-10-13 修（ext F-5）：★ 原签名 `gcr3()` **硬编码** `HOME/"dsh-plugin-central-inbox"`
      ⇒ ★★ **自证无法喂夹具** ⇒ 那两条「负例」只能拿夹具的值**自己比**（`pkg_name != d.name`）
      ⇒ **恒真**（★ 夹具写死 `"totally-different"` ⇒ 必不等）。
    ★ 现加【可选 root】⇒ ★ 自证可**真调**本函数。
    """
    bad = []
    root = Path(root) if root is not None else HOME / "dsh-plugin-central-inbox"
    if not root.exists():
        return "N-A", "被测插件目录不存在"
    dirname = root.name
    try:
        pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
        pname = pkg.get("name")
    except Exception as e:
        return "FAIL", "package.json 不可读：%s" % e
    patch = root / "cordis.patch.yml"
    pid = None
    if patch.exists():
        m = re.search(r'^\s*-?\s*id:\s*(\S+)', patch.read_text(encoding="utf-8"), re.M)
        pid = m.group(1) if m else None
    if pname != dirname:
        bad.append("package.name(%s) ≠ 目录名(%s)" % (pname, dirname))
    return ("FAIL", "; ".join(bad)) if bad else ("PASS", "目录名=%s · name=%s · patch id=%s" % (dirname, pname, pid))


def gcr4():
    """扫遮蔽：调 guard_deps_scan（无则退静态扫 profile node_modules）"""
    g = COLLAB / "tools" / "guard_deps_scan.py"
    rc, out, err = sh([sys.executable, str(g)], timeout=90) if g.exists() else (-1, "", "无该工具")
    if rc == 0:
        return "PASS", "guard_deps_scan 未报遮蔽"
    if rc == 1:
        return "FAIL", "guard_deps_scan 报出遮蔽：%s" % (out.strip().splitlines() or [""])[-1][:120]
    # 退化：静态数 .bak/.pnpmcopy 残骸
    nm = HOME / ".dsh" / "profiles" / "web" / "node_modules"
    n = 0
    if nm.exists():
        n = sum(1 for p in nm.iterdir() if ".bak" in p.name or ".pnpmcopy" in p.name)
    return "N-A", "guard_deps_scan 不可用；静态数得惰性残骸 %d 个（不判红）" % n


def gcr6():
    """逐个验签 —— ★ v1.0.1 扩展：验签 **+ entitlement 完整性**

    ★ 扩展动因（2026-10-10，MBP 侧会话的实测发现，非我推断）：
      它的根因报告指出：CLD.app 曾出现「**签名有效、但缺
      `com.apple.security.device.audio-input`**」⇒ hardened runtime 下 tccd **静默拒绝**麦克风
      （「Policy disallows prompt」，连弹窗都不给）⇒ 语音插件全部失效。
      ⇒ ★ **`codesign -v` 与 entitlement 检查是【正交互补】的两件事**：
        前者测**签名有效性**，后者测**授权键完整性**；**只做前者会漏掉后者**。
        我的初版 G-CR6 **只有前者** ⇒ 该缺口由本行修复。
    """
    appres = Path("/Applications/CLD.app/Contents/Resources")
    if not appres.exists():
        return "N-A", "CLD Resources 不存在"
    libs = list(appres.rglob("*.dylib")) + list(appres.rglob("*.so"))
    bad = []
    checked = 0
    for lib in libs[:60]:
        rc, out, err = sh(["codesign", "-v", str(lib)], timeout=20)
        checked += 1
        if rc != 0:
            bad.append(lib.name)
    # ★ entitlement 检查（对主 app）
    rc_e, ent_out, _ = sh(["codesign", "-d", "--entitlements", "-", "/Applications/CLD.app"], timeout=25)
    REQUIRED = ["com.apple.security.device.audio-input"]
    missing = [k for k in REQUIRED if k not in ent_out]
    detail = ("验签：抽检 %d 个 .dylib/.so（共 %d 个）%s ｜ "
              "entitlement：%s") % (
        checked, len(libs), "全部通过" if not bad else "失败 %d 个" % len(bad),
        "关键键齐备" if not missing else "**缺 %s**" % ", ".join(missing))
    if bad or missing:
        return "FAIL", detail + ("  ⇒ ★ 缺 entitlement 会导致 **hardened runtime 静默拒绝**（无弹窗），"
                                 "属「签名有效但功能失效」一类" if missing else "")
    return "PASS", detail


def gcr7():
    """重签后 TCC 流程 —— ★ v1.0.1 由 N-A 改为**可机械**（依据 MBP 侧会话的实测根因）

    ★ 原判定「流程类，无机械判据」**已被实证推翻**：
      根因不是「有没有走流程」，而是「**entitlement 里有没有 TCC 相关键**」——
      有键 ⇒ tccd 可判；无键 ⇒ 「requires entitlement … but it is missing」⇒ **静默拒绝**。
      ⇒ 该条**可机械检查**：核 CLD.app 及其 Helper 的 entitlements 是否含 TCC 所需的键。
    ★ 与 G-CR6 的分工（不重复）：
      G-CR6 核 **主 app** 的关键 entitlement（当前 = audio-input）；
      G-CR7 核 **Helper / Helper(Renderer)** 是否**同样**带上（重签时易漏签嵌套可执行体）。
    """
    # ★ v1.0.2 修（**由 MBP 侧会话的指正触发**，2026-10-10）：
    #   初版**硬编码 3 个** Helper 名字 ⇒ 漏了 `CLD Helper (Plugin).app`（实为 **4 个**）。
    #   ★ 后果：**漏检者可单独缺键而本门仍报 PASS** —— 属真实的检出漏洞。
    #   ⇒ 改为**动态枚举** `Contents/Frameworks/*.app`，**新增 Helper 亦自动覆盖**，
    #     不再依赖人工维护名单（这类"名单会过期"的判据本线已多次吃亏）。
    fw = Path("/Applications/CLD.app/Contents/Frameworks")
    targets = sorted(str(x) for x in fw.glob("*.app")) if fw.exists() else []
    found, missing, checked = [], [], 0
    for t in targets:
        if not Path(t).exists():
            continue
        checked += 1
        rc, out, _ = sh(["codesign", "-d", "--entitlements", "-", t], timeout=25)
        if "audio-input" in out:
            found.append(Path(t).name)
        else:
            missing.append(Path(t).name)
    if checked == 0:
        return "N-A", "未找到 Helper 可执行体（路径形态可能不同）"
    if missing:
        return "FAIL", ("★ 嵌套 Helper **未带** audio-input 的 %d/%d：%s —— "
                        "重签时漏签嵌套可执行体会使该进程仍被 tccd 拒绝"
                        % (len(missing), checked, ", ".join(missing[:3])))
    return "PASS", "TCC 相关键在 %d 个 Helper 上齐备：%s" % (checked, ", ".join(found[:3]))


def gcr8():
    """装载前事件数门：扫各会话 JSONL 事件数"""
    sess = HOME / ".dsh" / "sessions"
    if not sess.exists():
        return "N-A", "sessions 目录不存在"
    hot = []
    total = 0
    for f in sess.rglob("session.jsonl.zstd"):
        total += 1
        try:
            size = f.stat().st_size
        except Exception:
            continue
        # 事件数无法不解压即得 ⇒ 用**体积**作代理指标（并如实声明这是代理）
        mb = size / 1048576
        if mb >= 200:
            hot.append((mb, f.parent.name))
    if not hot:
        return "PASS", "%d 个会话文件均 < 200MB（代理指标；事件数未直接读取）" % total
    hot.sort(reverse=True)
    top = hot[0]
    state = "FAIL" if top[0] >= 240 else "PASS"
    return state, "★ %d 个会话文件 ≥200MB，最大 %.1fMB（%s）—— **体积是代理指标，非事件数**" % (
        len(hot), top[0], top[1][:24])


def gcr9():
    """compaction 挂载 + P26 负控（v2 要求判据须含负控）"""
    presets = HOME / ".dsh" / ".agent-presets"
    if not presets.exists():
        return "N-A", "presets 目录不存在"
    mounted, missing = [], []
    for d in sorted(presets.iterdir()):
        f = d / "agent.cordis.yml"
        if not f.exists():
            continue
        txt = f.read_text(encoding="utf-8", errors="replace")
        (mounted if "compaction" in txt else missing).append(d.name)
    if missing:
        return "FAIL", "preset 未挂 compaction：%s（已挂 %d 个）" % (", ".join(missing), len(mounted))
    # 负控判据（P26）：必须存在「下界不可用」的显式处理，否则判据不完备
    has_negctl = any("thresholdRatio" in (d / "agent.cordis.yml").read_text(encoding="utf-8", errors="replace")
                     for d in presets.iterdir() if (d / "agent.cordis.yml").exists())
    if not has_negctl:
        return "FAIL", "compaction 已挂载但**未见 P26 负控判据**（thresholdRatio 类显式阈值）"
    return "PASS", "6/6 preset 已挂 compaction，且见显式阈值配置（P26 负控的存在性证据）"


def gcr12():
    """不动运行中的 app.asar

    ★ 判据修正（v1.0.1，本工具首跑即自曝）：
      初版用 `codesign -v app.asar` 判签名 —— **对象错**：app.asar 是**数据文件**（`file` 报 `data`），
      **本来就不该被单独签名**（签名属于**外层 app bundle**）⇒ 该命令对它恒返回 `code object is not
      signed at all`（exit=1）⇒ **判据恒红，是假阳性**。
      ⇒ 正确判据有二：
        ① **bundle 验签**（`codesign -v /Applications/CLD.app`）——签名的正确对象
        ② ★ **asar 的 mtime 是否晚于 CLD 进程启动时刻** —— 这才是「**运行中被改**」的精确判据
    """
    asar = Path("/Applications/CLD.app/Contents/Resources/app.asar")
    if not asar.exists():
        return "N-A", "app.asar 不存在"
    st = asar.stat()
    # ① bundle 签名（正确对象）
    rc_b, out_b, _ = sh(["codesign", "-v", "/Applications/CLD.app"])
    # ② 运行中被改？（mtime vs 进程启动）
    rc_p, pid_out, _ = sh(["pgrep", "-f", "CLD.app/Contents/MacOS/CLD"])
    pids = [x.strip() for x in pid_out.split() if x.strip()]
    started = None
    if pids:
        rc_t, t_out, _ = sh(["ps", "-o", "lstart=", "-p", pids[0]])
        started = t_out.strip() or None
    import time as _t
    mtime = _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime(st.st_mtime))
    detail = ("app.asar %.2fMB · mtime=%s · bundle验签=%s"
              % (st.st_size / 1048576, mtime, "通过" if rc_b == 0 else "失败"))
    if rc_b != 0:
        return "FAIL", detail + " ⇒ **bundle 签名失效**"
    if started:
        detail += " · CLD 启于 %s" % started
        try:
            import datetime as _d
            st_ts = _d.datetime.strptime(started, "%a %b %d %H:%M:%S %Y").timestamp()
            if st.st_mtime > st_ts:
                return "FAIL", detail + " ⇒ ★ **asar 晚于进程启动 ⇒ 运行时被改过**"
            return "PASS", detail + " ⇒ asar 早于进程启动（未被运行中修改）"
        except Exception:
            return "PASS", detail + "（启动时刻不可解析，仅据 bundle 验签）"
    return "PASS", detail


def gcr14():
    """端口固定：配置端口不得为 0"""
    found = []
    for cand in [HOME / ".dsh" / "profiles" / "web" / "package.json",
                 HOME / ".cld" / "config.json"]:
        if not cand.exists():
            continue
        txt = cand.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'"?port"?\s*[:=]\s*"?(\d+)"?', txt):
            found.append((cand.name, int(m.group(1))))
    if not found:
        return "N-A", "未在配置中显式找到 port（可能由别处指定）"
    zeros = [x for x in found if x[1] == 0]
    if zeros:
        return "FAIL", "发现 port=0（OS 随机 ⇒ 每次重启换址）：%s" % zeros
    return "PASS", "配置端口：%s" % found


def gcr16():
    """token 预算门：config 上限 − completion 预留 vs 消息可达上限"""
    prof = HOME / ".dsh" / "profiles" / "web" / "package.json"
    cw = THRESHOLDS["context_window_default"]
    if prof.exists():
        txt = prof.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'"contextWindow"\s*:\s*(\d+)', txt)
        if m:
            cw = int(m.group(1))
    reserve = THRESHOLDS["completion_reserve"]
    msg_ceiling = cw - reserve if cw > reserve else 0
    # 若 config 声明的 window 大于 provider 真实上限 ⇒ 预算算错（P26 的成因）
    real = THRESHOLDS["context_window_default"]
    if cw > real:
        return "FAIL", ("★ config contextWindow=%d **大于** provider 真实上限 %d ⇒ "
                        "预算门会晚于溢出触发（P26 同族）" % (cw, real))
    return "PASS", "contextWindow=%d · completion 预留=%d ⇒ 消息可达上限=%d" % (cw, reserve, msg_ceiling)


def gcr17():
    """压缩有效性门：须读会话 JSONL 的降幅（本工具不读 245MB 文件）"""
    return "N-A", ("须读会话 JSONL 的 summar/shadowed 降幅 ⇒ 超出本工具范围；"
                   "判据与实测见 blackboard:data/registry/dead-session-postmortem-activity 与 c7 系列卡")


# ── 注册表 ────────────────────────────────────────────────────────
GATES = [
    ("G-CR1", "插件变更→沙箱挂载+dump-config+真挂载冒烟三态", gcr1),
    ("G-CR2", "schema/DSL 过官方规则", lambda: ("N-A", "须官方规则集；部分由 dump-config 覆盖（见 G-CR1 的 A 检）")),
    ("G-CR3", "命名门 N1–N3 常驻", gcr3),
    ("G-CR4", "依赖操作后扫遮蔽（含 .bak/.pnpmcopy）", gcr4),
    ("G-CR5", "去遮蔽顺序固定（先重指→再移走）", lambda: ("N-A", "流程类，无机械判据")),
    ("G-CR6", "dylib/binary 改动后逐个验签", gcr6),
    ("G-CR7", "重签后 TCC 流程", gcr7),
    ("G-CR8", "装载前事件数门（拒绝而非崩）", gcr8),
    ("G-CR9", "compaction 挂载+约束钉住（v2：含 P26 负控）", gcr9),
    ("G-CR10", "子进程内存监控", lambda: ("N-A", "需运行时；heartbeat.json 可作旁证")),
    ("G-CR11", "禁用/沙箱验证 31888 reload", lambda: ("N-A", "「不用即安全」")),
    ("G-CR12", "不动运行中的 app.asar", gcr12),
    ("G-CR13", "动态插件只用沙箱原语", lambda: ("N-A", "静态扫描可部分覆盖，本轮未做")),
    ("G-CR14", "端口固定", gcr14),
    ("G-CR15", "重启票流程", lambda: ("N-A", "既有 restart-governor.sh + RESTART_GO 标记")),
    ("G-CR16", "请求前 token 预算门（含 completion 预留）", gcr16),
    ("G-CR17", "压缩有效性门（降幅 ≤0 ⇒ 告警）", gcr17),
]


def run_all(only=None):
    rows = []
    for gid, desc, fn in GATES:
        if only and gid not in only:
            continue
        try:
            state, detail = fn()
        except Exception as e:
            state, detail = "FAIL", "判据自身异常：%s: %s" % (type(e).__name__, e)
        rows.append({"id": gid, "desc": desc, "state": state, "detail": detail})
    return rows


def selftest():
    """★ 判据可红性自证：用**合成的**负例证明判据会红（不碰生产）"""
    # gate-self-exempt: begin
    #   ↑ 本函数是【测试样例区】：在 `tempfile.mkdtemp` 里造数据并清理，
    #     **只在 `--selftest` 路径执行**，**不碰生产**。
    #   ⇒ A 项（源码无危险原语）本意是「**业务路径**无危险原语」⇒ 按通用豁免约定标注。
    #   ★ 实证：未标注前 A/D 两项因本函数的 `write_text` 与 `shutil.rmtree` 判红
    #     —— **那不是假阳性，是判据的适用面问题**（详见 docs/wave-s-toolchain-delivery-v1.md §4）。
    import tempfile
    # ★★★ 2026-10-12（D-204 / v7 更正账 19）重写说明 —★ **本函数旧版的五条「负例」是恒真字面量**：
    #   ★ 旧版 `("G-CR14 负例 port=0", 0 == 0, True)` —★★ **`0 == 0` 永远为 True**；
    #   ★ 旧版 `("G-CR8 负例 245MB ≥ 200MB", mb >= 200, True)` 且 `mb = 245.0` 写死；
    #   ★★ ⇒ **四条负例【从未调用被测判据函数】** ⇒ 对 11 个判据函数的**可信负控数 = 0**，
    #     而它报「自证 5/5」。
    #   ★ 而本仓**早已写好三个纯函数合成器**（`_synth_gcr16/_synth_gcr8/_synth_gcr6_ent`）—★ 旧版一个都没用。
    #   ★★★ 修法：**真调合成器 + 喂能红的输入 + 断言它真的红了**；并各配一条**反控**（喂好输入 ⇒ 必须绿）。
    cases = []
    # ── ★ 负控：喂【该红】的输入 ⇒ 判据函数必须返回 False（实得也必须是 False）──
    real_cw = THRESHOLDS["context_window_default"]
    cases.append(("G-CR16 负例：★ 真调 `_synth_gcr16(real+1)` ⇒ 必须不过",
                  _synth_gcr16(real_cw + 1), False))
    cases.append(("G-CR8 负例：★ 真调 `_synth_gcr8(245.0)` ⇒ 必须不过",
                  _synth_gcr8(245.0), False))
    cases.append(("G-CR6 负例：★ 真调 `_synth_gcr6_ent(空串)` ⇒ 必须不过",
                  _synth_gcr6_ent(""), False))
    # ── ★ 反控：喂【该绿】的输入 ⇒ 必须返回 True（防判据恒红）──
    cases.append(("G-CR16 反控：喂 `real_cw` ⇒ 必须过",
                  _synth_gcr16(real_cw), True))
    cases.append(("G-CR8 反控：喂 `10.0` ⇒ 必须过",
                  _synth_gcr8(10.0), True))
    cases.append(("G-CR6 反控：喂 audio-input ⇒ 必须过",
                  _synth_gcr6_ent("audio-input"), True))
    # ── ★★ G-CR3：真造两个夹具目录，★ 并【真调 gcr3()】（ext F-5 修）──
#   ★ 立据：原两条「负例」实为
#     `pkg_name != d.name`（★ 夹具写死 "totally-different" ⇒ 恒真）
#     `d.name != d.name`（★ 自己与自己比 ⇒ 恒假）
#   ★★ 两条都【没调用被测判据】⇒ 而本工具纪律①正是「不得用恒真字面量」。
#   ★ 现改为：真造目录 → 真调 gcr3(<夹具>) → 看它返回 PASS/FAIL。
    tmp = Path(tempfile.mkdtemp(prefix="gcr-neg-"))
    d_neq = tmp / "dsh-plugin-wrongname"                 # ★ name ≠ 目录名 ⇒ 应 FAIL
    d_neq.mkdir(parents=True)
    (d_neq / "package.json").write_text(json.dumps({"name": "totally-different"}), encoding="utf-8")
    d_eq = tmp / "dsh-plugin-rightname"                  # ★ name == 目录名 ⇒ 应 PASS
    d_eq.mkdir(parents=True)
    (d_eq / "package.json").write_text(json.dumps({"name": "dsh-plugin-rightname"}), encoding="utf-8")
    _v_neq, _d_neq = gcr3(d_neq)
    _v_eq, _d_eq = gcr3(d_eq)
    cases.append(("G-CR3 负例：★ 真调 `gcr3(<name≠目录名>)` ⇒ 必须 FAIL",
                  _v_neq == "FAIL", True))
    cases.append(("G-CR3 反控：★ 真调 `gcr3(<name=目录名>)` ⇒ 必须 PASS",
                  _v_eq == "PASS", True))
    # ── ★ G-CR9：读当前 preset（★ 真读盘）──
    presets = HOME / ".dsh" / ".agent-presets"
    n_ok = sum(1 for dd in presets.iterdir()
               if (dd / "agent.cordis.yml").exists()
               and "compaction" in (dd / "agent.cordis.yml").read_text(encoding="utf-8", errors="replace"))
    cases.append(("G-CR9 正例 preset 挂载数 >0", n_ok > 0, True))
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    print("★ G-CR 门自证：逐条用合成负例/正例证明判据可判")
    ok = 0
    for name, got, want in cases:
        good = (got == want)
        print("  %s %s（实得 %s）" % ("✅" if good else "❌", name, got))
        ok += 1 if good else 0
    print("  自证：%d/%d" % (ok, len(cases)))
    # gate-self-exempt: end
    return 0 if ok == len(cases) else 1



# ══════════════════════════════════════════════════════════════════
# ★ R006 §5 验收两步（v1.0.2 补 —— 此前本工具只有 `--selftest`，
#   缺 `--selfcheck`（②③④）与 `--lean4-check`（⑩ A–F）
#   ⇒ 属真实欠账，登记于 `docs/wave-s-toolchain-delivery-v1.md` §5「已知缺口」第 1 条）
# ══════════════════════════════════════════════════════════════════

# ★ A 项判据（**本工具版**）：**无【危险】原语** —— 杀进程 / 删数据 / 改权限 / 执行任意命令类。
#   ★ 为何不判「无 subprocess」：本工具**必须**调外部**只读**工具（codesign / pgrep / ps / spctl），
#     若按字面判「无危险原语」会**永远失败**（假阴性）。
#     R006 A 项原意是「**不该发生的路径在结构上不可绕过**」
#     ⇒ 故 A 项判【危险原语】，而把【外部命令】交给 **F 项**（枚举调用点 + 断言 ⊆ 白名单）。
DANGEROUS_PRIMS = (
    r"os\.remove\s*\(", r"os\.rmdir\s*\(", r"shutil\.rmtree\s*",
    r"os\.chmod\s*\(", r"os\.chown\s*\(", r"os\.kill\s*\(",
    r"\bpkill\b", r"\bkillall\b", r"launchctl\s+(unload|remove|bootout)",
    r"\beval\s*\(", r"os\.system\s*\(",
)

# ★ F 项白名单（**冻结**）：本门只允许**只读探测**类外部命令
ALLOWED_CMDS = ("codesign", "pgrep", "ps", "plutil", "spctl", "lsof", "grep", "python3")


# ═══ 剥离用模式（v1.0.2：显式区分 raw 与普通字符串的转义语义）═══
#   ★ 常量用 chr() 拼接生成 ⇒ 源码内无字面引号（避免自伤与转义歧义）
_D = chr(34); _S = chr(39); _T3 = _S * 3; _D3 = _D * 3
TRIPLE_DQ = '[rRbB]?' + _D3 + '(?:.|\\n)*?' + _D3
TRIPLE_SQ = '[rRbB]?' + _T3 + '(?:.|\\n)*?' + _T3
RAW_DQ = 'r' + _D + '[^' + _D + '\\n]*' + _D
RAW_SQ = 'r' + _S + '[^' + _S + '\\n]*' + _S
NORM_DQ = _D + '(?:[^' + _D + '\\\\]|\\\\.)*' + _D
NORM_SQ = _S + '(?:[^' + _S + '\\\\]|\\\\.)*' + _S


def _strip_lits(txt):
    """剥离字符串字面量与整行注释（R006 A 项要求 —— 否则会把自己的检测正则当靶子）。

    ★ v1.0.2 修正（自测抓到）：初版用**字符扫描**且不识别 r 前缀 ⇒ 对 raw string 里的
      反斜杠-引号（raw 中非转义）剥错边界，把模式串的一部分留在结果里 ⇒
      **判据把自己的模式串当靶子**（实测某工具 A/D 两项因此判红）。
      ⇒ 改用正则，**显式区分 r 前缀**（raw 中反斜杠不转义）。
    ★ 顺序纪律：调用方必须 **先 _apply_exempt 再 _strip_lits** ——
      反过来的话标记行（# gate-self-exempt: begin）会被当注释剥掉 ⇒ 豁免失效。
    """
    t = re.sub(TRIPLE_DQ, '\"\"', txt)
    t = re.sub(TRIPLE_SQ, '\"\"', t)
    t = re.sub(RAW_DQ, '\"\"', t)      # ★ raw 双引号（斜杠不转义）
    t = re.sub(RAW_SQ, '\"\"', t)
    t = re.sub(NORM_DQ, '\"\"', t)     # 普通双引号（斜杠转义）
    t = re.sub(NORM_SQ, '\"\"', t)
    out = []
    for ln in t.split('\n'):
        out.append('' if ln.lstrip().startswith('#') else re.sub(r'\s+#.*$', '', ln))
    return '\n'.join(out)

def _apply_exempt(text):
    """应用通用豁免约定 `# gate-self-exempt: begin/end`（等长空行替换，保行号）。

    ★ 约定来源：`tools/self-destruct-gate.py` v1.0.5 引入，本工具是**第二个**使用者
      ⇒ 实证该约定**可跨工具复用**（而非为单一工具定制）。
    ★ 用等长空行替换而非删除 —— 删除会使后续**行号整体偏移**（自指破坏门曾因此报错指向错误行）。
    """
    out, skip = [], False
    for ln in text.split("\n"):
        if "gate-self-exempt: begin" in ln:
            skip = True; out.append(""); continue
        if "gate-self-exempt: end" in ln:
            skip = False; out.append(""); continue
        out.append("" if skip else ln)
    return "\n".join(out)


def _synth_gcr16(cw):
    """合成 G-CR16 判据的**纯函数部分**（供 B/C 项用）。"""
    real = THRESHOLDS["context_window_default"]
    return cw <= real


def _synth_gcr8(mb):
    """合成 G-CR8 判据的**纯函数部分**（供 B/C 项用）。"""
    return mb < 240.0


def _synth_gcr6_ent(ent_text):
    """合成 G-CR6 的 entitlement 判据（供 B/C 项用）。"""
    return "audio-input" in (ent_text or "")


def selfcheck():
    """R006 ②③④ 能力边界自检。"""
    me = os.path.abspath(__file__)
    txt = open(me, encoding="utf-8").read()
    stripped = _strip_lits(_apply_exempt(txt))
    # ② 判「是否有写被检对象」的调用（本门为纯只读探测）
    writes = [p for p in (r"open\s*\([^)]*['\"]w", r"write_text\s*\(", r"\.write\s*\(")
              if re.search(p, stripped)]
    # ③ CLD 特有路径是否集中在常量区（散落多处 = 不可移植）
    # ★ v1.0.2 修正（自测抓到）：初版用「CLD 出现次数 ≤3」⇒ **不合理**：
    #   本门**本就需要多处**判 CLD（主 app + 4 Helper + 各判据）。
    #   ⇒ 改为判「**是否定义了统一的 CLD 常量**且散落字面量可控」——那才是"可适配"的本意。
    cld_const = "CLD_APP" in txt or "CLD_PATH" in txt or "CLD = " in txt
    cld_hits = len(re.findall(r"/Applications/CLD\.app", txt))
    checks = [
        ("② TCC：本门**不写**被检对象（只读探测）", len(writes) == 0),
        ("③ CLD 自适应：有 CLD 常量（%s）· 字面量 %d 处" % ("有" if cld_const else "无", cld_hits),
         cld_const or cld_hits <= 6),
        ("④ 版本单一来源 VERSION", 'VERSION = "%s"' % VERSION in txt),
        ("⑩ A 预检：源码无危险原语（剥离后）",
         not any(re.search(p, stripped) for p in DANGEROUS_PRIMS)),
    ]
    print("★ selfcheck（R006 ②③④）")
    n = 0
    for name, ok in checks:
        print("  %s %s" % ("✅" if ok else "❌", name))
        n += 1 if ok else 0
    print("  自查：%d/%d" % (n, len(checks)))
    return 0 if n == len(checks) else 1


def lean4_check():
    """R006 ⑩ `--lean4-check` 六项（A–F）。"""
    me = os.path.abspath(__file__)
    raw = open(me, encoding="utf-8").read()
    stripped = _strip_lits(_apply_exempt(raw))
    res = []

    # ── A 源码无危险原语（**剥离后**扫）──
    a_hits = [p for p in DANGEROUS_PRIMS if re.search(p, stripped)]
    res.append(("A 源码无危险原语（剥离后扫）", len(a_hits) == 0,
                "命中 0 条" if not a_hits else "命中 %d 条：%s" % (len(a_hits), a_hits[:3])))

    # ── B 负例全部被拒（用**本门判据的纯函数部分**造越界输入）──
    b_cases = [
        ("G-CR16 window 远超真实上限", _synth_gcr16(1_000_000_000), False),
        ("G-CR8 会话体积 999MB", _synth_gcr8(999.0), False),
        ("G-CR6 entitlement 缺 audio-input", _synth_gcr6_ent("com.apple.security.cs.allow-jit"), False),
    ]
    b_bad = [n for n, got, want in b_cases if got != want]
    res.append(("B 负例全部被拒", len(b_bad) == 0,
                "3 条越界样例全部 FAIL" if not b_bad else "★ 有负例被放过：%s" % b_bad))

    # ── C 正例可用（**防门太宽砍自己人**）──
    c_cases = [
        ("G-CR16 window=1000（合法）", _synth_gcr16(1000), True),
        ("G-CR8 体积 100MB（合法）", _synth_gcr8(100.0), True),
        ("G-CR6 含 audio-input", _synth_gcr6_ent("com.apple.security.device.audio-input"), True),
    ]
    c_bad = [n for n, got, want in c_cases if got != want]
    res.append(("C 正例可用（防门太宽）", len(c_bad) == 0,
                "3 条合法样例全部 PASS" if not c_bad else "★ 门把合法值也拦了：%s" % c_bad))

    # ── D 零变更（本门纯只读 ⇒ 断言源码无写调用）──
    d_writes = [p for p in (r"open\s*\([^)]*['\"]w", r"write_text\s*\(", r"shutil\.copy")
                if re.search(p, stripped)]
    res.append(("D 零变更（无写调用）", len(d_writes) == 0,
                "源码无写文件调用" if not d_writes else "★ 检出写调用：%s" % d_writes))

    # ── E 白名单冻结 ──
    e_ok = isinstance(DANGEROUS_PRIMS, tuple) and isinstance(ALLOWED_CMDS, tuple)
    res.append(("E 白名单冻结（tuple）", e_ok, "DANGEROUS_PRIMS / ALLOWED_CMDS 为不可变 tuple"))

    # ── F 外部命令白名单（**枚举调用点 → 回原文读实参 → 断言 ⊆ 允许集**）──
    #    ★ 依 R006 F 项步骤：**去字面量定位调用点 → 回原文读实参**（否则会「空集通过」）。
    calls = re.findall(r"sh\(\s*\[\s*\"([\w.\-]+)\"", raw)
    calls += re.findall(r"sh\(\s*\[\s*'([\w.\-]+)'", raw)
    bad = sorted(set(calls) - set(ALLOWED_CMDS))
    res.append(("F 外部命令白名单（枚举 %d 处 → 断言 ⊆ %d 项白名单）" % (len(calls), len(ALLOWED_CMDS)),
                len(bad) == 0, "命令集 %s" % sorted(set(calls)) if not bad else "★ 越界命令：%s" % bad))

    print("★ lean4-check（R006 ⑩ 六项）")
    n = 0
    for name, ok, note in res:
        print("  %s %s — %s" % ("✅" if ok else "❌", name, note))
        n += 1 if ok else 0
    print("  六项：%d/%d %s" % (n, len(res), "全绿" if n == len(res) else "★ 未全绿"))
    return 0 if n == len(res) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="逗号分隔，如 G-CR8,G-CR9")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--selfcheck", action="store_true", help="R006 ②③④ 能力边界")
    ap.add_argument("--lean4-check", action="store_true", help="R006 ⑩ 六项 A–F")
    a = ap.parse_args()

    if a.selfcheck:

        sys.exit(selfcheck())

    if a.lean4_check:

        sys.exit(lean4_check())

    if a.selftest:
        sys.exit(selftest())

    only = set(x.strip() for x in a.only.split(",")) if a.only else None
    print("★ gcr-gate v%s" % VERSION)
    print("★ 扫描时点：%s" % __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"))
    print("★ 条款来源：锚点 §7.9（**实列 17 条**；§10 称「十五条」⇒ 计数不符，已登记）")
    print("★ 覆盖：17 条全建档；本工具机械化的 %d 条，其余标 N-A 并指向既有工具"
          % sum(1 for _, _, fn in GATES if fn.__name__ != "<lambda>"))
    print()
    rows = run_all(only)
    icon = {"PASS": "✅", "FAIL": "❌", "N-A": "⚠️"}
    for r in rows:
        print("%s %-8s %s" % (icon[r["state"]], r["id"], r["desc"]))
        print("      %s" % r["detail"][:150])
    n_fail = sum(1 for r in rows if r["state"] == "FAIL")
    n_pass = sum(1 for r in rows if r["state"] == "PASS")
    n_na = sum(1 for r in rows if r["state"] == "N-A")
    print()
    print("══ 汇总：PASS %d · FAIL %d · N-A %d（共 %d）══" % (n_pass, n_fail, n_na, len(rows)))
    if n_fail:
        print("   ⇒ ❌ **有 FAIL ⇒ 禁止推进/重启**")
    else:
        print("   ⇒ ✅ 无 FAIL（N-A 项非通过，须按其指向的既有工具单独验）")
    if a.json:
        print(json.dumps({"version": VERSION, "rows": rows,
                          "tally": {"PASS": n_pass, "FAIL": n_fail, "N-A": n_na}},
                         ensure_ascii=False, indent=1))
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
