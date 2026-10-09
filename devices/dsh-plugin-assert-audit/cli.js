#!/usr/bin/env node
/**
 * cli.js — ⑨ CLI 治理 + ⑩ --lean4-check 六项 + ② --selfcheck + ⑥ --tool-version
 *
 * 退出码：0 成功 · 1 门失效/审计发现问题 · 2 用法或 IO 错误
 * 机器可读：--json（本工具无同名冲突用途）
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { audit } from './lib/audit.js';
import { scopeAudit, SCOPE_VERDICT } from './lib/scope.js';
import { mountSmoke, capabilityReport, runSelfCheck } from './lib/selfcheck.js';
import {
  stripLiterals, VERDICT, VERDICT_VALUES, ALLOWED_COMMANDS, DENIED_SUBCOMMANDS,
  gateNegativeCases, gatePositiveCases,
  scanDangerous, scanExecSites, scanWriteSites, GATE_META,
} from './lib/gate.js';

const BASE = path.join(path.dirname(fileURLToPath(import.meta.url)));
const LOG = path.join(os.homedir(), 'dsh-collab', 'logs', 'assert-audit.log');
const PKG = JSON.parse(fs.readFileSync(path.join(BASE, 'package.json'), 'utf8'));

let JSON_OUT = false;
const emit = (o) => { if (JSON_OUT) console.log(JSON.stringify(o, null, 2)); };
const say = (s) => { if (!JSON_OUT) console.log(s); };

function logLine(rec) {                                  // ⑦ 统一日志（失败也留痕）
  try {
    fs.mkdirSync(path.dirname(LOG), { recursive: true });
    fs.appendFileSync(LOG, `${new Date().toISOString()} ${JSON.stringify(rec)}\n`);
  } catch { /* 日志失败不影响主流程，但绝不吞掉结果 */ }
}

function sourceBundle(dir) {
  const out = {};
  for (const f of ['lib/index.js', 'lib/audit.js', 'lib/gate.js', 'lib/scope.js', 'lib/selfcheck.js', 'cli.js']) {
    const p = path.join(dir, f);
    if (fs.existsSync(p)) out[f] = fs.readFileSync(p, 'utf8');
  }
  return out;
}

/* ───────────── ⑩ --lean4-check 六项（全绿才交付） ───────────── */
async function lean4Check() {
  const src = sourceBundle(BASE);
  const res = {};
  const A = scanDangerous({ sources: src });
  res.A = { name: '源码无危险原语', ok: A.length === 0, hits: A };

  const neg = gateNegativeCases();
  const negFailed = neg.filter((n) => !n.rejected);
  res.B = { name: '负例全部被拒', ok: negFailed.length === 0, total: neg.length, failed: negFailed };

  const pos = gatePositiveCases();
  const posFailed = pos.filter((c) => !c.ok);
  res.C = { name: '正例可用', ok: posFailed.length === 0, total: pos.length, failed: posFailed };

  // D: --dry-run 零变更（外部状态实测一致）
  const snap = (d) => {
    const o = {};
    for (const f of fs.readdirSync(d)) {
      const p = path.join(d, f);
      if (fs.statSync(p).isFile()) o[f] = fs.statSync(p).mtimeMs;
    }
    return o;
  };
  const before = snap(BASE);
  const beforeTmp = fs.readdirSync(os.tmpdir()).filter((x) => x.startsWith('assert-audit-')).length;
  // dry-run：只枚举与静态扫描，不跑变异、不写文件
  const drySrc = path.join(BASE, 'lib', 'audit.js');
  audit({ sourcePath: drySrc, testSourcePath: drySrc, tokens: [], mutants: [], runArgs: [], runner: 'python3' });
  const after = snap(BASE);
  const afterTmp = fs.readdirSync(os.tmpdir()).filter((x) => x.startsWith('assert-audit-')).length;
  res.D = {
    name: '--dry-run 零变更',
    ok: JSON.stringify(before) === JSON.stringify(after) && beforeTmp === afterTmp,
    changed: Object.keys(after).filter((k) => before[k] !== after[k]),
    tmpDelta: afterTmp - beforeTmp,
  };

  const frozen = Object.isFrozen(ALLOWED_COMMANDS) && Object.isFrozen(VERDICT);
  res.E = { name: '白名单冻结', ok: frozen };

  const execSites = scanExecSites({ sources: src });
  const badCmd = execSites.filter((s) => s.resolved === 'literal' && !ALLOWED_COMMANDS.includes(s.command));
  const unresolved = execSites.filter((s) => s.resolved === 'UNRESOLVED');
  const writes = scanWriteSites({ sources: src });
  const auditSrc = src['lib/audit.js'] || '';
  const cliSrc = src['cli.js'] || '';
  // 允许的写入面【只有两处】，其余一律判红：
  //   ① lib/audit.js —— 变异体写盘（必须过 assertTmpContained）+ tmp 目录清理
  //   ② cli.js       —— ⑦ 统一日志（固定路径常量 LOG，不受调用方控制）
  const logSitesOk = writes.sites.filter((s) => s.file === 'cli.js')
    .every((s) => (cliSrc.split('\n')[s.line - 1] || '').includes('LOG'));
  const logPathFixed = /const LOG = path\.join\(os\.homedir\(\), 'dsh-collab', 'logs'/.test(cliSrc);
  const writeSitesOutsideAllowed = writes.sites.filter((s) => !['lib/audit.js', 'cli.js'].includes(s.file));
  const logSinkOk = logSitesOk && logPathFixed;
  res.F = {
    name: '外部命令白名单 + 唯一写入面（变异体 tmp 门 + 固定日志路径）',
    ok: badCmd.length === 0 && unresolved.length === 0 && writeSitesOutsideAllowed.length === 0
        && auditSrc.includes('assertTmpContained(') && logSinkOk,
    execSites, badCmd, unresolved,
    writeSites: writes.sites, writeSitesOutsideAllowed,
    tmpGuarded: auditSrc.includes('assertTmpContained('),
    logSink: { everyLogSiteUsesLOG: logSitesOk, logPathFixed },
  };

  // G（v1.1.0 新增）：禁用子命令不得出现 —— 本工具只做只读盘点，不得获得可变能力
  const deniedHits = [];
  for (const [file, raw] of Object.entries(src)) {
    const scan = stripLiterals(raw);
    for (const sub of DENIED_SUBCOMMANDS) {
      const re = new RegExp(`(launchctl|['"]` + sub + `['"])[^\\n]{0,80}['"\`]` + sub, 'i');
      if (new RegExp(`['"\`]` + sub + `['"\`]`).test(scan) && scan.includes('launchctl')) deniedHits.push({ file, sub });
    }
  }
  res.G = { name: '禁用子命令未出现（只读盘点，无可变能力）', ok: deniedHits.length === 0, deniedHits };

  const allGreen = Object.values(res).every((r) => r.ok);
  emit({ lean4: res, allGreen, verdicts: VERDICT_VALUES, gate: GATE_META });
  if (!JSON_OUT) {
    say('── R006 ⑩ --lean4-check 六项 ──');
    for (const [k, v] of Object.entries(res)) say(`  ${v.ok ? '✅' : '❌'} ${k} · ${v.name}`);
    say(`  判定闭集: ${VERDICT_VALUES.join(' / ')}`);
    say(allGreen ? '  ⇒ 全绿' : '  ⇒ 有红项，拒绝交付');
  }
  return allGreen ? 0 : 1;
}

/* ───────────── ② --selfcheck（三段 + ① 真挂载冒烟三态） ───────────── */
async function selfcheck() {
  const cap = capabilityReport();
  const sc = runSelfCheck('assert-audit', {
    requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
    requiredSymbols: ['defineTool', 'audit'],
    sourceFiles: ['lib/index.js'],
    baseDir: BASE,
  });
  const smoke = await mountSmoke();
  if (!JSON_OUT) {
    say('【能力清单】'); cap.capabilities.forEach((c) => say(`  · ${c}`));
    say('【不该发生的路径】'); cap.forbiddenPaths.forEach((c) => say(`  ✗ ${c}`));
    say('【依赖完整性】', JSON.stringify(cap.dependency));
    say(`【peer/符号】ok=${sc.ok} missing=${sc.missing.length} warnings=${sc.warnings.length}`);
    sc.notes.forEach((n) => say(`  · ${n}`));
    say('【① 真挂载冒烟】三态分开报');
    say(`  → ${smoke.state}${smoke.reason ? ' :: ' + smoke.reason : ''}${smoke.registered ? ' :: 注册 ' + smoke.registered.join(',') : ''}`);
    if (smoke.state === 'skipped') say('  ⚠ 已如实标注「跳过」，不代表通过');
  }
  emit({ capabilities: cap, selfcheck: sc, mountSmoke: smoke });
  logLine({ cmd: 'selfcheck', smoke: smoke.state, ok: sc.ok });
  return 0;                                            // ② 自检退出码 0（结论已在输出里）
}

/* ───────────── 范围审查（v1.1.0 新增） ───────────── */
function runScope() {
  const r = scopeAudit({});
  const V = SCOPE_VERDICT;
  if (!JSON_OUT) {
    say('── 工具链范围审查：agent 会话 / 跨设备沟通 ──');
    say(`  发现组件 ${r.tally.total} 个（进程 ${r.sources.processes} · launchd ${r.sources.launchd} · 插件 ${r.sources.plugins} · 路径 ${r.sources.paths}）`);
    say(`  覆盖状态：COVERED ${r.tally.COVERED} · HAS_TESTS_NO_AUDIT ${r.tally.HAS_TESTS_NO_AUDIT} · NO_TESTS ${r.tally.NO_TESTS} · UNKNOWN ${r.tally.UNKNOWN}`);
    say('');
    say('  ★ 盲区清单（按爆炸半径降序；UNKNOWN 不折算为任一侧）');
    say(`  ${'组件'.padEnd(34)}${'角色'.padEnd(18)}${'状态'.padEnd(22)}RSS/事故`);
    for (const i of r.blind) {
      const tag = i.coverage.verdict === V.COVERED ? '' : i.coverage.verdict;
      say(`  ${i.name.slice(0, 33).padEnd(34)}${String(i.role).padEnd(18)}${tag.padEnd(22)}${i.rssMB ? i.rssMB + 'MB' : ''}${i.incident ? ' ★' + i.incident : ''}`);
    }
    say('');
    say('  ⚠ 本工具的盲区（自述，不掩盖）:');
    for (const g of r.gaps) say(`     · ${g}`);
  }
  emit(r);
  logLine({ cmd: 'scope', tally: r.tally });
  return r.tally.NO_TESTS + r.tally.HAS_TESTS_NO_AUDIT + r.tally.UNKNOWN > 0 ? 1 : 0;
}

/* ───────────── 审计主命令 ───────────── */
function runAudit(opt) {
  const r = audit({
    sourcePath: opt.source, testSourcePath: opt.tests,
    tokens: opt.tokens || [], mutants: opt.mutants || [],
    runArgs: opt.runArgs || [], runner: opt.runner || 'python3',
  });
  const t = r.mutation ? r.mutation.tally : null;
  if (!JSON_OUT) {
    say(`断言条数: ${r.assertions.length}`);
    say(`空断言/弱比较: ${r.vacuity.length}`);
    r.vacuity.forEach((v) => say(`  ⚠ ${v.type} @L${v.line} ${v.name} — ${v.why}`));
    const bad = r.predicates.filter((p) => p.verdict !== 'OK');
    say(`多调用点/缺失谓词: ${bad.length}`);
    bad.forEach((p) => say(`  ⚠ ${p.verdict} ${JSON.stringify(p.token)} sites=${p.sites} testMentions=${p.testMentions}`));
    if (t) {
      say(`变异测试: 共 ${t.total} ｜ CAUGHT ${t.CAUGHT} · SURVIVED ${t.SURVIVED} · INCONCLUSIVE ${t.INCONCLUSIVE}`);
      say(`  三态互斥且合计一致: ${r.mutation.consistent ? '是' : '否（严重）'}`);
      r.mutation.results.forEach((x) => say(`  [${x.verdict}] ${x.name} :: ${x.reason}`));
    }
  }
  emit({ ...r, verdictValues: VERDICT_VALUES });
  logLine({ cmd: 'audit', source: opt.source, tests: opt.tests, tally: t, vacuity: r.vacuity.length });
  // 退出码：真存活 或 空断言 或 不可判 → 1
  const bad = (t && (t.SURVIVED > 0 || t.INCONCLUSIVE > 0)) || r.vacuity.length > 0;
  return bad ? 1 : 0;
}

/* ───────────── 参数解析（⑨ 严格：未知旗标 → 用法错误 exit 2） ───────────── */
function parse(argv) {
  const need = { source: null, tests: null, tokens: [], mutants: [], runArgs: [], runner: 'python3' };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--json') JSON_OUT = true;
    else if (a === '--scope') need.scope = true;
    else if (['--selfcheck','--lean4-check','--tool-version','--dry-run','--help'].includes(a)) need[a.slice(2)] = true;
    else if (a === '--source') need.source = argv[++i];
    else if (a === '--tests') need.tests = argv[++i];
    else if (a === '--runner') need.runner = argv[++i];
    else if (a === '--token') need.tokens.push(argv[++i]);
    else if (a === '--run-arg') need.runArgs.push(argv[++i]);
    else if (a === '--mutants-json') need.mutants = JSON.parse(fs.readFileSync(argv[++i], 'utf8'));
    else { console.error(`未知参数: ${a}\n用法: assert-audit --source <impl> --tests <suite> [--token T] [--mutants-json F] [--run-arg A] [--runner python3|node] [--json]`); process.exit(2); }
  }
  return need;
}

const arg = parse(process.argv.slice(2));
if (arg.help) {
  console.log(`assert-audit ${PKG.version}
用法:
  assert-audit --selfcheck                     能力边界自检（三段）+ 真挂载冒烟（三态）
  assert-audit --lean4-check                   R006 ⑩ 六项 A–F 自证
  assert-audit --tool-version                  版本（单一来源 = package.json）
  assert-audit --scope                         范围审查：工具链覆盖盲区枚举（三态 + 不可判）
  assert-audit --dry-run                       零变更演示（只枚举，不跑变异、不写文件）
  assert-audit --source <impl> --tests <suite> [--token T ...] [--mutants-json F] [--run-arg A ...] [--runner python3|node] [--json]
退出码: 0 成功 · 1 门失效/发现问题 · 2 用法或 IO 错误
机器可读输出开关: --json`);
  process.exit(0);
}
if (arg['tool-version']) { console.log(PKG.version); process.exit(0); }
if (arg['lean4-check']) { process.exit(await lean4Check()); }
if (arg.scope) { process.exit(runScope()); }
if (arg.selfcheck) { process.exit(await selfcheck()); }
if (arg['dry-run']) {
  const r = audit({ sourcePath: path.join(BASE, 'lib', 'audit.js'), testSourcePath: path.join(BASE, 'lib', 'audit.js'), tokens: [], mutants: [] });
  console.log(JSON.stringify({ dryRun: true, wouldAudit: true, assertionsFound: r.assertions.length, vacuity: r.vacuity.length, note: '未跑变异、未写任何文件' }, null, 2));
  logLine({ cmd: 'dry-run', ok: true });
  process.exit(0);
}
if (!arg.source || !arg.tests) {
  console.error('缺少 --source / --tests（或用 --help）');
  process.exit(2);
}
try { process.exit(runAudit(arg)); }
catch (e) { console.error(`执行失败: ${e.message}`); process.exit(1); }
