/**
 * selfcheck.js — ② TCC 能力边界自检（三段）+ ① 第5项 真挂载冒烟（三态）
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require_ = createRequire(import.meta.url);
const DIR = path.join(os.homedir(), '.dsh', 'plugin-selfcheck');
const PROFILE_NM = path.join(os.homedir(), '.dsh', 'profiles', 'web', 'node_modules');
const BASE = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');

function resolvePeer(peer) {
  try { require_.resolve(peer); return { ok: true, via: 'self' }; }
  catch { /* 再试 profile */ }
  try {
    createRequire(path.join(PROFILE_NM, 'noop.js')).resolve(peer);
    return { ok: true, via: 'profile' };
  } catch (e) {
    return { ok: false, via: null, err: String(e.message || e).split('\n')[0] };
  }
}

/** ① 第5项：真挂载冒烟 —— 三态分开报，绝不把 skipped 假装成 pass */
export async function mountSmoke() {
  let mod;
  try {
    mod = await import('./index.js');
  } catch (e) {
    const msg = String(e && e.message || e);
    if (/ERR_MODULE_NOT_FOUND|Cannot find package/.test(msg)) {
      return { state: 'skipped', reason: `依赖在本目录解析不到：${msg.split('\n')[0]}` };
    }
    return { state: 'fail', reason: `import 失败：${msg.split('\n')[0]}` };
  }
  const registered = [];
  const stubCtx = {
    tools: {
      register(t) {
        if (!t || typeof t.name !== 'string') throw new Error('register 收到非法工具对象');
        registered.push(t.name);
        return () => {};
      },
    },
    effect(fn) { try { const d = fn(); return typeof d === 'function' ? d : () => {}; } catch { return () => {}; } },
    on() { return () => {}; },
    get() { return undefined; },
    logger: { info() {}, warn() {}, error() {} },
  };
  try {
    mod.apply(stubCtx, { allowedRunners: ['python3', 'node'], timeoutSeconds: 300, maxMutants: 64 });
  } catch (e) {
    return { state: 'fail', reason: `apply 抛异常：${String(e && e.message || e).split('\n')[0]}` };
  }
  if (!registered.length) return { state: 'fail', reason: 'apply 未注册任何工具' };
  const want = ['assert_audit'];
  const missing = want.filter((w) => !registered.includes(w));
  if (missing.length) return { state: 'fail', reason: `注册结果缺 ${missing.join(',')}（实得 ${registered.join(',')}）` };
  return { state: 'pass', registered: [...registered] };
}

export function runSelfCheck(pluginName, spec = {}) {
  const missing = [];
  const warnings = [];
  const notes = [];
  for (const peer of spec.requiredPeers || []) {
    const r = resolvePeer(peer);
    if (!r.ok) warnings.push(`peer 无法解析: ${peer}（${r.err}）`);
    else notes.push(`peer ${peer} 经 ${r.via} 解析 ✅`);
  }
  const files = Array.isArray(spec.sourceFiles) ? spec.sourceFiles : [];
  if ((spec.requiredSymbols || []).length) {
    if (!files.length) {
      notes.push('未指定 sourceFiles → 符号检查跳过（不对"该文件是否导入"下结论）');
    } else {
      for (const rel of files) {
        const abs = path.isAbsolute(rel) ? rel : path.join(spec.baseDir || BASE, rel);
        let src;
        try { src = fs.readFileSync(abs, 'utf8'); }
        catch (e) { missing.push(`源文件不可读: ${rel}（${e.message}）`); continue; }
        for (const sym of spec.requiredSymbols) {
          const ok = new RegExp(`import[^;]*\\b${sym}\\b[^;]*from`).test(src)
                  || new RegExp(`\\b(?:const|let|var|function)\\s+${sym}\\b`).test(src);
          if (!ok) missing.push(`${rel} 中未见 ${sym} 的导入/定义`);
        }
      }
    }
  }
  return { ok: missing.length === 0, missing, warnings, notes };
}

/** ② 三段输出的组装（能力清单 / 不该发生路径 / 依赖完整性） */
export function capabilityReport() {
  return {
    capabilities: [
      '枚举断言调用（Python check()/assert，JS assert()）',
      '空断言检测：恒真 / 探针型 / 弱比较',
      '同谓词多调用点覆盖检测（含自动抽取错误码）',
      '变异测试三态判定：CAUGHT / SURVIVED / INCONCLUSIVE',
      '锚点唯一性检查（出现≠1 次即判不可判，不做替换）',
      '反控校验：套件必须含一条必然失败的控件',
    ],
    forbiddenPaths: [
      '把套件崩溃判成 CAUGHT 或 SURVIVED（必须 INCONCLUSIVE）',
      '把无效变异体（语法错/绑定错）判成 SURVIVED',
      '对未执行的断言报 PASS',
      '写入被测源文件或其所在目录',
      '越出 os.tmpdir() 写文件',
      '执行白名单外命令 / shell 拼接',
    ],
    dependency: { peers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'], runtime: 'node 内置模块 only' },
  };
}

export { DIR as SELFCHECK_DIR, BASE as PLUGIN_BASE };
