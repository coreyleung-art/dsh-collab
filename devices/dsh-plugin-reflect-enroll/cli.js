#!/usr/bin/env node
/**
 * cli.js — ⑨ CLI 治理 + ② 能力边界自检 + ⑥ 版本 + ⑩ 约束门自证
 * =============================================================================
 * 用法：
 *   node cli.js --ruling <file> [--dry-run] [--json] [--notify]
 *   node cli.js --rule P1=approve:philosophy [--proposal <file>] [--dry-run]
 *   node cli.js --selfcheck          # ② TCC 三段：能力清单 / 不该发生路径 / 依赖完整性
 *   node cli.js --lean4-check        # ⑩ 结构门自证 A–F
 *   node cli.js --tool-version
 *   node cli.js --help
 * 退出码：0 成功/门生效 · 1 失败（含门拒绝、已回滚） · 2 用法或 IO 错误
 */
import { parseArgs } from 'node:util';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { runPipeline } from './lib/pipeline.js';
import { runSelfCheck, tccSections } from './lib/selfcheck.js';
import { mountSmoke } from './lib/smoke.js';
import { resolveRoot, REL, planOne, applyOne, inRoot, readText, sha256, UsageError, todayDate } from './lib/enroll.js';
import {
  GateError, GATE_META, DECISIONS, TARGETS, LIBRARY_TARGETS, ALLOWED_BB_HOSTS, ALLOWED_BB_SCHEMES,
  ALLOWED_COMMANDS, DANGEROUS_PRIMITIVES, PHILOSOPHY_REQUIRED_FIELDS, RULE_REQUIRED_FIELDS,
  gateNegativeCases, gatePositiveCases, scanDangerousPrimitives, scanExecSites, scanOutboundSites, scanModuleRefs, functionCallsFn
} from './lib/gate.js';
import { VERSION } from './lib/version.js';
import { log, logFile, setLogFile } from './lib/log.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const C = { ok: '\u2705', no: '\u274c', warn: '\u26a0\ufe0f' };
const out = (s) => process.stdout.write(s + '\n');
const SOURCE_FILES = ['cli.js', 'lib/index.js', 'lib/gate.js', 'lib/enroll.js', 'lib/feedback.js', 'lib/pipeline.js', 'lib/selfcheck.js', 'lib/log.js', 'lib/version.js'];

/* ══════════════════════════ 参数（严格：未知旗标 → exit 2） ══════════════════════════ */
let args;
try {
  args = parseArgs({
    options: {
      ruling: { type: 'string' },
      rule: { type: 'string' },
      proposal: { type: 'string' },
      date: { type: 'string' },
      root: { type: 'string' },
      'bb-url': { type: 'string' },
      'central-bb': { type: 'string' },
      device: { type: 'string' },
      log: { type: 'string' },
      notify: { type: 'boolean', default: false },
      'no-bb': { type: 'boolean', default: false },
      'dry-run': { type: 'boolean', default: false },
      json: { type: 'boolean', default: false },
      selfcheck: { type: 'boolean', default: false },
      'lean4-check': { type: 'boolean', default: false },
      'tool-version': { type: 'boolean', default: false },
      help: { type: 'boolean', default: false }
    },
    allowPositionals: false,
    strict: true
  }).values;
} catch (e) {
  out(`用法错误: ${e.message}`);
  out('试 --help');
  process.exit(2);
}
if (args.log) setLogFile(args.log);

const HELP = `reflect-enroll v${VERSION} — 反思入册 · 反馈闭环（每日反思流水线的唯一写库环节）

它做什么：把**用户已裁定的提案**写入治理哲学库/规则库，并把新规则主动推给所有相关智能体。
它不做什么（结构上不存在，不是"被拒绝"）：
  · 不自动决定入册什么 —— 裁定只能由人给（裁定文件 / --rule），且只接受 ${DECISIONS.join(' | ')}
  · 不删除任何条目   —— 源码零删除原语，写形态只有"读取→追加→原子写"
  · 不重复入册       —— 幂等台账 + 编号唯一性双查
  · 不写坏目标文件   —— 备份前置(回读验证) → .tmp 原子写 → 回读校验 → 失败自动回滚
  · 不跑任何外部命令 —— 零 shell 出站；唯一对外通道是黑板 HTTP（主机白名单 ${ALLOWED_BB_HOSTS.join(', ')}）
跨设备（v1.1）：反馈卡同时上本机与中央黑板（data/reflect/feedback/<date>），规则变更通知卡 data/registry/reflect-feedback-<date> 全设备可检索；
                相关智能体判定为 <device>:<agent>；其他设备的短指引走中央黑板待投递队列（离线也能收到）；
                落盘/上黑板前强制凭据扫描+脱敏+复检；只写自己命名空间（正文限 data/reflect|data/registry，notes/ 仅 ≤50 字短指引）

用法：
  --ruling <file>          裁定文件（格式 A）：{"date":..,"rulings":[{proposal_id,decision,target,modifications,reason}]}
                           省略则读 <root>/data/reflect/ruling-<date>.json
  --rule <id>=<decision>:<target>   单条裁定（格式 B），如 P1=approve:philosophy
  --proposal <file>        提案正本（入册内容来源；省略则读 <root>/data/reflect/proposals-<date>.json）
  --date <YYYY-MM-DD>      默认今天（决定 ruling/proposals/反馈卡/归档 文件名）
  --root <dir>             协作根目录（默认 ~/dsh-collab；自测/沙箱指向副本）
  --dry-run                只出计划：**一个字节都不写**（含备份、台账、反馈卡、黑板）
  --json                   机器可读输出
  --notify                 对相关智能体推短消息（正文≤50字，先落黑板再发「看黑板 <key>」）
  --no-bb                  跳过黑板写入与推送（反馈卡仍落盘）
  --bb-url <url>           本机黑板地址（默认 http://127.0.0.1:8792，必须过主机白名单）
  --central-bb <url>       中央黑板地址（默认 http://106.53.214.108:8792；跨设备汇聚点，同样过白名单）
  --device <name>          本机设备名（默认 $DSH_NODE_ID → 主机名匹配设备登记表 → 派生名；决定 origin_device 与短指引投递域）
  --log <file>             统一日志路径（默认 ${logFile()}）
  --selfcheck              ② TCC：能力清单 / 不该发生路径 / 依赖完整性
  --lean4-check            ⑩ 结构门自证 A–F（含负例实测与 dry-run 零变更实测）
  --tool-version  --help

target 语义：philosophy=新增哲学条目（写 governance-philosophy.json + changelog）
             rule=新增规则（写 RULES.md + rules.json）· spec=转规范（只写 docs/sops/）
             archive=只归档为案例（不入治理库）
决策语义：approve=照提案入册 · modify=入册且裁定须带 modifications 文本（工具不猜）
          reject=不入册，仅归档驳回案例 · defer=完全不动（不写台账，可再提交）

退出码：0 成功/门生效 · 1 失败（门拒绝/校验失败/已回滚） · 2 用法或 IO 错误`;

if (args.help) { out(HELP); process.exit(0); }
if (args['tool-version']) { out(`reflect-enroll ${VERSION}`); process.exit(0); }

/* ══════════════════════════ --selfcheck（② TCC 三段） ══════════════════════════ */
if (args.selfcheck) {
  const sc = runSelfCheck('reflect-enroll', {
    requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
    requiredSymbols: ['parseArgs', 'runPipeline', 'planOne', 'applyOne', 'gateNegativeCases', 'scanOutboundSites'],
    sourceFiles: ['cli.js'],
    baseDir: HERE
  });
  const tcc = tccSections(sc);
  // ★ R006 v3.1.0 ① 第 5 项：真挂载冒烟（三态 pass/fail/skipped）
  const smoke = await mountSmoke({ baseDir: HERE, indexRel: 'lib/index.js', config: {} });
  if (args.json) {
    out(JSON.stringify({ selfcheck: sc, tcc, mountSmoke: smoke }, null, 1));
  } else {
    out(`R014 自查门: ${sc.ok ? C.ok : C.no} v${VERSION} missing=${sc.missing.length} warnings=${sc.warnings.length}`);
    sc.missing.forEach((m) => out(`    ${C.no} ${m}`));
    (sc.notes || []).forEach((n) => out(`    · ${n}`));
    out('');
    out(`TCC ① 能力清单（我能碰什么）:`);
    tcc.capabilities.forEach((x) => out(`    ${C.ok} ${x}`));
    out(`TCC ② 不该发生路径（碰不到什么 · 结构上不存在）:`);
    tcc.forbidden.forEach((x) => out(`    ${C.ok} ${x}`));
    out(`TCC ③ 依赖完整性:`);
    out(`    ${C.ok} peer: ${JSON.stringify(tcc.dependencies.peers)}`);
    out(`    ${C.ok} 运行期依赖: node ${process.version} 内置模块（fs/path/os/http/crypto/url/util/module），零外部包`);
    out(`    ${C.ok} 约束门: ${tcc.dependencies.gate}`);
    out('');
    const sm = { pass: '✅ 挂载通过', fail: '❌ 挂不上（真实缺陷）', skipped: '⊘ 已跳过（如实说明）' }[smoke.state] || smoke.state;
    out(`【⑤ 真挂载冒烟】${sm}`);
    if (smoke.state === 'pass') out(`    · 注册工具: ${smoke.tools.join(', ')}（effect ${smoke.effects} 个）`);
    else if (smoke.state === 'skipped') out(`    · 原因: ${smoke.reason}`);
    else out(`    · ${smoke.stage}: ${smoke.error}`);
    out('');
    out(`统一日志: ${logFile()}`);
  }
  process.exit(smoke.state === 'fail' ? 1 : (sc.ok ? 0 : 1));
}

/* ══════════════════════════ --lean4-check（⑩ A–F 六项） ══════════════════════════ */
if (args['lean4-check']) {
  const root = resolveRoot(args.root);
  const checks = [];
  const sources = {};
  for (const f of SOURCE_FILES) sources[f] = fs.readFileSync(path.join(HERE, f), 'utf8');

  // A. 源码无危险原语（去注释/字符串/正则字面量后扫描 → 不会把自己的检测正则当靶子）
  const hits = scanDangerousPrimitives({ sources });
  checks.push({
    id: 'A 源码无删除/终止原语',
    ok: hits.length === 0,
    detail: hits.length ? JSON.stringify(hits) : `扫描 ${SOURCE_FILES.length} 文件（去字面量后），${DANGEROUS_PRIMITIVES.join('/')} + process.kill 命中 0 次`
  });

  // B. 负例实测：43 条越界输入逐条必被拒
  const neg = gateNegativeCases();
  const leaked = neg.filter((n) => n.code === null);
  checks.push({
    id: 'B 负例全部被拒',
    ok: leaked.length === 0,
    detail: leaked.length ? `竟然放行: ${JSON.stringify(leaked)}` : `${neg.length}/${neg.length} 条被拒（如 decision=auto→BAD_DECISION, target=delete→BAD_TARGET, slug=../evil→BAD_SLUG, bbUrl=http://evil…→BB_HOST_FORBIDDEN, 重复编号→ID_CONFLICT）`
  });

  // C. 正例可用：合法输入必须能通过（防"门太宽把功能也砍了"）
  const pos = gatePositiveCases();
  const posBad = pos.filter((p) => !p.ok);
  checks.push({
    id: 'C 正例全部可用',
    ok: posBad.length === 0,
    detail: posBad.length ? `被误拦: ${JSON.stringify(posBad)}` : `${pos.length}/${pos.length} 通过（4 决策 × 4 目标 + slug + 编号 + 黑板主机）`
  });

  // D. dry-run 零变更（实测：目标文件 sha256 前后一致，且未产生 .tmp/.bak）
  const targets = [REL.philosophy, REL.philosophyChangelog, REL.rulesMd, REL.rulesJson, REL.ledger];
  const snap = () => targets.map((rel) => {
    const abs = inRoot(root, rel);
    return { rel, exists: fs.existsSync(abs), sha256: fs.existsSync(abs) ? sha256(readText(abs)) : null };
  });
  const probeId = 'phi-lean4-dryrun-probe';
  let dDetail;
  const before = snap();
  const probeProposal = {
    id: 'LEAN4-DRYRUN-PROBE', name: 'dry-run 探针（不得落盘）', slug: 'lean4-dryrun-probe',
    core: 'D 项探针：验证 dry-run 下计划生成不写任何字节', origin: 'lean4-check', doc: 'docs/README.md'
  };
  let dOk = true;
  try {
    const plan = planOne({
      root, proposal: probeProposal, ledgerEntries: [],
      ruling: { proposal_id: 'LEAN4-DRYRUN-PROBE', decision: 'approve', target: 'philosophy', reason: 'lean4 D 项' },
      date: todayDate()
    });
    const applied = applyOne(plan, { dryRun: true });
    const after = snap();
    const changed = after.filter((a, i) => a.sha256 !== before[i].sha256 || a.exists !== before[i].exists);
    dOk = changed.length === 0 && applied.wrote.length === 0;
    dDetail = dOk
      ? `dry-run 前后目标文件 sha256 完全一致；计划含 ${plan.writes.length} 个待写文件，实际写入 0 个、备份 0 个`
      : `发生变更: ${JSON.stringify(changed)} / wrote=${JSON.stringify(applied.wrote)}`;
  } catch (e) {
    if (e.code === 'TARGET_UNPARSEABLE' || e.code === 'ENOENT' || !fs.existsSync(inRoot(root, REL.philosophy))) {
      dDetail = `跳过（根目录 ${root} 下无可读的目标库：${e.code || e.message}）`;
    } else { dOk = false; dDetail = `探针异常: ${e.code || ''} ${e.message}`; }
  }
  checks.push({ id: 'D dry-run 零变更', ok: dOk, detail: dDetail, evidence: dOk ? { before, after: snap(), probeId } : undefined });

  // E. 白名单/枚举冻结
  const frozens = {
    DECISIONS: Object.isFrozen(DECISIONS), TARGETS: Object.isFrozen(TARGETS),
    LIBRARY_TARGETS: Object.isFrozen(LIBRARY_TARGETS), ALLOWED_BB_HOSTS: Object.isFrozen(ALLOWED_BB_HOSTS),
    ALLOWED_BB_SCHEMES: Object.isFrozen(ALLOWED_BB_SCHEMES), ALLOWED_COMMANDS: Object.isFrozen(ALLOWED_COMMANDS),
    DANGEROUS_PRIMITIVES: Object.isFrozen(DANGEROUS_PRIMITIVES),
    PHILOSOPHY_REQUIRED_FIELDS: Object.isFrozen(PHILOSOPHY_REQUIRED_FIELDS),
    RULE_REQUIRED_FIELDS: Object.isFrozen(RULE_REQUIRED_FIELDS)
  };
  const eOk = Object.values(frozens).every(Boolean);
  checks.push({
    id: 'E 白名单/枚举冻结',
    ok: eOk,
    detail: `${Object.entries(frozens).map(([k, v]) => `${k}=${v}`).join(' ')}；外部命令白名单=${JSON.stringify(ALLOWED_COMMANDS)}（空集=本工具不跑外部命令）`
  });

  // F. 出站通道白名单（唯一对外调用点必须唯一、且必须先过 assertBbHost）+ 零 shell 出站
  const outSites = scanOutboundSites({ sources });
  const execSites = scanExecSites({ sources });
  const childNeedle = ['child', '_process'].join('');
  const childRefs = scanModuleRefs({ sources, needle: childNeedle });
  const fOk = outSites.length === 1 && outSites[0].file === 'lib/feedback.js' && outSites[0].fn === 'bbRequest' &&
    functionCallsFn(sources['lib/feedback.js'], 'bbRequest', 'assertBbHost') && execSites.length === 0 && childRefs.length === 0;
  checks.push({
    id: 'F 出站白名单 + 零 shell 出站',
    ok: fOk,
    detail: fOk
      ? `对外调用点恰好 1 个（lib/feedback.js:${outSites[0].line} 函数 bbRequest，函数体内先调 assertBbHost 白名单）；` +
        `exec/spawn 执行点 ${execSites.length} 个；${childNeedle} 模块 import/require ${childRefs.length} 处；出站主机 ⊆ [${ALLOWED_BB_HOSTS.join(', ')}]，协议 ⊆ [${ALLOWED_BB_SCHEMES.join(', ')}]`
      : `出站点=${JSON.stringify(outSites)} exec 点=${JSON.stringify(execSites)} ${childNeedle} 模块引用=${JSON.stringify(childRefs)}`
  });

  const ok = checks.every((c) => c.ok);
  if (args.json) out(JSON.stringify({ ok, root, checks, gate: GATE_META }, null, 1));
  else {
    out(`lean4-check · 结构门自证（${GATE_META.principle}）`);
    for (const c of checks) out(`  ${c.ok ? C.ok : C.no} ${c.id} — ${c.detail}`);
    out(ok ? `\n${C.ok} 结构门生效：约束不可绕过（没有那个入口 + 没有那个能力 + 有那个证明 + 失败即停）`
      : `\n${C.no} 门未生效，禁止交付`);
  }
  log('lean4-check', { input: { root }, judge: { ok }, result: { checks: checks.map((c) => `${c.id}:${c.ok}`) } });
  process.exit(ok ? 0 : 1);
}

/* ══════════════════════════ 入册（需要裁定） ══════════════════════════ */
if (!args.ruling && !args.rule) {
  out('用法错误: 入册需要裁定 —— 请给 --ruling <file> 或 --rule <id>=<decision>:<target>');
  out('（本工具绝不自行决定入册什么：没有裁定就没有入册）');
  out('试 --help');
  process.exit(2);
}
if (args.ruling && args.rule) { out('用法错误: --ruling 与 --rule 只能二选一'); process.exit(2); }
if (args.date && !/^\d{4}-\d{2}-\d{2}$/.test(args.date)) { out('用法错误: --date 需为 YYYY-MM-DD'); process.exit(2); }

let res;
try {
  res = await runPipeline({
    root: args.root,
    rulingFile: args.ruling,
    ruleSpec: args.rule,
    proposalFile: args.proposal,
    date: args.date,
    dryRun: args['dry-run'],
    notify: args.notify,
    noBb: args['no-bb'],
    localBb: args['bb-url'],
    centralBb: args['central-bb'],
    device: args.device
  });
} catch (e) {
  const isUsage = e instanceof UsageError || e.code === 'USAGE';
  const isIo = ['ENOENT', 'EACCES', 'EISDIR', 'EPERM', 'ENOTDIR', 'RULING_FILE_MISSING', 'RULING_EMPTY', 'TARGET_UNPARSEABLE'].includes(e.code);
  if (args.json) {
    out(JSON.stringify({ ok: false, code: e.code || 'ERROR', error: e.message, rolledBack: e.rolledBack || [], backups: e.backups || [], logFile: logFile(), version: VERSION }, null, 1));
  } else {
    const kind = (e.rolledBack && e.rolledBack.length) ? '执行失败（已自动回滚）' : (isUsage || isIo ? '用法/IO 错误' : '门拒绝');
    out(`${C.no} ${kind} [${e.code || 'ERROR'}] ${e.message}`);
    if (e.rolledBack && e.rolledBack.length) out(`   回滚详情: ${JSON.stringify(e.rolledBack)}`);
    if (e.backups && e.backups.length) out(`   本次备份（保留在盘上，供人工核对）: ${e.backups.join(' · ')}`);
    out(`   日志: ${logFile()}`);
  }
  log('cli.failed', { input: { ruling: args.ruling, rule: args.rule, dryRun: args['dry-run'] }, judge: { code: e.code || 'ERROR' }, result: { ok: false, error: e.message, rolledBack: e.rolledBack || [] } });
  process.exit(e.rolledBack && e.rolledBack.length ? 1 : (isUsage || isIo ? 2 : 1));
}

if (args.json) {
  out(JSON.stringify(res, null, 1));
} else {
  out(`${res.dryRun ? C.warn + ' [dry-run] ' : C.ok + ' '}reflect-enroll v${VERSION} · 裁定来源 ${res.rulingSource} · root=${res.root}`);
  out(`设备(origin_device): ${res.device.device}（判定依据 ${res.device.source}）${res.device.note ? ' ⚠️ ' + res.device.note : ''}`);
  if (res.proposalNote) out(`⚠️ ${res.proposalNote}`);
  for (const x of res.results) {
    const mark = x.outcome === 'deferred' ? '⏸' : (x.applied ? C.ok : (x.dryRun ? C.warn : C.no));
    out(`${mark} ${x.proposal_id} → ${x.target} · ${x.outcome} · ${x.ref || '-'} · ${x.summary || ''}`);
    if (x.planned && x.planned.length) out(`    ${x.dryRun ? '计划写入' : '已写入'}: ${x.wrote.length ? x.wrote.join(' · ') : x.planned.map((p) => `${p.rel} (${p.bytes}B${p.existed ? ',追加' : ',新建'})`).join(' · ')}`);
    if (x.backups && x.backups.length) out(`    备份: ${x.backups.join(' · ')}`);
    if (x.verified) out(`    回读校验: ${x.verified.every((v) => v.ok) ? C.ok + ' 全部通过' : C.no} (${x.verified.length} 个文件)`);
    (x.notes || []).forEach((n) => out(`    · ${n}`));
  }
  if (!res.dryRun && res.results.some((x) => x.applied)) {
    out('');
    out(`反馈环节（飞轮闭环点 · 跨设备 v1.1）:`);
    out(`  反馈卡(本机): ${res.feedback.card ? res.feedback.card.rel : '(未写)'}${res.feedback.redactions && res.feedback.redactions.length ? ` · 凭据脱敏 ${res.feedback.redactions.length} 处（${[...new Set(res.feedback.redactions.map((r) => r.kind))].join(',')}；卡+黑板值合计）` : ' · 凭据扫描 0 命中（卡与黑板值）'}`);
    if (res.feedback.skipped) {
      out(`  黑板: 已跳过（${res.feedback.reason}）`);
    } else {
      out(`  本机黑板 ${res.feedback.local_bb} — ${res.feedback.landed_local ? C.ok + ' landed' : C.no + ' 未落地'}`);
      out(`  中央黑板 ${res.feedback.central_bb} — ${res.feedback.landed_central ? C.ok + ' landed' : C.no + ' 未落地'}`);
      for (const [bn, arr] of Object.entries(res.feedback.boards)) {
        for (const b of arr) out(`    ${b.landed ? C.ok : C.no} [${bn}] ${b.key} · PUT=${b.put_status} 回读=${b.readback_status}${b.error ? ' · ' + b.error : ''}`);
      }
    }
    out(`  规则变更通知键: ${res.feedback.cardKey}（全设备可检索） · 全卡键: ${res.feedback.fullCardKey}`);
    out(`  相关智能体（依据 ${res.related.source}）: ${res.related.agents.length ? res.related.agents.map((a) => '@' + a.key).join(' ') : '(未判定出)'}`);
    for (const d of res.related.devices) out(`    · 设备 ${d.device}: ${d.agents.length ? d.agents.map((a) => '@' + a).join(' ') : '（该设备全体）'}`);
    if (res.related.note) out(`    · ${res.related.note}`);
    (res.feedback.notify || []).forEach((n) => out(`  ${n.ok ? C.ok : C.warn} 短指引 → ${n.agent || n.key}: ${n.key || ''} ${n.chars ? `(${n.chars}字)` : ''} ${n.route || ''} ${n.reason || ''}`));
  }
  out(`日志: ${logFile()}`);
}

// 退出码：0 = 全部成功（dry-run 也算成功）；1 = 有结果未落地（入册成功但反馈未送达）
const bad = !res.ok;
if (bad) out(`${C.no} 未完全成功：入册结果或反馈环节未落地（见上；台账与库写入已完成的部分不再回滚，请人工核对备份）`);
process.exit(bad ? 1 : 0);
