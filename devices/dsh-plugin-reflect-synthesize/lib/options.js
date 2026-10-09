/**
 * options.js — CLI 旗标 与 工具入参 的**单一来源**（R006 ⑨ + ⑩「没有那个入口」的可验证形式）
 * =============================================================================
 * 本工具唯一的"不该发生路径"是**替用户改哲学库/规则库**。
 * 最直接的一条封堵就是：**根本没有 `--apply` / `--enroll` / `--write-rules` / `--out` 这些旗标**。
 *
 * 把旗标收进一个**冻结**的单一来源后，这条证明变成**集合运算**，而不是文本扫描：
 *     ∀ k ∈ keys(CLI_OPTIONS) ∪ keys(TOOL_PARAMETERS): k ∉ FORBIDDEN_FLAGS
 * 无需扫描、无假阳性（R006 §6 坑#2）、无空洞通过（坑#3）。
 */

/** 明令禁止出现的旗标/入参名（写库 / 入册 / 自定义输出路径） */
export const FORBIDDEN_FLAGS = Object.freeze([
  'apply', 'enroll', 'write-rules', 'writerules', 'write-philosophy', 'writephilosophy',
  'out', 'output', 'outfile', 'out-file', 'target', 'dest', 'destination',
  'rule', 'rules-file', 'phi-file', 'philosophy-file', 'registry'
]);

/** CLI 旗标（唯一来源；cli.js 用它构造 parseArgs options） */
export const CLI_OPTIONS = Object.freeze({
  date: Object.freeze({ type: 'string' }),
  'harvested-dir': Object.freeze({ type: 'string' }),
  preview: Object.freeze({ type: 'boolean', default: false }),
  summary: Object.freeze({ type: 'boolean', default: false }),
  json: Object.freeze({ type: 'boolean', default: false }),
  'dry-run': Object.freeze({ type: 'boolean', default: false }),
  selfcheck: Object.freeze({ type: 'boolean', default: false }),
  'lean4-check': Object.freeze({ type: 'boolean', default: false }),
  'tool-version': Object.freeze({ type: 'boolean', default: false }),
  help: Object.freeze({ type: 'boolean', default: false })
});

/** dsh 工具入参（唯一来源；lib/index.js 用它构造 defineTool.parameters） */
export const TOOL_PARAMETERS = Object.freeze({
  date: Object.freeze({
    type: 'string', required: true,
    description: '目标日期 YYYY-MM-DD（读 harvested-<date>.json，写 proposal-<date>.md）'
  }),
  dryRun: Object.freeze({
    type: 'boolean',
    description: 'true=只计算并回报，不写任何文件（零变更，含不写日志）'
  }),
  includeMarkdown: Object.freeze({
    type: 'boolean',
    description: 'true（默认）=回报提案 markdown 全文；false=只回报统计与逐项结论'
  })
});

export function toolParameters() {
  const out = {};
  for (const [k, v] of Object.entries(TOOL_PARAMETERS)) out[k] = { ...v };
  return out;
}

/** 集合运算式证明：「没有那个入口」（写库/入册/自定义路径）。 */
export function assertNoForbiddenFlags() {
  const hits = [];
  const checked = [];
  const scan = (source, keys) => {
    for (const key of keys) {
      checked.push(`${source}:${key}`);
      const low = String(key).toLowerCase();
      for (const f of FORBIDDEN_FLAGS) {
        if (low === f || low.includes(f)) hits.push({ source, key, token: f });
      }
    }
  };
  scan('CLI_OPTIONS', Object.keys(CLI_OPTIONS));
  scan('TOOL_PARAMETERS', Object.keys(TOOL_PARAMETERS));
  return { ok: hits.length === 0, checked, hits };
}

export const OPTIONS_META = Object.freeze({
  forbiddenFlags: FORBIDDEN_FLAGS,
  cliFlags: Object.keys(CLI_OPTIONS),
  toolParams: Object.keys(TOOL_PARAMETERS),
  note: '单一来源 + 冻结；「没有那个入口」用集合运算证明，不靠文本扫描'
});
