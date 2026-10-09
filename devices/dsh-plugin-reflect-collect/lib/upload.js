/**
 * upload.js — 跨设备上传 + 回读校验（design v1.1 §10.2 / §10.6 ①）
 * =============================================================================
 * 全包**唯一**允许"上传"这一动作的模块（`UPLOADER_MODULES = ['lib/upload.js']`）。
 * 它做三件事，缺一不可：
 *   1) 目标由**冻结构造器**拼出：`buildUploadUrl(device, date)` → `/data/reflect/events/<device>/<date>`
 *      （device 与 date 都先过门；origin 冻结为中央实例 —— 没有"换一个黑板"的参数）；
 *   2) **写入前脱敏**（凭据扫描，`redactPayload`）——本地落盘与上传共用同一份 payload，
 *      因此不存在"本地脱敏了、上传没脱敏"的路径；
 *   3) **写入后回读校验**：PUT 必须 200，且 GET 同 key 的 sha256 必须与上传内容一致
 *      （已知纪律：写入返回非 200 不能假定成功 —— 本日已发生 4 次"报告指向不存在的落盘物"）。
 */

import { buildUploadKey, buildUploadUrl, redactSecrets, sha256Hex, canonicalSha256, verifyReadback } from './gate.js';
import { httpGetJson, httpPutJson } from './transport.js';

/**
 * 凭据扫描 + 脱敏（同一份 payload 用于本地落盘与上传）。
 * @returns {{payload:object, text:string, secrets_redacted:number, byPattern:object}}
 */
export function redactPayload(payload, { allowSecrets = false } = {}) {
  const text = JSON.stringify(payload, null, 1);
  if (allowSecrets) return { payload, text, secrets_redacted: 0, byPattern: {}, bypassed: true };
  const r = redactSecrets(text);
  if (r.count === 0) return { payload, text, secrets_redacted: 0, byPattern: {}, bypassed: false };
  let parsed;
  try { parsed = JSON.parse(r.text); } catch { parsed = payload; }
  return { payload: parsed, text: r.text, secrets_redacted: r.count, byPattern: r.byPattern, bypassed: false };
}

/**
 * 黑板某个 key 的当前状态（只读；dry-run 零变更证据 + 可达性探测用）。
 * ★ R003 通告 v2 rule_2/rule_4 采纳：
 *   · **四态**而不是布尔 —— `present` / `absent`(404) / `bad-key`(400) / `unreachable`(网络或 5xx)。
 *     400=键写法非法、404=格式合法但不存在，二者语义不同，合并成 `exists:false` 会掩盖"键写错了"。
 *   · **有界探测**：探测可达性时必须带 `?limit=N`。实测：任何以 `/` 结尾的路径都返回同一份
 *     全量列举（本机 36.59MB / 20220 键），小工具会 OOM；`/data/?limit=1` 只要 120 字节。
 */
export async function centralKeyState(url, { timeoutMs = 12000, maxBytes = 96 * 1024 * 1024 } = {}) {
  try {
    const r = await httpGetJson(url, { timeoutMs, maxBytes });
    return { kind: 'present', exists: true, status: 200, sha256: r.sha256, bytes: Buffer.byteLength(r.text) };
  } catch (e) {
    const status = e.status || null;
    const err = String(e.message || e).split('\n')[0];
    if (status === 404) return { kind: 'absent', exists: false, status: 404, sha256: null, bytes: 0, error: err };
    if (status === 400) {
      return { kind: 'bad-key', exists: null, status: 400, sha256: null, bytes: 0, error: err, hint: '键写法非法（首段须 [a-z]+；后续段 [A-Za-z0-9._-]；不得有空段）' };
    }
    return { kind: 'unreachable', exists: null, status, sha256: null, bytes: 0, error: err };
  }
}

/** 有界可达性探测（rule_4：绝不为了"探活"拉全量列举）。 */
export async function boardReachable(base, { timeoutMs = 10000 } = {}) {
  const url = `${String(base).replace(/\/$/, '')}/data/?limit=1`;
  const r = await centralKeyState(url, { timeoutMs, maxBytes: 4 * 1024 * 1024 });
  // 探测的是"黑板块本身是否活着"，不是"某个 key 存在"——故把 present 改判为 reachable（语义不混用）
  return r.kind === 'present' ? { ...r, kind: 'reachable' } : r;
}

/**
 * 上传事件流到中央黑板，并**回读校验**。
 * @returns {Promise<object>} {attempted, ok, key, url, putStatus, readbackStatus, expectedSha256, readbackSha256, reason}
 */
export async function uploadEvents({ device, date, text, dryRun = false, timeoutMs = 30000 }) {
  const key = buildUploadKey(device, date);
  const url = buildUploadUrl(device, date);
  // 判据用**规范化** sha256（键序/空白无关）；原文 sha256 只作诊断（黑板会重新序列化为卡片信封）
  const expectedSha256 = canonicalSha256(JSON.parse(text));
  const rawSha256 = sha256Hex(text);
  if (dryRun) {
    // dry-run：**不发 PUT**（结构上由本分支保证），但仍给出"如果上传会是什么 sha256"
    return { attempted: false, ok: true, dryRun: true, key, url, expectedSha256, rawSha256, reason: 'dry-run：未上传（零字节变更）' };
  }

  let putStatus = null;
  let putBody = '';
  try {
    const r = await httpPutJson(url, text, { timeoutMs });
    putStatus = r.status;
    putBody = r.text;
  } catch (e) {
    return {
      attempted: true, ok: false, key, url, putStatus: e.status || null, error: String(e.message || e).split('\n')[0],
      expectedSha256, reason: `PUT 失败: ${String(e.message || e).split('\n')[0]}`
    };
  }

  // ★ 回读校验：不信 200，信"同 key 读回来是不是同一份内容（规范化后）"
  let readbackStatus = null, readbackSha256 = null, readbackKey = null;
  try {
    const rb = await httpGetJson(url, { timeoutMs });
    readbackStatus = 200;
    readbackKey = rb.json && rb.json.key !== undefined ? rb.json.key : key;
    // 黑板存储形态：卡片信封 {key,ts,value,version}；取 value 与上传载荷规范化后比对
    const stored = rb.json && rb.json.value !== undefined ? rb.json.value : rb.json;
    readbackSha256 = canonicalSha256(stored);
  } catch (e) {
    readbackStatus = e.status || null;
  }
  const verdict = verifyReadback({ putStatus, expectedSha256, readbackStatus, readbackSha256, expectedKey: key, readbackKey });
  return {
    attempted: true, ok: verdict.ok, key, url,
    putStatus, putBody: putBody.slice(0, 200),
    readbackStatus, readbackKey, expectedSha256, readbackSha256, rawSha256,
    reason: verdict.reason
  };
}
