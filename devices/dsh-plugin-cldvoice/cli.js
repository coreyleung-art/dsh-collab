#!/usr/bin/env node
// cli.js — cldvoice 治理入口（R006 ⑨ 补课，v0.6.1）：--tool-version / --selfcheck；未知旗标 exit 2。
import { readFileSync } from 'node:fs';
const pkg = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8'));
const args = process.argv.slice(2);
if (args.length === 0 || args.includes('--help')) {
  console.log('cldvoice CLI\n  --tool-version  版本号（package.json 单一来源）\n  --selfcheck     同步自检门 + CLI 专用真挂载冒烟');
  process.exit(args.includes('--help') ? 0 : 2);
}
if (args.includes('--tool-version')) { console.log(pkg.version); process.exit(0); }
if (args.includes('--selfcheck')) {
  const { runSelfCheck, runApplySmoke } = await import('./lib/selfcheck.js');
  const g = runSelfCheck('cldvoice', {
    requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
    requiredSymbols: ['appendFile', 'mkdir', 'homedir', 'join'],
  });
  console.log('  selfcheck: cldvoice → ' + (g.ok ? 'PASS' : 'FAIL'));
  if (g.notes.length) for (const n of g.notes) console.log('    note   : ' + n);
  if (g.missing.length) console.log('    missing: ' + g.missing.join(', '));
  const s = await runApplySmoke();
  console.log('  [' + s.state + '] 真挂载冒烟 — ' + s.detail);
  process.exit(g.ok && s.state !== 'fail' ? 0 : 1);
}
console.error('用法错误: 未知旗标 ' + args.join(' '));
process.exit(2);
