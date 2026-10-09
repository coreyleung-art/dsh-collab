#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLD-Voice MVP 后端 — whisper 转写 + 成稿引擎

功能:
  POST /api/asr      multipart 音频 → whisper 转写文本
  POST /api/record   接收整段录音(前端分段上传) → 返回转写
  POST /api/draft    讨论内容(多段) → 结构化 markdown 需求文件
  GET  /api/drafts   已生成的草稿列表
  POST /api/draft/insert  成稿插入 CLD 上下文(黑板 notes/)

运行: ./venv/bin/python asr_server.py [--port 8902]
"""
import argparse, base64, io, json, os, re, time, datetime, uuid
import http.server, socketserver, threading, wave

# ───────── whisper ─────────
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")
# 外网受限时用本地模型路径（绕过 faster-whisper 的网络下载检查）
_HF_CACHE = os.path.expanduser("~/.cache/huggingface/hub")
def _local_model_path(model_name="small"):
    """找本地缓存的 faster-whisper 模型路径"""
    base = os.path.join(_HF_CACHE, f"models--Systran--faster-whisper-{model_name}", "snapshots")
    if os.path.isdir(base):
        snaps = sorted(os.listdir(base))
        if snaps:
            return os.path.join(base, snaps[0])
    return model_name  # 无本地缓存则退回模型名

_model = None
_model_lock = threading.Lock()
_model_path = _local_model_path(WHISPER_MODEL)

def get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from faster_whisper import WhisperModel
                # 用本地路径加载，避免 download_model 网络卡死
                _model = WhisperModel(_model_path, device="cpu", compute_type="float32")
    return _model

def _ensure_wav(audio_bytes: bytes, fmt="webm") -> bytes:
    """webm/其他格式 → wav（whisper 需可解码音频）"""
    import subprocess, tempfile
    # 尝试直接给 whisper（若是 wav 则跳过）
    if audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE":
        return audio_bytes
    # 用 ffmpeg 转 wav
    with tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False) as tmp_in:
        tmp_in.write(audio_bytes)
        in_path = tmp_in.name
    out_path = in_path + ".wav"
    try:
        r = subprocess.run(["/opt/homebrew/bin/ffmpeg", "-y", "-i", in_path, "-ar", "16000", "-ac", "1", out_path],
                          capture_output=True, timeout=30)
        if r.returncode != 0:
            return audio_bytes  # 转换失败回退原样
        with open(out_path, "rb") as f:
            return f.read()
    except Exception:
        return audio_bytes
    finally:
        for p in (in_path, out_path):
            try: os.unlink(p)
            except Exception: pass

def transcribe_wav(wav_bytes: bytes) -> dict:
    """音频字节 → 文本（自动转 wav）"""
    audio = _ensure_wav(wav_bytes)
    t0 = time.time()
    model = get_model()
    segments, info = model.transcribe(io.BytesIO(audio), language="zh")
    text = "".join(s.text for s in segments).strip()
    return {"text": text, "asr_ms": int((time.time()-t0)*1000), "duration_s": round(info.duration, 2)}

# ───────── 对话应答引擎（方舟豆包优先 / GLM 兜底） ─────────
import urllib.request

def _load_key(env_name, yaml_name):
    """从 env → ~/.dsh/.credentials.yaml → ~/.dsh/.env 读 key（兼容 yaml 冒号与 env 等号）"""
    v = os.environ.get(env_name, "").strip()
    if v:
        return v
    for p in (os.path.expanduser("~/.dsh/.credentials.yaml"),
              os.path.expanduser("~/.dsh/.env")):
        try:
            for line in open(p, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line.startswith(yaml_name):
                    v = line.split("=", 1)[-1].split(":", 1)[-1].strip().strip('"').strip("'")
                    break
        except Exception:
            pass
        if v:
            return v
    return ""

# 方舟豆包（火山 Ark，OpenAI 兼容）
_ARK_KEY = _load_key("ARK_API_KEY", "ARK_API_KEY")
ARK_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
ARK_MODEL = os.environ.get("ARK_MODEL", "")

# GLM 兜底
_GLM_KEY = _load_key("GLM_API_KEY", "GLM_API_KEY")
GLM_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
GLM_MODEL = os.environ.get("GLM_MODEL", "glm-4-flash")

SYSTEM_PROMPT = ("你是 CLD-Voice 的需求协作伙伴，用户正在用语音描述需求。"
                 "你的任务：1) 简短确认你听懂了核心点；2) 最多追问一个最关键的不明确处；"
                 "3) 每轮回应控制在 60 字以内，口语化，像真人对话，不要列清单。"
                 "对话会持续多轮，用户可随时打断补充。")

def _chat(provider: dict, discussion: list) -> dict:
    """通用 chat 调用（OpenAI 兼容 body）"""
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for d in discussion[-12:]:
        msgs.append({"role": "user", "content": d.get("text", "")})
    body = json.dumps({"model": provider["model"], "messages": msgs,
                       "max_tokens": 150, "temperature": 0.7}).encode()
    req = urllib.request.Request(provider["url"], data=body, method="POST",
        headers={"Authorization": "Bearer " + provider["key"],
                 "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read().decode())
        reply = d["choices"][0]["message"]["content"].strip()
        return {"reply": reply, "llm_ms": int((time.time()-t0)*1000), "model": provider["model"]}
    except Exception as e:
        return {"reply": "", "error": str(e)[:150], "llm_ms": int((time.time()-t0)*1000)}

def ask_reply(discussion: list) -> dict:
    """应答：豆包(ARK)优先，未配/失败则 GLM 兜底"""
    if _ARK_KEY and ARK_MODEL:
        r = _chat({"url": ARK_URL, "key": _ARK_KEY, "model": ARK_MODEL}, discussion)
        if r.get("reply"):
            return r
        gl = _chat({"url": GLM_URL, "key": _GLM_KEY, "model": GLM_MODEL}, discussion) if _GLM_KEY else r
        return gl if gl.get("reply") else r
    if _GLM_KEY:
        return _chat({"url": GLM_URL, "key": _GLM_KEY, "model": GLM_MODEL}, discussion)
    return {"reply": "(未配置 ARK/GLM key，跳过应答)", "error": "no-key"}

def glm_reply(discussion: list) -> dict:
    """兼容旧名：等同 ask_reply"""
    return ask_reply(discussion)

# ───────── 成稿引擎 ─────────

# ───────── 成稿引擎（LLM 主动提炼，带关键词兜底） ─────────

_CLEAN_MARKER = re.compile(r"^\s*[-*]\s*(无|没有|待补充|未识别到明确需求|无明确约束|无明确决策|.*待补充.*|暂不确定|未知)\s*$", re.IGNORECASE)
_CLEAN_SECTION = re.compile(r"^#+\s*(背景|功能需求|非功能需求|决策记录|待确认问题|约束|其他讨论)(\s*/?\s*.*)?$", re.IGNORECASE)

def _strip_markers(md: str) -> str:
    """去掉 LLM 成稿里的空壳占位(『无/待补充/未识别』)与随之空掉的小节, 让记录干净"""
    lines = md.splitlines()
    out = []
    pending_header = None
    for ln in lines:
        s = ln.strip()
        # 折叠嵌套列表: "- - xxx" → "- xxx"; 去掉行内多余"# "泄漏
        if s.startswith("- - "): s = "- " + s[4:]
        elif s.startswith("- -"): s = "-"
        if s.startswith("- ## "): s = s[3:]
        # 记录即将到来的小节标题
        if _CLEAN_SECTION.match(s):
            if pending_header is not None and not out[-1:]:
                pass
            pending_header = ln
            out.append(ln)
            continue
        # 这一行是占位 marker
        if _CLEAN_MARKER.match(s):
            if pending_header is not None and out and out[-1].strip() == pending_header.strip():
                out.pop()
            pending_header = None
            continue
        # 普通内容行
        pending_header = None
        out.append(s)
    # 去掉"空小节头": 一个 #小节 头若后面直到**下一个小节头/文件尾**之间没有任何内容行, 就删掉
    # 先把连续空行压成一个分隔, 简化判断
    cleaned = []
    for ln in out:
        cleaned.append(ln)
    # 遍历重建: 遇到小节头时先暂存, 若后续有内容行再输出
    final = []
    buf_header = None
    for ln in cleaned:
        if _CLEAN_SECTION.match(ln.strip()):
            # 遇到新小节头: 之前缓存的 header 若无任何内容则丢弃(空小节)
            buf_header = ln   # 先清掉旧header(若有内容早已落盘; 无内容则被丢弃)
            continue
        # 有内容行
        if buf_header is not None:
            final.append(buf_header)
            buf_header = None
        if ln.strip():
            final.append(ln)
    # 结尾的 buf_header(空小节)丢弃
    # 在每个 #小节 头前补一个空行, 保证可读性
    pretty = []
    for ln in final:
        if _CLEAN_SECTION.match(ln.strip()) and pretty:
            pretty.append("")
        pretty.append(ln)
    return "\n".join(pretty).strip()


_DRAFT_LLM_PROMPT = (
    "你是需求整理引擎。下面是一段「用户与 AI 协作描述需求」的语音讨论记录。"
    "请从真实对话里主动提炼用户到底想要什么，输出一份结构化需求清单，用 markdown。\n"
    "要求：\n"
    "1. 只输出下面这几节，每节有实质内容才写，没有就整节省略，禁止写『待补充』『无』『未识别』这类空壳占位；\n"
    "   ## 背景\n   ## 功能需求\n   ## 非功能需求 / 约束\n   ## 决策记录\n   ## 待确认问题\n"
    "2. 每节用『- 』列表，逐条从讨论里提炼，用用户原本的意思；AI 的附和/寒暄不算需求。\n"
    "3. 若这段对话是纯寒暄、没有实质需求，则只输出一句『本次为寒暄/非需求性对话，未提炼到明确需求』，不要堆小节。\n"
    "4. 直接输出 markdown 正文，不要代码围栏，不要额外解说，尽量简短。"
)

def _llm_extract(discussion: list, title: str = "") -> str:
    """用 LLM 从讨论里提炼结构化需求；失败返回空串（触发关键词兜底）"""
    lines = []
    for d in discussion:
        t = d.get("text", "").strip()
        ts = d.get("ts", "")
        who = d.get("role", "")
        prefix = ("[用户] " if who == "user" else ("[AI] " if who == "ai" else ""))
        lines.append(f"{prefix}{ts} {t}".strip())
    transcript = "\n".join(lines)
    if not transcript.strip():
        return ""
    msgs = [{"role": "system", "content": _DRAFT_LLM_PROMPT},
            {"role": "user", "content": f"讨论标题：{title}\n\n讨论内容：\n{transcript}"}]
    body = json.dumps({"model": GLM_MODEL, "messages": msgs,
                       "max_tokens": 1200, "temperature": 0.3}).encode()
    try:
        req = urllib.request.Request(GLM_URL, data=body, method="POST",
            headers={"Authorization": "Bearer " + _GLM_KEY,
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
        out = d["choices"][0]["message"]["content"].strip()
        return _strip_markers(out) if out else ""
    except Exception as e:
        print(f"[cldvoice] LLM 提炼失败(走关键词兜底): {str(e)[:120]}")
        return ""

DRAFT_DIR = os.path.expanduser("~/dsh-collab/cld-voice/drafts")
UI_DIR = os.path.expanduser("~/dsh-collab/cld-voice/app/ui")
os.makedirs(DRAFT_DIR, exist_ok=True)

def parse_segments(discussion: list) -> dict:
    """讨论段落 → 分类（需求/约束/疑问/决策/其他）"""
    cats = {"requirement": [], "constraint": [], "question": [], "decision": [], "other": []}
    requirement_kw = ["要", "需要", "支持", "能", "应该", "必须", "实现", "提供", "增加", "做"]
    constraint_kw = ["只要", "优先", "不要", "不能", "限制", "移动端", "web", "简单", "最小", "先"]
    question_kw = ["?", "吗", "什么", "怎样", "如何", "行不行"]
    decision_kw = ["就", "定了", "决定", "选", "采用", "用", "方案"]
    for seg in discussion:
        text = seg.get("text", "").strip()
        if not text:
            continue
        ts = seg.get("ts", "")
        if any(k in text for k in question_kw):
            cats["question"].append({"ts": ts, "text": text})
        elif any(k in text for k in constraint_kw) and len(text) < 30:
            cats["constraint"].append({"ts": ts, "text": text})
        elif any(k in text for k in requirement_kw):
            cats["requirement"].append({"ts": ts, "text": text})
        elif any(k in text for k in decision_kw) and len(text) < 25:
            cats["decision"].append({"ts": ts, "text": text})
        else:
            cats["other"].append({"ts": ts, "text": text})
    return cats

def dedupe(items):
    """去重（按文本相似）"""
    seen = []
    for it in items:
        t = it["text"]
        if not any(t[:15] in s or s[:15] in t for s in seen):
            seen.append(t)
    return [{"text": t} for t in seen]

def _keyword_draft(discussion: list, title: str, ts: str) -> dict:
    """关键词兜底：讨论缓冲 → markdown 需求文件（无 LLM 时用）"""
    cats = parse_segments(discussion)
    reqs = dedupe(cats["requirement"])
    cons = dedupe(cats["constraint"])
    decs = dedupe(cats["decision"])
    qs = dedupe(cats["question"])
    others = dedupe(cats["other"])

    md = [f"# {title}", "", "> 由 CLD-Voice 语音讨论自动整理 · " + datetime.datetime.now().isoformat(timespec="seconds"), ""]
    md += ["## 背景", "(讨论自动生成，待补充)", "", "## 功能需求"]
    for r in reqs or [{"text": "(未识别到明确需求，待补充)"}]:
        md.append(f"- {r['text']}")
    md += ["", "## 非功能需求 / 约束"]
    for c in cons or [{"text": "(无明确约束)"}]:
        md.append(f"- {c['text']}")
    md += ["", "## 决策记录"]
    for c in decs or [{"text": "(无明确决策)"}]:
        md.append(f"- {c['text']}")
    md += ["", "## 待确认问题"]
    for q in qs:
        md.append(f"- [ ] {q['text']}")
    if others:
        md += ["", "## 其他讨论"]
        for o in others[:5]:
            md.append(f"- {o['text']}")
    md += ["", "## 讨论留痕"]
    md.append("| 时间 | 内容 |")
    md.append("|------|------|")
    for seg in discussion[-15:]:
        md.append(f"| {seg.get('ts','')} | {seg['text'][:60]} |")
    content = "\n".join(md)
    return {"_content": content, "requirements": len(reqs), "constraints": len(cons),
            "decisions": len(decs), "questions": len(qs), "source": "keyword"}


def _append_trace(content: str, discussion: list) -> str:
    """给 LLM 成稿附加讨论留痕表（保留原始记录，便于回溯）"""
    rows = ["", "", "## 讨论留痕", "| 时间 | 角色 | 内容 |", "|------|------|------|"]
    for seg in discussion[-15:]:
        role = {"user": "用户", "ai": "AI"}.get(seg.get("role", ""), "—")
        rows.append(f"| {seg.get('ts','')} | {role} | {seg['text'][:60]} |")
    return content + "\n".join(rows)


def generate_draft(discussion: list, title="") -> dict:
    """讨论缓冲 → markdown 需求文件. 优先 LLM 主动提炼, 失败走关键词兜底"""
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    title = title or f"语音需求-{ts}"
    header = [f"# {title}", "", "> 由 CLD-Voice 语音讨论自动整理 · " + datetime.datetime.now().isoformat(timespec="seconds"), ""]

    llm_content = ""
    if _GLM_KEY:
        llm = _llm_extract(discussion, title)
        if llm.strip():
            llm_content = llm.strip()
            if not llm_content.startswith("#"):
                llm_content = "\n".join(header) + llm_content
            # 注: 注入给 CLD 的 content 只保留"提炼总结", 不附加原始"讨论留痕"逐字表
            llm_content = llm_content.strip()

    if llm_content:
        content = llm_content
        stats = {"source": "llm"}
    else:
        kd = _keyword_draft(discussion, title, ts)
        content = kd["_content"]
        stats = {"source": "keyword", "requirements": kd["requirements"],
                 "constraints": kd["constraints"], "decisions": kd["decisions"],
                 "questions": kd["questions"]}

    # 落盘的 .md 文件带完整"讨论留痕"(可回溯), 但注入 CLD 的 content 只含提炼总结(见 content)
    fname = f"{ts}.md"
    fpath = os.path.join(DRAFT_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content + "\n\n---\n" + _append_trace("", discussion))

    return {"id": ts, "title": title, "file": fpath, "content": content, "stats": stats}


def insert_to_context(draft: dict) -> dict:
    """成稿 → 插入 CLD 上下文（写黑板，供本会话或其他端读取）"""
    try:
        token = os.environ.get("BLACKBOARD_TOKEN", "")
        key = f"notes/collab/cld-voice-draft-{draft['id']}"
        body = json.dumps({"from": "cld-voice-mvp", "subject": f"语音需求成稿 {draft['title']}",
                           "body": draft["content"], "ts": int(time.time()*1000)}).encode()
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:8792/" + key, data=body, method="PUT")
        if token:
            req.add_header("X-Blackboard-Token", token)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=8) as resp:
            r = json.loads(resp.read().decode())
        return {"ok": True, "key": key, "resp": r}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ───────── HTTP 服务 ─────────
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass  # 静默

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length else b""

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/health":
            return self._json(200, {"status": "ok", "model": WHISPER_MODEL, "drafts": len(os.listdir(DRAFT_DIR))})
        if self.path.startswith("/api/drafts"):
            files = sorted(os.listdir(DRAFT_DIR), reverse=True)[:20]
            return self._json(200, {"drafts": files})
        # UI 静态服务
        if self.path in ("/", "/index.html", "/ui"):
            return self._serve_ui("index.html")
        if self.path.startswith("/ui/"):
            fname = self.path.split("/ui/")[-1]
            return self._serve_ui(fname)
        return self._json(404, {"error": "not found"})

    def _serve_ui(self, fname):
        import mimetypes
        fpath = os.path.join(UI_DIR, os.path.basename(fname))
        if not os.path.exists(fpath):
            return self._json(404, {"error": "ui not found"})
        body = open(fpath, "rb").read()
        ctype = mimetypes.guess_type(fpath)[0] or "text/html"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            if self.path == "/api/asr":
                # multipart 音频
                ct = self.headers.get("Content-Type", "")
                raw = self._read_body()
                wav_bytes = None
                m = re.search(r'boundary=(.+)', ct)
                if m and b"audio" in raw:
                    boundary = m.group(1).strip().encode()
                    parts = raw.split(b"--" + boundary)
                    for p in parts:
                        if b'name="audio"' in p and b"\r\n\r\n" in p:
                            wav_bytes = p.split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n", 1)[0]
                            break
                if not wav_bytes:
                    wav_bytes = raw  # 裸音频兜底
                result = transcribe_wav(wav_bytes)
                return self._json(200, {"success": True, **result})

            if self.path == "/api/reply":
                data = json.loads(self._read_body().decode())
                return self._json(200, {"success": True, **glm_reply(data.get("discussion", []))})

            if self.path == "/api/draft":
                data = json.loads(self._read_body().decode())
                draft = generate_draft(data.get("discussion", []), data.get("title", ""))
                if data.get("insert"):
                    draft["insert"] = insert_to_context(draft)
                return self._json(200, {"success": True, **draft})

            if self.path == "/api/draft/insert":
                data = json.loads(self._read_body().decode())
                draft = json.load(open(os.path.join(DRAFT_DIR, data["id"] + ".md"))) if False else \
                    {"id": data["id"], "title": data.get("title", ""), "content": open(os.path.join(DRAFT_DIR, data["id"] + ".md")).read()}
                return self._json(200, {"success": True, **insert_to_context(draft)})

            return self._json(404, {"error": "not found"})
        except Exception as e:
            return self._json(500, {"error": str(e)})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8902)
    args = ap.parse_args()
    # 启动火山流式桥（ws://127.0.0.1:8903/stream）
    try:
        from stream_bridge import start_bridge
        start_bridge()
    except Exception as e:
        print("stream bridge start failed:", e)
    # 启动端到端全双工桥（ws://127.0.0.1:8904/dialogue）
    try:
        from duplex_bridge import start_bridge as start_duplex
        start_duplex()
    except Exception as e:
        print("duplex bridge start failed:", e)
    # 预热模型（后台）
    threading.Thread(target=lambda: (get_model(), print("whisper 模型已加载")), daemon=True).start()
    with socketserver.ThreadingTCPServer(("127.0.0.1", args.port), Handler) as httpd:
        print(f"CLD-Voice MVP backend on :{args.port}")
        httpd.serve_forever()

if __name__ == "__main__":
    main()
