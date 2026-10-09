#!/usr/bin/env node
/**
 * cli.js — CLI 治理（R006 ⑨）+ 自检（②）+ 版本（⑥）+ Lean4 约束门自证（⑩）
 * =============================================================================
 * 用法：
 *   node cli.js --status [--json]                 # 只读状态
 *   node cli.js --service cld-voice [--dry-run]    # 激活单个（--dry-run 零变更）
 *   node cli.js --all [--force]                    # 激活白名单全部
 *   node cli.js --selfcheck                        # R014 自查门 + 环境探测
 *   node cli.js --lean4-check                      # 结构门自证（含负例实测）
 *   node cli.js --tool-version
 * 退出码：0=成功/门生效 · 1=失败/门失效 · 2=用法错误
 */
import { parseArgs } from 'node:util';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { activateService, serviceState, listeners, VERSION, LOG_FILE, log } from './lib/activate.js';
import { ALLOWED_KEYS, ALLOWED, GATE_META, GateError, gateNegativeCases, gatePositiveCases, scanBroadKill, scanExecSites, ALLOWED_COMMANDS } from './lib/gate.js';
import { runSelfCheck } from './lib/selfcheck.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const C = { ok: '\u2705', no: '\u274c', warn: '\u26a0\ufe0f' };
function out(s) { process.stdout.write(s + '\n'); }

/* ---------------------------------- 参数 ---------------------------------- */
let args;
try {
  args = parseArgs({
    options: {
      service: { type: 'string' },
      all: { type: 'boolean', default: false },
      'dry-run': { type: 'boolean', default: false },
      force: { type: 'boolean', default: false },
      retries: { type: 'string' },
      'port-wait': { type: 'string' },
      'boot-wait': { type: 'string' },
      status: { type: 'boolean', default: false },
      selfcheck: { type: 'boolean', default: false },
      'tool-version': { type: 'boolean', default: false },
      'lean4-check': { type: 'boolean', default: false },
      json: { type: 'boolean', default: false },
      help: { type: 'boolean', default: false }
    },
    allowPositionals: false
  }).values;
} catch (e) {
  out(`用法错误: ${e.message}`); out('试 --help'); process.exit(2);
}

if (args.help) {
  out(`cldvoice-activate v${VERSION} — 激活性重启（端口释放检查 + 失败重试 + 健康验证）
遵守 R035：能热重启的，就不要直接杀死整个框架。
本工具**不能**重启框架进程：--service 只接受白名单键（${ALLOWED_KEYS.join(' / ')}）。

  --status [--json]        只读：launchd pid / 上次退出码 / 端口监听 / 健康端点
  --service <key>          激活单个服务
  --all                    激活白名单全部
  --dry-run                只打印计划，零变更（lean4-check 会实测验证其零变更）
  --force                  跳过热重启判定，强制重启
  --retries <n>            总尝试次数（默认 3）
  --port-wait <s>          等端口释放上限（默认 20）
  --boot-wait <s>          启动后等就绪上限（默认 25）
  --selfcheck              R014 自查门 + 环境探测
  --lean4-check            结构门自证：AST 无宽杀 + 负例实测 + dry-run 零变更实测
  --tool-version  --help
退出码：0 成功 · 1 失败 · 2 用法错误`);
  process.exit(0);
}

if (args['tool-version']) { out(`cldvoice-activate ${VERSION}`); process.exit(0); }

/* ------------------------------- --selfcheck ------------------------------- */
/**
 * 真挂载冒烟（R006 v3.1.0 ① 第 5 项硬项，2026-09-13 星桥补）
 *
 * 为什么需要：其它九项可以全绿而插件**根本挂不上**（apply 阶段抛异常＝交付物在运行时不存在）。
 * 三态分开报，绝不把 skipped 伪装成 pass：
 *   pass    挂上且注册了预期的东西
 *   fail    apply 抛非依赖类异常 → 真实缺陷
 *   skipped 依赖在本目录解析不到 → 如实说跳过（**据此不得声称 ① 达标**）
 * 两级解析：①本目录 → ②profile / CLD 运行时 node_modules（临时软链，用完即删）。
 */
async function mountSmoke() {
  const RUN_NM = '/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules';
  const PROF_NM = path.join(os.homedir(), '.dsh', 'profiles', 'web', 'node_modules');
  const linkPath = path.join(HERE, 'node_modules');
  let linked = false;
  const isMissingDep = (m) => /Cannot find package|ERR_MODULE_NOT_FOUND|Cannot find module/.test(String(m));
  try {
    let mod;
    // ★ 关键：**先把两级解析准备好，再一次性导入** —— 不要"先失败一次再补救"。
    //   实测教训：先 import 失败、再建软链重试，即使换了 specifier 也会拿着上一次的解析失败
    //   （报错形如 Cannot find package '<plugin>/node_modules/@deepseek-ai/dsh-tools/index.js'），
    //   而同一软链下"直接 import"是成功的。故顺序必须是：选候选 → 建软链 → import。
    const NEED = '@deepseek-ai/dsh-tools';
    const cands = [PROF_NM, RUN_NM].filter((p) => p && fs.existsSync(path.join(p, NEED)));
    try {
      if (cands.length) {
        if (fs.lstatSync(linkPath, { throwIfNoEntry: false })) fs.unlinkSync(linkPath);   // 注意 broken symlink：existsSync 为 false，须用 lstat
        fs.symlinkSync(cands[0], linkPath);
        linked = true;
      }
      mod = await import('./lib/index.js');
    } catch (e) {
      if (!isMissingDep(e?.message ?? e)) throw e;   // 非依赖类 → 外层判 fail
      return {
        state: 'skipped',
        detail: (cands.length
          ? `已建两级软链（${cands[0]}）仍解析失败：`
          : `依赖解析不到，且两级候选均不含 ${NEED}（已查 ${[PROF_NM, RUN_NM].join(' , ')}）：`) +
          String(e.message).split('\n')[0]
      };
    }
    const registered = [];
    const ctx = {
      tools: { register: (t) => { registered.push(t?.name ?? '(anon)'); return () => {}; } },
      effect: (fn) => { try { return fn(); } catch { return () => {}; } },
      on: () => () => {},
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    };
    mod.apply(ctx, {});
    if (typeof mod.apply !== 'function') return { state: 'fail', detail: '未导出 apply()' };
    return { state: 'pass', detail: `name=${mod.name || '(无)'} inject=[${(mod.inject || []).join(',')}] tools=[${registered.join(', ') || '无'}]` };
  } catch (e) {
    return { state: 'fail', detail: String(e?.message ?? e).split('\n').slice(0, 2).join(' ') };
  } finally {
    if (linked) { try { fs.unlinkSync(linkPath); } catch { /* 清理失败不掩盖结论 */ } }
  }
}

if (args.selfcheck) {
  const sc = runSelfCheck('cldvoice-activate', {
    requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
    requiredSymbols: ['parseArgs', 'activateService', 'serviceState'],
    sourceFiles: ['cli.js'],
    baseDir: HERE
  });
  out(`R014 自查门: ${sc.ok ? C.ok : C.no} missing=${sc.missing.length} warnings=${sc.warnings.length}`);
  sc.missing.forEach((m) => out(`    ${C.no} ${m}`));
  sc.warnings.forEach((w) => out(`    ${C.warn} ${w}`));
  (sc.notes || []).forEach((n) => out(`    · ${n}`));

  // ② TCC 检测：本工具的能力边界与「不该发生路径」清单
  out(`TCC 检测（能力边界）:`);
  out(`    ${C.ok} 唯一的下杀调用: launchctl kill SIGTERM <白名单 label>（不含按 PID / 宽杀）`);
  out(`    ${C.ok} 白名单冻结: ${Object.isFrozen(ALLOWED) ? '已冻结' : '未冻结!'} keys=[${ALLOWED_KEYS.join(', ')}]`);
  out(`    ${C.ok} 无任何"重启框架"入口（框架名命中即 GateError）`);

  // ③ CLD 自适应 / ④ dsh 版本自适应
  const domain = `gui/${process.getuid?.() ?? 501}`;
  const launchctlOk = fs.existsSync('/bin/launchctl');
  out(`CLD 自适应: ${launchctlOk ? C.ok : C.no} launchd 域=${domain}（不依赖 CLD 内部 API，纯 launchctl + node 内置模块）`);
  out(`dsh 版本自适应: ${C.ok} 运行期只依赖 node ${process.version} 内置模块；不调用任何 dsh 私有 API`);
  out(`统一日志: ${LOG_FILE}`);

  // ⑤ 真挂载冒烟（R006 v3.1.0 ① 第 5 项硬项）
  const smoke = await mountSmoke();
  const icon = { pass: C.ok, fail: C.no, skipped: C.warn }[smoke.state];
  out(`插件挂载冒烟: ${icon} ${smoke.state} — ${smoke.detail}`);
  if (smoke.state === 'skipped') {
    out(`    ⊘ 未验证 ⇒ **不得据此声称 R006 ① 达标**（依赖解析不到时如实标跳过，绝不假装通过）`);
  } else if (smoke.state === 'fail') {
    out(`    ❌ 这是真实缺陷：其它项全绿也不代表可交付（apply 阶段崩＝交付物在运行时不存在）`);
  }

  // 总判：三态里**只有 pass 算通过**；skipped＝门未生效，同样判未通过（诚实优先于好看）
  const scOk = sc.ok && smoke.state === 'pass';
  out(`自查总判: ${scOk ? C.ok + ' 通过' : C.no + ' 未通过'}` +
      (smoke.state === 'skipped' ? '（挂载冒烟 skipped ＝ 门未生效）' : ''));
  process.exit(scOk ? 0 : 1);
}

/* ------------------------------ --lean4-check ------------------------------ */
if (args['lean4-check']) {
  const checks = [];

  // A. AST/源码级：不存在宽杀调用（本工具 + 内核）
  const files = ['cli.js', 'lib/gate.js', 'lib/activate.js', 'lib/index.js', 'lib/selfcheck.js'];
  const sources = {};
  for (const f of files) sources[f] = fs.readFileSync(path.join(HERE, f), 'utf8');
  const hits = scanBroadKill({ sources });
  checks.push({ id: 'A 源码无宽杀调用', ok: hits.length === 0, detail: hits.length ? JSON.stringify(hits) : 'killall/pkill/process.kill(-1) 命中 0 次' });

  // B. 负例实测：框架名 / 通配 / 空值 / 外部服务名 必须全部被拒
  const neg = gateNegativeCases();
  const leaked = neg.filter((n) => n.code === null);
  checks.push({ id: 'B 负例全部被拒', ok: leaked.length === 0, detail: leaked.length ? `竟然放行: ${JSON.stringify(leaked)}` : `${neg.length}/${neg.length} 条被拒（如 CLD→FRAMEWORK_FORBIDDEN, nginx→UNKNOWN_SERVICE）` });

  // C. 正例：白名单键必须可用
  const pos = gatePositiveCases();
  const posOk = pos.every((p) => p.ok);
  checks.push({ id: 'C 白名单键可用', ok: posOk, detail: pos.map((p) => `${p.key}→${p.ok || 'FAIL'}`).join(', ') });

  // D. dry-run 零变更实测（结构门上再加行为证据）
  const before = {};
  for (const k of ALLOWED_KEYS) before[k] = await serviceState(k);
  for (const k of ALLOWED_KEYS) await activateService(k, { dryRun: true });
  let unchanged = true; const diff = [];
  for (const k of ALLOWED_KEYS) {
    const after = await serviceState(k);
    const same = before[k].launchdPid === after.launchdPid &&
      JSON.stringify(before[k].ports) === JSON.stringify(after.ports);
    if (!same) { unchanged = false; diff.push(k); }
  }
  checks.push({ id: 'D dry-run 零变更', ok: unchanged, detail: unchanged ? 'PID 与端口在 dry-run 前后完全一致' : `发生变更: ${diff.join(',')}` });

  // E. 白名单不可变
  checks.push({ id: 'E 白名单冻结', ok: Object.isFrozen(ALLOWED), detail: `ALLOWED frozen=${Object.isFrozen(ALLOWED)} keys=${ALLOWED_KEYS.join(',')}` });

  // F. 正向证明：全部外部命令执行点必须是字面量且在命令白名单内
  const sites = scanExecSites({ sources });
  const badSites = sites.filter((s) => !s.literal || !ALLOWED_COMMANDS.includes(s.cmd.replace(/^['"`]|['"`]$/g, '')));
  const cmds = [...new Set(sites.map((s) => s.cmd.replace(/^['"`]|['"`]$/g, '')))];
  checks.push({
    id: 'F 外部命令白名单', ok: badSites.length === 0,
    detail: badSites.length ? `越界执行点: ${JSON.stringify(badSites)}` : `${sites.length} 个执行点，命令集=[${cmds.join(', ')}] ⊆ 允许=[${ALLOWED_COMMANDS.join(', ')}]`
  });

  const ok = checks.every((c) => c.ok);
  if (args.json) out(JSON.stringify({ ok, checks, gate: GATE_META }, null, 1));
  else {
    out(`lean4-check · 结构门自证（${GATE_META.principle}）`);
    for (const c of checks) out(`  ${c.ok ? C.ok : C.no} ${c.id} — ${c.detail}`);
    out(ok ? `\n${C.ok} 结构门生效：约束不可绕过（无入口 + 有证明）` : `\n${C.no} 门未生效，禁止交付`);
  }
  log(`lean4-check ok=${ok}`, { checks: checks.map((c) => `${c.id}:${c.ok}`) });
  process.exit(ok ? 0 : 1);
}

/* --------------------------------- -status -------------------------------- */
if (args.status) {
  const keys = args.service ? [args.service] : ALLOWED_KEYS;
  const res = [];
  for (const k of keys) {
    try { res.push(await serviceState(k)); }
    catch (e) { out(`用法错误: ${e.message}`); process.exit(2); }
  }
  if (args.json) out(JSON.stringify(res, null, 1));
  else for (const s of res) {
    out(`${s.key} (${s.label})`);
    out(`  launchd pid=${s.launchdPid} last=${s.lastExit}`);
    out(`  端口: ${Object.entries(s.ports).map(([p, v]) => `:${p} ${v}`).join(' · ')}`);
    out(`  健康: ${s.health.ok ? C.ok : C.no} ${s.health.body}`);
  }
  process.exit(0);
}

/* --------------------------------- 激活 ---------------------------------- */
let keys;
if (args.all) keys = [...ALLOWED_KEYS];
else if (args.service) keys = [args.service];
else { out('用法错误: 需要 --service <key> 或 --all（或 --status/--selfcheck/--lean4-check）'); process.exit(2); }

const opts = {
  dryRun: args['dry-run'],
  force: args.force,
  retries: args.retries ? Number(args.retries) : undefined,
  portWaitSeconds: args['port-wait'] ? Number(args['port-wait']) : undefined,
  bootWaitSeconds: args['boot-wait'] ? Number(args['boot-wait']) : undefined
};

let failed = 0;
for (const k of keys) {
  let r;
  try { r = await activateService(k, opts); }
  catch (e) {
    if (e instanceof GateError) { out(`${C.no} 门拒绝 [${e.code}] ${e.message}`); failed = 1; continue; }
    throw e;
  }
  if (args.json) { out(JSON.stringify(r, null, 1)); continue; }
  if (r.hot) out(`${C.ok} ${r.key}: 无需重启（热生效）— ${r.reason}`);
  else if (r.dryRun) out(`${C.warn} ${r.key}: [dry-run] ${JSON.stringify(r.plan)}`);
  else if (r.ok) out(`${C.ok} ${r.key}: 已激活（pid=${r.after.launchdPid} · 端口 ${Object.entries(r.after.ports).map(([p, v]) => `:${p} ${v}`).join(' ')} · 健康 ok）`);
  else { out(`${C.no} ${r.key}: 连续 ${r.attempts.length} 次未通过 — ${r.diagnosis.hint}`); failed = 1; }
}

if (failed) { out(`\n${C.no} 有服务未通过 —— 不要继续升级流程`); process.exit(1); }
out(`\n${C.ok} 全部通过${opts.dryRun ? '（dry-run：未做任何变更）' : ''}`);
process.exit(0);
