/**
 * selfcheck.js — R006 ② TCC 检测（能力边界自检）+ R014 自查门
 * 目的：让"该文件是否真的导入了它裸用的符号"在**加载前**暴露，而不是等崩溃。
 *
 * v1 教训（照抄参考实现的血泪条，本包同样遵守）：
 *   不给 sourceFiles 时符号检查会扫到 selfcheck.js 自己身上 → **假失败**。
 *   因此本实现要求显式给出 sourceFiles；未给出则**如实说"符号检查已跳过"**，
 *   绝不假装通过、也绝不假装失败。
 *
 * 本包的两点收紧（相对参考实现）：
 *   1) 落盘位置：自查产物写进**本包自己的 `.selfcheck/last.json`**，
 *      不写 `~/.dsh/plugin-selfcheck/`（⑩ 写入白名单只有 3 条规则，selfcheck 不在其中）。
 *   2) peer 解析：作为 ④ 的证据输出**两级**尝试结果（本目录 → profile node_modules），
 *      并区分"环境问题"与"包问题"（R006 §6 坑 5）。
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { guardedMkdirp, guardedWrite } from './log.js';
import { peerSatisfies } from './gate.js';

const require_ = createRequire(import.meta.url);
const PROFILE_NM = path.join(os.homedir(), '.dsh', 'profiles', 'node_modules');

/** 两级 peer 解析：本目录 → profile node_modules。 */
export function resolvePeer(peer) {
  try { return { ok: true, via: 'self', resolved: require_.resolve(peer) }; }
  catch { /* 继续 */ }
  try {
    const req2 = createRequire(path.join(PROFILE_NM, 'noop.js'));
    return { ok: true, via: 'profile', resolved: req2.resolve(peer) };
  } catch (e) {
    return { ok: false, via: null, err: String(e.message || e).split('\n')[0] };
  }
}

/** node 是否在 PATH 上（**环境问题**，不是包问题 —— R006 §6 坑 5）。 */
export function nodeOnPath() {
  const dirs = String(process.env.PATH || '').split(path.delimiter).filter(Boolean);
  for (const d of dirs) {
    for (const name of ['node', 'node.exe']) {
      const p = path.join(d, name);
      try { if (fs.existsSync(p)) return { ok: true, path: p }; } catch { /* ignore */ }
    }
  }
  return { ok: false, path: null };
}

/**
 * ④ **真挂载冒烟**（兄弟插件靠这一项抓到过 apply 阶段直接抛 UNSUPPORTED_SCHEMA 的真缺陷）：
 *   import `lib/index.js` → 用**桩 ctx** 调 `apply()` → 数注册了几个工具并校验工具形状。
 *
 * 三条纪律：
 *   1) **peer 解析不到就如实标「跳过」，绝不判「通过」** —— 无宿主环境本来就挂不上，
 *      把它算成通过等于用假证据骗自己（R006 §3.2 的血泪条）。
 *   2) **桩 ctx 必须能记录副作用**：`tools.register` 收集注册项、`effect` 立即执行并捕获异常，
 *      这样"注册了 0 个工具"或"effect 里抛错"都会被看见，而不是被 try/catch 吞掉。
 *   3) **防递归**：本函数会调 apply()，而 apply() 内部又会调 runSelfCheck()；
 *      用模块级 inSmoke 闸门挡住"冒烟里的冒烟"，避免无限递归。
 */
let inSmoke = false;
export function mountSmokeRunning() { return inSmoke; }

export async function mountSmoke({ baseDir, indexRel = 'lib/index.js', requiredPeers = [], expectedToolName = null } = {}) {
  if (inSmoke) return { status: 'skipped', reason: '已在冒烟中（防 apply → runSelfCheck → 冒烟 的递归）' };
  const peers = requiredPeers.map((p) => ({ peer: p, ...resolvePeer(p) }));
  const unresolved = peers.filter((p) => !p.ok);
  if (unresolved.length) {
    return {
      status: 'skipped', peers,
      reason: `peer 解析不到：${unresolved.map((p) => `${p.peer}(${p.err})`).join('; ')} —— 无宿主环境挂不了真实插件，**如实标"跳过"，不判"通过"**`
    };
  }
  inSmoke = true;
  try {
    const abs = path.join(baseDir, indexRel);
    let mod;
    try { mod = await import(pathToFileURL(abs).href); }
    catch (e) { return { status: 'failed', stage: 'import', error: `${e.name}: ${e.message}`, code: e.code || null, peers }; }

    if (typeof mod.apply !== 'function') {
      return { status: 'failed', stage: 'shape', error: `${indexRel} 未导出 apply(ctx, config)（R006 ① 要求）`, peers };
    }
    const registered = []; const effects = []; const effectErrors = [];
    const ctx = {
      tools: { register(tool) { registered.push(tool); return () => {}; } },
      effect(fn) { effects.push(fn); try { return fn(); } catch (e) { effectErrors.push(String(e.message || e)); } },
      on() {}, logger: { info() {}, warn() {}, error() {}, debug() {} }
    };
    try { await mod.apply(ctx, {}); }
    catch (e) {
      return {
        status: 'failed', stage: 'apply', error: `${e.name}: ${e.message}`, code: e.code || null,
        violations: e.violations || null, registered: registered.length, peers
      };
    }
    const shape = registered.map((t) => ({
      name: (t && t.name) || null,
      hasDescription: Boolean(t && t.description),
      hasParameters: Boolean(t && t.parameters),
      hasExecute: typeof (t && t.execute) === 'function'
    }));
    const bad = shape.filter((s2) => !s2.name || !s2.hasDescription || !s2.hasParameters || !s2.hasExecute);
    const injectOk = Array.isArray(mod.inject) && mod.inject.includes('tools');
    const expectedOk = expectedToolName ? shape.some((s2) => s2.name === expectedToolName) : null;
    const problems = [];
    if (registered.length < 1) problems.push('注册工具数 = 0');
    if (bad.length) problems.push(`工具形状不全: ${JSON.stringify(bad)}`);
    if (!injectOk) problems.push(`inject 未声明 'tools'（实为 ${JSON.stringify(mod.inject || null)}）`);
    if (expectedOk === false) problems.push(`未注册期望工具 '${expectedToolName}'`);
    return {
      status: problems.length ? 'failed' : 'passed',
      stage: problems.length ? 'assert' : null,
      error: problems.length ? problems.join('；') : null,
      moduleName: mod.name || null, inject: mod.inject || null, injectOk,
      registered: registered.length, tools: shape,
      effectCount: effects.length, effectErrors, peers, expectedToolName, expectedOk
    };
  } finally { inSmoke = false; }
}

export function runSelfCheck(pluginName, spec = {}) {
  const missing = [];      // 包问题（must fail）
  const envIssues = [];    // 环境问题（only warn）
  const warnings = [];
  const notes = [];

  // 1) peer 依赖可解析性（两级）+ ④ 版本范围是否真的被满足
  const peers = [];
  const ranges = spec.peerRanges || {};
  for (const peer of spec.requiredPeers || []) {
    const r = resolvePeer(peer);
    let version = null;
    if (r.ok) {
      // 读**被解析到的那份** package.json 的版本（不是猜）
      try {
        const pkgPath = path.join(path.dirname(r.resolved), '..', 'package.json');
        version = JSON.parse(fs.readFileSync(pkgPath, 'utf8')).version || null;
      } catch { version = null; }
    }
    let rangeCheck = null;
    if (r.ok && ranges[peer]) {
      if (version) {
        rangeCheck = peerSatisfies(ranges[peer], version);
        if (!rangeCheck.ok) {
          missing.push(`peer ${peer} 声明 '${ranges[peer]}' 不满足已安装版本 ${version}：${rangeCheck.reason}` +
            '（已安装版本存在但声明解析不上 = 声明等于装饰；R006 ④ 要求"正式声明**并被解析**"）');
        }
      } else {
        rangeCheck = { ok: false, reason: '无法从被解析到的包读取版本号，未做范围判定（不假装通过）' };
        notes.push(`peer ${peer} 版本未知 → 范围判定跳过（如实标注）`);
      }
    }
    peers.push({ peer, ...r, version, range: ranges[peer] || null, rangeOk: rangeCheck ? rangeCheck.ok : null, rangeReason: rangeCheck ? rangeCheck.reason : null });
    if (!r.ok) missing.push(`peer 无法解析: ${peer}（${r.err}）— 两级都试过：本目录 / profile node_modules`);
    else if (r.via === 'profile') notes.push(`peer ${peer} 经 profile node_modules 解析 ✅（v${version || '?'} ∈ ${ranges[peer] || '(未声明范围)'}）`);
  }

  // 2) 关键符号：**只在实际使用它们的文件里查**
  const files = Array.isArray(spec.sourceFiles) ? spec.sourceFiles : [];
  if (spec.requiredSymbols && spec.requiredSymbols.length) {
    if (!files.length) {
      notes.push('未指定 sourceFiles → 符号检查跳过（不对"该文件是否导入"下结论）');
    } else {
      for (const rel of files) {
        const abs = path.isAbsolute(rel) ? rel : path.join(spec.baseDir || process.cwd(), rel);
        let src;
        try { src = fs.readFileSync(abs, 'utf8'); }
        catch (e) { missing.push(`源文件不可读: ${rel}（${e.message}）`); continue; }
        for (const sym of spec.requiredSymbols) {
          const imported = new RegExp(`import[^;]*\\b${sym}\\b`).test(src) ||
            new RegExp(`\\b(?:const|let|var|function|class)\\s+${sym}\\b`).test(src) ||
            new RegExp(`\\b${sym}\\s*[=({]`).test(src);
          if (!imported) missing.push(`${rel} 中未见 ${sym} 的导入/定义（裸用将 ReferenceError）`);
        }
      }
    }
  }

  // 3) type:module 匹配
  let pkg = null;
  try {
    pkg = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
    if (pkg.type !== 'module') missing.push('package.json 缺 "type": "module"（ESM 语法将 SyntaxError）');
  } catch (e) { missing.push(`package.json 不可读: ${e.message}`); }

  // 4) 环境问题（不判失败，但在输出里与包问题分开标注）
  const node = nodeOnPath();
  if (!node.ok) {
    envIssues.push(`node 不在 PATH 上（当前 PATH=${process.env.PATH || '(空)'}）：` +
      '本包 CLI 用 `#!/usr/bin/env node` 启动时要求 PATH 含 node（本机实测在 /opt/homebrew/bin/node）。' +
      '这是**环境问题**，不是包问题——用绝对路径或登录 shell 即可。');
  }

  const result = {
    plugin: pluginName,
    ok: missing.length === 0,
    missing, warnings, envIssues, notes, peers,
    node: { version: process.version, onPath: node.ok, path: node.path, argv0: process.argv[1] || null },
    packageVersion: pkg ? pkg.version : null,
    ts: new Date().toISOString()
  };

  try {
    guardedMkdirp(spec.selfcheckDir);
    guardedWrite(path.join(spec.selfcheckDir, `${pluginName}.json`), JSON.stringify(result, null, 1));
  } catch (e) {
    warnings.push(`自查产物落盘失败（不影响结论）: ${e.message}`);
  }
  return result;
}
