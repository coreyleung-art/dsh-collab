#!/usr/bin/env node
/**
 * cli.js — CLI 治理（⑨）+ 自查门（②③④）+ 版本（⑥）+ Lean4 结构门自证（⑩）
 * =============================================================================
 * 用法：
 *   node cli.js --date 2026-09-10            # 生成 proposal-<date>.md（**待用户裁定**）
 *   node cli.js --date 2026-09-10 --preview  # 只把提案全文打到 stdout，不落盘
 *   node cli.js --date 2026-09-10 --summary  # 终端摘要（按跨设备+复现广度排序）
 *   node cli.js --date 2026-09-10 --dry-run  # 只算不写（前后状态实测零变更）
 *   node cli.js --date 2026-09-10 --json
 *   node cli.js --selfcheck | --lean4-check | --tool-version | --help
 *
 * 退出码（R006 ⑨）：0=成功/门生效 · 1=失败/门失效 · 2=用法错误或 IO 错误
 */
import { parseArgs } from 'node:util';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

import { synthesize, formatSummary, DATE_RE, SynthesizeIOError } from './lib/synthesize.js';
import { writeProposal, LOG_FILE, DATA_DIR, log, writeTargetNegativeCases, writeTargetPositiveCases, OUT_META } from './lib/out.js';
import {
  ALLOWED_COMMANDS, JUDGMENTS, CATEGORIES, GATE_META, JUDGE_RULE,
  scanExecSites, scanWriteSites, scannerSelfTest, stripLiterals, vetNegativeCases, vetPositiveCases,
  GateError
} from './lib/gate.js';
import { assertNoForbiddenFlags, CLI_OPTIONS, OPTIONS_META } from './lib/options.js';
import { runSelfCheck } from './lib/selfcheck.js';
import { mountSmoke } from './lib/smoke.js';
import { RULES_PATH, PHILOSOPHY_PATH } from './lib/catalog.js';
import { judgeCluster, classify, judgmentPolicyCases, ANALYZE_META } from './lib/analyze.js';
import { buildProposal, recurrenceBreakdown } from './lib/proposal.js';
import { loadCatalog } from './lib/catalog.js';
import { LESSON_META } from './lib/lesson.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const C = { ok: '\u2705', no: '\u274c', warn: '\u26a0\ufe0f' };
const out = (s) => process.stdout.write(s + '\n');
const TESTDATA = path.join(HERE, 'testdata');

const VERSION = (() => {
  try { return JSON.parse(fs.readFileSync(path.join(HERE, 'package.json'), 'utf8')).version; }
  catch { return '0.0.0-unknown'; }
})();

let args;
try { args = parseArgs({ options: { ...CLI_OPTIONS }, allowPositionals: false }).values; }
catch (e) { out(`用法错误: ${e.message}`); out('试 --help'); process.exit(2); }

if (args.help) {
  out(`dsh-plugin-reflect-synthesize v${VERSION} — 每日反思流水线 · 提炼（⑤）
读 harvested-<date>.json → 对照现有库 → 分类归档 → ★按（跨设备, 复现广度）排序 → 生成 proposal-<date>.md

★ 本工具是全流水线**唯一需要判断**的环节，纪律是：
  规则能定的用规则；**规则定不了的显式标 unclear 交人工/LLM 复核**（不硬猜 —— 硬猜的代价不对称）。
★ 排序键是 **(cross_device, recurrence) 二元组**：跨设备复现优先。
  不同设备跑不同任务、看不同上下文，独立踩同坑 ⇒ 系统性缺陷，比同机多会话更强。
★ 本工具**没有**写 RULES.md / governance-philosophy.json 的能力：
  没有 --apply / --enroll / --write-rules / --out（旗标集合运算证明）；
  写目标白名单只有 proposal-md / unified-log / selfcheck-state，治理库目录**根本不在基目录之下**。

  --date <YYYY-MM-DD>     目标日期（默认今天）
  --harvested-dir <dir>   收牌产物目录（默认 ~/dsh-collab/data/reflect）
  --preview               把提案 markdown 全文打到 stdout（不落盘）
  --summary               终端摘要（跨设备优先 + 复现广度）
  --dry-run               只算不写：提案产物、日志、参照库**全部零变更**
  --json                  机器可读输出
  --selfcheck             ②③④：能力清单 / 不该发生路径清单 / 依赖完整性
  --lean4-check           ⑩ 结构门自证（A–F 六项，含扫描器正控与 dry-run 零变更实测）
  --tool-version  --help

退出码: 0 成功/门生效 · 1 失败/门失效 · 2 用法错误或 IO 错误
不能做: 写规则库/哲学库/规则机读本；入册（那是 ⑦ reflect-enroll 在用户裁定之后的事）；执行任何外部命令`);
  process.exit(0);
}

if (args['tool-version']) { out(`dsh-plugin-reflect-synthesize ${VERSION}`); process.exit(0); }

const SOURCES = {
  'cli.js': fs.readFileSync(path.join(HERE, 'cli.js'), 'utf8'),
  'lib/gate.js': fs.readFileSync(path.join(HERE, 'lib', 'gate.js'), 'utf8'),
  'lib/out.js': fs.readFileSync(path.join(HERE, 'lib', 'out.js'), 'utf8'),
  'lib/synthesize.js': fs.readFileSync(path.join(HERE, 'lib', 'synthesize.js'), 'utf8'),
  'lib/analyze.js': fs.readFileSync(path.join(HERE, 'lib', 'analyze.js'), 'utf8'),
  'lib/proposal.js': fs.readFileSync(path.join(HERE, 'lib', 'proposal.js'), 'utf8'),
  'lib/catalog.js': fs.readFileSync(path.join(HERE, 'lib', 'catalog.js'), 'utf8'),
  'lib/lesson.js': fs.readFileSync(path.join(HERE, 'lib', 'lesson.js'), 'utf8'),
  'lib/options.js': fs.readFileSync(path.join(HERE, 'lib', 'options.js'), 'utf8'),
  'lib/index.js': fs.readFileSync(path.join(HERE, 'lib', 'index.js'), 'utf8'),
  'lib/selfcheck.js': fs.readFileSync(path.join(HERE, 'lib', 'selfcheck.js'), 'utf8')
};

/* ------------------------------ ②③④ --selfcheck ------------------------------ */
if (args.selfcheck) {
  const L = [];
  L.push(`dsh-plugin-reflect-synthesize v${VERSION} · --selfcheck（R006 ② TCC / ③ CLD 自适应 / ④ dsh 版本自适应）`);
  L.push('');
  const sc = runSelfCheck('dsh-plugin-reflect-synthesize', {
    requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
    requiredSymbols: ['parseArgs', 'synthesize', 'writeProposal'],
    sourceFiles: ['cli.js'], baseDir: HERE
  });
  const nf = assertNoForbiddenFlags();

  L.push('【① 能力清单】我能做什么');
  L.push(`  ${C.ok} 读 harvested-<date>.json（只读；不改收牌产物、不改上游回填）`);
  L.push(`  ${C.ok} 对照现有库：规则（RULES.md）+ 哲学（governance-philosophy.json），判定闭集 [${JUDGMENTS.join(' · ')}]`);
  L.push(`  ${C.ok} 分类归档闭集 [${CATEGORIES.join(' · ')}]`);
  L.push(`  ${C.ok} ★ 按（跨设备, 复现广度）二元组降序排；逐项标注 \`复现: mac-mini×3 + mbp×1\` 与跨设备 ✅`);
  L.push(`  ${C.ok} 生成「看一眼就能裁」的 proposal-<date>.md（速览表 + 逐项明细 + 待复核清单 + 裁定落法）`);
  L.push(`  ${C.ok} 写且仅写：proposal-<date>.md（${DATA_DIR}）+ 统一日志（${LOG_FILE}）`);
  L.push('');

  L.push('【② 不该发生路径清单】我做不了什么（★ 本工具的重点）');
  L.push(`  ${C.ok} 不该：**替用户改哲学库/规则库**（RULES.md / governance-philosophy.json / rules.json）`);
  L.push(`       └ 「没有那个入口」：集合运算证明 ${nf.checked.length} 个旗标/入参中命中禁用名 ${nf.hits.length} 个 ${nf.ok ? C.ok : C.no}`);
  L.push(`         禁用名: [${OPTIONS_META.forbiddenFlags.join(', ')}]`);
  L.push(`       └ 「没有那个能力」：写目标白名单 = [${OUT_META.writeTargets.join(', ')}]`);
  L.push(`         规则库/哲学库所在目录（rules-registry/、data/blueprint/gallery/）**不在任何基目录之下 → 路径构造不出来**`);
  L.push(`       └ 写路径禁用词: [${OUT_META.forbiddenTokens.join(', ')}]`);
  L.push(`  ${C.ok} 不该：自动入册（入册是 ⑦ reflect-enroll 在用户裁定之后的事 —— phi-user-sovereignty）`);
  L.push(`  ${C.ok} 不该：把无证据的条目摆到用户面前让他据此裁定（输入侧纵深防御：vetClusterMember 丢弃并计数）`);
  L.push(`  ${C.ok} 不该：执行任何外部命令 —— 命令白名单 = [${ALLOWED_COMMANDS.join(', ') || '空集'}]`);
  L.push(`  ${C.ok} 不该：把判不了的东西硬归类（拿不准 → unclear + 进「需人工复核」清单，不猜）`);
  L.push('');

  L.push('【③ CLD 自适应】无 CLD 也能给出结论');
  L.push(`  ${C.ok} 运行期只用 node ${process.version} 内置模块（fs/path/os/crypto/util）；零外部命令、零网络`);
  L.push(`  ${C.ok} 不 import 宿主私有路径；CLI 与插件挂载点解耦，可独立运行`);
  L.push('');

  L.push('【③ 依赖完整性 / ④ dsh 版本自适应】两级解析（本目录 → profile/node_modules）');
  for (const p of sc.peers || []) L.push(`  ${p.ok ? C.ok : C.no} ${p.peer}${p.version ? '@' + p.version : ''} via=${p.via || '-'}`);
  L.push(`  ${sc.ok ? C.ok : C.no} R014 自查门: missing=${sc.missing.length} warnings=${sc.warnings.length}`);
  sc.missing.forEach((m) => L.push(`      ${C.no} ${m}`));
  (sc.notes || []).forEach((n) => L.push(`      · ${n}`));

  const ok = sc.ok && nf.ok;
  L.push('');
  // ★ R006 v3.1.0 ① 第 5 项：真挂载冒烟
  const smoke = await mountSmoke({ baseDir: HERE, indexRel: 'lib/index.js', config: {} });
  const sm = { pass: '✅ 挂载通过', fail: '❌ 挂不上（真实缺陷）', skipped: '⊘ 已跳过（如实说明）' }[smoke.state] || smoke.state;
  L.push('');
  L.push(`【⑤ 真挂载冒烟】${sm}`);
  if (smoke.state === 'pass') L.push(`  · 注册工具: ${smoke.tools.join(', ')}（effect ${smoke.effects} 个）`);
  else if (smoke.state === 'skipped') L.push(`  · 原因: ${smoke.reason}`);
  else L.push(`  · ${smoke.stage}: ${smoke.error}`);
  L.push('');
  L.push(`${ok ? C.ok : C.no} 自查门结论：${ok ? '通过（能力边界已自报，未发现依赖缺口）' : '未通过 —— 缺项见上'}`);
  out(L.join('\n'));
  process.exit(ok ? 0 : 1);
}

/* ------------------------------ ⑩ --lean4-check ------------------------------ */
if (args['lean4-check']) {
  const checks = [];

  // A. 源码无危险原语
  const EXEC_SITES = scanExecSites({ sources: SOURCES });
  const evalHits = [];
  for (const [f, raw] of Object.entries(SOURCES)) {
    const code = stripLiterals(raw);
    code.split('\n').forEach((line, i) => {
      if (/(?<![\w.$])eval\s*\(|new\s+Function\s*\(|child_process/.test(line)) evalHits.push({ file: f, line: i + 1 });
    });
  }
  checks.push({
    id: 'A 源码无危险原语',
    ok: evalHits.length === 0,
    detail: evalHits.length ? JSON.stringify(evalHits) : `去字面量扫描 ${Object.keys(SOURCES).length} 个文件：eval/new Function/child_process 命中 0 次（exec 调用点另有 F 项专门枚举）`
  });

  // B. 负例全部被拒 + 无削弱入口（写门是主角）
  const negWrite = writeTargetNegativeCases();
  const negWriteLeak = negWrite.filter((n) => n.code === null);
  const negEv = vetNegativeCases();
  const negEvLeak = negEv.filter((n) => n.code === null);
  const nf = assertNoForbiddenFlags();
  checks.push({
    id: 'B 负例全部被拒 + 无写库入口',
    ok: negWriteLeak.length === 0 && negEvLeak.length === 0 && nf.ok,
    detail: `★ 写门负例 ${negWrite.length - negWriteLeak.length}/${negWrite.length} 被拒（写 RULES.md / governance-philosophy.json / rules.json / rules-registry / gallery / ../ 穿越 / 子目录 / 假 kind apply·enroll / 空值${negWriteLeak.length ? ' ★竟然放行:' + JSON.stringify(negWriteLeak) : ''}）` +
      ` · 输入侧证据门负例 ${negEv.length - negEvLeak.length}/${negEv.length} 被拒（无证据的 member 不进提案）` +
      ` · 写库/入册/自定义路径旗标命中 ${nf.hits.length}/${nf.checked.length}（禁用名 [${OPTIONS_META.forbiddenFlags.join(',')}]${nf.hits.length ? ' ★竟然存在:' + JSON.stringify(nf.hits) : ''}）`
  });

  // C. 正例可用（防「门太宽把功能也砍了」）
  const posWrite = writeTargetPositiveCases();
  const posWriteOk = posWrite.every((p) => p.ok);
  // 正例：一个真实 cluster 必须能被判定出结论（不是全部 unclear）
  const cat = loadCatalog();
  const fakeCluster = {
    cluster_id: 'C0', lesson: '新做插件必须十项全达标才交付', recurrence: 2, item_count: 2,
    devices: ['mac-mini'], agents: ['mac-mini:a', 'mac-mini:b'], refs: ['R006'],
    members: [{ device: 'mac-mini', agent: 'a', item_id: 'R1', pit: 'p', lesson: '新做插件必须十项全达标才交付', related_rule: 'R006', suggestion: { type: '无需动作' }, evidence: { ts: 't', cmd: 'c' } }]
  };
  const j = judgeCluster(fakeCluster, cat);
  const cls = classify(fakeCluster, j);
  const judgeOk = j.judgment !== 'unclear' && cls.category !== '需人工复核';
  // ★ 判定分支覆盖自测：5 个 judgment 逐个用合成 cluster 实测（防"分支从没被执行过"）
  const policy = cat.available.rules || cat.available.phis ? judgmentPolicyCases(cat) : [];
  const policyOk = policy.length > 0 && policy.every((c) => c.ok);
  checks.push({
    id: 'C 合法输入可用（写目标 + 对照判定 + 成员准入）',
    ok: posWriteOk && judgeOk && policyOk && vetPositiveCases().every((p) => p.ok),
    detail: `写目标 ${posWrite.filter((p) => p.ok).length}/${posWrite.length} 可用（${posWrite.map((p) => p.input).join(', ')}）` +
      ` ‖ 输入侧证据门正例 ${vetPositiveCases().filter((p) => p.ok).length}/${vetPositiveCases().length} 可用` +
      ` ‖ 判定分支覆盖 ${policy.filter((c) => c.ok).length}/${policy.length}：${policy.map((c) => `${c.expect}→${c.ok ? '✅' : '❌got:' + c.got}`).join(' · ')}`
  });

  // D. --dry-run 零变更（实测）+ 产出不变量
  const probeDate = args.date && DATE_RE.test(args.date) ? args.date : '2026-09-10';
  const srcPath = path.join(TESTDATA, `harvested-${probeDate}.json`);
  const snap = () => {
    const h = (p) => { try { return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex').slice(0, 16); } catch { return null; } };
    return {
      proposal: h(path.join(DATA_DIR, `proposal-${probeDate}.md`)),
      logSize: (() => { try { return fs.statSync(LOG_FILE).size; } catch { return null; } })(),
      rules: h(RULES_PATH),
      philosophy: h(PHILOSOPHY_PATH),
      testdataHarvested: h(srcPath)
    };
  };
  let dOk = false, dDetail = '', invOk = true, invBad = [];
  try {
    const before = snap();
    const { result } = synthesize(probeDate, { dryRun: true, harvestedDir: TESTDATA, version: VERSION });
    const after = snap();
    const diffs = Object.keys(before).filter((k) => before[k] !== after[k]);
    dOk = diffs.length === 0;

    // ★ 产出不变量（自洽性）
    const inv = [];
    const ranks = result.items.map((i) => i.rank);
    if (ranks.join(',') !== ranks.slice().sort((a, b) => a - b).join(',')) inv.push('rank 不是 1..N 连续');
    let prevCd = 1, prevRec = Infinity;
    for (const it of result.items) {
      const cd = it.cross_device ? 1 : 0;
      if (cd > prevCd) inv.push(`P${it.rank}: 跨设备项排在单设备项之后 —— 排序键 (cross_device, recurrence) 未生效`);
      if (cd === prevCd && it.recurrence > prevRec) inv.push(`P${it.rank}: 同跨设备档内 recurrence 未降序`);
      prevCd = cd; prevRec = it.recurrence;
      const sum = Object.values(it.recurrence_breakdown).reduce((a, b) => a + b, 0);
      if (sum !== it.recurrence) inv.push(`P${it.rank}: 复现明细之和 ${sum} ≠ recurrence ${it.recurrence}`);
      if (it.cross_device !== (it.devices.length >= 2)) inv.push(`P${it.rank}: cross_device 与 devices 数矛盾`);
      if (it.category === '归档为案例' && it.needs_human) inv.push(`P${it.rank}: 归档项不应标 needs_human`);
    }
    const sumJ = Object.values(result.judgment_distribution).reduce((a, b) => a + b, 0);
    if (sumJ !== result.items.length) inv.push(`判定分布之和 ${sumJ} ≠ 项数 ${result.items.length}`);
    const sumC = Object.values(result.category_distribution).reduce((a, b) => a + b, 0);
    if (sumC !== result.items.length) inv.push(`处置分布之和 ${sumC} ≠ 项数 ${result.items.length}`);
    invOk = inv.length === 0; invBad = inv;

    dDetail = (dOk
      ? `dry-run 前后 **5 项**外部状态完全一致（提案产物 / 日志大小 / RULES.md / 哲学库 / 包内 harvested）· 计划写入 ${result.planned_file}（${result.planned_bytes}B，未写）`
      : `发生变更: ${diffs.map((k) => `${k}: ${before[k]} → ${after[k]}`).join('; ')}`) +
      `\n      ★ 产出不变量: ${invOk ? `全部自洽（${result.items.length} 项：跨设备优先排序已生效 / 复现明细之和=recurrence / cross_device↔devices / 分布求和=项数）` : `★ 自相矛盾 ${inv.length} 处: ${invBad.join(' | ')}`}`;
  } catch (e) {
    dDetail = `dry-run 实测无法执行：${e.name} ${e.code || ''} ${e.message}`.slice(0, 300);
  }
  checks.push({ id: 'D --dry-run 零变更 + 产出不变量自洽', ok: dOk && invOk, detail: dDetail });

  // E. 白名单冻结
  const frozenOk = Object.isFrozen(JUDGMENTS) && Object.isFrozen(CATEGORIES) && Object.isFrozen(ALLOWED_COMMANDS) &&
    Object.isFrozen(GATE_META) && Object.isFrozen(OPTIONS_META) && Object.isFrozen(OUT_META) && Object.isFrozen(JUDGE_RULE);
  checks.push({
    id: 'E 白名单冻结',
    ok: frozenOk,
    detail: `frozen=${frozenOk} · 判定闭集 ${JUDGMENTS.length} 条 · 分类闭集 ${CATEGORIES.length} 条 · 写目标=${OUT_META.writeTargets.length} 个 · 禁用名 ${OPTIONS_META.forbiddenFlags.length} 条 · 命令白名单=[]`
  });

  // F. 命令白名单 + 扫描器正控 + 写出口收口
  const st = scannerSelfTest();
  const nonBenign = EXEC_SITES.filter((s) => !s.benign);
  const benignSites = EXEC_SITES.filter((s) => s.benign);
  const bad = nonBenign.filter((s) => !s.literal || !ALLOWED_COMMANDS.includes(s.cmd));
  const WRITE_SITES = scanWriteSites({ sources: SOURCES });
  const strayWrites = WRITE_SITES.filter((s) => s.file !== 'lib/out.js');
  const forbiddenInWrite = WRITE_SITES.filter((s) =>
    s.sourceLine.includes('RULES.md') || s.sourceLine.includes('governance-philosophy.json') ||
    s.sourceLine.includes('rules.json') || s.sourceLine.includes('gallery'));
  checks.push({
    id: 'F 命令白名单 + 扫描器正控 + 写出口收口',
    ok: st.ok && bad.length === 0 && strayWrites.length === 0 && forbiddenInWrite.length === 0,
    detail: (!st.ok ? `★ 扫描器正控失败（可能是空洞通过）: ${st.detail}` : st.detail) +
      ` · 本包非良性 exec 调用点 ${nonBenign.length}（良性 ${benignSites.length}：${benignSites.map((s) => `${s.file}:${s.line}`).join(', ') || '无'}）⊆ [${ALLOWED_COMMANDS.join(',') || '空集'}]` +
      ` · 写调用点 ${WRITE_SITES.length} 个**全部**位于 [lib/out.js]（越界 ${strayWrites.length}）· 写语句命中治理库禁用词 ${forbiddenInWrite.length} 次` +
      ` —— 「无写库路径」由此得到源码级证明`
  });

  const ok = checks.every((c) => c.ok);
  if (args.json) out(JSON.stringify({ ok, checks, version: VERSION, gate: GATE_META, analyze: ANALYZE_META, lesson: LESSON_META, forbiddenFlagProof: nf, scanner: { ok: st.ok, detail: st.detail, execSites: EXEC_SITES, writeSites: WRITE_SITES } }, null, 1));
  else {
    out(`lean4-check · 结构门自证（${GATE_META.principle}）`);
    for (const c of checks) out(`  ${c.ok ? C.ok : C.no} ${c.id}\n      ${c.detail}`);
    out('');
    out(ok ? `${C.ok} 结构门生效：约束不可绕过（没有那个出口 + 有那个证明）` : `${C.no} 门未生效，禁止交付`);
  }
  log(`lean4-check ok=${ok} ` + JSON.stringify(checks.map((c) => `${c.id.split(' ')[0]}:${c.ok}`)), undefined, { dryRun: args['dry-run'] === true });
  process.exit(ok ? 0 : 1);
}

/* --------------------------------- 主流程 --------------------------------- */
const date = args.date || new Date().toISOString().slice(0, 10);
if (!DATE_RE.test(date)) { out(`用法错误: --date 必须是 YYYY-MM-DD，收到 '${date}'`); process.exit(2); }

let res, markdown;
try {
  const r = synthesize(date, { dryRun: args['dry-run'], harvestedDir: args['harvested-dir'], version: VERSION });
  res = r.result; markdown = r.markdown;
} catch (e) {
  if (e instanceof SynthesizeIOError) { out(`${C.no} IO 错误 [${e.code}] ${e.message}`); process.exit(2); }
  if (e instanceof GateError) { out(`${C.no} 门拒绝 [${e.code}] ${e.message}`); process.exit(1); }
  out(`${C.no} 失败: ${e.stack || e.message}`); process.exit(1);
}

if (args.preview) {
  out(markdown);
  if (!args.json) out(`（--preview：未落盘。去掉 --preview 即写入 ${res.planned_file || res.output_file}）`);
  process.exit(0);
}

if (args.json) out(JSON.stringify({ ...res, dryRun: args['dry-run'], version: VERSION }, null, 1));
else if (args.summary) out(formatSummary(res));
else {
  out(`候选 ${res.counts.clusters} 项（★跨设备 ${res.counts.cross_device}）· 需裁定 ${res.counts.need_ruling} · 归档 ${res.counts.archived} · 需人工复核 ${res.counts.need_human}`);
  out(`判定: ${Object.entries(res.judgment_distribution).map(([k, v]) => `${k}×${v}`).join(' · ')}`);
  out(res.output_file ? `已写入 ${res.output_file}（${res.output_bytes}B · sha256 ${res.output_sha256}）` : `[dry-run] 未写入；计划产物 ${res.planned_file}`);
  out('（--summary 看排序；--preview 看提案全文）');
}
process.exit(0);
