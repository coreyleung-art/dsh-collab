/**
 * board.js — 黑板 IO（唯一出站通道，两块板：本机 + 中央）
 * =============================================================================
 * 结构约束（不是纪律）：
 *   ① 主机来自**冻结常量** BOARD_TARGETS（local / central），且**没有环境变量入口**
 *      —— "把卡派到别的服务器"无法表达；加第三个板必须改代码。
 *   ② PUT 之后**必须**紧跟一次 GET 回读并逐字节比对（gate.assertReadback）——
 *      这是 R003 的硬要求，也是本工具封堵"假装派发了"的那道门。
 *      实测背景（2026-09-10）：已有 4 次"报告指向不存在的落盘物"，都是把
 *      "写入返回非 200"当成成功；400=写法非法、404=不存在，二者都不得当成功。
 *   ③ 跨设备层新增 listKeys()，但它**如实标注自己的局限** ——
 *      实测中央黑板 `GET /data/reflect/events/` 并不做前缀过滤（返回整个 data 命名空间，
 *      14.8MB / 57 键；`?limit=` 只是截断前 N 条），所以本工具**不把列举结果当作
 *      "全设备清单"**，只当辅助证据；权威枚举走 data/reflect/devices 索引 + 冻结候选探测。
 */
import http from 'node:http';
import { GateError, BOARD_TARGETS, ALLOWED_HOSTS, assertReadback, assertBoardKey, assertTargetName, isEmptyShell } from './gate.js';

const BB_TIMEOUT_MS = 8000;

export const BB_URLS = BOARD_TARGETS;

function parseBase(target) {
  const name = assertTargetName(target);
  const url = BOARD_TARGETS[name];
  const m = String(url).match(/^http:\/\/([^/]+)(\/.*)?$/);
  if (!m) throw new GateError('BB_URL_INVALID', `黑板地址非法: ${url}`);
  const [host, port] = m[1].split(':');
  if (!ALLOWED_HOSTS.includes(`${host}:${port || '80'}`)) {
    throw new GateError('BB_HOST_FORBIDDEN',
      `拒绝：出站主机 ${host}:${port} 不在白名单 [${ALLOWED_HOSTS.join(', ')}] 内（闸门在发起连接之前）。`);
  }
  return { name, host, port: Number(port || 80), prefix: m[2] || '' };
}

function rawRequest(method, pathname, body, writer, target) {
  const { host, port } = parseBase(target);
  const payload = body === undefined ? null : Buffer.from(JSON.stringify(body), 'utf8');
  const headers = { Accept: 'application/json' };
  if (payload) {
    headers['Content-Type'] = 'application/json';
    headers['Content-Length'] = String(payload.length);
  }
  if (writer) headers['X-Writer'] = String(writer);
  return new Promise((resolve, reject) => {
    const req = http.request({ host, port, path: pathname, method, headers, timeout: BB_TIMEOUT_MS }, (res) => {
      let data = '';
      res.setEncoding('utf8');
      res.on('data', (c) => { data += c; });
      res.on('end', () => {
        let doc = null;
        try { doc = data ? JSON.parse(data) : null; } catch { doc = { raw: data.slice(0, 400) }; }
        // reqBytes = 请求体长度；respBytes = 响应体长度（两个都要，别把 GET 的响应说成 0）
        resolve({ status: res.statusCode, doc, reqBytes: payload ? payload.length : 0, respBytes: Buffer.byteLength(data, 'utf8') });
      });
    });
    req.on('timeout', () => { req.destroy(); reject(new GateError('BB_TIMEOUT', `黑板[${target}] ${method} ${pathname} 超时 ${BB_TIMEOUT_MS}ms`)); });
    req.on('error', (e) => reject(new GateError('BB_ERROR', `黑板[${target}] ${method} ${pathname} 失败: ${String(e.message || e)}`)));
    if (payload) req.write(payload);
    req.end();
  });
}

function keyed(method, key, body, writer, target) {
  const k = assertBoardKey(key);
  const { prefix } = parseBase(target);
  return rawRequest(method, `${prefix}/${k}`, body, writer, target);
}

/** 只读取键：不存在 / 400 / 404 → null（调用方自行判断，不冒充内容）。 */
export async function bbGet(key, target = 'local') {
  try {
    const r = await keyed('GET', key, undefined, undefined, target);
    if (r.status !== 200) return null;
    if (!r.doc || typeof r.doc !== 'object') return null;
    return Object.prototype.hasOwnProperty.call(r.doc, 'value') ? r.doc.value : r.doc;
  } catch { return null; }
}

/** 只读取整卡（含 seq/ts，用于台账与"存在性探测"）。 */
export async function bbGetDoc(key, target = 'local') {
  try {
    const r = await keyed('GET', key, undefined, undefined, target);
    return r.status === 200 ? r.doc : { status: r.status };
  } catch (e) { return { status: 0, error: String(e.message || e) }; }
}

/**
 * 设备/键存在性探测：返回 {exists, status, ts, emptyShell, ...}。
 * ★ 语义区分（实测）：200=存在 · 404=格式合法但不存在 · 400=键写法非法。
 *   这三者绝不合并成一个布尔值 —— 400 与 404 含义完全不同（一个是我写错了，一个是还没写）。
 * ★★ `exists` 是**内容口径**，不是状态码口径（R003 补充通告 2026-09-11 第 ③ 条）：
 *   实测某个键 HTTP 200、带 ts/version，但 `value={}` —— 纯状态码校验会把它当成"存在"，
 *   于是"该设备当天上报过事件""在场"这类结论就被空壳满足了。现在：
 *     · `httpStatus200` = 状态码口径（写法对且键在）
 *     · `emptyShell`    = 内容是空壳（null/{} /[] /空白串）
 *     · `exists`        = 200 **且** 内容非空  ← 业务判定用这个
 *   二者都返回，谁用哪一个是显式的，不靠猜。
 */
export async function probeKey(key, target = 'local') {
  const doc = await bbGetDoc(key, target);
  const status = doc && typeof doc.status === 'number' ? doc.status : (doc ? 200 : 0);
  const httpStatus200 = status === 200;
  const value = httpStatus200 && doc && typeof doc === 'object' && Object.prototype.hasOwnProperty.call(doc, 'value') ? doc.value : undefined;
  const emptyShell = httpStatus200 && isEmptyShell(value);
  return {
    key, target,
    exists: httpStatus200 && !emptyShell,        // ← 内容口径（业务判定用这个）
    httpStatus200,
    emptyShell,
    status,
    ts: (doc && doc.ts) || null,
    error: (doc && doc.error) || null
  };
}

/**
 * 写入并**验证**：PUT → 立即 GET → assertReadback 逐字节比对。
 * 任一步不符 → 抛 GateError（readback 失败即派发失败，绝不报成功）。
 */
export async function putAndVerify(key, value, writer, target = 'local') {
  const k = assertBoardKey(key);
  const t0 = new Date().toISOString();
  const put = await keyed('PUT', k, value, writer, target);
  if (put.status !== 200) {
    throw new GateError('BB_WRITE_REJECTED',
      `黑板[${target}] 拒绝写入 ${k}：HTTP ${put.status} ${JSON.stringify(put.doc).slice(0, 160)}` +
      '（400=键写法非法 / 404=路径不存在，均不得当成功）');
  }
  const got = await bbGet(k, target);
  const rb = assertReadback(value, got, k);        // ← 门在这里：回读不一致就抛
  const t1 = new Date().toISOString();
  const seq = put.doc && typeof put.doc === 'object' ? (put.doc.seq ?? null) : null;
  return { ok: true, key: k, target, httpStatus: put.status, seq, readback: rb, reqBytes: put.reqBytes, writtenAt: t0, readbackAt: t1 };
}

/**
 * 命名空间列举（**非权威**，见文件头 ③）。
 * @returns {{supported:boolean, keys:string[], total:number|null, bytes:number, note:string}}
 */
export async function listKeys(ns = 'data', target = 'central', limit = 500) {
  try {
    const { prefix } = parseBase(target);
    const r = await rawRequest('GET', `${prefix}/${ns}/?limit=${Number(limit)}`, undefined, undefined, target);
    if (r.status !== 200 || !r.doc || typeof r.doc !== 'object' || !r.doc.list) {
      return { supported: false, keys: [], total: null, bytes: 0, note: `列举失败：HTTP ${r.status}` };
    }
    const keys = Object.keys(r.doc.list);
    const total = typeof r.doc.total === 'number' ? r.doc.total : null;
    // ★ 关键区分（首版结论下得太重，被自己的复核纠正）：
    //   · 该接口**不做前缀过滤**（/data/reflect/events/ 返回整个 ns）—— 这没错；
    //   · 但 `limit >= total` 时返回的就是**该命名空间的完整键集**，此时按前缀过滤**是有效的**；
    //   · 只有 `keys.length < total`（被截断）时才**不可**当好清单。
    const complete = total !== null && keys.length >= total;
    return {
      supported: true, keys, total, complete, respBytes: r.respBytes || 0,
      note: complete
        ? `GET /${ns}/?limit=${limit} 返回 **${keys.length}/${total} 键 = 完整键集**（响应 ${r.respBytes} 字节）：该接口不做前缀过滤，但**集合完整**，故按前缀过滤是**有效**的`
        : `GET /${ns}/?limit=${limit} 只返回 ${keys.length}/${total} 键 = **被截断**：此时**不能**当作全设备清单（需提高 limit 或改用探测法）`
    };
  } catch (e) {
    return { supported: false, keys: [], total: null, complete: false, respBytes: 0, note: `列举异常：${String(e.message || e)}` };
  }
}

/** 时间轴最大 seq（只读；用于零变更证明）。 */
export async function bbMaxSeq(target = 'local') {
  try {
    const { host, port, prefix } = parseBase(target);
    return await new Promise((resolve) => {
      const req = http.request({ host, port, path: `${prefix}/timeline?since_seq=0&limit=1`, method: 'GET', timeout: 4000 }, (res) => {
        let d = ''; res.setEncoding('utf8');
        res.on('data', (c) => { d += c; });
        res.on('end', () => {
          try {
            const j = JSON.parse(d);
            const arr = Array.isArray(j) ? j : (j.events || j.list || []);
            const seqs = arr.map((e) => Number(e && e.seq)).filter(Number.isFinite);
            resolve(seqs.length ? Math.max(...seqs) : 0);
          } catch { resolve(0); }
        });
      });
      req.on('timeout', () => { req.destroy(); resolve(0); });
      req.on('error', () => resolve(0));
      req.end();
    });
  } catch { return 0; }
}

/** 黑板可达性（只读；TCC 自检用它如实报告"中央板此刻通不通"）。 */
export async function ping(target = 'local') {
  try {
    const { prefix } = parseBase(target);
    const r = await rawRequest('GET', `${prefix}/`, undefined, undefined, target);
    return { target, ok: r.status === 200 || r.status === 400, status: r.status };
  } catch (e) {
    return { target, ok: false, status: 0, error: String(e.message || e) };
  }
}
