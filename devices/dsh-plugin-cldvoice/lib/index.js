// dsh-plugin-cldvoice — host 端
// 提供:
//   POST /voice/draft —— 语音讨论成稿: 调用 CLD-Voice 后端 8902 的成稿引擎, 落盘草稿, 返回内容
//   说明: 全双工语音对话(client↔8904 桥↔火山)在浏览器端直连, host 仅承载成稿落盘 + 读黑板
import { appendFile, mkdir } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { runSelfCheck } from './selfcheck.js';

export const name = 'cldvoice';
export const inject = ['webServer'];

const VOICE_DRAFTS = process.env.CLDVOICE_DRAFTS || join(homedir(), 'dsh-collab', 'cld-voice', 'drafts');
const GENEBANK = process.env.CLDVOICE_8902 || 'http://127.0.0.1:8902';

function json(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(payload),
    'cache-control': 'no-store',
  });
  res.end(payload);
}
function readBody(req) {
  return new Promise((resolveBody, reject) => {
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => resolveBody(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

export function apply(ctx) {
  // R014 自查门（v0.6.1 补课；同步纯检查，冒烟独立于 cli.js —— R040 自查不得自指）
  try {
    runSelfCheck('cldvoice', {
      requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
      requiredSymbols: ['appendFile', 'mkdir', 'homedir', 'join'],
    });
  } catch (e) { /* 自查失败不阻塞 */ }
  // 修复 2026-09-09: Cordis/webserver 规范——inject webServer 后用 webServer.register({kind,path,handler})
  // (先例: client-connection 的 ctx.webServer.register + ctx.effect 包裹; route 非函数, register 返回 disposer)
  const webServer = ctx.webServer;
  if (!webServer) { console.error("[cldvoice] webServer 缺失(空闲, 不挂路由)"); return; }

  // POST /voice/draft —— 语音讨论成稿
  ctx.effect(() => webServer.register({
    kind: "exact", path: "/voice/draft",
    handler: async (req, res) => {
      if (req.method !== "POST") return json(res, 405, { ok: false, error: "method not allowed" });
      try {
        const raw = JSON.parse(await readBody(req));
        const discussion = Array.isArray(raw.discussion) ? raw.discussion : [];
        const title = String(raw.title || "语音需求").slice(0, 80);
        const up = await fetch(GENEBANK + "/api/draft", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ discussion, title, insert: false }),
        });
        const d = await up.json();
        if (!d.success) return json(res, 500, { ok: false, error: d.error || "draft failed" });
        await mkdir(VOICE_DRAFTS, { recursive: true });
        const ts = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
        const fname = join(VOICE_DRAFTS, `cldvoice-${ts}.md`);
        // 落盘文件 = 纯总结 + 完整"讨论留痕"(原始语音逐字, 供回溯)
        let disk = (d.content || "").trim();
        if (discussion.length) {
          const trace = ["", "", "## 讨论留痕", "| 时间 | 角色 | 内容 |", "|------|------|------|"];
          for (const seg of discussion.slice(-30)) {
            const role = ({ user: "用户", ai: "AI" })[seg.role] || "—";
            trace.push(`| ${seg.ts || ""} | ${role} | ${String(seg.text || "").slice(0, 80)} |`);
          }
          disk += "\n" + trace.join("\n");
        }
        await appendFile(fname, disk);
        // 注入 CLD 的 content 只含纯总结(不含留痕)
        json(res, 200, { ok: true, id: d.id, title: d.title, content: d.content, file: fname, stats: d.stats });
      } catch (e) {
        json(res, 500, { ok: false, error: String((e && e.message) || e) });
      }
    },
  }), "cldvoice: POST /voice/draft");

  // GET /voice/health
  ctx.effect(() => webServer.register({
    kind: "exact", path: "/voice/health",
    handler: async (req, res) => {
      if (req.method !== "GET") return json(res, 405, { ok: false, error: "method not allowed" });
      json(res, 200, { ok: true, service: "cldvoice", drafts: VOICE_DRAFTS, backend: GENEBANK });
    },
  }), "cldvoice: GET /voice/health");
  // GET /voice/test — 诊断页(CLD renderer ws+麦克风能力)
  ctx.effect(() => webServer.register({
    kind: "exact", path: "/voice/test",
    handler: async (req, res) => {
      const html = '<!DOCTYPE html><html><body style="font-family:monospace;background:#111;color:#0f0;padding:20px"><h3>CLD-Voice diag</h3><div id="log">testing...</div><script>const L=document.getElementById("log");const a=[];function log(s){a.push(s);L.innerHTML=a.join("<br>");}log("1. WS 8905 connecting...");try{const ws=new WebSocket("ws://127.0.0.1:8905");ws.onopen=()=>{log("1. WS 8905 OK");log("2. mic requesting...");navigator.mediaDevices.getUserMedia({audio:true}).then(st=>{log("2. MIC OK tracks="+st.getAudioTracks().length);log("ALL PASS: env ok, problem in plugin client");st.getTracks().forEach(t=>t.stop());ws.close();}).catch(e=>log("2. MIC FAIL "+e.message));};ws.onerror=()=>log("1. WS 8905 FAIL");ws.onmessage=ev=>{if(ev.data.indexOf("ready")>=0)log("1b. got ready OK");};}catch(e){log("1. WS construct FAIL: "+e.message);}</script></body></html>';
      res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
      res.end(html);
    },
  }), "cldvoice: GET /voice/test");

  // POST /voice/fill-composer — i9-runner 成稿后把文本送 CLD 输入框(经 host 内存中转)
  // GET /voice/fill-poll — CLD client 轮询拉取待填文本(取出即清)
  let lastFill = ""; 
  ctx.effect(() => webServer.register({
    kind: "exact", path: "/voice/fill-composer",
    handler: async (req, res) => {
      if (req.method !== "POST") return json(res, 405, { ok: false, error: "method not allowed" });
      try {
        const raw = JSON.parse(await readBody(req));
        lastFill = String(raw.text || "").slice(0, 8000);
        json(res, 200, { ok: true, len: lastFill.length });
      } catch (e) { json(res, 500, { ok: false, error: String((e && e.message) || e) }); }
    },
  }), "cldvoice: POST /voice/fill-composer");
  ctx.effect(() => webServer.register({
    kind: "exact", path: "/voice/fill-poll",
    handler: async (req, res) => {
      if (req.method !== "GET") return json(res, 405, { ok: false, error: "method not allowed" });
      const t = lastFill; lastFill = ""; // 取即清(单消费者)
      json(res, 200, { ok: true, text: t });
    },
  }), "cldvoice: GET /voice/fill-poll");


}
