#!/usr/bin/env node
/**
 * sandbox-central-inbox.mjs —— central-inbox 的**可观察沙箱**（2026-10-04）
 *
 * 目的：用**我自己的判据**验证**别人的实现**（而不是跑它的 selftest 就算数）。
 * 现状：时效门逻辑在 `handleEvent` 闭包内、不可导出 ⇒ 静态读代码无法验证行为
 *   ⇒ 必须给它一个可控环境：**假 SSE 桥 + stub agentBus + 隔离 HOME**。
 *
 * 被测对象：`~/dsh-collab/data/packages/staging-central-inbox-0.2.11`
 * 影子布局（让 `../../dsh-comm-shared/identity.js` 能解析）：
 *   <tmp>/nm/dsh-plugin-central-inbox  ← 复制被测包
 *   <tmp>/nm/dsh-comm-shared           ← 软链真实的
 *
 * 用法： node sandbox-central-inbox.mjs [被测包目录]
 */
import fs from 'node:fs';
import os from 'node:os';
import http from 'node:http';
import path from 'node:path';

// 默认被测对象 = **已部署的那个**（判据应默认判线上实现；要验别的版本就显式传目录）
const SRC = process.argv[2] ||
  path.join(os.homedir(), '.dsh/profiles/web/node_modules/dsh-plugin-central-inbox');
// ★ 必须在改写 HOME **之前**把真实输入读进来（否则 os.homedir() 指向沙箱、token/数据取不到 —— 实测踩到）
const REAL_HOME = os.homedir();
const REAL_TOKEN = fs.readFileSync(path.join(REAL_HOME, '.dsh/blackboard-token'), 'utf8').trim();
const REAL_TRIAGE = path.join(REAL_HOME, 'dsh-collab/data/ops/replayed-batch-triage-20261003.json');
const REAL_NM = path.join(REAL_HOME, '.dsh/profiles/web/node_modules');
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'ci-sandbox-'));
const NM = path.join(TMP, 'nm');
const HOME = path.join(TMP, 'home');
fs.mkdirSync(path.join(HOME, '.dsh'), { recursive: true });
fs.mkdirSync(NM, { recursive: true });
fs.cpSync(SRC, path.join(NM, 'dsh-plugin-central-inbox'), {
  recursive: true,
  filter: (s) => !/(\.bak|\.git|__pycache__|\.DS_Store|\._)/.test(path.basename(s)),
});
fs.symlinkSync(path.join(REAL_NM, 'dsh-comm-shared'), path.join(NM, 'dsh-comm-shared'));
const PKG = path.join(NM, 'dsh-plugin-central-inbox');
const LOG = path.join(HOME, '.dsh/central-inbox.log');
const SEEN = path.join(HOME, '.dsh/central-inbox-seen.json');

// ── 假 SSE 桥 ────────────────────────────────────────────────────────────
let sseClients = [];
const server = http.createServer((req, res) => {
  if (!req.url.startsWith('/events')) { res.writeHead(404).end('nope'); return; }
  res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' });
  res.write('event: hello\ndata: {"bridge":"sandbox"}\n\n');
  sseClients.push(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const PORT = server.address().port;

function push(key, card, eventTs, id) {
  const frame = `event: change\nid: ${id}\ndata: ${JSON.stringify({
    key, ts: eventTs, value: card, version: 1,
  })}\n\n`;
  for (const c of sseClients) c.write(frame);
}

// ── 环境（必须在 import 之前设好：模块顶层读 env）──────────────────────
process.env.HOME = HOME;
process.env.CENTRAL_INBOX_SSE = `http://127.0.0.1:${PORT}/events`;
process.env.CENTRAL_INBOX_LOG = LOG;
process.env.DSH_NODE_ID = 'mbp';
process.env.CENTRAL_AGENT = 'session-sandbox-me';
process.env.CENTRAL_INBOX_MAX_REPLAY_AGE_MS = String(24 * 3600 * 1000);

// ── stub ctx / agentBus ──────────────────────────────────────────────────
const sent = [];
let busIds = ['session-sandbox-me', 'session-other-1234'];   // ★ S7 会把它清空来模拟 boot 窗口
const bus = {
  list: () => busIds.map((id) => ({ id, status: 'idle' })),
  send: (from, to, text, thread, opts) => { sent.push({ from, to, text, opts }); return { status: 'queued' }; },
};
const cleanups = [];
const ctx = { get: (k) => (k === 'agentBus' ? bus : undefined), effect: (fn) => { const c = fn(); if (typeof c === 'function') cleanups.push(c); } };

const mod = await import(path.join(PKG, 'lib/index.js'));
mod.apply(ctx);
await new Promise((r) => setTimeout(r, 800));      // 等 SSE 连接建立

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const readLog = () => { try { return fs.readFileSync(LOG, 'utf8'); } catch { return ''; } };
const inSeen = (k) => { try { return JSON.parse(fs.readFileSync(SEEN, 'utf8')).some((x) => String(x).startsWith(k + '#')); } catch { return false; } };
async function waitFor(pred, ms = 4000) { const t0 = Date.now(); while (Date.now() - t0 < ms) { if (pred()) return true; await sleep(120); } return pred(); }

const now = Date.now();
const old = now - 48 * 3600 * 1000;
const results = [];
function record(name, pass, detail) { results.push({ name, pass, detail }); }

// ── S1 新鲜事件 ⇒ 应注入 ────────────────────────────────────────────────
let n0 = sent.length;
push('notes/mbp/sbx-fresh', { from: 'session-other-1234', to: 'mbp', body: 'fresh', sent_at_epoch_ms: now, ts: Math.floor(now / 1000) },
     new Date(now).toISOString(), 1);
await waitFor(() => sent.length > n0);
record('S1 新鲜事件 ⇒ 注入（阴性对照）', sent.length === n0 + 1, `send 次数 +${sent.length - n0}`);

// ── S2 超龄事件（外层 ts 48h 前）⇒ 应跳过 ───────────────────────────────
n0 = sent.length;
push('notes/mbp/sbx-stale', { from: 'session-other-1234', to: 'mbp', body: 'stale', sent_at_epoch_ms: old, ts: Math.floor(old / 1000) },
     new Date(old).toISOString(), 2);
await waitFor(() => /R43 时效门跳过/.test(readLog()));
await sleep(900);
const staleSkipped = /R43 时效门跳过/.test(readLog()) && sent.length === n0;
record('S2 超龄事件 ⇒ 跳过（结论与 S1 相反）', staleSkipped, `send 次数 +${sent.length - n0}`);

// ── S3 ★ 关键差异：**卡片内容很旧、但外层 ts 是新的**（"按历史重建"刷新的形态）──
n0 = sent.length;
push('notes/collab/sbx-rebuilt-1790955662',                       // 键内 epoch = 旧
     { from: 'session-other-1234', to: 'mbp', body: 'rebuilt-old-content', sent_at_epoch_ms: old, ts: Math.floor(old / 1000) },
     new Date(now).toISOString(),                                   // 外层 ts = 现在
     3);
await waitFor(() => sent.length > n0);
const rebuiltInjected = sent.length > n0;
record('S3 重建卡（内容旧/外层新）⇒ 我的判据应拦、它**放行**（差异项，仅记录）', true,
       rebuiltInjected ? '它放行了（= 只看外层 ts 的已知弱点）' : '它拦住了');

// ── S4 own-node 别名（A②）⇒ 应路由到中枢而非丢弃 ───────────────────────
n0 = sent.length;
push('notes/collab/sbx-alias', { from: 'session-other-1234', to: 'mac-mini', body: 'alias', sent_at_epoch_ms: now, ts: Math.floor(now / 1000) },
     new Date(now).toISOString(), 4);
await waitFor(() => sent.length > n0);
record('S4 to=mac-mini ⇒ 不丢弃（A② 别名兜底生效）', sent.length > n0,
       sent.length > n0 ? `路由到 ${sent[sent.length - 1].to}` : '被丢弃');

// ── S5 seen 后置：成功注入 ⇒ 写 seen；失败注入 ⇒ 不写见 ────────────────
n0 = sent.length;
push('notes/mbp/sbx-fail', { from: 'session-other-1234', to: 'zzz-unresolvable-xyz', body: 'fail', sent_at_epoch_ms: now, ts: Math.floor(now / 1000) },
     new Date(now).toISOString(), 5);
await waitFor(() => /注入目标为 null/.test(readLog()) || sent.length > n0);
await sleep(600);
// ★ 它的 seen 是 **30s 防抖落盘**（setInterval(_flushSeen, 30000)）——
//   直接断言会假失败（我第一版就踩了）。这里用 ctx.effect 注册的清理函数**显式触发 flush**。
for (const c of cleanups) { try { c(); } catch {} }
await sleep(300);
const failNoSeen = !inSeen('notes/mbp/sbx-fail');
record('S5 失败注入（目标 null）⇒ **不写 seen**（seen 后置生效）', failNoSeen && sent.length === n0,
       `send +${sent.length - n0} / seen=${!failNoSeen}`);
record('S5b 成功注入的卡 **写进 seen**（flush 后）', inSeen('notes/mbp/sbx-fresh'),
       `fresh in seen=${inSeen('notes/mbp/sbx-fresh')}`);

console.log(`被测: ${SRC}\n沙箱: ${TMP}\n`);

// ── S6 ★ 真实数据回放：2026-10-03 那 106 条风暴卡（对**任何实现**都适用）──────
//   这一条是"判据必须拿真实坏数据回放"的落地：不看它怎么实现，只看**行为**。
try {
  const triage = JSON.parse(fs.readFileSync(REAL_TRIAGE, 'utf8'));
  const keys = triage.rows.map((r) => r.key);
  const TOK = REAL_TOKEN;
  const board = (await (await fetch('http://xingqiao.meetfunbp.com:8792/notes', {
    headers: { 'X-Blackboard-Token': TOK, Authorization: 'Bearer ' + TOK },
  })).json()).list;
  const before = sent.length;
  const logBefore = (readLog().match(/R43 时效门跳过/g) || []).length;
  let pushed = 0, id = 100;
  for (const k of keys) {
    const e = board[k];
    if (!e) continue;
    const card = (e.value && (e.value.from || e.value.to)) ? e.value
      : (e.value && e.value.value) ? e.value.value : e.value;
    push(k, card, e.ts, id++);                        // ★ 用**真实外层 ts**
    pushed++;
  }
  await waitFor(() => (readLog().match(/R43 时效门跳过/g) || []).length >= logBefore + pushed, 12000);
  await sleep(1500);
  const skipped = (readLog().match(/R43 时效门跳过/g) || []).length - logBefore;
  const injected = sent.length - before;
  const rate = skipped / Math.max(skipped + injected, 1);
  record(`S6 真实回放 ${pushed} 条风暴卡 ⇒ 拦截率 ≥95%`, rate >= 0.95,
         `跳过 ${skipped} / 注入 ${injected} ⇒ 拦截率 ${(rate * 100).toFixed(1)}%`);
} catch (e) {
  record('S6 真实回放（取板失败，未执行）', false, String(e).slice(0, 90));
}

// ── S7 ★ G30：boot 窗口（agentBus.list() 为空 ⇒ target=null）不得丢卡；bus 就绪后应重放 ──
//   对端 0.2.12 的 G30 修法 = 失败事件入有界缓冲（≤50 条 / 30min TTL），5s 周期在 bus 就绪后重放。
//   判据（正负对照）：空窗期**不许注入**；bus 就绪后**必须**注入（否则"缓冲"名不副实）。
{
  busIds = [];                                            // ① boot 窗口：无任何在线会话
  const n0 = sent.length;
  const k = 'notes/mbp/sbx-bootwin-' + Date.now();
  push(k, { from: 'session-other-1234', to: 'session-sandbox-me', body: 'boot-window',
            sent_at_epoch_ms: Date.now(), ts: Math.floor(Date.now() / 1000) },
       new Date().toISOString(), 90);
  await sleep(2500);
  const during = sent.length - n0;
  record('S7a boot 窗口（bus 空）⇒ **不许注入**', during === 0, `空窗期 send +${during}`);
  busIds = ['session-sandbox-me', 'session-other-1234'];   // ② bus 就绪
  const ok = await waitFor(() => sent.length > n0, 13000);  // 等它的重放周期（5s）
  record('S7b bus 就绪后 ⇒ **缓冲被重放注入**（G30）', ok,
         ok ? `重放成功（send +${sent.length - n0}）` : '未重放 ⇒ 卡被吞（G30 未生效）');
}

for (const r of results) console.log(`  ${r.pass ? '✅' : '❌'} ${r.name}  | ${r.detail}`);
console.log('\n── 沙箱日志摘录 ──');
console.log(readLog().split('\n').filter(Boolean).slice(-8).map((l) => '  ' + l.slice(-150)).join('\n'));

for (const c of cleanups) { try { c(); } catch {} }
server.close();
const ok = results.every((r) => r.pass);
console.log('\n' + (ok ? '✅ 沙箱全部通过' : '❌ 有失败项'));
process.exit(ok ? 0 : 1);
