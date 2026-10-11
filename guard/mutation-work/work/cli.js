#!/usr/bin/env node
/**
 * cli.js — CLI 治理（R006 ⑨）+ 自检（②）+ 版本（⑥）+ Lean4 约束门自证（⑩）
 * =============================================================================
 * 用法：
 *   node cli.js --status [--json]        # 只读：本插件标识/阶段/不变量/结构门
 *   node cli.js --dry-run [--json]       # 打印守卫计划，零外部变更
 *   node cli.js --selfcheck              # R014 自查门 + 能力边界 + 真挂载冒烟（三态）
 *   node cli.js --lean4-check [--json]   # 结构门自证（A–F，含负例实测）
 *   node cli.js --tool-version
 * 退出码：0=成功/门生效 · 1=失败/门失效 · 2=用法错误
 *
 * ★ 本 CLI 不 import lib/index.js（那会拉起 @deepseek-ai/dsh-tools）。
 *   只有 --selfcheck 的挂载冒烟才**动态** import 它。
 */
import { parseArgs } from 'node:util';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { PLUGIN_SLUG, PLUGIN_NAME, VERSION, LOG_FILE, log } from './lib/meta.js';
import {
  RECALL_KINDS, ALLOWED_COMMANDS, ALLOWED_INJECT, FORBIDDEN_INJECT,
  GateError, resolveRecallTarget, gateNegativeCases, gatePositiveCases,
  gateFreezeProof, scanExecSites, scanHostPaths, checkInject, readSources, GATE_META
} from './lib/gate.js';
import { runSelfCheck, buildSegments } from './lib/selfcheck.js';
import { runK2SelfTest, digest } from './lib/k2-selftest.js';
import { runK3SelfTest, digestK3 } from './lib/k3-selftest.js';
import { runK4SelfTest, digestK4 } from './lib/k4-selftest.js';
import { calibrationReport, renderCalibration } from './lib/calibration.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const C = { ok: '✅', no: '❌', warn: '⚠️' };
function out(s) { process.stdout.write(s + '\n'); }

/**
 * ★ 源码扫描面**自枚举**（cli.js + lib/ 下全部 .js，含子目录）。
 *
 * 为什么不能写死文件名：写死的名单在新增源码文件时**不会报错，只会漏扫**——
 * 于是 A 项「源码零执行点」在一个空集上通过，得到的是**假绿**。
 * 这正是本插件自己记下的 R006 三句口诀之一「**读不到实参会空集通过**」。
 * K3 新增 `lib/checkpoint.js` / `lib/k3-selftest.js` 时，旧硬编码名单正是会把这两个漏掉的形态；
 * 这里一并按**判据**修（枚举目录），不按**实例**修（再加两个名字）。
 */
function listSources(base = HERE) {
  const acc = ['cli.js'];
  const walk = (rel) => {
    for (const name of fs.readdirSync(path.join(base, rel)).sort()) {
      const r = `${rel}/${name}`;
      if (fs.statSync(path.join(base, r)).isDirectory()) walk(r);
      else if (name.endsWith('.js')) acc.push(r);
    }
  };
  walk('lib');
  return acc;
}

/* ---------------------------------- 参数 ---------------------------------- */
let args;
try {
  args = parseArgs({
    options: {
      status: { type: 'boolean', default: false },
      'dry-run': { type: 'boolean', default: false },
      selfcheck: { type: 'boolean', default: false },
      'tool-version': { type: 'boolean', default: false },
      'lean4-check': { type: 'boolean', default: false },
      'budget-check': { type: 'boolean', default: false },
      'checkpoint-check': { type: 'boolean', default: false },
      'recall-check': { type: 'boolean', default: false },
      calibration: { type: 'boolean', default: false },
      md: { type: 'boolean', default: false },   // ★ 必须声明：漏了它则 --md 会 'Unknown option' 并 exit 2（曾把该报错重定向进报告文件）
      // ★★ 危险开关，默认关：挂载冒烟会**真的执行 lib/index.js 的 apply()**。
      //    禁令（不执行 apply()，除单独授权）挡不住误跑 —— 纪律不如语法。故做成显式开关。
      'allow-apply': { type: 'boolean', default: false },
      'contract-check': { type: 'boolean', default: false },
      json: { type: 'boolean', default: false },
      help: { type: 'boolean', default: false }
    },
    allowPositionals: false
  }).values;
} catch (e) {
  out(`用法错误: ${e.message}`); out('试 --help'); process.exit(2);
}

if (args.help) {
  out(`${PLUGIN_NAME} v${VERSION} — 上下文存活守卫（与官方 compaction-basic 并存，不接管 ctx.compaction）
K2 只测量：守卫默认关闭（enableGuard=false）；本 CLI 全程只读，不改变任何外部状态。

  --status [--json]       只读：标识 / 阶段 / 六条不变量 / 结构门元信息
  --dry-run [--json]      打印守卫计划（阈值公式 + 丢弃阶梯 + 检查点形状），零外部变更
  --budget-check [--json] K2 纯决策核自检（预算表 + 守卫行为），**进程内跑**，末尾打印逐位确定摘要
  --checkpoint-check [--json] K3 纯决策核自检（检查点产出 + 有界阶梯 + 增量账等价性），同上
  --recall-check [--json] K4 纯核自检（检查点账本 + 召回逐字相等 + 三态区分），同上
  --calibration [--json|--md] K5 负控 1 标定：本核缩小地板 vs 官方地板（纯粹、可复跑）
  --contract-check         工具对外契约与实现状态一致性（防文案滞留）
  --selfcheck             R014 自查门 + 三段能力边界（**默认不跑挂载冒烟**）
  --selfcheck --allow-apply  ★ 加此开关**才会执行 apply()**（挂载冒烟）—— 需单独授权
  --lean4-check [--json]  结构门自证 A–F：无执行点 / 负例被拒 / 正例可用 / inject 合规 / 白名单冻结 / dry-run 零变更
  --tool-version  --help
退出码：0 成功 · 1 失败 · 2 用法错误`);
  process.exit(0);
}

if (args['tool-version']) { out(`${PLUGIN_NAME} ${VERSION}`); process.exit(0); }

/* ------------------------- 守卫计划（纯函数，零副作用） ------------------------- */
/** --dry-run 与 F 项共用：只描述"若有守卫会做什么"，不触碰任何状态。 */
function guardPlan() {
  return {
    seam: 'host 平面 agent/pre-step 守卫 + 表面替换（seam b）；不接管 ctx.compaction',
    threshold: 'usable = floor(cw×0.95); limit = min(config, floor(cw×0.90)); preemptCeil = floor(cw×0.70); threshold = min(limit + bufferTokens, usable, preemptCeil)',
    preempt: '第三项是**抢先上限**：官方 compaction-basic 在 floor(cw×0.8) 触发（:13 DEFAULT_THRESHOLD_RATIO）' +
      '⇒ 本守卫必须早于它，故 preemptRatio 默认 0.70、且 < 0.8 由 resolveBudget 强制（配成 ≥0.8 抛 BAD_PREEMPT，' +
      '不留"配置可改却静默失效"的口子）。加性 buffer 在**小窗口**做不到这件事：cw=8192 时 0.9cw+8000 被 usable 夹到 7782，仍晚于官方 6553。',
    concurrency: '★ K3 已接**真判据**（不再是写死的 false）：读 session.events 复刻官方\n'
      + '      assertNoActiveCompaction（dsh-compaction-basic/lib/index.js:504-516）——\n'
      + '      「存在未配对 compaction/start」∧ ¬「有更新的 session/end-seed 边界」。\n'
      + '      后者是**陈旧标记豁免**：崩溃/重启留下的孤儿 start 不会让守卫永久判忙\n'
      + '      （少了它正是 P26 那种静默失效）。守卫只在 enableGuard=true 时注册。',
    checkpoint: '<context_handoff v1 seq-range=A-B> 目标 / 阶段 / todo / 最近人类请求（逐字）/ notes / 省略账（带 seq 指针）/ 召回指南',
    dropLadder: ['1 压缩对话文本预算（每条最少 32 token）', '2 丢最旧工具结果条目（留 [N tool/result entries elided: seqs a-b]）', '3 丢最旧其余条目（留 [N earlier entries elided: seqs a-b]）'],
    onCannotShrink: '走到阶梯末端仍缩不小 ⇒ 写 compaction/notice + WARN（绝不静默 no-op，立项书 I1）',
    tierNote: 'K3：决策核已含**检查点产出 + 有界阶梯 + 保证能减**（lib/checkpoint.js，92 断言 + 19 node:test 全绿）；' +
      '守卫仍**只测量不替换**——表面替换的接线在 K3 后半（需先核实 session.events 真实形状）。'
  };
}

/* ------------------------------- --selfcheck ------------------------------- */
/**
 * 真挂载冒烟（R006 ① 第 5 项硬项）。三态分开报，绝不把 skipped 伪装成 pass：
 *   pass    挂上且注册了预期的东西
 *   fail    apply 抛非依赖类异常 → 真实缺陷
 *   skipped 依赖在本目录解析不到 → 如实说跳过（**据此不得声称 ① 达标**）
 */
/**
 * ★ R006 ③「CLD 自适应」：**不得硬编码宿主私有路径**。
 *   原实现把宿主运行时的那条 node_modules 路径**当成字符串常量写进源码**。
 *   ★ 此处**刻意不复现该字面量**（连注释里也不写）：路径型判据只能按文本扫，
 *     复现它会让「已移除」这件事在判据看来仍不成立。★ 这**不是**为过门禁削字 ——
 *     解释与判据完整保留，只是不再把**已废弃的字面量本身**再写一遍。
 *   危害：宿主一旦挪位/改名，本插件就带着一条**失效路径**继续跑，且**不会报错**
 *   （只是解析不到、静默降级）。这正是"配置可改却不生效"的同一形态。
 *   ⇒ 改为**按真实模块解析回溯**，三条候选、零硬编码：
 *     ① 环境变量 `DSH_RUNTIME_NODE_MODULES`（显式覆盖，供自定义载体）；
 *     ② 从**本插件自身**解析 `@deepseek-ai/dsh-tools` 成功后回溯出 node_modules 目录；
 *     ③ 从**profile/node_modules** 解析同样回溯 —— 插件在宿主体内运行时依赖正是从这里解析
 *        （与 `lib/selfcheck.js` 的 `resolvePeer` **同一条解析链**，不再各自实现口径）。
 *   ★ 三条都拿不到 ⇒ 候选为空 ⇒ 下方三态如实报 `skipped`（**绝不**退回硬编码路径假装能跑）。
 *   ★ 为什么必须复用解析链而不是 `fs.existsSync(目录/@deepseek-ai/dsh-tools)`：
 *     实测本机 `profile/node_modules/@deepseek-ai/dsh-tools` **并不存在**（只有 `.bak-*`），
 *     而 `require.resolve` 却能成功 ⇒ 两种判据**不等价**；用错的那种会把能跑的搞成 skipped。
 */
function runtimeNodeModulesCandidates(profileNm) {
  const cands = [];
  const envNm = process.env.DSH_RUNTIME_NODE_MODULES;
  if (typeof envNm === 'string' && envNm.length > 0) cands.push(envNm);
  const marker = `${path.sep}node_modules${path.sep}`;
  const bases = [import.meta.url];
  if (profileNm) bases.push(path.join(profileNm, 'noop.js'));
  for (const base of bases) {
    try {
      const resolved = createRequire(base).resolve('@deepseek-ai/dsh-tools/package.json');
      const i = resolved.lastIndexOf(marker);
      if (i > 0) cands.push(resolved.slice(0, i + marker.length - 1));
    } catch { /* 该基解析不到 ⇒ 不进候选：由三态如实报 skipped，不猜路径 */ }
  }
  return [...new Set(cands)];
}

async function mountSmoke() {
  const PROF_NM = path.join(os.homedir(), '.dsh', 'profiles', 'web', 'node_modules');
  const linkPath = path.join(HERE, 'node_modules');
  let linked = false;
  const isMissingDep = (m) => /Cannot find package|ERR_MODULE_NOT_FOUND|Cannot find module/.test(String(m));
  try {
    let mod;
    const NEED = '@deepseek-ai/dsh-tools';
    // ★ 候选**不再用 existsSync 过滤**：解析链能解到的目录才是真候选（见上方 ★ 两种判据不等价）
    const cands = runtimeNodeModulesCandidates(PROF_NM).filter((p) => p && fs.existsSync(path.join(p, NEED)));
    try {
      if (cands.length) {
        if (fs.lstatSync(linkPath, { throwIfNoEntry: false })) fs.unlinkSync(linkPath); // broken symlink：existsSync 为 false，须用 lstat
        fs.symlinkSync(cands[0], linkPath);
        linked = true;
      }
      mod = await import('./lib/index.js');
    } catch (e) {
      if (!isMissingDep(e?.message ?? e)) throw e;
      return {
        state: 'skipped',
        detail: (cands.length
          ? `已建两级软链（${cands[0]}）仍解析失败：`
          : `依赖解析不到，且候选均不含 ${NEED}（已查 ${runtimeNodeModulesCandidates(PROF_NM).join(' , ') || '(无候选：环境变量未设且两条解析链均未命中)'}）：`) +
          String(e.message).split('\n')[0]
      };
    }
    const registered = [];
    const ctx = {
      tools: { register: (t) => { registered.push(t?.name ?? '(anon)'); return () => {}; } },
      effect: (fn) => { try { return fn(); } catch { return () => {}; } },
      on: () => () => {},
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    };
    if (typeof mod.apply !== 'function') return { state: 'fail', detail: '未导出 apply()' };
    mod.apply(ctx, {});
    return { state: 'pass', detail: `name=${mod.name || '(无)'} inject=[${(mod.inject || []).join(',')}] tools=[${registered.join(', ') || '无'}]` };
  } catch (e) {
    return { state: 'fail', detail: String(e?.message ?? e).split('\n').slice(0, 2).join(' ') };
  } finally {
    if (linked) { try { fs.unlinkSync(linkPath); } catch { /* 清理失败不掩盖结论 */ } }
  }
}

if (args.selfcheck) {
  const sc = runSelfCheck(PLUGIN_SLUG, {
    requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
    requiredSymbols: ['parseArgs', 'resolveRecallTarget', 'VERSION'],
    sourceFiles: ['cli.js'],
    baseDir: HERE
  });
  out(`R014 自查门: ${sc.ok ? C.ok : C.no} missing=${sc.missing.length} warnings=${sc.warnings.length}`);
  sc.missing.forEach((m) => out(`    ${C.no} ${m}`));
  sc.warnings.forEach((w) => out(`    ${C.warn} ${w}`));
  (sc.notes || []).forEach((n) => out(`    · ${n}`));

  // ② TCC 能力边界自检 —— **三段内容由 lib/selfcheck.js 的 buildSegments() 产出**（R006 ② 的判据对象是模块本身）
  const segs = buildSegments({
    recallKinds: [...RECALL_KINDS], allowedInject: [...ALLOWED_INJECT],
    forbiddenInject: [...FORBIDDEN_INJECT], allowedCommands: [...ALLOWED_COMMANDS],
    nodeVersion: process.version, logFile: LOG_FILE
  });
  out('TCC 能力边界自检（三段）:');
  out(`  [① 能力清单] 本插件**能做**的事（${segs.capabilities.length} 条）：`);
  for (const x of segs.capabilities) out(`    ${C.ok} ${x}`);
  out(`  [② 不该发生路径] 本插件**永远不该做**的事（${segs.forbidden.length} 条，逐条可核）：`);
  for (const x of segs.forbidden) out(`    ${C.ok} ${x}`);
  out(`  [③ 依赖完整性] 本插件**靠什么活**（${segs.deps.length} 条）：`);
  (sc.notes || []).filter((n) => /peer /.test(n)).forEach((n) => out(`    ${C.ok} ${n}`));
  for (const x of segs.deps) out(`    ${C.ok} ${x}`);

  // ⑤ 真挂载冒烟 —— ★★ 约束前置·不可绕过：不给 --allow-apply 就**不构造**执行路径
  const smoke = args['allow-apply'] === true
    ? await mountSmoke()
    : { state: 'skipped', detail: '未给 --allow-apply ⇒ **不执行 apply()**（禁令：需单独授权）。加 --allow-apply 才会跑真挂载冒烟。' };
  const icon = { pass: C.ok, fail: C.no, skipped: C.warn }[smoke.state];
  out(`插件挂载冒烟: ${icon} ${smoke.state} — ${smoke.detail}`);
  if (smoke.state === 'skipped') out(`    ⊘ 未验证 ⇒ **不得据此声称 R006 ① 达标**`);
  else if (smoke.state === 'fail') out(`    ❌ 真实缺陷：apply 阶段崩＝交付物在运行时不存在`);

  const scOk = sc.ok && smoke.state === 'pass';
  out(`自查总判: ${scOk ? C.ok + ' 通过' : C.no + ' 未通过'}` +
      (smoke.state === 'skipped' ? '（挂载冒烟 skipped ＝ 门未生效）' : ''));
  process.exit(scOk ? 0 : 1);
}

/* ------------------------------ --lean4-check ------------------------------ */
/** 插件目录清单（path → {mtimeMs,size}），供 F 项做"零变更"实测。 */
function treeSnapshot(root) {
  const snap = {};
  const walk = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      if (e.name === 'node_modules' || e.name === '.git') continue;
      const p = path.join(dir, e.name);
      if (e.isDirectory()) walk(p);
      else { const s = fs.statSync(p); snap[path.relative(root, p)] = { mtimeMs: s.mtimeMs, size: s.size }; }
    }
  };
  walk(root);
  return snap;
}

if (args['lean4-check']) {
  const checks = [];
  const files = listSources();   // ★ 自枚举（不写死），否则新增文件会静默漏扫 ⇒ A 项假绿
  const sources = readSources(HERE, files);

  // A. 源码级：零执行点 **且** 零宿主私有路径字面量（R006 ③ CLD 自适应）
  const sites = scanExecSites({ sources });
  const hostPaths = scanHostPaths(sources);
  const aOk = sites.length === 0 && hostPaths.length === 0;
  const aDetail = [
    sites.length === 0
      ? `扫描面 ${files.length} 文件内 exec/execFile/spawn/fork 命中 0 次（能力为零，非"没找到危险命令"）`
      : `越界执行点: ${JSON.stringify(sites)}`,
    hostPaths.length === 0
      ? '宿主私有路径字面量命中 0 次（R006 ③ CLD 自适应；仅扫字符串字面量，注释里的历史留痕不判红）'
      : `★ 宿主私有路径字面量: ${JSON.stringify(hostPaths)}`
  ].join(' · ');
  checks.push({ id: 'A 源码零执行点+零宿主路径', ok: aOk, detail: aDetail });

  // B. 负例实测：路径 / 命令 / URL / 注入串 / 越界数字 必须全部被拒
  const neg = gateNegativeCases();
  const leaked = neg.filter((n) => n.code === null);
  checks.push({ id: 'B 负例全部被拒', ok: leaked.length === 0, detail: leaked.length ? `竟然放行: ${JSON.stringify(leaked)}` : `${neg.length}/${neg.length} 条被拒` });

  // C. 正例：枚举内的目标必须可用
  const pos = gatePositiveCases();
  const posOk = pos.every((p) => p.ok);
  checks.push({ id: 'C 正例可用', ok: posOk, detail: pos.map((p) => `${p.input.kind}:${p.input.id}→${p.ok ? 'ok' : 'FAIL'}`).join(', ') });

  // D. 宿主端 inject 合规（防 excalidraw 事故：宿主注客户端服务 ⇒ 整棵树加载失败）
  const inj = checkInject(sources['lib/index.js']);
  checks.push({ id: 'D 宿主端 inject 合规', ok: inj.ok, detail: inj.ok ? `inject=[${inj.inject.join(', ')}] ⊆ [${ALLOWED_INJECT.join(', ')}]，∩ 禁集 = ∅` : inj.reason });

  // E. 白名单冻结
  const fz = gateFreezeProof();
  const frozenOk = Object.values(fz).every((v) => v === true);
  checks.push({ id: 'E 白名单冻结', ok: frozenOk, detail: JSON.stringify(fz) });

  // F. dry-run 零变更实测（结构门上再加行为证据）
  const before = treeSnapshot(HERE);
  const plan = guardPlan();
  const after = treeSnapshot(HERE);
  const unchanged = JSON.stringify(before) === JSON.stringify(after);
  checks.push({ id: 'F dry-run 零变更', ok: unchanged && plan.tierNote.length > 0, detail: unchanged ? `插件目录 ${Object.keys(before).length} 个文件 mtime/size 在计划生成前后完全一致` : '检测到变更（见日志）' });

  const ok = checks.every((c) => c.ok);
  if (args.json) out(JSON.stringify({ ok, checks, gate: GATE_META }, null, 1));
  else {
    out(`lean4-check · 结构门自证（${GATE_META.principle}）`);
    for (const c of checks) out(`  ${c.ok ? C.ok : C.no} ${c.id} — ${c.detail}`);
    out(ok ? `\n${C.ok} 结构门生效：约束不可绕过（无入口 + 有证明）` : `\n${C.no} 门未生效，禁止交付`);
  }
  log(`lean4-check ok=${ok}`, { checks: checks.map((c) => `${c.id}:${c.ok}`) });
  process.exit(ok ? 0 : 1);
}

/* ------------------------------ --budget-check ----------------------------- */
/**
 * K2 纯决策核自检。**进程内跑**（本插件 ALLOWED_COMMANDS = []，连 `node --test` 都不能 spawn）。
 * 末尾打印 digest：两次独立运行若得同一 sha256 ⇒ 本核逐位确定（同 P4b「跨进程」的做法）。
 */
if (args['budget-check']) {
  const r = await runK2SelfTest();
  const dg = await digest();
  if (args.json) out(JSON.stringify({ ok: r.ok, total: r.total, failed: r.failed, bySuite: r.bySuite, digest: dg, failures: r.cases.filter((c) => !c.ok) }, null, 1));
  else {
    out(`K2 自检 · 纯决策核（预算表 + 守卫行为，零模型零会话）`);
    out(`  ${r.ok ? C.ok : C.no} 断言 ${r.total - r.failed}/${r.total} 通过（预算 ${r.bySuite.budget} · 守卫 ${r.bySuite.guard}）`);
    for (const c of r.cases.filter((x) => !x.ok)) out(`    ${C.no} ${c.suite}/${c.name}: got=${JSON.stringify(c.got)} want=${JSON.stringify(c.want)}`);
    out(`  逐位确定摘要: sha256=${dg.sha256} assertions=${dg.assertions}`);
  }
  log(`budget-check ok=${r.ok}`, { total: r.total, failed: r.failed, digest: dg.sha256 });
  process.exit(r.ok ? 0 : 1);
}

/* ---------------------------- --checkpoint-check --------------------------- */
/**
 * K3 纯决策核自检（检查点产出 + 有界丢弃阶梯 + 保证能减 + 增量账等价性）。
 * 与 --budget-check 同法：进程内跑，末尾打印 digest（跨进程同 sha ⇒ 逐位确定）。
 */
if (args['checkpoint-check']) {
  const r = runK3SelfTest();
  const dg = digestK3();
  const by = Object.entries(r.bySuite).map(([k, v]) => `${k} ${v}`).join(' · ');
  if (args.json) out(JSON.stringify({ ok: r.ok, total: r.total, failed: r.failed, bySuite: r.bySuite, digest: dg, failures: r.cases.filter((c) => !c.ok) }, null, 1));
  else {
    out(`K3 自检 · 纯决策核（检查点产出 + 有界阶梯 + 保证能减，零模型零会话）`);
    out(`  ${r.ok ? C.ok : C.no} 断言 ${r.total - r.failed}/${r.total} 通过（${by}）`);
    for (const c of r.cases.filter((x) => !x.ok)) out(`    ${C.no} ${c.suite}/${c.name}: got=${JSON.stringify(c.got)} want=${JSON.stringify(c.want)}`);
    out(`  逐位确定摘要: sha256=${dg.sha256} assertions=${dg.assertions}`);
  }
  log(`checkpoint-check ok=${r.ok}`, { total: r.total, failed: r.failed, digest: dg.sha256 });
  process.exit(r.ok ? 0 : 1);
}

/* ------------------------------ --recall-check ----------------------------- */
/**
 * K4 纯核自检（检查点账本 + 召回逐字相等 + DEGRADED/MISS 三态区分）。进程内跑。
 */
if (args['recall-check']) {
  const r = runK4SelfTest();
  const dg = digestK4();
  const by = Object.entries(r.bySuite).map(([k, v]) => `${k} ${v}`).join(' · ');
  if (args.json) out(JSON.stringify({ ok: r.ok, total: r.total, failed: r.failed, bySuite: r.bySuite, digest: dg, failures: r.cases.filter((c) => !c.ok) }, null, 1));
  else {
    out(`K4 自检 · 纯核（检查点账本 + 召回逐字相等，零模型零会话）`);
    out(`  ${r.ok ? C.ok : C.no} 断言 ${r.total - r.failed}/${r.total} 通过（${by}）`);
    for (const c of r.cases.filter((x) => !x.ok)) out(`    ${C.no} ${c.suite}/${c.name}: got=${JSON.stringify(c.got)} want=${JSON.stringify(c.want)}`);
    out(`  逐位确定摘要: sha256=${dg.sha256} assertions=${dg.assertions}`);
  }
  log(`recall-check ok=${r.ok}`, { total: r.total, failed: r.failed, digest: dg.sha256 });
  process.exit(r.ok ? 0 : 1);
}

/* ------------------------------- --calibration ----------------------------- */
/**
 * K5 负控 1 标定（立项书 §5，立论所系）：把「本核缩小地板」与「官方地板」摆在一起给出区间与逐点对照。
 * ★ 官方地板是**引用常量**（出处写在报告里），本核地板是**本核实算**——两者在报告里严格分开标注。
 */
if (args.calibration) {
  const r = calibrationReport();
  if (args.json) out(JSON.stringify(r, null, 1));
  else if (args.md) out(renderCalibration(r));
  else {
    out(`K5 负控 1 标定 · 缩小地板对照（纯粹、可复跑）`);
    out(`  官方地板（**引用实测常量**）: ${r.officialFloor.framedSummaryTokens} token`);
    out(`    出处 ${r.officialFloor.source}`);
    out(`    判据 ${r.officialFloor.judge}`);
    out(`  本核地板（**实算**，按粒度）:`);
    for (const row of r.rows) out(`    ${C.ok} 粒度 ${String(row.entryTokens).padStart(4)} -> 地板 ${String(row.ourFloorTokens ?? '—').padStart(6)} 检点 ${String(row.ourCheckpointAtFloor ?? '—').padStart(5)}  ${row.reason}`);
    out(`  最优 ${r.ourBestFloorTokens} / 最差 ${r.ourWorstFloorTokens} · 区间 [${r.band ? r.band.from : '—'}, ${r.band ? r.band.toExclusive : '—'}) 宽 ${r.band ? r.band.width : '—'}`);
    out(`  ★★ 崩溃点判据（被遮 ${r.atOfficialCrashPoint.shadowedTokens}）: ${r.atOfficialCrashPoint.ok ? C.ok : C.no} ${r.atOfficialCrashPoint.reason}`);
    out(`  ${/立论成立/.test(r.verdict) ? C.ok : C.no} ${r.verdict}`);
  }
  log(`calibration ok=${r.band ? !r.band.empty : false}`, { worst: r.ourWorstFloorTokens, official: r.officialFloor.framedSummaryTokens, atCrash: r.atOfficialCrashPoint.ok });
  process.exit(r.band && !r.band.empty && r.atOfficialCrashPoint.ok ? 0 : 1);
}

/* ----------------------------- --contract-check ---------------------------- */
/**
 * ★ 静态契约判据：**工具对外契约必须与实现状态一致**。
 *
 * 为什么机器化：本缺陷已出现**两次**（K2 复盘的 F5；本轮又是）。滞留的文案**读起来完全正常** ——
 * 它就是上一版的正确文案 ⇒ **靠人读不可能稳定发现**。
 *
 * 判据（逐条可核）：
 *   ① 工具描述里**不得**出现滞留表述（「尚未实现」「K1 骨架」等）——除非同时说明其真实状态；
 *   ② 每个声明了 coreStatus 的工具，其 module 必须**真实存在且非空**（防止"声称已实现"却没有文件）；
 *   ③ 文件头自述的阶段与 STAGE 常量不得背离（不许一个说 K2 一个说 K5）。
 */
if (args['contract-check']) {
  const idx = fs.readFileSync(path.join(HERE, 'lib/index.js'), 'utf8');
  const checks = [];

  const STALE = ['尚未实现', 'K1 骨架', 'K1：骨架'];
  const hits = STALE.filter((w) => idx.includes(w));

  checks.push({
    id: '① 无滞留表述',
    ok: hits.length === 0,
    detail: hits.length === 0
      ? `扫描 lib/index.js：${STALE.map((w) => '「' + w + '」').join(' ')} 命中 0 次`
      : `发现滞留表述 ${JSON.stringify(hits)} —— 文案停在旧阶段，而实现已前进`
  });

  // ② coreStatus 声明的模块必须真实存在且非空
  const mods = [...idx.matchAll(/module:\s*'([^']+)'/g)].map((m) => m[1]);
  const badMods = [];
  for (const rel of mods) {
    const abs = path.join(HERE, rel);
    try {
      const st = fs.statSync(abs);
      if (!st.isFile() || st.size === 0) badMods.push(rel + '(空或非文件)');
    } catch { badMods.push(rel + '(不存在)'); }
  }
  checks.push({
    id: '② 声称已实现的模块真实存在',
    ok: mods.length > 0 && badMods.length === 0,
    detail: mods.length === 0
      ? '未发现任何 coreStatus.module 声明（无法核"声称"与"实体"是否一致）'
      : (badMods.length ? `以下模块声称已实现却不存在/为空: ${JSON.stringify(badMods)}` : `${mods.length} 个模块均存在且非空: ${mods.join(', ')}`)
  });

  // ③ 文件头自述不得与 STAGE 背离
  const head = idx.slice(0, idx.indexOf('*/'));
  const stageInHead = (head.match(/K[1-9]/g) || []);
  const stageConst = (idx.match(/const STAGE = '([^']+)'/) || [])[1] || '';
  const stageNum = (stageConst.match(/K[1-9]/) || [''])[0];
  const headClaimsOld = stageInHead.length > 0 && stageNum && !head.includes(stageNum);
  checks.push({
    id: '③ 文件头自述与 STAGE 一致',
    ok: !headClaimsOld,
    detail: headClaimsOld
      ? `文件头只提 ${JSON.stringify([...new Set(stageInHead)])}，而 STAGE=${stageConst} ⇒ 自述滞后`
      : `STAGE=${stageConst}，文件头未与之背离`
  });

  const ok = checks.every((c) => c.ok);
  if (args.json) out(JSON.stringify({ ok, stsge: STAGE, checks }, null, 1));
  else {
    out(`contract-check · 工具对外契约与实现状态一致性`);
    for (const c of checks) out(`  ${c.ok ? C.ok : C.no} ${c.id} — ${c.detail}`);
    out(ok ? `\n${C.ok} 契约一致：模型读到的说明与实际实现相符` : `\n${C.no} 契约滞留，先修文案再交付`);
  }
  log(`contract-check ok=${ok}`, { checks: checks.length });
  process.exit(ok ? 0 : 1);
}

/* --------------------------------- -status -------------------------------- */
if (args.status) {
  const payload = {
    plugin: PLUGIN_NAME,
    version: VERSION,
    stage: 'K5-r006-7of10',
    implemented: false,
    invariants: ['I1 保证能减', 'I2 不摘要', 'I3 最新保活', 'I4 并存不独占', 'I5 可召回', 'I6 交接可续'],
    gate: { recallKinds: [...RECALL_KINDS], allowedCommands: [...ALLOWED_COMMANDS], allowedInject: [...ALLOWED_INJECT], forbiddenInject: [...FORBIDDEN_INJECT] },
    note: 'K2：守卫只测量、只记录，不做检查点、不替换表面；挂载（K6）是不可逆动作，由用户在独立试验会话内执行。'
  };
  out(args.json ? JSON.stringify(payload, null, 1) : `${PLUGIN_NAME} v${VERSION} · ${payload.stage}
  implemented=${payload.implemented}
  不变量: ${payload.invariants.join(' / ')}
  召回目标枚举: [${RECALL_KINDS.join(', ')}]
  零外部命令: ${C.ok} 允许集 = []（本插件不执行任何外部命令）
  ${payload.note}`);
  process.exit(0);
}

/* -------------------------------- -dry-run -------------------------------- */
if (args['dry-run']) {
  const plan = guardPlan();
  out(args.json ? JSON.stringify({ ok: true, dryRun: true, plan }, null, 1)
    : `[dry-run] 守卫计划（零外部变更）：\n${Object.entries(plan).map(([k, v]) => `  ${k}: ${Array.isArray(v) ? v.join(' | ') : v}`).join('\n')}`);
  process.exit(0);
}

out('用法错误: 需要 --status / --dry-run / --budget-check / --checkpoint-check / --recall-check / --calibration / --contract-check / --selfcheck / --lean4-check / --tool-version（或 --help）');
process.exit(2);
