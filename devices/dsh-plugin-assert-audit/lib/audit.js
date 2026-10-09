/**
 * lib/audit.js — 断言套件审计内核
 *
 * 四个动作（对应「断言审查」这一过程被工具化的四步）：
 *   1. enumerateAssertions  枚举断言调用
 *   2. vacuityScan          空断言 / 恒真 / 弱比较检测
 *   3. predicateCoverage    ★ 同谓词多调用点、只覆盖一个（2026-10-01 实测的最大结构缺口）
 *   4. runMutations         变异测试，三态判定（CAUGHT / SURVIVED / INCONCLUSIVE）
 *
 * 危险原语纪律（⑩）：
 *   · 本文件是全仓库**唯一**的 fs 写入处，且写入前必须过 assertTmpContained()（唯一受控入口）
 *   · 出站命令只允许 ALLOWED_COMMANDS 内的成员，shell:false + 数组实参
 *   · 被测源**只读**打开，绝不写回
 */
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync, readFileSync, openSync, writeSync, closeSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, basename } from 'node:path';
import { VERDICT, assertVerdict, assertTmpContained, assertCommand } from './gate.js';

/* ───────────────────────── 1. 枚举断言 ───────────────────────── */

/**
 * 支持两种形态：
 *   Python: check("名", 条件[, 详情])   /  assert 条件, "名"
 *   JS:     assert(条件, "名")          /  expect(...).toBe(...)
 * 返回 [{line, name, condRaw, kind}]
 */
export function enumerateAssertions(src, lang = 'python') {
  const out = [];
  const lines = src.split('\n');
  lines.forEach((ln, i) => {
    if (lang === 'python') {
      // check("...", <cond> ...) —— 多行也支持（取本行 + 后续 6 行拼接）
      const win = lines.slice(i, i + 7).join('\n');
      const m = win.match(/check\(\s*(['"])((?:\\.|[^'"\\])*)\1\s*,\s*([\s\S]*?)(?:,\s*(['"])(?:\\.|[^'"\\])*\4\s*)?\)\s*$/m);
      if (m && ln.includes('check(')) {
        out.push({ line: i + 1, name: m[2], condRaw: m[3].trim(), kind: 'check' });
      }
      const a = ln.match(/^\s*assert\s+([^,]+)(?:,\s*(['"])(.*?)\2)?\s*$/);
      if (a) out.push({ line: i + 1, name: a[3] || a[1].trim(), condRaw: a[1].trim(), kind: 'assert' });
    } else {
      const m = ln.match(/assert\s*\(([\s\S]*?)\)\s*;?\s*$/);
      if (m && /assert\s*\(/.test(ln)) {
        const parts = m[1].split(/,\s*(?=['"])/);
        out.push({ line: i + 1, name: (parts[1] || '').replace(/['"]/g, '').trim() || parts[0].trim(), condRaw: parts[0].trim(), kind: 'assert' });
      }
    }
  });
  return out;
}

/* ───────────────────── 2. 空断言 / 探针型检测 ───────────────────── */

const TAUTOLOGY = /^(True|true|1|1\s*==\s*1|bool\(1\))$/;
const WEAK_OPS = [/(^|[^<>=!])(>=|<=|!=)([^=]|$)/];
/** 探针型特征：只读取「载体元信息」而不读取「被断言的性质」 */
const PROBE_HINTS = [
  /format 3/i, /\.magic\b/, /startsWith\(['"]SQLite/i, /len\(raw\)\s*>\s*0/, /is_file\(\)/, /exists\(\)/,
];

export function vacuityScan(assertions) {
  const findings = [];
  for (const a of assertions) {
    const c = a.condRaw.replace(/\s+/g, ' ');
    if (TAUTOLOGY.test(c)) {
      findings.push({ line: a.line, name: a.name, type: 'TAUTOLOGY',
        why: `条件恒真（${c}）——永不失败，只虚高通过数` });
      continue;
    }
    if (PROBE_HINTS.some((r) => r.test(c))) {
      findings.push({ line: a.line, name: a.name, type: 'PROBE',
        why: `疑似探针型：条件只看载体元信息（${c.slice(0, 60)}），看不到被断言的性质` });
    }
    if (WEAK_OPS.some((r) => r.test(c))) {
      findings.push({ line: a.line, name: a.name, type: 'WEAK_COMPARE',
        why: `非严格比较（${c.slice(0, 60)}）——可能因错误原因通过` });
    }
  }
  return findings;
}

/* ───────────── 3. 同谓词多调用点、只覆盖一个（本轮最大缺口） ───────────── */

/**
 * @param {object} o
 * @param {string} o.source       被测源码
 * @param {string} o.testSource   断言套件源码
 * @param {string[]} o.tokens     谓词/错误码片段（如 'expires_at > ?'、'NO_ATTEMPT'）
 * @returns [{token, sites, testMentions, verdict}]
 */
export function predicateCoverage({ source, testSource, tokens }) {
  const count = (hay, needle) => hay.split(needle).length - 1;
  return tokens.map((t) => {
    const sites = count(source, t);
    const testMentions = count(testSource, t);
    let verdict = 'OK';
    if (sites > 1 && testMentions <= 1) verdict = 'MULTI_SITE_SINGLE_COVER';
    else if (sites === 0) verdict = 'TOKEN_NOT_FOUND';
    return { token: t, sites, testMentions, verdict };
  });
}

/** 自动抽出源码里的错误码（raise RuntimeError("CODE: ...") / throw new Error('CODE')） */
export function extractErrorCodes(source) {
  const set = new Set();
  for (const m of source.matchAll(/raise\s+\w+\(\s*f?["']([A-Z][A-Z0-9_]{2,})[:：]/g)) set.add(m[1]);
  for (const m of source.matchAll(/GateError\(\s*['"]([A-Z][A-Z0-9_]{2,})['"]/g)) set.add(m[1]);
  return [...set];
}

/* ───────────────────────── 4. 变异测试 ───────────────────────── */

/**
 * ★ 三态判定 —— 本工具存在的理由。
 * 2026-10-01 实测教训：把「变异体自己崩了」判成「存活」，会让审查得出反向结论。
 * 因此：**没有汇总行 / 出现语法错或绑定错 → INCONCLUSIVE，绝不判 CAUGHT 或 SURVIVED。**
 */
export function classify({ code, stdout, stderr }) {
  const out = String(stdout || '');
  const err = String(stderr || '');
  const fails = (out.match(/^\s*FAIL\b.*$/gm) || []).map((s) => s.trim());

  // (a) 变异体自身无效 / 环境错 → 不可判，绝不冒充结论
  if (/SyntaxError|IndentationError|Incorrect number of bindings|ModuleNotFoundError|ImportError|NameError/.test(err)) {
    return { verdict: assertVerdict(VERDICT.INCONCLUSIVE), reason: '变异体自身无效（语法/绑定/导入错）', fails };
  }
  // (b) 无汇总行 = 套件未跑完（崩溃） → 不可判
  const summary = out.match(/(\d+)\s*PASS\s*\/\s*(\d+)\s*FAIL/i);
  if (!summary) {
    return { verdict: assertVerdict(VERDICT.INCONCLUSIVE), reason: '无汇总行（套件未跑完/崩溃）', fails };
  }
  // (c) 有 FAIL → 变异被捕获
  if (Number(summary[2]) > 0 || fails.length > 0) {
    return { verdict: assertVerdict(VERDICT.CAUGHT), reason: `红 ${Math.max(Number(summary[2]), fails.length)} 条`, fails };
  }
  // (d) 汇总行全绿 → 真存活（覆盖有洞）
  return { verdict: assertVerdict(VERDICT.SURVIVED), reason: '断言全绿 ⇒ 覆盖有洞', fails: [] };
}

/** ★ ③ 唯一受控入口：全仓库唯一的 fs 写入 */
function writeMutant(dir, name, content) {
  const p = join(dir, name);
  assertTmpContained(p, tmpdir());            // 门：越界即抛 GateError
  const fd = openSync(p, 'w');
  try { writeSync(fd, content); } finally { closeSync(fd); }
  return p;
}

/**
 * @param {object} o
 * @param {string} o.sourcePath   被测源码（只读）
 * @param {Array<{name, old, new}>} o.mutants
 * @param {string[]} o.runArgs    运行参数（如 ['selftest']）
 * @param {string} o.runner       必须是 ALLOWED_COMMANDS 成员
 */
export function runMutations({ sourcePath, mutants, runArgs = [], runner = 'python3' }) {
  assertCommand(runner);
  const src = readFileSync(sourcePath, 'utf8');   // 只读
  const dir = mkdtempSync(join(tmpdir(), 'assert-audit-'));
  const results = [];
  try {
    for (const m of mutants) {
      const hits = src.split(m.old).length - 1;
      if (hits !== 1) {                            // ★ 锚点必须唯一（实测踩过：出现 2 次只改中 1 次）
        results.push({ name: m.name, verdict: VERDICT.INCONCLUSIVE,
          reason: `锚点出现 ${hits} 次（必须唯一，否则改的不是想改的调用点）`, fails: [] });
        continue;
      }
      const mutated = src.replace(m.old, m.new);
      const p = writeMutant(dir, `${basename(sourcePath)}.${results.length}.mut`, mutated);
      let code = 0; let stdout = ''; let stderr = '';
      try {
        const guardedRunner = assertCommand(runner);      // ★ 紧邻出站点的门（F 项窗口内可解析）
        stdout = execFileSync(guardedRunner, [p, ...runArgs], {
          encoding: 'utf8', timeout: 300000, shell: false,          // ★ shell:false
          cwd: dir, stdio: ['ignore', 'pipe', 'pipe'],
        });
      } catch (e) {
        code = typeof e.status === 'number' ? e.status : 1;
        stdout = String(e.stdout || '');
        stderr = String(e.stderr || '');
      }
      const c = classify({ code, stdout, stderr });
      results.push({ name: m.name, ...c, exit: code, mutantPath: p });
    }
  } finally {
    try { rmSync(dir, { recursive: true, force: true }); } catch { /* 清理失败不掩盖主结论 */ }
  }
  const tally = {
    total: results.length,
    [VERDICT.CAUGHT]: results.filter((r) => r.verdict === VERDICT.CAUGHT).length,
    [VERDICT.SURVIVED]: results.filter((r) => r.verdict === VERDICT.SURVIVED).length,
    [VERDICT.INCONCLUSIVE]: results.filter((r) => r.verdict === VERDICT.INCONCLUSIVE).length,
  };
  // ★ INCONCLUSIVE 不得被计为 CAUGHT（结构性保证：三者互斥且必须分别报出）
  const consistent = tally[VERDICT.CAUGHT] + tally[VERDICT.SURVIVED] + tally[VERDICT.INCONCLUSIVE] === tally.total;
  return { results, tally, consistent };
}

/* ───────────────────────── 汇总 ───────────────────────── */

export function audit({ sourcePath, testSourcePath, tokens = [], mutants = [], runArgs = [], runner = 'python3' }) {
  const source = readFileSync(sourcePath, 'utf8');
  const testSource = readFileSync(testSourcePath, 'utf8');
  const assertions = enumerateAssertions(testSource, testSourcePath.endsWith('.py') ? 'python' : 'js');
  const vacuity = vacuityScan(assertions);
  const codes = extractErrorCodes(source);
  const predicates = predicateCoverage({ source, testSource, tokens: [...tokens, ...codes] });
  const mutation = mutants.length ? runMutations({ sourcePath, mutants, runArgs, runner }) : null;
  return { sourcePath, testSourcePath, assertions, vacuity, predicates, mutation };
}
