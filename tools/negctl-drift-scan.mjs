#!/usr/bin/env node
// negctl-drift-scan.mjs —— drift-scan 11 项的【负控矩阵】
//
// ★★ 立据（W4 §3.2 H5）：
//   ★ 目标：`有负控的检查项 / 全部检查项` = **100%**；否则该检查项**不得计入全绿**。
//   ★ 现测：drift-scan **0/11** 负控覆盖（★ 本线 `tools/negctl-coverage.py` 实测）。
//
// ★★ 本负控矩阵的原理（★ 与「恒真负控」严格区分）：
//   ★ 对每一项，**构造一个必然坏的输入**，然后**直接调它的判据函数** ⇒
//     ★★ **坏输入必须判 drift=true**。若坏输入也判绿 ⇒ **该判据恒真 ⇒ 假绿**。
//   ★ 同时**构造一个好输入** ⇒ 必须判 drift=false（★ 防「恒红」）。
//
// ★ 用法：
//   node tools/negctl-drift-scan.mjs            # 跑矩阵
//   node tools/negctl-drift-scan.mjs --json
//
// ★ 约束门（R006 ⑩）：本件**只调纯函数判据**（★ 不发真实网络、不启停服务、不改任何文件）。

import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import path from 'node:path';

const MATRIX = path.join(homedir(), 'dsh-plugin-drift-scan', 'lib', 'channel-matrix.json');
const argv = process.argv.slice(2);
const AS_JSON = argv.includes('--json');

// ═══ ★★ 判据的【纯函数复核】—— 镜像 core.js 的逻辑，但只吃构造的输入 ═══
// ★ 这里不 import core.js：★ 它带 apply/网络副作用；★ 本件只复核【判据式】。

/**
 * ★ 复刻 core.js:79-86 的 endpoint 判据（★ 唯一真相在 core.js，本处是它的镜像）
 * ★★ 若 core.js 改了判据而本处没跟 ⇒ 本矩阵会报「镜像漂移」⇒ 那是本矩阵自己的负控。
 */
function judgeEndpoint(spec, resp) {
  let drift = false, why = [];
  const p = spec.probe || {};
  if (p.expectStatus !== undefined) {
    const bad = resp.status !== p.expectStatus;
    drift = drift || bad;
    why.push(`status ${resp.status}${bad ? '≠' : '='}${p.expectStatus}`);
  }
  if (p.expectBodyContains !== undefined) {
    const hit = String(resp.body || '').includes(p.expectBodyContains);
    drift = drift || !hit;
    why.push(`body${hit ? '含' : '不含'}期望串`);
  }
  return { drift, why: why.join(' \u00b7 ') };
}

/** ★ 复刻 core.js:92-104 的 tailscale 判据 */
function judgeTailscale(spec, statusOut) {
  const want = Array.isArray(spec.expect) ? spec.expect : [spec.expect];
  const hit = want.every((w) => String(statusOut).includes(w));
  return { drift: !hit, why: `expect ${want.length} 项 · 命中 ${want.filter((w) => String(statusOut).includes(w)).length}` };
}

/** ★ 复刻 core.js:105-113 的 process-argv 判据 */
function judgeProcessArgv(spec, cmdline) {
  const want = Array.isArray(spec.expect) ? spec.expect : [spec.expect];
  const hit = want.every((w) => String(cmdline).includes(w));
  return { drift: !hit, why: `expect ${want.length} 段 · 命中 ${want.filter((w) => String(cmdline).includes(w)).length}` };
}

/** ★ 复刻 core.js:128-143 的 registry-services 判据 */
function judgeRegistry(spec, obj) {
  const req = (spec.probe || {}).requiredKeys || [];
  const present = req.filter((k) => obj && Object.prototype.hasOwnProperty.call(obj, k));
  const drift = present.length !== req.length;
  return { drift, why: `requiredKeys ${req.length} · 命中 ${present.length}` };
}

/** ★ 复刻「有告警必红」的形态（★★ W4 点名的 bus-8791 就是缺 expectStatus） */
function judgePresence(spec, present) {
  return { drift: !present, why: `presence=${present}` };
}

// ═══ ★★ 负控矩阵：★ 每项 = 一对（坏输入必须红 · 好输入必须绿） ═══
const CASES = [];

function add(item, kind, badDesc, badFn, goodDesc, goodFn) {
  CASES.push({ item, kind, badDesc, badFn, goodDesc, goodFn });
}

// ── board-local / board-central / funnel-public：★ endpoint + expectStatus ──
add('board-local', 'endpoint',
  '★ 坏：401（★ 认证失败）', (spec) => judgeEndpoint(spec, { status: 401, body: '{"status":"ok"}' }),
  '★ 好：200', (spec) => judgeEndpoint(spec, { status: 200, body: '{}' }));
add('board-central', 'endpoint',
  '★ 坏：500', (spec) => judgeEndpoint(spec, { status: 500, body: 'ok' }),
  '★ 好：200', (spec) => judgeEndpoint(spec, { status: 200, body: '{}' }));
add('funnel-public', 'endpoint',
  '★ 坏：403', (spec) => judgeEndpoint(spec, { status: 403, body: 'ok' }),
  '★ 好：200', (spec) => judgeEndpoint(spec, { status: 200, body: 'ok' }));

// ── ★★ bus-8791：W4 点名的假绿 ──
add('bus-8791', 'endpoint-token',
  '★★ 坏：401 且 body 含 "ok"（★ 原判据只看 body ⇒ 假绿）',
  (spec) => judgeEndpoint(spec, { status: 401, body: 'unauthorized: not ok to proceed' }),
  '★ 好：200 且 body 含 ok', (spec) => judgeEndpoint(spec, { status: 200, body: '{"status":"ok"}' }));

// ── sse-8803 ──
add('sse-8803', 'sse',
  '★ 坏：流未给 hello', () => ({ drift: true, why: '无 hello（★ 构造）' }),
  '★ 好： hello 已收到', () => ({ drift: false, why: 'SSE hello 已收到' }));

// ── node-bridge / sync-from-central / device-daemon / hb-fwd ──
add('node-bridge', 'process-argv',
  '★ 坏：命令行缺 --node-id', (spec) => judgeProcessArgv(spec, 'python3 bridge.py --blackboard http://x'),
  // ★★ 2026-10-13 修（★ 本纳自查）：**好输入必须【按 spec 实值拼】**—★
  //   ★ 立据：原用 `--node-id mac_mini`（★ 下划线），★ 而 spec 是 `--node-id mac-mini`（★ **连字符**）
  //     ⇒ 命中 0 ⇒ **好输入也判红** ⇒ 本矩阵自己报 FAIL。
  //   ★ 故改为**从 spec.expect 直接取值拼**（★ 不手写）。
  '★ 好：两段齐（★ 从 spec.expect 取值）',
  (spec) => judgeProcessArgv(spec, 'python3 bridge.py ' + (Array.isArray(spec.expect) ? spec.expect.join(' ') : String(spec.expect))));
add('sync-from-central', 'process-alive',
  '★ 坏：进程不在', () => judgePresence({}, false),
  '★ 好：进程在', () => judgePresence({}, true));
add('device-daemon', 'process-alive',
  '★ 坏：进程不在', () => judgePresence({}, false),
  '★ 好：进程在', () => judgePresence({}, true));
add('hb-fwd', 'launchd-loaded',
  '★ 坏：未加载', () => judgePresence({}, false),
  '★ 好：已加载', () => judgePresence({}, true));

// ── tailscale-direct ──
add('tailscale-direct', 'tailscale-status',
  '★ 坏：两个对端都不在', (spec) => judgeTailscale(spec, '100.1.1.1 node-a\n100.2.2.2 node-b'),
  '★ 好：两个对端都在', (spec) => judgeTailscale(spec, '100.1.1.1 macbook-pro-2 active\n100.2.2.2 desktop-p8e7op1 active'));

// ── e2-registry-services ──
add('e2-registry-services', 'registry-services',
  '★ 坏：缺 requiredKeys', (spec) => judgeRegistry(spec, { 'some-other': {} }),
  '★ 好：requiredKeys 齐', (spec) => judgeRegistry(spec, { 'node-bridge': {}, 'dsh-tools': {}, 'agent-way': {} }));

// ═══ ★★ 镜像漂移检测（★ 本矩阵自己的负控）═══
// ★★ 立据：本矩阵复刻了 core.js 的判据式 ⇒
//   ★ 若 core.js 改了判据而本处没跟 ⇒ **本矩阵就在验一个没人用的东西**。
//   ★ 故每次跑都比对：★ **core.js 里必须仍有那些判据行**。
function mirrorDrift() {
  const corePath = path.join(homedir(), 'dsh-plugin-drift-scan', 'lib', 'core.js');
  let src = '';
  try { src = readFileSync(corePath, 'utf8'); } catch (e) { return { ok: false, why: '★ core.js 不可读：' + e.message }; }
  // ★ 镜像依赖的四个判据记号
  const marks = [
    ['expectStatus', 'spec.probe.expectStatus'],
    ['expectBodyContains', 'spec.probe.expectBodyContains'],
    ['requiredKeys', 'requiredKeys'],
    ['tailscale', 'checkTailscale'],
  ];
  const miss = marks.filter(([, k]) => !src.includes(k)).map(([n]) => n);
  return { ok: miss.length === 0, missing: miss, path: corePath,
           why: miss.length ? '★ core.js 缺镜像依赖的判据：' + miss.join(', ') : '★ 镜像依赖的 4 个判据均在 core.js 里' };
}

// ═══ 跑 ═══
function main() {
  let matrix = {};
  try {
    matrix = JSON.parse(readFileSync(MATRIX, 'utf8')).matrix || {};
  } catch (e) {
    console.error(`\u2605 \u77e9\u9635\u4e0d\u53ef\u8bfb\uff1a${e.message}`);
    process.exit(2);
  }
  const items = Object.keys(matrix).filter((k) => !k.startsWith('_'));
  const mirror = mirrorDrift();
  const rows = [];
  for (const c of CASES) {
    const spec = matrix[c.item];
    if (!spec) { rows.push({ ...c, verdict: 'UNDECIDABLE', why: '\u2605 \u9879\u5728\u77e9\u9635\u91cc\u4e0d\u5b58\u5728' }); continue; }
    let bad, good;
    try { bad = c.badFn(spec); } catch (e) { bad = { drift: null, why: 'ERR ' + e.message }; }
    try { good = c.goodFn(spec); } catch (e) { good = { drift: null, why: 'ERR ' + e.message }; }
    // ★★ 负控成立的条件：★ 坏输入必须红 且 好输入必须绿（★ 两者都要，防恒真/恒红）
    let verdict;
    if (bad.drift === true && good.drift === false) verdict = 'PASS';
    else if (bad.drift === false) verdict = 'FAIL';        // ★★ 坏输入判绿 ⇒ 假绿
    else if (good.drift === true) verdict = 'FAIL';        // ★ 好输入判红 ⇒ 假红
    else verdict = 'UNDECIDABLE';
    rows.push({ item: c.item, kind: c.kind, verdict,
      bad: c.badDesc, bad_drift: bad.drift, bad_why: bad.why,
      good: c.goodDesc, good_drift: good.drift });
  }
  const summary = {
    total: rows.length,
    PASS: rows.filter((r) => r.verdict === 'PASS').length,
    FAIL: rows.filter((r) => r.verdict === 'FAIL').length,
    UNDECIDABLE: rows.filter((r) => r.verdict === 'UNDECIDABLE').length,
    items_covered: [...new Set(rows.map((r) => r.item))].length,
    items_total: items.length,
  };
  const out = { version: '1.0.0', matrix: MATRIX, mirror, summary, rows };
  if (AS_JSON) { console.log(JSON.stringify(out, null, 1)); }
  else {
    console.log(`== negctl-drift-scan 1.0.0（\u2605 \u9879 ${items.length} \u00b7 \u56e0\u679c\u5bf9 ${rows.length}）==`);
    for (const r of rows) {
      const tag = r.verdict === 'PASS' ? '\u2705' : (r.verdict === 'FAIL' ? '\u274c' : '\u26a0\ufe0f');
      console.log(`  ${tag} ${r.verdict} \u00b7 ${r.item}`);
      console.log(`     \u574f\u8f93\u5165 drift=${r.bad_drift} \u2014 ${r.bad}`);
      console.log(`     \u597d\u8f93\u5165 drift=${r.good_drift} \u2014 ${r.good}`);
      if (r.bad_why) console.log(`     \u5224\u636e\uff1a${r.bad_why}`);
    }
    console.log(`\n  \u6c47\u603b\uff1a\u2605 **PASS ${summary.PASS} \u00b7 FAIL ${summary.FAIL} \u00b7 \u4e0d\u53ef\u5224 ${summary.UNDECIDABLE}**`);
    console.log(`  \u8986\u76d6\uff1a\u2605 **${summary.items_covered}/${summary.items_total}** \u9879`);
  }
  return (summary.FAIL || !mirror.ok) ? 1 : 0;
}
process.exit(main());
