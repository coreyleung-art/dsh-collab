/**
 * options.js — CLI 旗标 与 工具入参 的**单一来源**（R006 ⑨ + ⑩「没有那个入口」的可验证形式）
 * =============================================================================
 * 为什么要有这个文件：
 *   R006 §2 ⑩ 验收第 1 条要求「危险操作在参数/schema 层**无法表达**」。
 *   如果旗标散落在 cli.js 的 parseArgs 里，就只能靠**文本扫描**去证"没有 skip-evidence"——
 *   而文本扫描正是 R006 §6 坑#2/#3 的重灾区（扫到自己 / 空洞通过）。
 *
 *   把 CLI 旗标与工具入参收进一个**冻结**的单一来源后，证明变成**集合运算**：
 *     ∀ k ∈ keys(CLI_OPTIONS) ∪ keys(TOOL_PARAMETERS): k 不含任何 PERMISSIVE_FLAG_TOKENS
 *   无需扫描、无假阳性、无空洞通过。
 *
 * ★ 本文件的 object 全部 Object.freeze：运行时改不动（改 = 抛 TypeError in strict ESM）。
 */

/**
 * 削弱证据门的旗标名片段（**禁止出现在任何 CLI 旗标或工具入参里**）。
 * 命令白名单为空 + 这组禁用片段 = 「没有那个入口」。
 */
export const PERMISSIVE_FLAG_TOKENS = Object.freeze([
  'skip', 'force', 'lenient', 'ignore', 'bypass', 'unsafe', 'relax',
  'allowmissing', 'allow-missing', 'no-verify', 'nocheck', 'no-check'
]);

/** CLI 旗标（唯一来源；cli.js 用它构造 parseArgs options） */
export const CLI_OPTIONS = Object.freeze({
  date: Object.freeze({ type: 'string' }),
  devices: Object.freeze({ type: 'string' }),
  device: Object.freeze({ type: 'string' }),
  central: Object.freeze({ type: 'string' }),
  'local-root': Object.freeze({ type: 'string' }),
  'local-only': Object.freeze({ type: 'boolean', default: false }),
  'allow-late': Object.freeze({ type: 'boolean', default: false }),
  'dry-run': Object.freeze({ type: 'boolean', default: false }),
  summary: Object.freeze({ type: 'boolean', default: false }),
  json: Object.freeze({ type: 'boolean', default: false }),
  selfcheck: Object.freeze({ type: 'boolean', default: false }),
  'lean4-check': Object.freeze({ type: 'boolean', default: false }),
  'tool-version': Object.freeze({ type: 'boolean', default: false }),
  help: Object.freeze({ type: 'boolean', default: false })
});

/**
 * dsh 工具入参（唯一来源；lib/index.js 用它构造 defineTool.parameters）。
 * 与 CLI 旗标一样，**没有任何**能跳过证据判定的入参。
 */
export const TOOL_PARAMETERS = Object.freeze({
  date: Object.freeze({
    type: 'string', required: true,
    description: '目标日期 YYYY-MM-DD（决定读 answers/<date>/ 与写 harvested-<date>.json）'
  }),
  dryRun: Object.freeze({
    type: 'boolean',
    description: 'true=只计算并回报，不写任何文件（零变更，含不写日志）'
  }),
  includeItems: Object.freeze({
    type: 'boolean',
    description: 'true（默认）=额外回报 valid_items 全量明细；false=只回报统计与簇'
  }),
  devices: Object.freeze({
    type: 'string',
    description: '设备表（逗号分隔，如 "mac-mini,mbp,i9"）；省略则读 devices.json，再退到冻结默认表'
  }),
  localOnly: Object.freeze({
    type: 'boolean',
    description: 'true=只读本机目录，不触碰中央黑板（离线/测试用）'
  }),
  allowLate: Object.freeze({
    type: 'boolean',
    description: 'true=额外收 T-1/T-2 的补填（仅收归属当日者，并标注实际提交时刻）'
  })
});

/** 把冻结的 spec 拍平成 defineTool 需要的普通对象（不暴露冻结对象本身，避免宿主改写失败） */
export function toolParameters() {
  const out = {};
  for (const [k, v] of Object.entries(TOOL_PARAMETERS)) out[k] = { ...v };
  return out;
}

/**
 * 集合运算式证明：「没有那个入口」。
 * @returns {{ok:boolean, checked:string[], hits:Array<{source:string,key:string,token:string}>}}
 */
export function assertNoPermissiveFlags() {
  const hits = [];
  const checked = [];
  const scan = (source, keys) => {
    for (const key of keys) {
      checked.push(`${source}:${key}`);
      const low = String(key).toLowerCase();
      for (const tok of PERMISSIVE_FLAG_TOKENS) {
        if (low.includes(tok)) hits.push({ source, key, token: tok });
      }
    }
  };
  scan('CLI_OPTIONS', Object.keys(CLI_OPTIONS));
  scan('TOOL_PARAMETERS', Object.keys(TOOL_PARAMETERS));
  return { ok: hits.length === 0, checked, hits };
}

export const OPTIONS_META = Object.freeze({
  permissiveTokens: PERMISSIVE_FLAG_TOKENS,
  cliFlags: Object.keys(CLI_OPTIONS),
  toolParams: Object.keys(TOOL_PARAMETERS),
  note: '单一来源 + 冻结；「没有那个入口」用集合运算证明，不靠文本扫描',
  deviceLayer: '--devices / --device / --central / --local-root / --local-only / --allow-late 只影响"从哪儿读"，影响不了判定'
});
