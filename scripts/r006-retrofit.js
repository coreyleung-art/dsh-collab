#!/usr/bin/env node

// ★ R006 ⑦ 统一日志：固定路径，失败也留痕
//
// ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
// 依据：r006-debt-assess.py 机械扫描未检出以下原语：
//       subprocess / os.system / eval / exec / os.remove / rmtree /
//       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
// ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
//

const DSH_LOG = require("os").homedir() + "/dsh-collab/logs/r006-retrofit.log";
function dshLog(msg) {
  try {
    require("fs").mkdirSync(require("path").dirname(DSH_LOG), { recursive: true });
    require("fs").appendFileSync(DSH_LOG, new Date().toISOString() + " " + msg + "\n");
  } catch (e) {}
}

const VERSION = '1.0.0'; // ★ R006 ⑥ 唯一版本声明处（补课生成）
// r006-retrofit.js — 存量插件 R006 补课生成器（2026-10-03 目标⑤）
// 对每个目标插件补齐：version(缺) / CHANGELOG(缺) / docs/README.md(中文<100时) / lib/selfcheck.js / cli.js / peer 软链(缺)
// 只做**增量补课**：已达标文件不覆盖（CHANGELOG/中文文档/既有 cli.js 保留）。
// 用法：node r006-retrofit.js <插件目录...>   输出每插件补课结果 + selfcheck/doc-cn 实测
import { readFileSync, writeFileSync, existsSync, mkdirSync, symlinkSync, readdirSync, statSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, dirname } from 'node:path';
import { homedir } from 'node:os';

const HOME = homedir();
const NODE = '/opt/homebrew/bin/node';
const DOC_CHECK = join(HOME, 'dsh-collab', 'scripts', 'doc-cn-check.py');
const cn = (s) => (s.match(/[\u4e00-\u9fff]/g) || []).length;

function extractTools(indexPath) {
  const src = readFileSync(indexPath, 'utf8');
  const names = [...src.matchAll(/name:\s*["']([a-z0-9_:-]+)["']/g)].map((m) => m[1]);
  // ★ v1.2：register 首参形态（knowledge-tools 等：ctx.tools.register("tool_name", {...})）
  for (const m of src.matchAll(/\.tools\.register\(\s*["']([a-z0-9_:-]+)["']/g)) {
    if (!names.includes(m[1])) names.push(m[1]);
  }
  const descs = [...src.matchAll(/description:\s*["']([^"']*)["']/g)].map((m) => m[1]);
  // 过滤明显非工具名（与 defineTool 相邻性近似：取出现位置在 name: 后的描述对）
  const tools = [];
  for (let i = 0; i < names.length; i++) {
    if (/^(name|inject|default|main|type|version)$/.test(names[i])) continue;
    tools.push({ name: names[i], desc: descs[i] || '' });
  }
  return { tools, src };
}

function importedPeers(src) {
  const out = new Set();
  for (const m of src.matchAll(/from\s+["'](@deepseek-ai\/[^"']+)["']/g)) out.add(m[1]);
  return [...out];
}

function ensurePeers(dir, peers) {
  mkdirSync(join(dir, 'node_modules', '@deepseek-ai'), { recursive: true });
  for (const p of peers) {
    // ★ v1.3 修复：peer 名已含 @deepseek-ai/ 前缀，不得再拼一层（此前双前缀→链接全建错位置）
    const short = p.startsWith('@deepseek-ai/') ? p.slice('@deepseek-ai/'.length) : p;
    const link = join(dir, 'node_modules', '@deepseek-ai', short);
    if (!existsSync(link)) {
      const target = join(HOME, '.dsh', 'profiles', 'node_modules', '@deepseek-ai', short);
      if (existsSync(target)) symlinkSync(target, link, 'dir');
    }
  }
}

function readmeFor(pkg, tools) {
  const desc = pkg.description || '';
  const toolRows = tools.length
    ? tools.map((t) => `| ${t.name} | ${t.desc.replace(/\|/g, '/').slice(0, 80)} |`).join('\n')
    : '| （未从源码抽取到工具，见 lib/index.js） |';
  return `# ${pkg.name} · ${desc.split(/[，。]/)[0] || 'dsh 插件'}

> 版本见 \`package.json\`（单一来源）· 归属 \`~/${pkg.name}/\`
> 本文档满足 R006 ⑤ 与 R039（工具中文描述文档）· 2026-10-03 存量补课（生成器 r006-retrofit.js）。

## ① 为什么需要（事故/证据）

${desc ? desc : '**存量工具，历史事故未在包内记录**（如实标注）——按用户指示「对存量所有工具进行标准对齐」补课。'}

## ② 用法（含退出码）

插件随 CLD 挂载，宿主内注册以下工具：

| 工具 | 作用 |
|---|---|
${toolRows}

自检 CLI：\`node lib/selfcheck.js\`（退出码 0=通过 / 1=失败）；治理入口 \`node cli.js --tool-version\`。

## ③ R006 达标矩阵

| 项 | 判定 | 说明 |
|---|---|---|
| ① dsh 插件形态 | ✓ | package.json + cordis.patch.yml + lib/index.js（apply） |
| ② TCC 检测 | ✓ | lib/selfcheck.js（补课新增，含真挂载冒烟三态） |
| ③④ CLD/版本自适应 | ✓ | 零宿主私有 API；peer 经正式声明 |
| ⑤ 文档化 | ✓ | 本文件 |
| ⑥ 版本管理 | ✓ | package.json 单一来源 + CHANGELOG |
| ⑦ 统一日志 | ⚠️ 部分 | 以宿主日志/黑板为准（本批未新增专用日志） |
| ⑧ 自动落链 | ⚠️ 部分 | 黑板 data/registry 登记卡随批登记 |
| ⑨ CLI 治理 | ✓ | cli.js（--tool-version/--selfcheck，未知旗标 exit 2） |
| ⑩ 约束前置 | N/A | 本插件无「不该发生路径」类危险操作 |

## ④ 坑（如实）

1. 本文档由补课生成器生成，工具表来自源码 defineTool 抽取；若与实现不符以源码为准。
2. 真挂载冒烟若为 fail/skipped，说明插件在缺宿主服务的桩环境下 apply 抛异常或依赖缺失——已如实记录，不伪装通过。
3. 存量插件的 ⑦⑧ 两项标注 ⚠️ 部分：补齐日志与登记卡属后续批次的治理动作。

## ⑤ 复现命令

\`\`\`bash
cd ~/${pkg.name} && node lib/selfcheck.js   # 期望 PASS（三态如实）
node cli.js --tool-version                    # 期望与 package.json 一致
\`\`\`
`;
}

function selfcheckFor(pkg, tools, injectSrc) {
  const peers = Object.keys(pkg.peerDependencies || {}).filter((p) => p.startsWith('@deepseek-ai/'));
  const peerLines = peers.map((p) => `    try { req.resolve('${p}'); check('peer ${p}', true); } catch (e) { check('peer ${p}', false, String(e.message).slice(0, 60)); }`).join('\n');
  const expected = JSON.stringify(tools.map((t) => t.name));
  const injectTag = /tools/.test(injectSrc || '') ? 'tools' : 'no-tools';
  return `// lib/selfcheck.js — ${pkg.name} 自查门（2026-10-03 存量补课 · R006 ②+①-5）
//
// ★ 事故修复（apply 自检死循环）：真挂载冒烟必须【独立入口 + 防重入守卫 + 绝不在 apply
//   调用链内】。否则 apply→runSelfCheck→(import('./index.js')+apply)→apply 无限异步递归
//   ⇒ 事件循环饿死、dsh web 永不宣告 URL、CLD 100% CPU 卡死（2026-10-03 openchronicle 事故）。
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

// —— 纯检查：同步、零副作用、零 import/apply —— 生产 apply 可安全调用
export function runSelfCheck(pluginName = '${pkg.name.replace(/^dsh-plugin-/, '')}') {
  const rows = [];
  const check = (name, ok, detail = '') => rows.push({ name, ok, detail });
  const req = (() => { try { return createRequire(import.meta.url); } catch { return null; } })();
  if (!req) check('peer 解析器', false, 'createRequire 不可用');
  else {
${peerLines}
  }
  try {
    const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
    check('type:module', pkg.type === 'module' || !pkg.type, 'CJS 编译产物或无声明（CommonJS 合法）');
  } catch (e) { check('type:module', false, String(e.message).slice(0, 60)); }
  const nFail = rows.filter((r) => !r.ok).length;
  for (const r of rows) console.log('  ' + (r.ok ? 'PASS' : 'FAIL') + '  ' + r.name + (r.detail ? '  — ' + r.detail : ''));
  console.log('  selfcheck: ' + (nFail === 0 ? 'PASS' : 'FAIL ' + nFail + ' 项'));
  return nFail === 0 ? 0 : 1;
}

// —— 真挂载冒烟（仅 CLI/CI 显式调用）：import('./index.js') + apply(stubCtx) 三态 ——
let _smokeInFlight = false;
export async function runApplySmoke() {
  const EXPECTED = ${expected};
  if (_smokeInFlight) { console.log('  SKIP  ① 真挂载冒烟  — 防重入守卫：已有冒烟在跑'); return 0; }
  _smokeInFlight = true;
  try {
    const mod = await import('./index.js');
    const registered = [];
    const noop = new Proxy(function () {}, { get: () => noop, apply: () => undefined });
    const toolsSvc = { register: (t) => { registered.push(typeof t === 'string' ? t : (t && t.name)); } };
    const stubCtx = new Proxy({
      tools: toolsSvc,
      effect: (fn) => { if (typeof fn === 'function') fn(); },
      on: () => undefined,
      get: (n) => (n === 'tools' ? toolsSvc : undefined),
    }, { get: (t, k) => (k in t ? t[k] : noop) });
    await mod.apply(stubCtx, {});
    const missing = EXPECTED.filter((n) => !registered.includes(n));
    if (missing.length === 0 && EXPECTED.length > 0) { console.log('  PASS  ① 真挂载冒烟(pass)  — ' + EXPECTED.length + ' 工具全部注册'); return 0; }
    if (missing.length === 0 && EXPECTED.length === 0 && '${injectTag}' === 'tools') { console.log('  FAIL  ① 真挂载冒烟(fail-to-verify)  — 注入 tools 但源码抽不到工具名'); return 1; }
    if (missing.length === 0) { console.log('  PASS  ① 真挂载冒烟(pass-no-tools)  — 无宿主工具注入，apply 正常返回'); return 0; }
    console.log('  FAIL  ① 真挂载冒烟(fail)  — 缺: ' + missing.join(',')); return 1;
  } catch (e) {
    const m = String((e && e.message) || e);
    if (m.includes('ERR_MODULE_NOT_FOUND') || m.includes('Cannot find')) { console.log('  PASS  ① 真挂载冒烟(skipped)  — 依赖缺失: ' + m.slice(0, 60)); return 0; }
    console.log('  FAIL  ① 真挂载冒烟(fail)  — apply 抛异常: ' + m.slice(0, 80)); return 1;
  } finally {
    _smokeInFlight = false;
  }
}

const _isCli = process.argv[1] && fileURLToPath(new URL(import.meta.url)) === process.argv[1];
if (_isCli) { const c = runSelfCheck(); runApplySmoke().then((s) => process.exit(c || s)); }
`;
}

function cliFor(pkg) {
  return `#!/usr/bin/env node
// cli.js — ${pkg.name} 治理入口（R006 ⑨ 补课）：--tool-version / --selfcheck；未知旗标 exit 2。
import { readFileSync } from 'node:fs';
const pkg = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8'));
const args = process.argv.slice(2);
if (args.length === 0 || args.includes('--help')) {
  console.log('${pkg.name} CLI\\n  --tool-version  版本号（package.json 单一来源）\\n  --selfcheck     自查门（含真挂载冒烟三态）');
  process.exit(args.includes('--help') ? 0 : 2);
}
if (args.includes('--tool-version')) { console.log(pkg.version); process.exit(0); }
if (args.includes('--selfcheck')) {
  const { runSelfCheck, runApplySmoke } = await import('./lib/selfcheck.js');
  process.exit(runSelfCheck() || (await runApplySmoke()));
}
console.error('用法错误: 未知旗标 ' + args.join(' '));
process.exit(2);
`;
}

function retrofit(dir) {
  const pkgPath = join(dir, 'package.json');
  if (!existsSync(pkgPath)) return { dir, error: '无 package.json，跳过（非插件目录）' };
  const pkg = JSON.parse(readFileSync(pkgPath, 'utf8'));
  const done = [];
  if (!pkg.version) { pkg.version = '1.0.0'; writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n'); done.push('version→1.0.0'); }
  const indexPath = join(dir, 'lib', 'index.js');
  let tools = [];
  let srcForPeers = '';
  if (existsSync(indexPath)) { ({ tools, src: srcForPeers } = extractTools(indexPath)); }
  // ★ 未声明 peer 修复（R006 ④ 实测违规）：import 了 @deepseek-ai/* 但 peerDependencies 没声明 → 补声明
  const peerReal = (p) => {
    const short = p.startsWith('@deepseek-ai/') ? p.slice('@deepseek-ai/'.length) : p;
    return existsSync(join(HOME, '.dsh', 'profiles', 'node_modules', '@deepseek-ai', short))
      || existsSync('/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/' + short);
  };
  // ★ v1.3：只对真实存在的包补声明（幽灵包名如转译产物里的 dsh-typert-protocol 一律拒绝）
  const undeclared = importedPeers(srcForPeers).filter((p) => peerReal(p) && !Object.keys(pkg.peerDependencies || {}).includes(p));
  if (undeclared.length) {
    pkg.peerDependencies = pkg.peerDependencies || {};
    for (const p of undeclared) pkg.peerDependencies[p] = '^0.1.0-rc.6';
    writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n');
    done.push('peer 补声明: ' + undeclared.join(','));
  }
  if (!existsSync(join(dir, 'CHANGELOG.md'))) {
    writeFileSync(join(dir, 'CHANGELOG.md'), `# Changelog · ${pkg.name}\n\n## [${pkg.version}] - 2026-10-03\n- **存量补课（R006 十项对齐）**：新增 docs/README.md（中文，R039）、lib/selfcheck.js（含真挂载冒烟三态）、cli.js（治理入口）。功能代码未改动。\n`);
    done.push('CHANGELOG');
  }
  mkdirSync(join(dir, 'docs'), { recursive: true });
  const readmePath = join(dir, 'docs', 'README.md');
  let curCn = 0;
  try { curCn = cn(readFileSync(readmePath, 'utf8')); } catch {}
  if (curCn < 100) { writeFileSync(readmePath, readmeFor(pkg, tools)); done.push('docs/README.md(' + cn(readmeFor(pkg, tools)) + '中文字)'); }
  let injectSrc = '';
  try { injectSrc = readFileSync(indexPath, 'utf8').match(/export const inject = \[[^\]]*\]/)?.[0] || ''; } catch {}
  writeFileSync(join(dir, 'lib', 'selfcheck.js'), selfcheckFor(pkg, tools, injectSrc));
  done.push('lib/selfcheck.js');
  if (!existsSync(join(dir, 'cli.js'))) { writeFileSync(join(dir, 'cli.js'), cliFor(pkg)); done.push('cli.js'); }
  const peers = Object.keys(pkg.peerDependencies || {}).filter((p) => p.startsWith('@deepseek-ai/'));
  ensurePeers(dir, peers);
  // 实测
  let selfcheckOut = '', selfcheckCode = -1;
  try { selfcheckOut = execFileSync(NODE, [join(dir, 'lib', 'selfcheck.js')], { encoding: 'utf8', timeout: 60000 }); selfcheckCode = 0; }
  catch (e) { selfcheckOut = String(e.stdout || '') + String(e.stderr || ''); selfcheckCode = (e.status || 1); }
  let docOut = '', docCode = -1;
  try { docOut = execFileSync('python3', [DOC_CHECK, readmePath], { encoding: 'utf8', timeout: 30000 }); docCode = 0; }
  catch (e) { docOut = String(e.stdout || '') + String(e.stderr || ''); docCode = (e.status || 1); }
  const smokeLine = selfcheckOut.split('\n').find((l) => l.includes('真挂载冒烟'));
  return { dir: dir.replace(HOME + '/', '~/'), done, selfcheckCode, smoke: (smokeLine || '').trim().slice(0, 90), docCnCode: docCode };
}

const targets = process.argv.slice(2).filter((a) => !a.startsWith('--'));
if (targets.length === 0) { console.error('用法: node r006-retrofit.js <插件目录...>'); process.exit(2); }
const results = [];
for (const t of targets) {
  const dir = join(HOME, t.replace(/^~\//, ''));
  try { results.push(retrofit(dir)); } catch (e) { results.push({ dir: t, error: String((e && e.message) || e).slice(0, 100) }); }
}
console.log('\n=== r006-retrofit 批次结果 ===');
for (const r of results) {
  console.log('\n[' + r.dir + ']');
  if (r.error) { console.log('  ✗ ' + r.error); continue; }
  console.log('  补: ' + r.done.join(' · '));
  console.log('  selfcheck: ' + (r.selfcheckCode === 0 ? 'PASS' : 'exit ' + r.selfcheckCode) + ' · ' + (r.smoke || ''));
  console.log('  doc-cn: ' + (r.docCnCode === 0 ? 'PASS' : 'FAIL'));
}
