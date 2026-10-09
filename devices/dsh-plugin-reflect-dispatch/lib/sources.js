/**
 * sources.js — 跨设备事件源（v1.1，设计文档 §10）
 * =============================================================================
 * 事件源从"本机一个文件"扩展为"全设备"：
 *   优先 中央黑板 `data/reflect/events/<device>/<date>`（遍历所有可解析设备）
 *   回退 本机 `--events <path>`（`--local-only` 时只走这条）
 *
 * ★★ 设备枚举必须诚实标方法（这是本文件最重要的设计决定）★★
 * 设计文档 §10 假设"从黑板 data/reflect/events/ 前缀列举（单段列举返回 {list,total}）"。
 * **实测（2026-09-10，中央板）不支持前缀过滤**：
 *     GET /data/reflect/events/  → 返回整个 data 命名空间（14.8MB / 57 键）
 *     GET /data/reflect/events   → {"error":"not found"}
 *     GET /data/?limit=5         → 只截断前 5 条，不是按前缀筛
 * 所以本工具**不假装**"已经列举了全部设备"，而是给出四条有优先级的枚举路径，
 * 并把**实际用了哪一条 + 它的局限**写进结果、台账与卡片：
 *   1. explicit  —— --devices 显式指定（最权威）
 *   2. index     —— 中央板 `data/reflect/devices` 索引键（由各设备 collect 维护；协议面）
 *   3. probe     —— 冻结候选设备 + 索引里的设备名，逐个 GET 探测 200/404
 *   4. local     —— 兜底：只处理本机
 * 每条路径都返回 `method` / `evidence` / `limits`，绝不把"探测过的"说成"枚举到的"。
 */
import fs from 'node:fs';
import { GateError, assertDeviceName, CANDIDATE_DEVICES, cardKeyFor, eventsKeyFor, answersKeyFor } from './gate.js';
import { bbGet, probeKey, listKeys } from './board.js';

export const DEVICE_INDEX_KEY = 'data/reflect/devices';

/** 本机设备名：`--device` 优先，其次主机名映射，最后 'mac-mini'（本仓库的宿主实况）。 */
export function resolveLocalDevice(explicit, hostname) {
  if (explicit) return assertDeviceName(explicit);
  const h = String(hostname || '').toLowerCase();
  if (/mac-?mini|macmini/.test(h)) return 'mac-mini';
  if (/macbook|mbp|laptop/.test(h)) return 'mbp';
  if (/^(pc-)?i9/.test(h)) return 'i9';
  return 'mac-mini';
}

/**
 * 解析设备集合。
 * @param {object} o
 * @param {string|string[]} [o.devices]  --devices
 * @param {boolean} [o.localOnly]
 * @param {string} o.localDevice
 * @param {string} o.dateDashed
 * @returns {Promise<{devices:string[], method:string, evidence:object, limits:string[]}>}
 */
export async function resolveDevices(o = {}) {
  const localDevice = assertDeviceName(o.localDevice);
  const limits = [
    '黑板**不做前缀过滤**（GET /data/reflect/events/ 返回整个 data 命名空间）——但 `limit >= total` 时键集**完整**，按前缀过滤有效；被截断时不可当清单（本工具会检查 complete 再决定用不用）',
    'probe 法只能发现"冻结候选 ∪ 索引 ∪ 列举结果"里的设备；一台从未被登记的新设备只能靠 --devices 或列举/索引显式声明'
  ];

  if (o.localOnly) {
    return { devices: [localDevice], method: 'local-only', evidence: { reason: '--local-only' }, limits };
  }

  if (o.devices !== undefined && o.devices !== null && String(o.devices).trim() !== '') {
    const raw = Array.isArray(o.devices) ? o.devices : String(o.devices).split(',');
    const list = raw.map((s) => String(s).trim()).filter(Boolean).map(assertDeviceName);
    if (!list.length) throw new GateError('DEVICE_EMPTY', '--devices 给了空列表：要么不给，要么给合法设备名');
    return { devices: [...new Set(list)], method: 'explicit', evidence: { from: '--devices' }, limits };
  }

  // 2) ★ 中央板前缀列举（用户指定的默认路径）：仅当键集**完整**时可信
  const listing = await listKeys('data', 'central', 2000);
  const listedDevices = [];
  if (listing.supported && listing.complete) {
    const re = /^data\/reflect\/events\/([a-z][a-z0-9-]{1,15})\//;
    for (const k of listing.keys) {
      const m = k.match(re);
      if (m) { try { listedDevices.push(assertDeviceName(m[1])); } catch { /* 脏段不入集合 */ } }
    }
  }
  const uniqListed = [...new Set(listedDevices)];

  // 3) 中央板设备索引（协议面：各设备 collect 结束时维护）
  const idx = await bbGet(DEVICE_INDEX_KEY, 'central');
  const indexed = [];
  if (idx && Array.isArray(idx.devices)) {
    for (const d of idx.devices) {
      const name = typeof d === 'string' ? d : (d && d.device);
      try { indexed.push(assertDeviceName(name)); } catch { /* 脏数据不入索引，也不假装它不存在 */ }
    }
  }

  // 4) 探测：列举结果 ∪ 索引 ∪ 冻结候选（逐个 GET events 键，200=该设备当天有事件上报）
  const candidates = [...new Set([...uniqListed, ...indexed, ...CANDIDATE_DEVICES, localDevice])];
  const probes = [];
  const reporting = [];
  for (const d of candidates) {
    const p = await probeKey(eventsKeyFor(d, o.dateDashed), 'central');
    probes.push({ device: d, exists: p.exists, status: p.status });
    if (p.exists) reporting.push(d);
  }
  if (!reporting.includes(localDevice)) reporting.push(localDevice);   // 本机总参与（它可能还没上传）
  reporting.sort((a, b) => (a === localDevice ? -1 : b === localDevice ? 1 : a.localeCompare(b)));

  if (listedDevices.length || indexed.length || reporting.length > 1) {
    const method = listing.complete && uniqListed.length ? 'listing+probe'
      : (indexed.length ? 'index+probe' : 'probe');
    return {
      devices: reporting,
      method,
      evidence: {
        indexKey: DEVICE_INDEX_KEY,
        prefixListing: { attempted: true, complete: listing.complete, total: listing.total, keysReturned: listing.keys.length, respBytes: listing.respBytes, devicesFound: uniqListed, note: listing.note },
        indexed, candidates, probes, reportingToday: reporting.filter((d) => d !== localDevice)
      },
      limits
    };
  }

  return {
    devices: [localDevice],
    method: 'local-fallback',
    evidence: {
      prefixListing: { attempted: true, complete: listing.complete, total: listing.total, keysReturned: listing.keys.length, respBytes: listing.respBytes, devicesFound: uniqListed, note: listing.note },
      candidates, probes,
      reason: '中央板既没有列举结果、也没有设备索引、也没有任何设备的当天事件键 → 兜底只处理本机'
    },
    limits: [...limits, '本次是 local-fallback：跨设备面**没有生效**（不是"别的设备没问题"，而是"没读到它们的事件"）']
  };
}

/**
 * 取一台设备的事件流文档。
 *  - 本机 + --events 给了路径 → 读本地文件（`--local-only` 时的唯一路径）
 *  - 其余 → 中央板 data/reflect/events/<device>/<date>
 * 返回统一形状：{device, ok, doc, origin, key, status, fetchedAt, bytes, note}
 */
export async function fetchDeviceEvents(device, o = {}) {
  assertDeviceName(device);
  const dateDashed = o.dateDashed;
  const key = eventsKeyFor(device, dateDashed);
  const isLocal = device === o.localDevice;

  if (isLocal && o.eventsDoc) {
    return {
      device, ok: true, origin: 'inline-doc', key: null, status: 200, path: '(inline)',
      bytes: JSON.stringify(o.eventsDoc).length, fetchedAt: new Date().toISOString(),
      note: '本机事件流（调用方直接给的文档）', doc: o.eventsDoc
    };
  }

  if (isLocal && o.eventsPath) {
    try {
      const raw = fs.readFileSync(o.eventsPath, 'utf8');
      return {
        device, ok: true, origin: 'local-file', key: null, status: 200, path: o.eventsPath,
        bytes: Buffer.byteLength(raw, 'utf8'), fetchedAt: new Date().toISOString(),
        note: '本机事件流（--events 指定）', doc: JSON.parse(raw)
      };
    } catch (e) {
      return { device, ok: false, origin: 'local-file', key: null, status: 0, path: o.eventsPath, error: String(e.message || e), note: '本机事件流读取失败' };
    }
  }

  const p = await probeKey(key, 'central');
  if (!p.exists) {
    return {
      device, ok: false, origin: 'central-board', key, status: p.status, error: p.error,
      fetchedAt: new Date().toISOString(),
      note: p.status === 404
        ? '中央板 404：该设备**尚未上报**当天事件（404=不存在，不是"没有事件"——「没读到」≠「没有」）'
        : (p.status === 400 ? '中央板 400：键写法非法（本工具的 bug，不是设备的问题）' : `中央板不可用（status=${p.status}）`)
    };
  }
  const doc = await bbGet(key, 'central');
  return { device, ok: true, origin: 'central-board', key, status: 200, bytes: JSON.stringify(doc).length, fetchedAt: new Date().toISOString(), note: '取自中央黑板', doc };
}

/**
 * 在场判定（用于 delivered / pending）。
 *
 * ★★ 关键修正（2026-09-10，自己推演时抓到的一个**同义反复**）★★
 * 初版把 `reportedToday`（该设备当天事件键存在）也算作"在线"。
 * 但那与"有卡可发"是**同一个条件** —— 结果是**永远判 delivered，pending 分支永不可达**，
 * 而 pending 恰恰是设计文档 §10.4「待投递队列」的核心语义。
 * 事件是 collect 时一次性上传的：**设备当晚可能早就关机了**，"当天上报过"不等于"此刻在场"。
 *
 * 现在的口径（**独立活性信号**，与"有没有事件"解耦）：
 *   a) 本机设备 → 直接在场；
 *   b) 发现层心跳 `data/discovery/agents/<device>`（R-ERR4：ts < 90s = online）→ 在场；
 *   c) `--assume-online <devices>` 人工声明（运维已知设备在线时的显式覆盖）；
 *   其余 → **pending（离线待取）**，并把三个信号的实际取值一并记录（证据可复核）。
 * 三个信号分开报，不合成一个模糊的"在线"布尔值。
 */
export async function computePresence(device, o = {}) {
  if (device === o.localDevice) {
    return {
      device, online: true, status: 'delivered',
      signals: { local: true, reportedToday: null, heartbeat: null, assumed: false },
      note: '本机设备：直接在场（卡已落中央板，本机可立即读）'
    };
  }
  // 该信号只作**背景信息**，不参与在线判定（否则就是同义反复）
  const reportedToday = !!(await probeKey(eventsKeyFor(device, o.dateDashed), 'central')).exists;
  const hb = await bbGet(`data/discovery/agents/${device}`, 'central');
  let heartbeat = null;
  if (hb && (hb.ts || hb.updatedAt)) {
    const t = Date.parse(hb.ts || hb.updatedAt);
    if (Number.isFinite(t)) heartbeat = { ts: new Date(t).toISOString(), ageSec: Math.round((Date.now() - t) / 1000), fresh: (Date.now() - t) < 90_000 };
  }
  const assumed = Array.isArray(o.assumeOnline) && o.assumeOnline.includes(device);
  const online = assumed || !!(heartbeat && heartbeat.fresh);
  return {
    device, online,
    status: online ? 'delivered' : 'pending',
    signals: { local: false, reportedToday, heartbeat, assumed },
    note: online
      ? `在场（${assumed ? '--assume-online 人工声明' : ''}${assumed && heartbeat && heartbeat.fresh ? ' + ' : ''}${heartbeat && heartbeat.fresh ? `心跳新鲜(${heartbeat.ageSec}s<90s)` : ''}）`
      : `**不在场** → 状态记 \`pending\`（离线待取），**不是** \`failed\`：卡已落中央板 \`data/reflect/cards/${device}/${o.dateDashed}\`，` +
        `该设备上线自取即可（设计文档 §10.4）。依据：心跳${heartbeat ? `存在但已 ${heartbeat.ageSec}s 未更新(>90s)` : '缺失'}；` +
        `当天事件键${reportedToday ? '存在（=它当天跑过 collect，但这不代表此刻在线）' : '不存在'}。` +
        '若你确知它在线，可加 --assume-online 显式覆盖（人工声明会记录在台账里）。'
  };
}

/** 三件套键（供 CLI/工具展示，让"该写哪、该读哪"一目了然）。 */
export function keysFor(device, dateDashed) {
  return { events: eventsKeyFor(device, dateDashed), cards: cardKeyFor(device, dateDashed), answers: answersKeyFor(device, dateDashed) };
}
