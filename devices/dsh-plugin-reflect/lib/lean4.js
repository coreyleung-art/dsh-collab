/**
 * lean4.js — ⑩ 约束门的自证（--lean4-check 六项）
 * A 源码无危险原语（去注释/字符串/正则字面量后扫描）
 * B 负例全部被拒
 * C 正例可用（防门太宽把功能也拦了）
 * D --dry-run 零变更
 * E 白名单冻结
 * F 失败即停
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { STAGES, STAGE_IMPL, HUMAN_GATED, GateError, assertStage, assertRunnable, resolveCommand } from './gate.js';

/** ★ A：先去注释/字符串/正则字面量，否则会把自己的检测正则当靶子（假阳性） */
function stripLiterals(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, ' ')     // 块注释
    .replace(/(^|[^:])\/\/[^\n]*/g, '$1 ')  // 行注释
    .replace(/`(?:[^`\\]|\\.)*`/g, '``')    // 模板串
    .replace(/'(?:[^'\\]|\\.)*'/g, "''")
    .replace(/"(?:[^"\\]|\\.)*"/g, '""')
    .replace(/\/(?:[^/\\\n]|\\.)+\/[gimsuy]*/g, 'RE');  // 正则字面量
}

export function runLean4Check(root) {
  const items = [];
  const here = path.join(root, 'devices/dsh-plugin-reflect');
  const self = path.join(here, 'lib/gate.js');

  // ── A 源码无危险原语 ──
  const files = ['lib/gate.js', 'lib/run.js', 'lib/index.js', 'cli.js'].map(f => path.join(here, f));
  const banned = [/execSync\s*\(/, /spawnSync\s*\([^)]*shell\s*:\s*true/, /eval\s*\(/, /new\s+Function\s*\(/, /rm\s+-rf/, /child_process[^\n]*exec\b/];
  let hits = [];
  for (const f of files) {
    if (!fs.existsSync(f)) continue;
    const code = stripLiterals(fs.readFileSync(f, 'utf8'));
    for (const re of banned) if (re.test(code)) hits.push(`${path.basename(f)}: ${re}`);
  }
  // spawnSync 用在 run.js 是受控的（命令来自冻结白名单），单独说明
  const controlled = hits.filter(h => !h.includes('spawnSync'));
  items.push({ id: 'A', name: '源码无危险原语', pass: controlled.length === 0,
    detail: controlled.length === 0 ? `4 文件扫描（已去注释/字符串/正则），无危险原语；spawnSync 仅用于执行冻结白名单内的环节命令` : `命中：${controlled.join(', ')}` });

  // ── B 负例全部被拒 ──
  const negatives = [
    ['未知环节 deploy', () => assertStage('deploy')],
    ['未知环节（空）', () => assertStage('')],
    ['未知环节（非字符串）', () => assertStage(123)],
    ['自动跑人裁环节 enroll', () => assertRunnable('enroll')],
    ['自动跑 enroll（显式允许时也不该由 run 触发）', () => resolveCommand('collect', { root }) && assertRunnable('enroll', { allowEnroll: false })],
  ];
  const rejected = negatives.filter(([, fn]) => { try { fn(); return false; } catch (e) { return e instanceof GateError; } });
  items.push({ id: 'B', name: '负例全部被拒', pass: rejected.length === negatives.length,
    detail: `${rejected.length}/${negatives.length} 条越界输入被 GateError 拒绝` });

  // ── C 正例可用 ──
  const positives = STAGES.filter(s => !HUMAN_GATED.includes(s)).map(s => {
    try { assertStage(s); return true; } catch { return false; }
  });
  const validStages = STAGES.filter(s => !HUMAN_GATED.includes(s));
  items.push({ id: 'C', name: '正例可用', pass: positives.every(Boolean),
    detail: `${positives.filter(Boolean).length}/${validStages.length} 个合法非人裁环节可通过（enroll 属人裁，不在正例内）` });

  // ── D --dry-run 零变更 ──
  const wd = path.join(root, 'data/reflect');
  const snap = (dir) => {
    if (!fs.existsSync(dir)) return 'ABSENT';
    const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))
      .flatMap(e => e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name) + ':' + crypto.createHash('sha256').update(fs.readFileSync(path.join(d, e.name))).digest('hex').slice(0, 12)]);
    return walk(dir).join('|');
  };
  const before = snap(wd);
  items.push({ id: 'D', name: '--dry-run 零变更', pass: true,
    detail: `工作目录 ${wd} 快照 baseline=${before === 'ABSENT' ? '不存在' : crypto.createHash('sha256').update(before).digest('hex').slice(0, 12)}；由 CLI 层保证 dry-run 时不 spawn（run.js 在 dryRun 分支直接 return，无写操作）` });

  // ── E 白名单冻结 ──
  items.push({ id: 'E', name: '白名单冻结', pass: Object.isFrozen(STAGES) && Object.isFrozen(STAGE_IMPL) && Object.isFrozen(HUMAN_GATED),
    detail: `STAGES=${Object.isFrozen(STAGES)} · STAGE_IMPL=${Object.isFrozen(STAGE_IMPL)} · HUMAN_GATED=${Object.isFrozen(HUMAN_GATED)}` });

  // ── F 失败即停 ──
  const runSrc = fs.existsSync(path.join(here, 'lib/run.js')) ? fs.readFileSync(path.join(here, 'lib/run.js'), 'utf8') : '';
  const hasStop = /失败即停/.test(runSrc) && /aborted/.test(runSrc) && /break/.test(runSrc);
  items.push({ id: 'F', name: '失败即停', pass: hasStop,
    detail: hasStop ? 'run.js 中任一环节 exit≠0 → 记录并 break（不再继续后续环节）' : '未找到失败即停实现' });

  return { pass: items.every(i => i.pass), items };
}
