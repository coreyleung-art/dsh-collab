// 1.0.5 三条改动的最小可核测试：① 分项计数 ② partial 不并入 pass ③ 未测面机器可读
// 断言结构不变量，不硬编码具体条数（条数会随本机 dsh-plugin-* 目录变化而漂）。
import { pathToFileURL } from 'node:url'
import { stat as fstat, readFile, readdir, writeFile, mkdir } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'

const PKG = path.dirname(path.dirname(new URL(import.meta.url).pathname))
const expand = (p) => (String(p) === '~' ? os.homedir() : String(p).startsWith('~/') ? path.join(os.homedir(), String(p).slice(2)) : String(p))

const fsService = {
  async resolve(p) { return { targetKey: path.resolve(expand(p)), displayPath: String(p) } },
  processPath(t) { return t.targetKey },
  fileUrl(t) { return pathToFileURL(t.targetKey).href },
  contains(a, b) { const r = path.relative(a.targetKey, b.targetKey); return r === '' || (!r.startsWith('..') && !path.isAbsolute(r)) },
  async stat(t) { try { const s = await fstat(t.targetKey); return { version: String(s.mtimeMs), type: s.isDirectory() ? 'directory' : s.isFile() ? 'file' : 'other', size: s.size } } catch { return undefined } },
  async readText(t) { return await readFile(t.targetKey, 'utf8') },
  async listDir(t) { const n = await readdir(t.targetKey, { withFileTypes: true }); return n.sort((a, b) => (a.name < b.name ? -1 : 1)).map((e) => ({ name: e.name, type: e.isDirectory() ? 'directory' : e.isFile() ? 'file' : 'other', target: { targetKey: path.join(t.targetKey, e.name), displayPath: e.name } })) },
  async writeText(t, c) { await mkdir(path.dirname(t.targetKey), { recursive: true }); await writeFile(t.targetKey, c, 'utf8'); return { operation: 'create', version: 'v' } },
}

// ── 造三个夹具：合规范（期望 pass）· 无静态工具声明（期望 partial）· 缺前缀（期望 fail）──
const base = path.join(os.tmpdir(), 'pstd-105-fixture-' + process.pid)
await mkdir(base, { recursive: true })

async function makeDir(name, { tools = null, overrideName = null } = {}) {
  const dirName = overrideName || 'dsh-plugin-' + name
  const d = path.join(base, dirName)
  await mkdir(d, { recursive: true })
  await writeFile(path.join(d, 'package.json'), JSON.stringify({ name: dirName, version: '0.0.1', type: 'module', main: 'lib/index.js' }, null, 2), 'utf8')
  await writeFile(path.join(d, 'cordis.patch.yml'), 'plugins:\n  - insert:\n      id: ' + name + '\n      name: ' + dirName + '\n', 'utf8')
  await mkdir(path.join(d, 'lib'), { recursive: true })
  const body = tools === null
    ? 'export function apply(ctx) { /* 动态注册，静态不可见 */ }\n'
    : 'export function apply(ctx) {\n' + tools.map((t) => '  ctx.tools.register({ name: ' + JSON.stringify(t) + ', description: "x", parameters: {}, execute: async () => ({ ok: true }) })\n').join('') + '}\n'
  await writeFile(path.join(d, 'lib/index.js'), body, 'utf8')
}

await makeDir('alphafix', { tools: ['alpha_ping'] })   // 期望 pass
await makeDir('betafix')                                // 期望 partial（N4 unverified）
await makeDir('gammafix', { overrideName: 'dsh_plugin-gammafix' })  // 前缀变体：不进总体，须出现在 suspectsExcluded

const mod = await import(pathToFileURL(path.join(PKG, 'lib/index.js')).href)
const cap = []
const ctx = new Proxy({
  tools: { register: (d) => { cap.push(d); return () => {} }, schemas: () => [] },
  on: () => () => {}, effect: (cb) => { try { const d = cb(); return typeof d === 'function' ? d : () => {} } catch { return () => {} } },
  get: (n) => ({ fs: fsService, tools: { schemas: () => [] } })[n],
}, { get: (t, k) => (k in t ? t[k] : () => () => {}) })
await mod.apply(ctx, {})
const gate = cap.find((d) => d.name === 'plugin_name_gate')
if (!gate) { console.log('✗ 未捕获 plugin_name_gate'); process.exit(1) }

const r = await gate.execute({ action: 'audit', base: base }, {})
const F = []
const ck = (name, cond, got) => { if (!cond) F.push(name + ' → 实得: ' + JSON.stringify(got)); console.log((cond ? '  ✅ ' : '  ✗ ') + name) }

console.log('  ── 夹具实测（base=' + base + '）──')
for (const e of r.entries) console.log('    ' + e.dir.padEnd(22) + ' verdict=' + e.verdict)

console.log('  ── ① 分项计数 ──')
const ids = ['N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7', 'N8']
ck('ruleTally 含 N1–N8 全部键', ids.every((i) => r.ruleTally && r.ruleTally[i]), r.ruleTally && Object.keys(r.ruleTally))
ck('每项四态齐全', ids.every((i) => r.ruleTally[i] && ['pass', 'fail', 'unverified', 'notRun'].every((k) => typeof r.ruleTally[i][k] === 'number')), r.ruleTally && r.ruleTally.N1)
// ★ 本测试最初写成「缺前缀 ⇒ N1 fail」，实测为错：scanRegistry 已按同一前缀过滤 ⇒ 该类目录根本不进总体，
//   既不进 scanned 也不计 fail。正确的判据不是「N1 fail ≥1」，而是「该目录须在未枚举面里被点名」。
ck('N1.fail 恒为 0 —— 按构造不可能非零（前缀过滤先于 N1 判定）', r.ruleTally.N1.fail === 0, r.ruleTally.N1)
ck('缺前缀的目录不在 entries 中（故不进 scanned）', !r.entries.some((e) => e.dir === 'dsh_plugin-gammafix'), r.entries.map((e) => e.dir))
ck('但它出现在 enumeration.suspectsExcluded 里（信息未丢失）', r.enumeration.suspectsExcluded.some((s) => s.indexOf('dsh_plugin-gammafix') !== -1), r.enumeration.suspectsExcluded)
ck('enumeration.filter 声明了总体选取规则', r.enumeration.filter === 'dsh-plugin-*', r.enumeration.filter)
ck('machine_readable 一并声明 enumerationFilter', /audit\.enumerationFilter=dsh-plugin-\*/.test((r.surface_unmeasured && r.surface_unmeasured.machine_readable) || ''), r.surface_unmeasured && r.surface_unmeasured.machine_readable)
ck('roots 逐根带 suspectsExcluded 字段', r.roots.every((x) => Array.isArray(x.suspectsExcluded)), r.roots)
ck('逐项计数之和 ⊇ 全部条目', r.ruleTally.N1.pass + r.ruleTally.N1.fail + r.ruleTally.N1.unverified === r.scanned, r.ruleTally.N1)
ck('未被判的项计入 notRun（N5–N8 = scanned）', ids.slice(4).every((i) => r.ruleTally[i].notRun === r.scanned), ids.slice(4).map((i) => r.ruleTally[i].notRun))

console.log('  ── ② partial 不并入 pass ──')
ck('三态分区封闭 pass+partial+fail = scanned', r.pass + r.partial + r.fail === r.scanned, [r.pass, r.partial, r.fail, r.scanned])
ck('partial 非空（否则本条是空改动）', r.partial >= 1, r.partial)
ck('passIncludingPartial = pass + partial（1.0.4 原值仍可取回）', r.passIncludingPartial === r.pass + r.partial, [r.passIncludingPartial, r.pass, r.partial])
ck('pass 严格小于旧口径', r.pass < r.passIncludingPartial, [r.pass, r.passIncludingPartial])

console.log('  ── ③ 未测面机器可读 ──')
ck('rulesCovered ∪ rulesUnmeasured = N1–N8 且不交', r.rulesCovered.length + r.rulesUnmeasured.length === 8 && r.rulesCovered.every((x) => r.rulesUnmeasured.indexOf(x) === -1), [r.rulesCovered, r.rulesUnmeasured])
ck('rulesCovered = N1–N4（本审计实覆盖）', JSON.stringify(r.rulesCovered) === JSON.stringify(['N1', 'N2', 'N3', 'N4']), r.rulesCovered)
const mr = r.surface_unmeasured && r.surface_unmeasured.machine_readable
ck('machine_readable 存在', typeof mr === 'string' && mr.length > 0, mr)
const p1 = /audit\.rulesCovered=\[([^\]]*)\]/.exec(mr || '')
const p2 = /audit\.rulesUnmeasured=\[([^\]]*)\]/.exec(mr || '')
ck('machine_readable 可被正则反解回同一列表', p1 && p2 && p1[1] === r.rulesCovered.join(',') && p2[1] === r.rulesUnmeasured.join(','), [p1 && p1[1], p2 && p2[1]])
ck('surface_unmeasured.rules = rulesUnmeasured', JSON.stringify(r.surface_unmeasured.rules) === JSON.stringify(r.rulesUnmeasured), r.surface_unmeasured.rules)

const undef = (function scan(v, p, hits) { if (v === undefined) hits.push(p); else if (Array.isArray(v)) v.forEach((x, i) => scan(x, p + '[' + i + ']', hits)); else if (v && typeof v === 'object') for (const k of Object.keys(v)) scan(v[k], p + '.' + k, hits); return hits })(r, '$', [])
ck('返回体无 undefined', undef.length === 0, undef)

await (await import('node:fs/promises')).rm(base, { recursive: true, force: true })
console.log('\n失败项: ' + F.length)
if (F.length > 0) F.forEach((x) => console.log('  ✗ ' + x))
process.exit(F.length === 0 ? 0 : 1)
