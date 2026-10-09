#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seeduplex 方言/音色探测：验证「方言是靠 instructions 控制，还是靠 voice 参数控制」。

不喂音频也能测：Seeduplex 建会话后会主动开口，看它开场白的文字与音频字节即可。
"""
import base64, json, os, sys, threading, time
import websocket as ws_client

URL = "wss://openspeech.bytedance.com/api/v3/duplex/realtime/dialogue"
MODEL = "1.2.6.0"

# 粤语特征字（用于判定输出是否为粤语书面语）
CANTONESE_MARKERS = ["係", "唔", "嘅", "咗", "喺", "冇", "啲", "佢", "咁", "乜", "嘢", "睇", "畀", "嗰", "啱", "搵"]
MANDARIN_MARKERS = ["是", "不", "的", "了", "在", "没", "这", "那", "什么", "怎么", "可以"]


def load_key():
    v = os.environ.get("VOLC_ASR_API_KEY", "").strip()
    if v:
        return v
    for line in open(os.path.expanduser("~/.dsh/.credentials.yaml"), encoding="utf-8", errors="ignore"):
        s = line.strip()
        if s.startswith("VOLC_ASR_API_KEY"):
            return s.split(":", 1)[-1].strip().strip('"').strip("'")
    return ""


KEY = load_key()
if not KEY:
    print("✗ 无 VOLC_ASR_API_KEY")
    sys.exit(1)


def probe(label, voice, instructions, wait=16):
    print(f"\n{'='*70}\n[{label}]")
    print(f"  voice = {voice}")
    print(f"  instr = {instructions[:100]}{'...' if len(instructions) > 100 else ''}")
    try:
        volc = ws_client.create_connection(URL, header={"X-Api-Key": KEY}, timeout=20)
    except Exception as e:
        print(f"  ✗ 连接失败: {str(e)[:150]}")
        return None

    events = []
    stop = False

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

    try:
        volc.send(json.dumps({"type": "session.create", "session": {
            "model": MODEL,
            "audio": {
                "input": {"format": {"type": "pcm", "rate": 16000}},
                "output": {"format": {"type": "pcm_s16le", "rate": 24000}, "voice": voice},
            },
            "instructions": instructions,
        }}, ensure_ascii=False))
    except Exception as e:
        print(f"  ✗ session.create 发送失败: {str(e)[:150]}")
        return None

    time.sleep(wait)
    stop = True
    try:
        volc.close()
    except Exception:
        pass

    # 汇总
    types = {}
    text = ""
    audio_bytes = 0
    errs = []
    for o in events:
        t = o.get("type", "?")
        types[t] = types.get(t, 0) + 1
        if t == "response.output_text.delta":
            text += o.get("delta", "") or ""
        elif t == "response.output_text.done":
            text = o.get("text", "") or text
        elif t == "response.output_audio.delta":
            audio_bytes += len(o.get("delta", "") or "")
        elif "error" in t.lower():
            errs.append(json.dumps(o, ensure_ascii=False)[:220])

    print(f"  事件类型: {types}")
    if errs:
        print(f"  ⚠️ 错误: {errs[:3]}")
    print(f"  音频(base64长度): {audio_bytes}")
    print(f"  模型文字: {text[:200] if text else '(无文字输出)'}")

    if text:
        cm = [c for c in CANTONESE_MARKERS if c in text]
        mm = [c for c in MANDARIN_MARKERS if c in text]
        print(f"  粤语特征字: {cm if cm else '无'}")
        print(f"  国语特征字: {mm if mm else '无'}")
        verdict = "粤语" if len(cm) > len(mm) else ("国语" if mm else "不明")
        print(f"  ➜ 判定: 文字像【{verdict}】")

    return {"types": types, "text": text, "audio_bytes": audio_bytes, "errs": errs}


BASE = ("你是 CLD-Voice 的语音需求协作伙伴，用户正用语音描述需求。"
        "你必须**用语音开口回答**，每轮都要说话，不要让用户只看到文字。"
        "规则：1) 简短确认听懂核心点；2) 最多追问一个最关键不明确处；3) 每轮≤60字，口语化像真人，不列清单；"
        "4) 用户可随时打断，打断后接着新内容走；5) 对话多轮，最终目标是帮用户把需求聊清楚。")

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    V = "zh_female_cancan_mars_bigtts"

    if which in ("all", "base"):
        probe("A. 对照：现用音色 + 现用指令（预期国语）", V, BASE)

    if which in ("all", "yue"):
        probe("B. 同音色 + 追加「必须用粤语回答」指令",
              V, BASE + " 6) 【输出语言】你必须始终用**粤语（广东话）**口语回答，用字和语气都要地道粤语，不要用普通话。")

    if which in ("all", "sichuan"):
        probe("C. 同音色 + 追加「必须用四川话回答」指令",
              V, BASE + " 6) 【输出语言】你必须始终用**四川话**口语回答，用词和语气都要地道四川方言。")

    if which in ("all", "voices"):
        for cand in ["zh_female_wenroutaozi_mars_bigtts", "zh_female_yueyu_mars_bigtts",
                     "zh_male_yueyu_mars_bigtts", "zh_female_cantonese_mars_bigtts"]:
            probe(f"D. 音色候选试错: {cand}", cand, BASE, wait=10)
