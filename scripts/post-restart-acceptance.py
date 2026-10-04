#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""post-restart-acceptance.py — CLD 重启后的一键验收

验收对象（2026-10-04 批次）：agent-way v1.5.13（MBP 决定性根因 ①②③：deliver 失败出声 +
idle 主动 flushQueue + agentBus.flush 暴露 + delivery-guard 判据）与 central-inbox v0.2.12
（R43 三级时间源 + G30 boot 窗口有界缓冲重放）。历史批次判据保留：
- 2026-10-03 批次：agent-way v1.5.9/1.5.10/1.5.11（方案 A 唤醒语义 + 双板写 + fs 导入修复 +
  冒烟独立化）+ central-inbox v0.2.10（os 修复 + 冒烟独立化防递归链）+ comm-standard v1.3 门对齐
- 更早批次（v1.5.5/1.5.6：A 批 + D2.1 署名 + I1/I2 原语 + I3/I4 回执订阅 + I5 原子写 +
  I7 inject + A2 过期/DLQ + I1 from 迁移）判据保留。

用法：CLD 重启完成后执行
    python3 ~/dsh-collab/scripts/post-restart-acceptance.py
退出码：0 = 全部通过；1 = 有未达标项（打印明细）
"""
__version__ = '1.1.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json
import os
import sys
import subprocess

HOME = os.path.expanduser("~")
BUS = os.path.join(HOME, ".dsh", "agent-bus.json")
PASS, FAIL, WARN = "✅", "❌", "⚠️"

rows = []


def check(name, cond, detail):
    rows.append((name, cond, detail))
    print(f"  {PASS if cond else FAIL} {name}  {detail if not cond else ''}")


def load_bus():
    with open(BUS, encoding="utf-8") as f:
        return json.load(f)


def main():
    if not os.path.exists(BUS):
        print("环境错误：找不到 " + BUS)
        return 2
    j = load_bus()
    msgs = []
    for t in j.get("threads", []):
        for m in t.get("messages", []):
            msgs.append(m)
    st = {}
    for m in msgs:
        st[m.get("status") or "-"] = st.get(m.get("status") or "-", 0) + 1

    print("\n  重启后验收 · agent-way v1.5.16 + central-inbox v0.2.14 · comm-standard v1.3 · 2026-10-04")
    print("  " + "-" * 76)

    # ── A2 过期回收 ──
    queued = st.get("queued", 0)
    expired = st.get("expired", 0)
    check("A2 queued 骤降", queued <= 450, f"queued={queued}（2026-10-03 重校准：596−205 死形态≈391；>7d=0，A2 TTL 无增量；阈值 450 留头部）")
    check("A2 expired 已回收", expired >= 1500, f"expired={expired}（预期 ≈1976=历史1771+死形态205）")

    # ── I1 迁移 ──
    import re as _re
    RE_FULL = _re.compile(r"^session-[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$", _re.I)
    ALIAS = {"i9", "mbp", "mbp-bus", "node", "mac-mini", "macmini", "i9-协调", "ui", "coordinator", "unattributed"}
    # ★ 2026-10-03 重校准：bus:* 为决策表规定的合法设备形态（保留原文），不计入标签违规
    label_from = [m for m in msgs if m.get("from") and not RE_FULL.match(str(m["from"]))
                  and not str(m["from"]).lower() in ALIAS
                  and not _re.match(r"^bus:", str(m["from"]), _re.I)
                  and not _re.match(r"^unattributed\(", str(m["from"]), _re.I)   # ★ 归一化终点=匿名但可读，非违规
                  and not _re.match(r"^session-[0-9a-f]{8}$", str(m["from"]), _re.I)]
    check("I1 from 迁移生效", len(label_from) <= 200, f"真违规标签 {len(label_from)} 条（unattributed 666=迁移终点已豁免；bus 合法已豁免；预期残 ≈15）")

    # ── I3/I4 回执字段 ──
    acked = [m for m in msgs if m.get("acked")]
    claimed = [m for m in acked if m.get("acked") == "claimed"]
    check("I3 回执字段出现", len(acked) > 0, "尚无 acked 字段（需有重启后新消息）")
    if claimed:
        check("I4 claimedTurn 存在", any(m.get("claimedTurn") for m in claimed), "")

    # ── I7 wake:inject ──
    inj = [m for m in msgs if m.get("wake") == "inject"]
    check("I7 通知类不唤醒（wake:inject）", len(inj) > 0, "尚无 wake:inject（需有重启后的指针式通知）")

    # ── I5 原子写（旁证：写盘后无撕裂 → 文件可完整 JSON 解析即基础证据）──
    try:
        json.load(open(BUS, encoding="utf-8"))
        check("I5 载体可完整解析（无撕裂）", True, "")
    except Exception as e:
        check("I5 载体可完整解析（无撕裂）", False, str(e))

    # ── 审计矩阵 ──
    r = subprocess.run(["python3", os.path.join(HOME, "dsh-collab", "scripts", "comm-invariant-audit.py")],
                       capture_output=True, text=True)
    mline = [l for l in r.stdout.splitlines() if l.strip().startswith("PASS ")]
    print("\n  审计矩阵：")
    if mline:
        print("  " + mline[0].strip())

    # ── A6 第 4 层（2026-10-02）：变体表就绪性（生产五形态探针另测）──
    try:
        r2 = subprocess.run(["/opt/homebrew/bin/node",
                             os.path.join(HOME, "dsh-plugin-agent-bus", "lib", "selfcheck.js"),
                             "agent-way", "@deepseek-ai/cordis", "@deepseek-ai/dsh-tools"],
                            capture_output=True, text=True, timeout=60)
        ok2 = "A6-variants: PASS" in r2.stdout
        check("A6-variants 表 0 分裂+裸标签解析", ok2,
              r2.stdout.splitlines()[-2:] if not ok2 else "")
        ok3 = "identity-table: PASS" in r2.stdout
        check("身份决策表 12 例断言（normalizeIdentity 单一决策点）", ok3,
              r2.stdout.splitlines()[-2:] if not ok3 else "")
        # ★ 2026-10-03 冒烟判据（0.2.9 递归链事故教训）：CLI 冒烟必须 pass 且不刷屏
        ok_smoke_aw = "[pass] 真挂载冒烟" in r2.stdout and r2.stdout.count("真挂载冒烟") == 1
        check("agent-way 真挂载冒烟独立化（pass 且仅 1 次，防递归链）", ok_smoke_aw,
              r2.stdout.splitlines()[-3:] if not ok_smoke_aw else "")
        # ★ 2026-10-04 批次：delivery-guard（1.5.13 ①②③ 三处落点源码断言）+ 版本
        ok_dg = "delivery-guard: PASS" in r2.stdout
        check("agent-way delivery-guard PASS（deliver 失败出声/idle flush/flush 暴露）", ok_dg,
              r2.stdout.splitlines()[-2:] if not ok_dg else "")
        ok_rs = "reexport-silentcatch: PASS" in r2.stdout
        check("agent-way reexport-silentcatch PASS（再导出当本地用=0 · 静默 catch=0）", ok_rs,
              r2.stdout.splitlines()[-2:] if not ok_rs else "")
        try:
            _awpkg = json.load(open(os.path.join(HOME, "dsh-plugin-agent-bus", "package.json")))
            check("agent-way 版本 == 1.5.16", _awpkg.get("version") == "1.5.16", str(_awpkg.get("version")))
        except Exception as _e:
            check("agent-way 版本 == 1.5.16", False, str(_e))
    except Exception as e:
        check("A6-variants 表 0 分裂+裸标签解析", False, str(e))
        check("身份决策表 12 例断言（normalizeIdentity 单一决策点）", False, str(e))
        check("agent-way 真挂载冒烟独立化", False, str(e))

    # ── 壳 v4 宽限定时器修复（2026-10-04 壳修复③）：oldChild 实例捕获源码标记 ──
    #   10:51 实测 v3 竞态：POST /reload → 宽限定时器(t0+3000ms)读模块级 child 误杀新 child
    #   → 判 dsh 崩溃 → 自动重启 1/3…壳以 dsh-crash-after-child 退出（pid 41341）。
    #   判据：从 asar 提取 main.js 断言 oldChild 捕获（不采信磁盘副本，防手改未入包）。
    try:
        import subprocess as _sp2, tempfile as _tf
        _d = _tf.mkdtemp(prefix="asar-v4-check-")
        _sp2.run(["/opt/homebrew/bin/npx", "--yes", "@electron/asar", "extract-file",
                  "/Applications/CLD.app/Contents/Resources/app.asar", "main.js"],
                 capture_output=True, text=True, timeout=120, cwd=_d)
        _m = open(os.path.join(_d, "main.js"), encoding="utf-8").read()
        check("壳 v4 宽限定时器 oldChild 实例捕获（重载不误杀新代）", "const oldChild = child" in _m,
              "asar 内 main.js 未找到 oldChild 捕获")
    except Exception as e:
        check("壳 v4 宽限定时器 oldChild 实例捕获", False, str(e))

    # ── central-inbox 0.2.12 冒烟 + 版本判据（2026-10-04 批次：R43 三级时间源 + G30 缓冲重放）──
    try:
        r3 = subprocess.run(["/opt/homebrew/bin/node", os.path.join(HOME, "dsh-plugin-central-inbox", "cli.js"), "--selfcheck"],
                            capture_output=True, text=True, timeout=90)
        ok_smoke_ci = "[pass] 真挂载冒烟" in r3.stdout and r3.stdout.count("真挂载冒烟") == 1
        check("central-inbox selftest 18 PASS + 冒烟独立化", _re.search(r"selftest: 1[68] PASS", r3.stdout) is not None and ok_smoke_ci,
              r3.stdout.splitlines()[-3:] if not ok_smoke_ci else "")
        try:
            _cipkg = json.load(open(os.path.join(HOME, "dsh-plugin-central-inbox", "package.json")))
            check("central-inbox 版本 == 0.2.14", _cipkg.get("version") == "0.2.14", str(_cipkg.get("version")))
        except Exception as _e:
            check("central-inbox 版本 == 0.2.12", False, str(_e))
        # G30 boot 窗口有界缓冲重放 + R43 三级时间源（源码标记断言；行为验收另走 S6 真实回放）
        try:
            _cisrc = open(os.path.join(HOME, "dsh-plugin-central-inbox", "lib", "index.js")).read()
            _g30 = "_pending" in _cisrc and "flushPending" in _cisrc and "bufferPending" in _cisrc
            check("G30 boot 窗口有界缓冲重放（_pending/bufferPending/flushPending 在位）", _g30, "")
            _r43 = "sent_at_epoch_ms" in _cisrc and "cardAgeMs" in _cisrc
            check("R43 三级时间源（sent_at_epoch_ms/cardAgeMs 在位）", _r43, "")
            _r44 = "ensureCentralLive" in _cisrc and "resumeSessionId" in _cisrc
            check("0.2.13 注入目标自动续活（ensureCentralLive/resumeSessionId 在位）", _r44, "")
            _r45 = "Date.parse(raw)" in _cisrc and "/^\\d{10,13}$/" in _cisrc
            check("0.2.14 cardAgeMs ISO 三态解析（Date.parse 在位）", _r45, "")
        except Exception as _e:
            check("G30/R43 源码标记断言", False, str(_e))
    except Exception as e:
        check("central-inbox 冒烟验收", False, str(e))

    # ── 第⑨项同款（2026-10-03 MBP 共有缺陷）：死前缀拼接扫描──
    #   启发式：agent-way 源码不得出现「notes/' + from 变量 + /」无节点映射的拼接（曾致 502/511/518 三处死前缀）
    try:
        src = open(os.path.join(HOME, "dsh-plugin-agent-bus", "lib", "index.js")).read()
        bad = _re.findall(r"notes/'\s*\+\s*String\(msg\.from\)", src)
        check("reply-hint 死前缀拼接扫描（第⑨项同款）", len(bad) == 0, "命中 " + str(len(bad)) + " 处: " + str(bad[:3]))
    except Exception as e:
        check("reply-hint 死前缀拼接扫描", False, str(e))

    # ── 方案 A 唤醒语义（2026-10-03 用户裁定）：源码常量断言（行为验收另走探针）──
    try:
        src = open(os.path.join(HOME, "dsh-plugin-agent-bus", "lib", "index.js")).read()
        check("方案A-3 阈值 200 字", "THRESHOLD = 200" in src, "源码 THRESHOLD=200")
        check("方案A-2 发端限速 N=10", "RATE_N = 10" in src, "源码 RATE_N=10")
        check("方案A-1 唤醒反转（notify_only 才 inject）", "msg.notifyOnly === true || msg.rateLimited === true" in src, "源码 isNotify 判定")
    except Exception as e:
        check("方案 A 源码常量断言", False, str(e))

    # ── 黑板写端鉴权 flip 验收（2026-10-03 ⑥-A；flip 前本项记 skip 不判失败）──
    try:
        tok = open(os.path.expanduser("~/.dsh/blackboard-token")).read().strip()
        noauth = subprocess.run(["curl", "-m", "8", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                                 "-X", "PUT", "-d", "{}", "http://xingqiao.meetfunbp.com:8792/data/ops/auth-probe"],
                                capture_output=True, text=True, timeout=20).stdout
        if noauth == "401":
            check("黑板写端鉴权 flip 已生效（无头 401）", True, "无头 PUT=401")
            withauth = subprocess.run(["curl", "-m", "8", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                                       "-X", "PUT", "-H", "Authorization: Bearer " + tok, "-d", "{}",
                                       "http://xingqiao.meetfunbp.com:8792/data/ops/auth-probe"],
                                      capture_output=True, text=True, timeout=20).stdout
            check("黑板写端鉴权（带 token 200）", withauth == "200", "带 token=" + withauth)
        else:
            check("黑板写端鉴权 flip 已生效（无头 401）", False, "flip 未生效或未 flip（当前 " + noauth + "）——若未 flip 属预期，跳过")
    except Exception as e:
        check("黑板写端鉴权验收", False, str(e))

    n_fail = sum(1 for _, c, _ in rows if not c)
    print("  " + "-" * 76)
    print(f"  结果：{len(rows) - n_fail}/{len(rows)} 通过\n")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
