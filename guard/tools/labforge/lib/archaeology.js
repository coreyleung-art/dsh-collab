"use strict";
/**
 * lib/archaeology.js v1.0.0 — 故障根因考古引擎（labforge 提取的可复用产物）
 *
 * 从历史修复报告/崩溃记录中系统提取问题，归纳根因模式，映射实验守护面。
 * 独立可复用：任何工具/脚本可 require。
 *
 * 功能:
 *   scanReports(dir)       扫描 repair-reports JSON → 结构化条目
 *   classify(entry)        按 6 大根因模式 M1-M6 归类
 *   summarize(entries)     统计: 模式频次/时间线/守护缺口
 *   guardMap(cards)        对照 labforge 实验卡 → 守护面缺口清单
 *
 * R006 ⑤⑥⑦⑧⑨ 对齐: 文档头/版本/日志回调/结构化输出/可CLI。
 */
const fs = require("node:fs");
const path = require("node:path");
const VERSION = "1.0.0";

/** 6 大根因模式（考古实证收敛） */
const PATTERNS = [
  { id: "M1", name: "版本遮蔽/漂移", regex: /遮蔽|shadow|版本不一致|依赖漏装|keyed slot|漂移|version mismatch/i,
    defense: "C7 deps 扫描 + guard-check-deps",
    remediation: "跑 labforge loop deps-shadow-regression（已建卡守护）; 有遮蔽则 mv 出 profile + guard-check-deps --fix",
    leanGate: "改 profile/package → guard_compliance(过 P0/P1/P2/P4/P5) + C7 验证" },
  { id: "M2", name: "全量物化内存失控", regex: /OOM|out of memory|SIGABRT|全量解压|堆上限|heap|内存暴涨|doctor 扫描/i,
    defense: "崩溃实验室 + 帧索引 + memory 卡",
    remediation: "先黑箱实验室复现(memory-crash-oom-repro) → P2-3/LRU 治理已落地 → loadStoredFrom 帧索引待窗口",
    leanGate: "改 runtime/配置 → guard_compliance + 崩溃实验室断言 + C1-C7" },
  { id: "M3", name: "重启竞态/启动器冲突", regex: /重启|双启动|孤儿|tool_calls|未落盘|竞态|重复拉起|端口冲突/i,
    defense: "P1 重启 + 孤儿卡 + restart 路由",
    remediation: "orphan-reconcile-regression 已守护; 双启动器 → 卸 launchd 保留 GUI; 重启走 graceful quit→open",
    leanGate: "改壳/重启 → guard_compliance(OP-restart 路由) + stability-watch 观察" },
  { id: "M4", name: "插件加载协议不符", regex: /插件.*崩|注册崩溃|私有函数|未导出|加载失败|apply 阶段|slot.*注册/i,
    defense: "OP-add-plugin 路由 + T4 + 冒烟",
    remediation: "待建卡 plugin-load-fail-regression: 插件工程 import+apply 冒烟(参考 dsh-plugin-workflow); 依赖私有 API → 查官方插件模板",
    leanGate: "加插件 → guard_compliance(OP-add-plugin-host) + C7 无遮蔽 + import 冒烟" },
  { id: "M5", name: "凭旧认知修", regex: /白名单|fuse|旧认知|NODE_OPTIONS|没查官方/i,
    defense: "P0 doc-check 门",
    remediation: "受限区操作前必跑 guard-doc-check 留证(gate-state 24h); 已由 guard-gate P0 机械强制",
    leanGate: "任何底层操作 → guard-gate 自动查 P0(无 24h 证据即拒); 补证走 guard_doc_check" },
  { id: "M6", name: "改完不验证/不留痕", regex: /没备份|未验证|无回滚|不留痕/i,
    defense: "C1-C7 + repair-report + P1 备份",
    remediation: "每次修改后跑 cld_health_check(C1-C7 概览) + repair_report 留痕; guard backup 强制 P1",
    leanGate: "修改后穷尽验证 C1-C7(guard-gate 结论依赖) + repair_report 报告入知识库" },
];

/** 扫描 repair-reports 目录 → 结构化条目 */
function scanReports(dir) {
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json")).sort();
  const entries = [];
  for (const f of files) {
    try {
      const d = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
      const text = JSON.stringify(d);
      const done = Array.isArray(d.done) ? d.done.join(" ") : String(d.done || "");
      const body = d.body && typeof d.body === "object" ? JSON.stringify(d.body) : "";
      entries.push({
        file: f,
        ts: String(d.ts || d.time || f.slice(0, 15)),
        title: String(d.title || d.type || f),
        node: String(d.node || d.from || "?"),
        text: `${text} ${done} ${body}`,
        summary: (d.summary || (Array.isArray(d.done) ? d.done[0] : done)).slice(0, 200),
      });
    } catch { /* skip unparsable */ }
  }
  return entries;
}

/** 按根因模式归类单条目（返回命中的模式数组；建设类返回 []） */
function classify(entry) {
  // 建设类报告(知识库/部件卡/工具立项/品牌定制/标准文档)非故障 → 归 INCIDENT 外
  if (/部件卡|knowledge|知识库|毕业审计|品牌|my-brand|hero|图标|dock|scaffold|立项|工具化|标准|规范|实验室|实验卡|regression|考古/.test(entry.title)) {
    return [];
  }
  return PATTERNS.filter((p) => p.regex.test(entry.text)).map((p) => p.id);
}

/** 区分问题报告 vs 建设报告 */
function classifyKind(entry) {
  const t = entry.title;
  if (/部件卡|knowledge|知识库|毕业审计|品牌|my-brand|hero|图标|dock|scaffold|立项|工具化|标准文档|规范|标准/.test(t)) return "build";
  if (/修复|崩溃|OOM|遮蔽|事故|问题|失败|恢复|会话|rootcause|消失|错误|error/.test(t)) return "incident";
  return classify(entry).length ? "incident" : "build";
}

/** 聚合统计: 模式频次 + 时间线 + 分类条目 */
function summarize(entries) {
  const withClass = entries.map((e) => ({ ...e, patterns: classify(e) }));
  const byPattern = {};
  for (const p of PATTERNS) byPattern[p.id] = { count: 0, examples: [] };
  for (const e of withClass) {
    for (const pid of e.patterns) {
      byPattern[pid].count++;
      if (byPattern[pid].examples.length < 3) byPattern[pid].examples.push(`${e.ts} ${e.title}`);
    }
  }
  const unclassified = withClass.filter((e) => e.patterns.length === 0).length;
  const incidents = withClass.filter((e) => e.patterns.length > 0).length;
  return { total: entries.length, incidents, unclassified, byPattern, entries: withClass };
}

/** 对照 labforge 卡 → 守护缺口（考古发现的模式无卡守护者） */
function guardMap(cardsDir, patterns = PATTERNS) {
  const guarded = new Set();
  if (fs.existsSync(cardsDir)) {
    for (const f of fs.readdirSync(cardsDir).filter((x) => x.endsWith(".json"))) {
      try {
        const c = JSON.parse(fs.readFileSync(path.join(cardsDir, f), "utf8"));
        const tags = (c.tags || []).join(" ") + " " + (c.title || "") + " " + (c.hypothesis || "");
        if (/M1|遮蔽|deps|shadow/i.test(tags)) guarded.add("M1");
        if (/M2|memory|oom|物化/i.test(tags)) guarded.add("M2");
        if (/M3|orphan|重启|reconcile/i.test(tags)) guarded.add("M3");
        if (/M4|plugin|load/i.test(tags)) guarded.add("M4");
        if (/M5|doc-check/i.test(tags)) guarded.add("M5");
        if (/M6|report/i.test(tags)) guarded.add("M6");
      } catch { /* skip */ }
    }
  }
  return {
    guarded: [...guarded],
    gaps: patterns.filter((p) => !guarded.has(p.id)).map((p) => ({ id: p.id, name: p.name, defense: p.defense })),
  };
}

module.exports = { PATTERNS, scanReports, classify, classifyKind, summarize, guardMap, VERSION };
