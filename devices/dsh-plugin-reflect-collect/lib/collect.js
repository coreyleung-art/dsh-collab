/**
 * collect.js — 只读采集内核（R006 ⑩「没有那个能力」的载体）
 * =============================================================================
 * ★ 本文件**不含任何写入或删除原语**（writeFileSync / mkdirSync / rmSync /
 *   unlinkSync / renameSync / createWriteStream / openSync … 一个都没有；
 *   `--lean4-check` 的 A 项扫描直接证明这一点）。
 *   它只能读：readdirSync / statSync / readFileSync / readFileSync(fd) 与只读的 git。
 *
 * 五个采集源（各自独立开关，见 SOURCE_KEYS）：
 *   files  当日新增/修改的文件（~/dsh-collab、~/relationship-graph-app，按 mtime 过滤）
 *   board  当日写过的黑板卡（GET /data/ 与 /notes/，按卡上 ts 过滤；**本机黑板只读**）
 *   tools  当日新建/修改的工具（~/dsh-collab/scripts 下的 .py 与 devices/dsh-plugin-* 目录）
 *   logs   当日错误/失败痕迹（~/dsh-collab/logs/*.log 中含 error/fail/拒绝/deny 的行）
 *   git    当日提交（~/dsh-collab 是 git 仓库则读 git log --since；不是则跳过并留痕）
 *
 * 事件时点（跨设备层，design v1.1 §10.5 Φ13）：每条事件必带
 *   ts（**对象自身**的时刻，设备本地）/ collected_at（**本次采集**时刻）/ origin_device（**采集者**）。
 *   三者由唯一的 `stampEvents()` 打上，并由 `assertEventStamped()` 逐条门检——
 *   同步盘会让同一文件在两台设备都可见，所以"文件在哪"和"谁采的"必须分开。
 *
 * 失败不静默：任一源抛错/超限/跳过，都写进返回值的 errors[]（R006 §2 ⑩ 第 4 条精神 +
 * 「采集失败也要留痕」）。
 */

import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import {
  COLLAB_ROOT, REL_APP_ROOT, COLLECT_ROOTS, EXCLUDE_DIR_NAMES, EXCLUDE_BASENAMES,
  LOG_FILE, OUT_DIR, SELFCHECK_DIR, SOURCE_KEYS, BOARD_PAGE_SIZE, BOARD_MAX_KEYS,
  assertBoardUrl, assertGitArgs, assertSources, assertEventStamped, assertTimeSpec,
  collectPathStatus, fmtLocal, fmtLocalWithOffset, isCollectable, defaultDevice,
  assertDevice as assertDeviceName, hostShortName as hostShort,
  GateError as GateErrorLocal,
  buildGitProbeArgs, buildGitLogArgs
} from './gate.js';
import { httpGetJson, networkStats } from './transport.js';

const ERROR_RE = /error|fail|拒绝|deny/i;
const MAX_DEPTH = 16;
const MAX_FILES_PER_ROOT = 300000;
const MAX_LOG_BYTES = 1024 * 1024;      // 单个日志文件最多读尾部 1MB
const MAX_LOG_MATCH_PER_FILE = 50;      // 单个日志文件最多产出 50 条事件
const DEFAULT_GIT_CAP = 500;
const LINE_DESC_MAX = 240;

/* 网络计数由 transport.js 统一维护（唯一 HTTP 模块），此处只做再导出便于调用方使用。 */
export { networkStats };

/* ───────────────────────────── 工具函数（纯读） ───────────────────────────── */

function parseTs(v) {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  if (!s) return null;
  if (/[zZ]$|[+-]\d{2}:\d{2}$/.test(s)) {
    const t = Date.parse(s);
    return Number.isFinite(t) ? t : null;
  }
  try { return assertTimeSpec(s.slice(0, 19).replace(' ', 'T'), 'card.ts').ms; } catch { /* 落到下面 */ }
  const t = Date.parse(s);
  return Number.isFinite(t) ? t : null;
}

function isoOf(ms) { return fmtLocalWithOffset(new Date(ms)); }   // 事件 ts：设备本地时间 + 显式偏移（跨设备可比）

function rel(p) {
  for (const r of COLLECT_ROOTS) if (p === r || p.startsWith(r + path.sep)) return path.relative(path.dirname(r), p);
  return p;
}

function clip(s, n = LINE_DESC_MAX) {
  const t = String(s).replace(/\s+/g, ' ').trim();
  return t.length > n ? t.slice(0, n) + '…' : t;
}

/**
 * 目录遍历（只读）。不跟随软链（防环、防逃逸）；跳过冻结的排除目录名。
 * 返回 {files, truncated, errors}
 */
function walkFiles(root, { maxFiles = MAX_FILES_PER_ROOT, maxDepth = MAX_DEPTH, filter = null } = {}) {
  const files = [];
  const errors = [];
  let truncated = false;
  const stack = [[root, 0]];
  while (stack.length) {
    const [dir, depth] = stack.pop();
    let ents;
    try { ents = fs.readdirSync(dir, { withFileTypes: true }); }
    catch (e) { errors.push({ dir, message: String(e.message || e) }); continue; }
    for (const ent of ents) {
      const full = path.join(dir, ent.name);
      if (ent.isSymbolicLink()) continue;               // 不跟随软链
      if (ent.isDirectory()) {
        if (EXCLUDE_DIR_NAMES.includes(ent.name)) continue;
        if (depth < maxDepth) stack.push([full, depth + 1]);
        continue;
      }
      if (!ent.isFile()) continue;
      if (EXCLUDE_BASENAMES.includes(ent.name)) continue;
      if (filter && !filter(full, ent)) continue;
      files.push(full);
      if (files.length >= maxFiles) { truncated = true; return { files, truncated, errors }; }
    }
  }
  return { files, truncated, errors };
}

function statSafe(p) { try { return fs.statSync(p); } catch { return null; } }

/**
 * 只读读文件尾部（用 createReadStream + start/end，**不引入任何写入/打开写句柄的能力**）。
 * 明确不使用 openSync/readSync：openSync 的 flag 可以让调用方拿到写句柄，
 * 为避免"能拿到写句柄"的能力存在，本工具只保留 createReadStream（只读流）。
 */
function readTail(p, start, len) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    const rs = fs.createReadStream(p, { start, end: start + len - 1 });
    rs.on('data', (c) => chunks.push(c));
    rs.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    rs.on('error', (e) => reject(e));
  });
}

/* HTTP 只经 lib/transport.js（全包唯一 HTTP 模块）：
   · 读 → httpGetJson（门：GET + 环回 /data/ /notes/，或中央 /data/reflect/ 前缀）
   · 写 → httpPutJson（门：PUT + 中央 + data/reflect/events/<device>/<date>，见 lib/upload.js）
   本文件**不出现** http.request，也不出现任何 PUT —— 采集动作写不了被采集对象。 */

/* ───────────────────────────────── 各采集源 ───────────────────────────────── */

/** files：当日新增/修改的文件 */
function collectFiles(ctx) {
  const events = [], errors = [];
  for (const root of COLLECT_ROOTS) {
    if (!fs.existsSync(root)) { errors.push({ source: 'files', kind: 'collect-failed', message: `采集根不存在: ${root}` }); continue; }
    const { files, truncated, errors: walkErr } = walkFiles(root);
    for (const e of walkErr) errors.push({ source: 'files', kind: 'collect-failed', message: `无法读取目录 ${e.dir}: ${e.message}` });
    if (truncated) errors.push({ source: 'files', kind: 'limit', message: `${root} 文件数超过 ${MAX_FILES_PER_ROOT} 上限，结果已截断（提高上限需改 gate 常量）` });
    for (const f of files) {
      const st = statSafe(f);
      if (!st) { errors.push({ source: 'files', kind: 'collect-failed', message: `stat 失败: ${f}` }); continue; }
      if (st.mtimeMs < ctx.since.ms || st.mtimeMs > ctx.until.ms) continue;
      const status = collectPathStatus(f);
      if (!status.ok) continue; // 自产物/排除目录：静默跳过属于设计（不记 errors），见 README「自采样排除」
      const created = st.birthtimeMs >= ctx.since.ms && st.birthtimeMs <= ctx.until.ms;
      events.push({
        source: 'files', ts: isoOf(st.mtimeMs), kind: created ? 'created' : 'modified',
        path: rel(f), desc: `${rel(f)} (${st.size}B)`, mtimeMs: Math.round(st.mtimeMs)
      });
    }
  }
  return { events, errors };
}

/**
 * 有界分页枚举一个命名空间（R003 v3 统一操作建议）。
 * 服务端不做前缀/时间过滤，所以"取当日全部卡"只能枚举全部键；但**不必**用一次 36MB 响应：
 * 每页 `limit=BOARD_PAGE_SIZE`，用 `offset` 递进，用响应里的 `total` 判定是否取完/被截断。
 * 任何截断都写进 `errors[]`（不静默丢卡）。
 */
async function fetchNamespacePaged(nsPath, ctx) {
  const cards = [];
  let offset = 0, total = null, pages = 0, truncated = false;
  const maxPages = Math.ceil(BOARD_MAX_KEYS / BOARD_PAGE_SIZE) + 2;
  for (let i = 0; i < maxPages; i += 1) {
    const u = new URL(nsPath, ctx.boardUrl);
    u.searchParams.set('limit', String(BOARD_PAGE_SIZE));
    u.searchParams.set('offset', String(offset));
    const { json } = await httpGetJson(u.href, { timeoutMs: 25000 });
    pages += 1;
    if (total === null && Number.isFinite(json && json.total)) total = json.total;
    const list = (json && json.list) || {};
    const keys = Object.keys(list);
    for (const k of keys) cards.push([k, list[k]]);
    offset += keys.length;
    if (!keys.length) break;
    if (total !== null ? offset >= total : keys.length < BOARD_PAGE_SIZE) break;
    if (offset >= BOARD_MAX_KEYS) { truncated = true; break; }
  }
  if (total !== null && offset < total) truncated = true;
  return { cards, total, pages, truncated };
}

/** board：当日写过的黑板卡（只 GET；有界分页枚举，见 fetchNamespacePaged） */
async function collectBoard(ctx) {
  const events = [], errors = [];
  for (const ns of ['/data/', '/notes/']) {
    let fetched;
    try { fetched = await fetchNamespacePaged(ns, ctx); }
    catch (e) { errors.push({ source: 'board', kind: 'collect-failed', message: `GET ${ns} 失败: ${String(e.message || e)}` }); continue; }
    const list = Object.fromEntries(fetched.cards);
    const keys = Object.keys(list);
    if (fetched.truncated) {
      errors.push({
        source: 'board', kind: 'limit',
        message: `${ns} 枚举被截断：服务端 total=${fetched.total ?? '?'}，已取 ${keys.length} 键 / ${fetched.pages} 页（页大小 ${BOARD_PAGE_SIZE}，上限 ${BOARD_MAX_KEYS}）—— 当日卡片可能不全，请提高 BOARD_MAX_KEYS 或改用精确 key 读取`
      });
    }
    if (!keys.length) { errors.push({ source: 'board', kind: 'collect-failed', message: `GET ${ns} 返回 0 条（疑似黑板上游异常，非"当日无卡"）` }); continue; }
    for (const key of keys) {
      const card = list[key] || {};
      const ts = parseTs(card.ts);
      if (ts === null) { errors.push({ source: 'board', kind: 'skipped', message: `卡片 ${key} 的 ts='${card.ts}' 无法解析，已跳过` }); continue; }
      if (ts < ctx.since.ms || ts > ctx.until.ms) continue;
      const v = card.value;
      const raw = typeof v === 'string' ? v : (v && (v.status || v.value || v.summary || v.action || v.direction || v.ack));
      const hint = raw === undefined || raw === null ? ''
        : (typeof raw === 'string' ? raw : (() => { try { return JSON.stringify(raw); } catch { return String(raw); } })());
      events.push({
        source: 'board', ts: isoOf(ts), kind: 'card-written', key, ns,
        desc: `${key} · ${clip(hint, 120)}`, version: card.version ?? null
      });
    }
  }
  return { events, errors };
}

/** tools：当日新建/修改的工具 */
function collectTools(ctx) {
  const events = [], errors = [];
  const hit = (f, label) => {
    const st = statSafe(f);
    if (!st) { errors.push({ source: 'tools', kind: 'collect-failed', message: `stat 失败: ${f}` }); return; }
    if (st.mtimeMs < ctx.since.ms || st.mtimeMs > ctx.until.ms) return;
    if (!isCollectable(f)) return;
    const created = st.birthtimeMs >= ctx.since.ms && st.birthtimeMs <= ctx.until.ms;
    events.push({
      source: 'tools', ts: isoOf(st.mtimeMs), kind: created ? 'created' : 'modified',
      tool: label, path: rel(f), desc: `${label} → ${rel(f)} (${st.size}B)`
    });
  };

  // (1) ~/dsh-collab/scripts/*.py
  const scriptsDir = path.join(COLLAB_ROOT, 'scripts');
  try {
    for (const ent of fs.readdirSync(scriptsDir, { withFileTypes: true })) {
      if (ent.isFile() && ent.name.endsWith('.py')) hit(path.join(scriptsDir, ent.name), 'script');
    }
  } catch (e) { errors.push({ source: 'tools', kind: 'collect-failed', message: `读取 ${scriptsDir} 失败: ${e.message}` }); }

  // (2) ~/dsh-collab/devices/dsh-plugin-*/（递归）
  const devicesDir = path.join(COLLAB_ROOT, 'devices');
  try {
    for (const ent of fs.readdirSync(devicesDir, { withFileTypes: true })) {
      if (!ent.isDirectory() || !ent.name.startsWith('dsh-plugin-')) continue;
      const dir = path.join(devicesDir, ent.name);
      const { files, truncated, errors: walkErr } = walkFiles(dir);
      for (const e of walkErr) errors.push({ source: 'tools', kind: 'collect-failed', message: `无法读取目录 ${e.dir}: ${e.message}` });
      if (truncated) errors.push({ source: 'tools', kind: 'limit', message: `${dir} 文件数超上限，已截断` });
      for (const f of files) hit(f, ent.name);
    }
  } catch (e) { errors.push({ source: 'tools', kind: 'collect-failed', message: `读取 ${devicesDir} 失败: ${e.message}` }); }

  return { events, errors };
}

/** logs：当日错误/失败痕迹 */
async function collectLogs(ctx) {
  const events = [], errors = [];
  const logsDir = path.join(COLLAB_ROOT, 'logs');
  let ents;
  try { ents = fs.readdirSync(logsDir, { withFileTypes: true }); }
  catch (e) { return { events, errors: [{ source: 'logs', kind: 'collect-failed', message: `读取 ${logsDir} 失败: ${e.message}` }] }; }

  for (const ent of ents) {
    if (!ent.isFile() || !ent.name.endsWith('.log')) continue;
    const full = path.join(logsDir, ent.name);
    if (!isCollectable(full)) continue;            // 自采样排除：本工具自己的统一日志不采自己
    const st = statSafe(full);
    if (!st) { errors.push({ source: 'logs', kind: 'collect-failed', message: `stat 失败: ${full}` }); continue; }
    if (st.mtimeMs < ctx.since.ms) continue;       // 窗口前就没再写过 → 当日无痕迹
    let text;
    try {
      const start = Math.max(0, st.size - MAX_LOG_BYTES);
      const len = st.size - start;
      text = len > 0 ? await readTail(full, start, len) : '';   // 只读流，无写句柄能力
      if (st.size > MAX_LOG_BYTES) {
        errors.push({ source: 'logs', kind: 'limit', message: `${ent.name} ${st.size}B > ${MAX_LOG_BYTES}B，只读尾部；更早行未参与判定` });
      }
    } catch (e) { errors.push({ source: 'logs', kind: 'collect-failed', message: `读取 ${full} 失败: ${e.message}` }); continue; }

    let matchedAll = 0, inWindow = 0, emitted = 0;
    const lines = text.split('\n');
    for (const line of lines) {
      if (!ERROR_RE.test(line)) continue;
      matchedAll += 1;
      const m = line.match(/(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)/);
      let ts = m ? parseTs(m[1]) : null;
      if (ts === null) ts = Math.round(st.mtimeMs);
      if (ts < ctx.since.ms || ts > ctx.until.ms) continue;
      inWindow += 1;
      if (emitted >= MAX_LOG_MATCH_PER_FILE) continue;      // 只截断"超上限"的部分
      emitted += 1;
      events.push({ source: 'logs', ts: isoOf(ts), kind: 'error-line', path: rel(full), file: ent.name, desc: clip(line) });
    }
    if (inWindow > emitted) {
      errors.push({ source: 'logs', kind: 'limit', message: `${ent.name} 窗口内命中 ${inWindow} 行、产出 ${emitted} 条（单文件上限 ${MAX_LOG_MATCH_PER_FILE}；该文件全文含关键词 ${matchedAll} 行）` });
    }
  }
  return { events, errors };
}

/** git：当日提交（只读，无 shell，参数白名单） */
function collectGit(ctx) {
  const events = [], errors = [];
  const cwd = COLLAB_ROOT;
  const run = (args) => {
    const safe = assertGitArgs(args);
    return execFileSync('git', safe, {
      cwd, encoding: 'utf8', timeout: 20000, maxBuffer: 32 * 1024 * 1024,
      shell: false, windowsHide: true,
      env: { ...process.env, GIT_OPTIONAL_LOCKS: '0', GIT_PAGER: 'cat' }
    });
  };
  let isRepo = false;
  try { isRepo = run(buildGitProbeArgs()).trim() === 'true'; }
  catch (e) { errors.push({ source: 'git', kind: 'skipped', message: `${cwd} 不是可用 git 仓库（rev-parse 失败: ${String(e.message || e).split('\n')[0]}），按规格跳过` }); return { events, errors }; }
  if (!isRepo) { errors.push({ source: 'git', kind: 'skipped', message: `${cwd} 不是 git 仓库，按规格跳过` }); return { events, errors }; }

  const cap = ctx.limit > 0 ? ctx.limit : DEFAULT_GIT_CAP;
  let out;
  try {
    out = run(buildGitLogArgs({ sinceIso: ctx.since.iso, untilIso: ctx.until.iso, cap }));
  } catch (e) {
    errors.push({ source: 'git', kind: 'collect-failed', message: `git log 失败: ${String(e.message || e).split('\n')[0]}` });
    return { events, errors };
  }
  for (const line of out.split('\n')) {
    const t = line.trim();
    if (!t) continue;
    const [sha, date, ...rest] = t.split('|');
    const subject = rest.join('|');
    const ts = parseTs((date || '').trim());
    if (ts === null || ts < ctx.since.ms || ts > ctx.until.ms) continue;
    events.push({ source: 'git', ts: isoOf(ts), kind: 'committed', sha: sha.slice(0, 12), path: rel(cwd), desc: `${sha.slice(0, 8)} ${clip(subject, 150)}` });
  }
  return { events, errors };
}

/* ───────────────────────────────── 编排 ───────────────────────────────── */

function sortEvents(a, b) {
  if (a.ts !== b.ts) return a.ts < b.ts ? -1 : 1;
  return String(a.path || a.key || '') < String(b.path || b.key || '') ? -1 : 1;
}

/**
 * 采集五源 → 结构化事件流。
 * @param {object} opts
 *   since/until: assertTimeSpec 的返回值
 *   sources: string[]（冻结白名单内，默认全部）
 *   boardUrl: string（环回白名单内）
 *   limit: number（每源事件上限，0=不限）
 *   dryRun: boolean（不影响采集本身；只影响调用方是否落盘）
 * @returns {Promise<object>} 与规格一致的 doc
 */
/**
 * 时间窗归一：接受"已解析对象"（CLI 路径，已过门）或"原始字符串"（插件工具入参路径）。
 * ★ 为什么收在这里：v1.1 初版插件入口直接把入参字符串传了下来，于是 `since.ms` 是 undefined，
 *   窗口比对全部失效、`window.since` 变成 undefined —— 被"用 mock ctx 真跑 execute()"的
 *   冒烟测试当场抓到（`Cannot read properties of undefined (reading 'slice')`）。
 *   修法：归一动作下沉到唯一入口，两个调用方都不必各自记得先解析。
 */
function normWindow(v, label) {
  if (v && typeof v === 'object' && typeof v.ms === 'number') return v;
  return assertTimeSpec(v === undefined || v === null || v === '' ? label.fallback : String(v), label.name);
}

export async function collectAll(opts) {
  const now = new Date();
  const fallbackStart = fmtLocal(new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0));
  const fallbackEnd = fmtLocal(new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59));
  const since = normWindow(opts.since, { name: 'since', fallback: fallbackStart });
  const until = normWindow(opts.until, { name: 'until', fallback: fallbackEnd });
  if (since.ms > until.ms) {
    throw new GateErrorLocal('WINDOW_INVERTED', `拒绝：since(${since.iso}) 晚于 until(${until.iso})。`);
  }
  const sources = assertSources(opts.sources && opts.sources.length ? opts.sources : SOURCE_KEYS);
  const boardUrl = assertBoardUrl(opts.boardUrl || 'http://127.0.0.1:8792').origin;
  const limit = Number.isFinite(opts.limit) ? Math.max(0, Math.floor(opts.limit)) : 0;
  const hostname = opts.hostname || os.hostname();
  const dev = opts.device ? { device: assertDeviceName(opts.device), via: 'flag', hostnameShort: hostShort(opts.hostname || os.hostname()) } : defaultDevice(hostname);
  const ctx = { since, until, boardUrl, limit, dryRun: opts.dryRun === true, device: dev.device, hostname };

  const collected = {}; const errors = [];
  collected.files = sources.includes('files') ? collectFiles(ctx) : { events: [], errors: [] };
  collected.board = sources.includes('board') ? await collectBoard(ctx) : { events: [], errors: [] };
  collected.tools = sources.includes('tools') ? collectTools(ctx) : { events: [], errors: [] };
  collected.logs = sources.includes('logs') ? await collectLogs(ctx) : { events: [], errors: [] };
  collected.git = sources.includes('git') ? collectGit(ctx) : { events: [], errors: [] };

  const counts = {};
  const events = [];
  for (const key of SOURCE_KEYS) {
    const r = collected[key] || { events: [], errors: [] };
    r.errors.forEach((e) => errors.push({ ...e, collected_at: new Date().toISOString(), origin_device: dev.device }));
    // ★ 唯一打点入口：ts（源自己给，= 对象自身时刻）+ collected_at（本次）+ origin_device（采集者）
    const collectedAt = new Date().toISOString();
    const evs = stampEvents(r.events, { collectedAt, device: dev.device }).sort(sortEvents);
    const capped = limit > 0 ? evs.slice(0, limit) : evs;
    if (limit > 0 && evs.length > limit) errors.push({ source: key, kind: 'limit', message: `${key} 事件 ${evs.length} 条，按 --limit=${limit} 截断`, collected_at: new Date().toISOString(), origin_device: dev.device });
    counts[key] = capped.length;
    events.push(...capped);
  }
  events.forEach((e, i) => { e.id = 'E' + String(i + 1).padStart(3, '0'); });
  // 保持字段顺序与规格一致：window / device / hostname / collected_at / counts / events / errors
  const doc = {
    window: { since: since.iso, until: until.iso },
    device: dev.device,
    device_source: dev.via,
    hostname,
    plugin_version: opts.pluginVersion || null,
    collected_at: new Date().toISOString(),
    counts,
    events,
    errors
  };
  return { doc, counts, events, errors, sources, window: doc.window, device: dev.device, hostname };
}

/**
 * ★ 唯一的事件打点入口：给每条事件补 collected_at 与 origin_device，并逐条过门。
 * 门检在这里做而不是在调用方做 —— 只要有一条事件没被正确打点，采集就**失败即停**，
 * 不会产出"时点不可分辨"的事件流流到跨设备的下一步。
 */
export function stampEvents(events, { collectedAt, device }) {
  const out = [];
  for (const ev of events) {
    const stamped = { ...ev, collected_at: collectedAt, origin_device: device };
    assertEventStamped(stamped);   // ← 门：缺 ts/collected_at/origin_device 或缺时点格式 → GateError
    out.push(stamped);
  }
  return out;
}

/* ──────────────── 外部状态快照（只读；`--lean4-check` D 项证据） ──────────────── */

function statOf(p) {
  const st = statSafe(p);
  return st ? { size: st.size, mtimeMs: Math.round(st.mtimeMs) } : null;
}

function listing(dir) {
  try { return fs.readdirSync(dir).sort(); } catch { return null; }
}

/**
 * 只读外部状态快照。用于 dry-run 前后比对（实测，不是声明）。
 * sample：每个采集根的前 N 个文件（按路径排序，确定性）的 (path,size,mtime)。
 */
export function externalStateSnapshot({ samplePerRoot = 400 } = {}) {
  const snap = {
    ts: new Date().toISOString(),
    logFile: statOf(LOG_FILE),
    outDir: listing(OUT_DIR),
    selfcheckDir: listing(SELFCHECK_DIR),
    samples: {},
    sampleDigest: {}
  };
  for (const root of COLLECT_ROOTS) {
    if (!fs.existsSync(root)) { snap.samples[root] = null; snap.sampleDigest[root] = null; continue; }
    const { files } = walkFiles(root, { maxFiles: 40000 });
    const picked = files.slice().sort().slice(0, samplePerRoot);
    const rows = [];
    for (const f of picked) {
      const st = statSafe(f);
      if (st) rows.push(`${f}|${st.size}|${Math.round(st.mtimeMs)}`);
    }
    snap.samples[root] = rows.length;
    snap.sampleDigest[root] = crypto.createHash('sha256').update(rows.join('\n')).digest('hex').slice(0, 16);
  }
  return snap;
}

/** 对比两份快照，返回差异（只读）。 */
export function diffSnapshots(a, b) {
  const diffs = [];
  const cmp = (label, x, y) => { if (JSON.stringify(x) !== JSON.stringify(y)) diffs.push({ field: label, before: x, after: y }); };
  cmp('logFile', a.logFile, b.logFile);
  cmp('outDir', a.outDir, b.outDir);
  cmp('selfcheckDir', a.selfcheckDir, b.selfcheckDir);
  for (const root of Object.keys(a.sampleDigest)) cmp(`sampleDigest:${root}`, a.sampleDigest[root], b.sampleDigest[root]);
  return diffs;
}

export { parseTs, rel, clip };
