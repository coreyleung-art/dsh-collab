#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-gallery-refresh.py — gallery 快照统一刷新入口 v1.0.0

★★ 为什么需要它（实据 · 2026-10-13 独立考古）：
  `data/blueprint/gallery/` 下 **8 个快照**（knowledge-graph / original-assets /
  workflow-standards / plan-archive / mechanism / hardware-nodes /
  business-asset-map / governance-philosophy）**32–41 天陈旧**，而页面此前**无任何时间戳**。
  ★ 查「是否会自动刷新」的三态结论：
    · 「会」     ⇒ ❌ 无证据
    · 「不会」   ⇒ ★ **launchd 0 引用 · crontab 无匹配 · 脚本层无调用者 · 发布门禁 G1 不刷新**
    · 「不可判」 ⇒ ★ 不能 100% 排除（可能有未搜到的路径）
    ⇐ 搜过的面：launchd 632 条目 / 110 plist / scripts 下 *.sh+*.py / crontab
    ⇐ 正控：`grep 'gallery'` 命中 22 文件 · G1 有 6 处 python3 调用 ⇒ **检索面有效**
  ⇒ ★ 结论：**无自动刷新机制** ⇒ 本件补上【可复跑的刷新入口】。

★ 纪律（★ 本线反复的教训都写进工具）：
  ① ★ **默认 dry-run**（R006 §2⑨ · §6 坑 8：验证会改状态的工具不得用「跑它」当验证）
  ② ★ **三态**：每步如实报 成功 / 失败 / 不可判（★ 不把「没跑」写成「成功」）
  ③ ★ **⑦ 统一日志**（固定路径 · 成败都留痕）
  ④ ★ **⑨ CLI 治理**（退出码 0/1/2 · `--json` · `--help` · `--dry-run`）
  ⑤ ★ 每步**跑完看文件的 mtime 是否真的前进**（★ 「返回 0 ≠ 真写了」—— 本线实测教训）

用法：
    bb-gallery-refresh.py                  # ★ dry-run（默认，零写入）
    bb-gallery-refresh.py --apply          # 真跑全部刷新
    bb-gallery-refresh.py --apply --only plan-archive,mechanism
    bb-gallery-refresh.py --json
    bb-gallery-refresh.py --tool-version
"""
__version__ = "1.0.0"

import argparse, json, os, subprocess, sys, datetime, time

LOG = os.path.expanduser("~/dsh-collab/logs/bb-gallery-refresh.log")
SCRIPTS = os.path.expanduser("~/dsh-collab/scripts")
GALLERY = os.path.expanduser("~/dsh-collab/data/blueprint/gallery")

# ★ 冻结白名单：只允许跑这些（★ 不接任意命令 —— ⑩ 命令白名单）
STEPS = [
    {"id": "plan-archive",    "script": "bb-plan-scanner.py",       "args": ["--scan"],
     "produces": ["plan-archive.json"], "desc": "计划档案扫描"},
    # ★★ 2026-10-13 实测修正：本步是【自检器】—— **rc!=0 表示「发现了问题」**，
    #   而非「工具失败」。⇒ 标 `selfcheck: True`，判据随之改为「有发现 = 成功履行了职责」。
    {"id": "asset-relations", "script": "bb-asset-relations.py",    "args": ["--selfcheck"],
     "produces": [], "selfcheck": True,
     "desc": "资产关系自检（★ 只读 · rc!=0 = 发现问题而非失败）"},
    {"id": "paper-summaries", "script": "gen-paper-summaries.py",   "args": [],
     "produces": ["paper-summaries.json"], "desc": "论文中文概况生成"},
    # ★★ 2026-10-13 实测修正：`--auto` 实际写的是 **`gallery/static-export/` 目录**
    #   （实测「✅ 导出完成 → …/gallery/static-export (6062 KB, 22 API)」），
    #   ★ 不是 gallery/ 根下的那几个 json ⇒ 第一版 produces 声明错 ⇒ 误报「无文件变化」。
    # ★★ 2026-10-14（用户裁决「补生成器，也补元信息」）：
    #   `hardware-nodes.json`（36 天）与 `workflow-standards.json`（35 天）此前
    #   **从未接入任何自动更新路径**（★ 实测：mtime 完美双峰，中间态 0 个）。
    #   ⇒ 用户裁决补生成器 + 补元信息 ⇒ 二者各建一个 core/派生 分工的生成器，并接入本流水线。
    {"id": "hardware-nodes",  "script": "bb-hardware-nodes-gen.py",  "args": ["--go"],
     "produces": ["hardware-nodes.json"], "desc": "硬件节点图（core 人工事实 + 探测可达性）"},
    {"id": "workflow-standards", "script": "bb-workflow-standards-gen.py", "args": ["--go"],
     "produces": ["workflow-standards.json"], "desc": "工作流标准（core 人工摘要 + 校验 tool 存在性）"},
    # ★★★ 2026-10-15（用户裁决「3 个 orphaned 派生图谱写生成器」· 经 J44 建前门【修正为 2 个】）：
    #   ★ `business-asset-map.json` **不建生成器** —— ★ 实测它【已有维护工具】
    #     `bb-asset-relations.py`（`--add`/`--add-asset`/`--del` · 人工逐条确认）
    #     ⇒ ★ 分类改为 curated；★ 它在 refresh 里的那步是【只读 selfcheck】，设计如此。
    #   ★ `knowledge-graph.json` 与 `mechanism.json` ⇒ 图内容是策展的，**而派生字段会自相矛盾**
    #     （★ knowledge 曾自报 89 而实有 92；★ mechanism 的 gate_health 基于 75 而账本已 79）
    #     ⇒ ★ 本步用【实际内容】重算派生字段 + 补元信息（★ 不增删任何策展内容）。
    {"id": "derived-graphs",  "script": "bb-derived-graphs-gen.py",  "args": ["--go"],
     "produces": ["knowledge-graph.json", "mechanism.json"],
     "desc": "派生图谱派生字段重算（★ 只动派生计数与元信息）"},
    # ★★★ 2026-10-14/15（用户批准的计划 C1）：
    #   今晚实测一起 **11 天**的故障：中央 comm-server 因 cgroup OOM 重启 **2041 次**，
    #   ★★★ 而 `systemctl is-active` 全程返回 **active** —— **每 27 秒重启一次的服务，它判健康。**
    #   ⇒ 本步把判据换成【**重启计数增量**】：★ 健康不是「活不活」，是「有没有在重启」。
    #   ★ 三态：0 健康 · 1 退化（发现增量）· 2 不可判（★ 不把「读不到」读成「健康」）
    # ★★★ 2026-10-15（D1 · 面2 蓝图管理 · 用户「回到我们目标来」后做的第一个工作面项）：
    #   `data/blueprint/versionlog` 的**流程层**此前【停写】（★ stage-review §6 记「自 2026-09-07 停写」）。
    #   ★ 实测真因不是「工具坏了」，而是：**没有任何东西【自动调它】** ——
    #     `bb-blueprint-version.py` 功能齐全（bump/history/diff/snapshot/log/sync-from-artifacts/stale-report）
    #     但全是【人工触发】⇒ ★ **漂移发现了也没人看**。
    #   ★★ 本步把【检测】接上（★ 决定仍留给人 —— 版本号是治理决定）：
    #     · rc=0 ⇒ 无【未处理】漂移（★ 已登记待人工确认的**不算** —— 那待的是裁决，不是发现）
    #     · rc=1 ⇒ **发现未处理漂移**（★ 履行职责，非工具失败）
    #   ★★★ 两条诊断（stale-report vs sync-from-artifacts）此前【对同一对象结论相反】——
    #     已修：给 stale-report 加幂等过滤（★ 见该文件注释）。
    {"id": "blueprint-version", "script": "bb-blueprint-version.py", "args": ["--stale-report"],
     "produces": [], "selfcheck": True,
     "desc": "蓝图版本台账对账（★ 只读 · rc=1 = 发现未处理漂移）"},
    {"id": "central-health",  "script": "bb-central-health.py",     "args": ["--json"],
     "produces": [], "selfcheck": True,
     "desc": "中枢黑板健康（★ NRestarts 增量判据；rc=1 退化 · rc=2 不可判）"},
    {"id": "export",          "script": "bb-gallery-export.py",     "args": ["--auto"],
     "produces": ["static-export"], "desc": "gallery 静态导出（★ 产物在 static-export/ 目录）"},
    # ★★★ 2026-10-15（用户裁决 «A：每日自动发布»）：
    #   ★ 实测证明 B（只加 verify）**会变成每日常驻告警** —— 因为每日 refresh 都重生数据
    #     ⇒ 导出必然更新 ⇒ 每天都会报「线上滞后」⇒ ★ 按「每次必红 ≠ 这次变红」那条，
    #     常驻告警会被忽略 ⇒ 故裁决 A：**让 refresh 的终点【一致】**。
    #   ★★ 但【前置条件不得跳过】（计划 A3）：「自动发布会把不完整的中间态推上生产」
    #     ⇒ 本步用 `bb-publish-apply.py`，它把「不比对不发布」做成【结构】：
    #       ① **前验**：manifest 声明的哈希/字节 vs 实物 ⇒ ★ 不符即【拒绝发布】
    #       ② **发布**：`systemgraph-publish.sh --go`（★ 自带上传→服务端逐文件比对→原子切换→失败回滚）
    #       ③ **后验**：`bb-publish-verify.py` ⇒ ★ **只有一致才认「发布成功」**
    #   ★★★ 故本步位置在 export **之后**（★ 发布刚导出的那份）。
    {"id": "publish-apply",   "script": "bb-publish-apply.py",      "args": ["--go"],
     "produces": [], "selfcheck": True,
     "desc": "受门约束的自动发布（★ 前验→发布→后验；rc=2 不可判）"},
]
ALLOWED = frozenset(s["script"] for s in STEPS)   # ★ 命令白名单（冻结）


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


def _mtime(p):
    """★ 2026-10-13 修（实测触发）：**路径是目录时，取目录内【最新文件】的 mtime**。

    ★★ 起因：`export` 步的产物是 `static-export/` **目录**，而实测它
      **「目录 mtime 不变（Sep 28）但 124 个文件今天被更新」** ——
      因为写的是**同名文件覆盖**，不新增目录项 ⇒ Linux/macOS 的**目录 mtime 不会变**。
      ⇒ ★ 第一版查目录 mtime ⇒ **误报「无文件变化」**。
    ★ **这是「判据选错」的又一实例**：目录 mtime 是**间接/过程态**指标，
      目录内文件 mtime 才是**结果态**（★ 与本线「判据要选结果态而非过程态」同族）。
    """
    try:
        fp = os.path.expanduser(p)
        if os.path.isdir(fp):
            newest = None
            for root, _dirs, files in os.walk(fp):
                for f in files:
                    try:
                        t = os.path.getmtime(os.path.join(root, f))
                        if newest is None or t > newest:
                            newest = t
                    except Exception:
                        pass
            if newest is None:
                return None
            return datetime.datetime.fromtimestamp(newest).strftime("%Y-%m-%d %H:%M:%S") + " (目录内最新)"
        return datetime.datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def run_step(step, dry):
    """★ 三态返回：ok=True/False · skipped=dry-run · ★ 并以【mtime 是否前进】为准判「真写了」。"""
    script = step["script"]
    # ★ ⑩ 命令白名单（★ 只允许 STEPS 里声明的脚本）
    if script not in ALLOWED:
        return {"id": step["id"], "ok": False, "verdict": "★ 拒绝：脚本不在白名单", "mtimeAdv": None}
    path = os.path.join(SCRIPTS, script)
    if not os.path.isfile(path):
        # ★ 坑 #5：区分【环境问题】与【脚本问题】
        return {"id": step["id"], "ok": False, "verdict": "★ 不可判：脚本不存在（环境问题）", "mtimeAdv": None}
    before = {f: _mtime(os.path.join(GALLERY, f)) for f in step["produces"]}
    if dry:
        return {"id": step["id"], "ok": True, "skipped": True,
                "wouldRun": "python3 %s %s" % (script, " ".join(step["args"])),
                "beforeMtime": before, "verdict": "★ dry-run（未执行）", "mtimeAdv": None}
    t0 = time.time()
    try:
        r = subprocess.run(["python3", path] + step["args"], capture_output=True,
                           text=True, timeout=600, cwd=SCRIPTS)
        rc, out, err = r.returncode, (r.stdout or ""), (r.stderr or "")
    except subprocess.TimeoutExpired:
        rc, out, err = -1, "", "★ 超时 600s（环境问题）"
    except Exception as e:
        rc, out, err = -1, "", "%s: %s" % (type(e).__name__, e)
    after = {f: _mtime(os.path.join(GALLERY, f)) for f in step["produces"]}
    adv = {f: (before.get(f) != after.get(f)) for f in step["produces"]}
    # ★★ 判据选【结果态】：rc==0 但 mtime 没动 ⇒ 如实说「跑了但没写」
    if step.get("selfcheck"):
        # ★ 自检器：rc==0 = 全过；rc!=0 = **发现了问题**（★ 那是它履行职责，不是失败）
        verdict = ("✓ 自检全过" if rc == 0 else "⚠️ 自检【发现问题】（rc=%s）—— ★ 这是它的职责，非工具失败" % rc)
        return {"id": step["id"], "ok": True, "rc": rc, "selfcheck": True, "seconds": round(time.time()-t0,1),
                "verdict": verdict, "stdoutTail": out.strip()[-400:], "stderrTail": err.strip()[-200:]}
    if rc != 0:
        verdict = "★ 失败（rc=%s）" % rc
    elif any(adv.values()):
        verdict = "✓ 完成（mtime 前进: %s）" % ",".join(f for f, v in adv.items() if v)
    else:
        verdict = "★ 跑了但【无文件变化】（可能本就无需更新，也可能没生效 —— 不假装成功）"
    return {"id": step["id"], "ok": rc == 0, "rc": rc, "seconds": round(time.time() - t0, 1),
            "beforeMtime": before, "afterMtime": after, "mtimeAdvanced": adv,
            "verdict": verdict, "stdoutTail": out.strip()[-300:], "stderrTail": err.strip()[-200:]}


def main():
    ap = argparse.ArgumentParser(description="gallery 快照统一刷新入口（★ 默认 dry-run）")
    ap.add_argument("--apply", action="store_true", help="★ 真跑（缺省=dry-run 零写入）")
    ap.add_argument("--only", default="", help="只跑指定步骤（逗号分隔 id）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    a = ap.parse_args()
    if a.tool_version:
        print(__version__); return 0

    sel = [s for s in STEPS if (not a.only) or (s["id"] in [x.strip() for x in a.only.split(",")])]
    results = [run_step(s, dry=not a.apply) for s in sel]
    out = {"tool": "bb-gallery-refresh", "version": __version__, "dryRun": not a.apply,
           "at": datetime.datetime.now().isoformat(), "steps": results,
           "ran": sum(1 for r in results if not r.get("skipped")),
           "ok": sum(1 for r in results if r.get("ok") and not r.get("skipped")),
           "failed": sum(1 for r in results if not r.get("ok"))}
    log("run dry=%s ran=%d ok=%d failed=%d" % (out["dryRun"], out["ran"], out["ok"], out["failed"]))
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print("══ gallery 快照刷新 v%s ══ [%s]" % (__version__, "真跑" if a.apply else "★ dry-run"))
        for s in STEPS:
            if s not in sel:
                continue
            r = next(x for x in results if x["id"] == s["id"])
            print("  %-16s %s" % (s["id"], r["verdict"]))
            if r.get("wouldRun"):
                print("       将执行: %s" % r["wouldRun"])
            if r.get("mtimeAdvanced"):
                for f, v in r["mtimeAdvanced"].items():
                    print("       %s mtime: %s → %s" % (f, r["beforeMtime"][f], r["afterMtime"][f]))
        print("\n  ⇒ 跑 %d · 成功 %d · 失败 %d" % (out["ran"], out["ok"], out["failed"]))
        if not a.apply:
            print("  ★ dry-run：零写入。真跑请加 --apply")
    return 0 if out["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
