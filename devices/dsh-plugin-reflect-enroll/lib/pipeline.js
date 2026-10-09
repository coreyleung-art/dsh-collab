/**
 * pipeline.js — 入册 + 反馈 的总编排（CLI 与宿主工具共用同一条代码路径）
 * =============================================================================
 * 唯一入口形态：**用户裁定**（裁定文件或单条 --rule）。
 * 本模块不导出任何"没有裁定也能跑"的函数 —— 没有那个入口（R006 ⑩）。
 *
 * 跨设备层（v1.1）：设备名 → 相关智能体 `<device>:<agent>` → 反馈卡上本机+中央黑板 → 短指引进待投递队列。
 */
import {
  resolveRoot, loadRulings, loadProposals, parseRuleSpec, enrollAll, todayDate, UsageError
} from './enroll.js';
import {
  resolveRelatedAgents, buildFeedbackCard, publishFeedback, resolveDeviceName,
  LOCAL_BB_DEFAULT, CENTRAL_BB_DEFAULT, noticeKey, fullCardKey, writeFeedbackCard
} from './feedback.js';
import { log } from './log.js';
import { VERSION } from './version.js';

export async function runPipeline({
  root, rulingFile, ruleSpec, proposalFile, date, dryRun = false, notify = false,
  localBb, centralBb, device, noBb = false, now
} = {}) {
  const r = resolveRoot(root);
  const ts = (now || new Date()).toISOString();
  let rulings;
  let rulingSource;
  let d = date || todayDate();

  if (ruleSpec) {
    if (rulingFile) throw new UsageError('--rule 与 --ruling 只能二选一');
    rulings = [parseRuleSpec(ruleSpec)];
    rulingSource = `cli:--rule ${ruleSpec}`;
  } else {
    const f = loadRulings(r, { file: rulingFile, date: d });
    rulings = f.rulings;
    rulingSource = f.abs;
    d = f.date || d;
  }

  const dev = resolveDeviceName(r, device);
  const props = loadProposals(r, { file: proposalFile, date: d });
  if (props.note) log('pipeline.proposals-fallback', { input: { date: d }, judge: { used: props.abs }, result: { ok: true, note: props.note } });
  log('pipeline.start', {
    input: { root: r, rulingSource, proposals: props.abs, rulingCount: rulings.length, date: d, device: dev.device },
    judge: { dryRun, notify, noBb },
    result: { ok: null }
  });

  const out = enrollAll({ root: r, rulings, proposals: props.map, dryRun, date: d });
  const related = resolveRelatedAgents({ root: r, results: out.results, proposals: props.map, localDevice: dev.device });
  const card = buildFeedbackCard({ date: out.date, results: out.results, related, ts, device: dev.device });

  let feedback;
  if (noBb) {
    feedback = {
      cardKey: noticeKey(out.date), fullCardKey: fullCardKey(out.date),
      skipped: true, reason: '--no-bb：跳过黑板写入与消息推送（反馈卡仍落盘并脱敏）',
      boards: { local: [], central: [] }, notify: [],
      landed: false, landed_local: false, landed_central: false, redactions: []
    };
    if (!dryRun) {
      feedback.card = writeFeedbackCard(r, out.date, card);
      feedback.redactions = feedback.card.redactions;
    }
  } else {
    feedback = await publishFeedback({
      root: r, date: out.date, card, related, results: out.results,
      localBb: localBb || LOCAL_BB_DEFAULT, centralBb: centralBb || CENTRAL_BB_DEFAULT,
      notify, dryRun, ts, device: dev.device
    });
  }

  const enrollOk = out.results.every((x) => x.outcome === 'deferred' || x.applied || x.dryRun);
  const feedbackOk = dryRun || feedback.skipped || feedback.landed === true;
  const ok = enrollOk && feedbackOk;

  const result = {
    ok, dryRun, root: r, date: out.date, stamp: out.stamp, version: VERSION,
    device: dev, rulingSource, proposalSource: props.abs || null, proposalNote: props.note || null,
    results: out.results.map((x) => ({
      proposal_id: x.proposal_id, decision: x.decision, target: x.target, outcome: x.outcome, ref: x.ref,
      summary: x.summary, applied: !!x.applied, dryRun: !!x.dryRun,
      wrote: x.wrote || [], backups: x.backups || [], verified: x.verified || null,
      rolledBack: x.rolledBack || [], notes: x.notes || [],
      planned: (x.writes || []).map((w) => ({ rel: w.rel, bytes: Buffer.byteLength(w.after || '', 'utf8'), existed: w.exists }))
    })),
    feedback: {
      cardKey: feedback.cardKey, fullCardKey: feedback.fullCardKey,
      card: feedback.card || null,
      local_bb: feedback.local_bb || (localBb || LOCAL_BB_DEFAULT),
      central_bb: feedback.central_bb || (centralBb || CENTRAL_BB_DEFAULT),
      boards: feedback.boards || { local: [], central: [] },
      landed: !!feedback.landed, landed_local: !!feedback.landed_local, landed_central: !!feedback.landed_central,
      notify: feedback.notify || [], notify_ok: feedback.notify_ok === undefined ? null : feedback.notify_ok,
      redactions: feedback.redactions || [],
      skipped: !!feedback.skipped, reason: feedback.reason || null
    },
    related,
    cardPreview: card,
    ledger: out.ledger
  };
  log('pipeline.done', {
    input: { rulingSource, device: dev.device },
    judge: { ok, enrollOk, feedbackOk, dryRun },
    result: {
      outcomes: result.results.map((x) => `${x.proposal_id}:${x.outcome}:${x.ref || '-'}`),
      cardKey: feedback.cardKey, fullCardKey: feedback.fullCardKey,
      landedLocal: result.feedback.landed_local, landedCentral: result.feedback.landed_central,
      redactions: result.feedback.redactions.length
    }
  });
  return result;
}
