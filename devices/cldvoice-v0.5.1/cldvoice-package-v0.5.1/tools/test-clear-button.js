#!/usr/bin/env node
/* CLD-Voice 清屏按钮 · 真实文件渲染测试
 * 直接加载 lib/client.js（不复制逻辑），把 FloatBall 组件函数调起来，
 * 模拟桥消息造出历史记录 → 点两次 🧹 清屏 → 断言记录被清空。
 */
const fs = require("fs");
const path = require("path");

const FILE = process.argv[2] || path.join(process.env.HOME, "dsh-collab/cld-voice/plugin-voice-pack/lib/client.js");
const src = fs.readFileSync(FILE, "utf8");

let captured = null;
global.window = {
  __ModuleLoader__: {
    load: (def) => { captured = def; },
  },
};
global.document = { addEventListener() {}, removeEventListener() {} };
const _store = {};
global.localStorage = {
  getItem: (k) => (k in _store ? _store[k] : null),
  setItem: (k, v) => { _store[k] = String(v); },
  removeItem: (k) => { delete _store[k]; },
};
global.fetch = () => Promise.resolve({ json: () => Promise.resolve({ packs: [
  { id: "zh", name: "国语·灿灿", desc: "标准普通话", dialect: "普通话" },
  { id: "yue", name: "粤语·灿灿", desc: "地道粤语口语", dialect: "yue" },
] }) });
global.console.warn = () => {};

// --- 极简 React 桩 ---
function el(type, props, ...children) {
  const flat = [];
  for (const c of children.flat(Infinity)) if (c !== null && c !== undefined && c !== false) flat.push(c);
  return { type, props: Object.assign({}, props, flat.length ? { children: flat } : {}) };
}
const React = {
  createElement: el,
  Fragment: "Fragment",
  useState: (init) => [init, () => {}],
  useEffect: (fn) => { try { const c = fn(); } catch (e) {} },
  useRef: (init) => ({ current: init === undefined ? null : init }),
  useMemo: (fn) => { try { return fn(); } catch (e) { return null; } },
  useCallback: (fn) => fn,
};
const ReactDOM = { createPortal: (node) => node };

// --- 假 WebSocket：可由测试派发消息 ---
let lastWS = null;
class FakeWS {
  constructor(url) { this.url = url; this.readyState = 1; this.sent = []; lastWS = this; }
  send(d) { this.sent.push(d); }
  close() { this.readyState = 3; }
}
global.WebSocket = FakeWS;

// --- AudioContext 桩（toggleRec 会 ensurePlay） ---
global.AudioContext = class {
  constructor() { this.state = "running"; this.destination = {}; this.sampleRate = 24000; this.currentTime = 0; }
  createGain() { return { gain: { value: 1 }, connect() {} }; }
  createBufferSource() { return { buffer: null, connect() {}, start() {}, stop() {}, onended: null }; }
  createBuffer() { return { getChannelData: () => new Float32Array(1024) }; }
  resume() { return Promise.resolve(); }
  decodeAudioData() { return Promise.resolve({ getChannelData: () => new Float32Array(1024), duration: 1, length: 1024 }); }
};
global.navigator = { mediaDevices: { getUserMedia: () => Promise.reject(new Error("no-mic-in-test")) } };

// --- 加载真实文件 ---
// eslint-disable-next-line no-eval
eval(src);
if (!captured) { console.error("✗ 未捕获到模块定义"); process.exit(1); }
const mod = captured.factory((name) => {
  if (name === "react") return React;
  if (name === "react-dom") return ReactDOM;
  throw new Error("unexpected require: " + name);
});

// --- 用假 ctx 抓到 FloatBall 组件 ---
let FloatBall = null;
const slots = { register: (opts, comp) => { FloatBall = comp; return () => {}; } };
const ctx = {
  effect: (fn) => { try { fn(); } catch (e) {} },
  inject: (deps, fn) => { try { fn({ slots }); } catch (e) {} },
  slots,
};
mod.apply(ctx);
if (!FloatBall) { console.error("✗ 未注册 FloatBall"); process.exit(1); }
console.log("✓ 已从真实文件加载并注册 FloatBall");

// --- 工具：遍历元素树 ---
function walk(node, out = []) {
  if (!node || typeof node !== "object") return out;
  out.push(node);
  const ch = node.props && node.props.children;
  if (Array.isArray(ch)) ch.forEach((c) => walk(c, out));
  else if (ch) walk(ch, out);
  return out;
}
function findByText(tree, text) {
  return walk(tree).find((n) => {
    const c = n.props && n.props.children;
    return Array.isArray(c) && c.some((x) => typeof x === "string" && x.includes(text));
  });
}
function findButton(tree, text) {
  return walk(tree).find((n) => {
    if (n.type !== "button") return false;
    const c = n.props && n.props.children;
    return Array.isArray(c) && c.some((x) => typeof x === "string" && x.includes(text));
  });
}
function textOf(tree) {
  return walk(tree).map((n) => {
    const c = n.props && n.props.children;
    return Array.isArray(c) ? c.filter((x) => typeof x === "string").join("") : "";
  }).join(" | ");
}

const props = { inputActions: null };
let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { console.log("  ✅ " + name); pass++; }
  else { console.log("  ❌ " + name + (extra ? "  → " + extra : "")); fail++; }
}

// ===== 1. 点悬浮球打开面板，确认初始为空 =====
let tree = FloatBall(props);
const ball = findByText(tree, "🎤");
check("渲染出悬浮球", !!ball);
ball.props.onClick({ detail: 1, stopPropagation() {} });
tree = FloatBall(props);
check("面板标题栏出现 🧹 清屏 按钮", !!findButton(tree, "🧹 清屏"));
check("初始显示空态占位", textOf(tree).includes("还没有对话"));

// ===== 2. 通过假桥造出历史记录 =====
const recBtn = findButton(tree, "● 说话");
recBtn.props.onClick({ stopPropagation() {} });
check("已建立 WS 连接且 URL 带语音包", !!lastWS && lastWS.url.includes("pack="), lastWS && lastWS.url);
lastWS.onmessage({ data: JSON.stringify({ type: "transcript_delta", delta: "帮我做一个语音功能" }) });
lastWS.onmessage({ data: JSON.stringify({ type: "text_delta", delta: "收到，我记下了" }) });
lastWS.onmessage({ data: JSON.stringify({ type: "done" }) });
tree = FloatBall(props);
const t2 = textOf(tree);
check("历史记录里有用户那句", t2.includes("帮我做一个语音功能"));
check("历史记录里有 AI 那句", t2.includes("收到，我记下了"));
check("标题栏显示条数", textOf(tree).includes("2 条"), textOf(tree).match(/\d+ 条/) || "无");

// ===== 3. 第一次点清屏：进入待确认，不得清空 =====
let btn = findButton(tree, "🧹 清屏");
btn.props.onClick({ stopPropagation() {} });
tree = FloatBall(props);
check("第一次点击后按钮变成「确认清空?」", !!findButton(tree, "确认清空?"), textOf(tree));
check("第一次点击后记录仍在（防误删）", textOf(tree).includes("帮我做一个语音功能"));

// ===== 4. 第二次点：真清空 =====
btn = findButton(tree, "确认清空?");
btn.props.onClick({ stopPropagation() {} });
tree = FloatBall(props);
const t4 = textOf(tree);
check("第二次点击后历史记录被清空", !t4.includes("帮我做一个语音功能") && !t4.includes("收到，我记下了"));
check("清空后回到空态占位", t4.includes("还没有对话"));
check("清空后按钮复位为「🧹 清屏」", !!findButton(tree, "🧹 清屏"));

// ===== 5. 清空后仍可继续记录（不是把功能弄坏） =====
lastWS.onmessage({ data: JSON.stringify({ type: "transcript_delta", delta: "第二轮的新内容" }) });
lastWS.onmessage({ data: JSON.stringify({ type: "done" }) });
tree = FloatBall(props);
check("清空后可继续记录新内容", textOf(tree).includes("第二轮的新内容"));
check("旧内容不会回来", !textOf(tree).includes("帮我做一个语音功能"));

// ===== 6. 待确认态超时(3.5s)自动取消, 避免按钮一直停在"确认清空?" =====
findButton(tree, "🧹 清屏").props.onClick({ stopPropagation() {} });
check("超时前处于待确认", !!findButton(FloatBall(props), "确认清空?"));
console.log("  … 等待 4s 观察自动取消");
setTimeout(() => {
  const t6 = FloatBall(props);
  check("3.5s 后自动取消待确认态", !!findButton(t6, "🧹 清屏") && !findButton(t6, "确认清空?"));
  check("自动取消不会误清记录", textOf(t6).includes("第二轮的新内容"));
  console.log(`\n结果: PASS=${pass} FAIL=${fail}`);
  process.exit(fail ? 1 : 0);
}, 4000);
