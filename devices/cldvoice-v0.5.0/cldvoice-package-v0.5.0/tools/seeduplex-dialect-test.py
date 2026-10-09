#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seeduplex 受控实验：喂入语音 → 看模型回复的方言。

用法:
  seeduplex-dialect-test.py <wav文件> <指令档位> <音色>
指令档位: base(现用) | yue(强制粤语) | sichuan(强制四川话)

判定依据：回复文字的粤语/国语特征字计数 + 音频字节数（>0 表示确实开口了）。
"""
import base64, json, os, struct, sys, threading, time
import websocket as ws_client

URL = "wss://openspeech.bytedance.com/api/v3/duplex/realtime/dialogue"
MODEL = "1.2.6.0"

YUE = ["係", "唔", "嘅", "咗", "喺", "冇", "啲", "佢", "咁", "乜", "嘢", "睇", "畀", "嗰", "啱", "搵", "邊", "點解", "唔該", "多谢", "而家"]
CN = ["是", "不", "的", "了", "在", "没", "这", "那", "什么", "怎么", "可以", "我们", "需要", "一个", "我想"]


def load_key():
    v = os.environ.get("VOLC_ASR_API_KEY", "").strip()
    if v:
        return v
    for line in open(os.path.expanduser("~/.dsh/.credentials.yaml"), encoding="utf-8", errors="ignore"):
        s = line.strip()
        if s.startswith("VOLC_ASR_API_KEY"):
            return s.split(":", 1)[-1].strip().strip('"').strip("'")
    return ""


def wav_to_pcm(path):
    """极简 wav 解析：找 data chunk，返回 (pcm_bytes, rate, channels)"""
    d = open(path, "rb").read()
    assert d[:4] == b"RIFF" and d[8:12] == b"WAVE", "不是 wav"
    i, rate, ch, bits = 12, 16000, 1, 16
    while i + 8 <= len(d):
        cid, sz = d[i:i+4], struct.unpack("<I", d[i+4:i+8])[0]
        if cid == b"fmt ":
            _, ch, rate, _, bits = struct.unpack("<HHIIH", d[i+8:i+22])
        elif cid == b"data":
            return d[i+8:i+8+sz], rate, ch
        i += 8 + sz + (sz & 1)
    raise RuntimeError("无 data chunk")


BASE = ("你是 CLD-Voice 的语音需求协作伙伴，用户正用语音描述需求。"
        "你必须**用语音开口回答**，每轮都要说话，不要让用户只看到文字。"
        "规则：1) 简短确认听懂核心点；2) 最多追问一个最关键不明确处；3) 每轮≤60字，口语化像真人，不列清单；"
        "4) 用户可随时打断，打断后接着新内容走；5) 对话多轮，最终目标是帮用户把需求聊清楚。")

PRESETS = {
    "base": BASE,
    "yue": BASE + " 6) 【输出语言·硬性】你必须始终用**粤语（广东话）**口语回答；用字要用地道粤语（例如「係」「唔」「嘅」「咗」「冇」），"
                  "语气也要像香港/广东人讲嘢，绝对不要用普通话回答。",
    "sichuan": BASE + " 6) 【输出语言·硬性】你必须始终用**四川话**口语回答，用词和语气要地道四川方言，绝对不要用普通话回答。",
}


def run(label, wav, preset, voice, wait=22, gap=0.05):
    pcm, rate, ch = wav_to_pcm(wav)
    print(f"\n{'='*72}\n[{label}]")
    print(f"  音色={voice}  指令档位={preset}  输入={os.path.basename(wav)} ({len(pcm)}B pcm @{rate}Hz)")

    volc = ws_client.create_connection(URL, header={"X-Api-Key": load_key()}, timeout=20)
    events, stop = [], False

    def drain():
        while not stop:
            try:
                d = volc.recv()
            except Exception as e:
                events.append({"type": "__closed__", "err": str(e)[:150]})
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

    def send(o):
        volc.send(json.dumps(o, ensure_ascii=False))

    send({"type": "session.create", "session": {
        "model": MODEL,
        "audio": {"input": {"format": {"type": "pcm", "rate": rate}},
                  "output": {"format": {"type": "pcm_s16le", "rate": 24000}, "voice": voice}},
        "instructions": PRESETS[preset],
    }})
    time.sleep(1.5)   # 等 session.created

    # 分片推流（20ms/片，模拟实时）
    step = int(rate * 0.02) * 2
    for i in range(0, len(pcm), step):
        send({"type": "input_audio_buffer.append", "audio": base64.b64encode(pcm[i:i+step]).decode()})
        time.sleep(0.02)
    send({"type": "input_audio_buffer.commit"})

    # commit 后持续喂静音帮 VAD 判定说完
    silence = base64.b64encode(b"\x00\x00" * int(rate * 0.2)).decode()
    t0 = time.time()
    last_audio_t = t0
    while time.time() - t0 < wait:
        try:
            send({"type": "input_audio_buffer.append", "audio": silence})
        except Exception:
            break
        time.sleep(0.2)

    stop = True
    try:
        volc.close()
    except Exception:
        pass

    types, text, audio_bytes, errs, transcript = {}, "", 0, [], ""
    for o in events:
        t = o.get("type", "?")
        types[t] = types.get(t, 0) + 1
        if t == "response.output_text.delta":
            text += o.get("delta", "") or ""
        elif t == "response.output_text.done":
            text = o.get("text", "") or text
        elif t == "response.output_audio.delta":
            audio_bytes += len(o.get("delta", "") or "")
        elif t.endswith("input_audio_transcription.done"):
            transcript = o.get("text", "") or o.get("transcript", "") or transcript
        elif "error" in t.lower():
            errs.append(json.dumps(o, ensure_ascii=False)[:200])

    print(f"  事件: {types}")
    if errs:
        print(f"  ⚠️ 错误: {errs[:2]}")
    print(f"  用户说的(转写): {transcript[:120] or '(无)'}")
    print(f"  模型文字: {text[:200] or '(无文字输出)'}")
    print(f"  TTS 音频长度(b64 chars): {audio_bytes}  {'✅ 开口了' if audio_bytes > 0 else '❌ 没出声'}")

    if text:
        cm = [c for c in YUE if c in text]
        mm = [c for c in CN if c in text]
        print(f"  粤语特征: {cm or '无'}  |  国语特征: {mm or '无'}")
        verdict = "粤语" if len(cm) > len(mm) else ("国语" if mm else "不明")
        print(f"  ➜ 文字判定: 【{verdict}】")
    return {"preset": preset, "text": text, "audio": audio_bytes, "transcript": transcript}


if __name__ == "__main__":
    wav = sys.argv[1]
    preset = sys.argv[2] if len(sys.argv) > 2 else "base"
    voice = sys.argv[3] if len(sys.argv) > 3 else "zh_female_cancan_mars_bigtts"
    run(f"档位={preset}", wav, preset, voice)
