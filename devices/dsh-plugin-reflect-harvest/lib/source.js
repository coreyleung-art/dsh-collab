/**
 * source.js — 回填源解析（★ 跨设备层：本机 + 中央黑板）
 * =============================================================================
 * 只采本机 = 只看到四分之一（MBP 上有独立的 DSH 智能体网络，i9 经 MCP 接入）。
 * 本模块把"从哪儿读"从**单一目录**扩展为**全设备**，但保持两条纪律：
 *
 *   ① **按 (device, agent) 去重，来源优先级 = 黑板 > 本地**
 *      同一台设备可能既在本地落盘、又把同一份推到中央黑板（mac-mini 自己就是这种情况）。
 *      不去重就会把同一个人算两遍 → `recurrence` 虚高 → 排序失真。
 *      优先级取黑板：它是跨设备的**约定通道**（design §10.2「黑板即协议」）。
 *
 *   ② **绝不写黑板**。本模块只调 `blackboardGet` / `blackboardExists`（GET）。
 *      谁回填谁写；汇集方代笔 = 证据链当场失效。
 *
 * 支持的三种载荷形态（黑板一个 key 存一份 JSON，各设备写法可能不同，故都认）：
 *   A. 捆扎包  {device, date, submitted_at, plugin_version, answers:[{agent,items,declined}, ...]}
 *   B. 单体    {agent, items, declined}
 *   C. 黑板信封 {key, ts, value: <A 或 B>}   ← 黑板原生返回形态（由 lib/http.js 拆封）
 *
 * 跨设备污染防护：若载荷自带 `device` 字段且与 key 路径段不符 → 该条 **拒绝** 并计数
 * （`device_mismatch`）。key 路径强制含 `<device>` 段，但"key 对、内容来自别处"是真实存在的错法。
 */
import fs from 'node:fs';
import path from 'node:path';
import { blackboardGet, blackboardExists, isMeaningfulValue, HTTP_META } from './http.js';

/**
 * 载荷形态里可能承载 **agent 记录列表** 的字段名。
 * ★ 刻意**不含 `items`**：在单体答案里 `items` 是"这条反思的条目列表"（{id,event_ref,pit,lesson,...}），
 * 不是"智能体记录列表"。把它当记录列表会把一条反思拆成一堆缺 agent 的碎片
 * —— 这正是本工具开发中实测踩到的 bug（mac-mini 的 4 份单体回填被判成"第 N 条缺 agent"）。
 */
const BUNDLE_KEYS = Object.freeze(['answers', 'records', 'submissions']);
const DATE_FIELDS = Object.freeze(['date', 'reflection_date', 'reflect_date']);

/** 补填窗口（--allow-late 时向后找几天） */
export const LATE_WINDOW_DAYS = 2;

export function shiftDate(date, days) {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function nonEmptyString(v) { return typeof v === 'string' && v.trim() !== ''; }

/** 从任意载荷里抽出 {agent, data} 记录列表 */
function normalizePayload(rawIn, ctx) {
  const out = [];
  const warnings = [];
  // 有界解包：黑板原生信封是 {key,ts,value}，lib/http.js 已拆一层；
  // 但若写入方自己把值又包成了 {"value": ...}，这里再拆（**最多两层**，防无限递归）。
  let raw = rawIn;
  for (let i = 0; i < 2; i++) {
    if (raw && typeof raw === 'object' && !Array.isArray(raw) && 'value' in raw &&
        !('agent' in raw) && !Array.isArray(raw.items) &&
        !BUNDLE_KEYS.some((k) => Array.isArray(raw[k]))) {
      warnings.push(`载荷多包了一层 {"value": …}（第 ${i + 1} 层）已拆开 —— 写入方应直接 PUT 值本身`);
      raw = raw.value;
    } else break;
  }
  if (raw === null || raw === undefined) return { records: out, warnings: ['载荷为空'] };
  if (typeof raw !== 'object' || Array.isArray(raw)) return { records: out, warnings: [`载荷不是对象（${Array.isArray(raw) ? '数组' : typeof raw}）`] };

  // ★ 先判形态 B（单体）：自带 agent 且 items 是数组 —— 这是上游最初的格式，最常见
  let list = null;
  if (nonEmptyString(raw.agent) && Array.isArray(raw.items)) list = [raw];
  if (list === null) {
    for (const k of BUNDLE_KEYS) {
      if (Array.isArray(raw[k])) {
        const bad = raw[k].filter((x) => !x || typeof x !== 'object' || !nonEmptyString(x.agent));
        if (bad.length) warnings.push(`捆扎包 ${k} 里有 ${bad.length} 条记录缺 agent（已跳过）`);
        list = raw[k].filter((x) => x && typeof x === 'object' && nonEmptyString(x.agent));
        break;
      }
    }
  }
  if (list === null) {
    return { records: out, warnings: [`载荷既不是单体答案（有 agent + items 数组），也没有捆扎数组（${BUNDLE_KEYS.join('/')}）`] };
  }
  if (list.length === 0) return { records: out, warnings: ['记录列表为空'] };
  const bundleMeta = {
    device: raw.device, submitted_at: raw.submitted_at ?? raw.submittedAt ?? null,
    plugin_version: raw.plugin_version ?? raw.pluginVersion ?? null
  };

  list.forEach((a, i) => {
    if (a === null || typeof a !== 'object' || Array.isArray(a)) { warnings.push(`第 ${i + 1} 条不是对象`); return; }
    if (!nonEmptyString(a.agent)) { warnings.push(`第 ${i + 1} 条缺 agent`); return; }
    // 跨设备污染防护：载荷自称的设备必须与 key 路径段一致
    const declared = a.device ?? bundleMeta.device;
    if (nonEmptyString(declared) && String(declared).trim().toLowerCase() !== ctx.device) {
      warnings.push(`device_mismatch: 第 ${i + 1} 条自称 device='${declared}'，但来源是 '${ctx.device}' 的 key/目录 —— 已拒绝该条`);
      out.push({ rejected: true, reason: 'device_mismatch', agent: String(a.agent), declaredDevice: String(declared) });
      return;
    }
    const dateVal = DATE_FIELDS.map((f) => a[f] ?? raw[f]).find((v) => nonEmptyString(v)) || null;
    out.push({
      rejected: false,
      agent: String(a.agent).trim(),
      data: a,
      reflection_date: dateVal ? String(dateVal).slice(0, 10) : null,
      submitted_at: a.submitted_at ?? a.submittedAt ?? bundleMeta.submitted_at ?? null,
      plugin_version: a.plugin_version ?? a.pluginVersion ?? bundleMeta.plugin_version ?? null
    });
  });
  return { records: out, warnings };
}

function readLocalDir(dir) {
  try {
    if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) return { exists: false, files: [] };
    const files = fs.readdirSync(dir).filter((f) => f.endsWith('.json')).sort();
    return { exists: true, files: files.map((f) => ({ file: f, abs: path.join(dir, f), agent: f.replace(/\.json$/, '') })) };
  } catch (e) { return { exists: false, files: [], error: e.message }; }
}

/**
 * 收集全部设备的回填。
 *
 * @param {object} o
 *   date, devices[], localDevice, localRoot, central, localOnly, allowLate, timeoutMs
 *   legacyLocalRoot: 当 <localRoot>/answers/<localDevice>/<date>/ 不存在时，回退读 <localRoot>/answers/<date>/
 * @returns {Promise<object>} {records, perDevice, notes, attempts}
 */
export async function collectAnswerSources(o) {
  const {
    date, devices, localDevice, localRoot, central,
    localOnly = false, allowLate = false, timeoutMs = 8000
  } = o;

  const notes = [];
  const attempts = [];
  const records = [];
  const perDeviceMap = {};
  const answersRoot = path.join(localRoot, 'answers');
  const cardsRoot = path.join(localRoot, 'cards');
  const keyDates = [{ d: date, offset: 0 }];
  if (allowLate) {
    for (let k = 1; k <= LATE_WINDOW_DAYS; k++) keyDates.push({ d: shiftDate(date, -k), offset: k });
  }
  if (localOnly) notes.push('--local-only：未触碰中央黑板（仅本机目录）');

  for (const device of devices) {
    const rec = { device, local: 0, blackboard: 0, device_mismatch: 0, out_of_window: 0, late_accepted: 0, errors: [], card: { dispatched: null, via: null } };
    perDeviceMap[device] = rec;

    // ── 卡是否已派出（决定"没回填"是 pending 还是 not_dispatched）
    const cardLocal = [path.join(cardsRoot, device, `${date}.md`), path.join(cardsRoot, device, date)]
      .find((p) => fs.existsSync(p));
    if (cardLocal) { rec.card = { dispatched: true, via: `local:${cardLocal}` }; }
    else if (!localOnly) {
      const r = await blackboardExists(central, `data/reflect/cards/${device}/${date}`, { timeoutMs });
      if (r.exists) rec.card = { dispatched: true, via: 'blackboard' };
      else if (r.status === 404) rec.card = { dispatched: false, via: 'blackboard(404)' };
      else { rec.card = { dispatched: null, via: `blackboard(error:${r.error})` }; rec.errors.push(`卡探测失败: ${r.error}`); }
    } else { rec.card = { dispatched: false, via: 'local(miss)' }; }

    for (const { d, offset } of keyDates) {
      // ── 本地：<answersRoot>/<device>/<d>/*.json（新布局）
      let localDir = path.join(answersRoot, device, d);
      let local = readLocalDir(localDir);
      let legacy = false;
      // ── 老布局回退：answers/<d>/*.json（无设备段）→ 只对本机设备生效
      if (!local.exists && device === localDevice && offset === 0) {
        const legacyDir = path.join(answersRoot, date);
        const lg = readLocalDir(legacyDir);
        if (lg.exists && lg.files.length) { local = lg; localDir = legacyDir; legacy = true; }
      }
      if (local.error) rec.errors.push(`本地目录读取失败 ${localDir}: ${local.error}`);

      for (const f of local.files) {
        const origin = { kind: 'local', ref: f.abs, legacy, key_offset: offset };
        let raw;
        try { raw = JSON.parse(fs.readFileSync(f.abs, 'utf8')); }
        catch (e) {
          records.push({ device, agent: f.agent, payload: null, parseError: `JSON 解析失败: ${e.message}`, origin });
          rec.local++; continue;
        }
        const norm = normalizePayload(raw, { device });
        norm.warnings.forEach((w) => rec.errors.push(`${f.file}: ${w}`));
        for (const r of norm.records) {
          if (r.rejected) { rec.device_mismatch++; continue; }
          const keep = acceptByWindow(r, date, offset, rec);
          if (!keep) continue;
          records.push({ device, agent: r.agent, payload: r.data, origin, submitted_at: r.submitted_at, plugin_version: r.plugin_version, reflection_date: r.reflection_date, late_by_key: offset > 0, late_key_offset: offset });
          rec.local++; if (offset > 0) rec.late_accepted++;
        }
        if (!norm.records.length) { records.push({ device, agent: f.agent, payload: null, parseError: norm.warnings.join('; ') || '载荷不含答案记录', origin }); rec.local++; }
      }

      // ── 中央黑板：data/reflect/answers/<device>/<d>
      if (!localOnly) {
        const key = `data/reflect/answers/${device}/${d}`;
        const r = await blackboardGet(central, key, { timeoutMs });
        attempts.push({ device, key, status: r.status, ok: r.ok, error: r.error });
        if (r.ok && !isMeaningfulValue(r.value)) {
          // ★ 空壳键：状态码 200 但内容为空 → 按"未提交"处理，但必须留痕（否则就是静默漏读）
          rec.errors.push(`黑板 ${key}: 空壳键（HTTP 200 但 value 为空）—— 按未提交处理；依 R003 补充，写入方需回读确认内容非空`);
        } else if (r.ok) {
          const norm = normalizePayload(r.value, { device });
          norm.warnings.forEach((w) => rec.errors.push(`${key}: ${w}`));
          for (const rec2 of norm.records) {
            if (rec2.rejected) { rec.device_mismatch++; continue; }
            if (!acceptByWindow(rec2, date, offset, rec)) continue;
            records.push({
              device, agent: rec2.agent, payload: rec2.data,
              origin: { kind: 'blackboard', ref: key, board_ts: r.ts ?? null, key_offset: offset },
              submitted_at: rec2.submitted_at, plugin_version: rec2.plugin_version, reflection_date: rec2.reflection_date,
              late_by_key: offset > 0, late_key_offset: offset
            });
            rec.blackboard++; if (offset > 0) rec.late_accepted++;
          }
          if (!norm.records.length) rec.errors.push(`${key}: 载荷不含答案记录`);
        } else if (!r.missing) {
          rec.errors.push(`黑板读取失败 ${key}: ${r.error}`);
        }
      }
    }
    notes.push(`设备 ${device}: 本地 ${rec.local} · 黑板 ${rec.blackboard} · 卡=${rec.card.dispatched === null ? '未知' : (rec.card.dispatched ? '已派出' : '未派出')}（${rec.card.via}）`);
  }

  // ── ★ (device, agent) 去重，黑板 > 本地
  const byKey = new Map();
  const duplicates = [];
  const rank = (r) => (r.origin.kind === 'blackboard' ? 2 : 1) + (r.late_by_key ? 0 : 0.5); // 黑板优先；同源内"当日"优先
  for (const r of records) {
    const k = `${r.device}#${r.agent}`;
    if (!byKey.has(k)) { byKey.set(k, r); continue; }
    const prev = byKey.get(k);
    if (rank(r) > rank(prev)) {
      duplicates.push({ key: k, kept: r.origin.kind, dropped: prev.origin.kind, ref: prev.origin.ref });
      byKey.set(k, r);
    } else {
      duplicates.push({ key: k, kept: prev.origin.kind, dropped: r.origin.kind, ref: r.origin.ref });
    }
  }

  return { records: [...byKey.values()], perDevice: perDeviceMap, notes, attempts, duplicates, httpMeta: HTTP_META };
}

/** 窗口判定：offset=0 全收；offset>0（补填 key）只收"目标日"的记录 */
function acceptByWindow(r2, targetDate, offset, rec) {
  if (offset === 0) return true;
  if (r2.reflection_date === null) { rec.out_of_window++; rec.errors.push(`补填 key（T-${offset}）里的记录无 date 字段 → 无法确认归属，已跳过`); return false; }
  if (r2.reflection_date !== targetDate) { rec.out_of_window++; return false; }
  return true;
}
