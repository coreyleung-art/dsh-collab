#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""走 8905 网关测语音包：验证 ?pack= 真正生效（端到端，非直连火山）。

用法: voice-pack-e2e.py <wav> <pack> [ws端口]
"""
import base64, json, os, struct, sys, threading, time
import websocket as ws_client

YUE = ["係", "唔", "嘅", "咗", "喺", "冇", "啲", "佢", "咁", "乜", "嘢", "睇", "邊", "咩", "𠮶", "定系", "點"]
CN = ["是", "不", "的", "了", "在", "没", "这", "那", "什么", "怎么", "可以", "我们", "需要", "一个"]


def wav_to_pcm(path):
    d = open(path, "rb").read()
    assert d[:4] == b"RIFF" and d[8:12] == b"WAVE", "不是 wav"
    i = 12
    while i + 8 <= len(d):
        cid, sz = d[i:i+4], struct.unpack("<I", d[i+4:i+8])[0]
        if cid == b"fmt ":
            _, ch, rate, _, bits = struct.unpack("<HHIIH", d[i+8:i+22])
            return_rate = rate
        elif cid == b"data":
            return d[i+8:i+8+sz], return_rate
        i += 8 + sz + (sz & 1)
    raise RuntimeError("无 data chunk")


def run(wav, pack, port=8905, wait=24):
    pcm, rate = wav_to_pcm(wav)
    url = f"ws://127.0.0.1:{port}/?pack={pack}"
    print(f"\n{'='*72}\n[网关端到端] WS={url}")
    print(f"  输入={os.path.basename(wav)} ({len(pcm)}B @{rate}Hz)")

    ws = ws_client.create_connection(url, timeout=25)
    events, stop = [], False

    def drain():
        while not stop:
            try:
                d = ws.recv()
            except Exception as e:
                events.append({"type": "__closed__", "err": str(e)[:120]})
                return
            if isinstance(d, bytes):
                d = d.decode("utf-8", "ignore")
            s = d
            while s.strip():
                try:
                    obj, end = json.JSONDecoder().raw_decode(s)
                except Exception:
                    break
                events.append(obj)
                s = s[end:].lstrip()

    threading.Thread(target=drain, daemon=True).start()
    time.sleep(0.8)

    def send(o):
        ws.send(json.dumps(o, ensure_ascii=False))

    step = int(rate * 0.02) * 2
    # 注意: 网关 pump 只认**二进制帧**(原始 PCM); JSON 只用于 commit/cancel/close
    for i in range(0, len(pcm), step):
        ws.send(pcm[i:i+step], opcode=ws_client.ABNF.OPCODE_BINARY)
        time.sleep(0.02)
    send({"type": "commit"})

    silence = b"\x00\x00" * int(rate * 0.2)
    t0 = time.time()
    while time.time() - t0 < wait:
        try:
            ws.send(silence, opcode=ws_client.ABNF.OPCODE_BINARY)
        except Exception:
            break
        time.sleep(0.2)
    stop = True
    try:
        ws.close()
    except Exception:
        pass

    types, text, audio, errs, pack_ack, trans = {}, "", 0, [], None, ""
    for o in events:
        t = o.get("type", "?")
        types[t] = types.get(t, 0) + 1
        if t == "pack":
            pack_ack = o
        elif t == "text_delta":
            text += o.get("delta", "") or ""
        elif t == "text_done":
            text = o.get("text", "") or text
        elif t == "audio_delta":
            audio += len(o.get("audio", "") or "")
        elif t.startswith("transcript_delta"):
            trans += o.get("delta", "") or ""
        elif "error" in t.lower() or t == "err":
            errs.append(json.dumps(o, ensure_ascii=False)[:180])

    print(f"  服务端回告 pack: {pack_ack}")
    print(f"  你说的(转写): {trans[:100] or '(无)'}")
    print(f"  模型回复: {text[:180] or '(无文字)'}")
    print(f"  音频长度: {audio}  {'✅ 出声' if audio > 0 else '❌ 没出声'}")
    if errs:
        print(f"  ⚠️ 错误: {errs[:2]}")
    if text:
        cm = [c for c in YUE if c in text]
        mm = [c for c in CN if c in text]
        print(f"  粤语特征: {cm or '无'} | 国语特征: {mm or '无'}")
        print(f"  ➜ 判定: 【{'粤语' if len(cm) > len(mm) else ('国语' if mm else '不明')}】")
    return {"pack": pack_ack, "text": text, "audio": audio}


if __name__ == "__main__":
    wav, pack = sys.argv[1], sys.argv[2]
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 8905
    run(wav, pack, port)
