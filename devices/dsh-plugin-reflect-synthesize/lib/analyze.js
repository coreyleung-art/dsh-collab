/**
 * analyze.js — 第 1 步（对照现有库）+ 第 2 步（分类归档）
 * =============================================================================
 * ★ 本工具是全流水线里**唯一需要"判断"**的环节。设计原则只有一条：
 *
 *   规则能定的用规则；规则定不了的**显式标 `unclear` 交人工/LLM 复核**，不许强行归类。
 *
 * 为什么"不许硬猜"不是洁癖：synthesize 的输出会变成用户裁定的依据。
 * 一个被硬猜出来的 `already-application`（"已有规则覆盖了"）会让一条真正的盲区
 * **连被看见的机会都没有** —— 它被归进"无需动作"那一档，然后消失。
 * 反之 `unclear` 会让用户多看一眼，代价只是几秒钟。两种错的代价不对称，所以默认取 `unclear`。
 *
 * 机械判定能做到的部分（可复现、可审计）：
 *   - `related_rule` 是不是真实存在的条目（去库里核对）
 *   - lesson 与条目的**关键词重合度**（字符 bigram 交集计数）
 *   - 相对该条目有没有**新词**（novelty）→ 是"重复"还是"补维"
 *   - 智能体自己声明的处置倾向（suggestion.type）
 * 做不到的部分（必须交人）：
 *   - "这句话和那条规则是不是在说同一件事"（同义/换述/蕴含）
 *   - "这条和那条规则冲突吗"（冲突是语义判断；工具只认**显式**冲突措辞）
 *   - 多条目并列命中时该并给谁
 */
import { JUDGMENTS, JUDGE_RULE } from './gate.js';
import { bigrams, normalizeLesson } from './lesson.js';

/**
 * 从 lesson 里切出**该条目词表未覆盖的连续片段**（给用户看的"新词"）。
 *
 * 为什么需要：bigram 是内部表示，直接把 bigram 列表给用户看会得到「证证、据要、要标、注采」这种碎片 ——
 * 那是**渲染层把实现细节泄漏给用户**，看起来像乱码，反而让人不敢裁。
 *
 * 做法：在**归一化后的 lesson 原文**上滑动，标出「其 bigram 不在该条目词表里」的位置，
 * 取连续的 fresh 段（多字符）作为新词。输出是「采集时点」「标注」这类**真词**。
 * 注意：初版我用"把 bigram 首尾拼起来"的写法，结果只拼出 3 个字符、丢了中间（实测「前集时」而非「前采集时」）
 * —— 所以这里直接回到原文字符串上取子串，不再从 bigram 反推。
 */
export function freshFragments(lessonNorm, vocab, max = 3, minLen = 3) {
  const t = String(lessonNorm || '');
  const out = [];
  let i = 0;
  while (i + 1 < t.length) {
    if (vocab.has(t.slice(i, i + 2))) { i++; continue; }
    let k = i;
    while (k + 1 < t.length && !vocab.has(t.slice(k, k + 2))) k++;
    const frag = t.slice(i, k + 2);        // 覆盖 fresh bigram i..k 的原文子串
    if (frag.length >= minLen) out.push(frag);
    i = k + 1;
  }
  return out.sort((a, b) => b.length - a.length || a.localeCompare(b)).slice(0, max);
}

/** 显式冲突措辞（**只**认这些；工具不猜语义冲突） */
const CONFLICT_PATTERNS = Object.freeze([
  // 「与 R006 直接冲突」这种中间夹修饰语的写法也要认（实测：初版只允许紧邻，把真信号漏了）
  /(?:与|和|跟|同)\s*(R\d{3}|J\d+|phi-[a-z0-9-]+)\s*[^，。；;\n]{0,8}?(?:相?冲突|矛盾|相悖|不一致|不符)/,
  /(?:推翻|废止|取代|作废)\s*(?:R\d{3}|J\d+|phi-[a-z0-9-]+)/,
  /(R\d{3}|J\d+|phi-[a-z0-9-]+)\s*(?:已|已经)?(?:失效|过时|不再适用)/
]);

/** 规则信号词（用于"该立规则"还是"该立哲学"的**启发式**，并明确标注只是启发式） */
const RULE_HINTS = Object.freeze(['禁止', '不得', '一律', '每次', '步骤', '流程', '清单', 'SOP', '登记', '校验', '参数', '字段', '模板', '脚本', '工具', '调用', '超时', '重试', '阈值', '拒收', '质量门', '门禁', '拦截', '前置', '门槛', '阻断', '检查项']);
/** 哲学信号词（讲的是信息/系统的**固有属性**或**原理**，而不是操作步骤） */
const PHILOSOPHY_HINTS = Object.freeze(['本质', '固有', '属性', '规律', '不可避免', '总会', '必然', '原理', '维度', '范畴', '就是', '意味着', '一旦', '即', '律']);

/**
 * 对照现有库：判定一个 cluster 与现有规则/哲学的关系。
 * @param {object} cluster harvested 的 cluster
 * @param {object} catalog { rules: Map<id,entry>, phis: Map<id,entry> }
 * @returns {object} 判定结果（含依据，供审计）
 */
export function judgeCluster(cluster, catalog) {
  const lesson = String(cluster.lesson || '');
  const text = [lesson, ...(cluster.members || []).map((m) => String(m.pit || ''))].join('\n');
  const grams = bigrams(lesson);
  const lessonNorm = normalizeLesson(lesson);

  // ── refs：智能体自己填的规则号/哲学号，逐个去库里核对
  const refs = [];
  for (const r of cluster.refs || []) {
    if (!r || r === '无') continue;
    const rule = catalog.rules.get(r);
    const phi = catalog.phis.get(r);
    if (rule) refs.push({ ref: r, kind: 'rule', id: r, title: rule.title, exists: true });
    else if (phi) refs.push({ ref: r, kind: 'phi', id: r, title: phi.title, exists: true });
    else refs.push({ ref: r, kind: 'unknown', id: r, title: null, exists: false });
  }
  const knownRefs = refs.filter((r) => r.exists);

  // ── 关键词重合：对**全部**条目算（不只 refs），否则"没填规则号但其实已被覆盖"会漏判
  const scored = [];
  for (const [, e] of [...catalog.rules, ...catalog.phis]) {
    let inter = 0;
    let freshCount = 0;
    for (const g of grams) { if (e.vocab.has(g)) inter++; else freshCount++; }
    if (inter > 0) scored.push({
      kind: e.kind, id: e.id, title: e.title, overlap: inter, novelty: freshCount,
      top: freshFragments(lessonNorm, e.vocab, 3)   // 给用户看的：可读新词（原文字串，不是 bigram 碎片）
    });
  }
  scored.sort((a, b) => b.overlap - a.overlap || a.id.localeCompare(b.id));
  const best = scored[0] || null;

  // ── 显式冲突（只认显式措辞）
  let explicitConflict = null;
  for (const p of CONFLICT_PATTERNS) {
    const m = text.match(p);
    if (m) { explicitConflict = { pattern: String(p), hit: m[0] }; break; }
  }

  const types = [...new Set((cluster.members || []).map((m) => m.suggestion && m.suggestion.type).filter(Boolean))];
  const deviceCount = (cluster.devices || []).length;

  // ── 判定用的派生量（全部可审计）
  const second = scored[1] || null;
  const lessonGrams = grams.size || 1;
  const coverage = best ? best.overlap / lessonGrams : 0;                       // 本 lesson 有多大比例被该条目覆盖
  const decisive = !!best && best.overlap >= Math.max(JUDGE_RULE.decisiveMin, JUDGE_RULE.decisiveFactor * (second ? second.overlap : 0));
  const isRealMatch = !!best && best.overlap >= JUDGE_RULE.minMatch;
  // 引用的条目与"内容上的最佳匹配"对不上 → 智能体填的规则号可能不准，交人确认
  const refIds = new Set(knownRefs.map((r) => r.id));
  const refMismatch = knownRefs.length > 0 && !(best && refIds.has(best.id) && isRealMatch);
  const hasUnknownRef = refs.some((r) => !r.exists);

  let judgment, confidence, why;

  if (explicitConflict) {
    judgment = 'conflicts';
    confidence = 'medium';
    why = `检测到**显式冲突措辞**「${explicitConflict.hit}」—— 仅凭显式措辞判定，语义是否真冲突需人工确认`;
  } else if (hasUnknownRef) {
    // 引用了**不存在**的条目：机器无法确定它想关联谁（笔误？还是尚未存在的新条目？）→ 不猜
    judgment = 'unclear';
    confidence = 'low';
    why = `引用了**不存在的**条目号（${refs.filter((r) => !r.exists).map((r) => r.id).join('/')}）—— 是笔误还是尚未存在的新条目？机器无法判定，须人工确认后再归类`;
  } else if (isRealMatch && decisive && best.overlap >= JUDGE_RULE.minMatch && coverage >= JUDGE_RULE.coverageMin &&
             types.length === 1 && types[0] === '无需动作') {
    judgment = 'already-application';
    confidence = 'high';
    why = `智能体自评「无需动作」；本 lesson 的 ${best.overlap} 个关键词被 ${best.kind === 'phi' ? '哲学' : '规则'} ${best.id}（${best.title}）覆盖` +
      `（覆盖率 ${(coverage * 100).toFixed(0)}% ≥ ${JUDGE_RULE.coverageMin * 100}%，且明显领先第二名 ${second ? second.overlap : 0}）→ 属已有条目的**应用**，不是新条目`;
  } else if (isRealMatch && decisive && best.novelty >= JUDGE_RULE.noveltyMin) {
    judgment = 'extends-existing';
    confidence = 'medium';
    why = `与 ${best.kind === 'phi' ? '哲学' : '规则'} ${best.id}（${best.title}）关键词重合 ${best.overlap}` +
      `（明显领先第二名 ${second ? second.overlap : 0}），同时带 ${best.novelty} 个该条目词表外的关键词（如 ${best.top.join('、') || '—'}）` +
      `→ 像**补维/延伸**而非重复`;
  } else if (!isRealMatch) {
    judgment = 'new-dimension';
    confidence = 'medium';
    why = `与全部 ${catalog.rules.size + catalog.phis.size} 条现有条目的最高关键词重合仅 ${best ? best.overlap : 0} < ${JUDGE_RULE.minMatch}` +
      `（低于该阈值的重合属于中文短句间的偶然噪音，实测无关 lesson 也会共享 1-2 个 bigram）→ 现有关键词层**未覆盖**`;
  } else {
    judgment = 'unclear';
    confidence = 'low';
    why = `机械判定不足以下结论：${whyGap(knownRefs, best, second, types, decisive)} —— ★ 这一步需要**语义判断**，工具只做筛选与提示，不硬猜`;
  }

  return {
    judgment,
    judgment_reason: why,
    confidence,
    refs,
    matched: scored.slice(0, 3),
    best_match: best,
    novelty_vs_best: best ? best.novelty : null,
    coverage: Number(coverage.toFixed(3)),
    decisive,
    second_match: second ? { kind: second.kind, id: second.id, overlap: second.overlap } : null,
    ref_mismatch: refMismatch,
    has_unknown_ref: hasUnknownRef,
    declared_types: types,
    explicit_conflict: explicitConflict,
    cross_device: deviceCount >= 2,
    device_count: deviceCount,
    needs_human: judgment === 'unclear' || confidence !== 'high'
  };
}

function whyGap(knownRefs, best, second, types, decisive) {
  const bits = [];
  if (!decisive && second) bits.push(`最佳匹配 ${best.id}（${best.overlap}）与第二名 ${second.id}（${second.overlap}）**未拉开差距** → 无法确定该并给谁`);
  if (best && best.overlap >= JUDGE_RULE.minMatch && best.novelty < JUDGE_RULE.noveltyMin) bits.push(`与 ${best.id} 重合 ${best.overlap} 但不带新词（novelty ${best.novelty}）—— 可能是重复，也可能是同一件事的另一种说法`);
  if (knownRefs.length) bits.push(`智能体引用了 ${knownRefs.map((r) => r.id).join('/')}，但内容上的最佳匹配是 ${best ? best.id : '（无）'}`);
  if (types.includes('修订')) bits.push('有智能体主张「修订」既有条目，是否构成冲突属语义判断');
  if (!bits.length) bits.push('命中多条现有条目或判定条件不满足');
  return bits.join('；');
}

/**
 * 第 2 步 · 分类归档。
 * @returns {{category:string, target:object|null, snippet:object, needs_human:boolean, rationale:string}}
 */
export function classify(cluster, j) {
  const types = j.declared_types;
  const text = [cluster.lesson, ...(cluster.members || []).map((m) => String(m.pit || ''))].join('\n');

  if (j.judgment === 'already-application') {
    return {
      category: '归档为案例',
      target: { kind: j.best_match.kind, id: j.best_match.id, title: j.best_match.title },
      snippet: null,
      needs_human: false,
      rationale: `已有 ${j.best_match.id}（${j.best_match.title}）覆盖；本条作为**应用案例**登记，不新增条目`
    };
  }
  if (j.judgment === 'extends-existing') {
    return {
      category: '并入/补维',
      target: { kind: j.best_match.kind, id: j.best_match.id, title: j.best_match.title },
      snippet: buildSnippet(cluster, j, 'phi'),
      needs_human: true,
      rationale: `并入 ${j.best_match.id}（${j.best_match.title}）：补的是「${(j.best_match.top || []).join('、') || '新维度'}」这一维`
    };
  }
  if (j.judgment === 'conflicts') {
    return {
      category: '需裁决冲突',
      target: null,
      snippet: null,
      needs_human: true,
      rationale: `显式冲突措辞「${j.explicit_conflict.hit}」—— 需用户裁决：是修订现有条目、还是本条理解有误`
    };
  }
  if (j.judgment === 'new-dimension') {
    if (types.includes('转规范')) {
      return {
        category: '转规范',
        target: { kind: 'sop', id: guessSop(text), title: guessSop(text) },
        snippet: null,
        needs_human: true,
        rationale: `智能体主张「转规范」；目标 SOP 由关键词推测（${guessSop(text)}），**具体归到哪份 SOP 需人工确认**`
      };
    }
    const shape = shapeGuess(text);
    return {
      category: shape.kind === 'rule' ? '拟新增规则' : '拟新增哲学',
      target: null,
      snippet: buildSnippet(cluster, j, shape.kind),
      needs_human: true, // ★ 哲学/规则的取舍是启发式，必须让用户一眼看到并可否决
      rationale: `现有条目最高关键词重合 ${j.best_match ? j.best_match.overlap : 0} < ${JUDGE_RULE.minMatch}（未覆盖）；` +
        `内容形态**启发式**偏${shape.kind === 'rule' ? '规则（操作约束/流程）' : '哲学（原理/固有属性）'}（信号词：${shape.hits.join('、') || '无'}；${shape.note}）` +
        ` —— ★ 这只是启发式，请在裁定里明确选哲学还是规则`
    };
  }
  return {
    category: '需人工复核',
    target: null,
    snippet: null,
    needs_human: true,
    rationale: j.judgment_reason
  };
}

/** 规则 vs 哲学的启发式（**明确标注只是启发式**，最终由用户裁定） */
export function shapeGuess(text) {
  const t = String(text);
  const ruleHits = RULE_HINTS.filter((w) => t.includes(w));
  const phiHits = PHILOSOPHY_HINTS.filter((w) => t.includes(w));
  const ruleScore = ruleHits.length;
  const phiScore = phiHits.length;
  const tie = ruleScore === phiScore;
  const kind = phiScore > ruleScore ? 'phi' : (ruleScore > phiScore ? 'rule' : 'phi');
  return {
    kind, ruleScore, phiScore, tie, hits: kind === 'phi' ? phiHits : ruleHits, ruleHits, phiHits,
    note: tie
      ? '哲学/规则信号词打平 → 暂按**哲学**（更一般、不立刻变成硬约束）；若你认为是操作约束，请在裁定里径改为规则'
      : (kind === 'phi' ? '偏哲学（讲的是原理/固有属性）' : '偏规则（讲的是操作约束/流程）')
  };
}

/** 提案片段（一句话 + 理由 + 证据引用 + 与已有条目的关系） */
export function buildSnippet(cluster, j, kind) {
  const ev = (cluster.members || []).slice(0, 3).map((m) => ({
    device: m.device, agent: m.agent, item_id: m.item_id, event_ref: m.event_ref,
    ts: m.evidence ? m.evidence.ts : null, cmd: m.evidence ? m.evidence.cmd : null
  }));
  const oneLine = String(cluster.lesson).replace(/[。；;]\s*$/, '');
  return {
    kind: kind === 'rule' ? '规则' : '哲学',
    one_line: oneLine,
    why: buildWhy(cluster),
    evidence_refs: ev,
    relation: j.best_match
      ? `与 ${j.best_match.id}（${j.best_match.title}）相关：关键词重合 ${j.best_match.overlap}${j.best_match.novelty ? `，另有 ${j.best_match.novelty} 个新关键词` : ''}`
      : '与现有条目无明显关键词关联',
    scope_hint: (cluster.devices || []).length >= 2 ? `跨设备（${cluster.devices.join('、')}）` : `单设备（${(cluster.devices || [])[0] || '?'}）`
  };
}

function buildWhy(cluster) {
  const n = cluster.recurrence;
  const devs = cluster.devices || [];
  const facts = [];
  for (const m of (cluster.members || []).slice(0, 3)) {
    if (m.pit) facts.push(`[${m.device}:${m.agent}] ${String(m.pit).slice(0, 60)}`);
  }
  return `${n} 个独立「设备:智能体」${devs.length >= 2 ? `（跨 ${devs.length} 台设备）` : ''} 各自提到同一件事：${facts.join(' ／ ')}`;
}

/** SOP 归属推测（**明确标注需人工确认**） */
export function guessSop(text) {
  const t = String(text);
  const map = [
    [/凭据|口令|密钥|token|令牌/i, 'SOP-凭据处置'],
    [/重启|launchd|服务|进程|端口/, 'SOP-服务重启与验证'],
    [/数据迁移|导出|导入|备份/, 'SOP-数据迁移'],
    [/部署|发布|上线|推送/, 'SOP-发布与部署'],
    [/日志|轮转|清理/, 'SOP-日志治理'],
    [/会话|上下文|压缩/, 'SOP-会话与存档'],
    [/批量|批处理|断点|检查点/, 'SOP-批量任务'],
    [/黑板|同步|推送|重试/, 'SOP-跨设备同步']
  ];
  for (const [re, sop] of map) if (re.test(t)) return sop;
  return '待定（工具不猜）';
}

/** 复现广度排序键：★ (cross_device, recurrence) 二元组 —— 跨设备优先（design §10.7） */
export function sortKey(cluster, j) {
  const cd = (cluster.devices || []).length >= 2 ? 1 : 0;
  return {
    cross_device: cd,
    recurrence: cluster.recurrence || 0,
    devices: (cluster.devices || []).length,
    item_count: cluster.item_count || 0,
    lesson: String(cluster.lesson || '')
  };
}

/* ------------------- 判定策略自测（5 个分支逐条实测，供 --lean4-check 用） ------------------- */

/**
 * 造 5 个合成 cluster，断言**每个 judgment 分支都能被走到**。
 * 为什么需要：判定分支是"只在真实数据刚好命中时才跑到"的代码 ——
 * 没有这个自测，`conflicts` / `already-application` 这类分支可能**从来没被执行过**，
 * 而出问题时才发现它写错了。这是"检查要证明自己不是瞎的"（R006 §6 坑#3）在判定层的对应物。
 */
export function judgmentPolicyCases(catalog) {
  const mk = (lesson, refs, type, extra = {}) => ({
    cluster_id: 'PX', lesson, refs: refs || [], recurrence: 2, item_count: 2,
    devices: ['mac-mini'], agents: ['mac-mini:a', 'mac-mini:b'],
    members: [{
      device: 'mac-mini', agent: 'a', item_id: 'R1', pit: extra.pit || lesson,
      lesson, related_rule: (refs && refs[0]) || '无', suggestion: { type },
      evidence: { ts: '2026-09-10T00:00:00Z', cmd: 'ls' }
    }]
  });
  // 找两条真实存在的条目来构造"强命中"用例
  const ruleId = (catalog.rules.get('R006') ? 'R006' : [...catalog.rules.keys()][0]);
  const ruleEntry = catalog.rules.get(ruleId);
  const phiId = [...catalog.phis.keys()].find((k) => catalog.phis.get(k).vocab.size > 40) || [...catalog.phis.keys()][0];
  const phiEntry = catalog.phis.get(phiId);

  const cases = [
    {
      expect: 'already-application',
      cluster: mk(ruleEntry.title, [ruleId], '无需动作', { pit: ruleEntry.title })
    },
    {
      expect: 'extends-existing',
      cluster: mk(`${phiEntry.title}之外还要看采集时点这一维`, [phiId], '新增', { pit: phiEntry.title + ' 补维' })
    },
    {
      expect: 'new-dimension',
      cluster: mk('量子纠错码的稳定性与退相干时间的关系', [], '新增')
    },
    {
      expect: 'conflicts',
      cluster: mk(`本条的结论与 ${ruleId} 直接冲突：实测表明该做法不成立`, [ruleId], '修订')
    },
    {
      expect: 'unclear',
      cluster: mk('批量任务要在每批写入后记检查点', ['R099'], '新增')
    }
  ];
  return cases.map((c) => {
    const j = judgeCluster(c.cluster, catalog);
    return { expect: c.expect, got: j.judgment, ok: j.judgment === c.expect, why: j.judgment_reason.slice(0, 120) };
  });
}

export const ANALYZE_META = Object.freeze({
  judgments: JUDGMENTS,
  rule: JUDGE_RULE,
  conflictDetection: '仅显式措辞（工具不猜语义冲突）',
  philosophyVsRule: '启发式 + 强制标注（RULE_HINTS / PHILOSOPHY_HINTS），最终由用户裁定',
  note: '规则能定的用规则；规则定不了的显式标 unclear 交人工/LLM 复核'
});
