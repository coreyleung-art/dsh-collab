/**
 * selfcheck.js — R014 插件自查门（apply() 最前调用）
 * 目的：缺模块/断链在**加载前**暴露，而不是等崩溃或被外部检查发现。
 *
 * 与 cldvoice-activate 同形（该模块是通用件，照抄其 v1.0.1 修正后的语义）：
 *   - requiredSymbols **只在实际使用它们的文件里查**（由 spec.sourceFiles 显式给出），
 *     否则"检查报错了对象"（例如把 requiredSymbols 扫到 selfcheck.js 自己身上）。
 *   - 未给 sourceFiles 时如实说"符号检查已跳过"，绝不假装通过或假装失败。
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { createRequire } from 'node:module';

const require_ = createRequire(import.meta.url);
const DIR = path.join(os.homedir(), '.dsh', 'plugin-selfcheck');
const PROFILE_NM = path.join(os.homedir(), '.dsh', 'profiles', 'web', 'node_modules');

function resolvePeer(peer) {
  try { require_.resolve(peer); return { ok: true, via: 'self' }; }
  catch { /* 继续尝试 profile 的 node_modules（插件在宿主体内运行时 peer 从这里解析） */ }
  try {
    const req2 = createRequire(path.join(PROFILE_NM, 'noop.js'));
    req2.resolve(peer);
    return { ok: true, via: 'profile' };
  } catch (e) {
    return { ok: false, via: null, err: String(e.message || e).split('\n')[0] };
  }
}

export function runSelfCheck(pluginName, spec = {}) {
  const missing = [];
  const warnings = [];
  const notes = [];

  // 1) peer 依赖可解析性（先本目录，再 profile/node_modules）
  for (const peer of spec.requiredPeers || []) {
    const r = resolvePeer(peer);
    if (!r.ok) missing.push(`peer 无法解析: ${peer}（${r.err}）`);
    else if (r.via === 'profile') notes.push(`peer ${peer} 经 profile/node_modules 解析 ✅`);
  }

  // 2) 关键符号：**只在实际使用它们的文件里查**（不指定则跳过，并如实说明）
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
          const imported = new RegExp(`import[^;]*\\b${sym}\\b[^;]*from`).test(src) ||
                           new RegExp(`\\b(?:const|let|var|function)\\s+${sym}\\b`).test(src) ||
                           new RegExp(`\\b${sym}\\s*[=({]`).test(src);
          if (!imported) missing.push(`${rel} 中未见 ${sym} 的导入/定义（裸用将 ReferenceError）`);
        }
      }
    }
  }

  // 3) type:module 匹配
  try {
    const pkg = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
    if (pkg.type !== 'module') missing.push('package.json 缺 "type": "module"（ESM 语法将 SyntaxError）');
  } catch (e) { missing.push(`package.json 不可读: ${e.message}`); }

  const result = { plugin: pluginName, ok: missing.length === 0, missing, warnings, notes, ts: new Date().toISOString() };
  try {
    fs.mkdirSync(DIR, { recursive: true });
    fs.writeFileSync(path.join(DIR, `${pluginName}.json`), JSON.stringify(result, null, 1));
    fs.appendFileSync(path.join(DIR, 'selfcheck.log'),
      `[${result.ts}] ${pluginName} ok=${result.ok} missing=${missing.length} warnings=${warnings.length} notes=${notes.length}\n`);
  } catch { /* 落盘失败不阻塞 */ }
  return result;
}
