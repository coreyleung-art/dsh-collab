import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import { STAGES, STAGE_IMPL, HUMAN_GATED, assertRunnable, assertStage } from './gate.js';
import { log } from './logger.js';

const H = os.homedir();
const expand = (p) => p.replace(/^~/, H);

/** 各环节的产物判据（用于断点续跑） */
export function artifactsFor(stage, date, workdir) {
  const w = expand(workdir);
  const d = String(date);                 // 2026-09-10
  const dc = d.replace(/-/g, '');         // 20260910
  // ★ 发现式判据（2026-09-10 结构性修复）
  //   原版硬编码路径是我**猜**的（建编排器时子插件还不存在）→ 三处全错：
  //     · collect  产 events-20260910.json（无连字符），我猜 events-2026-09-10.json
  //     · dispatch 产 cards/<device>/20260910/（带设备层），我猜 cards/2026-09-10
  //   这正是「指称完整性」：**我断言的路径是想象出来的，不是读出来的。**
  //   现改为：列出目录 → 找包含日期标记的项。
  const hasDate = (name) => name.includes(d) || name.includes(dc);
  const listen = (dir) => {
    try { return fs.readdirSync(dir); } catch { return []; }
  };
  switch (stage) {
    case 'collect':
      return listen(w).filter((f) => f.startsWith('events-') && hasDate(f)).map((f) => path.join(w, f));
    case 'dispatch': {
      const cardsRoot = path.join(w, 'cards');
      const hits = [];
      for (const dev of listen(cardsRoot)) {
        const devDir = path.join(cardsRoot, dev);
        if (!fs.statSync(devDir, { throwIfNoEntry: false })?.isDirectory()) continue;
        // cards/<device>/<date>/  或  cards/<device>/<date>.md
        for (const e of listen(devDir)) {
          if (hasDate(e)) hits.push(path.join(devDir, e));
        }
      }
      return hits;
    }
    case 'harvest':
      return listen(w).filter((f) => f.startsWith('harvested-') && hasDate(f)).map((f) => path.join(w, f));
    case 'synthesize':
      return listen(w).filter((f) => f.startsWith('proposal-') && hasDate(f)).map((f) => path.join(w, f));
    case 'enroll':
      return listen(w).filter((f) => f.startsWith('feedback-') && hasDate(f)).map((f) => path.join(w, f));
    default:
      return [];
  }
}

export function isDone(stage, date, workdir) {
  const arts = artifactsFor(stage, date, workdir);
  if (arts.length === 0) return false;
  // ★ 候选路径是「或」关系（命名容错），故用 some 而非 every。
  //   2026-09-10 二次自查：我加容错时错用了 every，导致 harvest/synthesize 从 ✅ 变成 ⏳
  //   —— 又一次「改完不验证」。同一函数里两处都改过，第二次才改对。
  return arts.some((p) => fs.existsSync(p));
}

export function status(date, workdir) {
  return STAGES.map((s) => ({
    stage: s,
    plugin: STAGE_IMPL[s].plugin,
    human_gated: HUMAN_GATED.includes(s),
    done: isDone(s, date, workdir),
    artifacts: artifactsFor(s, date, workdir),
  }));
}

/**
 * 跑流水线
 * @param {object} o { root, date, workdir, upto, only, dryRun, autoRunEnroll }
 */
export function runPipeline(o) {
  const { root, date, workdir, dryRun } = o;
  const uptoIdx = o.upto ? STAGES.indexOf(assertStage(o.upto)) : STAGES.length - 1;
  const results = [];

  for (let i = 0; i < STAGES.length; i++) {
    const stage = STAGES[i];
    if (o.only && o.only.length && !o.only.includes(stage)) continue;
    if (i > uptoIdx) { results.push({ stage, action: '超出 --upto 范围', skipped: true }); continue; }

    // ★ 人裁环节：即使在范围内也不自动跑
    if (HUMAN_GATED.includes(stage) && !o.autoRunEnroll) {
      results.push({ stage, action: '跳过（需人裁）', skipped: true, human_gated: true });
      continue;
    }

    // 断点续跑：已完成则跳过
    if (isDone(stage, date, workdir)) {
      results.push({ stage, action: '已完成（跳过）', skipped: true, resumed: true });
      continue;
    }

    const impl = STAGE_IMPL[stage];
    const cli = path.join(root, 'devices', impl.plugin, impl.cli);
    if (!fs.existsSync(cli)) {
      results.push({ stage, action: '插件未就位（跳过）', skipped: true, missing_tool: true });
      continue;
    }

    if (dryRun) {
      const shown = impl.args.map((a) => String(a).replace('{date}', date));
      results.push({ stage, action: `将执行 node ${impl.plugin}/${impl.cli} ${shown.join(' ')}`, dry_run: true });
      continue;
    }

    // ★ {date} 占位符展开（2026-09-10 结构性修复：参数也改为显式携带日期，
    //   原版漏传导致 dispatch exit 2「需要 --events 或 --devices 或 --date」）
    const argv = impl.args.map((a) => String(a).replace('{date}', date));
    const r = spawnSync('node', [cli, ...argv], { encoding: 'utf8', timeout: 120000 });
    const ok = r.status === 0;
    log({ stage, cmd: cli, exit: r.status, ok });
    results.push({
      stage, action: ok ? '完成' : `失败（exit ${r.status}）`,
      exit: r.status, ok,
      stdout_tail: (r.stdout || '').split('\n').slice(-8).join('\n'),
      stderr_tail: (r.stderr || '').split('\n').slice(-4).join('\n'),
    });
    // ★ 失败即停（⑩ F 项）：不继续往下跑
    if (!ok) { results.push({ stage: '-', action: '因上一步失败而中止（失败即停）', aborted: true }); break; }
  }
  return results;
}
