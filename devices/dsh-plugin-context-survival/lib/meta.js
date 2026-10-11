/**
 * meta.js — 标识 / 版本 / 统一日志（**纯模块**：不 import 任何 dsh/cordis 依赖）
 * =============================================================================
 * 为什么单独一个文件：cli.js 要能在**没挂载、peer 解析不到**时照跑
 * （--selfcheck / --lean4-check / --tool-version）。若 VERSION 放在 lib/index.js，
 * cli.js 一 import 就会拉起 `@deepseek-ai/dsh-tools`，检查本身先崩。
 * 故标识与版本放在这里，lib/index.js 与 cli.js 都从这里取。
 *
 * R006 ⑥：版本**单一来源** = package.json。除本文件外不得第二处硬编码。
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';

export const PLUGIN_SLUG = 'context-survival';

/**
 * ★ 阶段标识的**单一来源**（R006 ⑥ 同精神：版本单一来源 = package.json，阶段单一来源 = 本文件）。
 * ★ 为什么搬到 meta.js：本文件是 index.js 与 cli.js **都**会 import 的纯模块（不拉 dsh 依赖）。
 *   2026-10-10 实测漂移：`lib/index.js` 已走到 K6，而 `cli.js --status` 仍把 stage 写死成 `K5-r006-7of10`
 *   —— **两处漂了整整一档，而当时没有任何门能发现**（contract-check ③ 只比 index.js 的文件头与常量）。
 *   ⇒ 把串收成一处，并加门禁止任何文件再写第二处字面量（contract-check ④）。
 */
export const STAGE = 'K6-wiring-3of3';

/**
 * ★★ 逐件接线状态 —— **单一来源**（与 STAGE 同等对待）。
 * ★ 为什么必须收成一处（2026-10-10，星桥 P2 实测）：接线完成当天，`csx_status` 已报 ②③ `wired`，
 *   而**同一文件**里 `csx_checkpoint` 的描述与 `coreStatus` 仍写「② 落盘 / ③ 召回尚未接线」
 *   —— 同一文件内自相矛盾。根因：状态是**手写在多处**的字符串/布尔，改一处必漏另一处。
 * ⇒ 现在三处（csx_status.wiring · csx_checkpoint.coreStatus · 工具描述尾句）**全部由本对象派生**，
 *   并加门 `contract-check ⑤`：任何文件再写出 `…Wired: true/false` 字面量或「未接线」字样即红。
 */
export const WIRING = Object.freeze({ write: true, persist: true, recall: true });

/** 由 WIRING 派生的中文状态串（描述与 note 共用；**不得**在别处手写）。 */
export function wiringText() {
  const f = (k, name) => `${name} ${WIRING[k] ? '已接线' : '未接线'}`;
  return `${f('write', '① 写入')} · ${f('persist', '② 落盘')} · ${f('recall', '③ 召回')}`;
}
export const PLUGIN_NAME = 'dsh-plugin-context-survival';

export const VERSION = (() => {
  try { return JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8')).version; }
  catch { return '0.0.0-unreadable'; }
})();

/** N5：日志固定路径，失败也留痕。 */
export const LOG_FILE = path.join(os.homedir(), 'dsh-collab', 'logs', `dsh-plugin-${PLUGIN_SLUG}.log`);

/**
 * ★★ 挂载记录（mount record）—— 让「**本进程加载的是哪一版代码**」有一份**可 cat 的**留痕。
 *
 * ★ 立据（P1 的根）：统一日志此前 1719 行里**零行**记录加载版本 ⇒ 要证「在役是哪一版」，
 *   唯一通道是**有人在会话里调一次 `csx_status``** ⇒ 单通道，且证人就是通道本身。
 *   实测形态：盘上 0.12.0 / 在役 0.11.1，只能靠人去调才发现。
 *
 * ★ 五条约束（星桥批准时逐条给定，实现与判据都按它长）：
 *   C1 **零行为改变**：纯日志，写在 try/catch 里，**绝不抛出、绝不改任何状态**；
 *   C2 记 **版本 + 已加载模块 sha256 + mount 时刻(RFC3339) + pid**，且**同版本两次 mount 须可区分**（加 mountId）；
 *   C3 **写在 apply() 时**（不懒到首调）；
 *   C4 **cat 日志即可读出**（一行 JSON，无需先调工具）；
 *   C5 **负控能红** —— 判据在 `tools/csx-mount-record-check.py`（结构检查 + `--expect-current` 对盘面）。
 *
 * ★ 不主张（写死在注释里，免得后人读多）：本记录**不替代** T3 的在役实测；
 *   它只证「某进程在 ts 时刻以 pid 加载了这组哈希」，须与 `ps` 的 boot 时刻**联合判读**。
 * @param {object} extra 附加字段（stage / wiring 等）——由调用方给，本函数不猜
 * @returns 写进日志的记录对象（也便于测试直接调用）
 */
/**
 * ★ 记录来源的**正证据**判定（星桥审查位指出：日志里冒烟 pid 与服务 pid 混着，C4 的**强形式**不成立）。
 * ★ 为什么不用"默认 serve"：默认值就是**静默的错误声明** —— 与本研究线反复出现的「两种成因同痕」同形。
 *   ⇒ 只在**拿到正证据**时才给 serve/smoke；两者都没有就如实写 `unknown`，并把证据字段一并落盘。
 * @returns {{mode:'serve'|'smoke'|'unknown', evidence:string}}
 */
export function mountModeOf(flag, argv1) {
  if (flag === 'smoke' || flag === 'serve') return { mode: flag, evidence: 'config.__mountMode（调用方显式声明）' };
  const base = typeof argv1 === 'string' && argv1.length > 0 ? path.basename(argv1) : '';
  if (base === 'cli.js') return { mode: 'smoke', evidence: `argv1=${base}（本插件 CLI 入口 ⇒ 冒烟/离线路径）` };
  const el = process.versions === undefined ? undefined : process.versions.electron;
  if (typeof el === 'string' && el.length > 0) return { mode: 'serve', evidence: `electron=${el}（宿主 CLD/Electron 进程内加载）` };
  return { mode: 'unknown', evidence: `argv1=${base === '' ? '(空)' : base} · electron=absent ⇒ 既非本插件 CLI，也非 Electron 宿主` };
}

export function mountRecord(extra = {}) {
  const flag = extra.mountMode;
  const { mode, evidence } = mountModeOf(flag, process.argv[1]);
  const cleaned = { ...extra };
  delete cleaned.mountMode;                // 内部信号不外泄成字段；落盘只留判定结果与证据
  const rec = {
    mountId: randomUUID(),
    ts: new Date().toISOString(),          // ISO-8601 / RFC3339（UTC，带毫秒）
    pid: process.pid,
    mode,                                  // serve | smoke | unknown（正证据判定，见 mountModeOf）
    modeEvidence: evidence,
    node: process.version,
    version: VERSION,
    ...cleaned
  };
  try {
    const base = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
    const libDir = path.join(base, 'lib');
    const files = fs.readdirSync(libDir).filter((f) => f.endsWith('.js')).sort();
    const sha = (p) => createHash('sha256').update(fs.readFileSync(p)).digest('hex');
    // 两项哈希：① 宿主真正加载的入口模块；② 整个纯核文件集的合并指纹（重建/换文件都会被看见）
    rec.entryModule = 'lib/index.js';
    rec.entrySha256 = sha(path.join(base, 'lib/index.js'));
    rec.bundleSha256 = createHash('sha256')
      .update(files.map((f) => `${f}:${sha(path.join(libDir, f))}`).join('\n'))
      .digest('hex');
    rec.bundleFiles = files.length;
  } catch (e) {
    // C1：取哈希失败绝不影响挂载 —— 如实标缺失，不猜、不抛
    rec.hashError = e instanceof Error ? e.message : String(e);
  }
  return rec;
}

/** 落一行挂载记录（C3：apply() 时调用）。失败静默（log 自身已 try/catch），绝不外溢。 */
export function logMount(extra = {}) {
  try { return log('mounted', mountRecord(extra)); } catch { return null; }
}

export function log(line, extra) {
  const rec = { ts: new Date().toISOString(), plugin: PLUGIN_SLUG, line, ...(extra || {}) };
  try {
    fs.mkdirSync(path.dirname(LOG_FILE), { recursive: true });
    fs.appendFileSync(LOG_FILE, JSON.stringify(rec) + '\n');
  } catch {
    /* 落盘失败不阻塞主流程 */
  }
  return rec;
}
