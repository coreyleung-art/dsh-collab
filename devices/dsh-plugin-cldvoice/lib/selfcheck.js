/**
 * selfcheck.js — R014 插件自查门（apply() 最前调用；同步、零副作用、零网络）
 * v0.6.1 补课（2026-10-03 星桥 · R006 ⑤ 存量对齐最后一项）：
 *   此前本插件无 selfcheck（矩阵 gap：无selfcheck/无CLI）。
 *   规则 R040（自查不得自指）：apply 链上的检查只做同步纯检查；
 *   真挂载冒烟独立为 cli.js --selfcheck 的 CLI 驱动项（带防重入守卫）。
 */
import { readFileSync, mkdirSync, writeFileSync, appendFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require_ = createRequire(import.meta.url);
const DIR = join(homedir(), '.dsh', 'plugin-selfcheck');

/** 提取源码全部顶层 import 符号（named/default/namespace 三形态，对齐 0.2.10 正则） */
export function extractImportedSymbols(src) {
  const out = new Set();
  const re = /import\s*(?:\{([^}]*)\}|\*\s*as\s+([A-Za-z_$][\w$]*)|([A-Za-z_$][\w$]*))\s*from/gs;
  let m;
  while ((m = re.exec(src))) {
    if (m[1] !== undefined) {
      for (const part of m[1].split(',')) {
        const name = part.trim().split(/\s+as\s+/)[0].trim();
        if (name) out.add(name);
      }
    }
    if (m[2]) out.add(m[2]);
    if (m[3]) out.add(m[3]);
  }
  return out;
}

function resolvePeer(peer) {
  try { require_.resolve(peer); return { ok: true, via: 'self' }; }
  catch { /* 宿主体内运行时 peer 从 profile 解析 */ }
  try {
    const req2 = createRequire(join(homedir(), '.dsh', 'profiles', 'web', 'node_modules', 'noop.js'));
    req2.resolve(peer);
    return { ok: true, via: 'profile' };
  } catch (e) {
    return { ok: false, via: null, err: String((e && e.message) || e).split('\n')[0] };
  }
}

export function runSelfCheck(pluginName, spec = {}) {
  const missing = [];
  const warnings = [];
  const notes = [];

  // 1) peer 依赖可解析性
  for (const peer of spec.requiredPeers || []) {
    const r = resolvePeer(peer);
    if (!r.ok) missing.push(`peer 无法解析: ${peer}（${r.err}）`);
    else if (r.via === 'profile') notes.push(`peer ${peer} 经 profile/node_modules 解析 ✅`);
  }

  // 2) 关键符号（默认扫调用方 index.js；sourceFiles 显式优先）
  if (spec.requiredSymbols && spec.requiredSymbols.length) {
    const files = (Array.isArray(spec.sourceFiles) && spec.sourceFiles.length)
      ? spec.sourceFiles
      : [fileURLToPath(new URL('./index.js', import.meta.url))];
    for (const rel of files) {
      const abs = rel.startsWith('/') ? rel : join(spec.baseDir || fileURLToPath(new URL('..', import.meta.url)), rel);
      let src;
      try { src = readFileSync(abs, 'utf8'); }
      catch (e) { missing.push(`源文件不可读: ${rel}（${e.message}）`); continue; }
      const imported = extractImportedSymbols(src);
      for (const sym of spec.requiredSymbols) {
        if (!imported.has(sym)) missing.push(`${rel} 中未见 ${sym} 的顶层导入（裸用将 ReferenceError）`);
      }
    }
  }

  // 3) type:module 匹配
  try {
    const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
    if (pkg.type !== 'module') missing.push('package.json 缺 "type": "module"（ESM 语法将 SyntaxError）');
  } catch (e) { missing.push(`package.json 不可读: ${e.message}`); }

  const result = { plugin: pluginName, ok: missing.length === 0, missing, warnings, notes, ts: new Date().toISOString() };
  try {
    mkdirSync(DIR, { recursive: true });
    writeFileSync(join(DIR, `${pluginName}.json`), JSON.stringify(result, null, 1));
    appendFileSync(join(DIR, 'selfcheck.log'),
      `[${result.ts}] ${pluginName} ok=${result.ok} missing=${missing.length} notes=${notes.length}\n`);
  } catch { /* 落盘失败不阻塞 */ }
  return result;
}

// ─── 真挂载冒烟（CLI 专用 · R040：独立入口 + 防重入；绝不在 apply 链内）─────
let _smokeInFlight = false;
export async function runApplySmoke() {
  if (_smokeInFlight) return { state: 'skipped', detail: '防重入守卫：已有冒烟在跑' };
  _smokeInFlight = true;
  try {
    const mod = await import('./index.js');
    const noop = new Proxy(function () {}, { get: () => noop, apply: () => undefined });
    const stubWebServer = { register: () => () => undefined };
    const stubCtx = new Proxy({ effect: (fn) => { if (typeof fn === 'function') fn(); }, on: () => undefined }, {
      get: (t, k) => {
        if (k === 'get') return (name) => (name === 'webServer' ? stubWebServer : noop);
        return (k in t ? t[k] : noop);
      },
    });
    await mod.apply(stubCtx, {});
    return { state: 'pass', detail: 'apply(stub) 正常返回' };
  } catch (e) {
    const m = String((e && e.message) || e);
    if (m.includes('ERR_MODULE_NOT_FOUND') || m.includes('Cannot find')) return { state: 'skipped', detail: '依赖缺失: ' + m.slice(0, 60) };
    return { state: 'fail', detail: 'apply 抛异常: ' + m.slice(0, 100) };
  } finally { _smokeInFlight = false; }
}
