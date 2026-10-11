/**
 * checkpoint.js — K3 纯决策核：**非摘要检查点产出 + 有界丢弃阶梯 + 保证能减**
 * =============================================================================
 * 本文件零 dsh import、零 I/O、零时钟、零随机 —— 因此可离线跑、可被判据逐位复算。
 * 它与 lib/budget.js 一起构成 K2/K3 的**决策核**：`cli.js --checkpoint-check` 与
 * `lib/checkpoint.test.js` 是仅有的两个消费者（同一份用例，见 lib/k3-selftest.js）。
 *
 * ★ 为什么"非摘要"是立论的中心（R030：此结论来自官方源码，见 lib/budget.js 文件头）：
 *   官方 compaction-basic 的检查点是**模型生成的摘要**，其开销是 LLM 输出，
 *   下界不可控 ⇒ 出现 `3435/3450 ≥ 2466`（摘要帧 ≥ 被遮内容）时会话硬死锁，**无配置解**。
 *   本插件的检查点是**投影 + 原文片段 + seq 指针**：
 *     · 投影字段（目标/阶段/todo/最近人类请求）从既有投影**抄**来，不是生成的；
 *     · 被遮内容以**逐字片段**保留一定预算，其余折叠成**带 seq 指针的省略账**；
 *     · 任一被省略段都能用 `csx_recall` 按 seq **逐字取回**。
 *   ⇒ 检查点体积 = 常量项（字段 + 省略账行）+ 受控项（片段预算），**不随被遮内容线性增长**；
 *     被遮内容越长，节省越多 ⇒ 这个判据可以被**保证**，而不是被指望。
 *
 * ★ 有界丢弃阶梯（立项书 §2.4）——**每升一档，检定点必然更小**：
 *     L0 引文预算 128 token/条   （最忠实：原文片段最全）
 *     L1 引文预算  32 token/条   （"压缩对话文本预算，每条最少保留 32 token"）
 *     L2 丢最旧**工具结果**条目  （改为省略账一行，带 seq 指针）
 *     L3 丢最旧**其余**条目      （同上；此时检定点只剩常量项）
 *   末档仍未达标 ⇒ 如实判 IMPOSSIBLE 并**带上实测数字**（绝不静默 no-op，立项书 I1）。
 *
 * ★ 两条口径**刻意**如此，写下来免得日后被当成 bug（R030）：
 *   ① 「工具调用行不缩放」：**缩放**（trim 文本）与**丢弃**（换成省略账）是两种操作。
 *      L0/L1 只缩放，故 `tool/call` 行整行保留；L2/L3 是丢弃，故按 §2.4"其余条目"一并处理。
 *      工具配对平衡**不在本核**兜——由替换站点用官方 `toolPairingBalancedBefore/After` 判据把关
 *      （立项书 §6 风险 2：找不到合法切点则本步不动并记 skipped）。
 *   ② 「每条最少保留 32 token」读作**上限截断**（`min(entry.tokens, 32)`）：原文不足 32 token 的
 *      条目本就无 32 可留，不可能凭空补齐；此读法使 L1 严格 ≤ L0，阶梯单调性由此成立。
 */

import { canShrink, BUDGET_DEFAULTS, SHRINK } from './budget.js';

/** 阶梯档位（闭集，次序即语义：数组顺序 = 升档顺序）。 */
export const RUNG = Object.freeze({
  L0_QUOTE: 'l0_quote',
  L1_TRIM: 'l1_trim',
  L2_DROP_TOOL_RESULTS: 'l2_drop_tool_results',
  L3_DROP_REST: 'l3_drop_rest'
});
export const RUNG_ORDER = Object.freeze([RUNG.L0_QUOTE, RUNG.L1_TRIM, RUNG.L2_DROP_TOOL_RESULTS, RUNG.L3_DROP_REST]);
/** 人读档位名（日志与通知用，不参与判定）。 */
export const RUNG_LABEL = Object.freeze({
  [RUNG.L0_QUOTE]: 'L0 引文 128/条',
  [RUNG.L1_TRIM]: 'L1 引文 32/条',
  [RUNG.L2_DROP_TOOL_RESULTS]: 'L2 丢工具结果',
  [RUNG.L3_DROP_REST]: 'L3 丢其余条目'
});

/** planCheckpoint 的结论取值集合。 */
export const PLAN = Object.freeze({
  OK: 'plan_ok',
  IMPOSSIBLE: 'plan_impossible',
  NOTHING_TO_SHADOW: 'plan_nothing_to_shadow'
});

export const CP_DEFAULTS = Object.freeze({
  charsPerToken: 4,        // 与宿主 token-meter 同口径（CHARS_PER_TOKEN=4）——必须同尺，否则节省量是假的
  l0QuoteTokens: 128,
  l1QuoteTokens: 32,
  minSavingsTokens: BUDGET_DEFAULTS.minSavingsTokens,
  maxScan: 4000,           // 线性扫描上限（见"为什么线性而非二分"）
  recallHint: 'csx_recall'
});

/** 工具结果行（L2 优先丢弃的对象）。kind 用法与官方事件流一致。 */
const TOOL_RESULT_KIND = 'tool/result';
const TOOL_CALL_KIND = 'tool/call';
const isToolResult = (e) => e.kind === TOOL_RESULT_KIND;
const isToolCall = (e) => e.kind === TOOL_CALL_KIND;

export class CheckpointError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'CheckpointError';
    this.code = code;
  }
}

/* ------------------------------- token 口径 ------------------------------- */

/**
 * 与宿主同口径的估算：`ceil(len / charsPerToken)`。
 * ★ 这是**估算不是测量**：真实计量由宿主 `tokenMeter.measure()` 给出。
 *   本核只用它算"检查点自身有多大"，故只要两边同尺，节省量就成立。
 *   CJK 低估（约 4×）已在 budget.js advisoryTokens 单列，**不在本核兜**（立项书 §6 风险 3）。
 */
export function estimateTokens(text, charsPerToken = CP_DEFAULTS.charsPerToken) {
  if (typeof text !== 'string') throw new CheckpointError('BAD_TEXT', `estimateTokens 需要字符串，收到 ${typeof text}`);
  if (!Number.isInteger(charsPerToken) || charsPerToken < 1) throw new CheckpointError('BAD_CPT', `charsPerToken 必须是 ≥1 的整数，收到 ${charsPerToken}`);
  return Math.ceil(text.length / charsPerToken);
}

/**
 * 按 token 预算截断文本。**保证** `estimateTokens(结果) <= maxTokens`。
 * 保留 `maxTokens*charsPerToken - 1` 个字符 + 1 个省略号，使长度恰为预算。
 */
export function trimToTokens(text, maxTokens, charsPerToken = CP_DEFAULTS.charsPerToken) {
  if (!Number.isInteger(maxTokens) || maxTokens < 1) throw new CheckpointError('BAD_MAX_TOKENS', `maxTokens 必须是 ≥1 的整数，收到 ${maxTokens}`);
  const before = estimateTokens(text, charsPerToken);
  if (before <= maxTokens) return Object.freeze({ text, trimmed: false, tokens: before, beforeTokens: before });
  const keep = maxTokens * charsPerToken - 1;
  const t = `${text.slice(0, keep)}…`;
  return Object.freeze({ text: t, trimmed: true, tokens: estimateTokens(t, charsPerToken), beforeTokens: before });
}

/* ------------------------------- 条目与几何 ------------------------------- */

function reqEntries(entries) {
  if (!Array.isArray(entries)) throw new CheckpointError('BAD_ENTRIES', 'entries 必须是数组');
  let prev = null;
  for (let i = 0; i < entries.length; i++) {
    const e = entries[i];
    if (e === null || typeof e !== 'object') throw new CheckpointError('BAD_ENTRY', `entries[${i}] 必须是对象`);
    if (!Number.isInteger(e.seq) || e.seq < 0) throw new CheckpointError('BAD_SEQ', `entries[${i}].seq 必须是 ≥0 的整数，收到 ${e.seq}`);
    if (typeof e.kind !== 'string' || e.kind.length === 0) throw new CheckpointError('BAD_KIND', `entries[${i}].kind 必须是非空字符串`);
    if (!Number.isInteger(e.tokens) || e.tokens < 0) throw new CheckpointError('BAD_TOKENS', `entries[${i}].tokens 必须是 ≥0 的整数，收到 ${e.tokens}`);
    if (e.text !== undefined && typeof e.text !== 'string') throw new CheckpointError('BAD_ENTRY_TEXT', `entries[${i}].text 必须是字符串`);
    if (prev !== null && e.seq <= prev) throw new CheckpointError('BAD_ORDER', `entries 必须按 seq 严格升序（第 ${i} 条 seq=${e.seq} ≤ 前一条 ${prev}）`);
    prev = e.seq;
  }
  return entries;
}

/**
 * 切出**可遮区**与**保活区**：从最新往回累计，累计 token ≥ retainTokens 即封口，
 * 更旧的部分全部进入可遮区。⇒ `保活窗口内永不动` 由本函数在结构上保证，而不是靠调用方自觉。
 * @returns {{shadowable:Array, retained:Array, retainedTokens:number}}
 */
export function splitRetain(entries, retainTokens) {
  if (!Number.isInteger(retainTokens) || retainTokens < 0) throw new CheckpointError('BAD_RETAIN', `retainTokens 必须是 ≥0 的整数，收到 ${retainTokens}`);
  let acc = 0;
  let cut = entries.length;
  for (let i = entries.length - 1; i >= 0; i--) {
    if (acc >= retainTokens) break;
    acc += entries[i].tokens;
    cut = i;
  }
  return Object.freeze({
    shadowable: entries.slice(0, cut),
    retained: entries.slice(cut),
    retainedTokens: acc
  });
}

/** 该条在本档的引文预算（token）。0 = 本档不引文，只进省略账。 */
export function quoteBudget(entry, rung, opts = CP_DEFAULTS) {
  if (!RUNG_ORDER.includes(rung)) throw new CheckpointError('BAD_RUNG', `未知档位 ${rung}`);
  if (rung === RUNG.L3_DROP_REST) return 0;
  if (rung === RUNG.L2_DROP_TOOL_RESULTS) return isToolResult(entry) ? 0 : Math.min(entry.tokens, opts.l1QuoteTokens);
  if (rung === RUNG.L1_TRIM) return isToolCall(entry) ? entry.tokens : Math.min(entry.tokens, opts.l1QuoteTokens);
  return isToolCall(entry) ? entry.tokens : Math.min(entry.tokens, opts.l0QuoteTokens);
}

/** 把被丢弃的条目按**连续同类**折叠成省略账分组。 */
export function groupElided(entries) {
  const groups = [];
  for (const e of entries) {
    const cls = isToolResult(e) ? 'tool/result' : 'earlier';
    const last = groups[groups.length - 1];
    if (last && last.cls === cls && last.endSeq + 1 === e.seq) {
      last.count += 1;
      last.endSeq = e.seq;
    } else {
      groups.push({ cls, count: 1, startSeq: e.seq, endSeq: e.seq });
    }
  }
  return groups;
}

/** 省略账行文本（形状照立项书 §2.4，逐字）。 */
export function elisionLine(g) {
  return g.cls === 'tool/result'
    ? `[${g.count} tool/result entries elided: seqs ${g.startSeq}-${g.endSeq}]`
    : `[${g.count} earlier entries elided: seqs ${g.startSeq}-${g.endSeq}]`;
}

/* ------------------------------- 检查点产出 ------------------------------- */

const NONE = '(无)';

/**
 * 产 `<context_handoff v1 seq-range=A-B>` 一条 user/message 的正文。
 * **纯函数**：同输入 ⇒ 逐字节同输出（无时钟、无随机、无迭代序依赖）。
 * 缺字段**如实留空**并标注，绝不编造（R030 / 立项书 §6 风险 4）。
 */
export function buildHandoff(input = {}) {
  const startSeq = input.startSeq;
  const endSeq = input.endSeq;
  if (!Number.isInteger(startSeq) || !Number.isInteger(endSeq) || startSeq > endSeq) {
    throw new CheckpointError('BAD_RANGE', `seq-range 非法：${startSeq}-${endSeq}`);
  }
  const s = (k) => {
    const v = input[k];
    return (typeof v === 'string' && v.length > 0) ? v : `${NONE}  ← ${k} 投影缺失，如实留空不编造`;
  };
  const lines = [];
  lines.push(`<context_handoff v1 seq-range=${startSeq}-${endSeq}>`);
  lines.push(`  目标:      ${s('goal')}`);
  lines.push(`  阶段/波次:  ${s('wave')}`);
  lines.push(`  todo:      ${s('todos')}`);
  lines.push(`  最近人类请求: ${s('lastHumanRequest')}`);
  lines.push(`  notes:     ${s('notes')}`);

  const quotes = Array.isArray(input.quotes) ? input.quotes : [];
  if (quotes.length > 0) {
    lines.push('  原文节选（逐字，未摘要）:');
    for (const q of quotes) lines.push(`    [seq ${q.seq} ${q.kind}] ${q.text}`);
  }
  const elided = Array.isArray(input.elided) ? input.elided : [];
  if (elided.length > 0) {
    lines.push('  省略账（每一处省略都带 seq 指针，可逐字召回）:');
    for (const g of elided) lines.push(`    ${elisionLine(g)}`);
  }
  const hint = typeof input.recallHint === 'string' && input.recallHint.length > 0 ? input.recallHint : CP_DEFAULTS.recallHint;
  lines.push(`  召回指南:   用 ${hint} {kind:"range", id:"${startSeq}-${endSeq}"} 逐字取回上述任一段`);
  lines.push('</context_handoff>');
  return lines.join('\n');
}

/**
 * 为**给定范围 + 给定档位**组装检查点（引文裁剪 + 省略账分组）。
 * 拆出来是为了让 planCheckpoint 的扫描能在 O(候选) 次组装内完成，且组装逻辑本身可单测。
 */
export function assemble(entries, rung, fields = {}, opts = CP_DEFAULTS, count = undefined) {
  const n = count === undefined ? entries.length : count;
  if (!Number.isInteger(n) || n < 1 || n > entries.length) {
    throw new CheckpointError('BAD_COUNT', `count 必须是 1..${entries.length} 的整数，收到 ${count}`);
  }
  const quotes = [];
  const dropped = [];
  for (let i = 0; i < n; i++) {
    const e = entries[i];
    const budget = quoteBudget(e, rung, opts);
    if (budget <= 0) { dropped.push(e); continue; }
    const trimmed = trimToTokens(e.text === undefined ? '' : e.text, budget, opts.charsPerToken);
    quotes.push({ seq: e.seq, kind: e.kind, text: trimmed.text, trimmed: trimmed.trimmed });
  }
  const elided = groupElided(dropped);
  const text = buildHandoff({
    startSeq: entries[0].seq,
    endSeq: entries[n - 1].seq,
    goal: fields.goal,
    wave: fields.wave,
    todos: fields.todos,
    lastHumanRequest: fields.lastHumanRequest,
    notes: fields.notes,
    quotes,
    elided,
    recallHint: opts.recallHint
  });
  return Object.freeze({
    text,
    tokens: estimateTokens(text, opts.charsPerToken),
    quotes,
    elided,
    quotedCount: quotes.length,
    elidedCount: dropped.length
  });
}

/**
 * ★ 增量字符账：把"每个 k 都重建全文"的 O(N²) 降成 O(N)。
 *
 * 为什么必须做：本核跑在 `agent/pre-step` 的决策路径上，长会话的可遮区可达数千条；
 * 实测 n=4000 时朴素重建要 **2065 ms**（一次决策 2 秒，不可接受）。
 *
 * ★ 它**只是优化**，不是第二套语义：`push(k)` 的返回值必须与 `assemble(..., k).text` 的字符数
 *   逐位相同。planCheckpoint 在命中点用真 `assemble()` **复核**，不符则回退慢路径继续扫——
 *   即"账错了只会变慢，不会给出错的决定"。k3-selftest 的 L 组用例扫全 k 把等价性钉死。
 *
 * 行结构（与 buildHandoff 逐行对应，改其一必须改另一）：
 *   [0] <context_handoff v1 seq-range=A-B>
 *   [1..5] 五个字段行
 *   [6] 原文节选标头 + nq 行        （仅当 nq>0）
 *   […] 省略账标头 + ng 行          （仅当 ng>0）
 *   [last] 召回指南行（含 seq-range）
 * 总字符 = Σ行字符 + (行数-1)
 *
 * @returns {{push:(k:number)=>number}} push 必须**按 k 递增顺序**调用（增量语义）
 */
export function makeCharAccount(shadowable, rung, fields, opts, limit) {
  const A = shadowable[0].seq;
  const hint = opts.recallHint;

  // 每条在本档的引文行字符数（含换行）；-1 = 本档不引文（进省略账）
  const quoteLineLen = new Array(limit);
  for (let i = 0; i < limit; i++) {
    const e = shadowable[i];
    const budget = quoteBudget(e, rung, opts);
    if (budget <= 0) { quoteLineLen[i] = -1; continue; }
    const t = trimToTokens(e.text === undefined ? '' : e.text, budget, opts.charsPerToken).text;
    quoteLineLen[i] = `    [seq ${e.seq} ${e.kind}] ${t}`.length + 1;
  }

  const QHEAD = '  原文节选（逐字，未摘要）:'.length + 1;
  const EHEAD = '  省略账（每一处省略都带 seq 指针，可逐字召回）:'.length + 1;
  const FOOTER = '</context_handoff>'.length + 1;

  // 与 k 无关的常量：五个字段行（含换行）。从一次真实构建里量出来，不手写猜。
  const fieldLinesChars = (() => {
    const h = buildHandoff({ startSeq: A, endSeq: A, ...fields, quotes: [], elided: [] });
    return h.split('\n').slice(1, 6).reduce((a, l) => a + l.length + 1, 0);
  })();

  let quotedChars = 0;
  let nq = 0;
  let elidedChars = 0;
  let ng = 0;
  let lastGroup = null;

  return {
    push(k) {
      const i = k - 1;
      const e = shadowable[i];
      if (quoteLineLen[i] >= 0) {
        quotedChars += quoteLineLen[i];
        nq += 1;
      } else {
        const cls = isToolResult(e) ? 'tool/result' : 'earlier';
        if (lastGroup !== null && lastGroup.cls === cls && lastGroup.endSeq + 1 === e.seq) {
          lastGroup.count += 1;
          lastGroup.endSeq = e.seq;
          // 延长末组：整行长度按新计数/新区间重算，只补差额
          const newLen = `    ${elisionLine(lastGroup)}`.length + 1;
          elidedChars += newLen - lastGroup.lineLen;
          lastGroup.lineLen = newLen;
        } else {
          const g = { cls, count: 1, startSeq: e.seq, endSeq: e.seq, lineLen: 0 };
          g.lineLen = `    ${elisionLine(g)}`.length + 1;
          elidedChars += g.lineLen;
          ng += 1;
          lastGroup = g;
        }
      }
      const B = shadowable[k - 1].seq;
      const lineChars = (`<context_handoff v1 seq-range=${A}-${B}>`.length + 1)
        + fieldLinesChars
        + (nq > 0 ? QHEAD + quotedChars : 0)
        + (ng > 0 ? EHEAD + elidedChars : 0)
        + (`  召回指南:   用 ${hint} {kind:"range", id:"${A}-${B}"} 逐字取回上述任一段`).length + 1
        + FOOTER;
      return lineChars - 1;   // 末尾那个换行不算进正文
    }
  };
}


/**
 * ★ K3 主决策：在可遮区里找**最小**的 (档位, 范围)，使 `被遮 token - 检查点 token ≥ 要求节省量`。
 *
 * 要求节省量 = `max(minSavingsTokens, neededSavingsTokens)`：
 *   · minSavingsTokens 是**下界判据**（canShrink，P26 机制二），保证检查点严格小于被遮内容；
 *   · neededSavingsTokens 是**回到阈值以下需要腾出的量**（调用方从守卫读数算出）。
 *   两者取大 ⇒ 既满足"能减"，又真的把会话拉回阈值以下。
 *
 * ★ 为什么**线性扫描**而不是二分：`savings(k)` 在 L2/L3 上**不必单调**——加入一条极小的条目
 *   可能新开一行省略账（约 12 token）而使节省量暂时下降。二分依赖单调性，此处不成立，故线性。
 *   上限 maxScan 兜住最坏情况；超出即如实截断并在结果里标注（scanTruncated），不假装扫完了。
 *
 * @returns 冻结的判定对象（含实测数字，供日志/通知/复算）
 */
export function planCheckpoint(input = {}) {
  const entries = reqEntries(input.entries === undefined ? [] : input.entries);
  const opts = Object.freeze({
    charsPerToken: input.charsPerToken === undefined ? CP_DEFAULTS.charsPerToken : input.charsPerToken,
    l0QuoteTokens: input.l0QuoteTokens === undefined ? CP_DEFAULTS.l0QuoteTokens : input.l0QuoteTokens,
    l1QuoteTokens: input.l1QuoteTokens === undefined ? CP_DEFAULTS.l1QuoteTokens : input.l1QuoteTokens,
    minSavingsTokens: input.minSavingsTokens === undefined ? CP_DEFAULTS.minSavingsTokens : input.minSavingsTokens,
    maxScan: input.maxScan === undefined ? CP_DEFAULTS.maxScan : input.maxScan,
    recallHint: input.recallHint === undefined ? CP_DEFAULTS.recallHint : input.recallHint
  });
  // ★ 合法切口掩码（表面配对安全的 k 值集合）。null = 不作限制（纯离线语义，与 K1/K2 行为一致）。
  //   为什么必须**喂进扫描**而不是事后修正：planCheckpoint 选定区间后若再被"收缩"（起点后移、终点前移），
  //   被遮 token 会变少而检查点**不随之重算** ⇒ 节省量可能掉到要求以下，而报告仍是 ok。
  //   把合法性做进候选集，则"扫出来的"就是"能用的"，不存在两套数。
  const legalEndIdx = input.legalEndIdx === undefined || input.legalEndIdx === null
    ? null : input.legalEndIdx;
  if (legalEndIdx !== null && typeof legalEndIdx.has !== 'function') {
    throw new CheckpointError('BAD_LEGAL_MASK', 'legalEndIdx 必须是 null 或带 has() 的集合（如 Set）');
  }
  for (const k of ['charsPerToken', 'l0QuoteTokens', 'l1QuoteTokens', 'maxScan']) {
    if (!Number.isInteger(opts[k]) || opts[k] < 1) throw new CheckpointError('BAD_OPT', `${k} 必须是 ≥1 的整数，收到 ${opts[k]}`);
  }
  if (!Number.isInteger(opts.minSavingsTokens) || opts.minSavingsTokens < 0) throw new CheckpointError('BAD_OPT', `minSavingsTokens 必须是 ≥0 的整数，收到 ${opts.minSavingsTokens}`);

  const retainTokens = input.retainTokens === undefined ? BUDGET_DEFAULTS.retainTokens : input.retainTokens;
  const neededSavingsTokens = input.neededSavingsTokens === undefined ? 0 : input.neededSavingsTokens;
  if (!Number.isInteger(neededSavingsTokens) || neededSavingsTokens < 0) throw new CheckpointError('BAD_NEEDED', `neededSavingsTokens 必须是 ≥0 的整数，收到 ${neededSavingsTokens}`);
  const requiredSavings = Math.max(opts.minSavingsTokens, neededSavingsTokens);

  const fields = Object.freeze({
    goal: input.goal, wave: input.wave, todos: input.todos,
    lastHumanRequest: input.lastHumanRequest, notes: input.notes
  });

  const { shadowable, retainedTokens, retained } = splitRetain(entries, retainTokens);
  const base = {
    requiredSavings, minSavingsTokens: opts.minSavingsTokens, neededSavingsTokens,
    retainTokens, retainedTokens, retainedCount: retained.length,
    totalEntries: entries.length, shadowableCount: shadowable.length,
    charsPerToken: opts.charsPerToken
  };

  if (shadowable.length === 0) {
    return Object.freeze({
      ...base, ok: false, verdict: PLAN.NOTHING_TO_SHADOW, rung: null, range: null,
      shadowedSeqs: null, shadowedTokens: 0, checkpointTokens: 0, savings: 0, savingsPct: 0,
      handoffText: null, elided: [], quotedCount: 0, elidedCount: 0,
      scanCount: 0, scanTruncated: false,
      reason: `可遮区为空（保活 ${retainedTokens} token 已吃满 ${entries.length} 条）⇒ 无处可压`
    });
  }

  const limit = Math.min(shadowable.length, opts.maxScan);
  let shadowedTokens = 0;
  let best = null;              // 末档全范围的实测（不可能时用它如实报数，不静默）
  let scanCount = 0;

  for (const rung of RUNG_ORDER) {
    const acct = makeCharAccount(shadowable, rung, fields, opts, limit);
    shadowedTokens = 0;
    for (let k = 1; k <= limit; k++) {
      shadowedTokens += shadowable[k - 1].tokens;
      scanCount += 1;
      const estChars = acct.push(k);                                    // O(1) 增量账（每次都必须推进）
      if (legalEndIdx !== null && !legalEndIdx.has(k)) continue;        // ★ 非合法切口 ⇒ 本 k 不可用
      const estTokens = Math.ceil(estChars / opts.charsPerToken);
      if (!canShrink({ shadowedTokens, checkpointTokens: estTokens, minSavingsTokens: requiredSavings }).ok) continue;
      // ★ 命中点用**真构建**复核：账若漂了，这一步会拦下并回退慢路径继续扫
      //   ⇒ 增量账错了只会变慢，**不会给出错的决定**。
      const asm = assemble(shadowable, rung, fields, opts, k);
      const shrink = canShrink({ shadowedTokens, checkpointTokens: asm.tokens, minSavingsTokens: requiredSavings });
      if (!shrink.ok) continue;
      {
        return Object.freeze({
          ...base, ok: true, verdict: PLAN.OK, rung, rungLabel: RUNG_LABEL[rung],
          range: Object.freeze({ startSeq: shadowable[0].seq, endSeq: shadowable[k - 1].seq, count: k }),
          shadowedSeqs: Object.freeze([shadowable[0].seq, shadowable[k - 1].seq]),
          shadowedTokens, checkpointTokens: asm.tokens,
          savings: shrink.savings, savingsPct: shrink.savingsPct,
          shrinkVerdict: shrink.verdict,
          handoffText: asm.text, quotes: asm.quotes, elided: asm.elided,
          quotedCount: asm.quotedCount, elidedCount: asm.elidedCount,
          scanCount, scanTruncated: shadowable.length > opts.maxScan,
          reason: `档位 ${rung}(${RUNG_LABEL[rung]}) · 遮 seq ${shadowable[0].seq}-${shadowable[k - 1].seq}（${k} 条 ${shadowedTokens} token）⇒ 检查点 ${asm.tokens} token，省 ${shrink.savings}（要求 ${requiredSavings}）`
        });
      }
    }
    // 本档走到尽头：用**真构建**记下最激进一次——既供 IMPOSSIBLE 如实报数，也把该档全范围定死。
    // ★ 若有限制，取**最大的合法 k**（而不是 limit），否则报了数也做不了。
    let kEnd = limit;
    if (legalEndIdx !== null) {
      kEnd = 0;
      let acc = 0;
      for (let k = 1; k <= limit; k++) { acc += shadowable[k - 1].tokens; if (legalEndIdx.has(k)) { kEnd = k; } }
      if (kEnd === 0) {
        return Object.freeze({
          ...base, ok: false, verdict: PLAN.NOTHING_TO_SHADOW, rung: null, range: null,
          shadowedSeqs: null, shadowedTokens: 0, checkpointTokens: 0, savings: 0, savingsPct: 0,
          handoffText: null, elided: [], quotedCount: 0, elidedCount: 0,
          scanCount, scanTruncated: false,
          reason: '可遮区内的切口全部不合法（无配对安全切点）⇒ 无处可压，本步不动'
        });
      }
      shadowedTokens = 0;
      for (let k = 1; k <= kEnd; k++) shadowedTokens += shadowable[k - 1].tokens;
    }
    const asmEnd = assemble(shadowable, rung, fields, opts, kEnd);
    best = {
      rung, k: kEnd, asm: asmEnd, shadowedTokens,
      shrink: canShrink({ shadowedTokens, checkpointTokens: asmEnd.tokens, minSavingsTokens: requiredSavings })
    };
  }

  const last = best;
  return Object.freeze({
    ...base, ok: false, verdict: PLAN.IMPOSSIBLE, rung: RUNG.L3_DROP_REST, rungLabel: RUNG_LABEL[RUNG.L3_DROP_REST],
    range: Object.freeze({ startSeq: shadowable[0].seq, endSeq: shadowable[(last ? last.k : shadowable.length) - 1].seq, count: last ? last.k : shadowable.length }),
    shadowedSeqs: Object.freeze([shadowable[0].seq, shadowable[(last ? last.k : shadowable.length) - 1].seq]),
    shadowedTokens: last ? last.shadowedTokens : 0,
    checkpointTokens: last ? last.asm.tokens : 0,
    savings: last ? last.shrink.savings : 0,
    savingsPct: last ? last.shrink.savingsPct : 0,
    shrinkVerdict: SHRINK.IMPOSSIBLE,
    handoffText: last ? last.asm.text : null,
    quotes: last ? last.asm.quotes : [], elided: last ? last.asm.elided : [],
    quotedCount: last ? last.asm.quotedCount : 0, elidedCount: last ? last.asm.elidedCount : 0,
    scanCount, scanTruncated: shadowable.length > opts.maxScan,
    reason: `可遮区全部取尽（${shadowable.length} 条 ${last ? last.shadowedTokens : 0} token）且降到末档 ${RUNG.L3_DROP_REST}，检查点仍为 ${last ? last.asm.tokens : 0} token ⇒ 达不到要求节省量 ${requiredSavings}（实测省 ${last ? last.shrink.savings : 0}）`
  });
}

/** 一行摘要（整数出整数，无浮点拼接）。 */
export function describePlan(p) {
  if (!p || p.ok !== true) {
    return `plan=${p ? p.verdict : 'null'} ok=false required=${p ? p.requiredSavings : '?'} shadowed=${p ? p.shadowedTokens : '?'} cp=${p ? p.checkpointTokens : '?'}`;
  }
  return `plan=ok rung=${p.rung} seqs=${p.range.startSeq}-${p.range.endSeq} n=${p.range.count}`
    + ` shadowed=${p.shadowedTokens} cp=${p.checkpointTokens} savings=${p.savings}(${p.savingsPct}%)`
    + ` required=${p.requiredSavings} retain=${p.retainedTokens} quoted=${p.quotedCount} elided=${p.elidedCount}`;
}
