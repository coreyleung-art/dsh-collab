// dsh-plugin-writing-guards · 写作过程守卫
// 业务内核：★ 危险原语【以命令白名单收口】（R006 ⑩-2 逐字允许：
//   「有能力时用【命令白名单】收口」）—— 本内核【不】暴露任意命令执行：
//   ★ 只允许 5 个冻结白名单子命令，且每个都映射到固定路径的既有 Python 工具。
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { existsSync, appendFileSync, mkdirSync } from "node:fs";
import { homedir } from "node:os";

const HERE = dirname(fileURLToPath(import.meta.url));
const COLLAB = join(homedir(), "dsh-collab");

// ── ⑩-1 【没有那个入口】：白名单是【冻结常量】；不在表内的输入结构上无法表达 ──
export const WHITELIST = Object.freeze({
  "write-guard-scan": { script: "tools/atomic-write-guard.py" },
  "denominator-require": { script: "tools/denominator-declare.py" },
  "ledger-gen": { script: "tools/correction-ledger-gen.py" },
  "live-read-guard": { script: "tools/live-read-guard.py" },
  "lint-inventory": { script: "tools/lint-inventory.py" },
});

// ── ⑦ 统一日志：固定路径，失败也留痕 ──
const LOG_PATH = join(COLLAB, "logs", "dsh-plugin-writing-guards.log");
function logLine(kind, detail) {
  try {
    mkdirSync(dirname(LOG_PATH), { recursive: true });
    appendFileSync(LOG_PATH, `${new Date().toISOString()} ${kind} ${detail}\n`);
  } catch (_) { /* 尽力留痕，不阻断主流程 */ }
}
export function logPath() { return LOG_PATH; }

export function describeCapabilities() {
  return {
    tool: "writing-guards",
    purpose: "写作过程守卫：非原子写扫描 · 数字口径申报 · 更正账生成 · 照抄旧读数疑似检测 · 既有 lint 清单",
    can: [
      "扫描本仓 .py 里的【非原子写关键文件】（open(p,\"w\") 且无 os.replace）",
      "扫描一份文档里的【裸数】（无窗口/分子/分母声明）",
      "从台账生成【上一版→本版更正账】表",
      "对两份文档做【照抄旧读数】的疑似检测（★ 只报疑似）",
      "列出本仓【既有 lint/gate 清单】并生成可粘进子代理提示词的片段",
    ],
    cannot: [
      "★ 结构上不可达：任意命令执行 —— 白名单是【冻结常量】，不在表内的 key 无法表达",
      "★ 结构上不可达：写被扫对象 —— 五条工具全部【只读】",
      "★ 不判「照抄」—— 逐字相同有两种成因（照抄 / 真的没变），文本层同形 ⇒ 只报「疑似」",
      "★ 不替代现测 —— 本工具报出的每一项都须人工现测复核",
    ],
  };
}

// ── 白名单执行：只允许 WHITELIST 内的 key；其余一律拒绝（⑩-4 失败即停）──
export function runGuard(key, argv = [], options = {}) {
  const dryRun = options.dryRun === true;
  const entry = Object.prototype.hasOwnProperty.call(WHITELIST, key) ? WHITELIST[key] : null;
  if (!entry) {
    logLine("REJECT", `key=${key} 不在白名单`);
    return { ok: false, code: 2, error: `未知子命令 ${key}（白名单 ${Object.keys(WHITELIST).join(",")}）`, dryRun };
  }
  const scriptPath = join(COLLAB, entry.script);
  if (!existsSync(scriptPath)) {
    logLine("MISSING", `key=${key} script=${entry.script}`);
    return { ok: false, code: 2, error: `目标脚本不在位（★ 读不到 ≠ 不存在）: ${entry.script}`, dryRun };
  }
  if (dryRun) {
    logLine("DRYRUN", `key=${key} script=${entry.script}`);
    return { ok: true, code: 0, dryRun: true, wouldRun: ["python3", entry.script, ...argv] };
  }
  // ★ 列表传参（★ 不用 shell）⇒ 结构上没有「管道换掉退出码」这个面
  const r = spawnSync("python3", [scriptPath, ...argv], { encoding: "utf8", timeout: 60000 });
  const code = r.status === null ? 2 : r.status;
  logLine("RUN", `key=${key} exit=${code} argv=${JSON.stringify(argv).slice(0, 120)}`);
  return { ok: code === 0, code, stdout: r.stdout || "", stderr: r.stderr || "", dryRun: false };
}

export async function runStatus(options = {}) {
  const dryRun = options.dryRun === true;
  const present = Object.entries(WHITELIST).map(([k, v]) => ({
    key: k, script: v.script, present: existsSync(join(COLLAB, v.script)),
  }));
  const missing = present.filter((p) => !p.present).map((p) => p.script);
  return {
    ok: missing.length === 0,
    tool: "writing-guards",
    dryRun,
    checkedAt: new Date().toISOString(),
    whitelist: present,
    // ★ 三态：全在 ⇒ PASS；有缺 ⇒ FAIL；一个都没有 ⇒ UNDECIDABLE
    verdict: present.length === 0 ? "UNDECIDABLE" : (missing.length === 0 ? "PASS" : "FAIL"),
    missing,
    logPath: LOG_PATH,
    note: dryRun ? "dry-run：未做任何变更" : "真实状态（只读扫描，无变更）",
  };
}
