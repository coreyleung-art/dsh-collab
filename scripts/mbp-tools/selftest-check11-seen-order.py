#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第⑪项判据（投递去重键后置）的正负样本自证 —— R31/R41 纪律：
新判据必须用**已知坏样本**验（否则"永远判通过"也能自称有效）。

样本：
  N1 真实坏代码形态（seen 在 target 守卫之前）      → 期望 False + 报「早于」
  N2 真实好代码形态（seen 在 send 之后、try 内）    → 期望 True
  N3 本机线上插件（已修）                            → 期望 True
  N4 无去重机制                                      → 期望 None（不适用）
  N5 形态已变（有 _seen 但无 target 守卫）           → 期望 False（fail-closed，不许默认通过）
"""
import os, sys, tempfile, shutil
from importlib.machinery import SourceFileLoader

RA = os.path.expanduser("~/dsh-collab/tools/restart-audit.py")
mod = SourceFileLoader("ra", RA).load_module()
chk = mod.check_seen_after_inject

BAD = """  function handleEvent(d) {
    const _verdict = _should(d, {});
    if (!_verdict.inject) return;
    _remember(_seen, _verdict.dedupKey);
    _seenDirty = true;
    const value = _verdict.value;
    const { target, mode, reason } = resolveTargetId(value.to, centralAgent);
    if (!target) {
      logLine('注入目标为 null，跳过');
      return;
    }
    try {
      const r = agentBus.send(from, target, text, undefined, {});
      logLine('注入 ' + key);
    } catch (e) { logLine('注入失败'); }
  }
"""

GOOD = """  function handleEvent(d) {
    const _verdict = _should(d, {});
    if (!_verdict.inject) return;
    const value = _verdict.value;
    const { target, mode, reason } = resolveTargetId(value.to, centralAgent);
    if (!target) {
      logLine('注入目标为 null，跳过');
      return;
    }
    try {
      const r = agentBus.send(from, target, text, undefined, {});
      _remember(_seen, _verdict.dedupKey);
      _seenDirty = true;
      logLine('注入 ' + key);
    } catch (e) { logLine('注入失败'); }
  }
"""

NODEDUP = "const x = 1;\nfunction f(){ return 2; }\n"

WEIRD = "const _seen = new Set();\n_remember(_seen, 'k');\n"   # 有 seen、无 target 守卫

# ★ N6：首跑真实假阳性形态（agent-way）—— 有同名 `dedupKey()` 函数 + 别处 `if (!target || …)`，
#   但**没有** `_remember(_seen` ⇒ 不属本判据管辖，必须回 None（否则整机被误判「不建议重启」）
AGENTWAY_LIKE = """  function dedupKey(from, threadId, text) { return from + threadId + text; }
  const _sharedDedupKey = dedupKey;
  function followup(target, msg) {
    if (!target || typeof target.followup !== 'function') return false;
    return target.followup(msg);
  }
"""

# ★ N7：合法形态 B —— 「有意丢弃分支」（先写 seen、**立刻 return**）+ 成功路径 seen 在 send 后。
#   这正是 2026-10-04 我加的「超龄卡丢弃」分支；首版判据用 min(seen)>guard 一刀切，把它误判了。
DROP_OK = """  function handleEvent(d) {
    const _verdict = _should(d, {});
    if (!_verdict.inject) return;
    const value = _verdict.value;
    if (isStaleCard(value, Date.now(), 24, d).stale) {
      _remember(_seen, _verdict.dedupKey);
      _seenDirty = true;
      return;
    }
    const { target, mode } = resolveTargetId(value.to, centralAgent);
    if (!target) { logLine('null'); return; }
    try {
      const r = agentBus.send(from, target, text, undefined, {});
      _remember(_seen, _verdict.dedupKey);
      _seenDirty = true;
      logLine('注入 ' + key);
    } catch (e) { logLine('失败'); }
  }
"""

# ★ N8：缺陷变体 —— send 之前写 seen **且不 return**（会继续走到注入）⇒ 必须判失败
ORPHAN_SEEN = """  function handleEvent(d) {
    const _verdict = _should(d, {});
    if (!_verdict.inject) return;
    _remember(_seen, _verdict.dedupKey);
    const value = _verdict.value;
    const { target, mode } = resolveTargetId(value.to, centralAgent);
    if (!target) { logLine('null'); return; }
    try {
      const r = agentBus.send(from, target, text, undefined, {});
      logLine('注入 ' + key);
    } catch (e) { logLine('失败'); }
  }
"""

tmp = tempfile.mkdtemp(prefix="chk11-")


def mk(name, body):
    d = os.path.join(tmp, name)
    os.makedirs(os.path.join(d, "lib"))
    open(os.path.join(d, "lib", "index.js"), "w", encoding="utf-8").write(body)
    return d


cases = [
    ("N1 真实坏形态（seen 早于守卫）", mk("n1", BAD), "dsh-plugin-central-inbox", False),
    ("N2 真实好形态（seen 在 send 后）", mk("n2", GOOD), "dsh-plugin-central-inbox", True),
    ("N3 本机线上插件（已修）", os.path.expanduser("~/.dsh/profiles/web/node_modules/dsh-plugin-central-inbox"),
     "dsh-plugin-central-inbox", True),
    ("N4 无去重机制", mk("n4", NODEDUP), "dsh-plugin-x", None),
    ("N5 形态已变（无守卫）⇒ fail-closed", mk("n5", WEIRD), "dsh-plugin-central-inbox", False),
    ("★N6 首跑假阳性形态（agent-way 同名 dedupKey）", mk("n6", AGENTWAY_LIKE), "dsh-plugin-agent-way", None),
    ("★N7 合法形态B（有意丢弃：seen+return）", mk("n7", DROP_OK), "dsh-plugin-central-inbox", True),
    ("★N8 缺陷变体（send 前写 seen 且不 return）", mk("n8", ORPHAN_SEEN), "dsh-plugin-central-inbox", False),
]

ok = True
print("第⑪项判据 · 正负样本自证")
for name, d, pkgname, want in cases:
    got, msg = chk(d, pkgname)
    good = (got is want) if want is None else (got == want)
    ok = ok and good
    print("  %s %-42s 期望=%-5s 实际=%-5s | %s"
          % ("✅" if good else "❌", name, str(want), str(got), str(msg)[:80]))
shutil.rmtree(tmp, ignore_errors=True)
print()
print("  ⇒ %s" % ("全部通过" if ok else "存在失败项"))
sys.exit(0 if ok else 1)
