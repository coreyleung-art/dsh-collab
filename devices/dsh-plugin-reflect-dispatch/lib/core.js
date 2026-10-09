/**
 * core.js — 编排内核（无危险原语）
 * =============================================================================
 * 流水线（v1.1 跨设备版）：
 *   解析日期+迟到门 → 载档案 → 解析设备集合 → 逐设备取事件流（中央板优先）
 *   → 归属判定（specific > dir > weak） → 逐设备逐人定制卡 → 凭据脱敏
 *   → 本机落盘（含设备段）→（可选）PUT 中央板 + 回读校验 → 在场判定 delivered/pending
 *   → 台账（含每张卡的投递时刻，Φ13）
 *
 * 四条纪律：
 *   ① **dry-run 在任何写操作之前返回**，连统一日志都不落盘 —— 这样 lean4-check D
 *      才能断言"卡目录树 + 探针键 + 日志 mtime 三者前后完全一致"。
 *   ② **发送 = PUT + 立即 GET 回读比对**（board.putAndVerify），回读失败即派发失败。
 *   ③ 每个目标走**状态机** planned→carded→board_written→readback_ok→recorded，跳步即抛。
 *   ④ **落盘与写黑板前都跑一次凭据脱敏**（Φ12 device_gates「落盘端 scrub」），
 *      且脱敏在**算 sha256 之前** —— 否则哈希与落盘内容不符，回读校验会误报。
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import {
  GateError, assertEventsDoc, resolveAgentFilter, assertTargetExists, assertWithinReflectRoot,
  assertDeviceInPath, assertDeviceSegment, assertDeviceName, assertNotLate, localDateCompact,
  buildNotice, cardKeyFor, eventsKeyFor, answersKeyFor, makeDispatchStateMachine,
  REFLECT_ROOT_REL, charCount, scrubCredentials, resolveStatus, CANDIDATE_DEVICES
} from './gate.js';
import { loadTargets, HOME, findRuleCandidates } from './profiles.js';
import { attributeEvents, pickForAgent, buildCard, buildDeviceCard, ruleKeywords, actionDistribution, normalizeResource } from './cards.js';
import { putAndVerify } from './board.js';
import { resolveDevices, resolveLocalDevice, fetchDeviceEvents, computePresence } from './sources.js';

/** ⑥ 版本管理：单一来源 = package.json（CLI 与工具都读这里，不硬编码第二份）。 */
export const VERSION = (() => {
  try { return JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8')).version; }
  catch { return '0.0.0-unknown'; }
})();

export const PLUGIN_NAME = 'dsh-plugin-reflect-dispatch';
export const LOG_FILE = path.join(HOME, 'dsh-collab', 'logs', `${PLUGIN_NAME}.log`);
export const HERE = path.dirname(fileURLToPath(import.meta.url));

/* ══════════════════════ ⑦ 统一日志 ══════════════════════ */

export function makeLogger({ persist = true, echo = false } = {}) {
  const lines = [];
  return {
    lines,
    log(msg, extra) {
      const line = `[${new Date().toISOString()}] ${msg}` + (extra ? ` ${JSON.stringify(extra)}` : '');
      lines.push(line);
      if (!persist) return line;                       // dry-run：不落盘（零变更）
      try {
        fs.mkdirSync(path.dirname(LOG_FILE), { recursive: true });
        fs.appendFileSync(LOG_FILE, line + '\n');
      } catch { /* 日志失败不阻塞主流程 */ }
      if (echo) process.stdout.write(line + '\n');
      return line;
    }
  };
}

/* ══════════════════════ 输入 ══════════════════════ */

export function loadEventsDoc(eventsPath) {
  if (!eventsPath) throw new GateError('EVENTS_IO', '缺少 --events <path>');
  let raw;
  try { raw = fs.readFileSync(eventsPath, 'utf8'); }
  catch (e) { throw new GateError('EVENTS_IO', `事件流文件不可读: ${eventsPath}（${e.message}）`); }
  let doc;
  try { doc = JSON.parse(raw); }
  catch (e) { throw new GateError('EVENTS_IO', `事件流不是合法 JSON: ${eventsPath}（${e.message}）`); }
  return { doc, file: eventsPath, bytes: Buffer.byteLength(raw, 'utf8') };
}

export function deriveDates(doc, override) {
  if (override) {
    const s = String(override).replace(/-/g, '');
    if (!/^\d{8}$/.test(s)) throw new GateError('DATE_INVALID', `--date 必须是 YYYY-MM-DD 或 YYYYMMDD，收到 "${override}"`);
    return { compact: s, dashed: `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}` };
  }
  const until = doc && doc.window && doc.window.until ? String(doc.window.until) : '';
  const m = until.match(/^(\d{4})-?(\d{2})-?(\d{2})/);
  if (m) return { compact: `${m[1]}${m[2]}${m[3]}`, dashed: `${m[1]}-${m[2]}-${m[3]}` };
  const c = localDateCompact();
  return { compact: c, dashed: `${c.slice(0, 4)}-${c.slice(4, 6)}-${c.slice(6, 8)}` };
}

export function sha256(text) {
  return crypto.createHash('sha256').update(text, 'utf8').digest('hex');
}

/* ══════════════════════ 跨设备信号（设计文档 §10.7） ══════════════════════ */

/**
 * 同一资源/关键词在**别的设备**上也出现了事件 → 独立复现 = 更强的信号。
 * 这里只给"线索"，不替智能体下结论（第 5 问仍由它自己回答）。
 */
export function crossDeviceSignal(matched, docsByDevice, thisDevice) {
  const kws = new Set();
  for (const m of matched) {
    const ev = m.event;
    if (ev.path) kws.add(path.basename(ev.path).toLowerCase());
    if (ev.key) kws.add(path.basename(ev.key).toLowerCase());
    for (const tok of String(ev.desc || '').split(/[\s,，。:：;；、()（）\[\]【】/|"'`]+/)) {
      const t = tok.trim().toLowerCase();
      if (t.length >= 4 && t.length <= 20) kws.add(t);
    }
    if (m.resource) kws.add(String(m.resource).toLowerCase());
  }
  const norm = (s) => String(s).toLowerCase().replace(/[-_]/g, '');
  const devices = [];
  let totalOther = 0;
  for (const [dev, doc] of docsByDevice) {
    if (dev === thisDevice || !doc || !Array.isArray(doc.events)) continue;
    const hits = [];
    for (const ev of doc.events) {
      const hay = norm([ev.path, ev.key, ev.desc, ev.source].filter(Boolean).join(' '));
      for (const kw of kws) {
        const n = norm(kw);
        if (n.length >= 4 && hay.includes(n)) { hits.push({ ev, kw }); break; }
      }
    }
    if (hits.length) {
      totalOther += hits.length;
      devices.push({ device: dev, count: hits.length, sampleIds: hits.slice(0, 4).map((x) => x.ev.id), resource: hits[0].kw });
    }
  }
  devices.sort((a, b) => b.count - a.count);
  return { devices, totalOther, note: totalOther ? '跨设备复现线索（独立复现=更强信号）' : '本次未在别的设备探测到同类事件（"没读到" ≠ "不存在"）' };
}

/* ══════════════════════ 主流程 ══════════════════════ */

/**
 * @param {object} opts
 * @param {string}  [opts.eventsPath]   本机事件流文件（本机设备用）
 * @param {object}  [opts.eventsDoc]    直接给本机事件流文档（自检用；与 eventsPath 二选一）
 * @param {string|string[]} [opts.agents]
 * @param {string|string[]} [opts.devices]  显式设备列表
 * @param {boolean} [opts.localOnly]    只处理本机
 * @param {string}  [opts.device]       本机设备名
 * @param {boolean} [opts.allowLate]    允许补派（T+1/T+2）
 * @param {boolean} [opts.send]         是否 PUT 到中央板
 * @param {boolean} [opts.dryRun]
 * @param {string}  [opts.date]
 * @param {number}  [opts.maxEvents=8]
 * @param {number}  [opts.threshold=50]
 * @param {string}  [opts.profilesPath]
 * @param {string}  [opts.cardsRoot]
 */
export async function dispatch(opts = {}) {
  const dryRun = opts.dryRun === true;
  const sendRequested = opts.send === true;
  const send = sendRequested && !dryRun;
  const maxEvents = Number.isFinite(opts.maxEvents) ? Math.max(1, opts.maxEvents) : 8;
  const threshold = Number.isFinite(opts.threshold) ? opts.threshold : 50;
  const logger = makeLogger({ persist: !dryRun, echo: opts.echoLog === true });
  const localDevice = resolveLocalDevice(opts.device, opts.hostname || os.hostname());

  const result = {
    ok: false, plugin: PLUGIN_NAME, version: VERSION, dryRun, send: sendRequested,
    localDevice, date: null, dateDashed: null, late: null,
    profiles: null, devices: [], deviceEnum: null, targets: [], skipped: [],
    unassigned: [], suppressedTotal: 0, notices: [], redactions: [],
    cardsRoot: null, cardsRootTilde: null, ledgerPath: null, ledgerPathTilde: null,
    logFile: dryRun ? null : LOG_FILE, logPersisted: !dryRun
  };

  // 1) 本机事件流（若给了）→ 用于定日期
  let localDoc = null, localFile = null;
  if (opts.eventsDoc) { localDoc = opts.eventsDoc; localFile = '(inline)'; }
  else if (opts.eventsPath) { const r = loadEventsDoc(opts.eventsPath); localDoc = r.doc; localFile = r.file; result.eventsBytes = r.bytes; }
  result.eventsFile = localFile;

  const dates = deriveDates(localDoc, opts.date);
  result.date = dates.compact;
  result.dateDashed = dates.dashed;

  // 2) 迟到门（补派 T+1/T+2 必须显式 --allow-late）
  const today = localDateCompact();
  const late = assertNotLate(dates.compact, today, opts.allowLate === true);
  result.late = late;
  logger.log(`开始 dispatch date=${dates.dashed} local=${localDevice} send=${sendRequested} dryRun=${dryRun} late=${late.late}`, { today });

  // 3) 档案
  const targets = loadTargets({ profilesPath: opts.profilesPath });
  result.profiles = { source: targets.source, file: targets.file, count: targets.index.size };
  logger.log(`档案载入 source=${targets.source} targets=${targets.index.size}`, { file: targets.file });

  // 4) 设备集合
  const devRes = await resolveDevices({
    devices: opts.devices, localOnly: opts.localOnly, localDevice, dateDashed: dates.dashed
  });
  result.deviceEnum = { method: devRes.method, evidence: devRes.evidence, limits: devRes.limits, devices: devRes.devices };
  logger.log(`设备解析 method=${devRes.method} devices=[${devRes.devices.join(', ')}]`, { limitCount: devRes.limits.length });

  // 5) 逐设备取事件流
  const docsByDevice = new Map();
  for (const dev of devRes.devices) {
    const entry = await fetchDeviceEvents(dev, {
      dateDashed: dates.dashed, localDevice,
      eventsPath: (opts.localOnly || dev === localDevice) ? opts.eventsPath : undefined,
      eventsDoc: (opts.localOnly || dev === localDevice) ? opts.eventsDoc : undefined
    });
    if (entry.ok && entry.doc && Array.isArray(entry.doc.events) && entry.doc.events.length === 0) {
      entry.ok = false; entry.empty = true;
      entry.note = '该设备事件流存在但为空（0 条）→ 记为 no-events，不为它出卡（没有事实就没有定制）';
    }
    docsByDevice.set(dev, entry);
    logger.log(`事件流 ${dev}: ${entry.ok ? `${entry.doc.events.length} 条` : '不可用'}`, { origin: entry.origin, key: entry.key || null, status: entry.status });
  }
  result.devices = [...docsByDevice.entries()].map(([device, e]) => ({
    device, ok: !!e.ok, origin: e.origin, key: e.key || null, status: e.status,
    eventCount: e.ok ? e.doc.events.length : 0, fetchedAt: e.fetchedAt || null, note: e.note, error: e.error || null
  }));

  const withEvents = [...docsByDevice.entries()].filter(([, e]) => e.ok);
  if (!withEvents.length) {
    throw new GateError('EVENTS_EMPTY',
      `全部 ${devRes.devices.length} 台设备都取不到事件流（设备枚举方式 ${devRes.method}）：` +
      `${result.devices.map((d) => `${d.device}(status=${d.status})`).join(', ')}。` +
      '没有当天真实事件就没有"定制卡"，此时只能产出套话 —— **拒绝生成**。' +
      '（若刚部署，请先让各设备跑 collect 并把事件流 PUT 到中央板 data/reflect/events/<device>/<date>。）');
  }

  // 6) 逐设备：归属 + 定制卡
  const selected = resolveAgentFilter(opts.agents, targets.index);
  const reflectRoot = `${HOME}/dsh-collab/${REFLECT_ROOT_REL}`;
  const cardsRoot = assertWithinReflectRoot(opts.cardsRoot || path.join(reflectRoot, 'cards'), HOME);
  result.cardsRoot = cardsRoot;
  result.cardsRootTilde = cardsRoot.replace(HOME, '~');
  const pendingWrites = [];
  const devicePlans = [];
  const allEntryDocs = new Map([...docsByDevice.entries()].filter(([, e]) => e.ok).map(([d, e]) => [d, e.doc]));

  for (const [device, entry] of withEvents) {
    assertDeviceName(device);
    let doc;
    try { doc = assertEventsDoc(entry.doc, { allowEmpty: false }); }
    catch (e) { throw new GateError(e.code, `设备 ${device} 的事件流未过 Schema 门：${e.message}`); }
    const events = doc.events;
    const attr = attributeEvents(events, targets, { home: HOME, threshold });
    result.suppressedTotal += attr.stats.suppressedTotal;
    result.broadResourcesTotal = (result.broadResourcesTotal || 0) + attr.stats.broadResourcesTotal;
    result.unassigned.push(...attr.unassigned.map((e) => ({
      device, id: e.id, source: e.source, path: e.path || null, key: e.key || null,
      desc: String(e.desc || '').slice(0, 80), reason: `无任何目标 resources 命中（阈值 ${threshold}）`
    })));
    logger.log(`归属 ${device}: events=${events.length} unassigned=${attr.unassigned.length} suppressed=${attr.stats.suppressedTotal}`);

    const deviceCardKey = cardKeyFor(device, dates.dashed);            // ← 类型锁：设备名/日期受控
    assertDeviceSegment(deviceCardKey, device, devRes.devices);        // ← 跨设备写门
    const notice = buildNotice(deviceCardKey);                         // ← 类型锁：唯一构造入口，>50 字直接抛
    const answersKey = answersKeyFor(device, dates.dashed);
    const deviceAgents = [];

    for (const agent of selected) {
      const matched = attr.perAgent.get(agent.agentId) || [];
      if (!matched.length) {
        result.skipped.push({
          device, agentId: agent.agentId, shortKey: agent.shortKey, reason: 'no-events',
          detail: `${device} 当天事件流里没有归到你 resources 的事件 → **不发卡**（没有事实就没有定制，发了只能是套话）；此处如实记录，不静默跳过`
        });
        continue;
      }
      const picked = pickForAgent(matched, maxEvents);
      const ruleCands = findRuleCandidates(ruleKeywords(matched), 3);
      const cross = crossDeviceSignal(matched, allEntryDocs, device);
      const suppressedForMe = (attr.suppressed.get(agent.agentId) || []).map((s) => ({ id: s.event.id, score: s.score, via: s.via, keptBy: s.keptBy }));
      const broadResourcesForMe = attr.broadResources.get(agent.agentId) || [];

      const pCanonical = assertDeviceInPath(path.join(cardsRoot, device, `${agent.shortKey}.md`), device, HOME);
      const pDated = assertDeviceInPath(path.join(cardsRoot, device, dates.compact, `${agent.shortKey}.md`), device, HOME);

      const cardInput = {
        agent, picked, matchedAll: matched, eventTotal: events.length,
        unassignedCount: attr.unassigned.length, dateCompact: dates.compact, dateDash: dates.dashed,
        window: doc.window || {}, version: VERSION, notice, ruleCands, indexSource: targets.source,
        topicNote: doc.topic || doc.theme || null, suppressedForMe, broadResourcesForMe, crossDevice: cross,
        device, deviceNote: entry.note,
        eventsNote: `${events.length} 条事件 · 来源 ${entry.origin}${entry.key ? ` · \`${entry.key}\`` : ''}`,
        emit: {
          cardPath: pDated.replace(HOME, '~'),
          mode: dryRun ? '**dry-run（未落盘、未发送）**' : (send ? `已落盘 + 已 PUT 中央板 \`${deviceCardKey}\`` : '仅落盘（--emit-only，未发送）'),
          boardKey: send ? deviceCardKey : null,
          replyKey: answersKey
        }
      };
      // ★ 脱敏在算 sha256 之前（否则哈希与落盘内容不符，回读校验会误报）
      const scrubbed = scrubCredentials(buildCard(cardInput));
      if (scrubbed.total) result.redactions.push({ device, shortKey: agent.shortKey, hits: scrubbed.hits });
      const card = scrubbed.text;

      deviceAgents.push({
        agent, picked, matchedAll: matched, card, cardInput,
        paths: { canonical: pCanonical, dated: pDated },
        sha256: sha256(card), bytes: charCount(card),
        suppressed: suppressedForMe, broadResources: broadResourcesForMe, cross, ruleCands: ruleCands.map((c) => c.id),
        distribution: actionDistribution(matched),
        machine: makeDispatchStateMachine(`${device}:${agent.shortKey}`)
      });
      pendingWrites.push({ absPath: pCanonical, content: card });
      pendingWrites.push({ absPath: pDated, content: card });
    }

    // 设备级合并卡（写中央板的那一张）
    let deviceCard = null, deviceCardPath = null, deviceCardSha = null;
    if (deviceAgents.length) {
      deviceCardPath = assertDeviceInPath(path.join(cardsRoot, device, dates.compact, '_device-card.md'), device, HOME);
      const scr = scrubCredentials(buildDeviceCard({
        device, deviceNote: entry.note, dateDash: dates.dashed, version: VERSION,
        window: doc.window || {}, agents: deviceAgents.map((a) => a.cardInput),
        eventsNote: `${events.length} 条事件 · 来源 ${entry.origin}`,
        eventsKey: eventsKeyFor(device, dates.dashed), cardKey: deviceCardKey, answersKey,
        indexSource: targets.source
      }));
      if (scr.total) result.redactions.push({ device, shortKey: '(device-card)', hits: scr.hits });
      deviceCard = scr.text;
      deviceCardSha = sha256(deviceCard);
      pendingWrites.push({ absPath: deviceCardPath, content: deviceCard });
    }

    devicePlans.push({
      device, doc, events, attr, entry, deviceCardKey, deviceCard, deviceCardSha, deviceCardPath,
      notice, answersKey, agents: deviceAgents, presence: null, board: null, status: 'planned',
      machine: makeDispatchStateMachine(device)
    });

    for (const a of deviceAgents) {
      result.targets.push({
        device, agentId: a.agent.agentId, shortKey: a.agent.shortKey, qualified: `${device}:${a.agent.shortKey}`,
        role: String(a.agent.role || '').slice(0, 80),
        cardPath: a.paths.dated, cardPathTilde: a.paths.dated.replace(HOME, '~'),
        aliasPathTilde: a.paths.canonical.replace(HOME, '~'),
        cardBytes: a.bytes, cardSha256: a.sha256, state: 'planned',
        events: a.matchedAll.map((m) => ({ id: m.event.id, score: m.score, via: m.via, level: m.level, resource: m.resource, shared: !!m.shared })),
        picked: a.picked.map((m) => m.event.id),
        suppressed: a.suppressed, broadResources: a.broadResources,
        crossDevice: { devices: a.cross.devices.map((d) => d.device), totalOther: a.cross.totalOther },
        distribution: a.distribution, ruleCandidates: a.ruleCands,
        boardKey: deviceCardKey, replyKey: answersKey,
        status: 'local', timestamps: { cardGeneratedAt: new Date().toISOString() },
        machine: a.machine
      });
      result.notices.push({ device, qualified: `${device}:${a.agent.shortKey}`, boardKey: deviceCardKey, notice: notice.text, chars: notice.chars, cardPath: a.paths.dated.replace(HOME, '~') });
    }
  }

  // 7) dry-run：任何写操作之前返回
  if (dryRun) {
    for (const t of result.targets) { t.state = t.machine.state; t.status = 'local'; delete t.machine; }
    result.ok = true;
    result.plan = {
      deviceEnum: devRes.method,
      willWriteFiles: pendingWrites.map((w) => w.absPath.replace(HOME, '~')),
      willPutCentral: sendRequested ? devicePlans.filter((d) => d.deviceCard).map((d) => `${d.deviceCardKey}  ← 正文 ${d.notice.chars} 字：${d.notice.text}`) : [],
      willWriteLedger: `${reflectRoot.replace(HOME, '~')}/dispatch/${dates.compact}/dispatch.json`,
      zeroChange: 'dry-run：未落盘、未写黑板、未写日志（日志行只打印在 stdout）'
    };
    logger.log(`[dry-run] 计划完成 devices=${devicePlans.length} agents=${result.targets.length} files=${pendingWrites.length}（零变更：未写卡 / 未写黑板 / 未落日志）`);
    return result;
  }

  // 8) 落盘（卡 + 别名 + 设备合并卡 + 索引），逐文件回读校验
  for (const w of pendingWrites) {
    fs.mkdirSync(path.dirname(w.absPath), { recursive: true });
    fs.writeFileSync(w.absPath, w.content, 'utf8');
    const back = fs.readFileSync(w.absPath, 'utf8');
    if (sha256(back) !== sha256(w.content)) {
      throw new GateError('CARD_WRITE_MISMATCH', `卡落盘后回读不一致: ${w.absPath}（写 ${charCount(w.content)} 字 / 读 ${charCount(back)} 字）`);
    }
  }
  const nowIso = () => new Date().toISOString();
  for (const d of devicePlans) {
    for (const a of d.agents) {
      a.machine.to('carded');
      const t = result.targets.find((x) => x.device === d.device && x.shortKey === a.agent.shortKey);
      if (t) { t.state = a.machine.state; t.timestamps.cardWrittenAt = nowIso(); t.timestamps.cardReadbackAt = nowIso(); }
    }
    d.status = 'carded';
    logger.log(`卡已落盘 ${d.device}：${d.agents.length} 张 + 设备合并卡`, { dir: path.join(cardsRoot, d.device).replace(HOME, '~') });
  }

  // 9) 派发（可选）：PUT 中央板 + 回读校验 + 在场判定 → delivered / pending
  if (send) {
    for (const d of devicePlans) {
      if (!d.deviceCard) continue;
      assertTargetExists(d.agents[0].agent.agentId, targets.index);        // 入口门：发送前必须能验证目标存在
      assertDeviceSegment(d.deviceCardKey, d.device, devRes.devices);
      const assumeOnline = typeof opts.assumeOnline === 'string'
        ? opts.assumeOnline.split(',').map((x) => x.trim()).filter(Boolean)
        : (Array.isArray(opts.assumeOnline) ? opts.assumeOnline : []);
      const presence = await computePresence(d.device, { dateDashed: dates.dashed, localDevice, assumeOnline });
      const value = {
        device: d.device, date: dates.dashed, type: 'reflect-card-device-merged',
        notice: d.notice.text,
        cardPathLocal: d.deviceCardPath.replace(HOME, '~'),
        agents: d.agents.map((a) => ({
          agentId: a.agent.agentId, shortKey: a.agent.shortKey, qualified: `${d.device}:${a.agent.shortKey}`,
          events: a.picked.map((m) => m.event.id), sha256: a.sha256, notice: d.notice.text
        })),
        answersKey: d.answersKey,
        eventsKey: eventsKeyFor(d.device, dates.dashed),
        cardSha256: d.deviceCardSha,
        generator: `${PLUGIN_NAME} v${VERSION}`,
        generatedAt: nowIso()
      };
      const w = await putAndVerify(d.deviceCardKey, value, PLUGIN_NAME, 'central');   // PUT + 回读比对（失败即抛）
      d.board = { httpStatus: w.httpStatus, seq: w.seq, readbackChars: w.readback.chars, verified: true, writtenAt: w.writtenAt, readbackAt: w.readbackAt };
      d.presence = presence;
      for (const a of d.agents) { a.machine.to('board_written'); a.machine.to('readback_ok'); }
      d.status = resolveStatus(presence.status);                           // delivered | pending（都不是 failed）
      for (const t of result.targets.filter((x) => x.device === d.device)) {
        t.state = 'readback_ok';
        t.status = d.status;
        t.presence = { online: presence.online, signals: presence.signals, note: presence.note };
        t.board = d.board;
        t.timestamps.boardWrittenAt = w.writtenAt;
        t.timestamps.boardReadbackAt = w.readbackAt;
        // Φ13：投递时刻按状态分别标注；pending 明确写"待取起点"，不是失败时刻
        if (d.status === 'delivered') t.deliveredAt = w.readbackAt;
        else t.pendingSince = w.readbackAt;
      }
      logger.log(`派发 ${d.device} → ${d.deviceCardKey} 状态=${d.status}`, { seq: w.seq, noticeChars: d.notice.chars, online: presence.online });
    }
  } else {
    for (const t of result.targets) t.status = 'local';
  }

  // 10) 落链：逐设备卡索引 + 派发台账
  for (const d of devicePlans) {
    for (const a of d.agents) a.machine.to('recorded');
    d.status = resolveStatus(d.status === 'carded' ? 'local' : d.status);
  }
  for (const t of result.targets) t.state = 'recorded';

  for (const d of devicePlans) {
    const cardIndex = {
      tool: PLUGIN_NAME, version: VERSION, device: d.device, date: dates.dashed, generatedAt: nowIso(),
      eventsKey: eventsKeyFor(d.device, dates.dashed), cardKey: d.deviceCardKey, answersKey: d.answersKey,
      eventTotal: d.events.length, eventOrigin: d.entry.origin, profilesSource: targets.source,
      status: d.status, presence: d.presence,
      agents: d.agents.map((a) => ({
        agentId: a.agent.agentId, shortKey: a.agent.shortKey, qualified: `${d.device}:${a.agent.shortKey}`,
        card: `${a.agent.shortKey}.md`, sha256: a.sha256, events: a.picked.map((m) => m.event.id)
      })),
      unassigned: d.attr.unassigned.map((u) => u.id)
    };
    const idxPath = assertDeviceInPath(path.join(cardsRoot, d.device, dates.compact, '_index.json'), d.device, HOME);
    fs.writeFileSync(idxPath, JSON.stringify(cardIndex, null, 2) + '\n', 'utf8');
  }

  const ledgerDir = assertWithinReflectRoot(path.join(reflectRoot, 'dispatch', dates.compact), HOME);
  fs.mkdirSync(ledgerDir, { recursive: true });
  const ledgerPath = path.join(ledgerDir, 'dispatch.json');
  const ledgerOut = {
    ...result,
    targets: result.targets.map((t) => { const c = { ...t }; delete c.machine; return c; }),
    devicePlans: devicePlans.map((d) => ({
      device: d.device, status: d.status, cardKey: d.deviceCardKey, answersKey: d.answersKey,
      eventsKey: eventsKeyFor(d.device, dates.dashed), events: d.events.length,
      agents: d.agents.map((a) => `${d.device}:${a.agent.shortKey}`),
      board: d.board, presence: d.presence, cardSha256: d.deviceCardSha,
      cardPathTilde: d.deviceCardPath ? d.deviceCardPath.replace(HOME, '~') : null
    })),
    logLines: logger.lines, generatedAt: nowIso()
  };
  delete ledgerOut.plan;
  ledgerOut.ledgerPath = ledgerPath.replace(HOME, '~');
  fs.writeFileSync(ledgerPath, JSON.stringify(ledgerOut, null, 2) + '\n', 'utf8');

  const ledgerBack = JSON.parse(fs.readFileSync(ledgerPath, 'utf8'));
  if (!Array.isArray(ledgerBack.targets) || ledgerBack.targets.length !== result.targets.length) {
    throw new GateError('LEDGER_MISMATCH', `台账回读不一致：写 ${result.targets.length} 个目标，回读 ${ledgerBack.targets ? ledgerBack.targets.length : 'n/a'} 个`);
  }
  for (const t of result.targets) delete t.machine;
  result.ledgerPath = ledgerPath;
  result.ledgerPathTilde = ledgerPath.replace(HOME, '~');
  result.ledgerReadback = { ok: true, targets: ledgerBack.targets.length, devices: ledgerBack.devicePlans.length, bytes: fs.statSync(ledgerPath).size };
  result.ok = true;
  const sent = result.targets.filter((t) => t.status === 'delivered').length;
  const pend = result.targets.filter((t) => t.status === 'pending').length;
  logger.log(`完成 devices=${devicePlans.length} cards=${result.targets.length} delivered=${sent} pending=${pend} local=${result.targets.filter((t) => t.status === 'local').length} ledger=${result.ledgerPathTilde}`);
  return result;
}

/**
 * 只读：列出可派目标与它们登记的 resources（供人先看"能不能派、依据是什么"）。
 */
export function listTargets(opts = {}) {
  const targets = loadTargets({ profilesPath: opts.profilesPath });
  const c = localDateCompact();
  const dashed = `${c.slice(0, 4)}-${c.slice(4, 6)}-${c.slice(6, 8)}`;
  const localDevice = resolveLocalDevice(opts.device, opts.hostname || os.hostname());
  return {
    ok: true, source: targets.source, file: targets.file, count: targets.index.size,
    localDevice, candidateDevices: CANDIDATE_DEVICES,
    targets: targets.index.list().map((a) => {
      const atoms = [];
      for (const r of a.resources || []) atoms.push(...normalizeResource(r, HOME));
      return {
        agentId: a.agentId, shortKey: a.shortKey, qualified: `${localDevice}:${a.shortKey}`,
        role: String(a.role || '').slice(0, 100), resources: a.resources,
        resourceAtoms: atoms.length,
        cardKeyToday: cardKeyFor(localDevice, dashed)
      };
    })
  };
}
