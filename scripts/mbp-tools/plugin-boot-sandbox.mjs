#!/usr/bin/env node
/**
 * plugin-boot-sandbox.mjs — **可观察的模拟 boot 沙箱**
 *
 * ## 为什么需要它（2026-10-03 四次误报之后）
 *
 * 之前的两条路都有死结：
 *   · **静态检查**（语法/依赖/裸符号）：看不到**运行时**行为 ⇒ 0.2.9 的自递归**整体溜过**
 *   · **stub 隔离冒烟**：环境不真 ⇒ 报 4 个假阳性（`config` 缺失导致 `config.dataDir` 崩、
 *     非标准插件无 `lib/index.js`、注释里的 `import()` 被当成依赖）
 *   ⇒ 一句话：**模拟得不够真 = 假失败；模拟不到 = 假通过。**
 *
 * ## 本沙箱的取舍
 *
 * | 维度 | 真实 | 隔离 |
 * |---|---|---|
 * | **配置** | ✅ 从真实 profile 的 `cordis.patch.yml` 读 | — |
 * | **加载顺序** | ✅ 按真实 `bundles[]` 顺序 | — |
 * | **服务面** | ✅ 提供 agentBus/tools/commands/webServer/logger… | — |
 * | **文件系统** | — | ✅ `HOME` 指向 mkdtemp 沙箱 |
 * | **网络** | — | ✅ `fetch`/`XMLHttpRequest` 全掐 |
 * | **进程** | — | ✅ 独立进程，可被父级超时强杀 |
 *
 * ## 可观测性（这是本沙箱存在的理由）
 *
 * 逐插件记录 **① 加载耗时 ② apply 耗时 ③ 输出行数 ④ 事件循环漂移**，
 * 并对**每一步**设超时 ⇒ **卡住时能指出是哪个插件**（之前只知道"整体超时"）。
 *
 * 用法：
 *   node plugin-boot-sandbox.mjs [--profile web] [--settle-ms 800] [--json]
 * 退出码：0 = 全部沉降正常 / 1 = 有插件异常（并指出是哪个）/ 2 = 用法错误
 */
import { mkdtempSync, existsSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, basename } from 'node:path';
import { pathToFileURL } from 'node:url';

// ── 参数 ────────────────────────────────────────────────────────────────────
const argv = process.argv.slice(2);
const getArg = (k, d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d; };
const PROFILE = getArg('--profile', 'web');
const SETTLE_MS = Math.min(Number(getArg('--settle-ms', 800)) || 800, 10000);
const AS_JSON = argv.includes('--json');

const DSH_HOME = process.env.DSH_HOME || join(process.env.HOME || '', '.dsh');
const PROFILE_DIR = join(DSH_HOME, 'profiles', PROFILE);
const NM = join(PROFILE_DIR, 'node_modules');

if (!existsSync(join(PROFILE_DIR, 'package.json'))) {
  console.error(`找不到 profile: ${PROFILE_DIR}`);
  process.exit(2);
}
// 探针（走 stderr，不经 console 劫持）——用于确认脚本确实执行到这里
process.stderr.write(`[boot-sandbox] start profile=${PROFILE} dir=${getArg('--dir', '') || '(bundles)'}\n`);

// ── 隔离：HOME 沙箱 + 掐网络（必须在任何插件 import 之前设置）─────────────
const SANDBOX_HOME = mkdtempSync(join(tmpdir(), 'boot-sandbox-'));
const REAL_HOME = process.env.HOME;
process.env.HOME = SANDBOX_HOME;
process.env.USERPROFILE = SANDBOX_HOME;
process.env.CENTRAL_AGENT = process.env.CENTRAL_AGENT || 'boot-sandbox-dummy';
delete process.env.BLACKBOARD_TOKEN;

globalThis.fetch = () => Promise.reject(new Error('boot-sandbox: network disabled'));
globalThis.XMLHttpRequest = class { constructor() { throw new Error('boot-sandbox: network disabled'); } };

// ── 输出计数（自递归每层一行；设转发上限避免沙箱自己变成刷屏源）──────────
// ★ 报告输出必须**绕过 console 劫持**（2026-10-03 实测踩坑）：
//   原实现里报告用 `console.log.bind(console)`，而劫持版带 `outLines <= 30` 限流；
//   插件探测期间 `outLines` 会被**插件自身输出**累加 ⇒ 一旦某插件吐超 30 行，
//   **我自己的报告就被自己的限流整段挡掉** ⇒ 表现为「exit 0 且输出为空」。
//   ⇒ 报告走 `process.stdout.write`，与限流完全解耦。
let outLines = 0;
let counting = false;
const FORWARD_LIMIT = 30;
const _log = (s) => process.stdout.write(String(s) + '\n');
const _err = (s) => process.stderr.write(String(s) + '\n');
const _rawLog = console.log.bind(console);
const _rawErr = console.error.bind(console);
console.log = (...a) => { if (counting) outLines++; if (outLines <= FORWARD_LIMIT) _rawLog(...a); };
console.error = (...a) => { if (counting) outLines++; if (outLines <= FORWARD_LIMIT) _rawErr(...a); };

// ── 读真实 profile：bundles 顺序 + 每个插件行的 config ────────────────────
const pkg = JSON.parse(readFileSync(join(PROFILE_DIR, 'package.json'), 'utf8'));
const bundles = (pkg?.dsh?.profile?.bundles) || [];

/** 从 profile 的 cordis.patch.yml 里尽量抽出各插件行的 config（YAML 子集解析）。 */
function readPatchConfigs() {
  const out = {};
  for (const f of ['cordis.patch.yml', 'cordis.yml']) {
    const p = join(PROFILE_DIR, f);
    if (!existsSync(p)) continue;
    const txt = readFileSync(p, 'utf8');
    // 极简解析：找 `- insert:` 段里的 `id: X` 与紧随的 `config:` 块
    const lines = txt.split('\n');
    let curId = null, inCfg = false, cfgIndent = 0, buf = [];
    const flush = () => {
      if (curId && buf.length) {
        // 只取一层 key: value
        const c = {};
        for (const l of buf) {
          const m = l.match(/^\s*([\w-]+):\s*(.*)$/);
          if (m) {
            let v = m[2].trim();
            if (v === '' ) v = undefined;
            else if (/^-?\d+$/.test(v)) v = Number(v);
            else if (v === 'true' || v === 'false') v = v === 'true';
            else v = v.replace(/^["']|["']$/g, '');
            if (v !== undefined) c[m[1]] = v;
          }
        }
        if (Object.keys(c).length) out[curId] = c;
      }
      buf = []; inCfg = false;
    };
    for (const l of lines) {
      const idm = l.match(/^\s*-\s*id:\s*([\w-]+)/) || l.match(/^\s*id:\s*([\w-]+)/);
      if (idm) { flush(); curId = idm[1]; continue; }
      const cfm = l.match(/^(\s*)config:\s*$/);
      if (cfm) { inCfg = true; cfgIndent = cfm[1].length; continue; }
      if (inCfg) {
        const ind = (l.match(/^\s*/) || [''])[0].length;
        if (l.trim() && ind <= cfgIndent) { inCfg = false; continue; }
        buf.push(l);
      }
    }
    flush();
  }
  return out;
}
const PATCH_CONFIGS = readPatchConfigs();

// ── 未处理异常：**不能让单个插件的异步崩溃杀掉整个沙箱** ──────────────────
// 实测：fapai-intel 的 `apply` 里是 `void boot(...)`（fire-and-forget），
// config.dataDir 缺失时后台 rejection ⇒ 直接杀掉沙箱进程，后续插件全没测。
// ⇒ 记录下来并归到「当前正在探的插件」，然后继续。
let CURRENT = null;
function noteAsync(mark, e) {
  const msg = `${mark}: ${String(e?.message || e).slice(0, 150)}`;
  // ★ 必须发声（R034：静默失败不允许）。2026-10-03 实测教训：本处理器最初在 CURRENT 为空时
  //   什么都不做，结果**把沙箱自身的 ReferenceError 静默吞掉** ⇒ 表现为「exit 0 + 零输出」，
  //   排查了很久。任何被捕获的异常都必须留下痕迹。
  process.stderr.write('[boot-sandbox] ' + msg + '\n');
  if (CURRENT && CURRENT.status === 'ok') { CURRENT.status = 'apply-threw'; CURRENT.detail = msg; }
  else if (CURRENT) { CURRENT.detail = (CURRENT.detail ? CURRENT.detail + ' | ' : '') + msg; }
}
process.on('unhandledRejection', (e) => noteAsync('unhandledRejection', e));
process.on('uncaughtException', (e) => noteAsync('uncaughtException', e));

// ── 造「足够真实」的 ctx ───────────────────────────────────────────────────
function makeCtx(pluginName, config) {
  const noop = () => noop;
  const disposers = [];
  const bus = {
    list: () => [],
    send: async () => ({ ok: true, dryRun: true }),
    broadcast: async () => ({ ok: true, dryRun: true }),
    claim: () => null,
    release: () => null,
  };
  const services = { agentBus: bus };
  // ★ `fiber` 是 cordis 的真实 API（`ctx.fiber.effect(...)`）——首版 stub 漏了它，
  //   导致 fapai-intel（lib/index.js:74）报 `… reading 'effect'` 假阳性。
  //   经验：stub ctx 要照着**真实 cordis Context 的面**补，而不是只补「我见过被用到的」。
  const fiber = {
    effect: (fn) => { const d = fn?.(); if (typeof d === 'function') disposers.push(d); return noop; },
    dispose: noop, name: pluginName, runtime: null, config,
  };
  const ctx = {
    name: pluginName,
    fiber,
    config,                                    // ★ 真实配置（不再一律 {}）
    get: (k) => services[k],
    set: (k, v) => { services[k] = v; },
    provide: (k, v) => { services[k] = v; },
    effect: (fn) => { const d = fn?.(); if (typeof d === 'function') disposers.push(d); return noop; },
    on: noop, inject: noop, emit: noop, parallel: noop, waterfall: noop,
    logger: { info: noop, warn: noop, error: noop, debug: noop, trace: noop },
    tools: { register: noop, get: () => undefined },
    commands: { register: noop },
    webServer: { register: () => noop, route: () => noop, get: () => undefined },
    schema: { union: (x) => x, object: (x) => x, string: () => ({}), number: () => ({}) },
    __disposers: disposers,
  };
  return ctx;
}

// ── 逐插件：载入 → 造 ctx → apply → 沉降观测（每步可定位）──────────────────
async function probe(id, dir, label) {
  const rec = { id, label, dir, load_ms: null, apply_ms: null, settle_ms: null,
                lines: 0, drift_ms: null, status: 'ok', detail: '' };
  if (!existsSync(join(dir, 'package.json'))) { rec.status = 'skip'; rec.detail = '无 package.json'; return rec; }
  const entry = join(dir, 'lib/index.js');
  if (!existsSync(entry)) { rec.status = 'skip'; rec.detail = '无 lib/index.js（非标准插件形态）'; return rec; }
  let mod;
  const t0 = Date.now();
  try {
    mod = await import(pathToFileURL(entry).href);
  } catch (e) {
    rec.load_ms = Date.now() - t0;
    rec.status = 'load-fail'; rec.detail = String(e?.message || e).slice(0, 160); return rec;
  }
  rec.load_ms = Date.now() - t0;

  if (typeof mod.apply !== 'function') { rec.status = 'skip'; rec.detail = '无 apply 导出'; return rec; }

  // ★ 配置必须「足够真实」：cordis 会用插件的 `Config` schema 填 default。
  //   漏了这步 ⇒ fapai-intel 的 `config.dataDir` 是 undefined ⇒ mkdir 崩 ⇒ 假阳性。
  let cfg = { ...(PATCH_CONFIGS[id] || {}), ...(PATCH_CONFIGS[label.replace('dsh-plugin-', '')] || {}) };
  try {
    if (mod.Config && typeof mod.Config === 'function') {
      const filled = mod.Config(cfg);
      if (filled && typeof filled === 'object' && !(filled instanceof Promise)) cfg = filled;
    }
  } catch (_) { /* schema 填不动就保留原样（会在结果里体现为 apply-threw，可据此判断） */ }
  const ctx = makeCtx(id, cfg);
  CURRENT = rec;

  counting = true; outLines = 0;
  const t1 = Date.now();
  let threw = null;
  try {
    mod.apply(ctx, cfg);
  } catch (e) {
    threw = String(e?.message || e).slice(0, 180);
  }
  rec.apply_ms = Date.now() - t1;

  // ★ 沉降窗口：apply 返回后**不退出**，看事件循环是否被占用、输出是否暴增
  const t2 = Date.now();
  await new Promise((r) => setTimeout(r, SETTLE_MS));
  rec.settle_ms = Date.now() - t2;
  rec.drift_ms = rec.settle_ms - SETTLE_MS;
  rec.lines = outLines;
  counting = false;

  const DRIFT_LIMIT = Math.max(SETTLE_MS, 1200);
  const LINE_LIMIT = 150;
  if (threw) { rec.status = 'apply-threw'; rec.detail = threw; }
  else if (rec.drift_ms > DRIFT_LIMIT) {
    rec.status = 'stalled';
    rec.detail = `事件循环漂移 ${rec.drift_ms}ms（限 ${DRIFT_LIMIT}）⇒ 疑后台链失控`;
  } else if (rec.lines > LINE_LIMIT) {
    rec.status = 'flood';
    rec.detail = `窗口内输出 ${rec.lines} 行（限 ${LINE_LIMIT}）⇒ 疑刷屏循环`;
  }
  return rec;
}

// ── 主流程：按真实 bundles 顺序（或 --dir 单探，用于判别力自证）──────────────
const ONLY_DIR = getArg('--dir', '');
const results = [];

if (ONLY_DIR) {
  const d = resolve(ONLY_DIR);
  results.push(await probe(basename(d), d, basename(d)));
} else {
  for (let i = 0; i < bundles.length; i++) {
    const b = bundles[i];
    const label = String(b).replace(/^@[^/]+\//, '');
    const dir = join(NM, label);
    if (existsSync(dir)) {
      results.push(await probe(b, dir, label));
    } else {
      // 宿主包（@deepseek-ai/* 在 runtime 里）⇒ 标记为宿主层，不在此探
      results.push({ id: b, label, dir, status: 'host', load_ms: null, apply_ms: null,
                     settle_ms: null, lines: 0, drift_ms: null, detail: '宿主包（非 profile 插件）' });
    }
  }
}
const bad = results.filter((r) => ['load-fail', 'apply-threw', 'stalled', 'flood'].includes(r.status));

/** ★ 收尾必须等 stdout flush。
 *  2026-10-03 实测：直接 `process.exit()` 会**丢弃未 flush 的管道缓冲** ——
 *  `--dir` 模式下表现为「exit 0 且输出全空」，让人误以为沙箱没跑。
 *  故：先设 exitCode，再等一次 write 回调，最后兜底超时退出。 */
function finish(code) {
  process.exitCode = code;
  process.stdout.write('', () => process.exit(code));
  const t = setTimeout(() => process.exit(code), 800);
  t.unref?.();
}
if (AS_JSON) {
  _log(JSON.stringify({ sandbox_home: SANDBOX_HOME, settle_ms: SETTLE_MS, results }, null, 2));
  // ★ 同一条修正也要落在 JSON 分支：**什么都没测到 ≠ 通过**（否则 --json 调用方会误判）
  const _tested = results.filter((r) => !['skip', 'host'].includes(r.status));
  finish((bad.length || _tested.length === 0) ? 1 : 0);
} else {

_log('═'.repeat(76));
_log(`可观察 boot 沙箱 · profile=${PROFILE} · 顺序=${bundles.length} 项 · 沉降窗口=${SETTLE_MS}ms`);
_log(`沙箱 HOME: ${SANDBOX_HOME}（真实 ${REAL_HOME} 未被触碰）`);
_log('═'.repeat(76));
for (const r of results) {
  const mark = { ok: '✅', skip: '·', host: '·', 'load-fail': '❌', 'apply-threw': '❌',
                 stalled: '❌', flood: '❌' }[r.status] || '?';
  const t = [r.load_ms !== null ? `载入${r.load_ms}ms` : null,
             r.apply_ms !== null ? `apply${r.apply_ms}ms` : null,
             r.settle_ms !== null ? `沉降${r.settle_ms}ms(漂移${r.drift_ms >= 0 ? '+' : ''}${r.drift_ms})` : null,
             r.lines ? `输出${r.lines}行` : null].filter(Boolean).join(' · ');
  _log(`${mark} ${String(r.id).padEnd(34)} ${t}`);
  if (r.detail) _log(`      ${r.detail}`);
}
_log('═'.repeat(76));
// ── ★ 判据判别力修正（2026-10-03 完整审查 T5 查出 · 类别 C「假绿灯」）──────────
//   缺陷：`status='skip'`（目标不可探：无 package.json / 无 lib/index.js）
//         与 `status='host'`（宿主包）都**既不算 bad 也不计入成功条件** ⇒
//         于是「一个插件都没真测到」时，仍打印 **✅ 全部沉降正常 ⇒ 可以重启** 且 exit 0。
//   实测证据（正负样本）：
//     · 正样本 `/Users/coreyleung/dsh-plugin-restart-audit` ⇒ `✅ 载入12ms · apply1ms · 沉降802ms`
//     · 负样本 `--dir /tmp/definitely-not-exist-xyz` ⇒ `· 无 package.json` 之后仍打印
//       `✅ 全部沉降正常 ⇒ 可以重启`（exit 0）
//   危害：本判据被宣传为「**唯一**能抓 apply 后台链失控的判据」，又是 R040 重启门的一道
//         ⇒ 它假绿灯 = **重启门整体失效而不自知**。判据「什么都没测」必须**报失败**，
//           而不是报成功 —— 这是"没观测 ≠ 不存在"（R035）在判据侧的落地。
const tested = results.filter((r) => !['skip', 'host'].includes(r.status));
const untestable = results.filter((r) => ['skip', 'host'].includes(r.status));
if (untestable.length) {
  _log(`ℹ️ 实测 ${tested.length} 项 / 未测 ${untestable.length} 项`
       + `（未测=${untestable.map((r) => `${r.label}:${r.detail || r.status}`).join('、')}）`);
}
if (bad.length) {
  _log(`⛔ ${bad.length} 个插件异常：${bad.map((r) => `${r.label}(${r.status})`).join('、')}`);
  _log('   ⇒ **不建议重启**（上面已定位到具体插件与阶段）');
} else if (tested.length === 0) {
  // ★ 关键：什么都没真测到 ⇒ 必须报失败，不得报成功
  _log('⛔ **未实际探测任何插件** —— 目标不可探（无 package.json / 无 lib/index.js / 全为宿主包）。');
  _log('   ⇒ 本次「无异常」**不构成任何证据**（判据未运行，不是判据通过）。');
  if (ONLY_DIR) _log(`   ⇒ 请用 **插件目录的绝对路径**（不是插件名）：--dir /path/to/dsh-plugin-x`);
  _log('   ⇒ **不得**据此宣告"可以重启"。');
} else {
  _log(`✅ ${tested.length} 项实测沉降正常 ⇒ 可以重启`);
}
finish((bad.length || tested.length === 0) ? 1 : 0);
}
