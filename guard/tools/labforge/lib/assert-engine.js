"use strict";
/**
 * lib/assert-engine.js v1.0.0 — 通用断言引擎（labforge 提取的可复用产物）
 *
 * 从任意 JSON 产物中按路径提取指标，对照 op+target 判定。独立于 labforge，
 * 任何工具/脚本可 require 复用（R006 ⑤⑥⑦⑧⑨ 对齐：文档头/版本/日志回调/可CLI）。
 *
 * 用法:
 *   const { evaluate, dig } = require("./lib/assert-engine.js");
 *   evaluate({ metric: "a.b", op: "gte", target: 10 }, metricsObj)  → {ok, value}
 */
const VERSION = "1.0.0";

/** 路径提取: "a.b[0].c" → 深取值 */
function dig(obj, pathExpr) {
  return String(pathExpr).split(".").reduce((acc, seg) => {
    if (acc === undefined || acc === null) return undefined;
    const m = seg.match(/^(\w+)\[(\d+)\]$/);
    if (m) return acc[m[1]]?.[Number(m[2])];
    return acc[seg];
  }, obj);
}

/** 单断言求值: {metric, op, target} → {ok, value} */
function evalMetric(value, op, target) {
  if (typeof value === "string") {
    switch (op) {
      case "contains": return value.includes(String(target));
      case "eq": return value === String(target);
      case "match": return new RegExp(String(target)).test(value);
      default: return false;
    }
  }
  const n = Number(value);
  if (!Number.isFinite(n)) return false;
  const t = Number(target);
  switch (op) {
    case "lt": return n < t;
    case "lte": return n <= t;
    case "gt": return n > t;
    case "gte": return n >= t;
    case "eq": return n === t;
    default: return false;
  }
}

/** 跑一组断言: [{id,metric,op,target,desc}] + metrics → [{id,metric,op,target,value,ok,desc}] */
function evaluate(assertions, metrics) {
  return (assertions || []).map((a) => {
    const value = dig(metrics, a.metric);
    const ok = value !== undefined && value !== null && evalMetric(value, a.op, a.target);
    return { id: a.id, metric: a.metric, op: a.op, target: a.target, value: value ?? null, ok, desc: a.desc };
  });
}

module.exports = { evaluate, dig, evalMetric, VERSION };
