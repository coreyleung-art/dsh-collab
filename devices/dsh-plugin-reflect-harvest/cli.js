#!/usr/bin/env node
/**
 * cli.js — CLI 治理（⑨）+ 自查门（②③④）+ 版本（⑥）+ Lean4 结构门自证（⑩）· ★ 跨设备版
 * =============================================================================
 * 用法：
 *   node cli.js --date 2026-09-10                      # 全设备收牌（本地 + 中央黑板）
 *   node cli.js --date 2026-09-10 --summary            # 人类可读摘要（按设备分组 + 跨设备复现）
 *   node cli.js --date 2026-09-10 --devices mac-mini,mbp --allow-late
 *   node cli.js --date 2026-09-10 --local-only         # 只读本机（离线/测试）
 *   node cli.js --date 2026-09-10 --dry-run            # 只算不写（前后状态实测零变更）
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

import { harvest, formatSummary, DATE_RE, HarvestIOError, DEFAULT_CENTRAL } from './lib/harvest.js';
import { writeHarvested, LOG_FILE, DATA_DIR, log, writeTargetNegativeCases, writeTargetPositiveCases } from './lib/out.js';
import {
  ALLOWED_COMMANDS, SUGGESTION_TYPES, ALL_REJECT_REASONS, GATE_META, SYNC_DUP_RULE,
  evidenceNegativeCases, shapeNegativeCases, evidencePositiveCases, brandNegativeCases,
  scanExecSites, scanWriteSites, scannerSelfTest, stripLiterals, GateError
} from './lib/gate.js';
import { scanHttpSites, httpScannerSelfTest, HTTP_META } from './lib/http.js';
import { deviceNegativeCases, devicePositiveCases, DEVICES_META, DEFAULT_DEVICES } from './lib/devices.js';
import { assertNoPermissiveFlags, CLI_OPTIONS, OPTIONS_META } from './lib/options.js';
import { runSelfCheck } from './lib/selfcheck.js';
import { mountSmoke } from './lib/smoke.js';
import { RULES_PATH, PHILOSOPHY_PATH } from './lib/catalog.js';
import { SIM_RULE } from './lib/lesson.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const C = { ok: '\u2705', no: '\u274c', warn: '\u26a0\ufe0f' };
const out = (s) => process.stdout.write(s + '\n');
const TESTDATA_ROOT = path.join(HERE, 'testdata', 'data');

/** ⑥ 版本单一来源 */
const VERSION = (() => {
  try { return JSON.parse(fs.readFileSync(path.join(HERE, 'package.json'), 'utf8')).version; }
  catch { return '0.0.0-unknown'; }
})();

/* ------------------------------- 参数（⑨） ------------------------------- */
let args;
try {
  args = parseArgs({ options: { ...CLI_OPTIONS }, allowPositionals: false }).values;
} catch (e) {
  out(`用法错误: ${e.message}`); out('试 --help'); process.exit(2);
}

if (args.help) {
  out(`dsh-plugin-reflect-harvest v${VERSION} — 每日反思流水线 · 收牌（④ · ★ 跨设备）
从**全部设备**收智能体回填（本机目录 + 中央黑板）→ 五类校验 → 跨设备聚类 → 复现广度计数 → harvested-<date>.json

★ 质量门（本工具的核心，不是简单合并）：无证据的条目**在结构上无法进入 valid 集合**
  evidence 必须含 ts + (cmd 或 output)；缺任一项 → invalid_evidence 并隔离。
  mintAdmitted() 是条目入 valid 的唯一入口；buildValidSet() 只收品牌化条目（裸对象抛 GateError）。
★ 跨设备：recurrence 数的是独立 <设备>:<智能体>；集群带 cross_device；
  逐字相同且跨设备、时点接近的 lesson 判 possible_sync_duplicate（不重复计入 recurrence）。

  --date <YYYY-MM-DD>   目标日期（默认今天）
  --devices <a,b,c>     设备表（默认读 devices.json，再退到冻结默认表 [${DEFAULT_DEVICES.join(', ')}]）
  --device <name>       本机设备名（用于把无设备段的老布局目录归到谁名下）
  --central <url>       中央黑板地址（默认 ${DEFAULT_CENTRAL}）
  --local-root <dir>    本地根目录（默认 ~/dsh-collab/data/reflect）
  --local-only          只读本机目录，不触碰中央黑板（离线/测试）
  --allow-late          额外收 T-1/T-2 的补填（仅收归属当日者，并标注实际提交时刻 —— Φ13）
  --summary             人类可读摘要（按设备分组 + 拒收原因分布 + 跨设备复现排序）
  --dry-run             只算不写：数据产物、日志、参照库**全部零变更**
  --json                机器可读输出
  --selfcheck           ②③④：能力清单 / 不该发生路径清单 / 依赖完整性
  --lean4-check         ⑩ 结构门自证（A–F 六项，含扫描器正控与 dry-run 零变更实测）
  --tool-version  --help

退出码: 0 成功/门生效 · 1 失败/门失效 · 2 用法错误或 IO 错误
不能做: 写黑板（只 GET）；写 RULES.md / 哲学库 / rules.json；执行任何外部命令（命令白名单=空集）
没有那个入口: --skip-evidence / --force / --lenient（集合运算证明，见 --lean4-check B 项）`);
  process.exit(0);
}

if (args['tool-version']) { out(`dsh-plugin-reflect-harvest ${VERSION}`); process.exit(0); }

const SOURCES = {
  'cli.js': fs.readFileSync(path.join(HERE, 'cli.js'), 'utf8'),
  'lib/gate.js': fs.readFileSync(path.join(HERE, 'lib', 'gate.js'), 'utf8'),
  'lib/harvest.js': fs.readFileSync(path.join(HERE, 'lib', 'harvest.js'), 'utf8'),
  'lib/out.js': fs.readFileSync(path.join(HERE, 'lib', 'out.js'), 'utf8'),
  'lib/index.js': fs.readFileSync(path.join(HERE, 'lib', 'index.js'), 'utf8'),
  'lib/selfcheck.js': fs.readFileSync(path.join(HERE, 'lib', 'selfcheck.js'), 'utf8'),
  'lib/catalog.js': fs.readFileSync(path.join(HERE, 'lib', 'catalog.js'), 'utf8'),
  'lib/lesson.js': fs.readFileSync(path.join(HERE, 'lib', 'lesson.js'), 'utf8'),
  'lib/options.js': fs.readFileSync(path.join(HERE, 'lib', 'options.js'), 'utf8'),
  'lib/http.js': fs.readFileSync(path.join(HERE, 'lib', 'http.js'), 'utf8'),
  'lib/devices.js': fs.readFileSync(path.join(HERE, 'lib', 'devices.js'), 'utf8'),
  'lib/source.js': fs.readFileSync(path.join(HERE, 'lib', 'source.js'), 'utf8')
};

const devicesFromArgs = () => (args.devices ? String(args.devices).split(',').map((s) => s.trim()).filter(Boolean) : undefined);

/* ------------------------------ ②③④ --selfcheck ------------------------------ */
if (args.selfcheck) {
  const L = [];
  L.push(`dsh-plugin-reflect-harvest v${VERSION} · --selfcheck（R006 ② TCC / ③ CLD 自适应 / ④ dsh 版本自适应）`);
  L.push('');

  const sc = runSelfCheck('dsh-plugin-reflect-harvest', {
    requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
    requiredSymbols: ['parseArgs', 'harvest', 'writeHarvested'],
    sourceFiles: ['cli.js'],
    baseDir: HERE
  });

  L.push('【① 能力清单】我能做什么');
  L.push(`  ${C.ok} 全设备收牌：本地 <localRoot>/answers/<device>/<date>/ + 中央黑板 data/reflect/answers/<device>/<date>`);
  L.push(`  ${C.ok} 五类校验：★证据完整性 / 必填字段 / suggestion.type 合法性 / related_rule 存在性 / declined 合法性`);
  L.push(`  ${C.ok} (device,agent) 去重（黑板 > 本地）→ 跨设备聚类（Dice ≥ ${SIM_RULE.dice} 或 shared ≥ ${SIM_RULE.sharedMin}）`);
  L.push(`  ${C.ok} 复现广度 = 独立 <设备>:<智能体> 数 · 集群带 cross_device · possible_sync_duplicate 不重复计入`);
  L.push(`  ${C.ok} 按设备分组统计 · 版本漂移检查（plugin_version）· pending / not_dispatched 区分`);
  L.push(`  ${C.ok} 写且仅写：harvested-<date>.json（${DATA_DIR}）+ 统一日志（${LOG_FILE}）`);
  L.push(`  ${C.ok} suggestion.type 闭集: [${SUGGESTION_TYPES.join(' / ')}] · 拒收原因闭集: [${ALL_REJECT_REASONS.join(' / ')}]`);
  L.push('');

  const nf = assertNoPermissiveFlags();
  L.push('【② 不该发生路径清单】我做不了什么（★ 本工具的重点）');
  L.push(`  ${C.ok} 不该：把无证据的条目当有效混进汇总（质量门死线）`);
  L.push(`       └ 结构封堵：mintAdmitted() 唯一入口（不过返回 null）；buildValidSet() 唯一 push 点（裸对象抛错）`);
  L.push(`       └ 「没有那个入口」：集合运算证明 ${nf.checked.length} 个旗标/入参中命中禁用片段 ${nf.hits.length} 个 ${nf.ok ? C.ok : C.no}`);
  L.push(`  ${C.ok} 不该：**写黑板**（谁回填谁写，汇集方不得代笔）`);
  L.push(`       └ 结构封堵：lib/http.js 只导出 httpGetJson(url)（**无 method 参数**）；无 http.request / fetch / XMLHttpRequest 原语`);
  L.push(`       └ 允许的 HTTP 方法闭集: [${HTTP_META.allowedMethods.join(', ')}] · 允许的外部命令: [${ALLOWED_COMMANDS.join(', ') || '空集'}]`);
  L.push(`  ${C.ok} 不该：写 RULES.md / governance-philosophy.json / rules.json（写出口白名单只含 data/reflect 与 logs）`);
  L.push(`  ${C.ok} 不该：设备名带路径穿越（../ 、/ 、空白、前导点）—— 设备名门同时挡黑板 key 与本地路径`);
  L.push(`  ${C.ok} 不该：把别的设备的事件算到本设备头上（device_mismatch 拒绝）或把同一份文件算两遍（sync_duplicate 剔除）`);
  L.push(`  ${C.ok} 不该：改/删上游回填文件、代上游建目录（找不到回填 → IO 错误 exit 2，不猜不建）`);
  L.push(`  ${C.ok} 不该：把"弃权"当合法回填（declined:true 必须给理由，否则 invalid_decline）`);
  L.push('');

  L.push('【③ CLD 自适应】无 CLD / 无网也能给出结论');
  L.push(`  ${C.ok} 运行期依赖：node ${process.version} 内置模块（fs/path/os/crypto/util/http/https）+ 无任何外部命令`);
  L.push(`  ${C.ok} 中央黑板不可达 → 逐设备报错并**继续用本地数据**（降级，不是抛栈）；--local-only 完全不触网`);
  L.push(`  ${C.ok} 不 import 宿主私有路径；CLI 与插件挂载点解耦，可独立运行`);
  L.push('');

  L.push('【③ 依赖完整性 / ④ dsh 版本自适应】两级解析（本目录 → profile/node_modules）');
  for (const p of sc.peers || []) L.push(`  ${p.ok ? C.ok : C.no} ${p.peer}${p.version ? '@' + p.version : ''} via=${p.via || '-'}`);
  L.push(`  ${sc.ok ? C.ok : C.no} R014 自查门: missing=${sc.missing.length} warnings=${sc.warnings.length}`);
  sc.missing.forEach((m) => L.push(`      ${C.no} ${m}`));
  (sc.notes || []).forEach((n) => L.push(`      · ${n}`));

  L.push('');
  L.push(`设备层: 设备表默认 [${DEFAULT_DEVICES.join(', ')}]（${DEVICES_META.registryPath} 可覆盖）· 设备名规则 ${DEVICES_META.nameRule}`);
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

  // B. 负例全部被拒 + 无削弱入口
  const negEv = evidenceNegativeCases();
  const negShape = shapeNegativeCases();
  const negBrand = brandNegativeCases();
  const negWrite = writeTargetNegativeCases();
  const negDev = deviceNegativeCases();
  const negWriteLeak = negWrite.filter((n) => n.code === null);
  const negDevLeak = negDev.filter((n) => n.code === null);
  const leaked = [...negEv, ...negShape, ...negBrand].filter((n) => n.code === null);
  const nf = assertNoPermissiveFlags();
  checks.push({
    id: 'B 负例全部被拒 + 无削弱入口',
    ok: leaked.length === 0 && nf.ok && negWriteLeak.length === 0 && negDevLeak.length === 0,
    detail: (leaked.length
      ? `竟然放行: ${JSON.stringify(leaked)}`
      : `证据负例 ${negEv.length}/${negEv.length} 被拒 · 字段/类型负例 ${negShape.length}/${negShape.length} 被拒 · 品牌负例 ${negBrand.length}/${negBrand.length} 被拒（裸对象→UNBRANDED_ENTRY）`) +
      ` · 写门负例 ${negWrite.length - negWriteLeak.length}/${negWrite.length} 被拒（写 RULES.md / governance-philosophy.json / rules.json / ../ 穿越 / 子目录 / 假 kind${negWriteLeak.length ? ' ★竟然放行:' + JSON.stringify(negWriteLeak) : ''}）` +
      ` · 设备名门负例 ${negDev.length - negDevLeak.length}/${negDev.length} 被拒（../ 穿越 / 含斜杠 / 空白 / 前导点或横线 / 超长 / 空值${negDevLeak.length ? ' ★竟然放行:' + JSON.stringify(negDevLeak) : ''}）` +
      ` · 削弱旗标命中 ${nf.hits.length}/${nf.checked.length}`
  });

  // C. 正例可用
  const pos = evidencePositiveCases();
  const posOk = pos.every((p) => p.ok);
  const posWrite = writeTargetPositiveCases();
  const posWriteOk = posWrite.every((p) => p.ok);
  const posDev = devicePositiveCases();
  const posDevOk = posDev.every((p) => p.ok);
  checks.push({
    id: 'C 合法输入可用（证据 / 写目标 / 设备名）',
    ok: posOk && posWriteOk && posDevOk,
    detail: `证据正例 ${pos.filter((p) => p.ok).length}/${pos.length} · 写目标 ${posWrite.filter((p) => p.ok).length}/${posWrite.length} · 设备名 ${posDev.filter((p) => p.ok).length}/${posDev.length}（含 MAC-MINI→mac-mini 归一化、纯数字名 42）`
  });

  // D. --dry-run 零变更（实测 7 项外部状态）
  const probeDate = args.date && DATE_RE.test(args.date) ? args.date : '2026-09-10';
  const snap = () => {
    const h = (p) => { try { return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex').slice(0, 16); } catch { return null; } };
    const dirSnap = (d) => { try { return fs.readdirSync(d).sort().map((f) => `${f}:${fs.statSync(path.join(d, f)).size}`).join('|'); } catch { return null; } };
    return {
      harvested: h(path.join(DATA_DIR, `harvested-${probeDate}.json`)),
      logSize: (() => { try { return fs.statSync(LOG_FILE).size; } catch { return null; } })(),
      rules: h(RULES_PATH),
      philosophy: h(PHILOSOPHY_PATH),
      probeAnswersMac: dirSnap(path.join(TESTDATA_ROOT, 'answers', 'mac-mini', probeDate)),
      probeAnswersMbp: dirSnap(path.join(TESTDATA_ROOT, 'answers', 'mbp', probeDate)),
      liveAnswers: dirSnap(path.join(DATA_DIR, 'answers'))
    };
  };
  let dOk = false, dDetail = '', probeErr = null, invOk = true, invBad = [];
  try {
    const before = snap();
    const payload = await harvest(probeDate, {
      dryRun: true, localRoot: TESTDATA_ROOT, localOnly: true,   // 只读包内 testdata，且完全不触网
      devices: ['mac-mini', 'mbp', 'lab-mbp', 'i9'], localDevice: 'mac-mini'
    });
    const plan = writeHarvested(probeDate, payload, { dryRun: true });
    const after = snap();
    const diffs = Object.keys(before).filter((k) => before[k] !== after[k]);

    // ★ 产出不变量（自洽性）—— 这一组**本该**在开发期就抓住 recurrence 少算的 bug，
    //   它检查的是"同一份输出里两个字段互相矛盾"，而这正是最容易被漏掉的一类错。
    const inv = [];
    for (const c of payload.clusters) {
      if (c.recurrence !== c.agents.length) inv.push(`${c.cluster_id}: recurrence=${c.recurrence} ≠ agents 数=${c.agents.length}（明细与计数矛盾）`);
      if (c.recurrence > c.item_count) inv.push(`${c.cluster_id}: recurrence ${c.recurrence} > 条目数 ${c.item_count}`);
      if (c.cross_device !== (c.devices.length >= 2)) inv.push(`${c.cluster_id}: cross_device=${c.cross_device} 与 devices=${c.devices.length} 矛盾`);
      for (const a of c.agents) if (!a.includes(':')) inv.push(`${c.cluster_id}: agents 项 '${a}' 缺 <device>: 前缀`);
      if (c.sync_duplicate_members.some((k) => c.agents.includes(k))) inv.push(`${c.cluster_id}: 同步盘重复项仍被计入 agents`);
    }
    const sumValid = Object.values(payload.per_device).reduce((n, a) => n + a.items_valid, 0);
    if (sumValid !== payload.items_valid) inv.push(`per_device 有效数之和 ${sumValid} ≠ items_valid ${payload.items_valid}`);
    const sumRej = Object.values(payload.per_device).reduce((n, a) => n + a.items_rejected, 0);
    if (sumRej !== payload.items_rejected) inv.push(`per_device 拒收数之和 ${sumRej} ≠ items_rejected ${payload.items_rejected}`);
    if (payload.devices_submitted + payload.devices_pending > payload.devices_total) inv.push('submitted+pending > total');
    invOk = inv.length === 0; invBad = inv;

    dOk = diffs.length === 0;
    dDetail = (dOk
      ? `dry-run 前后 **7 项**外部状态完全一致（产物 / 日志大小 / RULES.md / 哲学库 / 包内 testdata×2 / 实盘 answers）· 计划写入 ${plan.target}（${plan.bytes}B，未写）· 只用包内 testdata + --local-only（零出站）`
      : `发生变更: ${diffs.map((k) => `${k}: ${before[k]} → ${after[k]}`).join('; ')}`) +
      `\n      ★ 产出不变量: ${invOk ? `全部自洽（${payload.clusters.length} 簇：recurrence=agents 数 / cross_device↔devices / 同步盘重复项不计入 / 分设备求和=全局）` : `★ 自相矛盾 ${inv.length} 处: ${invBad.join(' | ')}`}`;
  } catch (e) {
    probeErr = e;
    dDetail = `dry-run 实测无法执行：${e.name} ${e.code || ''} ${e.message}`.slice(0, 300);
  }
  checks.push({ id: 'D --dry-run 零变更 + 产出不变量自洽', ok: dOk && invOk, detail: dDetail });

  // E. 白名单冻结
  const frozenOk = Object.isFrozen(SUGGESTION_TYPES) && Object.isFrozen(ALL_REJECT_REASONS) &&
    Object.isFrozen(ALLOWED_COMMANDS) && Object.isFrozen(GATE_META) && Object.isFrozen(OPTIONS_META) &&
    Object.isFrozen(SYNC_DUP_RULE) && Object.isFrozen(HTTP_META) && Object.isFrozen(DEVICES_META) && Object.isFrozen(DEFAULT_DEVICES);
  checks.push({
    id: 'E 白名单冻结',
    ok: frozenOk,
    detail: `frozen=${frozenOk} · types=[${SUGGESTION_TYPES.join(',')}] · 拒收原因 ${ALL_REJECT_REASONS.length} 条 · 命令白名单=[] · syncDup window=${SYNC_DUP_RULE.windowMs}ms · HTTP 方法=[${HTTP_META.allowedMethods.join(',')}]`
  });

  // F. 命令白名单 + 扫描器正控 + HTTP 原语收口 + 写出口收口
  const st = scannerSelfTest();
  const ht = httpScannerSelfTest();
  const nonBenign = EXEC_SITES.filter((s) => !s.benign);
  const benignSites = EXEC_SITES.filter((s) => s.benign);
  const bad = nonBenign.filter((s) => !s.literal || !ALLOWED_COMMANDS.includes(s.cmd));
  const HTTP_SITES = scanHttpSites({ sources: SOURCES });
  const WRITE_SITES = scanWriteSites({ sources: SOURCES });
  const strayWrites = WRITE_SITES.filter((s) => s.file !== 'lib/out.js');
  const forbiddenInWrite = WRITE_SITES.filter((s) =>
    s.sourceLine.includes('RULES.md') || s.sourceLine.includes('governance-philosophy.json') ||
    s.sourceLine.includes('rules.json') || s.sourceLine.includes('gallery'));
  checks.push({
    id: 'F 命令白名单 + 扫描器正控 + HTTP 原语收口',
    ok: st.ok && ht.ok && bad.length === 0 && HTTP_SITES.length === 0 && strayWrites.length === 0 && forbiddenInWrite.length === 0,
    detail: (!st.ok ? `★ exec 扫描器正控失败: ${st.detail}` : `${st.detail}`) +
      ` · 本包非良性 exec 调用点 ${nonBenign.length}（良性 ${benignSites.length}：${benignSites.map((s) => `${s.file}:${s.line}`).join(', ') || '无'}）⊆ [${ALLOWED_COMMANDS.join(',') || '空集'}]` +
      ` · ${ht.detail}；本包通用 HTTP/套接字调用点 **${HTTP_SITES.length}**（期望 0 —— 出站只能走 httpGetJson 的 http.get）` +
      ` · 写调用点 ${WRITE_SITES.length} 个全部位于 [lib/out.js]（越界 ${strayWrites.length}）· 写语句命中治理库禁用词 ${forbiddenInWrite.length} 次`
  });

  const ok = checks.every((c) => c.ok);
  if (args.json) {
    out(JSON.stringify({
      ok, checks, version: VERSION, gate: GATE_META, http: HTTP_META, devices: DEVICES_META,
      permissiveFlagProof: nf,
      scanner: { exec: { ok: st.ok, detail: st.detail, sites: EXEC_SITES }, http: { ok: ht.ok, detail: ht.detail, sites: HTTP_SITES }, writeSites: WRITE_SITES.length }
    }, null, 1));
  } else {
    out(`lean4-check · 结构门自证（${GATE_META.principle}）`);
    for (const c of checks) out(`  ${c.ok ? C.ok : C.no} ${c.id}\n      ${c.detail}`);
    out('');
    out(ok ? `${C.ok} 结构门生效：约束不可绕过（没有那个入口 + 有那个证明）`
      : `${C.no} 门未生效，禁止交付${probeErr ? `（D 项探测异常：${probeErr.name}）` : ''}`);
  }
  log(`lean4-check ok=${ok} ` + JSON.stringify(checks.map((c) => `${c.id.split(' ')[0]}:${c.ok}`)), undefined, { dryRun: args['dry-run'] === true });
  process.exit(ok ? 0 : 1);
}

/* --------------------------------- 主流程 --------------------------------- */
const date = args.date || new Date().toISOString().slice(0, 10);
if (!DATE_RE.test(date)) { out(`用法错误: --date 必须是 YYYY-MM-DD，收到 '${date}'`); process.exit(2); }

let payload;
try {
  payload = await harvest(date, {
    dryRun: args['dry-run'],
    devices: devicesFromArgs(),
    localDevice: args.device,
    localRoot: args['local-root'],
    central: args.central,
    localOnly: args['local-only'],
    allowLate: args['allow-late']
  });
} catch (e) {
  if (e instanceof HarvestIOError) { out(`${C.no} IO 错误 [${e.code}] ${e.message}`); process.exit(2); }
  if (e instanceof GateError) { out(`${C.no} 门拒绝 [${e.code}] ${e.message}`); process.exit(1); }
  out(`${C.no} 失败: ${e.stack || e.message}`); process.exit(1);
}

let writeResult;
try {
  writeResult = writeHarvested(date, payload, { dryRun: args['dry-run'] });
} catch (e) {
  if (e instanceof GateError) { out(`${C.no} 写门拒绝 [${e.code}] ${e.message}`); process.exit(1); }
  throw e;
}

if (args.json) {
  out(JSON.stringify({ ...payload, dryRun: args['dry-run'], outputFile: args['dry-run'] ? null : writeResult.target, version: VERSION }, null, 1));
} else if (args.summary) {
  out(formatSummary(payload));
  out('');
  out(args['dry-run'] ? `${C.warn} [dry-run] 未写入任何文件；计划产物: ${writeResult.target}（${writeResult.bytes}B）`
    : `${C.ok} 已写入 ${writeResult.target}（${writeResult.bytes}B）`);
  out(`   统一日志: ${LOG_FILE}`);
} else {
  out(`设备 ${payload.devices_submitted}/${payload.devices_total} 已回填 · ${payload.devices_pending} pending` +
    `${payload.pending_devices.length ? `（${payload.pending_devices.join(', ')}）` : ''}`);
  out(`${payload.items_valid} valid / ${payload.items_rejected} rejected（条目级）· ${payload.files_rejected} 文件级拒收 · ${payload.clusters.length} 簇` +
    `（跨设备 ${payload.clusters.filter((c) => c.cross_device).length}）`);
  out(args['dry-run'] ? `[dry-run] 未写入；计划产物: ${writeResult.target}` : `已写入 ${writeResult.target}`);
  out('（加 --summary 看按设备分组 + 拒收原因分布 + 跨设备复现排序）');
}
process.exit(0);
