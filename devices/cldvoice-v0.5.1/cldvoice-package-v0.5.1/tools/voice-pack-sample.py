#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为每个语音包生成试听样本 WAV（供人工听感确认/挑选）。

用法: voice-pack-sample.py [输出目录] [输入wav]
对每个包反复重试(默认≤3次)直到拿到音频, 写入 <out>/pack-<id>.wav (24k 单声道 s16le)
"""
import base64, json, os, struct, sys, threading, time
import websocket as ws_client

PACKS = ["zh", "yue", "sichuan", "dongbei", "shaanxi", "yue_taozi"]


def wav_to_pcm(path):
    d = open(path, "rb").read()
    i, rate = 12, 16000
    while i + 8 <= len(d):
        cid, sz = d[i:i+4], struct.unpack("<I", d[i+4:i+8])[0]
        if cid == b"fmt ":
            _, ch, rate, _, bits = struct.unpack("<HHIIH", d[i+8:i+22])
        elif cid == b"data":
            return d[i+8:i+8+sz], rate
        i += 8 + sz + (sz & 1)
    raise RuntimeError("无 data chunk")


def pcm_to_wav(pcm, rate, path):
    n = len(pcm)
    hdr = (b"RIFF" + struct.pack("<I", 36 + n) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
           + b"data" + struct.pack("<I", n))
    with open(path, "wb") as f:
        f.write(hdr + pcm)


def one_round(pcm, rate, pack, port=8905, wait=22):
    url = f"ws://127.0.0.1:{port}/?pack={pack}"
    ws = ws_client.create_connection(url, timeout=25)
    audio, text, stop = bytearray(), "", False

    def drain():
        nonlocal text
        while not stop:
            try:
                d = ws.recv()
            except Exception:
                return
            if isinstance(d, bytes):
                d = d.decode("utf-8", "ignore")
            s = d
            while s.strip():
                try:
                    o, end = json.JSONDecoder().raw_decode(s)
                except Exception:
                    break
                t = o.get("type", "")
                if t == "audio_delta":
                    try:
                        audio.extend(base64.b64decode(o.get("audio", "") or ""))
                    except Exception:
                        pass
                elif t == "text_delta":
                    text += o.get("delta", "") or ""
                s = s[end:].lstrip()

    threading.Thread(target=drain, daemon=True).start()
    time.sleep(0.8)

    step = int(rate * 0.02) * 2
    for i in range(0, len(pcm), step):
        ws.send(pcm[i:i + step], opcode=ws_client.ABNF.OPCODE_BINARY)
        time.sleep(0.02)
    ws.send(json.dumps({"type": "commit"}))
    sil = b"\x00\x00" * int(rate * 0.2)
    t0 = time.time()
    while time.time() - t0 < wait:
        try:
            ws.send(sil, opcode=ws_client.ABNF.OPCODE_BINARY)
        except Exception:
            break
        time.sleep(0.2)
    stop = True
    try:
        ws.close()
    except Exception:
        pass
    return bytes(audio), text


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/cldvoice-samples"
    src = sys.argv[2] if len(sys.argv) > 2 else "/tmp/test-cn.wav"
    os.makedirs(out, exist_ok=True)
    pcm, rate = wav_to_pcm(src)
    print(f"输入: {src} ({len(pcm)}B @{rate}Hz) → 输出目录 {out}\n")

    for p in PACKS:
        ok = False
        for attempt in range(3):
            audio, text = one_round(pcm, rate, p)
            if audio:
                path = os.path.join(out, f"pack-{p}.wav")
                pcm_to_wav(audio, 24000, path)
                print(f"  ✅ {p:<9} 第{attempt+1}次 音频={len(audio)//1024}KB → {os.path.basename(path)}")
                print(f"     回复: {text[:90]}")
                ok = True
                break
            print(f"  … {p:<9} 第{attempt+1}次 无音频(已知偶发), 重试")
        if not ok:
            print(f"  ❌ {p:<9} 3 次均无音频; 最后文字: {text[:80]}")
    print(f"\n完成。试听: open {out}")
