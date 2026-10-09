/**
 * transport.js — 唯一的 HTTP 传输模块（R006 ⑩「没有那个能力」在网线上的落地）
 * =============================================================================
 * 本文件是全包**唯一**出现 `http.request` 的地方，且只导出两个函数：
 *   · httpGetJson(url)       —— 读。目标必须过 `assertReadTarget`
 *   · httpPutJson(url, body) —— 写。目标必须过 `assertBoardUpload`
 * 两个函数的门都在**发起请求之前**执行（失败即停），方法字面量写死在各自函数里，
 * 调用方**没有传 method 的口子** —— "用别的方法打别的主机"在结构上无法表达。
 *
 * 本文件不含任何本地文件写入/删除原语（writeFileSync/mkdirSync/… 一个都没有）。
 */

import http from 'node:http';
import crypto from 'node:crypto';
import { assertBoardUpload, assertReadTarget } from './gate.js';

const net = { gets: 0, puts: 0, nonGetAttempts: 0, bytesIn: 0 };
export function networkStats() { return { ...net }; }

function request({ url, method, body, timeoutMs, maxBytes }) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const payload = body === undefined || body === null ? null : Buffer.from(String(body), 'utf8');
    const headers = { accept: 'application/json' };
    if (payload) {
      headers['content-type'] = 'application/json';
      headers['content-length'] = String(payload.length);
    }
    const req = http.request({
      protocol: 'http:', hostname: u.hostname, port: u.port || 80,
      path: u.pathname + (u.search || ''), method, headers, timeout: timeoutMs
    }, (res) => {
      const chunks = []; let size = 0;
      res.on('data', (c) => {
        size += c.length;
        if (size > maxBytes) { req.destroy(new Error(`响应超过 ${maxBytes} 字节上限`)); return; }
        chunks.push(c);
      });
      res.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf8');
        net.bytesIn += Buffer.byteLength(text);
        resolve({ status: res.statusCode, text, sha256: crypto.createHash('sha256').update(text, 'utf8').digest('hex') });
      });
    });
    req.on('timeout', () => req.destroy(new Error(`请求超时 ${timeoutMs}ms`)));
    req.on('error', (e) => reject(e));
    if (payload) req.write(payload);
    req.end();
  });
}

/** 读（GET）。目标白名单：环回 /data/ 与 /notes/；中央仅 /data/reflect/ 前缀。 */
export async function httpGetJson(url, { timeoutMs = 25000, maxBytes = 256 * 1024 * 1024 } = {}) {
  assertReadTarget(url);              // ← 门（GET + 主机 + 路径）
  net.gets += 1;
  const r = await request({ url, method: 'GET', timeoutMs, maxBytes });
  if (r.status !== 200) { const e = new Error(`HTTP ${r.status} ${new URL(url).pathname}`); e.status = r.status; throw e; }
  try { return { json: JSON.parse(r.text), sha256: r.sha256, text: r.text }; }
  catch (e) { throw new Error(`JSON 解析失败: ${e.message}`); }
}

/** 写（PUT）——本工具**唯一**的写黑板动作，目标只有一个冻结 key 形态。 */
export async function httpPutJson(url, body, { timeoutMs = 30000, maxBytes = 8 * 1024 * 1024 } = {}) {
  assertBoardUpload('PUT', url);      // ← 门（PUT + 中央主机 + key 形态）
  net.puts += 1;
  return request({ url, method: 'PUT', body, timeoutMs, maxBytes });
}
