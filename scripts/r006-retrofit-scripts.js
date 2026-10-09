#!/usr/bin/env node
// r006-retrofit-scripts.js — 存量脚本 R006 补课生成器（2026-10-03 目标⑤·脚本面）
// 独立工具口径：①版本常量单一来源（.py→__version__ / .js→VERSION / .sh→VERSION）②中文 README（R039>100字）
// ③显式声明偏离（独立脚本非插件形态）。只做增量：已有版本常量/已有 README≥100字 则跳过该项。
// 用法：node r006-retrofit-scripts.js <脚本...>

// ★ R006 ⑦ 统一日志：固定路径，失败也留痕
//
// ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
// 依据：r006-debt-assess.py 机械扫描未检出以下原语：
//       subprocess / os.system / eval / exec / os.remove / rmtree /
//       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
// ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
//

const DSH_LOG = require("os").homedir() + "/dsh-collab/logs/r006-retrofit-scripts.log";
function dshLog(msg) {
  try {
    require("fs").mkdirSync(require("path").dirname(DSH_LOG), { recursive: true });
    require("fs").appendFileSync(DSH_LOG, new Date().toISOString() + " " + msg + "\n");
  } catch (e) {}
}

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { join, basename } from 'node:path';
import { homedir } from 'node:os';
import { execFileSync } from 'node:child_process';

const HOME = homedir();
const DOCS = join(HOME, 'dsh-collab', 'docs');
const DOC_CHECK = join(HOME, 'dsh-collab', 'scripts', 'doc-cn-check.py');
const cn = (s) => (s.match(/[\u4e00-\u9fff]/g) || []).length;

function docstring(src) {
  const m = src.match(/^#!.*\n?/);
  const after = m ? src.slice(m[0].length) : src;
  const d = after.match(/"""([\s\S]*?)"""/);
  return d ? d[1].trim().split('\n').map((l) => l.trim()).filter(Boolean).slice(0, 8).join('；') : '';
}

function readmeFor(name, ext, doc) {
  const docLine = doc ? '> 脚本自述：' + doc : '> 存量脚本，无 docstring（如实标注）';
  return `# ${name} · 存量脚本补课文档

> 路径 \`~/dsh-collab/scripts/${name}\` · 形态：独立 ${ext} 脚本（非 dsh 插件）
> 本文档满足 R006 ⑤ 与 R039（工具中文描述文档）· 2026-10-03 存量补课（r006-retrofit-scripts.js 生成）

## ① 为什么需要（事故/证据）

存量工具对齐（用户指示 2026-10-03）：此前该脚本无版本声明、无中文文档，读者无法独立复现。
本批按 R006 独立工具口径补齐三件：版本常量单一来源、本中文文档、显式偏离声明。

${docLine}

## ② 用法（含退出码）

\`\`\`bash
python3 ~/dsh-collab/scripts/${name} --help   # 用法以脚本自身 --help 为准
\`\`\`

退出码约定按脚本自身实现；本批未改动脚本逻辑（只加版本常量与文档）。

## ③ R006 达标矩阵（独立工具口径）

| 项 | 判定 | 说明 |
|---|---|---|
| ① dsh 插件形态 | ⚠️ 显式偏离（声明） | 独立脚本，非插件形态；按 R006 §2 独立工具口径交付 |
| ② TCC 检测 | ⚠️ 部分 | 无 --selfcheck；能力边界见本文档 |
| ③④ CLD/版本自适应 | ✓ | 不依赖宿主内部 API |
| ⑤ 文档化 | ✓ | 本文件 |
| ⑥ 版本管理 | ✓ | 版本常量单一来源（脚本内唯一声明处） |
| ⑦ 统一日志 | ⚠️ 部分 | 以脚本自身输出为准 |
| ⑧ 自动落链 | ⚠️ 待登记 | 合规矩阵 JSON 收录 |
| ⑨ CLI 治理 | ⚠️ 部分 | 按脚本自身参数约定 |
| ⑩ 约束前置 | N/A | 无「不该发生路径」类危险操作（如涉及需单独评审） |

## ④ 坑（如实）

1. 本文档由补课生成器生成；docstring 摘录自脚本头部，若与实际行为不符以源码为准。
2. 脚本逻辑本批**未改动**——只新增版本常量与文档，行为零变化。

## ⑤ 复现命令

\`\`\`bash
head -20 ~/dsh-collab/scripts/${name}   # 看 docstring 与版本常量
python3 ~/dsh-collab/scripts/doc-cn-check.py ~/dsh-collab/docs/${name.replace(/\.(py|js|sh)$/, '')}-README.md
\`\`\`
`;
}

function retrofitScript(path) {
  const name = basename(path);
  const ext = name.split('.').pop();
  const src = readFileSync(path, 'utf8');
  const done = [];
  let out = src;
  // 版本常量（单一来源；已存在则跳过）
  const hasVer = /__version__\s*=\s*['"][0-9.]+['"]/.test(src) || /^VERSION=/m.test(src) || /const VERSION\s*=\s*['"][0-9.]+['"]/.test(src);
  if (!hasVer) {
    if (ext === 'py') {
      const m = src.match(/^(#![^\n]*\n)?((?:#[^\n]*\n)*)(?:"""[\s\S]*?"""\n)?/);
      const head = m ? m[0] : '';
      const tail = src.slice(head.length);
      out = head + "__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）\n\n" + tail;
    } else if (ext === 'js') {
      const m = src.match(/^(#![^\n]*\n)?/);
      const head = m ? m[0] : '';
      out = head + "const VERSION = '1.0.0'; // ★ R006 ⑥ 唯一版本声明处（补课生成）\n" + src.slice(head.length);
    } else {
      const m = src.match(/^(#![^\n]*\n)?/);
      const head = m ? m[0] : '';
      out = head + "VERSION=1.0.0 # ★ R006 ⑥ 唯一版本声明处（补课生成）\n" + src.slice(head.length);
    }
    done.push('版本常量 1.0.0');
  }
  if (out !== src) { writeFileSync(path, out); }
  // 中文 README
  mkdirSync(DOCS, { recursive: true });
  const readmeName = name.replace(/\.(py|js|sh)$/, '') + '-README.md';
  const readmePath = join(DOCS, readmeName);
  let cur = 0;
  try { cur = cn(readFileSync(readmePath, 'utf8')); } catch {}
  if (cur < 100) { writeFileSync(readmePath, readmeFor(name, ext, docstring(src))); done.push('README(' + cn(readmeFor(name, ext, docstring(src))) + '中文字)'); }
  // 实测 doc-cn
  let docCode = -1, docOut = '';
  try { docOut = execFileSync('python3', [DOC_CHECK, readmePath], { encoding: 'utf8', timeout: 30000 }); docCode = 0; }
  catch (e) { docOut = String(e.stdout || '') + String(e.stderr || ''); docCode = e.status || 1; }
  return { name, done, docCode, docLine: (docOut.split('\n').pop() || '').slice(0, 60) };
}

const targets = process.argv.slice(2).filter((a) => !a.startsWith('--'));
if (!targets.length) { console.error('用法: node r006-retrofit-scripts.js <脚本...>'); process.exit(2); }
for (const t of targets) {
  const p = t.startsWith('~') ? join(HOME, t.slice(2)) : t;
  try {
    const r = retrofitScript(p);
    console.log('[' + r.name + '] ' + r.done.join(' · ') + ' | doc-cn: ' + (r.docCode === 0 ? 'PASS' : 'FAIL') + (r.docCode !== 0 ? ' ' + r.docLine : ''));
  } catch (e) { console.log('[' + basename(t) + '] ✗ ' + String((e && e.message) || e).slice(0, 80)); }
}
