/**
 * gate.js — R006 ⑩ 结构门：约束前置 · 不可绕过（Lean4 逻辑门）
 * =============================================================================
 * 本工具唯一的「不该发生路径」是：**采集动作写出/改动了被采集对象**。
 * 一个"只读采集器"如果写坏了被采集对象，就是污染证据链——比不做更危险。
 *
 * 门不是"检查后放行"，而是让那条路径**在结构上不存在**：
 *   1) **没有那个能力**：采集内核 `lib/collect.js` 与 CLI `cli.js` 里
 *      **不含任何写入/删除原语**（writeFileSync / mkdirSync / rmSync / unlinkSync /
 *      renameSync / createWriteStream / openSync … 一个都没有）。A 项扫描证明。
 *   2) **只有一个入口**：全包唯一的写入原语出现在 `lib/log.js`（唯一写入模块）的
 *      三个封装函数里，每个函数**入口第一行**就是 `assertWriteAllowed(target)`。
 *      F 项枚举全部写入调用点 + 回原文读实参证明。
 *   3) **没有那个入口（目标侧）**：`WRITE_TARGETS` 是冻结白名单（3 条规则：
 *      统一日志文件 / data/reflect 产出目录 / 自己的包目录）。
 *      `--out` 不是任意路径——不在白名单内直接 GateError（exit 2）。
 *   4) **没有那个入口（网络侧）**：HTTP 方法白名单冻结为 `['GET']`，
 *      黑板路径白名单冻结为 `['/data/','/notes/']`，主机白名单冻结为环回地址。
 *      写黑板（PUT/POST）这件事**无法表达**。
 *   5) **没有那个能力（命令侧）**：外部命令白名单冻结为 `['git']`，
 *      且只用 `execFileSync`（无 shell），参数由冻结模板拼装、时间值先过严格正则。
 *   6) **失败即停**：任何门不通过 → 抛 GateError → 调用方拒绝执行（不是警告后继续）。
 *   7) **有那个证明**：`--lean4-check` 六项自证 + 负例实测。
 *
 * 直白说：本模块导出的是「不许做什么」的**可执行判据**，不是文档里的「请勿」。
 */

import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';

export class GateError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'GateError';
    this.code = code;
  }
}

/* ───────────────────────────── 路径常量（冻结） ───────────────────────────── */

const HOME = os.homedir();

export const COLLAB_ROOT = Object.freeze(path.join(HOME, 'dsh-collab'));
export const REL_APP_ROOT = Object.freeze(path.join(HOME, 'relationship-graph-app'));
export const SELF_DIR = Object.freeze(path.join(COLLAB_ROOT, 'devices', 'dsh-plugin-reflect-collect'));
export const SELFCHECK_DIR = Object.freeze(path.join(SELF_DIR, '.selfcheck'));
export const LOG_FILE = Object.freeze(path.join(COLLAB_ROOT, 'logs', 'dsh-plugin-reflect-collect.log'));
export const OUT_DIR = Object.freeze(path.join(COLLAB_ROOT, 'data', 'reflect'));

/** 允许被采集的根（白名单，冻结）。任何采集路径必须落在这两个根内。 */
export const COLLECT_ROOTS = Object.freeze([COLLAB_ROOT, REL_APP_ROOT]);

/** 扫描时跳过的目录名（冻结）：版本库/依赖/缓存/构建产物不是"当日事件"。 */
export const EXCLUDE_DIR_NAMES = Object.freeze([
  '.git', 'node_modules', 'node_modules.bak', '.next', '__pycache__', '.venv', 'venv',
  '.pnpm', '.turbo', '.cache', '.mypy_cache', '.pytest_cache', '.parcel-cache', 'dist', 'build'
]);

/** 扫描时跳过的文件名（冻结）。 */
export const EXCLUDE_BASENAMES = Object.freeze(['.DS_Store', 'Thumbs.db']);

/**
 * **自采样排除**（冻结）：本工具自己的产物不得进入自己的采集结果。
 * 理由：日志里天然含 "error/fail" 字样，若不排除，工具每次运行都会把
 * 自己的日志行当成"当日错误痕迹"采回来 —— 自我污染，且随运行次数增长。
 */
export const SELF_ARTIFACTS = Object.freeze([LOG_FILE, OUT_DIR, SELFCHECK_DIR]);

/**
 * 写入目标白名单（冻结，3 条规则）——这是本工具**全部**可写位置的闭集。
 * kind=file 时精确匹配；kind=dir 时匹配该目录及其子孙。
 * 词法路径与 realpath 必须**同时**落在规则内（防软链逃逸）。
 */
export const WRITE_TARGETS = Object.freeze([
  Object.freeze({ kind: 'file', path: LOG_FILE, why: '⑦ 统一日志（唯一固定日志文件）' }),
  Object.freeze({ kind: 'dir', path: OUT_DIR, why: '产出目录 data/reflect/（事件流 JSON）' }),
  Object.freeze({ kind: 'dir', path: SELF_DIR, why: '②⑩ 自查/自证产物只写回自己包内（收紧：不写 ~/.dsh/plugin-selfcheck）' })
]);

/** 唯一允许出现写入原语的模块（冻结）。F 项以此判定"入口唯一"。 */
export const WRITER_MODULES = Object.freeze(['lib/log.js']);

/** 门模块自身（含 assertWriteAllowed/assertHttpGet 的定义与门自己的负例矩阵）。 */
export const GATE_MODULE = Object.freeze('lib/gate.js');

/** 采集内核（必须零写入零删除，A 项扫描对象）。 */
export const READONLY_MODULES = Object.freeze(['lib/collect.js', 'cli.js', 'lib/index.js', 'lib/selfcheck.js', 'lib/version.js']);

/**
 * 网络白名单（冻结）。
 * v1.1 变更（跨设备层）：本工具**新增**一个受控写入点 —— 把事件流 PUT 到中央黑板的
 * `data/reflect/events/<device>/<date>`。因此"无写黑板能力"这条不再成立，
 * 换成更精确的**结构性约束**：
 *   · 读：仅环回主机的 /data/ 与 /notes/（本地黑板永远只读）；中央主机仅 /data/reflect/ 前缀（回读校验/跨设备吸收用）
 *   · 写：**仅**中央主机的**一个 key 形态**（前缀冻结 + device 校验 + date 校验拼成），本地黑板永远不可写
 *   · 除上述之外的一切 (host, path, method) 组合 → GateError（失败即停）
 */
export const ALLOWED_HTTP_METHODS = Object.freeze(['GET', 'PUT']);
export const ALLOWED_HOSTS = Object.freeze(['127.0.0.1', 'localhost', '::1', '[::1]']);
export const ALLOWED_BOARD_PATHS = Object.freeze(['/data/', '/notes/']);

/** 中央黑板（跨设备汇聚点，冻结：不可通过参数改成别的实例）。 */
export const CENTRAL_ORIGIN = Object.freeze('http://106.53.214.108:8792');
export const CENTRAL_HOST = Object.freeze('106.53.214.108');
/** 中央上允许**读**的前缀（回读校验 + 跨设备吸收）。 */
export const CENTRAL_READ_PREFIX = Object.freeze('/data/reflect/');
/** 唯一允许**写**的 key 前缀（跨设备汇聚约定，见 design v1.1 §10.2）。 */
export const UPLOAD_KEY_PREFIX = Object.freeze('data/reflect/events/');
/** 上传路径的完整形态（device 与 date 由冻结构造器拼出）。 */
export const UPLOAD_PATH_RE = Object.freeze(/^\/data\/reflect\/events\/([a-z0-9][a-z0-9-]{0,31})\/(\d{4}-\d{2}-\d{2})$/);

/** 网络模块（唯一允许出现 http.request 的模块）。 */
export const NETWORK_MODULES = Object.freeze(['lib/transport.js']);
/** 上传模块（唯一允许出现"PUT 上传"的模块）。 */
export const UPLOADER_MODULES = Object.freeze(['lib/upload.js']);

/** 外部命令白名单（冻结）：只有 git，且无 shell。 */
export const ALLOWED_COMMANDS = Object.freeze(['git']);
export const ALLOWED_GIT_SUBCOMMANDS = Object.freeze(['rev-parse', 'log']);
export const GIT_LOG_PRETTY = Object.freeze('%H|%ad|%s');
export const ALLOWED_GIT_ARG_PREFIXES = Object.freeze([
  '--is-inside-work-tree',
  '--since=', '--until=', '--date=iso', `--pretty=${GIT_LOG_PRETTY}`, '--no-merges', '--max-count='
]);

/**
 * 设备名（跨设备层的 key 段，见 design v1.1 §10.2）。
 * 设计文档用 `mac-mini` / `mbp` / `i9` 这类**短标签**做 key 段，
 * 而 os.hostname() 返回的是 `CoreydeMac-mini.local` 这种机器名 —— 两者必须对齐，
 * 否则 collect 写的 key 与 dispatch/harvest 读的 key 对不上（跨设备链断在命名上）。
 * 因此：① 冻结别名表（已知机器 → 设计文档标签）；② 未命中则用净化后的短主机名。
 */
export const DEVICE_ALIAS = Object.freeze([
  Object.freeze({ match: /^coreydemac-mini$|^mac-?mini$|^macmini$/, device: 'mac-mini' }),
  Object.freeze({ match: /^coreydemacbook|^corey-?s?-?macbook|^macbook|^mbp$/, device: 'mbp' }),
  Object.freeze({ match: /^pc-?i9$|^i9$|^desktop-/, device: 'i9' })
]);
export const DEVICE_RE = Object.freeze(/^[a-z0-9][a-z0-9-]{0,31}$/);

/** 本机 hostname（原始）→ 短标签 → 设备名。 */
export function hostShortName(hostname) {
  return String(hostname || '').split('.')[0].toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 32);
}

/** 默认设备名：别名表命中则用设计文档标签，否则用净化后的短主机名。 */
export function defaultDevice(hostname) {
  const short = hostShortName(hostname);
  for (const a of DEVICE_ALIAS) {
    if (a.match.test(short)) return { device: a.device, via: 'alias', hostnameShort: short };
  }
  return { device: short, via: 'hostname', hostnameShort: short };
}

/** 门：设备名必须合法（小写字母数字与连字符，≤32 字符）——它要进 key 段，越界写就在这里被拦。 */
export function assertDevice(name) {
  const d = String(name ?? '').trim().toLowerCase();
  if (!DEVICE_RE.test(d)) {
    throw new GateError('DEVICE_INVALID',
      `拒绝 device='${name}'：必须匹配 ${DEVICE_RE}（小写字母/数字/连字符，≤32 字符）。` +
      '设备名会拼进中央黑板 key 段，因此它本身是一道门。');
  }
  if (d.includes('..')) throw new GateError('DEVICE_INVALID', `拒绝 device='${name}'：不允许路径穿越片段。`);
  return d;
}

/* ─────────────────── R003 黑板 key 语法门（2026-09-11 通告 v2 采纳） ─────────────────── */

/**
 * 黑板 key 语法（实测复测后固化）：
 *   · 首段必须**纯小写字母** `[a-z]+`（`data` ✅；`Registry/x`、`Data/reflect` → 实测 400）
 *   · 后续段合法字符集 `[A-Za-z0-9._-]`（`:` `+` `@` `~` `!` 空格 `%2F` → 实测 400；
 *     `a.b-c_d` → 404 = 格式合法但不存在）
 *   · **空段必须由客户端拒**：实测尾斜杠 `data/registry/` → **HTTP 200 + 36.59MB 全量列举**
 *     （不是 400！服务端不报错，只静默降级成"列举全部"）→ 若客户端用"回读有内容=已落地"
 *     这类判据，就会**假通过**；双斜杠 `data//registry` → 404（也不报错）。
 *   这条由本工具在**构造 key 时**拦截（结构上不可表达），不依赖服务端报错。
 */
export const BOARD_KEY_FIRST_RE = Object.freeze(/^[a-z]+$/);
export const BOARD_KEY_SEGMENT_RE = Object.freeze(/^[A-Za-z0-9._-]+$/);

export function assertBoardKeySyntax(key) {
  const k = String(key ?? '');
  if (!k) throw new GateError('KEY_EMPTY', '拒绝空 key。');
  if (k.startsWith('/')) throw new GateError('KEY_LEADING_SLASH', `拒绝 key '${k}'：不允许前导斜杠（URL 构造由 buildUploadUrl 负责）。`);
  if (k.endsWith('/') || k.includes('//')) {
    throw new GateError('KEY_EMPTY_SEGMENT',
      `拒绝 key '${k}'：存在空段（尾斜杠/双斜杠）。服务端**不会**报错 —— 实测尾斜杠返回 ` +
      'HTTP 200 + 全量列举，会被"回读有内容即落地"的判据误判为成功。故空段必须在客户端拦。');
  }
  const segs = k.split('/');
  if (!BOARD_KEY_FIRST_RE.test(segs[0])) {
    throw new GateError('KEY_FIRST_SEGMENT',
      `拒绝 key '${k}'：首段 '${segs[0]}' 必须是纯小写字母 [a-z]+（实测 'Registry/x'、'Data/reflect' → 400 bad key）。`);
  }
  for (const seg of segs.slice(1)) {
    if (!BOARD_KEY_SEGMENT_RE.test(seg)) {
      throw new GateError('KEY_SEGMENT_CHARSET',
        `拒绝 key '${k}'：段 '${seg}' 超出合法字符集 [A-Za-z0-9._-]（实测 ':' '+' '@' '~' '!' 空格 '%2F' 一律 400）。`);
    }
  }
  return k;
}

/** 唯一构造入口：上传 key（不在别处手拼）。 */
export function buildUploadKey(device, date) {
  const d = assertDevice(device);
  const day = String(date ?? '');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) throw new GateError('DATE_INVALID', `拒绝 date='${date}'：需 YYYY-MM-DD（由窗口 since 派生）。`);
  assertTimeSpec(day, 'upload date');
  return assertBoardKeySyntax(`${UPLOAD_KEY_PREFIX}${d}/${day}`);
}

/** 唯一构造入口：上传 URL（origin 冻结为中央实例）。 */
export function buildUploadUrl(device, date) {
  return `${CENTRAL_ORIGIN}/${buildUploadKey(device, date)}`;
}

/**
 * 黑板枚举分页（冻结）—— 采纳 R003 v3 的**统一操作建议**："探活/枚举必须带 ?limit=N"。
 * 实测依据：`/data/`（无 limit）→ 34.90–36.6 MB；`/data/?limit=1` → 120 字节；
 * 且服务端**支持 `offset` 与 `total`**（实测 `?limit=5&offset=5` 返回另一批键，`total=20224` 准确）
 * → 因此"要枚举全部键"不必用一次巨型响应，可以**有界分页**：峰值内存有界、进度可见、截断可判定。
 */
export const BOARD_PAGE_SIZE = Object.freeze(2000);
export const BOARD_MAX_KEYS = Object.freeze(200000);

/** 采集源白名单（冻结）：五个源，各自独立开关。 */
export const SOURCE_KEYS = Object.freeze(['files', 'board', 'tools', 'logs', 'git']);

/* ───────────────────────────── 危险原语清单（冻结） ───────────────────────────── */

/** 写入/删除类原语：采集内核里出现即 A 项失败。 */
export const WRITE_PRIMITIVES = Object.freeze([
  'writeFileSync', 'writeFile', 'appendFileSync', 'appendFile', 'createWriteStream',
  'mkdirSync', 'mkdir', 'rmSync', 'rm', 'rmdirSync', 'unlinkSync', 'unlink',
  'renameSync', 'rename', 'copyFileSync', 'copyFile', 'chmodSync', 'chmod',
  'chownSync', 'chown', 'truncateSync', 'truncate', 'openSync', 'utimesSync',
  'symlinkSync', 'linkSync', 'writevSync'
]);

/**
 * shell 执行形态：全包出现即 A 项失败（本工具只用 execFileSync，无 shell）。
 * ★ 必须用**带前缀否定**的正则，不能用 `line.includes('exec(')`：
 *   初版用 includes 时，本模块自己的 `callRe.exec(code)`（正则对象的 exec 方法）
 *   被当成了 shell 调用 —— 又一次"扫描器误伤自己"（R006 §6 坑 2）。
 */
const SHELL_FORMS = Object.freeze([
  Object.freeze({ name: 'exec(', re: /(?<![\w.$])exec\s*\(/ }),
  Object.freeze({ name: 'execSync(', re: /(?<![\w.$])execSync\s*\(/ }),
  Object.freeze({ name: 'spawn(', re: /(?<![\w.$])spawn\s*\(/ }),
  Object.freeze({ name: 'spawnSync(', re: /(?<![\w.$])spawnSync\s*\(/ }),
  Object.freeze({ name: 'fork(', re: /(?<![\w.$])fork\s*\(/ }),
  Object.freeze({ name: 'shell:true', re: /shell\s*:\s*true/ })
]);

/* ───────────────────────────── 源码扫描（剥字面量） ───────────────────────────── */

/**
 * 去注释 / 字符串 / 模板 / 正则字面量（**行号与偏移保持不变**）。
 * 为什么必须去掉：初版直接扫原文，会把本模块自己的检测词表、帮助文本、
 * 正则当成了"危险调用"——假阳性（R006 §6 坑 2）。
 * 如实标注：这是**源码结构扫描**，不是完整 AST（本包零外部依赖，宿主内无可用解析器）。
 */
export function stripLiterals(src) {
  let out = '';
  let i = 0;
  const n = src.length;
  const pushBlank = (s) => { for (const ch of s) out += (ch === '\n' ? '\n' : ' '); };
  while (i < n) {
    const c = src[i], d = src[i + 1];
    if (c === '/' && d === '/') { let j = i; while (j < n && src[j] !== '\n') j++; pushBlank(src.slice(i, j)); i = j; continue; }
    if (c === '/' && d === '*') { let j = src.indexOf('*/', i + 2); j = j < 0 ? n : j + 2; pushBlank(src.slice(i, j)); i = j; continue; }
    if (c === '"' || c === "'" || c === '`') {
      let j = i + 1;
      while (j < n) { if (src[j] === '\\') { j += 2; continue; } if (src[j] === c) { j++; break; } j++; }
      pushBlank(src.slice(i, j)); i = j; continue;
    }
    if (c === '/') {
      const lineEnd = src.indexOf('\n', i); const stop = lineEnd < 0 ? n : lineEnd;
      const prev = out.replace(/\s+$/, '').slice(-1);
      const regexPos = prev === '' || '(,=:[!&|?{};'.includes(prev);
      if (regexPos) {
        let j = i + 1, closed = false;
        while (j < stop) { if (src[j] === '\\') { j += 2; continue; } if (src[j] === '/') { closed = true; j++; break; } j++; }
        if (closed) { pushBlank(src.slice(i, j)); i = j; continue; }
      }
    }
    out += c; i++;
  }
  return out;
}

/** 在**去字面量**的代码上定位调用点，再**回原文同一偏移**读第一个实参（防"空集通过"）。 */
function scanCallSites({ sources, names, prefixRe }) {
  // `(?:fs\\s*\\.\\s*)?` 不可省：本包的写入调用写作 fs.writeFileSync(...)，
  // 若正则在 `.` 上做否定前瞻，**一个调用点都枚举不到** → "0 ⊆ 允许"空洞通过（R006 §6 坑 3）。
  const callRe = new RegExp(`(?<![\\w.$])(?:fs\\s*\\.\\s*)?(?:${names.join('|')})\\s*\\(`, 'g');
  const sites = [];
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    let m;
    callRe.lastIndex = 0;
    while ((m = callRe.exec(code)) !== null) {
      const line = code.slice(0, m.index).split('\n').length;
      const after = raw.slice(m.index + m[0].length);
      const lit = after.match(/^\s*'([^']*)'/) || after.match(/^\s*"([^"]*)"/) || after.match(/^\s*`([^`]*)`/);
      const nm = m[0].replace(/\s*\($/, '').trim();
      sites.push({ file, line, callee: nm, target: lit ? lit[1] : null, literal: !!lit });
    }
    if (prefixRe) {
      let pm;
      prefixRe.lastIndex = 0;
      while ((pm = prefixRe.exec(code)) !== null) {
        const line = code.slice(0, pm.index).split('\n').length;
        sites.push({ file, line, callee: 'fs.promises.' + pm[1], target: null, literal: false });
      }
    }
  }
  return sites;
}

/** 危险原语扫描（去字面量后）：命中即 A 项失败。 */
export function scanDangerousPrimitives({ sources }) {
  const hits = [];
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    code.split('\n').forEach((line, idx) => {
      for (const name of WRITE_PRIMITIVES) {
        if (new RegExp(`(?<![\\w.$])${name}\\s*\\(`).test(line)) hits.push({ file, line: idx + 1, callee: name, class: 'WRITE_OR_DELETE' });
      }
      for (const form of SHELL_FORMS) {
        if (form.re.test(line)) hits.push({ file, line: idx + 1, callee: form.name, class: 'SHELL_EXEC' });
      }
      if (/\.\s*promises\s*\.\s*(writeFile|appendFile|mkdir|rm|unlink|rename|copyFile|chmod|chown|truncate)\b/.test(line)) {
        hits.push({ file, line: idx + 1, callee: 'fs.promises.*', class: 'WRITE_OR_DELETE' });
      }
    });
  }
  return hits;
}

/** 枚举全部写入调用点（全包），用于 F 项"入口唯一"证明。 */
export function scanWriteSites({ sources }) {
  return scanCallSites({
    sources,
    names: [
      'writeFileSync', 'writeFile', 'appendFileSync', 'appendFile', 'createWriteStream',
      'mkdirSync', 'mkdir', 'rmSync', 'rm', 'rmdirSync', 'unlinkSync', 'unlink',
      'renameSync', 'rename', 'copyFileSync', 'copyFile', 'chmodSync', 'chmod',
      'chownSync', 'chown', 'truncateSync', 'truncate', 'openSync', 'utimesSync',
      'symlinkSync', 'linkSync', 'writevSync'
    ],
    prefixRe: /(?<![\\w.$])promises\s*\.\s*(writeFile|appendFile|mkdir|rm|unlink|rename|copyFile|chmod|chown|truncate)\b/g
  });
}

/** 枚举全部外部命令执行点（全包），第一个实参必须字面量且在命令白名单内。 */
export function scanExecSites({ sources }) {
  const sites = [];
  const callRe = /(?<![\w.$])(execFileSync|execFile|execSync|spawnSync|spawn)\s*\(/g;
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    let m;
    callRe.lastIndex = 0;
    while ((m = callRe.exec(code)) !== null) {
      const line = code.slice(0, m.index).split('\n').length;
      const after = raw.slice(m.index + m[0].length);
      const lit = after.match(/^\s*'([^']*)'/) || after.match(/^\s*"([^"]*)"/) || after.match(/^\s*`([^`]*)`/);
      sites.push({ file, line, callee: m[1], cmd: lit ? lit[1] : null, literal: !!lit });
    }
  }
  return sites;
}

/** 通用：枚举某个函数名的**调用点**并回原文读第一个实参（去定义行、去注释/字符串）。 */
export function scanNameArgSites({ sources, name }) {
  const sites = [];
  const re = new RegExp(`(?<![\\w.$])${name}\\s*\\(`, 'g');
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    let m;
    re.lastIndex = 0;
    while ((m = re.exec(code)) !== null) {
      const before = raw.slice(Math.max(0, m.index - 24), m.index);
      if (/function\s+$/.test(before)) continue;    // 只数调用点，不数定义
      const line = code.slice(0, m.index).split('\n').length;
      const after = raw.slice(m.index + m[0].length);
      const lit = after.match(/^\s*'([^']*)'/) || after.match(/^\s*"([^"]*)"/) || after.match(/^\s*`([^`]*)`/);
      sites.push({ file, line, callee: name, arg: lit ? lit[1] : null, literal: !!lit });
    }
  }
  return sites;
}

/** 枚举 http.request / https.request 调用点（唯一网络模块的证明）。 */
export function scanHttpRequestSites({ sources }) {
  const hits = [];
  const re = /(?<![\w.$])(?:https?|http)\s*\.\s*request\s*\(/g;
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    let m;
    re.lastIndex = 0;
    while ((m = re.exec(code)) !== null) {
      hits.push({ file, line: code.slice(0, m.index).split('\n').length, callee: m[0].trim() });
    }
  }
  return hits;
}

/** 枚举 http method 字面量，断言全部为 GET 或 PUT（且各自绑定在唯一函数里）。 */
export function scanHttpMethods({ sources }) {
  // 只在**去字面量后**定位 `method:` 这个键，再回原文看冒号后是否真的跟一个字符串字面量。
  // 初版直接扫原文的 `method\\s*:\\s*([A-Za-z]+)`，结果把本模块自己源码里的
  // `method: m[1]` / `method: lit ? ...` 当成了 HTTP 方法 → **假阳性**（R006 §6 坑 2）。
  const found = [];
  const re = /method\s*:/g;
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    let m;
    re.lastIndex = 0;
    while ((m = re.exec(code)) !== null) {
      const line = code.slice(0, m.index).split('\n').length;
      const after = raw.slice(m.index + m[0].length);
      const lit = after.match(/^\s*'([^']*)'/) || after.match(/^\s*"([^"]*)"/) || after.match(/^\s*`([^`]*)`/);
      if (lit) found.push({ file, line, method: lit[1] });
      else found.push({ file, line, method: null, literal: false, note: 'method: 后不是字符串字面量（如 method: m[1]），跳过' });
    }
  }
  return found.filter((f) => f.method !== null);
}

/**
 * 枚举 **HTTP 方法门的实际调用点**并回原文读第一个实参。
 * 为什么需要它：`scanHttpMethods` 找的是 `method: 'X'` 这种字面量写法，
 * 而本包的实现是 `assertHttpGet('GET')` —— 若只看前者，结果是**空集**，
 * "0 ⊆ 允许"会**空洞通过**（R006 §6 坑 3）。这里要求调用点 ≥ 1 且实参字面量合法。
 */
export function scanHttpMethodSites({ sources }) {
  const sites = [];
  const callRe = /(?<![\w.$])assertHttpGet\s*\(/g;
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    let m;
    callRe.lastIndex = 0;
    while ((m = callRe.exec(code)) !== null) {
      const line = code.slice(0, m.index).split('\n').length;
      const before = raw.slice(Math.max(0, m.index - 24), m.index);
      if (/function\s+$/.test(before)) continue;   // 跳过 define 行本身（只数调用点）
      const after = raw.slice(m.index + m[0].length);
      const lit = after.match(/^\s*'([^']*)'/) || after.match(/^\s*"([^"]*)"/) || after.match(/^\s*`([^`]*)`/);
      sites.push({ file, line, callee: 'assertHttpGet', method: lit ? lit[1] : null, literal: !!lit });
    }
  }
  return sites;
}

/* ───────────────────────────── 运行时判据（门本体） ───────────────────────────── */

/** 解析最近的已存在祖先的 realpath，再拼回未存在的后缀（防软链逃逸）。 */
export function realpathNearest(p) {
  let cur = path.resolve(p);
  const suffix = [];
  for (let i = 0; i < 64; i++) {
    if (fs.existsSync(cur)) {
      let real;
      try { real = fs.realpathSync(cur); } catch { real = cur; }
      return suffix.length ? path.join(real, ...suffix.reverse()) : real;
    }
    const parent = path.dirname(cur);
    if (parent === cur) return path.resolve(p);
    suffix.push(path.basename(cur));
    cur = parent;
  }
  return path.resolve(p);
}

/** 目标是否在白名单内。返回命中的规则对象，或 null（拒绝）。 */
export function writeRuleFor(target) {
  if (typeof target !== 'string' || !target.trim()) return null;
  const abs = path.resolve(target);
  const real = realpathNearest(abs);
  for (const rule of WRITE_TARGETS) {
    const base = path.resolve(rule.path);
    const baseReal = realpathNearest(base);
    const lexOk = rule.kind === 'file' ? abs === base : (abs === base || abs.startsWith(base + path.sep));
    const realOk = rule.kind === 'file' ? real === baseReal : (real === baseReal || real.startsWith(baseReal + path.sep));
    if (lexOk && realOk) return rule;
  }
  return null;
}

export function isWriteAllowed(target) { return writeRuleFor(target) !== null; }

/** 门：写入目标必须落在冻结白名单内，否则拒绝执行（失败即停）。 */
export function assertWriteAllowed(target) {
  const rule = writeRuleFor(target);
  if (!rule) {
    throw new GateError('WRITE_FORBIDDEN',
      `拒绝写入 '${target}'：不在冻结写入白名单内。本工具是**只读采集器**，只能写：` +
      WRITE_TARGETS.map((r) => r.path).join(' · ') +
      '。写入目标是闭集（含 realpath 校验，防软链逃逸）。');
  }
  return rule;
}

/** 门：HTTP 方法只允许 GET。 */
export function assertHttpGet(method) {
  const m = String(method || '').toUpperCase();
  if (!ALLOWED_HTTP_METHODS.includes(m)) {
    throw new GateError('HTTP_METHOD_FORBIDDEN',
      `拒绝 HTTP ${m}：方法白名单冻结为 [${ALLOWED_HTTP_METHODS.join(', ')}]。` +
      '本工具**不写黑板**（登记卡由人在工具之外落链），因此"写黑板"这件事无法表达。');
  }
  return m;
}

/** 门：黑板地址只允许环回（绝不向远端实例发请求）。 */
export function assertBoardUrl(raw) {
  let u;
  try { u = new URL(String(raw)); }
  catch { throw new GateError('BOARD_URL_INVALID', `拒绝 board-url '${raw}'：不是合法 URL。`); }
  if (u.protocol !== 'http:') {
    throw new GateError('BOARD_PROTOCOL_FORBIDDEN', `拒绝 board-url '${raw}'：只允许 http: 环回。`);
  }
  if (!ALLOWED_HOSTS.includes(u.hostname)) {
    throw new GateError('BOARD_HOST_FORBIDDEN',
      `拒绝 board-url '${raw}'：主机 '${u.hostname}' 不在环回白名单 [${ALLOWED_HOSTS.join(', ')}] 内。` +
      '本地事件源只从环回黑板读（防把远端实例的事件误算成本机事件）；中央实例的读只允许 ' +
      `${CENTRAL_READ_PREFIX} 前缀，且必须经 assertReadTarget（见 upload/回读校验）。`);
  }
  return u;
}

/** 门：黑板路径只允许冻结的两个命名空间。 */
export function assertBoardPath(p) {
  const pathname = String(p);
  if (!ALLOWED_BOARD_PATHS.includes(pathname)) {
    throw new GateError('BOARD_PATH_FORBIDDEN',
      `拒绝黑板路径 '${pathname}'：只允许 [${ALLOWED_BOARD_PATHS.join(', ')}]（命名空间列举，只读）。`);
  }
  return pathname;
}

const TIME_RE = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?$/;

/** 门：时间串严格解析（防把 shell 片段/相对词当参数塞进 git）。 */
export function assertTimeSpec(s, label = 'time') {
  if (typeof s !== 'string' || !s.trim()) {
    throw new GateError('TIME_EMPTY', `拒绝 ${label}='${s}'：不能为空。格式 YYYY-MM-DD[THH:mm[:ss]]。`);
  }
  const t = s.trim();
  if (t.length > 19) throw new GateError('TIME_FORMAT', `拒绝 ${label}='${s}'：超长（>19 字符），格式 YYYY-MM-DD[THH:mm[:ss]]。`);
  const m = TIME_RE.exec(t);
  if (!m) throw new GateError('TIME_FORMAT', `拒绝 ${label}='${s}'：不是严格时间格式（只接受 YYYY-MM-DD[THH:mm[:ss]]）。`);
  const y = +m[1], mo = +m[2], d = +m[3], hh = +(m[4] ?? 0), mi = +(m[5] ?? 0), ss = +(m[6] ?? 0);
  if (mo < 1 || mo > 12 || d < 1 || d > 31 || hh > 23 || mi > 59 || ss > 59) {
    throw new GateError('TIME_INVALID', `拒绝 ${label}='${s}'：日期/时间分量越界。`);
  }
  const dt = new Date(y, mo - 1, d, hh, mi, ss);
  if (dt.getFullYear() !== y || dt.getMonth() !== mo - 1 || dt.getDate() !== d) {
    throw new GateError('TIME_INVALID', `拒绝 ${label}='${s}'：该日期不存在（如 2 月 31 日）。`);
  }
  return { ms: dt.getTime(), iso: fmtLocal(dt), raw: t };
}

export function fmtLocal(d) {
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

/**
 * 设备本地时间 + **显式时区偏移**（如 `2026-09-10T11:05:41+08:00`）。
 * 为什么事件 ts 要带偏移：跨设备流水线里，各设备本地时钟不同步，
 * 只写 `...T11:05:41` 无法判断它与另一台设备的 `...T03:05:41` 是不是同一时刻。
 * 带偏移后 ts 仍是"设备本地时间"（可用性不变），但**跨设备可比**。
 * 实测对齐：中央上已存在的对端设备卡（mbp）其 ts 也是带偏移形态。
 * （window.since/until 保持无偏移形态，与规格示例一致。）
 */
export function fmtLocalWithOffset(d) {
  const off = -d.getTimezoneOffset();
  const sign = off >= 0 ? '+' : '-';
  const hh = String(Math.floor(Math.abs(off) / 60)).padStart(2, '0');
  const mm = String(Math.abs(off) % 60).padStart(2, '0');
  return `${fmtLocal(d)}${sign}${hh}:${mm}`;
}

/** 门：采集路径必须在冻结根内，且不是自产物/排除目录。 */
export function collectPathStatus(p) {
  const abs = path.resolve(String(p));
  const inRoot = COLLECT_ROOTS.some((r) => abs === r || abs.startsWith(r + path.sep));
  if (!inRoot) return { ok: false, code: 'COLLECT_OUT_OF_ROOT', why: `不在采集根内（${COLLECT_ROOTS.join(' · ')}）` };
  const segs = abs.split(path.sep);
  const hitDir = segs.find((s) => EXCLUDE_DIR_NAMES.includes(s));
  if (hitDir) return { ok: false, code: 'COLLECT_EXCLUDED', why: `命中排除目录名 '${hitDir}'` };
  const isSelf = SELF_ARTIFACTS.some((a) => abs === a || abs.startsWith(a + path.sep));
  if (isSelf) return { ok: false, code: 'COLLECT_SELF', why: '是本工具自己的产物（自采样排除：防止日志/产出污染自己的采集结果）' };
  return { ok: true };
}

export function isCollectable(p) { return collectPathStatus(p).ok; }

export function assertCollectPath(p) {
  const st = collectPathStatus(p);
  if (!st.ok) throw new GateError(st.code, `拒绝采集 '${p}'：${st.why}。`);
  return path.resolve(String(p));
}

/** 门：git 子命令与参数必须在冻结白名单内（无 shell + 参数闭集）。 */
export function assertGitArgs(args) {
  const a = Array.isArray(args) ? args.map(String) : [];
  if (!a.length) throw new GateError('GIT_ARGS_EMPTY', '拒绝 git 参数为空。');
  if (!ALLOWED_GIT_SUBCOMMANDS.includes(a[0])) {
    throw new GateError('GIT_SUBCOMMAND_FORBIDDEN',
      `拒绝 git ${a[0]}：子命令白名单冻结为 [${ALLOWED_GIT_SUBCOMMANDS.join(', ')}]。本工具对仓库**只读**。`);
  }
  for (const tok of a.slice(1)) {
    const ok = ALLOWED_GIT_ARG_PREFIXES.some((p) => tok === p || tok.startsWith(p));
    if (!ok) throw new GateError('GIT_ARG_FORBIDDEN', `拒绝 git 参数 '${tok}'：不在冻结参数白名单 [${ALLOWED_GIT_ARG_PREFIXES.join(', ')}] 内。`);
    if (tok.startsWith('--since=') || tok.startsWith('--until=')) {
      assertTimeSpec(tok.slice(tok.indexOf('=') + 1), tok.slice(0, tok.indexOf('=')));
    }
    if (tok.startsWith('--max-count=')) {
      const n = tok.slice('--max-count='.length);
      if (!/^\d{1,6}$/.test(n)) throw new GateError('GIT_ARG_FORBIDDEN', `拒绝 git 参数 '${tok}'：max-count 必须是 1–6 位数字。`);
    }
  }
  return a;
}

/**
 * git 参数的**唯一构造入口**（白名单与实参同源，防"下标引用漂移"）。
 * 血泪条：初版在 collect.js 里用 `ALLOWED_GIT_ARG_PREFIXES[3]` 取 pretty 模板，
 * 白名单后来插了一项 `--is-inside-work-tree`，下标 3 变成 `--date=iso`，
 * 实参漂移成 `--pretty=o` —— 被门当场拒（`拒绝 git 参数 '--pretty=o'`）。
 * 门抓到了错误，但根因是"白名单和构造各写一份"。现改为同源构造器。
 */
export function buildGitProbeArgs() {
  const a = ['rev-parse', '--is-inside-work-tree'];
  return assertGitArgs(a);
}

export function buildGitLogArgs({ sinceIso, untilIso, cap }) {
  const a = [
    'log', `--since=${sinceIso}`, `--until=${untilIso}`, '--date=iso',
    `--pretty=${GIT_LOG_PRETTY}`, '--no-merges', `--max-count=${cap}`
  ];
  return assertGitArgs(a);
}

/** 门：采集源名必须在冻结白名单内。 */
export function assertSources(list) {
  const arr = (Array.isArray(list) ? list : String(list || '').split(',')).map((s) => String(s).trim()).filter(Boolean);
  if (!arr.length) throw new GateError('SOURCES_EMPTY', `拒绝空采集源。可用源：[${SOURCE_KEYS.join(', ')}]。`);
  for (const s of arr) {
    if (!SOURCE_KEYS.includes(s)) {
      throw new GateError('SOURCE_FORBIDDEN', `拒绝采集源 '${s}'：白名单冻结为 [${SOURCE_KEYS.join(', ')}]。`);
    }
  }
  return [...new Set(arr)];
}

/* ─────────────────── ④ peer 版本范围门（可机械核验） ─────────────────── */

function parseVer(v) {
  const m = /^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$/.exec(String(v).trim());
  return m ? { maj: +m[1], min: +m[2], pat: +m[3], pre: m[4] || null } : null;
}

/** semver 序：-1/0/1（预发布 < 正式；同为预发布时按字符串序，够用 rc.1 < rc.2） */
function cmpVer(a, b) {
  for (const k of ['maj', 'min', 'pat']) if (a[k] !== b[k]) return a[k] < b[k] ? -1 : 1;
  if (a.pre === b.pre) return 0;
  if (a.pre === null) return 1;
  if (b.pre === null) return -1;
  return a.pre < b.pre ? -1 : 1;
}

/**
 * 最小 semver 范围判定（**只覆盖本包声明的形态**：`>=A <B` / `>=A <B-0` / `^A` / `A` / `*`）。
 * 为什么要自己写：本包零外部依赖，而 ④ 要求"peer 走正式声明**并被解析**" ——
 * 声明了却解析不上（npm 的预发布语义陷阱）等于没声明。
 * ★ 预发布语义（实测踩到，见 CHANGELOG 纠错 12）：
 *   一个带预发布标签的版本，只有当范围里存在**同 major.minor.patch 且带预发布**的比较器时才会被满足。
 *   所以 `^0.1.0-rc.6` / `>=0.1.0-rc.1 <1.0.0` **都不满足**已安装的 `0.1.1-rc.2`；
 *   而 `*` 也不满足任何预发布版本。实测可用形态：`>=0.1.1-rc.1 <1.0.0-0`。
 * 不支持的形态**明确返回 unsupported**（不假装通过 —— R006 §2 ②的反例就是"会撒谎的检查"）。
 */
export function peerSatisfies(range, version) {
  const v = parseVer(version);
  if (!v) return { ok: false, reason: `版本不可解析: '${version}'` };
  const r = String(range).trim();
  const unsupported = (why) => ({ ok: false, reason: `不支持的 range 形态（本包只支持 >=A <B / >=A <B-0 / ^A / A / *）：'${r}' ${why || ''}` });
  let lower = null, upper = null, exact = null, star = false;
  try {
    if (r === '*') star = true;
    else if (/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(r)) { exact = parseVer(r); if (!exact) return unsupported(); }
    else if (r.startsWith('^')) {
      const c = parseVer(r.slice(1));
      if (!c) return unsupported();
      lower = c;
      upper = c.maj > 0 ? { maj: c.maj + 1, min: 0, pat: 0, pre: null }
        : (c.min > 0 ? { maj: 0, min: c.min + 1, pat: 0, pre: null } : { maj: 0, min: 0, pat: c.pat + 1, pre: null });
    } else {
      for (const part of r.split(/\s+/).filter(Boolean)) {
        if (part.startsWith('>=')) { lower = parseVer(part.slice(2)); if (!lower) return unsupported(); }
        else if (part.startsWith('<')) {
          const body = part.slice(1);
          upper = body.endsWith('-0') ? parseVer(body.slice(0, -2)) : parseVer(body);
          if (!upper) return unsupported();
        } else return unsupported(`（令牌 '${part}'）`);
      }
    }
  } catch { return unsupported(); }

  const comparators = [lower, upper, exact].filter(Boolean);
  if (v.pre) {
    const sameTuplePre = comparators.some((c) => c.maj === v.maj && c.min === v.min && c.pat === v.pat && c.pre);
    if (!sameTuplePre) {
      return { ok: false, reason: `预发布版本 ${version} 不被满足：范围内没有同 major.minor.patch 的预发布比较器（npm semver 语义）` };
    }
  }
  if (star) return { ok: !v.pre, reason: v.pre ? '`*` 不匹配预发布版本（npm 语义）' : '`*` 匹配正式版本' };
  if (exact) return cmpVer(v, exact) === 0 ? { ok: true, reason: `精确匹配 ${version}` } : { ok: false, reason: `${version} ≠ ${r}` };
  if (lower && cmpVer(v, lower) < 0) return { ok: false, reason: `${version} < 下界 ${r}` };
  if (upper && cmpVer(v, upper) >= 0) return { ok: false, reason: `${version} ≥ 上界 ${r}` };
  return { ok: true, reason: `${version} ∈ ${r}` };
}

/* ─────────────────── 读 / 写目标门（跨设备层新增） ─────────────────── */

/** 门：读目标 = GET +（环回主机的 /data/ /notes/）或（中央主机的 /data/reflect/ 前缀）。 */
export function assertReadTarget(url) {
  let u;
  try { u = new URL(String(url)); } catch { throw new GateError('READ_TARGET_FORBIDDEN', `拒绝读取 '${url}'：不是合法 URL。`); }
  assertHttpGet('GET');
  const loopback = ALLOWED_HOSTS.includes(u.hostname);
  // 本机分支复用 assertBoardPath（同一判据只有一份，避免"测试用的门"与"产品用的门"漂移）
  if (loopback) { assertBoardPath(u.pathname); return u; }
  if (u.hostname === CENTRAL_HOST && u.pathname.startsWith(CENTRAL_READ_PREFIX)) {
    // 中央侧的读**只能是精确 key 读**：以 `/` 结尾的路径是"命名空间列举端点"
    // （实测 GET /data/reflect/ 返回该实例全量列举，且响应里没有 value 字段）——
    // 放进读路径就会让"有内容即成功"的判据静默假通过（R003 rule_4）。
    assertBoardKeySyntax(u.pathname.replace(/^\//, ''));
    return u;
  }
  throw new GateError('READ_TARGET_FORBIDDEN',
    `拒绝读取 '${url}'：只允许 (a) 环回主机 + [${ALLOWED_BOARD_PATHS.join(', ')}]，或 ` +
    `(b) 中央实例 ${CENTRAL_HOST} + 前缀 ${CENTRAL_READ_PREFIX}。`);
}

/**
 * 门：上传目标 —— 本工具**唯一**允许的写黑板动作。
 * 四条同时成立才放行：方法是 PUT、主机是中央实例、路径精确匹配
 * `/data/reflect/events/<device>/<date>`（device 与 date 都已被校验）。
 * 任何其它组合（PUT 本地 / PUT 中央别的命名空间 / PUT 别的实例 / 路径穿越）→ GateError。
 */
export function assertBoardUpload(method, url) {
  const m = String(method || '').toUpperCase();
  if (m !== 'PUT') {
    throw new GateError('UPLOAD_METHOD_FORBIDDEN',
      `拒绝上传方法 ${m}：上传只允许 PUT（读只允许 GET），且只用于唯一上传点 ${UPLOAD_KEY_PREFIX}<device>/<date>。`);
  }
  let u;
  try { u = new URL(String(url)); } catch { throw new GateError('UPLOAD_URL_INVALID', `拒绝上传目标 '${url}'：不是合法 URL。`); }
  if (u.hostname !== CENTRAL_HOST) {
    throw new GateError('UPLOAD_HOST_FORBIDDEN',
      `拒绝上传到 '${u.hostname}'：只能写中央实例 ${CENTRAL_HOST}（${CENTRAL_ORIGIN}）。` +
      '本地黑板永远只读——防止把本机事件回流成"外部事件"。');
  }
  if (u.protocol !== 'http:') throw new GateError('UPLOAD_URL_INVALID', `拒绝上传协议 '${u.protocol}'：只允许 http:。`);
  assertBoardKeySyntax(u.pathname.replace(/^\//, ''));
  if (!UPLOAD_PATH_RE.test(u.pathname)) {
    throw new GateError('UPLOAD_PATH_FORBIDDEN',
      `拒绝上传路径 '${u.pathname}'：唯一允许的形态是 ${UPLOAD_KEY_PREFIX}<device>/<date>（例：` +
      `${UPLOAD_KEY_PREFIX}mac-mini/2026-09-10）。其它命名空间（registry/ack/iterations…）本工具不可写。`);
  }
  return u;
}

/* ─────────────────── 凭据扫描（跨设备扩散防线 / Φ12 形态④） ─────────────────── */

const BENIGN_VALUES = Object.freeze(['[redacted]', 'redacted', 'null', 'undefined', 'true', 'false', 'none', '***', '']);
const isBenign = (v) => BENIGN_VALUES.includes(String(v).toLowerCase());

/** 高熵形态的最低要求：同时含字母与数字（纯词/纯数字不算凭据）。 */
function mixedAlnum(v) {
  const t = String(v);
  return /[A-Za-z]/.test(t) && /\d/.test(t) && !isBenign(t);
}

/**
 * 凭据形态表（冻结）。**这是形态启发式，不是完备 DLP** —— 如实标注局限：
 *   · 能抓：4-4-4 分组混合串、FL-XX-#### 供应商号、`token=/secret=/key=` 赋值、
 *     Bearer、PEM 私钥、常见前缀密钥（sk-/ghp_/glpat-/xox/AKIA/app-…）
 *   · 抓不到：无分组形态的自定义凭据、被 base64/压缩包裹的凭据
 *   · **刻意不抓**：≥32 位十六进制（那是 sha256——本流水线用它做回读校验，脱敏会毁掉证据）；
 *     通用 40+ base64 串（实测在真实事件流里 100% 是路径/文件名 → 会毁掉事件流）
 */
export const SECRET_PATTERNS = Object.freeze([
  Object.freeze({
    name: 'grouped-triplet',
    re: Object.freeze(/(?<![0-9a-z-])[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}(?![0-9a-z-])/g),
    // 三段**每段**都要既含字母又含数字；且整体不是 UUID/路径片段（前后 lookaround 已排除）。
    // 实测：不加此谓词时，真实事件流里 `flowernet-tech-path-moat-revision-v1.md`、
    // `664ce0d2-2ef1-4a68-b1d4-b86209009911`(UUID)、`cloudbase-plan-push-task` 会被误脱敏。
    pass: (m) => m.split('-').every((seg) => /[a-z]/.test(seg) && /\d/.test(seg))
  }),
  Object.freeze({
    name: 'provider-id-FL',
    re: Object.freeze(/\bFL-[A-Za-z0-9]{2,8}-[0-9]{3,8}\b/g),
    pass: () => true
  }),
  Object.freeze({
    name: 'assignment',
    // 带引号的 JSON 键（`"key":"…"`）**不匹配**：黑板 key 长得就像赋值，误伤会毁掉事件流。
    // 因此 bare `key` 只认 `=`（CLI/env 形态），且值里不允许出现 `/`。
    re: Object.freeze(/\b(token|secret|api[_-]?key|apikey|access[_-]?key|private[_-]?key|app[_-]?secret|appkey|password|passwd|auth[_-]?token|credential|key)\s*([:=])\s*["'`]?([A-Za-z0-9_\-+=.]{16,})/g),
    pass: (m, g) => g[2] === '=' || !/^(key)$/.test(g[1]),   // bare key 只认 `=`
    group: 3
  }),
  Object.freeze({
    name: 'bearer',
    re: Object.freeze(/\b[Bb]earer\s+([A-Za-z0-9._\-]{20,})/g),
    pass: (m, g) => mixedAlnum(g[1]),
    group: 1
  }),
  Object.freeze({
    name: 'pem-private-key',
    re: Object.freeze(/-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g),
    pass: () => true
  }),
  Object.freeze({
    name: 'known-prefix',
    re: Object.freeze(/\b(sk-ant-[A-Za-z0-9_\-]{20,}|sk-[A-Za-z0-9_\-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_\-]{16,}|xox[baprs]-[A-Za-z0-9\-]{10,}|AKIA[0-9A-Z]{16}|app-[A-Za-z0-9]{20,})/g),
    // app-…：实测 `laodeng-app-arch-v1_0-20260903-100236.svg` 这类文件名极易误伤，
    // 故要求 20 位连续字母数字（文件名在 `app-arch` 后就是 `-`，直接不匹配）+ 混合大小写 + 含数字。
    pass: (m) => mixedAlnum(m) && /[a-z]/.test(m) && /[A-Z]/.test(m) && /\d/.test(m)
  })
]);

/**
 * 凭据扫描 + 脱敏。命中 → 替换为 `[REDACTED]` 并计数。
 * 结构位置：**写入本地产出文件之前**与**上传中央之前**都会调用（同一份 payload），
 * 所以不存在"本地脱敏了、上传没脱敏"这种路径。
 */
export function redactSecrets(text) {
  let out = String(text ?? '');
  const byPattern = {};
  let count = 0;
  for (const p of SECRET_PATTERNS) {
    const re = new RegExp(p.re.source, p.re.flags.includes('g') ? p.re.flags : p.re.flags + 'g');
    let m;
    let work = '';
    let last = 0;
    while ((m = re.exec(out)) !== null) {
      const groups = m.slice();
      if (p.pass && !p.pass(m[0], groups)) continue;
      const secret = p.group ? groups[p.group] : m[0];
      if (!secret) continue;
      const start = p.group ? m.index + m[0].indexOf(secret) : m.index;
      work += out.slice(last, start) + '[REDACTED]';
      last = start + secret.length;
      count += 1;
      byPattern[p.name] = (byPattern[p.name] || 0) + 1;
      if (m[0].length === 0) re.lastIndex += 1;
    }
    if (last > 0) { work += out.slice(last); out = work; }
  }
  return { text: out, count, byPattern };
}

/* ─────────────────── 事件时点门（跨设备时钟不同步 / Φ13） ─────────────────── */

export const EVENT_TIME_FIELDS = Object.freeze(['ts', 'collected_at', 'origin_device']);

/**
 * 门：每条事件必须同时带**三个时点/来源字段**。
 * 为什么必须有：跨设备后"文件在哪"与"谁采的"不是一回事（同步盘）、
 * 各设备时钟也不同步 —— 只有 ts（对象自身时刻）+ collected_at（采集时刻）+
 * origin_device（采集者）三者分开，synthesize 才能判断"这是什么时候、谁看到的"。
 */
export function assertEventStamped(ev) {
  for (const f of EVENT_TIME_FIELDS) {
    const v = ev && ev[f];
    if (v === undefined || v === null || v === '') {
      throw new GateError('EVENT_UNSTAMPED', `拒绝事件：缺字段 '${f}'（必须有 ts / collected_at / origin_device 三者）。`);
    }
  }
  const t1 = assertTimeSpec(String(ev.ts).slice(0, 19).replace(' ', 'T'), 'event.ts');
  const t2 = assertTimeSpec(String(ev.collected_at).slice(0, 19).replace(' ', 'T'), 'event.collected_at');
  const d = String(ev.origin_device);
  if (!DEVICE_RE.test(d)) throw new GateError('EVENT_UNSTAMPED', `拒绝事件：origin_device='${d}' 不合法。`);
  return { ts: t1.ms, collectedAt: t2.ms };
}

/* ─────────────────── 回读校验门（"非 200 不能假定成功"） ─────────────────── */

/**
 * 规范化 JSON（键排序、无空白）—— 回读比对的**唯一可比形态**。
 * ★ 为什么不能直接比原文 sha256（v1.1 实测踩到）：
 *   黑板把上传体存为卡片信封 `{key,ts,value,version}`，GET 回来的是**重新序列化**的 JSON
 *   （信封包裹 + 键序变化），因此"原文 sha256"必然不一致 —— 那是**假失败**
 *   （R006 §6 坑 4：检查报错，报错了对象）。实测：原文 sha 82445f… vs 回读 c3087f…，
 *   而规范化后两侧**完全相同**（9ac34f97…）。所以判据是"规范化 JSON 相等"，
 *   原文 sha 只作为诊断字段保留。
 */
export function canonicalJson(v) {
  if (v === null || typeof v !== 'object') return JSON.stringify(v);
  if (Array.isArray(v)) return '[' + v.map(canonicalJson).join(',') + ']';
  return '{' + Object.keys(v).sort().map((k) => JSON.stringify(k) + ':' + canonicalJson(v[k])).join(',') + '}';
}

/**
 * 上传结果判据：**必须回读 + 规范化内容一致 + key 一致 + HTTP 200**，缺一即判失败。
 * 依据：本日已发生 4 次"报告指向不存在的落盘物"（写入返回非 200 被当成成功）。
 */
export function verifyReadback({ putStatus, expectedSha256, readbackStatus, readbackSha256, expectedKey, readbackKey }) {
  if (putStatus !== 200) return { ok: false, reason: `PUT 返回 ${putStatus}（非 200，不能假定成功）` };
  if (readbackStatus !== 200) return { ok: false, reason: `回读返回 ${readbackStatus}（写入物不存在或不可读 → 视为失败）` };
  if (!expectedSha256 || !readbackSha256) return { ok: false, reason: '缺少规范化 sha256（期望值或回读值），无法证明写入' };
  if (expectedSha256 !== readbackSha256) return { ok: false, reason: `回读内容不一致（规范化 sha256）：期望 ${expectedSha256.slice(0, 12)}… 实际 ${readbackSha256.slice(0, 12)}…` };
  if (expectedKey !== undefined && readbackKey !== undefined && String(readbackKey) !== String(expectedKey)) {
    return { ok: false, reason: `回读回来了另一个 key：期望 ${expectedKey} 实际 ${readbackKey}` };
  }
  return { ok: true, reason: `PUT 200 + 回读 200 + 规范化内容一致（sha256 ${expectedSha256.slice(0, 12)}…）` };
}

/** 任意文本的 sha256（诊断用；判据用 canonicalJson 的 sha256）。 */
export function sha256Hex(text) {
  return crypto.createHash('sha256').update(String(text), 'utf8').digest('hex');
}

/** 上传载荷的**规范化** sha256（判据）。 */
export function canonicalSha256(value) {
  return sha256Hex(canonicalJson(value));
}

/* ───────────────────────────── 负例 / 正例矩阵 ───────────────────────────── */

const NEG_WRITE_TARGETS = Object.freeze([
  '', '   ', '/etc/passwd', '/tmp/x.json',
  path.join(COLLAB_ROOT, 'docs', 'R006-x.md'),
  path.join(COLLAB_ROOT, 'scripts', 'evil.py'),
  path.join(COLLAB_ROOT, 'devices', 'dsh-plugin-cldvoice-activate', 'lib', 'index.js'),
  path.join(COLLAB_ROOT, 'data', 'registry', 'dsh-plugin-reflect-collect'),
  path.join(COLLAB_ROOT, 'logs', 'other-tool.log'),
  path.join(COLLAB_ROOT, 'logs', 'dsh-plugin-reflect-collect.log.1'),
  path.join(LOG_FILE, '..', 'other.log'),
  path.join(OUT_DIR, '..', 'registry', 'x.json'),
  path.join(REL_APP_ROOT, 'data', 'x.json'),
  path.join(SELF_DIR, '..', 'dsh-plugin-cldvoice-activate', 'x.js'),
  path.join(OUT_DIR, 'sub', '..', '..', '..', 'Documents', 'x.json')
]);

/** 负例矩阵：每条都必须被门拒绝（code !== null 表示竟然放过了 = 门失效）。 */
export function gateNegativeCases() {
  const cases = [];
  const probe = (group, input, fn, label) => {
    try { fn(input); cases.push({ group, input: label ?? String(input), code: null }); }
    catch (e) { cases.push({ group, input: label ?? String(input), code: e.code || 'ERROR' }); }
  };

  for (const t of NEG_WRITE_TARGETS) probe('write-target', t, (x) => assertWriteAllowed(x), t || '(空)');
  for (const m of ['POST', 'DELETE', 'PATCH', 'post', 'delete', 'head']) probe('http-method', m, (x) => assertHttpGet(x));
  for (const u of ['http://106.53.214.108:8792', 'http://example.com', 'https://127.0.0.1:8792', 'ftp://127.0.0.1', 'not a url', '']) {
    probe('board-url', u, (x) => assertBoardUrl(x), u || '(空)');
  }
  for (const p of ['/data/registry/x', '/', '/notes', '/tasks/', '/data', '/health', '/data/../etc']) {
    probe('board-path', p, (x) => assertBoardPath(x));
  }
  for (const t of ['2026-01-01; rm -rf /', '$(date)', '`date`', 'now', 'today', '2026-13-01', '2026-02-31', '2026-09-10T99:00', '2026-09-10 00:00:00 extra', '', '   ', '2026-09-10T00:00:00Z']) {
    probe('time-spec', t, (x) => assertTimeSpec(x), t || '(空)');
  }
  for (const p of ['/etc', path.join(HOME, 'Documents'), path.join(HOME, '.ssh'), path.join(COLLAB_ROOT, '..', 'Documents'), COLLAB_ROOT.replace('dsh-collab', 'Documents')]) {
    probe('collect-path', p, (x) => assertCollectPath(x));
  }
  probe('collect-path', 'git dir', (x) => assertCollectPath(path.join(COLLAB_ROOT, '.git', 'config')), path.join(COLLAB_ROOT, '.git', 'config'));
  probe('collect-path', 'node_modules', (x) => assertCollectPath(path.join(COLLAB_ROOT, 'node_modules', 'x.js')), path.join(COLLAB_ROOT, 'node_modules', 'x.js'));
  probe('collect-path', 'self log', (x) => assertCollectPath(LOG_FILE), LOG_FILE);
  probe('collect-path', 'self out', (x) => assertCollectPath(path.join(OUT_DIR, 'events-20260910.json')), path.join(OUT_DIR, 'events-20260910.json'));
  for (const a of [['push', 'origin', 'main'], ['clean', '-fdx'], ['log', '--output=/tmp/x'], ['log', '; rm -rf /'], ['log', '--since=2026-01-01; rm -rf /'], ['checkout', 'main'], []]) {
    probe('git-args', a.join(' '), (x) => assertGitArgs(x), `git ${a.join(' ') || '(空)'}`);
  }
  for (const s of [['files', 'hack'], [''], [], ['FILES'], ['files/../..']]) {
    probe('sources', s.join(','), (x) => assertSources(x), `sources=${s.join(',') || '(空)'}`);
  }

  // 跨设备层（v1.1）：上传目标门
  const up = (dev, day) => buildUploadUrl(dev, day);
  for (const [m, url, label] of [
    ['POST', up('mac-mini', '2026-09-10'), 'POST 中央 reflect 路径'],
    ['PUT', `http://127.0.0.1:8792/data/reflect/events/mac-mini/2026-09-10`, 'PUT 本地黑板'],
    ['PUT', `http://127.0.0.1:8792/data/registry/dsh-plugin-reflect-collect`, 'PUT 本地 registry'],
    ['PUT', `${CENTRAL_ORIGIN}/data/registry/dsh-plugin-reflect-collect`, 'PUT 中央 registry'],
    ['PUT', `${CENTRAL_ORIGIN}/data/reflect/cards/mbp/2026-09-10`, 'PUT 中央 cards（别的环节的命名空间）'],
    ['PUT', `${CENTRAL_ORIGIN}/data/reflect/events/mac-mini`, 'PUT 缺 date 段'],
    ['PUT', `${CENTRAL_ORIGIN}/data/reflect/events/mac-mini/2026-09-10/extra`, 'PUT 多余段'],
    ['PUT', `${CENTRAL_ORIGIN}/data/reflect/events/../registry/x/2026-09-10`, 'PUT 路径穿越'],
    ['PUT', `${CENTRAL_ORIGIN}/data/reflect/events/MAC-MINI/2026-09-10`, 'PUT device 大写（形态不符）'],
    ['PUT', 'http://10.0.0.9:8792/data/reflect/events/mac-mini/2026-09-10', 'PUT 其它主机'],
    ['PUT', 'https://106.53.214.108:8792/data/reflect/events/mac-mini/2026-09-10', 'PUT https（协议不符）'],
    ['PUT', 'not a url', 'PUT 非法 URL'],
    ['PUT', `${CENTRAL_ORIGIN}/data/reflect/events/mac-mini/2026-9-1`, 'PUT 非零填日期']
  ]) probe('upload-target', `${m} ${url}`, () => assertBoardUpload(m, url), label);

  // 跨设备层：设备名门（注意 'MAC-MINI'/'cld-health' 属于**合法**输入：前者归一化为小写、
  // 后者是后续段（后续段可含连字符）；把它们当负例会假失败。故此处只放形态非法的输入。）
  for (const d of ['', '  ', 'mac mini', 'Mac_Mini', 'mac_mini', '../etc', 'a'.repeat(33), 'mac-mini/../x', '-lead', 'mac-mini/', '中文设备', null, undefined]) {
    cases.push({ group: 'device', input: `device=${JSON.stringify(d)}`, code: (() => { try { assertDevice(d); return null; } catch (e) { return e.code || 'ERROR'; } })() });
  }

  // 跨设备层：读目标门（远端随便读也不行）
  for (const u of ['http://10.0.0.9:8792/data/', `${CENTRAL_ORIGIN}/data/`, `${CENTRAL_ORIGIN}/data/registry/x`, `${CENTRAL_ORIGIN}/notes/`, 'http://127.0.0.1:8792/data/reflect/']) {
    probe('read-target', u, (x) => assertReadTarget(x));
  }
  // R003 rule_4 的"尾斜杠 → 全量列举"陷阱：本工具读路径只允许两个列举端点
  // （本机 /data/ 与 /notes/）与中央 /data/reflect/ 前缀，其余以 / 结尾的路径一律拒 ——
  // 实测 `GET /data/registry/` = 200 + 36,596,419 B / 20,222 键（无 value 字段），
  // 若放进读路径，任何"有内容即成功"的判据都会静默假通过。
  for (const u of [
    'http://127.0.0.1:8792/data/registry/',
    'http://127.0.0.1:8792/data/reflect/',
    `${CENTRAL_ORIGIN}/data/registry/`,
    `${CENTRAL_ORIGIN}/data/reflect/`,
    `${CENTRAL_ORIGIN}/data/`
  ]) probe('read-target-trailing-slash', u, (x) => assertReadTarget(x));

  // 跨设备层：事件时点门
  for (const ev of [
    { collected_at: '2026-09-10T00:00:00', origin_device: 'mac-mini' },
    { ts: '2026-09-10T00:00:00', origin_device: 'mac-mini' },
    { ts: '2026-09-10T00:00:00', collected_at: '2026-09-10T00:00:00' },
    { ts: '2026-09-10T00:00:00', collected_at: '2026-09-10T00:00:00', origin_device: 'MAC-MINI' },
    { ts: 'garbage', collected_at: '2026-09-10T00:00:00', origin_device: 'mac-mini' },
    { ts: '2026-09-10T00:00:00', collected_at: '2026-02-31T00:00:00', origin_device: 'mac-mini' },
    null
  ]) probe('event-stamp', JSON.stringify(ev), (x) => assertEventStamped(x), `event=${JSON.stringify(ev)}`);

  // R003 key 语法门（负例全部取自实测 400 / 静默降级形态）
  for (const [k, why] of [
    ['', '空 key'],
    ['/data/reflect', '前导斜杠'],
    ['data/registry/', '尾斜杠（实测 HTTP 200 + 全量列举，不报错 → 必须客户端拦）'],
    ['data//registry', '双斜杠空段（实测 404，不报错）'],
    ['data/reflect/events/mac-mini/2026-09-10/', '深路径尾斜杠'],
    ['Registry/x', '首段非纯小写（实测 400）'],
    ['Data/reflect', '首段含大写（实测 400）'],
    ['data/reflect/a b', '段内空格（实测 400）'],
    ['data/reflect/a:b', '段内冒号（实测 400）'],
    ['data/reflect/a+b', '段内加号（实测 400）'],
    ['data/reflect/a@b', '段内 @（实测 400）'],
    ['data/reflect/a~b', '段内 ~（实测 400）'],
    ['data/reflect/a!b', '段内 !（实测 400）'],
    ['data/reflect/..%2Fx', '编码斜杠（实测 400）'],
    ['data/reflect/#frag', '段内 #'],
    ['data/reflect/a?b=1', '段内 ?']
  ]) cases.push({ group: 'board-key', input: `${k || '(空)'}（${why}）`, code: (() => { try { assertBoardKeySyntax(k); return null; } catch (e) { return e.code || 'ERROR'; } })() });

  // ④ peer 范围门（含真实世界反例：参考实现与常见写法都解析不上）
  for (const [range, ver, why] of [
    ['^0.1.0-rc.6', '0.1.1-rc.2', '参考实现 dsh-plugin-cldvoice-activate 的写法（实测不满足）'],
    ['>=0.1.0-rc.1 <1.0.0', '0.1.1-rc.2', '看似宽松，但预发布语义下不满足'],
    ['>=0.1.0-rc.1 <1.0.0-0', '0.1.1-rc.2', '仍是 tuple 不匹配'],
    ['*', '0.1.1-rc.2', '`*` 不匹配预发布'],
    ['^1.0.0', '0.1.1-rc.2', '大版本不匹配'],
    ['>=0.1.1-rc.1 <1.0.0-0', '1.0.0', 'stable 1.0.0 超上界'],
    ['^0.1.1-rc.1', '0.2.0', 'caret 上界外'],
    ['>=0.1.1-rc.1 <1.0.0-0', 'not-a-version', '版本不可解析'],
    ['~0.1.1', '0.1.1', '不支持的形态必须明确报 unsupported'],
    ['>=0.1.1-rc.1 || >=2.0.0', '0.1.1', '不支持的形态']
  ]) cases.push({ group: 'peer-range', input: `${range} @ ${ver}（${why}）`, code: peerSatisfies(range, ver).ok ? null : 'PEER_RANGE_UNSATISFIED' });

  // 跨设备层：回读校验门（"非 200 不能假定成功"）
  const shaA = sha256Hex('A'), shaB = sha256Hex('B');
  for (const [label, r] of [
    ['PUT 非 200（201）', { putStatus: 201, expectedSha256: shaA, readbackStatus: 200, readbackSha256: shaA }],
    ['PUT 非 200（500）', { putStatus: 500, expectedSha256: shaA, readbackStatus: 200, readbackSha256: shaA }],
    ['回读 404', { putStatus: 200, expectedSha256: shaA, readbackStatus: 404, readbackSha256: null }],
    ['sha256 不一致', { putStatus: 200, expectedSha256: shaA, readbackStatus: 200, readbackSha256: shaB }],
    ['缺 sha256', { putStatus: 200, expectedSha256: null, readbackStatus: 200, readbackSha256: null }],
    ['回读回来了另一个 key', { putStatus: 200, expectedSha256: shaA, readbackStatus: 200, readbackSha256: shaA, expectedKey: 'data/reflect/events/mac-mini/2026-09-10', readbackKey: 'data/reflect/events/mbp/2026-09-10' }]
  ]) cases.push({ group: 'readback', input: label, code: verifyReadback(r).ok ? null : 'READBACK_FAILED' });
  return cases;
}

/** 凭据形态扫描的实测用例：必须脱敏的（redact）与**必须保留**的（keep）。 */
export function secretRedactCases() {
  return [
    ['grouped-triplet', 'deploy key a1b2-c3d4-e5f6 rotated'],
    ['provider-id-FL', 'supplier id FL-AB12-345678 assigned'],
    ['assignment-token', 'token=a1B2c3D4e5F6g7H8'],
    ['assignment-api_key', 'api_key: "Xk29fJ3nQ8zL5mP0"'],
    ['assignment-secret', 'secret=9f8e7d6c5b4a3210'],
    ['assignment-key-eq', 'key=Zq7Wm2Np5Rr8Tt1Y'],
    ['bearer', 'Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload123456'],
    ['pem', '-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----'],
    ['known-prefix-sk', 'sk-abc123DEF456ghi789JKL012mno345'],
    ['known-prefix-ghp', 'ghp_AbCdEf0123456789AbCdEf0123456789Ab'],
    ['known-prefix-app', 'app-Ab3Cd4Ef5Gh6Ij7Kl8Mn9Op']
  ].map(([label, input]) => {
    const r = redactSecrets(input);
    return { label, must: 'redact', got: r.count > 0 ? 'redact' : 'keep', count: r.count, ok: r.count > 0, masked: input.replace(/[A-Za-z0-9]{4}/g, '****') };
  });
}

/**
 * **必须保留**的合法形态 —— 全部取自真实事件流的实测样本（2026-09-10 的 1747 条事件）。
 * 这组用例是"门太宽会砍掉自己人"（R006 §6 坑 1）的回归测试：
 * 初版通用 40+ base64 与朴素 4-4-4 规则把下面这些**全**误判成凭据，会毁掉整个事件流。
 */
export function secretKeepCases() {
  return [
    ['filename-triplet-letters', 'dsh-collab/docs/flowernet-tech-path-moat-revision-v1.md'],
    ['uuid-session-dir', 'dsh-collab/notes/664ce0d2-2ef1-4a68-b1d4-b86209009911/iteration-report.md'],
    ['svg-filename-app-prefix', 'data/blueprint/gallery/static-export/snapshots/laodeng-app-arch-v1_0-20260903-100236.svg'],
    ['blackboard-key-notes', 'notes/mac-mini/cloudbase-plan-push-task'],
    ['json-key-field', '{"key":"notes/mac-mini/cloudbase-plan-push-done","ns":"/notes/"}'],
    ['sha256-evidence', 'readback sha256 4f8c1d0a9be7f3c25d6b8a1e0c4f7a2b3d5e6f8091a2b3c4d5e6f708192a3b4c'],
    ['upload-key-itself', 'data/reflect/events/mac-mini/2026-09-10'],
    ['company-name', 'dsh-collab/data/industry/external/partner/FLOWERNET-CAPITAL-PLAN-v2.md'],
    ['plain-sentence', '当日 1747 条事件，其中 files=796 · board=820 · tools=108'],
    ['timestamps', 'window 2026-09-10T00:00:00 → 2026-09-10T23:59:59']
  ].map(([label, input]) => {
    const r = redactSecrets(input);
    return { label, must: 'keep', got: r.count === 0 ? 'keep' : 'redact', count: r.count, ok: r.count === 0, byPattern: r.byPattern };
  });
}

/** 正例矩阵：合法输入必须全部通过（防"门太宽把功能也砍了"）。 */
export function gatePositiveCases() {
  const out = [];
  const ok = (group, label, fn) => { try { const r = fn(); out.push({ group, label, ok: true, got: typeof r === 'string' ? r : (r && r.iso) || 'ok' }); } catch (e) { out.push({ group, label, ok: false, err: e.message }); } };
  for (const rule of WRITE_TARGETS) {
    ok('write-target', rule.path, () => assertWriteAllowed(rule.path).path);
  }
  ok('write-target', '产出文件', () => assertWriteAllowed(path.join(OUT_DIR, 'events-20260910.json')).path);
  ok('http-method', 'GET', () => assertHttpGet('GET'));
  ok('board-url', '127.0.0.1:8792', () => assertBoardUrl('http://127.0.0.1:8792').hostname);
  ok('board-url', 'localhost:8792', () => assertBoardUrl('http://localhost:8792').hostname);
  for (const p of ALLOWED_BOARD_PATHS) ok('board-path', p, () => assertBoardPath(p));
  for (const t of ['2026-09-10', '2026-09-10T00:00:00', '2026-09-10 23:59:59']) ok('time-spec', t, () => assertTimeSpec(t).iso);
  for (const p of [COLLAB_ROOT, REL_APP_ROOT, path.join(COLLAB_ROOT, 'scripts'), path.join(COLLAB_ROOT, 'logs', 'x.log')]) ok('collect-path', p, () => assertCollectPath(p));
  ok('git-args', 'rev-parse', () => assertGitArgs(['rev-parse', '--is-inside-work-tree']).join(' '));
  ok('git-args', 'log --since', () => assertGitArgs(['log', '--since=2026-09-10T00:00:00', '--until=2026-09-10T23:59:59', '--date=iso', '--pretty=%H|%ad|%s', '--no-merges']).join(' '));
  for (const s of [SOURCE_KEYS.join(','), 'files,logs']) ok('sources', `sources=${s}`, () => assertSources(s).join(','));
  ok('upload-target', 'PUT 中央 reflect', () => buildUploadUrl('mac-mini', '2026-09-10'));
  ok('upload-target', 'assertBoardUpload', () => assertBoardUpload('PUT', buildUploadUrl('mac-mini', '2026-09-10')).hostname);
  ok('read-target', '中央 reflect 前缀', () => assertReadTarget(`${CENTRAL_ORIGIN}/data/reflect/events/mac-mini/2026-09-10`).pathname);
  ok('read-target', '本地 /data/', () => assertReadTarget('http://127.0.0.1:8792/data/').pathname);
  for (const d of ['mac-mini', 'mbp', 'i9', 'coreydemac-mini', 'a', 'a1-b2']) ok('device', d, () => assertDevice(d));
  ok('device', 'defaultDevice(本机)', () => defaultDevice('CoreydeMac-mini.local').device);
  ok('event-stamp', '三字段齐备', () => JSON.stringify(assertEventStamped({ ts: '2026-09-10T10:00:00', collected_at: '2026-09-10T10:05:00', origin_device: 'mac-mini' })));
  for (const k of ['data/reflect/events/mac-mini/2026-09-10', 'data/registry/dsh-plugin-reflect-collect', 'notes/mac-mini/cloudbase-plan-task', 'data/reflect/a.b-c_d']) {
    ok('board-key', k, () => assertBoardKeySyntax(k));
  }
  ok('peer-range', 'cordis 4.0.2', () => peerSatisfies('>=4.0.0 <5.0.0', '4.0.2').reason);
  ok('peer-range', 'dsh-tools 0.1.1-rc.2（本包实际声明）', () => peerSatisfies('>=0.1.1-rc.1 <1.0.0-0', '0.1.1-rc.2').reason);
  ok('peer-range', '同 tuple 预发布', () => peerSatisfies('^0.1.1-rc.1', '0.1.1-rc.5').reason);
  ok('readback', 'PUT200+回读200+规范化内容一致+key 一致', () => verifyReadback({ putStatus: 200, expectedSha256: canonicalSha256({ a: 1 }), readbackStatus: 200, readbackSha256: canonicalSha256({ a: 1 }), expectedKey: 'k', readbackKey: 'k' }).reason);
  ok('canonical', '键序无关', () => canonicalJson({ b: 1, a: [2, { d: 4, c: 3 }] }));
  return out;
}

/** 自采样排除的正/负例（证明"自己的产物不会被自己采回来"）。 */
export function selfSamplingCases() {
  return [
    { path: LOG_FILE, expect: 'rejected', got: isCollectable(LOG_FILE) ? 'accepted' : 'rejected' },
    { path: path.join(OUT_DIR, 'events-20260910.json'), expect: 'rejected', got: isCollectable(path.join(OUT_DIR, 'events-20260910.json')) ? 'accepted' : 'rejected' },
    { path: path.join(COLLAB_ROOT, 'logs', 'cld-voice.launchd.log'), expect: 'accepted', got: isCollectable(path.join(COLLAB_ROOT, 'logs', 'cld-voice.launchd.log')) ? 'accepted' : 'rejected' },
    { path: path.join(COLLAB_ROOT, 'scripts', 'bb-write.py'), expect: 'accepted', got: isCollectable(path.join(COLLAB_ROOT, 'scripts', 'bb-write.py')) ? 'accepted' : 'rejected' }
  ];
}

export const GATE_META = Object.freeze({
  principle: '只读采集 + 唯一受控上传：采集动作绝不可写出/改动被采集对象，跨设备上传只有一个冻结 key 形态',
  writeTargets: WRITE_TARGETS.map((r) => `${r.kind}:${r.path}`),
  forbiddenPaths: Object.freeze([
    '写入白名单外的任何本地路径',
    '采集根之外的任何路径（含 .. 穿越/软链逃逸）',
    '本地黑板任何写入（本地永远只读；只有中央的 reflect 前缀可写）',
    '上传到 data/reflect/events/<device>/<date> 之外的任何中央 key',
    '上传未脱敏凭据（默认脱敏，--allow-secrets 才原样）',
    '只信 HTTP 200 不回读（必须回读 + sha256 一致）',
    '事件缺 ts/collected_at/origin_device（跨设备时点必须可分辨）',
    '执行 git 以外命令/带 shell/参数注入',
    '静默跳过失败源（失败/超限/跳过都进 errors[]）'
  ]),
  collectRoots: COLLECT_ROOTS,
  sources: SOURCE_KEYS,
  httpMethods: ALLOWED_HTTP_METHODS,
  commands: ALLOWED_COMMANDS,
  writerModules: WRITER_MODULES,
  readonlyModules: READONLY_MODULES,
  networkModules: NETWORK_MODULES,
  uploaderModules: UPLOADER_MODULES,
  centralOrigin: CENTRAL_ORIGIN,
  uploadKeyPrefix: UPLOAD_KEY_PREFIX,
  secretPatterns: SECRET_PATTERNS.map((p) => p.name)
});
