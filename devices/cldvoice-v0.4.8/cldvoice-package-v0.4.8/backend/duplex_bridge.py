#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLD-Voice 端到端全双工桥 — GUI(ws://127.0.0.1:8904) → 火山 Seeduplex 全双工 wss
浏览器无法自定义 X-Api-Key 头 → 本桥承担鉴权 + 音频/文本双向泵。

桥 → GUI 事件（JSON 文本帧）:
  {"type":"ready","sid":...}
  {"type":"text_delta","delta":"..."}        模型回答文本逐字
  {"type":"text_done","text":"..."}          文本完成
  {"type":"audio_delta","audio":"<b64>"}     模型语音 24k PCM s16le 分片
  {"type":"audio_done"}
  {"type":"transcript_delta","delta":"..."}  你说的内容转写（回声上屏）
  {"type":"done","reason":"..."}
  {"type":"err","msg":"..."}
  {"type":"closed"}

GUI → 桥:
  二进制帧: 你麦克风 16k PCM s16le 包
  {"type":"commit"}        强制端点判定（你说完）
  {"type":"cancel"}        打断模型回复（response.cancel）
  {"type":"close"}         结束会话
"""
import asyncio, base64, json, os, threading, time, uuid
import websockets as ws_server
import websocket as ws_client

def _load_key():
    v = os.environ.get("VOLC_ASR_API_KEY", "").strip()
    if v:
        return v
    try:
        for line in open(os.path.expanduser("~/.dsh/.credentials.yaml"), encoding="utf-8"):
            line = line.strip()
            if line.startswith("VOLC_ASR_API_KEY"):
                return line.split(":", 1)[-1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""

_KEY = _load_key()
VOLC_WS = "wss://openspeech.bytedance.com/api/v3/duplex/realtime/dialogue"
MODEL = os.environ.get("SEEDUPLEX_MODEL", "1.2.6.0")
VOICE = os.environ.get("SEEDUPLEX_VOICE", "zh_female_cancan_mars_bigtts")
BRIDGE_PORT = 8904

_LOG = os.path.expanduser("~/dsh-collab/logs/cld-voice-duplex.log")
def blog(msg):
    try:
        with open(_LOG, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass

INSTRUCTIONS = ("你是 CLD-Voice 的语音需求协作伙伴，用户正用语音描述需求。"
    "你必须**用语音开口回答**，每轮都要说话，不要让用户只看到文字。"
    "规则：1) 简短确认听懂核心点；2) 最多追问一个最关键不明确处；3) 每轮≤60字，口语化像真人，不列清单；"
    "4) 用户可随时打断，打断后接着新内容走；5) 对话多轮，最终目标是帮用户把需求聊清楚。")


async def pump(gui_ws):
    if not _KEY:
        await gui_ws.send(json.dumps({"type": "err", "msg": "未配置 VOLC_ASR_API_KEY"}))
        return
    volc = None
    try:
        volc = ws_client.create_connection(VOLC_WS, header={"X-Api-Key": _KEY}, timeout=20)
    except Exception as e:
        await gui_ws.send(json.dumps({"type": "err", "msg": f"Seeduplex 连接失败: {str(e)[:100]}"}))
        return

    def vsend(o):
        volc.send(json.dumps(o, ensure_ascii=False))

    vsend({"type": "session.create", "session": {
        "model": MODEL,
        "audio": {
            "input": {"format": {"type": "pcm", "rate": 16000}},
            "output": {"format": {"type": "pcm_s16le", "rate": 24000}, "voice": VOICE}
        },
        "instructions": INSTRUCTIONS,
    }})
    blog("session.create sent")
    sid = None
    volc_buf = b""
    loop = asyncio.get_running_loop()

    # 静音尾包：commit 后持续发，帮 VAD 判定说完（模型才会开口）
    silence = (b"\x00\x00" * 1600)  # 200ms @16k
    silence_on = False
    _last_trans = ""   # 转录去重(LCP)：记录「已发给 GUI 的累积文本」，只发真正新增尾部
    _run_audio_bytes = 0   # 本次 response 累计收到的 TTS 音频字节(诊断用)
    _resp_had_audio = False  # 本次 response 是否确有音频(done 时判, 防 audio_done 提前清零误触发兜底)
    _ai_text = ""        # 本次 response 累积的 AI 文本(用于 audio=0 时兜底 TTS)

    def _silence_loop():
        nonlocal silence_on
        try:
            while silence_on:
                vsend({"type": "input_audio_buffer.append", "audio": base64.b64encode(silence).decode()})
                time.sleep(0.2)
        except Exception:
            pass

    def _drain():
        """读火山响应（阻塞线程）→ asyncio 转发 GUI"""
        nonlocal volc_buf, sid
        try:
            while True:
                data = volc.recv()
                if isinstance(data, str):
                    data = data.encode()
                volc_buf += data
                # Seeduplex 是文本 JSON 帧（非二进制协议），直接按行/完整 json 尝试
                dec = data.decode("utf-8", "ignore")
                s = dec
                while s.strip():
                    try:
                        obj, end = json.JSONDecoder().raw_decode(s)
                    except Exception:
                        break
                    loop.call_soon_threadsafe(_push, obj)
                    s = s[end:].lstrip()
                    if not s:
                        break
                volc_buf = b""
        except ws_client.WebSocketConnectionClosedException as e:
            blog(f"VOLC-CLOSED: {getattr(e,'status_code','?')} {getattr(e,'reason','')[:80]}")
        except ws_client.WebSocketBadStatusException as e:
            blog(f"VOLC-BADSTATUS: {e.status_code} {str(e)[:120]}")
        except Exception as e:
            blog(f"drain end: {str(e)[:100]}")

    def _push(o):
        nonlocal sid, _last_trans, _run_audio_bytes, _resp_had_audio, _ai_text
        tp = o.get("type", "")
        try:
            if tp == "session.created":
                sid = o.get("session", {}).get("id")
                blog(f"session.created sid={sid}")
                asyncio.ensure_future(gui_ws.send(json.dumps({"type": "ready", "sid": sid})))
            elif tp == "response.output_text.delta":
                _ai_text += o.get("delta", "") or ""
                asyncio.ensure_future(gui_ws.send(json.dumps({"type": "text_delta", "delta": o.get("delta", "")}, ensure_ascii=False)))
            elif tp == "response.output_text.done":
                _ai_text = o.get("text", "") or _ai_text
                asyncio.ensure_future(gui_ws.send(json.dumps({"type": "text_done", "text": o.get("text", "")}, ensure_ascii=False)))
            elif tp == "response.output_audio.delta":
                _run_audio_bytes += len(o.get("delta", "") or "")
                _resp_had_audio = True
                asyncio.ensure_future(gui_ws.send(json.dumps({"type": "audio_delta", "audio": o.get("delta", "")})))
            elif tp == "response.output_audio.done":
                blog(f"audio_done, this-response audio bytes={_run_audio_bytes}")
                asyncio.ensure_future(gui_ws.send(json.dumps({"type": "audio_done"})))
            elif tp.endswith("input_audio_transcription.delta"):
                full = o.get("delta", "") or ""
                # 转录去重（LCP）：火山 duplex 的 delta 是"累积全文"，且可能回退/改写整段。
                # 取「已发给 GUI 的文本」与本次 full 的最长公共前缀，只发前缀之后真正新增的尾部，
                # 避免 full 不以 _last_trans 开头时把整段重发导致 "来聊一下吧。" 重复两次。
                lcp = 0
                _lt = _last_trans
                _lim = min(len(full), len(_lt))
                while lcp < _lim and full[lcp] == _lt[lcp]:
                    lcp += 1
                newpart = full[lcp:] if lcp < len(full) else ""
                _last_trans = full
                if newpart:
                    asyncio.ensure_future(gui_ws.send(json.dumps({"type": "transcript_delta", "delta": newpart}, ensure_ascii=False)))
            elif tp == "response.done":
                # 本轮结束：停静音(允许下一轮重新说话)，通知 GUI 可继续
                silence_on = False
                # 兜底 TTS: 若模型这轮只回文字(0字节音频), 用 speech_text_buffer.commit 强制合成语音
                if (not _resp_had_audio) and (_ai_text or "").strip():
                    fallback_txt = _ai_text.strip()
                    blog(f"TTS fallback (no-audio) -> synthesize '{fallback_txt[:30]}'")
                    vsend({"type": "speech_text_buffer.commit", "text": fallback_txt})
                _ai_text = ""
                _run_audio_bytes = 0
                _resp_had_audio = False
                blog("response.done — silence off, round complete")
                asyncio.ensure_future(gui_ws.send(json.dumps({"type": "done"})))
            elif "error" in tp.lower():
                asyncio.ensure_future(gui_ws.send(json.dumps({"type": "err", "msg": json.dumps(o, ensure_ascii=False)[:200]})))
        except Exception:
            pass

    threading.Thread(target=_drain, daemon=True).start()

    try:
        async for msg in gui_ws:
            if isinstance(msg, bytes):
                vsend({"type": "input_audio_buffer.append", "audio": base64.b64encode(msg).decode()})
            elif isinstance(msg, str):
                try:
                    d = json.loads(msg)
                    t = d.get("type")
                    if t == "commit":
                        _last_trans = ""   # 新一轮，重置转录累积基线
                        vsend({"type": "input_audio_buffer.commit"})
                        if not silence_on:
                            silence_on = True
                            threading.Thread(target=_silence_loop, daemon=True).start()
                        blog("commit sent, silence on")
                    elif t == "cancel":
                        vsend({"type": "response.cancel"})
                        blog("cancel sent")
                    elif t == "close":
                        break
                except Exception:
                    pass
    finally:
        silence_on = False
        try:
            vsend({"type": "session.close"})
        except Exception:
            pass
        try:
            volc.close()
        except Exception:
            pass
        try:
            await gui_ws.send(json.dumps({"type": "closed"}))
        except Exception:
            pass


async def _ws_handler(websocket, path=None):
    try:
        await pump(websocket)
    except Exception as e:
        try:
            await websocket.send(json.dumps({"type": "err", "msg": str(e)[:100]}))
        except Exception:
            pass


def start_bridge(port=BRIDGE_PORT):
    def run():
        async def serve():
            async with ws_server.serve(_ws_handler, "127.0.0.1", port, max_size=2**20):
                print(f"CLD-Voice duplex bridge on ws://127.0.0.1:{port}/dialogue")
                await asyncio.Future()
        asyncio.run(serve())
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    start_bridge()
    print("duplex bridge keep-alive")
    time.sleep(120)
