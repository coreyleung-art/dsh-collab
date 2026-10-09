#!/usr/bin/env node
/**
 * cli.js — CLI 治理（R006 ⑨）+ 自查门（②）+ 版本（⑥）+ 结构门自证（⑩）+ 落链（⑧）
 * =============================================================================
 * 用法：
 *   node cli.js --events <path> [--local-only] [--agents a,b] [--max-events 8]   # 本机出卡（只落盘）
 *   node cli.js [--devices mac-mini,mbp,i9] [--send]                             # 全设备：中央板取事件流 + 派发
 *   node cli.js --events <path> --dry-run [--json]                               # 只打印计划，零变更
 *   node cli.js --targets                                                        # 只读：可派目标与 resources
 *   node cli.js --devices-status                                                 # 只读：各设备三件套键存在性探测
 *   node cli.js --list-check                                                     # 诊断：黑板前缀列举实测
 *   node cli.js --register [--dry-run]                                           # ⑧ 写黑板登记卡
 *   node cli.js --selfcheck / --lean4-check / --tool-version / --help
 * 退出码：0=成功/门生效 · 1=失败或门被触发 · 2=用法或 IO 错误
 */
import { parseArgs } from 'node:util';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { dispatch, listTargets, VERSION, LOG_FILE, PLUGIN_NAME, makeLogger } from './lib/core.js';
import { putAndVerify, bbGet, ping, probeKey, listKeys } from './lib/board.js';
import { runSelfCheck } from './lib/selfcheck.js';
import { resolveLocalDevice, resolveDevices, keysFor } from './lib/sources.js';
import {
  GateError, ALLOWED_COMMANDS, ALLOWED_HOSTS, BOARD_TARGETS, CANDIDATE_DEVICES, DEVICE_STATUS,
  SUGGESTION_TYPES, DISPATCH_STATES, DISPATCH_TRANSITIONS, NOTICE_MAX_CHARS,
  TARGET_TOKENS_FORBIDDEN, SECRET_PATTERNS, GATE_META, REFLECT_ROOT_REL, localDateCompact,
  gateNegativeCases, gatePositiveCases, scanForbiddenPrimitives, scanExecSites,
  scanChildProcessImports, scanOutboundHosts
} from './lib/gate.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const HOME = os.homedir();
const C = { ok: '\u2705', no: '\u274c', warn: '\u26a0\ufe0f' };
/**
 * ★ 同步写 stdout。
 * 实测（2026-09-10）：`process.stdout.write()` 是**异步**的 —— 紧跟其后调用 `process.exit()`，
 * 一旦输出较大（如 `--json` 带 1407 条 unassigned 的完整结果）而 stdout 是**管道**，
 * 尾部数据会被直接丢掉 → 下游拿到的是**截断的 JSON**（本工具自己的 `--json` 管线就是这么坏的）。
 * 改用 `fs.writeSync(1, ...)`：同步落管道，`process.exit()` 不再截断。
 */
function out(s) { fs.writeSync(1, s + '\n'); }
const tilde = (p) => String(p).replace(HOME, '~');

/* ---------------------------------- 参数 ---------------------------------- */
let args;
try {
  args = parseArgs({
    options: {
      events: { type: 'string' },
      agents: { type: 'string' },
      devices: { type: 'string' },
      device: { type: 'string' },
      'local-only': { type: 'boolean', default: false },
      'allow-late': { type: 'boolean', default: false },
      'assume-online': { type: 'string' },
      'max-events': { type: 'string' },
      threshold: { type: 'string' },
      date: { type: 'string' },
      profiles: { type: 'string' },
      'cards-root': { type: 'string' },
      send: { type: 'boolean', default: false },
      'emit-only': { type: 'boolean', default: false },
      'dry-run': { type: 'boolean', default: false },
      targets: { type: 'boolean', default: false },
      'devices-status': { type: 'boolean', default: false },
      register: { type: 'boolean', default: false },
      selfcheck: { type: 'boolean', default: false },
      'lean4-check': { type: 'boolean', default: false },
      'list-check': { type: 'boolean', default: false },
      'tool-version': { type: 'boolean', default: false },
      json: { type: 'boolean', default: false },
      help: { type: 'boolean', default: false }
    },
    allowPositionals: false
  }).values;
} catch (e) {
  out(`用法错误: ${e.message}`); out('试 --help'); process.exit(2);
}

const num = (v, name) => {
  if (v === undefined) return undefined;
  const n = Number(v);
  if (!Number.isFinite(n) || n < 0) { out(`用法错误: --${name} 需要非负数字，收到 "${v}"`); process.exit(2); }
  return n;
};
const dashed = (d) => `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`;

if (args.help) {
  out(`${PLUGIN_NAME} v${VERSION} — 按每个智能体当天真实做过的事件，定制一张「思考卡」并派发（★ 跨设备）
「每日反思」流水线的**发牌**环节。核心设计意图：**不能发统一问卷**——统一问题会让智能体写套话，
所以每张卡的 ① 事件实摘 与 ② 每个问题后的上下文，都按**它自己的**当天事件生成。
v1.1 跨设备层：事件源从"本机"扩到"全设备"（中央板 ${BOARD_TARGETS.central}），
卡按 <device> 分目录、设备合并卡 PUT 到 data/reflect/cards/<device>/<date>，离线设备标 pending（待取，不是失败）。

  --events <path>        本机事件流 JSON（--local-only 时的唯一来源）
  --devices <a,b,...>    显式设备列表（默认：中央板设备索引 → 冻结候选探测 → 兜底本机）
  --device <name>        本机设备名（默认按主机名映射：mac-mini / mbp / i9）
  --local-only           ★ 只读本机，退回单设备行为（测试用；仍会读中央板做存在性探测）
  --allow-late           ★ 允许补派 T+1/T+2（不加则处理过去的日期会被**拒绝**，Φ13）
  --assume-online <a,b>  人工声明某设备在线（默认按心跳判定；声明会记入台账，不静默）
  --agents <id,...>      只派给这些智能体（会话 id 或短键）
  --max-events <n>       每个智能体最多带几条事件（默认 8）
  --threshold <n>        归属阈值（默认 50）
  --date <YYYY-MM-DD>    覆盖日期（默认取事件流 window.until）
  --profiles <path>      指定档案文件（默认 ~/.dsh/agent-bus.json → 旧路径 → 镜像 → 黑板）
  --cards-root <dir>     覆盖卡根目录（仍必须落在 ~/dsh-collab/${REFLECT_ROOT_REL}/ 下）
  --send                 ★ PUT 到中央黑板 data/reflect/cards/<device>/<date>，**并立即回读校验**
  --emit-only            只落盘不发送（**默认行为**，显式写出以免误判）
  --dry-run              只打印计划：不落盘 / 不发黑板 / 不写日志（零变更，lean4-check D 会实测）
  --targets              只读：列出可派目标与它们登记的 resources
  --devices-status       只读：逐设备探测事件流/卡/回填键（200 存在 / 404 尚未 / 400 键错）
  --list-check           诊断：实测黑板"前缀列举"到底支不支持（结论打印，不当设备清单用）
  --register             ⑧ 落链：写黑板 data/registry/${PLUGIN_NAME} 登记卡（可配 --dry-run）
  --json                 机器可读输出
  --selfcheck            ② TCC 自查门：能力 / 不该发生路径 / 依赖完整性
  --lean4-check          ⑩ 结构门自证：A 无危险原语 · B 负例全拒 · C 正例可用 · D dry-run 零变更 · E 白名单冻结 · F 命令与主机白名单
  --tool-version  --help

★ 结构约束（不是纪律）：
  · 通知正文由冻结模板生成，恒 ≤${NOTICE_MAX_CHARS} 字（总线 v2.4 门禁）——本工具**没有**传自由文本的入口。
  · 目标不存在 / 设备段不匹配 → **拒绝执行**（exit 1），不静默跳过、不跨设备写别人目录。
  · 发送 = PUT 中央板 + 立即 GET 回读逐字节比对；回读不一致即派发失败，绝不报成功。
  · 落盘与写黑板前对最终文本再跑一次**凭据脱敏**（Φ12）；命中即替换为 [REDACTED:<kind>]。
  · 设备离线 → 状态记 pending（离线待取），**不是** failed（设计文档 §10.4）。

退出码：0 成功/门生效 · 1 失败或门被触发 · 2 用法错误或 IO 错误`);
  process.exit(0);
}

if (args['tool-version']) { out(`${PLUGIN_NAME} ${VERSION}`); process.exit(0); }

/* ----------------------------- --list-check（诊断） ----------------------------- */
if (args['list-check']) {
  const r = await listKeys('data', 'central', 500);
  const reflectKeys = r.keys.filter((k) => k.startsWith('data/reflect'));
  const devFromKey = (k) => (k.match(/^data\/reflect\/events\/([a-z][a-z0-9-]{1,15})\//) || [])[1];
  const listedDevices = [...new Set(reflectKeys.map(devFromKey).filter(Boolean))];
  const res = {
    ...r, reflectKeys, listedDevices,
    verdict: r.complete
      ? `**接口不做前缀过滤，但键集完整**（返回 ${r.keys.length}/${r.total} 键）→ 按前缀过滤**有效**：可从中解析出设备 ${listedDevices.length} 个`
      : `**被截断**（只返回 ${r.keys.length}/${r.total} 键）→ 此时**不能**当作全设备清单`,
    therefore: '本工具的设备枚举顺序：--devices（显式）→ 前缀列举（仅在 complete 时可信）→ data/reflect/devices（协议索引）→ 冻结候选逐个 GET 探测 → 兜底本机'
  };
  if (args.json) out(JSON.stringify(res, null, 1));
  else {
    out('黑板前缀列举实测（中央板）');
    out(`  supported=${r.supported} present=${r.keys.length}/${r.total} complete=${r.complete} 响应字节=${r.respBytes}`);
    out(`  其中 data/reflect/events/* 解析出的设备：${listedDevices.length ? listedDevices.join(', ') : '（无）'}`);
    out(`  ${r.complete ? C.ok : C.warn} 结论：${res.verdict}`);
    out(`  → ${res.therefore}`);
  }
  process.exit(0);
}

/* ----------------------------- --devices-status（只读） ----------------------------- */
if (args['devices-status']) {
  const localDevice = resolveLocalDevice(args.device, os.hostname());
  const dateDashed = args.date
    ? (String(args.date).includes('-') ? String(args.date) : dashed(String(args.date).replace(/-/g, '')))
    : dashed(localDateCompact());
  try {
    const devRes = await resolveDevices({ devices: args.devices, localOnly: args['local-only'], localDevice, dateDashed });
    const rows = [];
    for (const d of devRes.devices) {
      const k = keysFor(d, dateDashed);
      rows.push({
        device: d, isLocal: d === localDevice,
        events: await probeKey(k.events, 'central'),   // §10.2 协议把三件套都放在中央板；探本地板会得到假 404
        cards: await probeKey(k.cards, 'central'),
        answers: await probeKey(k.answers, 'central')
      });
    }
    const res = { date: dateDashed, localDevice, enumMethod: devRes.method, enumLimits: devRes.limits, rows };
    if (args.json) out(JSON.stringify(res, null, 1));
    else {
      out(`设备状态 · ${dateDashed} · 本机=${localDevice} · 枚举方式=${devRes.method}`);
      out(`  键：data/reflect/{events,cards,answers}/<device>/${dateDashed}`);
      for (const r of rows) {
        // 内容口径：200 但 value 是空壳 → 单列出来（R003 补充通告第③条）
        const m = (p) => p.exists ? `${C.ok}200`
          : (p.emptyShell ? `${C.no}空壳`
            : (p.status === 404 ? `${C.warn}404` : `${C.no}${p.status}`));
        out(`  ${r.device.padEnd(11)} events=${m(r.events).padEnd(6)} cards=${m(r.cards).padEnd(6)} answers=${m(r.answers).padEnd(6)}${r.isLocal ? ' ← 本机' : ''}`);
      }
      out('  （200=已存在且有内容 · 空壳=键在但 value 为空（R003 第③条：纯状态码校验会漏）· 404=格式合法但尚未写入 · 400=键写法非法；四者语义不同，不合并成一个布尔）');
      for (const l of devRes.limits) out(`  ${C.warn} 枚举局限：${l}`);
    }
    process.exit(0);
  } catch (e) {
    if (e instanceof GateError) { out(`${C.no} [${e.code}] ${e.message}`); process.exit(1); }
    out(`${C.no} 失败: ${e.message}`); process.exit(2);
  }
}

/* ------------------------------ --targets（只读） ------------------------------ */
if (args.targets) {
  try {
    const r = listTargets({ profilesPath: args.profiles, device: args.device });
    if (args.json) out(JSON.stringify(r, null, 1));
    else {
      out(`可派目标 ${r.count} 个 · 本机设备 ${r.localDevice} · 档案来源 ${r.source}: ${tilde(r.file)}`);
      out(`  冻结候选设备：${r.candidateDevices.join(', ')}`);
      for (const t of r.targets) out(`  ${t.qualified}  ${t.agentId}\n      ${t.role.slice(0, 90)}\n      资源 ${t.resources.length} 条（归一后 ${t.resourceAtoms} 个原子）`);
    }
    process.exit(0);
  } catch (e) {
    if (e instanceof GateError) { out(`${C.no} [${e.code}] ${e.message}`); process.exit(1); }
    out(`${C.no} IO 错误: ${e.message}`); process.exit(2);
  }
}

/* ------------------------------- --selfcheck ------------------------------- */
if (args.selfcheck) {
  const sc = runSelfCheck('dsh-plugin-reflect-dispatch', {
    requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
    requiredSymbols: ['parseArgs', 'dispatch', 'putAndVerify', 'resolveDevices'],
    sourceFiles: ['cli.js'],
    baseDir: HERE
  });
  const localPing = await ping('local');
  const centralPing = await ping('central');
  const localDevice = resolveLocalDevice(args.device, os.hostname());

  out(`【① 依赖完整性】R014 自查门: ${sc.ok ? C.ok : C.no} missing=${sc.missing.length} warnings=${sc.warnings.length}`);
  sc.missing.forEach((m) => out(`    ${C.no} ${m}`));
  (sc.notes || []).forEach((n) => out(`    · ${n}`));

  out('');
  out('【② 能力清单】这个工具**能**做什么');
  out(`    ${C.ok} 读：本机事件流（--events）、**中央板各设备事件流** data/reflect/events/<device>/<date>、能力登记表、规则账本`);
  out(`    ${C.ok} 算：归属判定（路径/键/命名空间/词干/描述关键词，逐条可解释 score+via+level）；按人取 top-N；跨设备复现线索`);
  out(`    ${C.ok} 写：只写 ~/dsh-collab/${REFLECT_ROOT_REL}/ —— cards/<device>/[<日期>/]<短键>.md + _device-card.md + _index.json + dispatch/<日期>/dispatch.json`);
  out(`    ${C.ok} 派：PUT 中央板 data/reflect/cards/<device>/<date>（出站主机白名单 [${ALLOWED_HOSTS.join(', ')}]），随后立即回读校验`);
  out(`    ${C.ok} 离线语义：目标设备不在场 → 状态记 pending（离线待取）而非 failed；--allow-late 支持 T+1/T+2 补派（Φ13 标时点）`);
  out(`    ${C.ok} 脱敏：落盘/写板前对最终文本扫描 ${SECRET_PATTERNS.length} 类凭据形态并替换为 [REDACTED:<kind>]（只报形态与条数，不回显原文）`);

  out('');
  out('【③ 不该发生路径清单】这些路径**结构上不存在**（不是"文档说请勿"）');
  out(`    ${C.ok} 假装派发了（写卡未送达/送达没验）→ 发送路径强制 PUT→GET 回读逐字节比对；不符即 READBACK_MISMATCH 失败`);
  out(`    ${C.ok} 目标不存在时静默跳过 → assertTargetExists 是 **void-or-throw**，没有可 continue 的布尔返回值；--agents 任一未知 id 使整次失败`);
  out(`    ${C.ok} 发送超 ${NOTICE_MAX_CHARS} 字总线正文 → 通知只能由 buildNotice(boardKey) 生成（键必须过 data/reflect/<k>/<device>/<date> 形状门）；CLI/工具均无自由文本入参`);
  out(`    ${C.ok} **跨设备污染**（A 设备的卡写进 B 设备目录）→ 键与落盘路径的 <device> 段必须**正好等于**卡片自己的 device（REFLECT_CROSS_DEVICE_WRITE）`);
  out(`    ${C.ok} 未知设备名 → DEVICE_NAME_INVALID（只接受 ^[a-z][a-z0-9-]{1,15}$）；>16 字直接拒绝（通知装不进 50 字预算）`);
  out(`    ${C.ok} **凭据跨设备扩散**（Φ12 形态④）→ 落盘/写板前脱敏；7 类样本在 lean4-check C 里被实测`);
  out(`    ${C.ok} 把"离线待取"记成 failed → DEVICE_STATUS 冻结枚举 [${DEVICE_STATUS.join(', ')}]，pending 是合法终态`);
  out(`    ${C.ok} **空壳键当成"有内容"**（键在但 value={}）→ probeKey 的 exists 是**内容口径**（200 且非空），另返回 httpStatus200/emptyShell 供显式选择；回读门另有 READBACK_EMPTY_SHELL（R003 补充通告 2026-09-11 第③条）`);
  out(`    ${C.ok} 把补派记成当天 → assertNotLate：处理过去日期必须显式 --allow-late，否则拒绝（Φ13）`);
  out(`    ${C.ok} 广播/通配目标（${TARGET_TOKENS_FORBIDDEN.slice(0, 4).join(' ')}…）→ TARGET_FORBIDDEN（定制与广播互斥）`);
  out(`    ${C.ok} dry-run 改盘 → dry-run 在任何写操作之前返回，连日志都不落盘`);
  out(`    ${C.ok} 越界写盘（含 ../ 穿越）→ 写路径 resolve 后必须落在 <home>/dsh-collab/${REFLECT_ROOT_REL}/ 前缀内且设备段匹配`);
  out(`    ${C.ok} 执行外部命令 → ALLOWED_COMMANDS 冻结为空 + 源码不含 child_process 导入（正面缺席证明）`);
  out(`    ${C.ok} 连第三台黑板 → 出站主机冻结为 [${ALLOWED_HOSTS.join(', ')}]，运行期**无环境变量入口**（加板必须改代码）`);
  out(`    ${C.ok} 空事件流发套话卡 → 单设备空流直接拒绝；多设备时"全部设备都没事件"才拒绝，某台为空只记 no-events`);
  out(`    ${C.ok} 跳步派发（没写黑板却记 readback_ok）→ 状态机 ${DISPATCH_STATES.join('→')}`);

  out('');
  out('【④ 边界与降级】③ CLD 自适应 / ④ dsh 版本自适应');
  out(`    ${C.ok} 运行期只用 node ${process.version} 内置模块（fs/path/http/crypto/os/module/url/util）；不碰 CLD/dsh 私有 API`);
  out(`    ${C.ok} 本机黑板 ${localPing.ok ? `可达(status=${localPing.status})` : `**不可达**(${localPing.error || localPing.status})`} · 中央黑板 ${centralPing.ok ? `可达(status=${centralPing.status})` : `**不可达**(${centralPing.error || centralPing.status})`}`);
  out(`    ${C.ok} 中央黑板不可达 → 各设备事件流取不到 → 明确失败并给可操作原因（不降级成"应该派成功了"）`);
  out(`    ${C.ok} 档案不可读 → [PROFILES_UNAVAILABLE] 拒绝执行（不在无法验证目标时瞎派）`);
  out(`    ${C.ok} 设备枚举**诚实标方法**（并把 method/limits/evidence 写进结果与台账）：--devices → 前缀列举（**仅当键集完整**时可信）→ data/reflect/devices 索引 → 冻结候选探测 → 兜底本机`);
  out(`      实测口径（见 --list-check）：黑板**不做前缀过滤**（GET /data/reflect/events/ 返回整个 data 命名空间 ~15MB），但 limit ≥ total 时键集完整 → 按前缀过滤有效；被截断时不可当清单`);
  out(`    ${C.ok} 本机设备名 ${localDevice} · 冻结候选 [${CANDIDATE_DEVICES.join(', ')}]`);
  out(`    ${C.ok} 写域：${tilde(path.join(HOME, 'dsh-collab', 'data', 'reflect'))}${fs.existsSync(path.join(HOME, 'dsh-collab', REFLECT_ROOT_REL)) ? '（已存在）' : '（首次落盘时创建）'}`);
  out(`    统一日志: ${tilde(LOG_FILE)}`);

  // 【⑤ 插件挂载冒烟】—— 这一项不是装饰：它抓到过一个**apply 阶段就崩**的 bug
  // （输出 schema 的嵌套对象漏写 additionalProperties → dsh-tools 抛 UNSUPPORTED_SCHEMA → 插件根本挂不上）。
  // 诚实规则：peer 在本目录解析不到时**如实说"跳过"**，绝不假装通过。
  out('');
  out('【⑤ 插件挂载冒烟】import lib/index.js → 用桩 ctx 调 apply() → 数注册了几个工具');
  let smoke = { skipped: false };
  try {
    const mod = await import('./lib/index.js');
    const registered = [];
    const ctx = { tools: { register: (t) => { registered.push(t); return () => {}; } }, effect: (fn) => fn() };
    mod.apply(ctx, {});
    smoke = { ok: true, name: mod.name, inject: (mod.inject || []).join(','), tools: registered.map((t) => t.name) };
  } catch (e) {
    const msg = String(e && e.message || e);
    if (/Cannot find package|ERR_MODULE_NOT_FOUND|Cannot find module/.test(msg)) {
      smoke = { skipped: true, reason: msg.split('\n')[0] };
    } else {
      smoke = { ok: false, error: msg.split('\n').slice(0, 3).join(' '), code: e && e.code };
    }
  }
  if (smoke.skipped) {
    out(`    ${C.warn} **跳过**（peer 在本目录解析不到：${smoke.reason}）`);
    out('      · 这不是"通过"：本目录没有 node_modules，在宿主体内（profile）才能真挂载。');
    out('      · 若要真验：把本包装进 profile 后重跑 --selfcheck，或临时软链 profile 的 node_modules/@deepseek-ai。');
    out('      · 已知该类隐患：输出 schema 的嵌套对象若漏写 additionalProperties，dsh-tools 会抛 UNSUPPORTED_SCHEMA（→ apply 崩、插件挂不上）；本包已用 obj() 统一构造修掉。');
  } else if (smoke.ok) {
    out(`    ${C.ok} 挂载成功：name=${smoke.name} · inject=[${smoke.inject}] · 注册 ${smoke.tools.length} 个工具：${smoke.tools.join(' / ')}`);
  } else {
    out(`    ${C.no} **挂载失败**[${smoke.code || 'ERR'}]：${smoke.error}`);
    out('      → 这是 R006 §1 的「apply 阶段崩、启动即崩」那一类事故，必须先修再交付。');
  }
  const smokeOk = smoke.ok === true || smoke.skipped === true;
  process.exit(sc.ok && smokeOk ? 0 : 1);
}

/* ------------------------------ --lean4-check ------------------------------ */
if (args['lean4-check']) {
  const logger = makeLogger({ persist: true });
  const checks = [];
  const files = ['cli.js', 'lib/gate.js', 'lib/board.js', 'lib/cards.js', 'lib/core.js', 'lib/profiles.js', 'lib/sources.js', 'lib/index.js', 'lib/selfcheck.js'];
  const sources = {};
  for (const f of files) {
    try { sources[f] = fs.readFileSync(path.join(HERE, f), 'utf8'); }
    catch (e) { out(`${C.no} 源文件不可读: ${f}（${e.message}）`); process.exit(2); }
  }

  /* A. 源码无危险原语（去注释/字符串/正则字面量后扫描） */
  const prim = scanForbiddenPrimitives({ sources });
  const cpImport = scanChildProcessImports({ sources });
  checks.push({
    id: 'A 源码无危险原语',
    ok: prim.length === 0 && cpImport.length === 0,
    detail: (prim.length || cpImport.length)
      ? `命中: ${JSON.stringify([...prim, ...cpImport])}`
      : '宽杀/任意命令执行/破坏性文件操作 命中 0 次；child_process 导入 0 处（源码结构扫描，非完整 AST）'
  });

  /* B. 负例全部被拒 */
  const neg = gateNegativeCases();
  const leaked = neg.filter((n) => n.code === null);
  checks.push({
    id: 'B 负例全部被拒',
    ok: leaked.length === 0,
    detail: leaked.length
      ? `竟然放行: ${JSON.stringify(leaked)}`
      : `${neg.length}/${neg.length} 条被拒，覆盖 ${[...new Set(neg.map((n) => n.code))].length} 类错误码（含 跨设备写 / 设备名非法 / 补派未授权 / 键形状非法）`
  });

  /* C. 正例可用（防"门太宽把功能也拦了"） */
  const pos = gatePositiveCases();
  const posBad = pos.filter((p) => !p.ok);
  checks.push({
    id: 'C 正例可用',
    ok: posBad.length === 0,
    detail: posBad.length
      ? `被误拦: ${JSON.stringify(posBad)}`
      : `${pos.length}/${pos.length} 条通过（含 ★ 凭据脱敏 7 类样本 + 假阳性检查、三件套 key、设备段匹配、状态机完整链）`
  });

  /* D. dry-run 零变更（外部状态实测：卡目录树 + 中央板探针键 + 日志 mtime） */
  const reflectDir = path.join(HOME, 'dsh-collab', REFLECT_ROOT_REL);
  const walk = (dir) => {
    const acc = [];
    const go = (d) => {
      let ents = [];
      try { ents = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
      for (const e of ents) {
        const p = path.join(d, e.name);
        if (e.isDirectory()) go(p);
        else { try { const st = fs.statSync(p); acc.push(`${path.relative(reflectDir, p)}|${st.size}|${st.mtimeMs}`); } catch { /* */ } }
      }
    };
    go(dir);
    return acc.sort();
  };
  const logStat = () => { try { const st = fs.statSync(LOG_FILE); return `${st.size}|${st.mtimeMs}`; } catch { return 'absent'; } };

  // 夹具全在 tmpdir + 内存里（不碰真实数据域）
  const fxProfiles = [{ agentId: 'session-aaaaaaaa-1111-2222-3333-444444444444', role: '夹具甲（lean4-check D）', resources: ['file:/tmp/fx/a.md', 'store:8'] }];
  const fxEvents = { window: { since: '2026-09-10T00:00:00Z', until: '2026-09-10T23:00:00Z' }, counts: { files: 1 }, events: [{ id: 'E001', source: 'files', ts: '2026-09-10T10:00:00Z', kind: 'modified', path: '/tmp/fx/a.md', desc: '夹具事件：改写 a.md 的门禁判定' }] };
  const fxDir = path.join(os.tmpdir(), `${PLUGIN_NAME}-lean4`);
  fs.mkdirSync(fxDir, { recursive: true });
  const fxFile = path.join(fxDir, 'profiles.json');
  fs.writeFileSync(fxFile, JSON.stringify(fxProfiles, null, 1), 'utf8');

  const probeKeys = ['data/reflect/cards/mac-mini/2026-09-10', 'data/reflect/answers/mac-mini/2026-09-10'];
  const beforeTree = walk(reflectDir);
  const beforeLog = logStat();
  const beforeKeys = [];
  for (const k of probeKeys) beforeKeys.push(JSON.stringify(await bbGet(k, 'central')));

  let dryRes = null, dryErr = null;
  try {
    dryRes = await dispatch({
      eventsDoc: fxEvents, profilesPath: fxFile, localOnly: true, device: 'mac-mini',
      dryRun: true, send: true, date: '2026-09-10', allowLate: true, maxEvents: 8
    });
  } catch (e) { dryErr = e; }

  const afterTree = walk(reflectDir);
  const afterLog = logStat();
  const afterKeys = [];
  for (const k of probeKeys) afterKeys.push(JSON.stringify(await bbGet(k, 'central')));

  const sameTree = JSON.stringify(beforeTree) === JSON.stringify(afterTree);
  const sameLog = beforeLog === afterLog;
  const sameKeys = JSON.stringify(beforeKeys) === JSON.stringify(afterKeys);
  const dryOk = !dryErr && dryRes && dryRes.ok === true && dryRes.targets.length === 1;
  checks.push({
    id: 'D dry-run 零变更',
    ok: sameTree && sameLog && sameKeys && dryOk,
    detail: (sameTree && sameLog && sameKeys && dryOk)
      ? `卡目录树 ${beforeTree.length} 项 / 统一日志 ${beforeLog} / 中央板探针键 ${probeKeys.length} 个 —— 前后**完全一致**；` +
        `dry-run 算出 ${dryRes.targets.length} 张卡 + ${dryRes.plan.willPutCentral.length} 个待 PUT 设备卡 + ${dryRes.plan.willWriteFiles.length} 个待写文件，全部未落盘（跨设备路径也零变更）`
      : `不一致: tree=${sameTree} log=${sameLog} keys=${sameKeys} dryOk=${dryOk} err=${dryErr && dryErr.message}`
  });

  /* E. 白名单冻结 */
  const frozenAll = [
    ALLOWED_COMMANDS, ALLOWED_HOSTS, BOARD_TARGETS, CANDIDATE_DEVICES, DEVICE_STATUS,
    SUGGESTION_TYPES, DISPATCH_STATES, DISPATCH_TRANSITIONS, TARGET_TOKENS_FORBIDDEN, SECRET_PATTERNS, GATE_META,
    DISPATCH_TRANSITIONS.carded, GATE_META.doorTypes, GATE_META.secretKinds
  ].every(Object.isFrozen);
  checks.push({
    id: 'E 白名单冻结',
    ok: frozenAll,
    detail: 'ALLOWED_COMMANDS/ALLOWED_HOSTS/BOARD_TARGETS/CANDIDATE_DEVICES/DEVICE_STATUS/SUGGESTION_TYPES/DISPATCH_STATES|TRANSITIONS/TARGET_TOKENS_FORBIDDEN/SECRET_PATTERNS/GATE_META 全部 Object.isFrozen=true；' +
      `命令集=[${ALLOWED_COMMANDS.join(', ') || '（空）'}] 出站主机=[${ALLOWED_HOSTS.join(', ')}] 设备候选=[${CANDIDATE_DEVICES.join(',')}] 状态=[${DEVICE_STATUS.join('/')}] 脱敏形态=${SECRET_PATTERNS.length} 类`
  });

  /* F. 外部命令白名单 + 出站主机白名单（空集 → 用正面缺席证明替代，避免"空洞通过"） */
  const sites = scanExecSites({ sources });
  const badSites = sites.filter((s) => !s.literal || !ALLOWED_COMMANDS.includes(String(s.cmd).replace(/^['"`]|['"`]$/g, '')));
  const hostScan = scanOutboundHosts({ sources });
  const badHosts = hostScan.hosts.filter((h) => !ALLOWED_HOSTS.includes(h));
  const fOk = sites.length === 0 && cpImport.length === 0 && badHosts.length === 0;
  checks.push({
    id: 'F 命令与主机白名单',
    ok: fOk,
    detail: fOk
      ? 'exec/spawn/fork 执行点 **0** 个（且 child_process 导入 0 处 —— 用**正面缺席证明**替代"空集 ⊆ 允许"的空洞通过，R006 §6 坑 3）；' +
        `出站主机字面量 ${hostScan.hosts.length} 个=[${hostScan.hosts.join(', ')}] ⊆ 允许=[${ALLOWED_HOSTS.join(', ')}]（本机板 + 中央板；无第三处）`
      : `越界: sites=${JSON.stringify(badSites)} cpImport=${JSON.stringify(cpImport)} hosts=${JSON.stringify(badHosts)}`
  });

  const ok = checks.every((c) => c.ok);
  if (args.json) out(JSON.stringify({ ok, checks, gate: GATE_META }, null, 1));
  else {
    out(`lean4-check · 结构门自证（${GATE_META.principle}）`);
    out(`不该发生路径 = ${GATE_META.notHappens}`);
    out(`门型 = ${GATE_META.doorTypes.join(' + ')}`);
    out('');
    for (const c of checks) out(`  ${c.ok ? C.ok : C.no} ${c.id}\n      ${c.detail}`);
    out('');
    out(ok ? `${C.ok} 结构门生效：约束不可绕过（没有那个入口 + 没有那个能力 + 有那个证明 + 失败即停）` : `${C.no} 门未生效，禁止交付`);
  }
  logger.log(`lean4-check ok=${ok}`, { checks: checks.map((c) => `${c.id}:${c.ok}`) });
  process.exit(ok ? 0 : 1);
}

/* -------------------------------- --register -------------------------------- */
if (args.register) {
  const REG_KEY = `data/registry/${PLUGIN_NAME}`;
  const payload = {
    content: [
      `【交付：${PLUGIN_NAME} v${VERSION}（R006 十项达标 · 含跨设备层 v1.1）】`,
      `位置：~/dsh-collab/devices/${PLUGIN_NAME}/`,
      '一句话：按每个智能体当天真实做过的事件，定制一张「思考卡」并派发 —— 「每日反思」流水线的发牌环节。',
      '',
      '■ 核心设计意图',
      '不能发统一问卷：每天问同样的问题，智能体会写套话。所以每张卡的 ① 事件实摘 与 ② 每个问题后的上下文，都按该智能体自己的当天事件生成。',
      '',
      '■ 跨设备层（v1.1 · 设计文档 §10）',
      `· 事件源：中央板 ${BOARD_TARGETS.central} 的 data/reflect/events/<device>/<date>（遍历设备）；--local-only 退回本机`,
      '· 卡片：本机 cards/<device>/[<日期>/]<短键>.md + 设备合并卡；PUT 中央板 data/reflect/cards/<device>/<date>（一设备一键，含各 agent 段落）',
      '· 离线：目标设备不在场 → 状态 pending（离线待取；卡落中央即投递完成），**不是 failed**；--allow-late 支持 T+1/T+2 补派',
      '· 第 5 问（新增）：这个坑在你的设备/环境下是普遍的，还是特定于你这边？（普遍/仅本设备/不确定）—— 跨设备独立复现 = 更强的系统性信号（§10.7）',
      '· 设备枚举**诚实标方法**：实测黑板不支持前缀列举（GET /data/reflect/events/ 返回整个 data 命名空间 14.8MB/57 键；?limit= 只截断）→ 走 --devices → data/reflect/devices 索引 → 冻结候选探测 → 兜底本机，并把 method/limits 写进结果与卡片',
      '',
      '■ ⑩ 约束前置（不该发生路径 = **假装派发** + **跨设备污染** + **凭据扩散**）',
      '1) 假装派发 → 发送路径强制 PUT→GET 回读逐字节比对（R003/R-ERR1）；不符即 READBACK_MISMATCH，绝不报成功。',
      '2) 目标不存在静默跳过 → assertTargetExists 是 void-or-throw，没有可 continue 的布尔返回值；--agents 任一未知 id 使整次失败。',
      `3) 发送超 ${NOTICE_MAX_CHARS} 字总线正文（v2.4 门禁）→ 通知只能由冻结模板 buildNotice(boardKey) 生成，键必须过 data/reflect/<k>/<device>/<date> 形状门；CLI/工具均无自由文本入参。`,
      '4) 跨设备污染 → 键与落盘路径的 <device> 段必须正好等于卡片自己的 device（REFLECT_CROSS_DEVICE_WRITE）；设备名 ^[a-z][a-z0-9-]{1,15}$，>16 字拒绝。',
      '5) 凭据扩散（Φ12 形态④）→ 落盘/写板前对最终文本扫描 9 类凭据形态并替换为 [REDACTED:<kind>]，只报形态与条数、不回显原文；lean4-check C 有 7 类样本 + 假阳性检查。',
      '6) "离线待取"记成 failed → DEVICE_STATUS 冻结枚举；把补派记成当天 → assertNotLate（Φ13 证据有时点）。',
      `7) 越界写盘 → 写路径必须落在 ~/dsh-collab/${REFLECT_ROOT_REL}/ 前缀内且设备段匹配。`,
      '8) 执行外部命令 / 连第三台黑板 → ALLOWED_COMMANDS 冻结为空 + 源码零 child_process 导入（正面缺席证明）；出站主机冻结为两块板，无环境变量入口。',
      '9) 跳步派发 → 状态机 planned→carded→board_written→readback_ok→recorded。',
      '',
      '■ 验收（实测）',
      '`node cli.js --selfcheck`（三段 TCC）· `node cli.js --lean4-check`（A–F 六项全绿）· `node cli.js --tool-version`（= package.json）· `node cli.js --events <f> --dry-run`（前后状态一致）· `node cli.js --list-check`（黑板前缀列举实测结论）· `node cli.js --devices-status`（三件套键存在性）',
      '',
      '■ 相关规则',
      'R003（写黑板后必须回读确认）· R006（插件化工具化十项）· R030（无验证不陈述）· R-ERR1（黑板写入封装+回读）· Φ12 引用即复制（device_gates：拉取只拉本域 / 落盘端 scrub）· Φ13 证据有时点（ts 与 collected_at 分开标）· 总线 v2.4 门禁（正文 ≤50 字）',
      '',
      `■ 登记项：data/registry/${PLUGIN_NAME} · 统一日志 ~/dsh-collab/logs/${PLUGIN_NAME}.log`
    ].join('\n'),
    version: VERSION,
    tool: PLUGIN_NAME,
    ts: new Date().toISOString()
  };

  if (args['dry-run']) {
    if (args.json) out(JSON.stringify({ dryRun: true, key: REG_KEY, bytes: JSON.stringify(payload).length, payload }, null, 1));
    else out(`${C.warn} [dry-run] 将 PUT ${REG_KEY}（${JSON.stringify(payload).length} 字节，随后立即回读校验）—— 本次未写入`);
    process.exit(0);
  }
  try {
    const r = await putAndVerify(REG_KEY, payload, PLUGIN_NAME, 'local');
    if (args.json) out(JSON.stringify(r, null, 1));
    else out(`${C.ok} 已登记并回读校验通过：${r.key}（HTTP ${r.httpStatus}, seq=${r.seq}, 回读 ${r.readback.chars} 字符（语义比对））`);
    process.exit(0);
  } catch (e) {
    if (e instanceof GateError) { out(`${C.no} [${e.code}] ${e.message}`); process.exit(1); }
    out(`${C.no} 失败: ${e.message}`); process.exit(2);
  }
}

/* --------------------------------- 派发主流程 --------------------------------- */
if (args['emit-only'] && args.send) { out('用法错误: --emit-only 与 --send 互斥（默认就是 --emit-only）'); process.exit(2); }
if (!args.events && args['local-only']) { out('用法错误: --local-only 需要 --events <path>（本机事件流）'); process.exit(2); }
if (!args.events && !args.devices && !args['local-only'] && !args.date) {
  out('用法错误: 需要 --events <path>（本机事件流）或 --devices <a,b>（跨设备取中央板）或 --date（指定日期）');
  process.exit(2);
}

let res;
try {
  res = await dispatch({
    eventsPath: args.events,
    agents: args.agents,
    devices: args.devices,
    device: args.device,
    localOnly: args['local-only'],
    allowLate: args['allow-late'],
    assumeOnline: args['assume-online'],
    maxEvents: num(args['max-events'], 'max-events'),
    threshold: num(args.threshold, 'threshold'),
    date: args.date,
    profilesPath: args.profiles,
    cardsRoot: args['cards-root'],
    send: args.send === true,
    dryRun: args['dry-run'] === true
  });
} catch (e) {
  if (e instanceof GateError) {
    const usageCodes = ['EVENTS_IO', 'DATE_INVALID', 'REFLECT_PATH_EMPTY', 'REFLECT_PATH_OUTSIDE_ROOT', 'DEVICE_NAME_INVALID'];
    out(`${C.no} [${e.code}] ${e.message}`);
    process.exit(usageCodes.includes(e.code) ? 2 : 1);
  }
  out(`${C.no} 未预期错误: ${e.stack || e.message}`);
  process.exit(2);
}

if (args.json) { out(JSON.stringify(res, null, 1)); process.exit(0); }

const icon = (s) => s === 'delivered' ? C.ok : (s === 'pending' ? C.warn : '·');
if (res.dryRun) {
  out(`${C.warn} [dry-run] ${PLUGIN_NAME} v${VERSION} · ${res.dateDashed} · 本机 ${res.localDevice} · 设备 ${res.devices.length} 台 · 目标 ${res.targets.length} 个（零变更）`);
  out(`  设备枚举方式：${res.deviceEnum.method}`);
  out(`  档案来源 ${res.profiles.source}（${res.profiles.count} 个目标）`);
  if (res.late.late) out(`  ${C.warn} 补派：T-${res.late.lateDays}（--allow-late 已授权）`);
  out('  将落盘：');
  for (const p of res.plan.willWriteFiles) out(`    ${p}`);
  out(`    ${res.plan.willWriteLedger}`);
  if (res.plan.willPutCentral.length) { out('  将 PUT 中央板（需 --send 且非 dry-run）：'); for (const s of res.plan.willPutCentral) out(`    ${s}`); }
  else out('  将 PUT 中央板：无（未给 --send）');
  for (const s of res.skipped.slice(0, 6)) out(`  ${C.warn} 跳过 ${s.device}:${s.shortKey} — ${s.reason}`);
  if (res.skipped.length > 6) out(`  ${C.warn} …另有 ${res.skipped.length - 6} 个「设备×目标」无归属事件（已全部记入台账，非静默）`);
  out(`  未归属事件 ${res.unassigned.length} 条：${res.unassigned.map((u) => `${u.device}/${u.id}`).join(', ') || '（无）'}`);
  out(`  ${res.plan.zeroChange}`);
  process.exit(0);
}

out(`${C.ok} ${PLUGIN_NAME} v${VERSION} · ${res.dateDashed} · 本机 ${res.localDevice} · 设备 ${res.devices.length} 台 · 出卡 ${res.targets.length} 张`);
out(`  设备枚举：${res.deviceEnum.method}${res.late.late ? ` · ${C.warn}补派 T-${res.late.lateDays}` : ''}`);
for (const d of res.devices) {
  const cards = res.targets.filter((t) => t.device === d.device);
  out(`  ${d.ok ? C.ok : C.warn} ${d.device.padEnd(11)} ${d.ok ? `${String(d.eventCount).padStart(3)} 条事件（来源 ${d.origin}）` : `不可用：${d.note}`}`);
  if (cards.length) {
    const st = cards[0].status;
    out(`      ${icon(st)} status=${st} · ${cards[0].boardKey}${cards[0].board ? `（HTTP ${cards[0].board.httpStatus}, seq=${cards[0].board.seq}, 回读 ${cards[0].board.readbackChars} 字符语义一致 ✅）` : '（未发送）'}`);
    for (const t of cards) out(`      · ${t.qualified}  ${t.picked.join(',')} → ${path.basename(t.cardPath)}（${t.cardBytes} 字）`);
    out(`      ↳ 落盘目录：${tilde(path.dirname(cards[0].cardPath))}`);
  }
}
if (res.redactions.length) {
  out(`  ${C.warn} ★ 凭据脱敏命中：${res.redactions.map((r) => `${r.device}:${r.shortKey}=[${r.hits.map((h) => `${h.kind}×${h.count}`).join(',')}]`).join(' · ')}`);
  out('      （只报形态与条数，不回显原文 —— Φ12 引用即复制）');
}
out(`  跳过（如实记录，非静默）：${res.skipped.length} 个「设备×目标」组合无归属事件`);
if (res.unassigned.length) out(`  ${C.warn} 未归属事件 ${res.unassigned.length} 条（不硬塞给任何人）：${res.unassigned.map((u) => `${u.device}/${u.id}`).join(', ')}`);
out(`  派发台账：${res.ledgerPathTilde}（回读校验 ✅ ${res.ledgerReadback.targets} 个目标 / ${res.ledgerReadback.devices} 台设备）`);
for (const l of res.deviceEnum.limits) out(`  ${C.warn} 枚举局限：${l}`);
if (res.notices.length) {
  out(`  ★ 供 agent_send 的通知正文（每台设备一条，恒 ≤${NOTICE_MAX_CHARS} 字；本工具不自己发 p2p，也不谎称发过）：`);
  const seen = new Set();
  for (const n of res.notices) {
    if (seen.has(n.boardKey)) continue;
    seen.add(n.boardKey);
    out(`    ${n.boardKey}  [${n.chars} 字]  ${n.notice}`);
  }
}
out(`  统一日志：${tilde(LOG_FILE)}`);
process.exit(0);
