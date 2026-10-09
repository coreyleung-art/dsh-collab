/**
 * devices.js — 设备名解析与设备表（跨设备层的入口）
 * =============================================================================
 * 为什么单独一个模块：设备名是**黑板 key 的一个路径段**，也是 `recurrence` 的聚合维度。
 * 它错了，整条跨设备链就错了 —— 而且错得很安静（回填被算到别的设备头上，或同一台被算两次）。
 * 所以：设备名有**格式门**（黑板 key 语法 + 文件系统安全），设备表有**显式来源**（绝不隐式猜）。
 *
 * 设备表来源优先级（每一步都写进输出，不留隐式行为）：
 *   1) `--devices a,b,c`                      —— 显式，最高优先
 *   2) `~/dsh-collab/data/reflect/devices.json` 的 `devices` 数组（上游 collect/dispatch 可写；本工具只读）
 *   3) 冻结默认表 DEFAULT_DEVICES（并在 notes 里说明"用了默认表"）
 *
 * 本机设备名（用于把"没有 <device> 段的老布局目录"归到谁名下）：
 *   1) `--device <name>`  2) env REFLECT_DEVICE / DSH_DEVICE
 *   3) registry 的 `local`  4) 主机名小写（并在 notes 里提示可能不在规范设备表内）
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export const COLLAB_ROOT = path.join(os.homedir(), 'dsh-collab');

/** 冻结默认设备表（来自 docs/daily-reflection-pipeline-design-v1.md §10.1） */
export const DEFAULT_DEVICES = Object.freeze(['mac-mini', 'mbp', 'i9']);

/** 设备名格式门：首字符字母数字，其余 [a-z0-9._-]，≤32；**不含 `/`、`..`、空白**（黑板 key 段 + 路径段双安全） */
export const DEVICE_NAME_RE = /^[a-z0-9][a-z0-9._-]{0,31}$/;

export const REGISTRY_PATH = path.join(COLLAB_ROOT, 'data', 'reflect', 'devices.json');

export class DeviceError extends Error {
  constructor(code, message) { super(message); this.name = 'DeviceError'; this.code = code; }
}

/** 归一化设备名（小写、去空白）。不合法 → 抛 DeviceError（失败即停，不静默改名） */
export function normalizeDevice(input) {
  if (input === undefined || input === null || String(input).trim() === '') {
    throw new DeviceError('EMPTY_DEVICE', '设备名为空。');
  }
  const d = String(input).trim().toLowerCase();
  if (!DEVICE_NAME_RE.test(d)) {
    throw new DeviceError('BAD_DEVICE_NAME',
      `非法设备名 '${input}'：只允许 [a-z0-9][a-z0-9._-]{0,31}（小写字母开头）。` +
      `设备名会进黑板 key 路径段与本地目录，含 '/' 、'..' 、空白或大写都会被拒绝。`);
  }
  return d;
}

function readRegistry(registryPath) {
  try {
    const j = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
    return { ok: true, data: j };
  } catch (e) {
    return { ok: false, error: `${e.code || e.name}: ${e.message}` };
  }
}

/**
 * 解析设备表。
 * @returns {{devices:string[], source:string, localDevice:string, localSource:string, registryPath:string, notes:string[]}}
 */
export function resolveDevices(opts = {}) {
  const notes = [];
  const registryPath = opts.registryPath || REGISTRY_PATH;
  const reg = readRegistry(registryPath);
  const regData = reg.ok && reg.data && typeof reg.data === 'object' ? reg.data : null;
  if (!reg.ok) notes.push(`设备表文件不可读（${reg.error}）→ ${registryPath}`);
  else if (!regData) notes.push(`设备表文件内容不是对象 → ${registryPath}`);

  // ── 设备列表
  let devices, source;
  if (Array.isArray(opts.devices) && opts.devices.length) {
    devices = opts.devices.map(normalizeDevice);
    source = 'cli:--devices';
  } else if (regData && Array.isArray(regData.devices) && regData.devices.length) {
    devices = regData.devices.map(normalizeDevice);
    source = `registry:${registryPath}`;
  } else {
    devices = [...DEFAULT_DEVICES];
    source = 'frozen:DEFAULT_DEVICES';
    notes.push(`未指定 --devices 且无 devices.json → 使用冻结默认设备表 [${devices.join(', ')}]（会在输出里如实标注来源）`);
  }
  devices = [...new Set(devices)]; // 去重，保序

  // ── 本机设备名
  let localDevice, localSource;
  const hostShort = os.hostname().split('.')[0].toLowerCase();
  if (opts.localDevice) { localDevice = normalizeDevice(opts.localDevice); localSource = 'cli:--device'; }
  else if (process.env.REFLECT_DEVICE) { localDevice = normalizeDevice(process.env.REFLECT_DEVICE); localSource = 'env:REFLECT_DEVICE'; }
  else if (process.env.DSH_DEVICE) { localDevice = normalizeDevice(process.env.DSH_DEVICE); localSource = 'env:DSH_DEVICE'; }
  else if (regData && regData.local) { localDevice = normalizeDevice(regData.local); localSource = 'registry:local'; }
  else { localDevice = normalizeDevice(hostShort); localSource = 'os.hostname()'; }

  if (!devices.includes(localDevice)) {
    notes.push(`本机设备名 '${localDevice}'（来源 ${localSource}）不在设备表 [${devices.join(', ')}] 内 —— ` +
      `老布局目录（answers/<date>/ 无设备段）仍会归到它名下；建议在 ${registryPath} 里显式登记设备的规范名。`);
  }
  return { devices, source, localDevice, localSource, registryPath, notes };
}

/* ------------------- 设备名门负例 / 正例（供 --lean4-check 实测） ------------------- */

/** 负例：路径穿越 / 黑板 key 语法非法 / 空值 —— **必须全部被拒** */
export function deviceNegativeCases() {
  const attempts = [
    '..', '../mbp', '../../etc/passwd', 'mac-mini/../mbp', 'mac mini',
    '', '   ', 'a'.repeat(33), '-mbp', '.hidden', '.', 'mbp\x00',
    'mbp/2026-09-10', 'data/reflect/answers', null, undefined
  ];
  return attempts.map((input) => {
    try { normalizeDevice(input); return { input: String(input), code: null }; }
    catch (e) { return { input: String(input), code: e.code || 'ERROR' }; }
  });
}

/**
 * 正例：合法设备名必须可用（防「门太宽把功能也砍了」）。
 * 含两条**易被误判为非法**的合法情形（本工具开发中我自己就把它们错列进了负例）：
 *   - `MAC-MINI` → 大小写归一化为 `mac-mini`（设备名大小写不敏感，归一化是有意行为）
 *   - `42`      → 纯数字设备名合法（正则只要求首字符是字母数字）
 * 说明：这不是放宽门，是**修正我自己的测试期望** —— 负例里放一个本来就不该被拒的输入，
 * 只会制造一个永远修不掉的"红"，或者诱使后来者去收紧一个正确的实现。
 */
export function devicePositiveCases() {
  const cases = [...DEFAULT_DEVICES, 'MAC-MINI', 'Mac-Mini', '42'];
  return cases.map((d) => {
    try { const n = normalizeDevice(d); return { input: d, normalized: n, ok: n === d.toLowerCase() }; }
    catch (e) { return { input: d, ok: false, reason: e.code }; }
  });
}

export const DEVICES_META = Object.freeze({
  defaultDevices: DEFAULT_DEVICES,
  nameRule: String(DEVICE_NAME_RE),
  registryPath: REGISTRY_PATH,
  note: '设备名同时是黑板 key 路径段与本地目录段 —— 格式门挡路径穿越'
});
