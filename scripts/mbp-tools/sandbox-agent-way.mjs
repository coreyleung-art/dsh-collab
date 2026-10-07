#!/usr/bin/env node
/**
 * sandbox-agent-way.mjs —— agent-way **投递路径**的可观察沙箱（2026-10-04 建立）
 *
 * 【为什么必须有】（这次事故的判据缺口）
 *   1.5.12 把回复指路改成 `export { peerNodeHint, replyCardHint } from './reply-hint.js'` ——
 *   **这是"再导出"，不在本模块建立绑定** ⇒ index.js 内调用 `replyCardHint(...)` 抛
 *   `ReferenceError: replyCardHint is not defined` ⇒ 被 `deliver()` 的 `catch { return false }`
 *   **静默吞掉** ⇒ 消息状态退回 `queued` ⇒ **凡非本机会话发来的消息全部投不出去**（实测 16 小时）。
 *   ★ 两端的判据都没抓到：它的 selfcheck 与我的 ⑨b 都**只 import `reply-hint.js` 直接调函数**，
 *     **从不经过 index.js 的作用域** ⇒ 判据与故障不同层。本沙箱补上这一层：
 *     **真 apply 插件 → 真调 agentBus.send → 看它返回 delivered 还是 queued**。
 *
 * 用法： node sandbox-agent-way.mjs [被测插件目录]
 *   期望：`send → delivered` 且 fake agent 的 followup 被调用；
 *         若出现 `queued` 或 lastError，则**判失败**（附 lastError 原文）。
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const SRC = process.argv[2] ||
  path.join(os.homedir(), '.dsh/profiles/web/node_modules/dsh-plugin-agent-way');
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'aw-sandbox-'));
process.env.HOME = TMP;                       // 隔离（它会写 ~/.dsh 下的状态）
fs.mkdirSync(path.join(TMP, '.dsh'), { recursive: true });
process.env.DSH_NODE_ID = 'mbp-sandbox';

const LOCAL = 'session-abcdef01-2345-6789-abcd-ef0123456789';     // ★ 真实 id 形态（hex）——非 hex 会被规范化判成标签、targetLive=false（实测踩过）
const followups = [];
const fakeAgent = {
  id: LOCAL, status: 'idle',
  followup(msg) { followups.push(msg); },
  inject(msg) { followups.push(msg); },
};
const provided = {};
const ctx = {
  get: (name, dflt) => {
    if (name === 'agents') return { list: () => [{ id: LOCAL, status: 'idle' }], get: (id) => (id === LOCAL ? fakeAgent : undefined) };
    if (name === 'systemPrompt') return { section: () => ({}) };
    if (name === 'tools') return { define: () => {} };
    return dflt === undefined ? undefined : dflt;
  },
  provide: (name, obj) => { provided[name] = obj; },
  on: () => {},
  effect: (fn) => { try { fn(); } catch {} },
  logger: { info() {}, warn() {}, error() {} },
  server: { register() {} },
};

const mod = await import(path.join(SRC, 'lib/index.js'));
let applied = 'ok';
try { mod.apply(ctx); } catch (e) { applied = 'apply 抛错: ' + String(e.message).slice(0, 120); }

const out = [];
const bus = provided['agentBus'];
if (!bus) out.push(['❌', 'agentBus 未被 provide', applied]);
else {
  // ★ 关键：from 用**非本机会话**（跨机来源），正是触发 replyCardHint 分支的形态
  const r1 = bus.send('session-12345678-9abc-def0-1234-56789abcdef0', LOCAL, '看黑板 notes/mbp/x', undefined, { replyRequired: true });
  out.push([r1 && r1.status === 'delivered' ? '✅' : '❌',
            '跨机来源 send ⇒ 应 delivered', 'status=' + (r1 && r1.status)]);
  // 阴性对照：本机来源（走 agent_send 指引分支，不经 replyCardHint）
  const r2 = bus.send(LOCAL, LOCAL, '本机自测', undefined, {});
  out.push([r2 && (r2.status === 'self-echo' || r2.status === 'delivered') ? '✅' : '❌',
            '本机来源 send ⇒ 不受影响（阴性对照）', 'status=' + (r2 && r2.status)]);
  out.push([followups.length > 0 ? '✅' : '❌', 'fake agent 收到 followup', 'followups=' + followups.length]);
  // flush 是否能救回
  // ★ 断言「能力存在」而不是「必须 >0」：上一条已 delivered ⇒ 没有积压可 flush 是**正确**结果
  //   （我第一版写成 saved>0 ⇒ 对自己刚修好的实现误报，属类别 C：判据的期望值没考虑正常路径）
  if (typeof bus.flush === 'function') {
    const saved = bus.flush();
    out.push([typeof saved === 'number' ? '✅' : '❌', 'agentBus.flush() 已暴露且返回计数（1.5.13 能力）',
              'delivered=' + saved + '（上一条已投递 ⇒ 0 正确）']);
  } else {
    out.push(['❌', 'agentBus.flush() 未暴露（1.5.13 应有）', '']);
  }
  // 直接暴露 lastError（1.5.13 起会记）
  const threads = typeof bus.threads === 'function' ? bus.threads(LOCAL) : [];
  const errs = threads.flatMap((t) => t.messages || []).map((m) => m.lastError).filter(Boolean);
  if (errs.length) out.push(['❌', '存在投递失败记录（lastError）', String(errs[0]).slice(0, 90)]);
}

console.log('被测:', SRC);
console.log('apply:', applied);
for (const [mk, name, detail] of out) console.log(`  ${mk} ${name}  | ${detail}`);
const ok = out.every(([mk]) => mk === '✅');
console.log('\n' + (ok ? '✅ 投递路径可用' : '❌ 投递路径**不可用**（这就是"消息排队收不到"的形态）'));
process.exit(ok ? 0 : 1);
