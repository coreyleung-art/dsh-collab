/**
 * out.js — ★ 全包**唯一**的写副作用模块（⑦ 统一日志 + 提案落盘出口）
 * =============================================================================
 * 本工具唯一的「不该发生路径」是**替用户改哲学库/规则库**（RULES.md / governance-philosophy.json）。
 * 拦它的地方就是这里 —— 而且是结构性的，不是"检查后放行"：
 *
 *   - 写目标来自**冻结**的 WRITE_SPEC，只有三个语义名；
 *   - `guardWritePath()` 四道判定，任一不过 → GateError，**调用方拿不到路径**；
 *   - 治理库名（RULES.md / governance-philosophy.json / rules.json / rules-registry /
 *     gallery / blueprint）是**显式禁用词**；
 *   - `rules-registry/` 与 `data/blueprint/gallery/` **根本不在任何基目录之下**
 *     （base 只有 `data/reflect`、`logs/`、`~/.dsh/plugin-selfcheck`），
 *     所以"写库"在本实现里连**路径都构造不出来**。
 *
 * 为什么这比"加一句 if 检查目标路径"强：后者是运行时判断，可能被参数绕过；
 * 前者是**值域封死** —— 越界的值构造不出来，就没有"绕过"这回事。
 *
 * 依 据：R006 v3.0 §2 ⑩ + §4.1（入口门 / 类型锁）+ phi-user-sovereignty + phi-027
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { GateError, ALLOWED_WRITE_TARGETS, FORBIDDEN_WRITE_TOKENS } from './gate.js';

const COLLAB = path.join(os.homedir(), 'dsh-collab');

/** 冻结：语义名 → 基目录 + 文件名模板。这是写副作用的**唯一入口集合**。 */
export const WRITE_SPEC = Object.freeze({
  'proposal-md': Object.freeze({
    base: path.join(COLLAB, 'data', 'reflect'),
    pattern: /^proposal-\d{4}-\d{2}-\d{2}\.md$/
  }),
  'unified-log': Object.freeze({
    base: path.join(COLLAB, 'logs'),
    pattern: /^dsh-plugin-reflect-synthesize\.log(\.\d+)?$/
  }),
  'selfcheck-state': Object.freeze({
    base: path.join(os.homedir(), '.dsh', 'plugin-selfcheck'),
    pattern: /^[A-Za-z0-9._-]+\.(json|log)$/
  })
});

export const LOG_FILE = path.join(WRITE_SPEC['unified-log'].base, 'dsh-plugin-reflect-synthesize.log');
export const DATA_DIR = WRITE_SPEC['proposal-md'].base;

/**
 * 写路径结构门（入口门 + 类型锁）。
 * 四道判定，任一不过即抛 GateError（失败即停，不是警告后继续）：
 *   1) kind 必须 ∈ 冻结的 ALLOWED_WRITE_TARGETS（没有"自定义 kind"这个入口）
 *   2) 解析后的绝对路径不得含任何 FORBIDDEN_WRITE_TOKENS（治理库）
 *   3) 必须落在该 kind 基目录**之内**且**不得多一级子目录**（防 ../ 穿越与旁路目录）
 *   4) 文件名必须匹配该 kind 的模板
 */
export function guardWritePath(kind, target) {
  if (!ALLOWED_WRITE_TARGETS.includes(kind)) {
    throw new GateError('WRITE_KIND_FORBIDDEN',
      `拒绝：写目标类别 '${kind}' 不在白名单 [${ALLOWED_WRITE_TARGETS.join(', ')}] 内。本工具没有"自定义写目标"这个入口。`);
  }
  if (typeof target !== 'string' || target.trim() === '') {
    throw new GateError('EMPTY_TARGET', '拒绝：写路径为空。');
  }
  const abs = path.resolve(target);
  const low = abs.toLowerCase();
  for (const tok of FORBIDDEN_WRITE_TOKENS) {
    if (low.includes(tok.toLowerCase())) {
      throw new GateError('FORBIDDEN_TARGET',
        `拒绝：写路径命中治理库禁用词「${tok}」→ ${abs}。` +
        `本工具**没有**写规则库/哲学库的能力 —— 依据 phi-user-sovereignty：库的改动权在用户裁定（⑥）之后的 ⑦ reflect-enroll，不在提炼环节。`);
    }
  }
  const spec = WRITE_SPEC[kind];
  if (!(abs === spec.base || abs.startsWith(spec.base + path.sep))) {
    throw new GateError('OUT_OF_SCOPE', `拒绝：写路径越界 → ${abs}（'${kind}' 只允许写在 ${spec.base} 之内）。`);
  }
  if (path.dirname(abs) !== spec.base) {
    throw new GateError('NESTED_TARGET', `拒绝：写路径落在子目录 → ${abs}（'${kind}' 只允许直接写在 ${spec.base} 下）。`);
  }
  if (!spec.pattern.test(path.basename(abs))) {
    throw new GateError('BAD_FILENAME', `拒绝：文件名 '${path.basename(abs)}' 不符合 '${kind}' 的模板 ${String(spec.pattern)}。`);
  }
  return abs;
}

/* ------------------- 写门负例 / 正例（供 --lean4-check 实测） ------------------- */

/** 负例：企图写治理库 / 越界 / 子目录 / 错文件名 / 假 kind —— **必须全部被拒** */
export function writeTargetNegativeCases() {
  const attempts = [
    { name: '写 RULES.md（规则库）', kind: 'proposal-md', target: path.join(COLLAB, 'rules-registry', 'RULES.md') },
    { name: '写 governance-philosophy.json（哲学库）', kind: 'proposal-md', target: path.join(COLLAB, 'data', 'blueprint', 'gallery', 'governance-philosophy.json') },
    { name: '写 rules.json（规则机读本）', kind: 'proposal-md', target: path.join(COLLAB, 'rules-registry', 'rules.json') },
    { name: '写 rules-registry 下的新文件', kind: 'proposal-md', target: path.join(COLLAB, 'rules-registry', 'proposal-2026-09-10.md') },
    { name: '写 gallery 下的新文件', kind: 'proposal-md', target: path.join(COLLAB, 'data', 'blueprint', 'gallery', 'proposal-2026-09-10.md') },
    { name: '路径穿越 ../../ 到 rules-registry', kind: 'proposal-md', target: path.join(DATA_DIR, '..', '..', 'rules-registry', 'proposal-2026-09-10.md') },
    { name: '完全越界 /tmp', kind: 'proposal-md', target: '/tmp/proposal-2026-09-10.md' },
    { name: '基目录内多一级子目录', kind: 'proposal-md', target: path.join(DATA_DIR, 'sub', 'proposal-2026-09-10.md') },
    { name: '文件名不符合模板', kind: 'proposal-md', target: path.join(DATA_DIR, 'RULES.md') },
    { name: '不存在的写目标类别(apply)', kind: 'apply', target: path.join(DATA_DIR, 'proposal-2026-09-10.md') },
    { name: '不存在的写目标类别(enroll)', kind: 'enroll', target: path.join(DATA_DIR, 'proposal-2026-09-10.md') },
    { name: '空路径', kind: 'proposal-md', target: '' },
    { name: 'null 路径', kind: 'proposal-md', target: null }
  ];
  return attempts.map(({ name, kind, target }) => {
    try { guardWritePath(kind, target); return { input: name, code: null }; }
    catch (e) { return { input: name, code: e.code || 'ERROR' }; }
  });
}

/** 正例：三个合法写目标必须可用（防「门太宽把自己人也砍了」） */
export function writeTargetPositiveCases() {
  const cases = [
    { name: 'proposal-<date>.md', kind: 'proposal-md', target: path.join(DATA_DIR, 'proposal-2026-09-10.md') },
    { name: '统一日志', kind: 'unified-log', target: LOG_FILE },
    { name: '日志轮转 .log.1', kind: 'unified-log', target: LOG_FILE + '.1' },
    { name: '自查状态 json', kind: 'selfcheck-state', target: path.join(WRITE_SPEC['selfcheck-state'].base, 'dsh-plugin-reflect-synthesize.json') },
    { name: '自查日志', kind: 'selfcheck-state', target: path.join(WRITE_SPEC['selfcheck-state'].base, 'selfcheck.log') }
  ];
  return cases.map(({ name, kind, target }) => {
    try { return { input: name, ok: true, resolved: guardWritePath(kind, target) }; }
    catch (e) { return { input: name, ok: false, reason: `${e.code}: ${e.message.slice(0, 90)}` }; }
  });
}

/**
 * ⑦ 统一日志：失败也留痕。
 * dry-run 例外（R006 §2 ⑨ 要求 --dry-run **零变更**）：不写盘，只返回本该写入的那一行。
 */
export function log(msg, extra, opts = {}) {
  const line = `[${new Date().toISOString()}] ${msg}` + (extra ? ` ${JSON.stringify(extra)}` : '');
  if (opts.dryRun === true) return line;
  try {
    const p = guardWritePath('unified-log', LOG_FILE);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.appendFileSync(p, line + '\n');
  } catch (e) {
    try { process.stderr.write(`[log-failed] ${String(e && e.message || e)}\n`); } catch { /* 无处可报 */ }
  }
  return line;
}

/** 落盘 proposal-<date>.md（本工具**唯一**的数据产物出口） */
export function writeProposal(date, markdown, opts = {}) {
  const target = path.join(DATA_DIR, `proposal-${date}.md`);
  const abs = guardWritePath('proposal-md', target);
  const bytes = Buffer.byteLength(markdown);
  if (opts.dryRun) return { dryRun: true, target: abs, bytes, sha256: null };
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(abs, markdown);
  return { dryRun: false, target: abs, bytes, sha256: createHash('sha256').update(markdown).digest('hex').slice(0, 16) };
}

/** 自查门状态落盘（② 的落地；路径同样过门） */
export function writeSelfcheckState(pluginName, result) {
  const json = path.join(WRITE_SPEC['selfcheck-state'].base, `${pluginName}.json`);
  const a = guardWritePath('selfcheck-state', json);
  fs.mkdirSync(path.dirname(a), { recursive: true });
  fs.writeFileSync(a, JSON.stringify(result, null, 1));
  const logf = path.join(WRITE_SPEC['selfcheck-state'].base, 'selfcheck.log');
  const b = guardWritePath('selfcheck-state', logf);
  fs.appendFileSync(b, `[${result.ts}] ${pluginName} ok=${result.ok} missing=${result.missing.length} notes=${result.notes.length}\n`);
  return { json: a, log: b };
}

export const OUT_META = Object.freeze({
  logFile: LOG_FILE,
  dataDir: DATA_DIR,
  writeTargets: ALLOWED_WRITE_TARGETS,
  forbiddenTokens: FORBIDDEN_WRITE_TOKENS,
  note: '全包唯一的写副作用模块；所有写调用先过 guardWritePath（治理库路径构造不出来，不是"检查后放行"）'
});
