#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { STAGES, HUMAN_GATED, GateError } from './lib/gate.js';
import { runSelfCheck } from './lib/selfcheck.js';
import { mountSmoke } from './lib/smoke.js';
import { runPipeline, status } from './lib/run.js';
import { log, logPath } from './lib/logger.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '../..');           // ~/dsh-collab
const PKG = JSON.parse(fs.readFileSync(path.join(__dirname, 'package.json'), 'utf8'));

// ⑨ 严格参数解析：未知旗标 → exit 2
const KNOWN = new Set(['--selfcheck','--lean4-check','--tool-version','--help','--dry-run','--json',
                       'run','status','--date','--upto','--only','--workdir']);
const argv = process.argv.slice(2);
for (const a of argv) {
  if (a.startsWith('--') && !KNOWN.has(a)) {
    console.error(`未知旗标：${a}\n`); usage(2);
  }
}
const has = (k) => argv.includes(k);
const val = (k, d) => { const i = argv.indexOf(k); return i >= 0 && argv[i+1] ? argv[i+1] : d; };

function usage(code = 0) {
  console.log(`dsh-plugin-reflect v${PKG.version} · 每日反思流水线编排器

用法：
  reflect run [--upto <stage>] [--only <stage,...>] [--date YYYY-MM-DD] [--dry-run] [--json]
  reflect status [--date YYYY-MM-DD] [--json]
  reflect --selfcheck | --lean4-check | --tool-version | --help

环节（冻结枚举，无第五个）：
  ${STAGES.map(s => HUMAN_GATED.includes(s) ? s + '（需人裁，不自动跑）' : s).join(' · ')}

退出码：0 成功 · 1 失败/门失效 · 2 用法或 IO 错误`);
  process.exit(code);
}

if (has('--help') || argv.length === 0) usage(0);
if (has('--tool-version')) { console.log(PKG.version); process.exit(0); }   // ⑥ 从 package.json 读，不硬编码

if (has('--selfcheck')) {
  const sc = runSelfCheck(ROOT);
  console.log(`== dsh-plugin-reflect 自查 ==`);
  [...sc.capability, ...sc.mustNot, ...sc.deps].forEach(l => console.log(l));
  if (sc.warnings.length) { console.log('\n提示：'); sc.warnings.forEach(w => console.log('  · ' + w)); }
  log({ action: 'selfcheck', ok: sc.ok, missing: sc.missing.length });
  // ★ R006 v3.1.0 ① 第 5 项：真挂载冒烟（三态 pass/fail/skipped，绝不把 skipped 写成 pass）
  const smoke = await mountSmoke({ baseDir: __dirname, indexRel: 'lib/index.js', config: {} });
  const sm = { pass: '✅ 挂载通过', fail: '❌ 挂不上（真实缺陷）', skipped: '⊘ 已跳过（如实说明）' }[smoke.state] || smoke.state;
  console.log(`【⑤ 真挂载冒烟】${sm}`);
  if (smoke.state === 'pass') console.log(`  · 注册工具: ${smoke.tools.join(', ')}（effect ${smoke.effects} 个）`);
  else if (smoke.state === 'skipped') console.log(`  · 原因: ${smoke.reason}`);
  else console.log(`  · ${smoke.stage}: ${smoke.error}`);
  log({ action: 'mount-smoke', state: smoke.state });
  process.exit(smoke.state === 'fail' ? 1 : (sc.ok ? 0 : 1));
}

if (has('--lean4-check')) {
  const { runLean4Check } = await import('./lib/lean4.js');
  const r = runLean4Check(ROOT);
  console.log('== --lean4-check 六项 ==');
  r.items.forEach(it => console.log(`  ${it.pass ? '✅' : '❌'} ${it.id} ${it.name} — ${it.detail}`));
  console.log(`\n结论：${r.pass ? '六项全绿，门成立' : '有未通过项，门不成立'}`);
  log({ action: 'lean4-check', ok: r.pass });
  process.exit(r.pass ? 0 : 1);
}

const date = val('--date', new Date().toISOString().slice(0, 10));
const workdir = val('--workdir', '~/dsh-collab/data/reflect');
const json = has('--json');
const dryRun = has('--dry-run');

if (argv[0] === 'status') {
  const st = status(date, workdir);
  if (json) console.log(JSON.stringify({ date, stages: st }, null, 2));
  else {
    console.log(`== 反思流水线进度 · ${date} ==`);
    st.forEach(s => {
      const mark = s.human_gated ? '🔒' : (s.done ? '✅' : '⏳');
      console.log(`  ${mark} ${s.stage.padEnd(11)} ${s.done ? '已完成' : (s.human_gated ? '需人裁' : '待跑')}  ${s.plugin}`);
    });
  }
  process.exit(0);
}

if (argv[0] === 'run') {
  try {
    const only = val('--only', '');
    const results = runPipeline({
      root: ROOT, date,
      workdir,
      upto: val('--upto', undefined),
      only: only ? only.split(',').map(s => s.trim()).filter(Boolean) : null,
      dryRun,
      autoRunEnroll: false,   // ★ 编排器永不自动入册
    });
    if (json) console.log(JSON.stringify({ date, dry_run: dryRun, results }, null, 2));
    else {
      console.log(`== 反思流水线 · ${date}${dryRun ? '（dry-run）' : ''} ==`);
      results.forEach(r => {
        const mark = r.aborted ? '⛔' : (r.skipped ? '⏭' : (r.ok ? '✅' : '❌'));
        console.log(`  ${mark} ${String(r.stage).padEnd(11)} ${r.action}`);
        if (r.dry_run) console.log(`      ${r.action}`);
      });
      console.log(`\n日志：${logPath()}`);
    }
    const failed = results.some(r => r.ok === false || r.aborted);
    process.exit(failed ? 1 : 0);
  } catch (e) {
    if (e instanceof GateError) { console.error(`门拒绝：${e.message}`); log({ action: 'gate-reject', msg: e.message }); process.exit(1); }
    console.error(`错误：${e.message}`); log({ action: 'error', msg: e.message }); process.exit(1);
  }
}

usage(2);
