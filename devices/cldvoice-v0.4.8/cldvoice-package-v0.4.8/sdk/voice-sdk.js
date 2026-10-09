/* voice-sdk.js — CLD-Voice 产品化接入库 (L2)
 * 任何 Web/Electron 页面引入本文件即可获得全双工语音对话能力。
 *
 * 用法:
 *   const v = new VoiceClient({ url:'ws://127.0.0.1:8905', token:'', voice:true });
 *   v.on('partial',  t => {...});   // 你说的内容实时转写
 *   v.on('ai_text',  t => {...});   // AI 回复文本(流式)
 *   v.on('state',    s => {...});   // listening|ai_talking|idle|error
 *   v.on('audio',    () => {});     // AI 语音开始播放
 *   v.start();        // 开始说话
 *   v.stop();         // 结束 → 触发 AI 回应
 *   v.interrupt();    // 打断 AI
 *   v.draft();        // 成稿(可选): 若配置 draftUrl 回调 md
 *   v.destroy();      // 关闭
 *
 * 兼容: 浏览器 WebSocket + AudioContext; 自动 16k 采集 / 24k 播放。
 * 协议: WS 文本帧 v1 (voice-service)。
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.VoiceClient = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  class VoiceClient {
    constructor(opts = {}) {
      this.url = opts.url || 'ws://127.0.0.1:8905';
      this.token = opts.token || '';
      this.playVoice = opts.voice !== false;      // 默认播放 AI 语音
      this.draftUrl = opts.draftUrl || '/voice/draft';
      this.autoDraftOnStop = opts.autoDraftOnStop === true;
      this._events = {};
      this._ws = null;
      this._stream = null;
      this._actx = null;      // 录音 ctx (16k)
      this._proc = null;
      this._playCtx = null;   // 播放 ctx (24k)
      this._audioBuf = '';
      this._userFinal = '';
      this._rows = [];
      this._started = false;
    }

    on(ev, fn) { (this._events[ev] = this._events[ev] || []).push(fn); return this; }
    _emit(ev, data) { (this._events[ev] || []).forEach(f => { try { f(data); } catch (e) {} }); }

    get state() {
      if (this._err) return 'error';
      if (this._aiTalking) return 'ai_talking';
      if (this._listening) return 'listening';
      return this._started ? 'idle' : 'off';
    }
    _pushState() { this._emit('state', this.state); }

    // ── 录音(16k PCM Int16) ──
    _startMic() {
      return navigator.mediaDevices.getUserMedia({ audio: true }).then(st => {
        this._stream = st;
        this._actx = new AudioContext({ sampleRate: 16000 });
        const src = this._actx.createMediaStreamSource(st);
        this._proc = this._actx.createScriptProcessor(2048, 1, 1);
        this._proc.onaudioprocess = ev => {
          const d = ev.inputBuffer.getChannelData(0);
          const b = new Int16Array(d.length);
          for (let i = 0; i < d.length; i++) { const s = Math.max(-1, Math.min(1, d[i])); b[i] = s < 0 ? s * 0x8000 : s * 0x7FFF; }
          this._sendPcm(b.buffer);
        };
        src.connect(this._proc);
        const mute = this._actx.createGain(); mute.gain.value = 0;
        this._proc.connect(mute); mute.connect(this._actx.destination);
      });
    }
    _stopMic() {
      try { if (this._proc) { this._proc.disconnect(); this._proc = null; } } catch (e) {}
      try { if (this._stream) { this._stream.getTracks().forEach(t => t.stop()); } } catch (e) {}
      this._stream = null;
      try { if (this._actx) { this._actx.close(); } } catch (e) {}
      this._actx = null;
    }
    _sendPcm(buf) {
      if (this._ws && this._ws.readyState === 1) { try { this._ws.send(buf); } catch (e) {} }
    }
    _sendJson(o) {
      if (this._ws && this._ws.readyState === 1) { try { this._ws.send(JSON.stringify(o)); } catch (e) {} }
    }

    // ── AI 语音播放(24k PCM, 累积成段播) ──
    _playAi(b64) { if (this.playVoice) this._audioBuf += b64; }
    _flushAudio() {
      if (!this._audioBuf || !this.playVoice) { this._audioBuf = ''; return; }
      try {
        const c = new AudioContext({ sampleRate: 24000 });
        if (c.state === 'suspended') c.resume();
        const bin = atob(this._audioBuf), n = bin.length / 2, f = new Float32Array(n);
        for (let i = 0; i < n; i++) { const s = bin.charCodeAt(2 * i) | (bin.charCodeAt(2 * i + 1) << 8); f[i] = s > 32767 ? (s - 65536) / 32768 : s / 32768; }
        const ab = c.createBuffer(1, f.length, 24000); ab.copyToChannel(f, 0);
        const src = c.createBufferSource(); src.buffer = ab; src.connect(c.destination);
        src.onended = () => { try { c.close(); } catch (e) {} };
        src.start();
        this._emit('audio');
      } catch (e) {}
      this._audioBuf = '';
    }

    _onWsMsg(ev) {
      try {
        const d = JSON.parse(ev.data);
        switch (d.type) {
          case 'ready': break;
          case 'transcript_delta': this._userFinal += d.delta; this._emit('partial', this._userFinal); break;
          case 'text_delta': this._aiText = (this._aiText || '') + d.delta; this._emit('ai_text', d.delta); break;
          case 'text_done': this._emit('ai_done', d.text || this._aiText || ''); break;
          case 'audio_delta': this._aiTalking = true; this._pushState(); this._playAi(d.audio); break;
          case 'audio_done': this._flushAudio(); this._aiTalking = false; this._listening = false; this._pushState(); break;
          case 'done':
            this._flushAudio();
            if (this._userFinal.trim()) this._rows.push({ role: 'user', text: this._userFinal.trim() });
            if (this._aiText) this._rows.push({ role: 'ai', text: this._aiText });
            this._aiText = '';
            this._userFinal = '';
            this._aiTalking = false; this._listening = true;
            this._emit('turn', this._rows);
            this._pushState();
            break;
          case 'err': this._err = d.msg; this._emit('error', d.msg); this._pushState(); break;
        }
      } catch (e) {}
    }
    _onWsText(t) {
      // 流式文本: 累积 AI 文本
      this._aiText = (this._aiText || '') + t;
    }

    // ── 对外 API ──
    start() {
      if (this._started) return this.stop();
      this._started = true; this._err = null; this._rows = [];
      try { this._ws = new WebSocket(this.url); } catch (e) { this._err = 'ws: ' + e.message; this._pushState(); return; }
      this._ws.binaryType = 'arraybuffer';
      this._ws.onmessage = ev => {
        if (typeof ev.data === 'string') {
          // 可能是 JSON 或纯文本流
          try { this._onWsMsg(ev); } catch (e) { this._onWsText(ev.data); }
        } else this._onWsMsg({ data: new TextDecoder().decode(ev.data) });
      };
      this._ws.onerror = () => { this._err = '连接失败'; this._pushState(); };
      this._ws.onopen = () => {
        this._startMic(buf => this._sendPcm(buf))
          .then(() => { this._listening = true; this._pushState(); })
          .catch(e => { this._err = 'mic: ' + String(e.message || e); this._pushState(); });
      };
    }
    stop() {
      if (!this._started) return;
      this._listening = false; this._pushState();
      this._sendJson({ type: 'commit' });
      this._stopMic();
      setTimeout(() => { this._started = false; }, 1000);
      if (this.autoDraftOnStop) setTimeout(() => this.draft(), 1500);
    }
    interrupt() {
      this._sendJson({ type: 'cancel' });
      this._aiTalking = false; this._listening = true; this._pushState();
    }
    draft(cb) {
      const disc = this._rows.map(x => ({ text: x.text }));
      if (!disc.length) { this._emit('draft', { ok: false, error: 'empty' }); return; }
      fetch(this.draftUrl, {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ discussion: disc, title: '语音需求' }),
      }).then(r => r.json()).then(d => {
        this._emit('draft', d);
        if (cb) cb(d);
      }).catch(e => this._emit('error', String(e)));
    }
    destroy() {
      this._sendJson({ type: 'close' });
      this._stopMic();
      try { if (this._ws) this._ws.close(); } catch (e) {}
      this._ws = null; this._started = false;
    }
  }

  return VoiceClient;
});
