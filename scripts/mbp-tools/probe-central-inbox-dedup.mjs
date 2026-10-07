/**
 * probe-central-inbox-dedup.mjs — central-inbox 去重/路由纯逻辑判别性探针
 *
 * 目的：为「重启后新版是否真的在跑」提供**可判别**的证据。
 *   仅看版本号字符串（verify 脚本 ④⑤）只能证明包已就位，证不了行为。
 *
 * 判别性设计（关键）：
 *   A 用例的输入对**新旧两种去重键公式给出相反结论**：
 *     · 新公式 key + '#' + fp(内容)      ⇒ 同内容/version 变 ⇒ 不注入（正确）
 *     · 旧公式 key + '@' + version       ⇒ 同内容/version 变 ⇒ 会注入（错误重复）
 *   ⇒ 若探针通过，说明跑的确实是新逻辑，而非"恰好没触发"。
 *   （这正是 2026-10-03 MBP 提的合并建议所针对的形态：星桥「批量补 to→误覆盖→按历史重建」）
 *
 * 用法: node probe-central-inbox-dedup.mjs
 * 退出码: 0=全部通过 / 1=有失败
 */
import path from 'node:path';
import os from 'node:os';
import { pathToFileURL } from 'node:url';

const NM = path.join(os.homedir(), '.dsh/profiles/web/node_modules');
const ROUTE = path.join(NM, 'dsh-plugin-central-inbox/lib/route.js');

const R = await import(pathToFileURL(ROUTE).href);
const { shouldInject, remember, resolveTargetId } = R;

const SELF = 'session-20b800d4-98f6-4e5e-90e4-34f7b6ca61d7';
const PEER = 'session-fa1f9150-c949-401f-ba8c-d265f6221676';
const CTX = {
  prefixes: ['notes/mbp/', 'notes/collab/'],
  nodeId: 'mbp',
  ownSession: SELF,
  centralAgent: PEER,
};

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ✅ %s', name); }
  else { fail++; console.log('  ❌ %s  %s', name, detail === undefined ? '' : '→ ' + detail); }
}

/** 造卡：内容固定，仅 version 可变（模拟「重建卡片」） */
const mkCard = (ver, body = 'same-body') => ({
  key: 'notes/mbp/probe-card',
  version: ver,
  value: { from: PEER, to: 'mbp', title: 'probe', body },
});

console.log('模块: %s', ROUTE);
console.log('导出:', Object.keys(R).sort().join(', '));
console.log();

// ── A. 同 key 同内容 / version 变 ⇒ 必须不注入（新旧判别点）──────────────
console.log('【A】同 key·同内容·version 变（重建卡形态）—— 新旧判别点');
{
  const seen = new Set();
  const a1 = shouldInject(mkCard(1), { ...CTX, seen });
  if (a1.inject) remember(seen, a1.dedupKey);
  const a2 = shouldInject(mkCard(2), { ...CTX, seen });
  check('首次注入', a1.inject === true, JSON.stringify(a1));
  check('重建卡(version 1→2, 内容同) 被抑制', a2.inject === false, JSON.stringify(a2));
  check('抑制原因是 dup', String(a2.reason).startsWith('dup('), a2.reason);

  // 判别力自证：旧公式在同一输入下必须给出**相反**结论
  const oldKey = (c) => c.key + '@' + c.version;
  const seenOld = new Set([oldKey(mkCard(1))]);
  const oldVerdict = seenOld.has(oldKey(mkCard(2)));
  check('判别力自证：旧公式会误判为「新卡」', oldVerdict === false,
        '旧公式也抑制了 ⇒ 本用例无判别力，需重设计');
}

// ── B. 同 key 内容变 ⇒ 必须注入（防「过度去重」回归）────────────────────
console.log('\n【B】同 key·内容变 —— 防过度去重回归（曾于 0.1.6 真实发生）');
{
  const seen = new Set();
  const b1 = shouldInject(mkCard(1, 'v1 内容'), { ...CTX, seen });
  if (b1.inject) remember(seen, b1.dedupKey);
  const b2 = shouldInject(mkCard(1, 'v2 内容已更新'), { ...CTX, seen });
  check('内容变化后仍能注入', b2.inject === true, JSON.stringify(b2));
  check('内容变 ⇒ 去重键不同', b1.dedupKey !== b2.dedupKey);
}

// ── C. 自回声（八位短形式）⇒ 不注入 ────────────────────────────────────
console.log('\n【C】自回声：from 为自身 8 位短 id');
{
  const short = 'session-' + SELF.match(/session-([0-9a-f]{8})/i)[1];
  const c = shouldInject({ key: 'notes/mbp/x', version: 1,
                            value: { from: short, to: 'mbp' } }, { ...CTX, seen: new Set() });
  check('短形式自回声被拦', c.inject === false && String(c.reason).startsWith('self-echo'), JSON.stringify(c));
}

// ── D. 前缀不匹配 ⇒ 不注入 ─────────────────────────────────────────────
console.log('\n【D】前缀门：非本节点监听的 key');
{
  const d = shouldInject({ key: 'notes/mac-mini/x', version: 1,
                           value: { from: PEER, to: 'mbp' } }, { ...CTX, seen: new Set() });
  check('非监听前缀被拦', d.inject === false && d.reason === 'prefix', JSON.stringify(d));
}

// ── E. 收件人不可解析 ⇒ 不得静默回退中枢 ────────────────────────────────
console.log('\n【E】路由：不可解析的 to 不得静默回退中枢（缺陷3）');
{
  const ids = [PEER, SELF];
  const e1 = resolveTargetId('session-deadbeef', { ids, central: PEER });
  check('不可解析 ⇒ skip（不回退中枢）', e1.target === null && e1.mode === 'skip', JSON.stringify(e1));
  const e2 = resolveTargetId('', { ids, central: PEER });
  check('空 to ⇒ 走中枢（合法别名）', e2.target === PEER, JSON.stringify(e2));
  const e3 = resolveTargetId('session-20b800d4', { ids, central: PEER });
  check('短 id 片段唯一命中', e3.target === SELF && e3.reason === 'fragment', JSON.stringify(e3));
}

// ── F. 有界去重表 FIFO 淘汰 ─────────────────────────────────────────────
console.log('\n【F】remember 有界性');
{
  const seen = new Set();
  for (let i = 0; i < 12; i++) remember(seen, 'k' + i, 5);
  check('容量被限制在 cap=5', seen.size === 5, 'size=' + seen.size);
  check('淘汰的是最早写入者', !seen.has('k0') && seen.has('k11'));
}

console.log('\n════ %s ════', fail === 0 ? `全部通过 ${pass}/${pass}` : `通过 ${pass} · 失败 ${fail}`);
process.exit(fail === 0 ? 0 : 1);
