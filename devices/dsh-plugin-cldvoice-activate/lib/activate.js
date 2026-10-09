/**
 * activate.js — 激活性重启内核（端口释放检查 + 失败重试 + 健康验证 + 热重启优先）
 * =============================================================================
 * 实证背景（2026-09-10，非推测）：
 *   `launchctl kickstart -k <label>` 是"杀掉并立即重启"。新进程在旧进程 socket
 *   尚未释放时就开始 bind 8903 →
 *       OSError: [Errno 48] Address already in use
 *   表现为 :8902/:8903 未监听、launchd last=1、服务起不来，必须第二次 kickstart 才成功。
 *
 * 本内核把正确顺序固化：SIGTERM（按 label，非 PID） → 等端口释放 → 启动（不带 -k）→ 验证 → 失败重试。
 *
 * 与 R035 的关系（能热重启的，就不要直接杀死整个框架）：
 *   ① 本工具**不具备**任何"杀框架 / 按 PID 杀进程 / 宽杀"的能力：唯一的下杀调用是
 *      `launchctl kill SIGTERM <白名单 label>`；端口未释放时**不做 PID 强杀**，而是重试 + 明确失败。
 *   ② 若后端文件自进程启动后未变（纯前端 client.js 改动），则**直接判定无需重启**，
 *      返回 hot=true，提示刷新页面即可 —— 优先热生效，而不是"重启了事"。
 */
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import net from 'node:net';
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { resolveService, ALLOWED, GateError } from './gate.js';

const pExecFile = promisify(execFile);
// ⑥ 版本管理：单一来源 = package.json（避免 CLI 打印与包版本不一致）
export const VERSION = (() => {
  try { return JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8')).version; }
  catch { return '0.0.0-unknown'; }
})();
export const LOG_FILE = path.join(os.homedir(), 'dsh-collab', 'logs', 'cldvoice-activate.log');

/* ------------------------------ ⑦ 统一日志 ------------------------------ */
export function log(msg, extra) {
  const line = `[${new Date().toISOString()}] ${msg}` + (extra ? ` ${JSON.stringify(extra)}` : '');
  try {
    fs.mkdirSync(path.dirname(LOG_FILE), { recursive: true });
    fs.appendFileSync(LOG_FILE, line + '\n');
  } catch { /* 日志失败不阻塞主流程 */ }
  return line;
}

/* ------------------------------ 基础探测 ------------------------------ */
export function portListening(port, timeoutMs = 800) {
  return new Promise((resolve) => {
    const sock = net.connect({ host: '127.0.0.1', port });
    const done = (v) => { try { sock.destroy(); } catch {} resolve(v); };
    sock.setTimeout(timeoutMs);
    sock.once('connect', () => done(true));
    sock.once('timeout', () => done(false));
    sock.once('error', () => done(false));
  });
}

export async function listeners(ports) {
  const out = {};
  for (const p of ports) out[p] = (await portListening(p)) ? 'listening' : 'free';
  return out;
}

export function healthOk(url, timeoutMs = 4000) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: timeoutMs }, (res) => {
      let body = '';
      res.on('data', (c) => { body += c; });
      res.on('end', () => {
        const ok = /"ok"\s*:\s*true/.test(body) || /"status"\s*:\s*"ok"/.test(body);
        resolve({ ok, status: res.statusCode, body: body.slice(0, 200) });
      });
    });
    req.on('timeout', () => { req.destroy(); resolve({ ok: false, status: 0, body: 'timeout' }); });
    req.on('error', (e) => resolve({ ok: false, status: 0, body: String(e.message || e) }));
  });
}

export async function launchctlList() {
  try {
    const { stdout } = await pExecFile('launchctl', ['list'], { timeout: 10000 });
    const map = {};
    for (const line of stdout.split('\n')) {
      const m = line.trim().split(/\s+/);
      if (m.length >= 3) map[m[2]] = { pid: m[0], last: m[1] };
    }
    return map;
  } catch { return {}; }
}

export async function serviceState(key) {
  const svc = resolveService(key);
  const map = await launchctlList();
  const entry = map[svc.label] || { pid: '-', last: '-' };
  const listenersMap = await listeners(svc.ports);
  const health = await healthOk(svc.health);
  return { key: svc.key, label: svc.label, launchdPid: entry.pid, lastExit: entry.last, ports: listenersMap, health };
}

/* ------------------------------ 热重启优先 ------------------------------ */
/**
 * 后端是否需要重启：比较后端文件 mtime 与进程启动时刻。
 * 全部后端文件都早于进程启动 → 运行中已是当前代码 → 无需重启（前端改动只需刷新页面）。
 */
export function backendRestartNeeded(key, opts = {}) {
  const svc = resolveService(key);
  const backendDir = opts.backendDir || path.join(os.homedir(), 'dsh-collab', 'cld-voice', 'backend');
  const startedAt = opts.processStartedAt; // ms
  if (!startedAt) return { needed: true, reason: '无法确定进程启动时刻 → 保守判定需要重启' };
  const stale = [];
  for (const f of svc.backendFiles) {
    const fp = path.join(backendDir, f);
    try {
      const st = fs.statSync(fp);
      if (st.mtimeMs > startedAt) stale.push({ file: f, mtime: new Date(st.mtimeMs).toISOString() });
    } catch { /* 文件不存在不阻塞 */ }
  }
  return stale.length
    ? { needed: true, reason: '后端文件晚于进程启动（运行的是旧代码）', stale }
    : { needed: false, reason: '后端文件均早于进程启动 → 运行中已是当前代码，热生效即可（刷新页面）', stale: [] };
}

export async function processStartedAt(pid) {
  if (!pid || pid === '-') return null;
  try {
    const { stdout } = await pExecFile('ps', ['-o', 'lstart=', '-p', String(pid)], { timeout: 5000 });
    const d = new Date(stdout.trim());
    return isNaN(d.getTime()) ? null : d.getTime();
  } catch { return null; }
}

/* ------------------------------ 主流程 ------------------------------ */
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitPortsFree(svc, timeoutSec) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutSec * 1000) {
    const m = await listeners(svc.ports);
    if (Object.values(m).every((v) => v === 'free')) return { ok: true, waitedSec: Math.round((Date.now() - t0) / 1000) };
    await sleep(1000);
  }
  const m = await listeners(svc.ports);
  return { ok: false, waitedSec: timeoutSec, ports: m };
}

async function waitReady(svc, timeoutSec) {
  const t0 = Date.now();
  let listeningAll = false;
  while (Date.now() - t0 < timeoutSec * 1000) {
    const m = await listeners(svc.ports);
    listeningAll = Object.values(m).every((v) => v === 'listening');
    if (listeningAll) {
      const h = await healthOk(svc.health);
      if (h.ok) return { ok: true, waitedSec: Math.round((Date.now() - t0) / 1000), health: h };
    }
    await sleep(1000);
  }
  const h = await healthOk(svc.health);
  return { ok: false, waitedSec: timeoutSec, listeningAll, health: h };
}

/**
 * 激活单个服务（键必须来自冻结白名单）
 *
 * 顺序（v1.0.1 修正，2026-09-10 由本工具自己的日志证明初版模型是错的）：
 *   初版要求"端口必须先释放才启动"，但这两个服务是 **KeepAlive=true**：
 *   SIGTERM 之后 launchd 会立刻自动拉起 → 端口从未空过 →
 *   初版对 voice-service 连续 3 次判定"端口未释放"最终**报假失败**（服务其实一直健康），
 *   对 cld-voice 则第 1 次真失败、第 2 次才成功。
 *   结论：在 KeepAlive 下，**"端口释放"不是前置条件，只是症状**；正确的编排原语是
 *   `kickstart -k`（原子重启，且与 KeepAlive 共存），判据是**重启后的就绪**（端口在听 + 健康端点）。
 *   端口占用信息降级为"重试时的诊断信息"，并新增"服务已自愈→判成功"以避免假失败。
 *
 * @returns {Promise<object>} 结构化结果（供 CLI 与工具共用）
 */
export async function activateService(key, opts = {}) {
  const svc = resolveService(key);           // ① 门：不通过的输入在此终止，任何副作用之前
  const domain = opts.domain || `gui/${process.getuid?.() ?? 501}`;
  const retries = Number.isInteger(opts.retries) ? opts.retries : 3;
  const bootWait = opts.bootWaitSeconds ?? 25;
  const dryRun = opts.dryRun === true;
  const force = opts.force === true;

  const before = await serviceState(svc.key);
  log(`activate 开始 ${svc.key}`, { label: svc.label, dryRun, retries });

  // ② 热重启优先：后端未变且服务健康 → 不重启（R035）
  if (!force && !dryRun && before.health.ok && before.launchdPid !== '-') {
    const startedAt = await processStartedAt(before.launchdPid);
    const chk = backendRestartNeeded(svc.key, { ...opts, processStartedAt: startedAt });
    if (!chk.needed) {
      log(`activate 判定无需重启 ${svc.key}：${chk.reason}`);
      return { ok: true, hot: true, key: svc.key, label: svc.label, reason: chk.reason, before, restarted: false };
    }
  }

  if (dryRun) {
    log(`activate [dry-run] ${svc.key}：将 kickstart -k → 等就绪(${bootWait}s) + 健康探针（失败则重试，最多 ${retries} 次）`);
    return {
      ok: true, hot: false, dryRun: true, key: svc.key, label: svc.label,
      plan: {
        restart: `launchctl kickstart -k ${domain}/${svc.label}`,
        waitReadySec: bootWait, retries,
        verify: { ports: svc.ports, health: svc.health },
        note: 'KeepAlive=true 时端口不会空出来；本工具不等待端口释放，只验证重启后就绪'
      },
      before, restarted: false
    };
  }

  const attempts = [];
  for (let attempt = 1; attempt <= retries; attempt++) {
    const entry = { attempt };

    // 三步：原子重启（-k = 停+起，与 KeepAlive 共存）
    try {
      await pExecFile('launchctl', ['kickstart', '-k', `${domain}/${svc.label}`], { timeout: 10000 });
      entry.kickstart = 'ok (-k)';
    } catch (e) {
      entry.kickstart = `-k 失败(${String(e.message || e).slice(0, 60)}) → 回退 kill+start`;
      try { await pExecFile('launchctl', ['kill', 'SIGTERM', `${domain}/${svc.label}`], { timeout: 8000 }); } catch {}
      await sleep(1500);
      try { await pExecFile('launchctl', ['kickstart', `${domain}/${svc.label}`], { timeout: 10000 }); entry.kickstart += ' → start ok'; }
      catch (e2) { entry.kickstart += ` → start 失败(${String(e2.message || e2).slice(0, 60)})`; }
    }

    // 判据：重启后就绪（端口在听 + 健康端点 ok）
    const ready = await waitReady(svc, bootWait);
    const after = await serviceState(svc.key);
    entry.ready = ready;
    entry.after = { launchdPid: after.launchdPid, lastExit: after.lastExit, ports: after.ports, health: after.health };
    if (ready.ok) {
      entry.result = 'ok';
      attempts.push(entry);
      log(`activate 成功 ${svc.key}`, { attempt, waitedSec: ready.waitedSec, pid: after.launchdPid });
      return { ok: true, hot: false, key: svc.key, label: svc.label, restarted: true, attempts, after };
    }

    // 未就绪：记录诊断（端口占用属"症状信息"，不是"前置条件"）
    const portState = await listeners(svc.ports);
    entry.result = 'not-ready';
    entry.diagnostic = { ports: portState, lastExit: after.lastExit, health: after.health.body };
    attempts.push(entry);
    log(`activate 第 ${attempt} 次未通过 ${svc.key}`, entry.diagnostic);
    await sleep(2000);
  }

  const after = await serviceState(svc.key);
  // 最后再看一眼：KeepAlive 可能在我们放弃后自愈 → 不报假失败
  if (after.health.ok) {
    log(`activate 收尾复核：${svc.key} 已自愈（KeepAlive）→ 判成功`);
    return { ok: true, hot: false, selfHealed: true, key: svc.key, label: svc.label, restarted: true, attempts, after };
  }
  log(`activate 失败 ${svc.key}：连续 ${retries} 次未就绪`);
  return {
    ok: false, hot: false, key: svc.key, label: svc.label, restarted: false, attempts, after,
    diagnosis: {
      lastExit: after.lastExit,
      hint: `查日志：~/dsh-collab/logs/${svc.key}.launchd.err（Errno 48=端口仍被占；本工具已含重启+重试+自愈复核）`
    }
  };
}
