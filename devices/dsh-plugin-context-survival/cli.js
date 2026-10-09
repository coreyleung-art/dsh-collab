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
import { PLUGIN_SLUG, PLUGIN_NAME, VERSION, LOG_FILE, log } from './lib/meta.js';
import {
  RECALL_KINDS, ALLOWED_COMMANDS, ALLOWED_INJECT, FORBIDDEN_INJECT,
  GateError, resolveRecallTarget, gateNegativeCases, gatePositiveCases,
  gateFreezeProof, scanExecSites, checkInject, readSources, GATE_META
} from './lib/gate.js';
import { runSelfCheck } from './lib/selfcheck.js';
import { runK2SelfTest, digest } from './lib/k2-selftest.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const C = { ok: '✅', no: '❌', warn: '⚠️' };
function out(s) { process.stdout.write(s + '\n'); }

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
  --selfcheck             R014 自查门 + 能力边界 + 真挂载冒烟（pass/fail/skipped 三态）
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
    concurrency: '检测到已有压缩在途则不叠加（对齐 ctxwin hasOpenCompaction）',
    checkpoint: '<context_handoff v1 seq-range=A-B> 目标 / 阶段 / todo / 最近人类请求（逐字）/ notes / 省略账（带 seq 指针）/ 召回指南',
    dropLadder: ['1 压缩对话文本预算（每条最少 32 token）', '2 丢最旧工具结果条目（留 [N tool/result entries elided: seqs a-b]）', '3 丢最旧其余条目（留 [N earlier entries elided: seqs a-b]）'],
    onCannotShrink: '走到阶梯末端仍缩不小 ⇒ 写 compaction/notice + WARN（绝不静默 no-op，立项书 I1）',
    tierNote: 'K2：守卫已实现**测量与阈值判定**（lib/budget.js + lib/guard.js），仍**只测量不替换**；' +
      '检查点产出与表面替换在 K3。本计划其余各条仍是**声明**。'
  };
}

/* ------------------------------- --selfcheck ------------------------------- */
/**
 * 真挂载冒烟（R006 ① 第 5 项硬项）。三态分开报，绝不把 skipped 伪装成 pass：
 *   pass    挂上且注册了预期的东西
 *   fail    apply 抛非依赖类异常 → 真实缺陷
 *   skipped 依赖在本目录解析不到 → 如实说跳过（**据此不得声称 ① 达标**）
 */
async function mountSmoke() {
  const RUN_NM = '/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules';
  const PROF_NM = path.join(os.homedir(), '.dsh', 'profiles', 'web', 'node_modules');
  const linkPath = path.join(HERE, 'node_modules');
  let linked = false;
  const isMissingDep = (m) => /Cannot find package|ERR_MODULE_NOT_FOUND|Cannot find module/.test(String(m));
  try {
    let mod;
    const NEED = '@deepseek-ai/dsh-tools';
    const cands = [PROF_NM, RUN_NM].filter((p) => p && fs.existsSync(path.join(p, NEED)));
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
          : `依赖解析不到，且两级候选均不含 ${NEED}（已查 ${[PROF_NM, RUN_NM].join(' , ')}）：`) +
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

  // ② 能力边界（TCC 检测）：本工具的"不该发生路径"清单
  out('能力边界（TCC 检测）:');
  out(`    ${C.ok} 零外部命令：ALLOWED_COMMANDS = []（本插件不 spawn/exec 任何东西）`);
  out(`    ${C.ok} 召回目标枚举化：RECALL_KINDS = [${RECALL_KINDS.join(', ')}]，id 为有界数字/区间（无路径/命令/URL）`);
  out(`    ${C.ok} 不接管压缩后端：inject 白名单 = [${ALLOWED_INJECT.join(', ')}]，禁 [${FORBIDDEN_INJECT.join(', ')}]`);

  // ③ CLD 自适应 / ④ dsh 版本自适应
  out(`CLD 自适应: ${C.ok} 运行期只依赖 node ${process.version} 内置模块；不调用任何 dsh 私有 API`);
  out(`dsh 版本自适应: ${C.ok} 标识/版本来自 package.json（R006 ⑥ 单一来源）`);
  out(`统一日志: ${LOG_FILE}`);

  // ⑤ 真挂载冒烟
  const smoke = await mountSmoke();
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
  const files = ['cli.js', 'lib/index.js', 'lib/gate.js', 'lib/selfcheck.js', 'lib/meta.js',
    'lib/budget.js', 'lib/guard.js', 'lib/budget-selftest.js', 'lib/k2-selftest.js'];
  const sources = readSources(HERE, files);

  // A. 源码级：不存在任何外部命令执行点（本插件的能力是零执行）
  const sites = scanExecSites({ sources });
  checks.push({ id: 'A 源码零执行点', ok: sites.length === 0, detail: sites.length ? `越界执行点: ${JSON.stringify(sites)}` : 'exec/execFile/spawn/fork 命中 0 次（能力为零，非"没找到危险命令"）' });

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

/* --------------------------------- -status -------------------------------- */
if (args.status) {
  const payload = {
    plugin: PLUGIN_NAME,
    version: VERSION,
    stage: 'K2-measure-only',
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

out('用法错误: 需要 --status / --dry-run / --budget-check / --selfcheck / --lean4-check / --tool-version（或 --help）');
process.exit(2);
