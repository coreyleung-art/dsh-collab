#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLD-Voice 流式桥 — GUI(ws://127.0.0.1:8903) → 火山 wss://openspeech.bytedance.com/api/v3/sauc/bigmodel
浏览器 WebSocket 无法自定义 X-Api-Key 头 → 桥承担鉴权与双向泵。

协议（GUI ↔ 本桥, ws://127.0.0.1:8903/stream）：
  GUI → 桥: 二进制帧 = Int16 LE PCM 16k（~200ms 每包）
  GUI → 桥: JSON 文本 '{"end":true}' 表示说完（发负包结束）
  桥 → GUI: JSON '{"type":"partial","text":"...","definite":bool}'
  桥 → GUI: JSON '{"type":"err","msg":"..."}'

本桥 → 火山: 二进制协议 [4B header][4B plen][payload]
  火山鉴权头: X-Api-Key / X-Api-Resource-Id: volc.seedasr.sauc.duration
"""
import asyncio, json, os, struct, threading, time, uuid
import websockets as ws_server
import websocket as ws_client

def _load_key():
    """从 env → ~/.dsh/.credentials.yaml → ~/.dsh/.env 读 key。

    兼容两种凭证文件写法（跨设备部署实测必需）：
      1) 扁平:  VOLC_ASR_API_KEY: xxx
      2) 嵌套:  refs:\n  VOLC_ASR_API_KEY: xxx     ← 部分 DSH 安装默认此格式
    以及 .env 的 KEY=value 形式。故必须先 strip 再匹配，否则缩进键永远匹配不到。
    """
    v = os.environ.get("VOLC_ASR_API_KEY", "").strip()
    if v:
        return v
    for p in (os.path.expanduser("~/.dsh/.credentials.yaml"),
              os.path.expanduser("~/.dsh/.env")):
        try:
            for line in open(p, encoding="utf-8", errors="ignore"):
                line = line.strip()          # ← 关键：剥掉 refs: 的缩进
                if line.startswith("VOLC_ASR_API_KEY"):
                    v = line.split("=", 1)[-1].split(":", 1)[-1].strip().strip('"').strip("'")
                    if v:
                        return v
        except Exception:
            pass
    return ""


_GLM_KEY = _load_key()

VOLC_WS = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
VOLC_RESOURCE = os.environ.get("VOLC_ASR_RESOURCE", "volc.seedasr.sauc.duration")
BRIDGE_PORT = 8903

# ── 火山二进制帧构建 ──
def volc_frame(msg_type, payload=b"", flags=0x0):
    """msg_type: 0x1=full client request(JSON), 0x2=audio; flags 0x2=负包结束"""
    b0 = 0x11                                   # ver=1, header=4B
    b1 = (msg_type << 4) | flags
    ser = 0x10 if msg_type == 0x1 else 0x00     # full request JSON, 音频 raw
    return bytes([b0, b1, ser, 0x00]) + struct.pack(">I", len(payload)) + payload

def full_client_json():
    return json.dumps({
        "user": {"uid": "cldvoice", "device_id": "mbp"},
        "audio": {"format": "pcm", "rate": 16000, "bits": 16, "channel": 1},
        "request": {"model_name": "bigmodel", "enable_itn": True,
                    "enable_punc": True, "enable_ddc": False,
                    "result_type": "single"},
    }, ensure_ascii=False).encode()

# ── 解析火山服务端响应（鲁棒：定位 JSON 对象） ──
def parse_server(buf: bytes):
    """从累积 buffer 提取 (json_obj_list, rest_buffer)"""
    objs = []
    dec = json.JSONDecoder()
    s = buf.decode("utf-8", "ignore")
    while True:
        start = s.find("{")
        if start < 0:
            return objs, b""
        try:
            obj, end = dec.raw_decode(s[start:])
        except Exception:
            return objs, buf  # 不完整，等更多
        objs.append(obj)
        s = s[start + end:]
        if not s.strip():
            return objs, b""

# ── 单个 GUI 会话泵 ──
async def pump(gui_ws):
    """GUI ws ↔ 火山 wss 双向转发"""
    if not _GLM_KEY:
        await gui_ws.send(json.dumps({"type": "err", "msg": "未配置 VOLC_ASR_API_KEY"}))
        return
    try:
        volc = ws_client.create_connection(
            VOLC_WS,
            header={"X-Api-Key": _GLM_KEY,
                    "X-Api-Resource-Id": VOLC_RESOURCE,
                    "X-Api-Connect-Id": str(uuid.uuid4())},
            timeout=15)
    except Exception as e:
        await gui_ws.send(json.dumps({"type": "err", "msg": f"火山连接失败: {str(e)[:100]}"}))
        return

    volc.send_binary(volc_frame(0x1, full_client_json()))
    blog("volc connected + full-client sent")
    volc_buf = b""
    ended = False
    loop = asyncio.get_running_loop()
    pcm_pkts = 0

    def _drain_volc():
        """读火山（阻塞，跑在线程）→ 解析 → 塞回 asyncio 队列"""
        nonlocal volc_buf
        try:
            while True:
                data = volc.recv()
                if isinstance(data, str):
                    data = data.encode()
                volc_buf += data
                objs, volc_buf = parse_server(volc_buf)
                for o in objs:
                    res = o.get("result", {})
                    blog(f"volc->gui text={res.get('text','')[:60]!r} def={res.get('definite')}")
                    loop.call_soon_threadsafe(_push_result, o)
        except Exception as e:
            blog(f"volc drain end: {str(e)[:80]}")

    def _push_result(o):
        res = o.get("result", {})
        txt = res.get("text", "")
        if txt:
            fut = asyncio.ensure_future(gui_ws.send(
                json.dumps({"type": "partial", "text": txt,
                            "definite": res.get("definite")}, ensure_ascii=False)))

    threading.Thread(target=_drain_volc, daemon=True).start()
    await gui_ws.send(json.dumps({"type": "ready"}, ensure_ascii=False))
    try:
        async for msg in gui_ws:
            if isinstance(msg, bytes):
                pcm_pkts += 1
                if pcm_pkts in (1, 20, 50, 100):
                    blog(f"gui pcm pkt#{pcm_pkts} len={len(msg)}")
                volc.send_binary(volc_frame(0x2, msg))      # PCM 包
            elif isinstance(msg, str):
                try:
                    d = json.loads(msg)
                    if d.get("end"):
                        blog(f"gui end signal after {pcm_pkts} pkts")
                        volc.send_binary(volc_frame(0x2, b"", flags=0x2))  # 负包结束
                        ended = True
                        break
                except Exception:
                    pass
    finally:
        try:
            if not ended:
                volc.send_binary(volc_frame(0x2, b"", flags=0x2))
        except Exception:
            pass
        try:
            volc.close()
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
    """在独立线程启动本地 WS 桥 :8903（asyncio）"""
    def run():
        async def serve():
            async with ws_server.serve(_ws_handler, "127.0.0.1", port, max_size=2**20):
                print(f"CLD-Voice stream bridge on ws://127.0.0.1:{port}/stream")
                await asyncio.Future()
        asyncio.run(serve())
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t

if __name__ == "__main__":
    start_bridge()
    print("bridge started; keep-alive 60s")
    time.sleep(60)

# 简易日志（供诊断）
_BRIDGE_LOG = os.path.expanduser("~/dsh-collab/logs/cld-voice-bridge.log")
def blog(msg):
    try:
        with open(_BRIDGE_LOG, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass
