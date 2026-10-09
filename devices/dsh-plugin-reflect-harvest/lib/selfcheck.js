/**
 * selfcheck.js — R014 插件自查门（apply() 最前调用）
 * =============================================================================
 * 目的：缺模块 / 断链在**加载前**暴露，而不是等崩溃或被外部检查发现。
 *
 * 沿用参考实现 dsh-plugin-cldvoice-activate v1.0.1 的两条血泪修正：
 *   ① requiredSymbols 必须**显式给 sourceFiles**，否则会扫到 selfcheck.js 自己身上 → **假失败**；
 *      未给 sourceFiles 时如实说"符号检查已跳过"，绝不假装通过或假装失败。
 *   ② peer 解析走**两级**：先本目录，再 ~/.dsh/profiles/web/node_modules（宿主内运行时的真实来源）。
 *
 * 本版新增（R006 ④ 可核验）：peer 解析结果带**版本号 + 实际路径**，让「dsh 版本自适应」看得见。
 *
 * 写盘走 lib/out.js（全包唯一写副作用模块），路径过 guardWritePath —— 写不出去就如实降级为 note。
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { createRequire } from 'node:module';
import { writeSelfcheckState } from './out.js';

const require_ = createRequire(import.meta.url);
const PROFILE_NM = path.join(os.homedir(), '.dsh', 'profiles', 'web', 'node_modules');

/** 两级解析：本目录 → profile/node_modules；并回读其 package.json 版本 */
function resolvePeer(peer) {
  const tryOne = (fn, via) => {
    try {
      const entry = fn.resolve(peer);
      let version = null;
      try {
        const pkgPath = entry.replace(/[\\/]lib[\\/][^\\/]+$/, '/package.json');
        version = JSON.parse(fs.readFileSync(pkgPath, 'utf8')).version;
      } catch { /* 版本读不到不算失败，如实留 null */ }
      return { ok: true, via, entry, version };
    } catch { return null; }
  };

  const a = tryOne(require_, 'self');
  if (a) return a;
  try {
    const req2 = createRequire(path.join(PROFILE_NM, 'noop.js'));
    const b = tryOne(req2, 'profile');
    if (b) return b;
    return { ok: false, via: null, err: `两级解析均失败（本目录 + ${PROFILE_NM}）` };
  } catch (e) {
    return { ok: false, via: null, err: String(e.message || e).split('\n')[0] };
  }
}

export function runSelfCheck(pluginName, spec = {}) {
  const missing = [];
  const warnings = [];
  const notes = [];
  const peers = [];

  // 1) peer 依赖可解析性（两级）+ 版本可见（④）
  for (const peer of spec.requiredPeers || []) {
    const r = resolvePeer(peer);
    peers.push({ peer, ok: r.ok, via: r.via, version: r.version || null });
    if (!r.ok) missing.push(`peer 无法解析: ${peer}（${r.err}）`);
    else if (r.via === 'profile') notes.push(`peer ${peer}@${r.version} 经 profile/node_modules 解析 ✅`);
    else notes.push(`peer ${peer}@${r.version} 经本目录解析 ✅`);
  }

  // 2) 关键符号：只在实际使用它们的文件里查（未指定 sourceFiles → 如实跳过）
  const files = Array.isArray(spec.sourceFiles) ? spec.sourceFiles : [];
  if (spec.requiredSymbols && spec.requiredSymbols.length) {
    if (!files.length) {
      notes.push('未指定 sourceFiles → 符号检查跳过（不对"该文件是否导入"下结论，防假失败）');
    } else {
      for (const rel of files) {
        const abs = path.isAbsolute(rel) ? rel : path.join(spec.baseDir || process.cwd(), rel);
        let src;
        try { src = fs.readFileSync(abs, 'utf8'); }
        catch (e) { missing.push(`源文件不可读: ${rel}（${e.message}）`); continue; }
        for (const sym of spec.requiredSymbols) {
          const imported = new RegExp(`import[^;]*\\b${sym}\\b[^;]*from`).test(src) ||
                           new RegExp(`\\b(?:const|let|var|function|class)\\s+${sym}\\b`).test(src) ||
                           new RegExp(`\\b${sym}\\s*[=({]`).test(src);
          if (!imported) missing.push(`${rel} 中未见 ${sym} 的导入/定义（裸用将 ReferenceError）`);
        }
      }
    }
  }

  // 3) type:module 匹配（血泪：central-inbox 缺 type:module → CLD 启动崩溃）
  try {
    const pkg = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
    if (pkg.type !== 'module') missing.push('package.json 缺 "type": "module"（ESM 语法将 SyntaxError）');
    if (pkg.name !== pluginName && !String(pkg.name).endsWith(pluginName)) {
      warnings.push(`package.json name='${pkg.name}' 与自查名 '${pluginName}' 不一致（自查名应为其短名）`);
    }
  } catch (e) { missing.push(`package.json 不可读: ${e.message}`); }

  const result = {
    plugin: pluginName, ok: missing.length === 0, missing, warnings, notes, peers,
    node: process.version, ts: new Date().toISOString()
  };
  try { writeSelfcheckState(pluginName, result); }
  catch (e) { notes.push(`自查状态落盘被门拒绝/失败：${String(e.message || e)}`); }
  return result;
}
