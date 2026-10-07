#!/usr/bin/env node
/**
 * plugin-apply-smoke.mjs — DSH 插件的「真 apply 冒烟」门 v1.0
 *
 * 由来（2026-10-03 MBP CLD 崩溃事故，session-cff6275e 取证）：
 *   dsh-plugin-central-inbox 0.2.8 的 lib/index.js:145 在 ESM 里裸用 `os.homedir()`，
 *   而第 30 行只导入了 `{ homedir, hostname as osHostname }` ⇒ apply() 内抛 ReferenceError
 *   ⇒ cordis `plugin tree failed to load` ⇒ dsh 子进程 exit 1 ⇒ CLD 启动崩溃。
 *
 * 四门负控实测（同一份含缺陷副本，实测于 2026-10-03）：
 *   · node --check lib/index.js            → PASS   （语法检查：ESM 裸全局不是语法错，拦不住）
 *   · 仅 import() 模块（真加载模块层）      → OK     （apply() 未执行，拦不住）
 *   · 插件自带 lib/selftest.js             → 16 PASS（只测纯函数，拦不住）
 *   · 真 apply 冒烟（本工具）               → 拦住 ReferenceError: os is not defined  ★
 *   ⇒ 发版判据必须是「真 apply 冒烟」（comm-standard §4.4 判据先行）。
 *
 * 用法：
 *   1) 冒烟一个插件目录：      node plugin-apply-smoke.mjs <pluginDir>
 *   2) 带缺陷注入的判别力自证：node plugin-apply-smoke.mjs <pluginDir> --selftest "<find>" "<inject>"
 *      ⇒ 正控（原样）必须 PASS，负控（把 <find> 替换成 <inject> 后）必须 FAIL；两者都对才算这道门有效。
 *      实例（本次事故）：--selftest "const SEEN_FILE = homedir()" "const SEEN_FILE = os.homedir()"
 *      注意用**够长的唯一片段**（String.replace 只替换首处；短串会命中同名较早行）。
 *   3) 期望反向（已知会抛）时：--expect throw
 *
 * 安全边界：
 *   · 强制把 HOME 指向临时目录（os.homedir() 优先读 $HOME）⇒ 插件的日志/自查产物/去重表都落到沙箱，
 *     不会污染 ~/.dsh/*（实测核对过：真实 selfcheck 产物 mtime 与 central-inbox.log 均未被改写）。
 *   · 掐断网络（global fetch 直接 reject）⇒ 冒烟不会真连黑板/SSE，不会误注入他机会话。
 *   · stub ctx 只提供最小面（get/effect/on/inject），不构成运行环境。
 *
 * 退出码：0 = 门通过（正控 PASS 且负控被拦），1 = 门失败，2 = 用法错误。
 */
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, cpSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname, resolve, basename } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const SANDBOX_HOME = mkdtempSync(join(tmpdir(), 'apply-smoke-'));
process.env.HOME = SANDBOX_HOME;              // 必须在动态 import 之前
process.env.USERPROFILE = SANDBOX_HOME;
process.env.CENTRAL_AGENT = process.env.CENTRAL_AGENT || 'apply-smoke-dummy';
delete process.env.BLACKBOARD_TOKEN;

const argv = process.argv.slice(2);
const pluginDirArg = argv.find((a) => !a.startsWith('--'));
const flag = (name) => argv.includes(name);
const valueAfter = (name) => {
  const i = argv.indexOf(name);
  return i >= 0 ? argv.slice(i + 1, i + 3) : [];
};
if (!pluginDirArg) {
  console.error('用法: node plugin-apply-smoke.mjs <pluginDir> [--selftest "<defect>" "<replacement>"] [--expect pass|throw]');
  process.exit(2);
}
const expectThrow = (() => {
  const i = argv.indexOf('--expect');
  return i >= 0 ? argv[i + 1] === 'throw' : false;
})();

/** 掐断网络：任何网络调用直接失败（插件内部均有 try/catch，不会阻断 apply） */
globalThis.fetch = () => Promise.reject(new Error('apply-smoke: network disabled'));
class NoNetRequest extends Error {}
globalThis.XMLHttpRequest = class { constructor() { throw new NoNetRequest('apply-smoke: network disabled'); } };

function stubCtx() {
  const bus = {
    list: () => [],
    send: async () => ({ ok: true, dryRun: true }),
    broadcast: async () => ({ ok: true, dryRun: true }),
    claim: () => null,
    release: () => null,
  };
  const noop = () => {};
  return {
    get: (name) => (name === 'agentBus' ? bus : undefined),
    set: noop, provide: noop, inject: noop, effect: noop, on: noop, once: noop, off: noop, emit: noop,
    logger: { info: noop, warn: noop, error: noop, debug: noop },
    get config() { return {}; },
  };
}

/** 跑一次真 apply 冒烟；返回 { ok, error } */
async function smoke(dir) {
  const entry = join(dir, 'lib', 'index.js');
  const entryPath = existsSync(entry) ? entry : join(dir, 'index.js');
  if (!existsSync(entryPath)) return { ok: false, skipped: true, error: new Error(`无插件入口（非插件包，本门不适用）: ${entryPath}`) };
  let mod;
  try {
    mod = await import(pathToFileURL(entryPath).href);
  } catch (e) {
    return { ok: false, error: e, stage: 'import' };
  }
  if (typeof mod.apply !== 'function' && typeof mod.default !== 'function') {
    return { ok: false, error: new Error('模块未导出 apply（也不是 default 函数）——本门不适用') };
  }
  try {
    const fn = typeof mod.apply === 'function' ? mod.apply : mod.default;
    fn(stubCtx());
    return { ok: true, stage: 'apply' };
  } catch (e) {
    return { ok: false, error: e, stage: 'apply' };
  }
}

const label = (r) => r.ok ? 'PASS' : `拦住 -> ${r.error?.constructor?.name || 'Error'}: ${r.error?.message}`;

// ---- 模式 1：判别力自证（正控 + 负控）----
if (flag('--selftest')) {
  const [defect, replacement] = valueAfter('--selftest');
  if (!defect || replacement === undefined) {
    console.error('--selftest 需要两个参数：<find 原串> <inject 注入串>');
    process.exit(2);
  }
  const src = resolve(pluginDirArg);
  const positive = await smoke(src);
  console.log(`正控（原样 ${basename(src)}）: ${label(positive)}`);
  if (positive.skipped) { console.log('结论: 不适用（该目录不是插件包）'); process.exit(3); }

  // 负控：把插件 + 同级兄弟包（relative 依赖如 ../../dsh-comm-shared）复制到沙箱后注入缺陷
  const work = mkdtempSync(join(tmpdir(), 'apply-smoke-nc-'));
  const parent = dirname(src);
  const pkgName = basename(src);
  cpSync(src, join(work, pkgName), { recursive: true });
  for (const sib of ['dsh-comm-shared', 'dsh-tools']) {
    const p = join(parent, sib);
    if (existsSync(p)) cpSync(p, join(work, sib), { recursive: true });
  }
  let injected = 0;
  for (const rel of ['lib/index.js', 'index.js']) {
    const f = join(work, pkgName, rel);
    if (!existsSync(f)) continue;
    const t = readFileSync(f, 'utf8');
    if (!t.includes(defect)) continue;
    writeFileSync(f, t.replace(defect, replacement));
    injected++;
  }
  if (injected === 0) {
    console.log(`负控: 跳过（在 ${pkgName} 里找不到注入目标 ${JSON.stringify(defect)}）——无法自证判别力`);
    process.exit(1);
  }
  const negative = await smoke(join(work, pkgName));
  console.log(`负控（注入 ${JSON.stringify(defect)} → ${JSON.stringify(replacement)} 后）: ${label(negative)}`);

  const gateOk = positive.ok && !negative.ok;
  console.log(`结论: 门${gateOk ? '有效 ✅（正控 PASS 且负控被拦）' : '无效 ❌（不能区分新旧）'}`);
  console.log(`沙箱 HOME: ${SANDBOX_HOME}（真实 ~/.dsh 未被触碰）`);
  process.exit(gateOk ? 0 : 1);
}

// ---- 模式 2：单次冒烟 ----
const r = await smoke(resolve(pluginDirArg));
console.log(`apply 冒烟 ${basename(resolve(pluginDirArg))}: ${label(r)}${r.stage ? `（stage=${r.stage}）` : ''}`);
console.log(`沙箱 HOME: ${SANDBOX_HOME}（真实 ~/.dsh 未被触碰）`);
if (r.skipped) process.exit(3);   // 3 = 不适用（非插件包）
process.exit((expectThrow ? !r.ok : r.ok) ? 0 : 1);
