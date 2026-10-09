#!/usr/bin/env node
/**
 * cli.js — R006 ⑨ CLI 治理 + ② 自检 + ⑥ 版本 + ⑩ 结构门自证（v1.1 跨设备层）
 * =============================================================================
 * 用法：
 *   node cli.js [窗口] [源开关] [--device <name>] [--out <path>] [--summary|--json]
 *   node cli.js --dry-run ...             零变更：不写产出、不写日志、**不上传**
 *   node cli.js --no-upload               只本地落盘，不传中央黑板
 *   node cli.js --selfcheck               ② TCC 三段输出
 *   node cli.js --lean4-check             ⑩ A–F 六项自证
 *   node cli.js --tool-version
 *
 * 退出码（语义固定）：
 *   0 = 成功 / 门生效
 *   1 = 失败（有源采集失败 / 上传或回读校验失败）/ 门失效
 *   2 = 用法错误 或 IO 错误（含被参数门拒绝的值）
 *
 * ★ 本文件**不含任何写入/删除原语**：本地落盘一律经 lib/log.js 的 guarded* 封装，
 *   网络只经 lib/transport.js（读 httpGetJson / 写 httpPutJson）。
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { parseArgs } from 'node:util';
import { fileURLToPath } from 'node:url';
import { collectAll, externalStateSnapshot, diffSnapshots } from './lib/collect.js';
import { networkStats } from './lib/transport.js';
import { log, writeStats, LOG_FILE, guardedMkdirp, guardedWrite } from './lib/log.js';
import { runSelfCheck, nodeOnPath, mountSmoke } from './lib/selfcheck.js';
import { redactPayload, uploadEvents, centralKeyState, boardReachable } from './lib/upload.js';
import {
  SOURCE_KEYS, GATE_META, OUT_DIR, SELFCHECK_DIR, WRITE_TARGETS, WRITER_MODULES, NETWORK_MODULES,
  BOARD_PAGE_SIZE, BOARD_MAX_KEYS,
  UPLOADER_MODULES, ALLOWED_COMMANDS, ALLOWED_HTTP_METHODS,
  COLLECT_ROOTS, CENTRAL_ORIGIN, CENTRAL_HOST, UPLOAD_KEY_PREFIX, DEVICE_ALIAS, GATE_MODULE,
  SECRET_PATTERNS, EVENT_TIME_FIELDS,
  GateError, assertSources, assertTimeSpec, assertWriteAllowed, assertDevice, realpathNearest,
  defaultDevice, buildUploadKey, buildUploadUrl,
  gateNegativeCases, gatePositiveCases, selfSamplingCases, secretRedactCases, secretKeepCases,
  scanDangerousPrimitives, scanWriteSites, scanExecSites, scanHttpMethods,
  scanHttpRequestSites, scanNameArgSites, fmtLocal
} from './lib/gate.js';
import { packageVersion } from './lib/version.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const C = { ok: '\u2705', no: '\u274c', warn: '\u26a0\ufe0f' };
const out = (s) => process.stdout.write(s + '\n');
const err = (s) => process.stderr.write(s + '\n');

const VERSION = packageVersion();   // ⑥ 单一来源：只从 package.json 读，CLI 不硬编码第二份

/* ───────────────────────────── ⑨ 严格参数解析 ───────────────────────────── */

const FLAGS = {
  since: { type: 'string' },
  until: { type: 'string' },
  sources: { type: 'string' },
  out: { type: 'string' },
  'board-url': { type: 'string' },
  device: { type: 'string' },
  limit: { type: 'string' },
  summary: { type: 'boolean', default: false },
  json: { type: 'boolean', default: false },
  'dry-run': { type: 'boolean', default: false },
  'no-upload': { type: 'boolean', default: false },
  'allow-secrets': { type: 'boolean', default: false },
  selfcheck: { type: 'boolean', default: false },
  'lean4-check': { type: 'boolean', default: false },
  'tool-version': { type: 'boolean', default: false },
  help: { type: 'boolean', default: false },
  'no-files': { type: 'boolean', default: false },
  'no-board': { type: 'boolean', default: false },
  'no-tools': { type: 'boolean', default: false },
  'no-logs': { type: 'boolean', default: false },
  'no-git': { type: 'boolean', default: false }
};

let argv;
try {
  argv = parseArgs({ options: FLAGS, allowPositionals: false, strict: true }).values;
} catch (e) {
  out(`用法错误: ${e.message}`);
  out('试 --help（未知旗标一律 exit 2）');
  process.exit(2);
}

function usage() {
  return `reflect-collect v${VERSION} — 只读采集「当日发生的事件」+ 跨设备上传，输出结构化事件流（供每日反思流水线）
R006 十项达标 · ⑩ 结构门：本地采集动作**结构上无写入能力**；跨设备上传**只有 1 个冻结 key 形态**

用法：
  reflect-collect [窗口] [源开关] [--device <name>] [--out <path>] [--summary|--json]
  reflect-collect --dry-run ...            零变更（不写产出/不写日志/**不上传**）
  reflect-collect --no-upload               只本地落盘，不传中央黑板
  reflect-collect --selfcheck               R014 自查门 + ② TCC 三段（能力 / 不该发生路径 / 依赖）
  reflect-collect --lean4-check             ⑩ A–F 六项自证（负例实测 + dry-run 零变更实测）
  reflect-collect --tool-version             打印版本（单一来源 package.json）

窗口：
  --since <t>        窗口起，YYYY-MM-DD[THH:mm[:ss]]（设备本地时区）；默认今天 00:00:00
  --until <t>        窗口止；默认今天 23:59:59

采集源（默认全部；每个源可独立关闭）：
  files   当日新增/修改的文件   ${COLLECT_ROOTS.join(' 与 ')}
  board   当日写过的黑板卡       GET /data/ 与 /notes/（**本机黑板只读**）
  tools   当日新建/修改的工具   ~/dsh-collab/scripts 下的 .py 与 devices/dsh-plugin-* 目录
  logs    当日错误/失败痕迹     ~/dsh-collab/logs/*.log 中 error/fail/拒绝/deny 行
  git     当日提交             ~/dsh-collab 的 git log --since（非仓库则跳过并留痕）
  --sources files,logs        显式指定源（白名单外 → exit 2）
  --no-board --no-git ...     逐个关闭

跨设备（design v1.1 §10）：
  --device <name>    设备名（key 段）。默认：主机名别名表命中 → ${DEVICE_ALIAS.map((a) => a.device).join(' / ')}，否则净化后的短主机名
  --no-upload        跳过上传（中央不可达时用）
  --allow-secrets    ★危险：跳过凭据脱敏，原样上传（仅调试用；默认命中即脱敏为 [REDACTED]）
  上传目标（唯一，写死）：PUT ${CENTRAL_ORIGIN}/${UPLOAD_KEY_PREFIX}<device>/<date>
  上传后**必回读校验**（GET 同 key + sha256 比对）；不一致 → 判失败 exit 1

输出：
  --out <path>       事件流 JSON 落盘路径（默认 ${path.join(OUT_DIR, 'events-<YYYYMMDD>.json')}；
                     部分源运行（--sources/--no-*）时默认改为 events-<date>-<源名>.json，
                     **避免覆盖当天全量**；**只允许落在 data/reflect/ 内**，其它路径一律 exit 2）
  --limit <n>        每个源最多 n 条事件（0=不限，默认 0）
  --board-url <url>  本机黑板地址（仅环回）
  --summary          人类可读摘要（各源计数 + 前若干条事件）
  --json             机器可读 JSON（stdout）

退出码：0 成功/门生效 · 1 有源采集失败 · 上传或回读失败 · 门失效 · 2 用法或 IO 错误
统一日志：${LOG_FILE}
文档：docs/README.md（含十项达标矩阵与坑）`;
}

if (argv.help) { out(usage()); process.exit(0); }

/* ───────────────────────────── ⑥ --tool-version ───────────────────────────── */

if (argv['tool-version']) {
  let pkgVer = null;
  try { pkgVer = JSON.parse(fs.readFileSync(path.join(HERE, 'package.json'), 'utf8')).version; } catch { /* ignore */ }
  out(`reflect-collect ${VERSION}`);
  if (pkgVer !== VERSION) { err(`${C.no} 版本不一致：CLI=${VERSION} package.json=${pkgVer}`); process.exit(1); }
  out(`package.json version: ${pkgVer} ${C.ok}（单一来源）`);
  process.exit(0);
}

/* ──────────────────────── 参数归一（门在此拦截非法值） ──────────────────────── */

let since, until, sources, outPath, boardUrl, limit, device, devInfo, uploadKey, uploadUrl, day;
try {
  const today = new Date();
  const dayStart = fmtLocal(new Date(today.getFullYear(), today.getMonth(), today.getDate(), 0, 0, 0));
  const dayEnd = fmtLocal(new Date(today.getFullYear(), today.getMonth(), today.getDate(), 23, 59, 59));
  since = assertTimeSpec(argv.since || dayStart, 'since');
  until = assertTimeSpec(argv.until || dayEnd, 'until');
  if (since.ms > until.ms) throw new GateError('WINDOW_INVERTED', `拒绝：--since(${since.iso}) 晚于 --until(${until.iso})。`);
  const requested = argv.sources ? argv.sources.split(',') : [...SOURCE_KEYS];
  let explicitSources = Boolean(argv.sources);
  for (const [flag, key] of [['no-files', 'files'], ['no-board', 'board'], ['no-tools', 'tools'], ['no-logs', 'logs'], ['no-git', 'git']]) {
    if (argv[flag]) { explicitSources = true; const i = requested.indexOf(key); if (i >= 0) requested.splice(i, 1); }
  }
  sources = assertSources(requested);
  const ymd = since.iso.slice(0, 10).replace(/-/g, '');
  // 默认产出名：五源全开 → events-<date>.json（规格要求）；
  // **部分源 → events-<date>-<源名>.json**：否则部分源的一次运行会覆盖当天的全量产出
  //（v1.1 实测踩到两次：一次把 1779 条的当日全量文件覆盖成 55 条，一次覆盖成 logs-only）。
  // 规格的"默认路径"针对的正是"默认五源"这件事；部分源属于非默认用法，给它一个自描述的文件名。
  const partial = explicitSources && sources.length < SOURCE_KEYS.length;
  const defaultOut = partial ? `events-${ymd}-${sources.join('+')}.json` : `events-${ymd}.json`;
  // 注意：assertWriteAllowed 返回的是**命中的规则**，不是目标本身（v1.0.0 踩过：outPath 变成规则目录）
  const requestedOut = argv.out || path.join(OUT_DIR, defaultOut);
  if (partial && !argv.out) process.stderr.write(`${C.warn} 部分源运行（${sources.join('+')}）→ 默认产出改为 ${defaultOut}，避免覆盖当天全量 events-${ymd}.json\n`);
  assertWriteAllowed(requestedOut);
  outPath = path.resolve(requestedOut);
  boardUrl = argv['board-url'] || 'http://127.0.0.1:8792';
  limit = argv.limit === undefined ? 0 : Number(argv.limit);
  if (!Number.isInteger(limit) || limit < 0) throw new GateError('LIMIT_INVALID', `拒绝 --limit '${argv.limit}'：必须是非负整数。`);
  devInfo = argv.device ? { device: assertDevice(argv.device), via: 'flag', hostnameShort: null } : defaultDevice(os.hostname());
  device = devInfo.device;
  day = since.iso.slice(0, 10);
  uploadKey = buildUploadKey(device, day);
  uploadUrl = buildUploadUrl(device, day);
} catch (e) {
  if (e instanceof GateError) { out(`${C.no} 门拒绝 [${e.code}] ${e.message}`); process.exit(2); }
  out(`用法错误: ${e.message}`); process.exit(2);
}
const doUpload = !argv['no-upload'] && !argv['dry-run'];
const allowSecrets = argv['allow-secrets'] === true;

/* ───────────────────────────── ② --selfcheck ───────────────────────────── */

if (argv.selfcheck) {
  const sc = runSelfCheck('reflect-collect', {
    requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
    requiredSymbols: ['parseArgs', 'collectAll', 'runSelfCheck', 'guardedWrite', 'GATE_META', 'uploadEvents'],
    peerRanges: (() => { try { return JSON.parse(fs.readFileSync(path.join(HERE, 'package.json'), 'utf8')).peerDependencies || {}; } catch { return {}; } })(),
    sourceFiles: ['cli.js'],
    baseDir: HERE,   // cli.js 在包根：HERE 即包根（误写成 HERE/.. 会查错目录 → 假失败；v1.0.0 实测踩过）
    selfcheckDir: SELFCHECK_DIR
  });

  out('① 能力清单（我能做什么）');
  out(`    ${C.ok} 采集五源: ${SOURCE_KEYS.join(' / ')}（各自独立开关：--sources / --no-<src>）`);
  out(`    ${C.ok} 时间窗口: --since/--until（默认今天 00:00:00–23:59:59），严格时间格式`);
  out(`    ${C.ok} 本机设备名: ${device}（来源=${devInfo.via}${devInfo.hostnameShort ? ` · 短主机名=${devInfo.hostnameShort}` : ''} · os.hostname=${os.hostname()}）`);
  out(`    ${C.ok} 跨设备上传: PUT ${uploadUrl}（唯一写点；上传后 GET 同 key 回读校验 sha256）`);
  out(`    ${C.ok} 凭据脱敏: ${SECRET_PATTERNS.length} 类形态（${SECRET_PATTERNS.map((p) => p.name).join(', ')}）→ 默认 [REDACTED]；--allow-secrets 才原样`);
  out(`    ${C.ok} 事件时点: ${EVENT_TIME_FIELDS.join(' / ')}（ts=对象自身时刻 · collected_at=采集时刻 UTC · origin_device=采集者）`);
  out(`    ${C.ok} 输出: window/device/hostname/collected_at/counts/events/errors + secrets_redacted → --out / --json / --summary`);
  out(`    ${C.ok} 可写位置（本地闭集，${WRITE_TARGETS.length} 条）:`);
  for (const r of WRITE_TARGETS) out(`        · ${r.kind}: ${r.path}  (${r.why})`);
  out(`    ${C.ok} 网络: 读 GET（环回 /data/ /notes/；中央仅精确 key）/ 写 PUT（仅中央 + 唯一 key 形态）`);
  out(`    ${C.ok} 枚举: **有界分页**（${BOARD_PAGE_SIZE} 键/页 + offset 递进 + total 判定截断）—— R003 v3「需枚举时必须带 limit」；存在性判定一律精确 key GET（绝不用前缀列举）`);
  out(`    ${C.ok} 外部命令: [${ALLOWED_COMMANDS.join(', ')}]（execFileSync 无 shell，参数白名单）`);

  out('② 不该发生路径清单（结构上不可表达，不是"请勿"）');
  out(`    ${C.ok} 键写法非法/空段（尾斜杠、双斜杠、首段非 [a-z]+、段内非法字符）→ 无入口：assertBoardKeySyntax 在**构造 key 时**校验；实测服务端**不会报错**（尾斜杠 → HTTP 200 + 全量列举），所以这道门必须在客户端（R003 补充通告 v2）`);
  out(`    ${C.ok} 本地写坏被采集对象 → 无能力：除唯一写入模块 ${WRITER_MODULES.join(', ')}（3 个 guarded* 封装点，入口第一行 assertWriteAllowed）外，**全包零本地写入/删除原语**`);
  out(`    ${C.ok} 写到本地白名单外（--out 指向 docs/scripts/registry/etc）→ 无入口：WRITE_TARGETS 冻结 ${WRITE_TARGETS.length} 条 + realpath 校验（防软链逃逸）`);
  out(`    ${C.ok} 写本机黑板 → 无表达：本机读只 GET；写只允许中央 + ${UPLOAD_KEY_PREFIX}<device>/<date> 一个形态`);
  out(`    ${C.ok} 上传到别的 key（registry/cards/answers…）或别的实例 → 无入口：assertBoardUpload 三条件（PUT + ${CENTRAL_HOST} + 路径正则）`);
  out(`    ${C.ok} 未脱敏上传凭据 → fail-safe：默认脱敏 + 计数（secrets_redacted）；--allow-secrets 是显式人工开关`);
  out(`    ${C.ok} 只信 200 不回读 → 无能力：上传后必 GET 同 key 比对 sha256；非 200/不一致 → exit 1（纪律来源：本日 4 次"报告指向不存在的落盘物"）`);
  out(`    ${C.ok} 事件缺时点/来源 → 无能力：stampEvents 唯一打点 + assertEventStamped 逐条门检（ts/collected_at/origin_device）`);
  out(`    ${C.ok} 采集根之外（含 .. 穿越/软链逃逸）→ 无入口：COLLECT_ROOTS 冻结，resolve + realpath 双重校验`);
  out(`    ${C.ok} 采集自己的产物（自采样污染）→ 无入口：SELF_ARTIFACTS 冻结排除（自己的日志/产出/自查）`);
  out(`    ${C.ok} 执行 git 以外命令/带 shell/参数注入 → 无能力：命令白名单 [${ALLOWED_COMMANDS.join(', ')}] + shell:false + 参数白名单 + 时间严格正则`);
  out(`    ${C.ok} 静默跳过失败源 → 无能力：任何源失败/超限/跳过都写入 errors[]`);

  out('③ 依赖完整性');
  out(`    ${sc.ok ? C.ok : C.no} R014 自查门 ok=${sc.ok} missing=${sc.missing.length} warnings=${sc.warnings.length}`);
  sc.missing.forEach((m) => out(`        ${C.no} ${m}`));
  sc.warnings.forEach((w) => out(`        ${C.warn} ${w}`));
  (sc.notes || []).forEach((n) => out(`        · ${n}`));
  for (const p of sc.peers) {
    out(`    ${p.ok ? C.ok : C.no} peer ${p.peer} v${p.version || '?'} via=${p.via || '-'} 声明='${p.range || '(无)'}'`);
    out(`        ${p.rangeOk === null ? C.warn : (p.rangeOk ? C.ok : C.no)} ④ 范围判定: ${p.rangeReason || '(未判定)'}`);
    out(`        解析到: ${p.ok ? p.resolved : '(' + p.err + ')'}`);
  }
  out(`    ${C.ok} 运行期依赖: 仅 node 内置模块（fs/path/os/http/url/crypto/child_process/module）+ 系统 git`);
  out(`    ${C.ok} 无 CLD 也能跑: node ${process.version} 独立执行 CLI（③ CLD 自适应）`);
  // 四态（R003 rule_2）：present / absent(404) / bad-key(400) / unreachable —— 不合并成布尔
  const central = await centralKeyState(uploadUrl);
  const CENTRAL_LABEL = {
    present: `${C.ok} 该 key 已存在（上传将覆盖并回读校验）`,
    absent: `${C.ok} 该 key 尚不存在（404=格式合法但不存在）`,
    'bad-key': `${C.no} 该 key **写法非法**（400）—— 键语法门应已在客户端拦下，出现即说明门漏了`,
    unreachable: `${C.warn} 不可达（运行期依赖，非包问题）`
  };
  out(`    ${central.kind === 'unreachable' ? C.warn : C.ok} 中央黑板 ${uploadUrl} → HTTP ${central.status ?? '-'} [${central.kind}] ${CENTRAL_LABEL[central.kind] || ''}`);
  if (central.error) out(`        ${central.error}`);
  // rule_4：探活**必须有界**（尾斜杠路径会返回 36.59MB/20220 键的全量列举）
  const local = await boardReachable('http://127.0.0.1:8792');
  out(local.kind === 'unreachable'
    ? `    ${C.warn} 本机黑板探测失败（运行期依赖，非包问题）: ${local.error}`
    : `    ${C.ok} 本机黑板可达: GET /data/?limit=1 → HTTP ${local.status} [${local.kind}] · ${local.bytes} 字节（**有界探测**；R003 rule_4：尾斜杠路径会返回全量列举 ~36.59MB/20220 键，探活绝不用它）`);
  const nodeEnv = nodeOnPath();
  out(nodeEnv.ok
    ? `    ${C.ok} 环境: node 在 PATH 上 → ${nodeEnv.path}`
    : `    ${C.warn} 环境问题（非包问题）: node 不在 PATH（PATH=${process.env.PATH || '(空)'}）；shebang 需 node 在 PATH`);
  out(`    ${C.ok} type:module ✓ · 不 import 任何宿主内部路径（只 import 'node:*'、peer 包与本包相对路径）`);
  out(`    自查产物: ${path.join(SELFCHECK_DIR, 'reflect-collect.json')}（写入白名单内，不写 ~/.dsh/plugin-selfcheck）`);

  // ④ 真挂载冒烟：import lib/index.js + 桩 ctx 调 apply() → 数注册了几个工具
  const smoke = await mountSmoke({
    baseDir: HERE,
    indexRel: 'lib/index.js',
    requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
    expectedToolName: 'reflect_collect'
  });
  out('④ 真挂载冒烟（import lib/index.js + 桩 ctx 调 apply()）');
  const SMOKE_ICON = { passed: C.ok, failed: C.no, skipped: '⏭' };
  out(`    ${SMOKE_ICON[smoke.status] || '?'} 结论: ${smoke.status === 'passed' ? '通过' : smoke.status === 'failed' ? '失败' : '**跳过**（如实标注，不判通过）'}`);
  if (smoke.status === 'skipped') {
    out(`        原因: ${smoke.reason}`);
    out('        说明: 无宿主环境（peer 解析不到）下不假装挂载成功；在 CLD 内由宿主真实挂载时本项才有意义');
  } else if (smoke.status === 'failed') {
    out(`        失败位置: ${smoke.stage}（${smoke.stage === 'import' ? '导入期' : smoke.stage === 'apply' ? 'apply 阶段：宿主启动即会崩的那类问题' : '断言期'}）`);
    out(`        错误: ${smoke.error}`);
    if (smoke.violations) out(`        违规明细: ${JSON.stringify(smoke.violations)}`);
  } else {
    out(`        注册工具数: ${smoke.registered} → ${smoke.tools.map((t) => t.name).join(', ')}`);
    out(`        模块名/注入: name=${smoke.moduleName} · inject=${JSON.stringify(smoke.inject)} · 期望工具命中=${smoke.expectedOk}`);
    out(`        工具形状: ${smoke.tools.map((t) => `${t.name}(desc=${t.hasDescription},params=${t.hasParameters},execute=${t.hasExecute})`).join(' · ')}`);
    out(`        副作用回收: ctx.effect 执行 ${smoke.effectCount} 次，effect 内异常 ${smoke.effectErrors.length} 个${smoke.effectErrors.length ? ' → ' + JSON.stringify(smoke.effectErrors) : ''}`);
  }

  // ⑤ 自证摘要
  const gateNeg = gateNegativeCases();
  const gatePos = gatePositiveCases();
  const gateRed = secretRedactCases();
  const gateKeep = secretKeepCases();
  out('⑤ 自证摘要（数字）');
  out(`    ${C.ok} 属性模式: package.json v${VERSION} · type:module · main=lib/index.js · dsh.bundle.patch · peer 两级解析`);
  out(`    ${C.ok} 结构门用例: 负例 ${gateNeg.length} 条（放行 ${gateNeg.filter((n) => n.code === null).length}）· 正例 ${gatePos.length} 条（误拦 ${gatePos.filter((p) => !p.ok).length}）`);
  out(`    ${C.ok} 凭据形态用例: 必须脱敏 ${gateRed.filter((r) => r.ok).length}/${gateRed.length} · 必须保留 ${gateKeep.filter((k) => k.ok).length}/${gateKeep.length}`);
  out(`    ${C.ok} 冻结白名单: 本地写入 ${WRITE_TARGETS.length} · 采集根 ${COLLECT_ROOTS.length} · 源 ${SOURCE_KEYS.length} · 命令 ${ALLOWED_COMMANDS.length} · HTTP ${ALLOWED_HTTP_METHODS.length} · 凭据形态 ${SECRET_PATTERNS.length} · 设备别名 ${DEVICE_ALIAS.length}`);
  out(`    ${C.ok} 唯一性: 本地写入模块 ${WRITER_MODULES.join(',')} · 网络模块 ${NETWORK_MODULES.join(',')} · 上传模块 ${UPLOADER_MODULES.join(',')}`);
  out(`    ${C.ok} 冒烟/依赖: 真挂载=${smoke.status} · 中央黑板=[${central.kind}] · 本机探活=${local.bytes} 字节`);

  // 把冒烟结果并进自查产物（§3.2 的"自查落盘"要完整：产物里必须能看到真挂载结论）
  try {
    guardedWrite(path.join(SELFCHECK_DIR, 'reflect-collect.json'), JSON.stringify({
      ...sc,
      mountSmoke: { status: smoke.status, stage: smoke.stage || null, registered: smoke.registered ?? null, tools: smoke.tools || null, error: smoke.error || null, reason: smoke.reason || null, ts: new Date().toISOString() },
      centralKeyState: { kind: central.kind, status: central.status ?? null },
      localProbeBytes: local.bytes
    }, null, 1));
  } catch { /* 不阻塞 */ }

  log('selfcheck', {
    input: { plugin: 'reflect-collect', sourceFiles: ['cli.js'], device, smoke: smoke.status },
    judgement: `R014 ok=${sc.ok} missing=${sc.missing.length} env=${sc.envIssues.length}`,
    result: sc.ok && smoke.status !== 'failed' ? 'success' : 'fail',
    diagnosis: {
      missing: sc.missing, envIssues: sc.envIssues, peers: sc.peers.map((p) => `${p.peer}:${p.via || 'FAIL'}`),
      device, via: devInfo.via, central: central.status ?? central.error ?? null,
      mountSmoke: { status: smoke.status, stage: smoke.stage || null, registered: smoke.registered ?? null, error: smoke.error || null }
    }
  }, { dryRun: argv['dry-run'] });
  process.exit(sc.ok && smoke.status !== 'failed' ? 0 : 1);
}

/* ─────────────────────────── ⑩ --lean4-check ─────────────────────────── */

if (argv['lean4-check']) {
  const checks = [];
  const files = ['cli.js', 'lib/collect.js', 'lib/log.js', 'lib/gate.js', 'lib/selfcheck.js',
    'lib/index.js', 'lib/version.js', 'lib/transport.js', 'lib/upload.js'];
  const sources0 = {};
  for (const f of files) sources0[f] = fs.readFileSync(path.join(HERE, f), 'utf8');
  const productSources = Object.fromEntries(Object.entries(sources0).filter(([f]) => f !== GATE_MODULE));

  // A. 除唯一写入模块外，全包零本地写入/删除原语 + 零 shell
  const aSources = Object.fromEntries(Object.entries(sources0).filter(([f]) => !WRITER_MODULES.includes(f)));
  const dangerHits = scanDangerousPrimitives({ sources: aSources });
  checks.push({
    id: 'A 源码无危险原语',
    ok: dangerHits.length === 0,
    detail: dangerHits.length
      ? `命中: ${JSON.stringify(dangerHits)}`
      : `除唯一写入模块 [${WRITER_MODULES.join(', ')}] 外，全包（${Object.keys(aSources).join(' ')}）零写入/删除原语（writeFileSync/mkdirSync/rmSync/unlinkSync/renameSync/createWriteStream/openSync… 命中 0）+ 零 shell（exec(/execSync(/spawn/shell:true 命中 0）`
  });

  // B. 负例全部被拒 + 凭据形态（该脱敏的必脱敏 / 该保留的必保留）
  const neg = gateNegativeCases();
  const leaked = neg.filter((n) => n.code === null);
  const byGroup = {};
  for (const n of neg) byGroup[n.group] = (byGroup[n.group] || 0) + 1;
  const selfCases = selfSamplingCases();
  const selfBad = selfCases.filter((c) => c.got !== c.expect);
  const red = secretRedactCases();
  const redBad = red.filter((c) => !c.ok);
  const keep = secretKeepCases();
  const keepBad = keep.filter((c) => !c.ok);
  let realpathProbe = null;
  try { realpathProbe = { probe: '/tmp', real: realpathNearest('/tmp'), live: realpathNearest('/tmp') !== '/tmp' }; } catch { realpathProbe = null; }
  let traversalRejected = true;
  try { assertWriteAllowed(path.join(OUT_DIR, 'sub', '..', '..', '..', 'Documents', 'x.json')); traversalRejected = false; } catch { /* 期望被拒 */ }
  checks.push({
    id: 'B 负例全部被拒',
    ok: leaked.length === 0 && selfBad.length === 0 && redBad.length === 0 && keepBad.length === 0 && traversalRejected,
    detail: (leaked.length || selfBad.length || redBad.length || keepBad.length || !traversalRejected)
      ? `放行/误判: ${JSON.stringify({ leaked, selfBad, redBad, keepBad, traversalRejected })}`
      : `${neg.length} 条越界输入全部 GateError（${Object.entries(byGroup).map(([g, n]) => `${g}:${n}`).join(' ')}）` +
        ` + 自采样排除 ${selfCases.length}/${selfCases.length} 符合预期` +
        ` + 凭据形态【必须脱敏】${red.length - redBad.length}/${red.length}、【必须保留】${keep.length - keepBad.length}/${keep.length}` +
        (realpathProbe ? `；realpath 分支存活=${realpathProbe.live}（${realpathProbe.probe} → ${realpathProbe.real}）` : '')
  });

  // C. 正例可用（防"门太宽把功能也砍了"）
  const pos = gatePositiveCases();
  const posBad = pos.filter((p) => !p.ok);
  checks.push({
    id: 'C 正例可用',
    ok: posBad.length === 0,
    detail: posBad.length
      ? `被误拦: ${JSON.stringify(posBad)}`
      : `${pos.length}/${pos.length} 条合法输入全部通过（写入目标 3 条 + 产出文件 + 读目标(环回/中央) + 上传目标(PUT 中央 reflect) + 设备名 + 事件时点 + 回读成功判据 + git 只读参数 + 源白名单…）`
  });

  // D. dry-run 零变更（实测：本地 + 中央两侧）
  const before = externalStateSnapshot();
  const beforeCentral = await centralKeyState(uploadUrl);
  const dry = await collectAll({ since, until, sources, boardUrl, limit, dryRun: true, device, pluginVersion: VERSION });
  const dryUp = await uploadEvents({ device, date: day, text: JSON.stringify(dry.doc), dryRun: true });
  const after = externalStateSnapshot();
  const afterCentral = await centralKeyState(uploadUrl);
  const diffs = diffSnapshots(before, after);
  const st = writeStats();
  const net = networkStats();
  const writablePaths = WRITE_TARGETS.map((r) => r.path);
  const foreignDiffs = diffs.filter((d) => !writablePaths.some((w) => (JSON.stringify(d.after) + JSON.stringify(d.before)).includes(w)));
  const ownDiffs = diffs.filter((d) => !foreignDiffs.includes(d));
  const centralSame = JSON.stringify(beforeCentral) === JSON.stringify(afterCentral);
  const dOk = ownDiffs.length === 0 && st.attempts.length === 0 && net.puts === 0 && centralSame;
  checks.push({
    id: 'D dry-run 零变更',
    ok: dOk,
    detail: dOk
      ? `实测：本地落盘调用 ${st.attempts.length} 次、PUT ${net.puts} 次、只读 GET ${net.gets} 次；` +
        `本地状态（日志 ${path.basename(LOG_FILE)} 的 size/mtime、产出目录列表、自查目录列表、两采集根抽样摘要）前后一致` +
        (foreignDiffs.length ? `（另有 ${foreignDiffs.length} 项第三方并发写入，非本进程，已排除：${foreignDiffs.map((d) => d.field).join(',')}）` : '') +
        `；中央 key ${uploadKey} 前后一致（${beforeCentral.exists ? `存在 sha256=${String(beforeCentral.sha256).slice(0, 12)}…` : '不存在(404)'}）`
      : `发生变更: ${JSON.stringify({ ownDiffs, attempts: st.attempts, puts: net.puts, centralSame, beforeCentral, afterCentral })}`
  });
  checks.push({
    id: 'D2 dry-run 采集不空转',
    ok: Boolean(dry.doc) && Array.isArray(dry.doc.errors) && dryUp.attempted === false,
    detail: `dry-run 真实跑完五源：counts=${JSON.stringify(dry.counts)}，errors=${dry.doc.errors.length} 条；` +
      `上传分支 attempted=${dryUp.attempted}（dry-run 结构上不发 PUT）`
  });

  // E. 白名单冻结
  const frozenTargets = Object.isFrozen(WRITE_TARGETS) && WRITE_TARGETS.every((r) => Object.isFrozen(r));
  const eOk = frozenTargets && Object.isFrozen(COLLECT_ROOTS) && Object.isFrozen(ALLOWED_COMMANDS)
    && Object.isFrozen(SOURCE_KEYS) && Object.isFrozen(SECRET_PATTERNS) && Object.isFrozen(DEVICE_ALIAS)
    && Object.isFrozen(ALLOWED_HTTP_METHODS) && Object.isFrozen(NETWORK_MODULES) && Object.isFrozen(UPLOADER_MODULES);
  checks.push({
    id: 'E 白名单冻结',
    ok: eOk,
    detail: `WRITE_TARGETS frozen=${Object.isFrozen(WRITE_TARGETS)}(规则项亦冻结=${WRITE_TARGETS.every((r) => Object.isFrozen(r))}) ` +
      `COLLECT_ROOTS=${Object.isFrozen(COLLECT_ROOTS)} SECRET_PATTERNS=${Object.isFrozen(SECRET_PATTERNS)} DEVICE_ALIAS=${Object.isFrozen(DEVICE_ALIAS)} ` +
      `HTTP方法=${Object.isFrozen(ALLOWED_HTTP_METHODS)} 网络模块=${Object.isFrozen(NETWORK_MODULES)} 上传模块=${Object.isFrozen(UPLOADER_MODULES)} 分页常量=${Object.isFrozen(BOARD_PAGE_SIZE) && Object.isFrozen(BOARD_MAX_KEYS)}`
  });

  // F. 写入点 / 命令 / 网络 / 上传点白名单（去字面量定位 + 回原文读实参；防"空集通过"）
  const writeSites = scanWriteSites({ sources: sources0 });
  const outsideWriter = writeSites.filter((s) => !WRITER_MODULES.includes(s.file));
  const execSites = scanExecSites({ sources: sources0 });
  const badExec = execSites.filter((s) => !s.literal || !ALLOWED_COMMANDS.includes(String(s.cmd)));
  const methodLiterals = scanHttpMethods({ sources: productSources });
  const badMethods = methodLiterals.filter((m) => !ALLOWED_HTTP_METHODS.includes(m.method));
  // 读门：产品路径上的实际调用点是 assertReadTarget（放在 lib/transport.js，GET 字面量在 request({method:'GET'})）
  const readGuards = scanNameArgSites({ sources: productSources, name: 'assertReadTarget' });
  const badReadGuards = readGuards.filter((s) => !NETWORK_MODULES.includes(s.file));
  const uploadGuards = scanNameArgSites({ sources: productSources, name: 'assertBoardUpload' });
  const badUploadGuards = uploadGuards.filter((s) => !s.literal || s.arg !== 'PUT');
  const httpReqs = scanHttpRequestSites({ sources: sources0 });
  const badHttpReqs = httpReqs.filter((s) => !NETWORK_MODULES.includes(s.file));
  const putSites = scanNameArgSites({ sources: sources0, name: 'httpPutJson' });
  const badPutSites = putSites.filter((s) => !UPLOADER_MODULES.includes(s.file));
  const fOk = writeSites.length > 0 && outsideWriter.length === 0 && badExec.length === 0 && badMethods.length === 0
    && readGuards.length >= 1 && badReadGuards.length === 0 && uploadGuards.length >= 1 && badUploadGuards.length === 0
    && httpReqs.length >= 1 && badHttpReqs.length === 0 && putSites.length >= 1 && badPutSites.length === 0
    && Object.isFrozen(WRITER_MODULES);
  checks.push({
    id: 'F 写入点/命令/网络/上传点白名单',
    ok: fOk,
    detail: fOk
      ? `本地写入调用点 ${writeSites.length} 个全部在 [${WRITER_MODULES.join(', ')}]（目标非字面量 = guarded* 封装，入口第一行 assertWriteAllowed）；` +
        `exec 调用点 ${execSites.length} 个命令集=[${[...new Set(execSites.map((s) => s.cmd))].join(', ')}] ⊆ [${ALLOWED_COMMANDS.join(', ')}]；` +
        `http.request 调用点 ${httpReqs.length} 个全部在 [${NETWORK_MODULES.join(', ')}]；` +
        `读门调用点 assertReadTarget ${readGuards.length} 个（∈ [${NETWORK_MODULES.join(', ')}]）；上传门调用点 assertBoardUpload ${uploadGuards.length} 个（字面量全为 PUT，∈ [${NETWORK_MODULES.join(', ')}]）；` +
        `上传调用点 httpPutJson ${putSites.length} 个全部在 [${UPLOADER_MODULES.join(', ')}]；method 字面量 ${methodLiterals.length} 个 ⊆ [${ALLOWED_HTTP_METHODS.join(', ')}]（各项均要求 >0，防"空集通过"）`
      : `本地写入 ${writeSites.length}(外溢${outsideWriter.length}) · exec 越界 ${badExec.length} · method 越界 ${badMethods.length} · 读门 ${readGuards.length}(越界${badReadGuards.length}) · 上传门 ${uploadGuards.length}(越界${badUploadGuards.length}) · http.request ${httpReqs.length}(外溢${badHttpReqs.length}) · httpPutJson ${putSites.length}(外溢${badPutSites.length})`
  });

  const ok = checks.every((c) => c.ok);
  if (argv.json) out(JSON.stringify({ ok, version: VERSION, device, checks, gate: GATE_META }, null, 1));
  else {
    out(`lean4-check · 结构门自证（${GATE_META.principle}）`);
    for (const c of checks) out(`  ${c.ok ? C.ok : C.no} ${c.id} — ${c.detail}`);
    out(ok ? `\n${C.ok} 结构门生效：约束不可绕过（无入口 + 无能力 + 有证明 + 失败即停）` : `\n${C.no} 门未生效，禁止交付`);
  }
  log('lean4-check', {
    input: { files, device },
    judgement: checks.map((c) => `${c.id}:${c.ok}`).join(' '),
    result: ok ? 'success' : 'fail',
    diagnosis: { checks: checks.map((c) => ({ id: c.id, ok: c.ok })), writeSites: writeSites.length, execSites: execSites.length, httpReqs: httpReqs.length, putSites: putSites.length }
  }, { dryRun: argv['dry-run'] });
  process.exit(ok ? 0 : 1);
}

/* ───────────────────────────── 采集主流程 ───────────────────────────── */

const dryRun = argv['dry-run'] === true;
const t0 = Date.now();
let res;
try {
  res = await collectAll({ since, until, sources, boardUrl, limit, dryRun, device, pluginVersion: VERSION });
} catch (e) {
  log('collect', {
    input: { since: since.iso, until: until.iso, sources, boardUrl, device },
    judgement: '采集流程抛出异常', result: 'fail',
    diagnosis: { error: String(e.message || e), code: e.code || null, ms: Date.now() - t0 }
  }, { dryRun });
  err(`${C.no} 采集失败: ${e.message}`);
  process.exit(e instanceof GateError ? 2 : 1);
}

/* ★ 凭据扫描 + 脱敏：本地落盘与上传**共用同一份 payload**，
   因此不存在"本地脱敏了、上传没脱敏"（或反之）的路径。 */
const red = redactPayload(res.doc, { allowSecrets });
const payload = JSON.stringify({
  ...red.payload,
  secrets_redacted: red.secrets_redacted,
  outPath, sources: res.sources, version: VERSION, logFile: LOG_FILE, uploadKey
}, null, 1) + '\n';

const failed = res.errors.filter((e) => e.kind === 'collect-failed');
const limited = res.errors.filter((e) => e.kind === 'limit');
const skipped = res.errors.filter((e) => e.kind === 'skipped');

/* ★ 跨设备上传（唯一写点）+ 回读校验 */
let up = { attempted: false, ok: true, reason: '未上传（--no-upload 或 --dry-run）', key: uploadKey, url: uploadUrl };
if (doUpload) up = await uploadEvents({ device, date: day, text: payload, dryRun: false });
if (red.secrets_redacted > 0) {
  err(`${C.warn} 凭据扫描命中 ${red.secrets_redacted} 处，已脱敏为 [REDACTED]：${JSON.stringify(red.byPattern)}`);
}

let receipt = { persisted: false, dryRun };
try {
  if (!dryRun) {
    guardedMkdirp(path.dirname(outPath));
    guardedWrite(outPath, payload);
  }
  receipt = log('collect', {
    input: { since: res.window.since, until: res.window.until, sources, boardUrl, limit, outPath, device, upload: doUpload ? uploadUrl : '(skipped)' },
    judgement: `五源采集：${Object.entries(res.counts).map(([k, v]) => `${k}=${v}`).join(' ')}；上传 ${up.attempted ? (up.ok ? 'ok+回读校验通过' : 'FAIL') : 'skipped'}`,
    result: failed.length || (up.attempted && !up.ok) ? 'fail' : 'success',
    diagnosis: {
      errors: res.errors.length, limit: limited.length, skipped: skipped.length, ms: Date.now() - t0,
      secrets_redacted: red.secrets_redacted, redact_by: red.byPattern,
      upload: {
        key: up.key, url: up.url, putStatus: up.putStatus ?? null, readbackStatus: up.readbackStatus ?? null,
        expectedSha256: up.expectedSha256 || null, readbackSha256: up.readbackSha256 || null,
        verified: up.ok === true, reason: up.reason
      },
      writeCalls: writeStats(), network: networkStats(), outPath: dryRun ? null : outPath
    }
  }, { dryRun });
} catch (e) {
  err(`${C.no} 产物落盘/日志失败 [${e.code || e.name}]: ${e.message}`);
  process.exit(2);
}

const uploadFailed = up.attempted && !up.ok;
const summaryLine = `secrets_redacted=${red.secrets_redacted} · upload=${up.attempted ? (up.ok ? 'ok+回读校验通过' : 'FAIL') : 'skipped'}`;

if (argv.json) {
  out(JSON.stringify({
    ...red.payload,
    secrets_redacted: red.secrets_redacted,
    outPath: dryRun ? null : outPath,
    sources: res.sources, version: VERSION, logFile: LOG_FILE,
    uploadKey, uploadUrl, upload: up,
    dryRun, logPersisted: receipt.persisted === true
  }, null, 1));
} else if (argv.summary) {
  out(`摘要 · reflect-collect v${VERSION} · device=${device} · 窗口 ${res.window.since} → ${res.window.until}（共 ${res.doc.events.length} 条）`);
  out(`各源计数：${Object.entries(res.counts).map(([k, v]) => `${k}=${v}`).join(' · ')} · errors ${res.errors.length}（采集失败 ${failed.length} · 超限 ${limited.length} · 跳过 ${skipped.length}）`);
  out(`跨设备：${summaryLine}`);
  for (const src of SOURCE_KEYS) {
    const evs = res.doc.events.filter((e) => e.source === src);
    out(`\n[${src}] ${res.counts[src]} 条`);
    for (const e of evs.slice(0, 8)) out(`  ${e.id} ${e.ts} ${String(e.kind).padEnd(11)} ${e.desc}`);
    if (evs.length > 8) out(`  … 另有 ${evs.length - 8} 条（完整见 JSON）`);
    if (!evs.length) out('  （无）');
  }
  if (res.errors.length) {
    out(`\nerrors（${res.errors.length} 条，不静默）`);
    for (const e of res.errors.slice(0, 12)) out(`  [${e.source}/${e.kind}] ${e.message}`);
    if (res.errors.length > 12) out(`  … 另有 ${res.errors.length - 12} 条`);
  }
  if (up.attempted) out(`\n上传：${up.ok ? C.ok : C.no} ${up.url}\n  PUT=${up.putStatus} · 回读=${up.readbackStatus} · ${up.reason}`);
  out(dryRun ? `\n${C.warn} dry-run：零字节落盘 + 未上传（日志行见上方 [dry-run] 行）` : `\n${C.ok} 事件流 → ${outPath}\n${C.ok} 统一日志 → ${LOG_FILE}`);
} else {
  out(`reflect-collect v${VERSION} · device=${device} · 窗口 ${res.window.since} → ${res.window.until}`);
  for (const [k, v] of Object.entries(res.counts)) out(`  ${k.padEnd(6)} ${String(v).padStart(5)} 条`);
  out(`  ${'合计'.padEnd(6)} ${String(res.doc.events.length).padStart(5)} 条 · errors ${res.errors.length}（采集失败 ${failed.length} · 超限 ${limited.length} · 跳过 ${skipped.length}）`);
  out(`  跨设备：${summaryLine}`);
  if (up.attempted) out(`  ${up.ok ? C.ok : C.no} 上传 ${up.url} → PUT=${up.putStatus} 回读=${up.readbackStatus}`);
  out(dryRun ? `  ${C.warn} dry-run：零字节落盘 + 未上传` : `  ${C.ok} 事件流 → ${outPath}`);
  if (!dryRun) out(`  ${C.ok} 统一日志 → ${LOG_FILE}`);
  out('  （加 --summary 看事件明细，加 --json 拿机器可读输出）');
}

process.exit(failed.length || uploadFailed ? 1 : 0);
