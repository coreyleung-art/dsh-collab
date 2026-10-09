/**
 * proposal.js — 第 4 步：生成 `proposal-<date>.md`
 * =============================================================================
 * 唯一的格式要求：**看一眼就能裁**。
 *
 * 用户在看这份东西的时候通常是忙的。所以：
 *   - 开头是「30 秒速览表」—— 一句话 + 复现 + 跨设备 + 建议处置 + 你要裁什么，五列看全；
 *   - 逐项明细排在后面，**想看理由的人往下翻，不想看的人看完表就能裁**；
 *   - 每一项都带**勾选框**，裁定成为"打勾"而不是"写一段话"；
 *   - ★ 跨设备信号**必须一眼可见**（它直接影响裁定权重：异构环境独立复现 = 系统性缺陷）；
 *   - 涉及"哲学还是规则"这种启发式判断，**不藏起来** —— 直接在"你要裁什么"里让用户选。
 *
 * 安全：提案正文包含**智能体提交的原始文本**（pit / lesson 等），一律先做 markdown 转义
 * （表格里的 `|`、换行、反引号），否则一条含 `|` 的 pit 就能把整张表拆坏 —— 那是渲染层注入。
 */

/** markdown 表格单元格转义 + 截断 */
function cell(s, max = 90) {
  let t = String(s ?? '').replace(/\|/g, '\\|').replace(/\r?\n/g, ' ').replace(/`/g, "'").trim();
  if (t.length > max) t = t.slice(0, max - 1) + '…';
  return t || '—';
}
/** 正文行内转义（防反引号/换行破坏结构） */
function inline(s, max = 400) {
  let t = String(s ?? '').replace(/\r?\n/g, ' ').replace(/`/g, "'").trim();
  if (t.length > max) t = t.slice(0, max - 1) + '…';
  return t || '—';
}

/** 复现分布文本：`mac-mini×3 + mbp×1` */
export function recurrenceBreakdown(cluster) {
  const per = {};
  for (const a of cluster.agents || []) { const d = String(a).split(':')[0]; per[d] = (per[d] || 0) + 1; }
  const parts = Object.entries(per).sort().map(([d, n]) => `${d}×${n}`);
  return parts.join(' + ') || '—';
}

/** 裁定速览表里"你要裁什么"的可选项（按建议处置给不同的选项集合） */
function rulingOptions(category) {
  switch (category) {
    case '拟新增哲学': return '☐ 立为哲学 ☐ 改立为规则 ☐ 并入既有条目 ☐ 驳回';
    case '拟新增规则': return '☐ 立为规则 ☐ 改立为哲学 ☐ 并入既有条目 ☐ 驳回';
    case '并入/补维': return '☐ 并入（补维） ☐ 单独新立 ☐ 驳回';
    case '转规范': return '☐ 转规范（并指定 SOP） ☐ 留作规则 ☐ 驳回';
    case '需裁决冲突': return '☐ 修订既有条目 ☐ 本条作废 ☐ 并存（说明边界）';
    case '需人工复核': return '☐ 定性（哲学/规则/应用） ☐ 退回重填 ☐ 驳回';
    case '归档为案例': return '（无需裁定，仅登记）';
    default: return '☐ 采纳 ☐ 驳回';
  }
}

/**
 * 生成提案 markdown。
 * @param {object} o {date, version, items:[{cluster, judge, cls, rank}], stats, notes, sourceFile}
 */
export function buildProposal(o) {
  const { date, version, items, stats, notes = [], sourceFile } = o;
  const L = [];
  const P = (s = '') => L.push(s);

  const needRuling = items.filter((it) => it.cls.category !== '归档为案例');
  const archived = items.filter((it) => it.cls.category === '归档为案例');
  const needHuman = items.filter((it) => it.cls.needs_human);

  P(`# 每日反思提案 · ${date}`);
  P('');
  P(`> \`dsh-plugin-reflect-synthesize\` v${version} · 生成于 ${new Date().toISOString()} · 源: \`${sourceFile}\``);
  P(`> **候选 ${items.length} 项** · 需你裁定 **${needRuling.length} 项** · 归档（无需裁定）${archived.length} 项 · ★ 需人工/LLM 复核 ${needHuman.length} 项`);
  P(`> 排序依据：**（跨设备, 复现广度）** 二元组降序 —— **跨设备复现优先**。`);
  P(`> 理由：不同设备跑的是不同任务、看的是不同上下文，它们**独立**踩到同一个坑 ⇒ 这不是某条工作流的偶然，而是**系统性缺陷**。`);
  P(`> ★ 本工具**没有**写规则库/哲学库的能力（源码扫描证明无该路径）；入册是 ⑦ reflect-enroll 在你裁定之后的事。`);
  P('');

  /* ---------------- 〇 裁定速览 ---------------- */
  P('## 〇 · 裁定速览（30 秒看完）');
  P('');
  if (!items.length) { P('_没有候选项。_'); P(''); }
  else {
    P('| # | 一句话 | 复现 | 跨设备 | 对照现有库 | 建议处置 | 你要裁什么 |');
    P('|---|---|---|---|---|---|---|');
    for (const it of items) {
      const c = it.cluster;
      const devs = c.devices || [];
      const cd = devs.length >= 2 ? `✅ ${devs.length} 台` : '✗ 单机';
      const cmp = it.judge.judgment === 'unclear'
        ? '`unclear` ⚠️'
        : `\`${it.judge.judgment}\`${it.judge.best_match ? `（${it.judge.best_match.id}）` : ''}`;
      P(`| **P${it.rank}** | ${cell(c.lesson, 44)} | ${cell(recurrenceBreakdown(c), 30)} = **${c.recurrence}** | ${cd} | ${cmp} | ${it.cls.category} | ${rulingOptions(it.cls.category)} |`);
    }
    P('');
    P(`> 表中「复现」= 独立 **设备:智能体** 数（同一智能体反复提只算 1）。**跨设备 ✅ 的项建议优先裁。**`);
    P('');
  }

  /* ---------------- 一 逐项明细 ---------------- */
  P('## 一 · 逐项明细（想看理由再往下翻）');
  P('');
  for (const it of items) {
    const c = it.cluster;
    const j = it.judge;
    const devs = c.devices || [];
    P(`### P${it.rank} · ${inline(c.lesson, 120)}`);
    P('');
    P(`**复现 ${c.recurrence}**（${recurrenceBreakdown(c)}）· **${devs.length >= 2 ? `★跨设备 ✅ ${devs.length} 台（${devs.join('、')}）` : '单设备 ✗'}** · 条目 ${c.item_count} 条 · 广度排名 ${it.rank}/${items.length}`);
    P('');
    P(`- **摘要**：${inline(c.lesson, 300)}`);
    P(`- **涉及智能体**：${(c.agents || []).map((a) => `\`${a}\``).join(' · ')}`);
    if (c.sync_duplicate_members && c.sync_duplicate_members.length) {
      P(`- ⚠️ **同步盘污染剔除**：${c.sync_duplicate_members.map((m) => `\`${m}\``).join(' · ')} —— lesson 逐字相同且跨设备、时点接近（疑似同步盘/复制粘贴），**未重复计入 recurrence**`);
    }
    if (c.flags && c.flags.length) P(`- **标记**：${c.flags.map((f) => `\`${f}\``).join(' · ')}`);
    P('');

    // 证据引用
    P('**证据引用**（每条都必须有时点：Φ13）');
    P('');
    P('| 设备:智能体 | 条目 | 事件 | 证据时点 | 采集时刻 | 命令 / 输出 |');
    P('|---|---|---|---|---|---|');
    for (const m of (c.members || [])) {
      const ev = m.evidence || {};
      const cmdOut = [ev.cmd ? `\`${cell(ev.cmd, 60)}\`` : null, ev.output ? cell(ev.output, 90) : null].filter(Boolean).join('<br>');
      P(`| \`${m.device}:${m.agent}\`${m.sync_duplicate ? ' ⚠️同步重复' : ''} | ${cell(m.item_id, 12)} | ${cell(m.event_ref, 12)} | ${cell(ev.ts || '（缺）', 28)} | ${cell(ev.collected_at || '（未标）', 28)} | ${cmdOut || '—'} |`);
    }
    P('');

    // 对照结果
    const mb = j.best_match;
    P(`- **对照结果**：\`${j.judgment}\`（置信 ${j.confidence}）${mb ? ` — 最佳匹配 **${mb.id}**（${inline(mb.title, 40)}），关键词重合 ${mb.overlap}${mb.novelty ? `，新关键词 ${mb.novelty}` : ''}` : ' — 与现有条目无关键词重合'}`);
    P(`  - 依据：${inline(j.judgment_reason, 500)}`);
    if (j.refs && j.refs.length) {
      P(`  - 智能体自填引用：${j.refs.map((r) => r.exists ? `\`${r.id}\`(${r.kind})` : `\`${r.id}\`(**不存在** ⚠️)`).join(' · ')}`);
    }
    if (j.declared_types && j.declared_types.length) {
      P(`  - 智能体主张的处置：${j.declared_types.map((t) => `\`${t}\``).join(' · ')}`);
    }
    P('');

    // 建议处置 + 片段
    P(`- **建议处置**：**${it.cls.category}**${it.cls.target ? ` → ${it.cls.target.id}${it.cls.target.title ? `（${inline(it.cls.target.title, 30)}）` : ''}` : ''}`);
    P(`  - 理由：${inline(it.cls.rationale, 400)}`);
    if (it.cls.snippet) {
      const s = it.cls.snippet;
      P(`  - **提案片段**（可直接抄进库）：`);
      P(`    - 类型：${s.kind}`);
      P(`    - 一句话：**${inline(s.one_line, 200)}**`);
      P(`    - 适用面：${s.scope_hint}`);
      P(`    - 理由：${inline(s.why, 300)}`);
      P(`    - 与已有条目关系：${inline(s.relation, 200)}`);
      P(`    - 证据引用：${s.evidence_refs.map((e) => `\`${e.device}:${e.agent}#${e.item_id}@${e.event_ref || '-'}\`（${inline(e.ts || '无时点', 24)}）`).join(' · ')}`);
    }
    P('');
    P(`- **★ 你要裁什么**：${rulingOptions(it.cls.category)}`);
    P(`  ${j.needs_human ? '（本项工具**不敢定论**，理由见上 → 请人工/LLM 复核）' : '（该判定置信 high）'}`);
    P('');
    P('---');
    P('');
  }

  /* ---------------- 二 归档 ---------------- */
  P('## 二 · 无需裁定（已归档为案例，仅登记）');
  P('');
  if (!archived.length) P('_无。_');
  else {
    P('| # | 一句话 | 复现 | 跨设备 | 归档到 | 为什么不用裁 |');
    P('|---|---|---|---|---|---|');
    for (const it of archived) {
      P(`| P${it.rank} | ${cell(it.cluster.lesson, 44)} | ${cell(recurrenceBreakdown(it.cluster), 24)} = **${it.cluster.recurrence}** | ${(it.cluster.devices || []).length >= 2 ? '✅' : '✗'} | \`${it.cls.target.id}\` | 已有条目覆盖，属其应用 |`);
    }
  }
  P('');

  /* ---------------- 三 需人工复核 ---------------- */
  P('## 三 · ★ 需人工/LLM 复核清单');
  P('');
  P('> 为什么单列：**「是应用还是新维度」需要语义判断**，纯规则化做不到。');
  P('> 工具只做筛选与提示。硬猜的代价不对称 —— 一个被硬猜成"已有覆盖"的盲区会**连被看见的机会都没有**；');
  P('> 而标 `unclear` 只让你多看一眼。所以拿不准的一律进这里。');
  P('');
  if (!needHuman.length) P('_无（本次全部判定置信 high）。_');
  else {
    P('| # | 一句话 | 为什么工具不敢定论 | 需要谁 |');
    P('|---|---|---|---|');
    for (const it of needHuman) {
      const who = it.cls.category === '需人工复核' ? '**人工/LLM 语义判定**' : '人工确认处置方向';
      P(`| P${it.rank} | ${cell(it.cluster.lesson, 40)} | ${cell(it.cls.rationale, 100)} | ${who} |`);
    }
  }
  P('');

  /* ---------------- 四 统计 ---------------- */
  P('## 四 · 统计与来源（可复核）');
  P('');
  P('| 项 | 值 |');
  P('|---|---|');
  P(`| 源文件 | \`${sourceFile}\` |`);
  P(`| 设备表 | ${(stats.devices || []).join('、')}（来源 ${stats.device_source}） |`);
  P(`| 设备回填 | ${stats.devices_submitted}/${stats.devices_total} 已回填 · ${stats.devices_pending} pending${stats.pending_devices && stats.pending_devices.length ? `（${stats.pending_devices.join('、')} 可能需要补填 / 离线）` : ''} |`);
  P(`| 有效条目 | ${stats.items_valid}（拒收 ${stats.items_rejected} 条目级 / ${stats.files_rejected} 文件级） |`);
  P(`| 集群 | ${items.length}（跨设备 ${items.filter((i) => (i.cluster.devices || []).length >= 2).length}） |`);
  P(`| 判定分布 | ${Object.entries(stats.judgment_distribution || {}).map(([k, v]) => `\`${k}\`×${v}`).join(' · ') || '—'} |`);
  P(`| 处置分布 | ${Object.entries(stats.category_distribution || {}).map(([k, v]) => `${k}×${v}`).join(' · ') || '—'} |`);
  if (stats.rejection_distribution && Object.keys(stats.rejection_distribution).length) {
    P(`| 拒收原因分布（未进入提案） | ${Object.entries(stats.rejection_distribution).map(([k, v]) => `\`${k}\`×${v}`).join(' · ')} |`);
  }
  if (stats.version_drift && stats.version_drift.drifted) {
    P(`| ★ 设备间版本漂移 | ${stats.version_drift.distinct.join(' vs ')} —— **裁定前请先确认口径**（不同版本行为可能不同） |`);
  }
  P('');
  if (notes.length) {
    P('**说明**');
    P('');
    for (const n of notes) P(`- ${inline(n, 300)}`);
    P('');
  }
  P('---');
  P('');
  P('## 附 · 裁定怎么落下去（⑥ → ⑦）');
  P('');
  P('1. 在**〇 速览表**上把每项的勾选挑好（或直接回一句「P1 采纳哲学 / P3 驳回」）；');
  P('2. 把裁定写成 `~/dsh-collab/data/reflect/ruling-' + date + '.json`；');
  P('3. 跑 ⑦ `dsh-plugin-reflect-enroll --ruling ruling-' + date + '.json --notify` 入册（**那一步才写库**，且会备份+回读校验）。');
  P('');
  P(`*每日反思提案 · ${date} · 由 dsh-plugin-reflect-synthesize v${version} 生成 · 本工具未改动任何规则库/哲学库*`);

  return L.join('\n') + '\n';
}
