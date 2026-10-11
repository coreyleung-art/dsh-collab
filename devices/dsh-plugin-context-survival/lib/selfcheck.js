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

/**
 * ★ R006 ②「TCC 能力边界自检」的**三段内容本体**（2026-10-10 从 cli.js 渲染层移入）.
 *
 * 为什么搬进本模块：R006 ② 的判据对象是 **selfcheck 本身**。
 * 搬入前本模块只做 peer 解析 + 符号检查 ⇒ **只覆盖三段中的「依赖完整性」一段**（审计器报 1/3 是对的）。
 * 三段是：
 *   [① 能力清单]     本插件**能做**的事
 *   [② 不该发生路径] 本插件**永远不该做**的事（负能力）—— R006 ② 的立意所在
 *   [③ 依赖完整性]   本插件**靠什么活**（peer 可解析 + 缺则如实降级）
 *
 * @param {{recallKinds:string[], allowedInject:string[], forbiddenInject:string[],
 *          allowedCommands:string[], nodeVersion:string, logFile:string}} env
 * @returns {{capabilities:string[], forbidden:string[], deps:string[]}} 三段，每段是逐条陈述
 */
export function buildSegments(env = {}) {
  const rk = (env.recallKinds || []).join(', ');
  const ai = (env.allowedInject || []).join(', ');
  const fi = (env.forbiddenInject || []).join(', ');
  const ac = (env.allowedCommands || []).length;
  const nv = env.nodeVersion || process.version;
  const lf = env.logFile || '(未指定)';

  return {
    capabilities: [
      `三工具：csx_status（只读状态）/ csx_checkpoint（产出检查点）/ csx_recall（按 seq 逐字召回）`,
      `只读观测：agent/pre-step 上读 tokenMeter 与 session.events，判定压力与并发状态`
    ],
    forbidden: [
      `零外部命令：ALLOWED_COMMANDS 长度 ${ac}（不 spawn/exec/fork 任何东西 —— **能力为零**，非「没找到危险命令」）`,
      `召回目标枚举化：RECALL_KINDS = [${rk}]，id 为有界数字/区间 ⇒ **不接受路径/命令/URL/任何其它字符串**`,
      `不接管压缩后端：inject 白名单 = [${ai}]，禁 [${fi}]（seam b：与官方并存，不替换 ctx.compaction）`,
      `观察器契约：任何读不到 ⇒ 如实报原因码，**绝不抛出**（守卫自身缺陷不得影响会话）`
    ],
    deps: [
      `运行期只依赖 node ${nv} 内置模块；不调用任何 dsh 私有 API（R006 ③ CLD 自适应）`,
      `标识/版本来自 package.json（R006 ⑥ 单一来源）`,
      `统一日志：${lf}`,
      `可选服务（tokenMeter/llm）一律 ctx.get() 取，拿不到即如实跳过（**不写进 inject**，避免整棵树加载失败）`
    ]
  };
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
