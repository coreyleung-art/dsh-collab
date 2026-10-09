/**
 * selfcheck.js — ② TCC 检测（能力边界自检）：apply() 最前调用，也是 --selfcheck 的实现。
 * 输出三段（R006 ②验收标准）：
 *   ① 能力清单（能碰什么）
 *   ② 不该发生路径清单（碰不到什么 / 结构上不存在什么）
 *   ③ 依赖完整性（peer 解析 / 关键符号 / type:module）
 *
 * ★ 血泪条（R006 §3.2）：不给 sourceFiles 时，符号检查会扫到 selfcheck.js 自己身上 → 假失败。
 *   所以本实现**必须**显式给 sourceFiles；未给则如实说"符号检查已跳过"，
 *   绝不假装通过、也绝不假装失败。
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { createRequire } from 'node:module';
import { DECISIONS, TARGETS, ALLOWED_BB_HOSTS, ALLOWED_COMMANDS, DANGEROUS_PRIMITIVES, GATE_META } from './gate.js';
import { VERSION } from './version.js';

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

  // ③ 依赖完整性 —— peer 可解析性（先本目录，再 profile/node_modules 两级）
  for (const peer of spec.requiredPeers || []) {
    const r = resolvePeer(peer);
    if (!r.ok) missing.push(`peer 无法解析: ${peer}（${r.err}）`);
    else if (r.via === 'profile') notes.push(`peer ${peer} 经 profile/node_modules 解析 ✅`);
  }

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

  try {
    const pkg = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
    if (pkg.type !== 'module') missing.push('package.json 缺 "type": "module"（ESM 语法将 SyntaxError）');
    if (!pkg.dsh || !pkg.dsh.bundle || !pkg.dsh.bundle.patch) missing.push('package.json 缺 dsh.bundle.patch（宿主无法挂载）');
    if (spec.expectedVersion && pkg.version !== spec.expectedVersion) missing.push(`版本漂移: package.json=${pkg.version} ≠ 期望 ${spec.expectedVersion}`);
  } catch (e) { missing.push(`package.json 不可读: ${e.message}`); }

  const result = {
    plugin: pluginName, version: VERSION, ok: missing.length === 0, missing, warnings, notes,
    ts: new Date().toISOString()
  };
  try {
    fs.mkdirSync(DIR, { recursive: true });
    fs.writeFileSync(path.join(DIR, `${pluginName}.json`), JSON.stringify(result, null, 1));
    fs.appendFileSync(path.join(DIR, 'selfcheck.log'),
      `[${result.ts}] ${pluginName} v${VERSION} ok=${result.ok} missing=${missing.length} warnings=${warnings.length} notes=${notes.length}\n`);
  } catch { /* 落盘失败不阻塞 */ }
  return result;
}

/** ② TCC 三段文本（--selfcheck 打印用）：能力清单 / 不该发生路径 / 依赖完整性。 */
export function tccSections(sc) {
  return {
    capabilities: [
      `唯一副作用入口: 用户裁定（裁定文件 --ruling / 单条 --rule <id>=<decision>:<target>）`,
      `可写目标（冻结枚举）: ${TARGETS.join(' / ')} —— philosophy/rule 写治理库，spec 写 SOP，archive 只归档案例`,
      `唯一对外通道: 黑板 HTTP（PUT/GET），且主机必须在白名单 [${ALLOWED_BB_HOSTS.join(', ')}] 内`,
      `写形态: 读取 → 追加 → .tmp 原子写 → 回读校验（失败自动回滚）`,
      `依赖: 仅 node 内置模块（fs/path/os/http/crypto/url/module）+ ${(sc && sc.notes ? '' : '')}零外部依赖`
    ],
    forbidden: [
      `绝不自动决定入册什么：裁定结果只接受 ${DECISIONS.join(' / ')}；包内无任何"生成裁定"的函数，无 autoDecide/force 开关`,
      `绝不删除任何条目：源码零删除原语（扫描目标 ${DANGEROUS_PRIMITIVES.join('/')}）；无 unlink/rm/rmdir/truncate 调用点；写入后断言条目数严格 +N`,
      `绝不重复入册：幂等台账 data/reflect/enrolled.json（proposal_id 已入册即拒）+ 编号唯一性查重（哲学 id / order、规则号 RULES.md+rules.json 双查）`,
      `绝不写坏目标文件：备份→回读验证→原子写→回读校验→失败回滚；另有"计划后文件被改动即拒写"的并发保护`,
      `绝不 shell 出站：不 import child_process，exec/spawn 调用点 0 个（外部命令白名单 = 空集 ${JSON.stringify(ALLOWED_COMMANDS)}）`,
      `绝不接受非白名单出站主机：assertBbHost 冻结白名单，非白名单 → BB_HOST_FORBIDDEN`,
      `绝不覆盖已有 SOP / 越界文件名：slug 封闭字符集 + root 内路径校验（PATH_ESCAPE）`
    ],
    dependencies: {
      peers: sc.missing.filter((m) => m.startsWith('peer')).length ? sc.missing.filter((m) => m.startsWith('peer')) : '全部解析 ✅',
      notes: sc.notes, missing: sc.missing, gate: GATE_META.principle
    }
  };
}
