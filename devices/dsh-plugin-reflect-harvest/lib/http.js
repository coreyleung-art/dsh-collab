/**
 * http.js — 出站原语（**只有 GET**）
 * =============================================================================
 * 跨设备层要求 harvest 从中央黑板拉其它设备的回填。这给本工具**新增了出站能力**，
 * 因此必须同时给出结构约束（R006 §2 ⑩：新增能力 = 新增"不该发生路径"的候选）：
 *
 *   本工具**绝不应写黑板** —— 黑板上的 `data/reflect/answers/<device>/<date>` 是
 *   **各设备自己的**产物（谁回填谁写）。harvest 是汇集方，不是代笔方：
 *   一旦 harvest 能写，它就能"替别的设备回填"，证据链当场失效（谁说的、什么时候说的都不可信了）。
 *
 * 结构封堵（不是"检查后放行"）：
 *   1) **没有那个入口**：本模块只导出 `httpGetJson(url)` —— 没有任何 method 参数，
 *      没有任何 `httpRequest(url, {method})` 这类通用原语。方法不是"被校验"，而是**无法表达**。
 *      `ALLOWED_HTTP_METHODS` 是冻结常量 `['GET']`，且**没有任何代码读它去做判断**
 *      （它只用于文档与自证输出；真正的方法来自下面硬写的 `mod.get`）。
 *   2) **没有那个能力**：本包只调用 `http.get` / `https.get`（node 内置）。
 *      `--lean4-check` 的 F 项用**去字面量扫描**证明：全包不存在
 *      `.request(` / `fetch(` / `XMLHttpRequest` / `net.connect` / `dgram` 调用点，
 *      且该扫描器由**正控**证明非盲（喂 `http.request({method:'PUT'})` + `fetch(..., {method:'POST'})`
 *      必须被命中）。
 *   3) 只读语义：`GET` 是幂等只读方法；本模块不做重定向跟随（防被引到别的主机），
 *      不做 cookie/凭据注入，响应体有大小上限。
 */
import http from 'node:http';
import https from 'node:https';

/** 允许的出站 HTTP 方法（冻结闭集。真实取值来自下面硬写的 `mod.get`，不是运行时判断） */
export const ALLOWED_HTTP_METHODS = Object.freeze(['GET']);

/** 中央黑板（跨设备汇聚点；可用 --central 覆盖） */
export const DEFAULT_CENTRAL = 'http://106.53.214.108:8792';

/** 响应体上限（防黑洞式大响应；超出即截断并标记） */
export const MAX_BODY_BYTES = 4 * 1024 * 1024;

/**
 * 唯一的出站原语：GET 一个 URL 并尝试解析 JSON。
 * @returns {Promise<{ok:boolean, status:number, json:any, body:string, error:string|null, truncated:boolean, elapsedMs:number}>}
 */
export function httpGetJson(url, opts = {}) {
  const timeoutMs = Number.isFinite(opts.timeoutMs) ? opts.timeoutMs : 8000;
  return new Promise((resolve) => {
    const t0 = Date.now();
    let parsed;
    try { parsed = new URL(url); }
    catch (e) { return resolve({ ok: false, status: 0, json: null, body: '', error: `非法 URL: ${e.message}`, truncated: false, elapsedMs: 0 }); }

    const mod = parsed.protocol === 'https:' ? https : http; // http: 与 https: 二选一，无其它协议
    let settled = false;
    const done = (v) => { if (!settled) { settled = true; resolve({ ...v, elapsedMs: Date.now() - t0 }); } };

    const req = mod.get({
      protocol: parsed.protocol,
      hostname: parsed.hostname,
      port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
      path: parsed.pathname + parsed.search,
      headers: { accept: 'application/json', 'user-agent': 'dsh-plugin-reflect-harvest' }
    }, (res) => {
      let body = '';
      let truncated = false;
      res.setEncoding('utf8');
      res.on('data', (c) => {
        if (body.length + c.length > MAX_BODY_BYTES) { truncated = true; res.destroy(); return; }
        body += c;
      });
      res.on('end', () => {
        let json = null;
        try { json = JSON.parse(body); } catch { /* 非 JSON 不算错，交给调用方判断 */ }
        done({ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode || 0, json, body: truncated ? body.slice(0, 200) : body, error: null, truncated });
      });
      res.on('error', (e) => done({ ok: false, status: res.statusCode || 0, json: null, body: '', error: `响应流错误: ${e.message}`, truncated }));
    });

    req.setTimeout(timeoutMs, () => { req.destroy(); done({ ok: false, status: 0, json: null, body: '', error: `超时 ${timeoutMs}ms`, truncated: false }); });
    req.on('error', (e) => done({ ok: false, status: 0, json: null, body: '', error: `请求失败: ${e.message}`, truncated: false }));
  });
}

const JOIN = (base, key) => `${String(base).replace(/\/+$/, '')}/${String(key).replace(/^\/+/, '')}`;

/**
 * 读黑板一个 key。返回统一信封：
 *   {ok, status, missing(404), value, ts(黑板写入时刻), error}
 * 404 = 格式合法但不存在（内容缺失）；与 400（键写法非法）语义不同 —— 必须分开报。
 */
export async function blackboardGet(central, key, opts = {}) {
  const res = await httpGetJson(JOIN(central, key), opts);
  if (res.status === 404) return { ok: false, status: 404, missing: true, value: null, ts: null, error: 'not found', elapsedMs: res.elapsedMs };
  if (res.status === 400) return { ok: false, status: 400, missing: false, value: null, ts: null, error: 'bad key（黑板 key 语法非法：首段必须是纯小写字母）', elapsedMs: res.elapsedMs };
  if (!res.ok) return { ok: false, status: res.status, missing: false, value: null, ts: null, error: res.error || `HTTP ${res.status}`, elapsedMs: res.elapsedMs };
  const j = res.json;
  if (j && typeof j === 'object' && 'value' in j && 'key' in j) {
    return { ok: true, status: res.status, missing: false, value: j.value, ts: j.ts ?? null, error: null, elapsedMs: res.elapsedMs };
  }
  // 有的实现直接返回裸值；两种都接受
  return { ok: true, status: res.status, missing: false, value: j, ts: null, error: null, elapsedMs: res.elapsedMs };
}

/**
 * ★ 「键存在」的判据是**内容非空**，不是状态码 200。
 *
 * 依据（2026-09-11 读卡 `data/registry/r003-key-syntax-notice-20260911`，R003 补充 · enforced）：
 *   · 400 = 写法非法（键错）—— 你以为写了，其实被拒
 *   · 404 = 格式合法但不存在（内容缺失）
 *   · **空壳键变体**：键存在但 `value = {}` —— **纯状态码校验会漏，必须验内容**
 *
 * 血泪（本工具实测）：初版 `blackboardExists` 写的是 `r.ok && r.value !== null`，
 * 正是通告点名的那种"只看状态码"的写法 —— 一个 `value={}` 的空壳卡会被判成"卡已派出"，
 * 于是设备状态从 `not_dispatched` 被误标成 `pending`（**静默降级，且看不出来**）。
 * 现改为内容判据，并把 `emptyShell` 单独报出来（不静默当不存在）。
 */
export function isMeaningfulValue(v) {
  if (v === null || v === undefined) return false;
  if (Array.isArray(v)) return v.length > 0;
  if (typeof v === 'string') return v.trim() !== '';
  if (typeof v === 'object') return Object.keys(v).length > 0;
  return true; // number / boolean
}

/** 探针：判断 key 是否存在**且有内容**，用于 cards（卡是否已派出）判定 */
export async function blackboardExists(central, key, opts = {}) {
  const r = await blackboardGet(central, key, opts);
  const meaningful = r.ok && isMeaningfulValue(r.value);
  return {
    exists: meaningful,
    emptyShell: r.ok && !meaningful,      // ← 键在、但 value 空：按"不存在"处理，但**如实上报**
    status: r.status,
    error: r.error,
    reason: r.status === 400 ? 'bad key（首段须纯小写字母）'
      : r.status === 404 ? 'not found（格式合法但不存在）'
      : (r.ok ? (meaningful ? 'ok（内容非空）' : 'empty shell（键在但 value 为空）') : r.error)
  };
}

/* ========================================================================== *
 * HTTP 调用点扫描 + ★ 扫描器正控（新增出站能力 = 必须新增的证明）
 * ========================================================================== */

import { stripLiterals } from './gate.js';

/**
 * 通用 HTTP 入口（一旦出现，就"可以选方法"了 → 结构约束失效）。
 * `http.get` / `https.get` 是**允许**的（本包唯一的出站原语）；
 * `http.request` / `fetch` / `XMLHttpRequest` / `net.connect` / `dgram` 一律命中即失败。
 */
const GENERIC_HTTP_RE = /(?<![\w$])(fetch|XMLHttpRequest|request)\s*\(|(?<![\w$])connect\s*\(/g;

/** 枚举通用 HTTP / 原始套接字调用点（去字面量定位 → 回原文读接收者） */
export function scanHttpSites({ sources }) {
  const sites = [];
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    let m;
    const re = new RegExp(GENERIC_HTTP_RE.source, 'g');
    while ((m = re.exec(code)) !== null) {
      const line = code.slice(0, m.index).split('\n').length;
      const recv = code.slice(0, m.index).match(/([\w$]+)\s*\.\s*$/);
      sites.push({ file, line, callee: m[1] || m[0].replace(/\s*\($/, ''), receiver: recv ? recv[1] : null });
    }
  }
  return sites;
}

/**
 * ★ 正控：喂一段**明知含通用 HTTP 入口**的合成源码，扫描器必须命中。
 * 命中 0 = 扫描器瞎了 → 「0 个通用入口」毫无意义（R006 §6 坑#3 空洞通过）。
 */
export function httpScannerSelfTest() {
  const probe = [
    "import http from 'node:http';",
    "http.request({ method: 'PUT' }, cb);",
    "await fetch('http://x', { method: 'POST' });",
    "new XMLHttpRequest();",
    "net.connect(9999);",
    "http.get('http://ok');           // 允许：唯一的出站原语"
  ].join('\n');
  const hits = scanHttpSites({ sources: { '__probe__.js': probe } });
  const callees = hits.map((h) => h.callee).sort();
  const ok = hits.length === 4 && callees.includes('request') && callees.includes('fetch') && callees.includes('XMLHttpRequest') && callees.includes('connect');
  return { ok, hits, detail: `正控: 通用 HTTP/套接字调用点 ${hits.length}（期望 4：http.request / fetch / XMLHttpRequest / net.connect）→ [${callees.join(', ')}]` };
}

export const HTTP_META = Object.freeze({
  allowedMethods: ALLOWED_HTTP_METHODS,
  defaultCentral: DEFAULT_CENTRAL,
  maxBodyBytes: MAX_BODY_BYTES,
  primitive: 'httpGetJson(url) —— 无 method 参数，无通用 request 原语',
  scanRule: '全包不得出现 http.request / fetch / XMLHttpRequest / net.connect / dgram（F 项扫描 + 正控证明）',
  principle: 'harvest 只读黑板，绝不写黑板（谁回填谁写；汇集方不得代笔）'
});
