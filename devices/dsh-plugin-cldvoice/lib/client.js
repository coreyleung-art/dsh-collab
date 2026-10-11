// dsh-plugin-cldvoice — client 端（CLD 内嵌悬浮球语音会议记录）
// v0.4.8: 注入改为"纯总结需求文件"——内容只含 LLM 提炼(背景/需求/约束/决策), 不再带原始"讨论留痕"; 原始语音只落盘 .md 回溯
//   成稿引擎增强: 折叠"- -"嵌套 / 删空节(含"- 无"占位) 让注入更干净; 加注入诊断(origin/ok/contentLen 上屏)
// v0.4.7: 音量可调——增加全局 playGain(默认 1.35 补偿火山默认偏低), 播放路径经过增益; 面板加"音量"滑块(30%~250%), localStorage 记住
// v0.4.6: ①默认样式=星云 ②修"球放大被方框约束"——canvas 280→460(半宽230>最大光晕216), 球随声音放大不再被边界裁切
// v0.4.5: 太极图改"线描透底版"——无实心色块, 只留外圈+S曲线描边+阴阳眼(上实心=阳有, 下空心=阴无), 体现象征"有/无"且透底
// v0.4.4: ①默认样式=科技环(改成存储键 _v2 重置浏览器旧"极光"选择) ②新增 ☯ 太极图 样式(阴阳流转, 随能量缩放/缓转)
// v0.4.3: 默认样式改回"最初那个"(科技环 tech, v0.4.0 原版) — 用户要找最开始样式
// v0.4.2: 光球可换样式——面板提供 多 种(科技环/极光/声波雷达/星云), 用户自选, localStorage 记住选择
// v0.4.1: 光球升级——更大(280px/baseR64) + 更快跟随(0.32) + AI说话也动球(aiPulse) + RMS增益3.8(30%口语≈0.28平缓)
// v0.4.0: 新增"科技感语音浮点球"——点●说话(rec)时画面浮现 canvas 动画 orb, 随麦克风能量(RMS)缩放/波动, 可拖拽, 关掉消失
// v0.3.9: 弃用 micOff 送静音(会干扰模型对用户语音感知, 诱发"只回文字没语音"), 改用硬件回声消除(echoCancellation/noiseSuppression)
// v0.3.8: 修"3把不同声音"——flushAi 改单 buffer 无缝播放(不再 2s 切块多 start), 避免接缝/异音感; 仅超长(>45s)才切块
// v0.3.7: 修"一句话4人回/4次录入"(回声/自我循环)——AI TTS 播放时置 micOff, 麦克风改送静音
// v0.3.6: 修"打断叠音"——flushAi 播放前先 _stopPlayback + 用户插话即停播+发 cancel
// v0.3.5: 真·根因修复"没声音"——audio_delta 分片 base64 各自带 padding, 改逐片解码
// v0.3.4: 加音频诊断(收KB/播次/ctx/错误)
// v0.3.3: 播放前 resume + 分片 + 全局 pointerdown 解锁 + 🔊/⏳ 指示
// v0.3.2: ensurePlay() 移到点●手势内同步解锁
// v0.3.1: 成稿注入带 role(/AI)
// G6 教训: portal 到 body, 脱离布局流, 不占 conversation 区域空间
// G1 对照: ui-attachment 用 createPortal(...,document.body) 为 fixed 元素官方姿势
window.__ModuleLoader__.load({
  id: "dsh-plugin-cldvoice",
  factory: (require) => {
    var module = { exports: {} };
    var exports = module.exports;
    Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
    const React = require("react");
    let ReactDOM = null;
    try { ReactDOM = require("react-dom"); } catch (e) { console.warn('[cldvoice] react-dom 不可用, 降级为内联样式', e); }
    const BRIDGE = "ws://127.0.0.1:8905";

    // ---------- 引擎状态(模块级单例) ----------
    let eng = { open:false, rec:false, listening:false, aiTalking:false, live:'', aiLive:'', rows:[], err:null, aud:false, playing:false, errWin:'', orbStyle:'nebula', volume:1.35, pack:'zh', packs:[], clearArm:false,
      // 2026-10-10 迭代：成稿改为「先看/先改/再采用」，不再一点就发出去
      draftText:'', draftPrev:'', draftId:'', draftNote:'', draftBusy:false, note:'',
      autoSend:(function(){ try{ const v=localStorage.getItem('cldvoice_autosend'); return v==='1'; }catch(e){ return false; } })() };
    const ls = new Set();
    function setEng(p){ eng = Object.assign({}, eng, p); for (const f of ls) f(); }
    function useEng(){ const [,b]=React.useState(0); React.useEffect(()=>{ const f=()=>b(x=>x+1); ls.add(f); return ()=>ls.delete(f); },[]); return eng; }
    // 全局一次性手势监听: 任意用户交互都尝试解锁 playCtx, 兜底 autoplay 过期
    let _unlocked=false;
    function _primeAudio(){
      if(_unlocked) return; _unlocked=true;
      try{
        // 用临时 ctx 完成一次手势解锁, 之后 flushAi 的 ensurePlay 可直接用
        const c=new AudioContext(); if(c.state==='suspended') c.resume().catch(()=>{});
      }catch(e){}
    }

    // ---------- 语音引擎(复用 v0.2 已验证逻辑, 全双工 8905) ----------
    // 修复"没声音"(根因): 每个 audio_delta 分片的 b64 各自带 '=' padding, 整段拼接后再 atob 会抛 Invalid character
    //   → flushAi 静默失败, 400KB+ 音频全丢. 改为**逐片解码**累积 Float32, 播放时直接分段. 15/15 分片各自可解.
    let ws=null, actx=null, proc=null, muteG=null, aiBuf='', userFinal='';
    // ---------- v0.8.0: 首轮无音频 ⇒ 自动重连并回放 ----------
    // 背景（2026-10-10 实测结论）：
    //   · 下行音频失败呈【会话级二值】——同一会话要么整场出声、要么整场哑；
    //     32 场会话中「部分成部分败」的混合场 = 0（9 个有机会混合的会话里 0 个混合）。
    //   · 判别量在【服务端】：两场紧邻的会话，客户端 session.create 参数逐字相同，结果却相反；
    //     `session.created` 全量载荷仅 3 字段（type/event_id/session.id），不含可区分信息
    //     ⇒ 【无法预测】，只能「哑了就重开」。
    //   · 失败率（探针样本内）约 20%/会话 ⇒ 重连 1 次命中约 80%、2 次约 96%。
    // 设计：不回放则用户必须重说一遍；回放则「说了一次，稍等，答案自己出来」。
    let micStream=null;       // ★ v0.8.1: 麦克风 MediaStream 引用（原来没保存 ⇒ 停止时无法释放设备）
    let roundBuf=[];          // 本轮自上次 done 以来累计的 PCM 分片
    let roundBufBytes=0;
    let lastRoundBuf=[];      // 上一轮的完整分片快照（供重连回放；roundBuf 在 done 时清空）
    let roundGotAudio=false;  // 本轮是否收到过下行音频
    let pendingFail=false;    // 本轮已结束且无音频，正在等「兜底音频窗口」
    let reconnTries=0;        // 本次「一句话」已重连次数
    let reconnTimer=null;
    const RECONN_MAX=2;                          // 最多重连 2 次（探针样本内覆盖约 96%）
    const ROUNDBUF_CAP=16000*2*45;               // 缓存上限 45 秒 PCM（防长说不放）
    const FALLBACK_WAIT_MS=3000;                 // ★ 等桥的 TTS 兜底窗口（见下）
    let playCtx=null;
    let playGain=null;   // 播放增益(用户可调, 默认放大补偿火山默认偏低音量)
    let playVolume=1.35; // 默认放大 1.35x, 存 localStorage
    try{ playVolume=parseFloat(localStorage.getItem('cldvoice_play_volume'))||1.35; }catch(e){}
    function setPlayVolume(v){ playVolume=Math.max(0.3,Math.min(3,v)); try{localStorage.setItem('cldvoice_play_volume',String(playVolume));}catch(e){} if(playGain) playGain.gain.value=playVolume; setEng({volume:playVolume}); }

    // ---------- 语音包(v0.5.0): 音色+方言预设 ----------
    // 机制: 方言由 Seeduplex 的 instructions 驱动, 音色由 audio.output.voice 驱动 —— 两者独立。
    // 语音包在**建会话时**经 URL query 传给网关 8905 (?pack=<id>), 故切换后需重开会话才生效。
    let voicePack='zh';
    try{ voicePack=localStorage.getItem('cldvoice_voice_pack')||'zh'; }catch(e){}
    let packList=[{id:'zh',name:'国语·灿灿',desc:'标准普通话（默认）',dialect:'普通话'}];
    let packNote='';   // 服务端回告的实际生效包(诊断用)
    function setVoicePack(id){
      id=id||'zh'; voicePack=id;
      try{localStorage.setItem('cldvoice_voice_pack',id);}catch(e){}
      setEng({pack:id, packNote:''});
    }
    function bridgeUrl(){ return BRIDGE+'/?pack='+encodeURIComponent(voicePack); }
    function loadPacks(){
      // 包清单由网关提供(GET /v1/packs), 避免前端硬编码; 失败则用内置兜底
      try{
        fetch('http://127.0.0.1:8906/v1/packs').then(r=>r.json()).then(d=>{
          if(d&&d.packs&&d.packs.length){ packList=d.packs; setEng({packs:d.packs}); }
        }).catch(()=>{});
      }catch(e){}
    }

    // ---------- 一键清屏(v0.5.1) ----------
    // rows/live/aiLive 只存在内存(模块级 eng), 不落 localStorage; 原来唯一清空点是
    // "✅完成注入"成功后 → 只要不做注入, 关掉面板再开旧记录仍在。此处提供手动清空。
    // 二次确认(点击后 3.5s 内再点才真清), 避免误删尚未注入的讨论内容。
    let clearTimer=null;
    function clearHistory(){
      userFinal=''; aiBuf='';
      audDbg={rx:0, played:0, err:''};
      // ★★★ 2026-10-12 用户产品决策：「点清屏算一轮，然后历史成稿自动归档」
      //   ⇒ 清屏 = 【本轮结束】的边界，一次做完三件：
      //     ① 成稿【自动归档】（存【当前界面文本】—— 用户可在文本框里改，按 id 归档会丢掉编辑）
      //     ② 清空讨论（rows）
      //     ③ 清空底稿（draftText/draftPrev/draftId）⇒ 下一轮从零起稿，不再混上一轮
      //   ★ 归档【成败都要如实说】—— 不能说"已归档"而实际没落盘。
      const draftText = (eng.draftText || '').trim();
      if (draftText) {
        setEng({ draftNote: '正在归档本轮成稿…' });
        fetch('/voice/drafts/save', {
          method: 'POST', headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ content: draftText, title: '语音会议记录', edited: true }),
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            setEng({ draftNote: (d && d.ok)
              ? ('本轮已归档 · ' + (d.name || '') + ' · ' + (d.chars || 0) + ' 字 · 可在 8902/drafts 翻查')
              : ('★ 归档失败：' + ((d && d.error) || '未知原因') + ' —— 成稿未落盘（讨论与底稿已清）') });
          })
          .catch(function (e) {
            setEng({ draftNote: '★ 归档失败：' + String((e && e.message) || e) + ' —— 成稿未落盘' });
          });
      }
      setEng({ rows: [], live: '', aiLive: '', aiTalking: false, clearArm: false,
               draftText: '', draftPrev: '', draftId: '',
               // ★ 归档是异步的，上面若已写过"正在归档…"就不要被这句覆盖掉
               draftNote: draftText ? (eng.draftNote || '正在归档本轮成稿…') : '已清空 · 新一轮' });
    }
    // ★★★ 2026-10-12 加（用户实测）：
    //   「成稿没办法清理…当我把语音的上下文对话记录清理掉之后，成稿却没有清理的地方，
    //     这就导致我两轮对话之间的成稿会被混淆」
    //   根因：`/api/draft` 的 base 取自 `eng.draftText`（:679），
    //         而 `clearHistory()` 只清 rows、**不清 draftText**
    //         ⇒ 清掉讨论后，下一轮成稿【仍以旧成稿为底稿做增量修订】⇒ 两轮混淆。
    //   ⇒ 提供独立的「清成稿」入口：只清成稿，不动讨论（两者生命周期本就不同）。
    function clearDraft(){
      setEng({draftText:'', draftPrev:'', draftId:'', draftNote:'成稿已清空 · 下一轮将从零起稿，不再沿用旧底稿'});
    }
    function armClear(){
      if(eng.clearArm){                       // 第二次点击 → 真清
        if(clearTimer){ clearTimeout(clearTimer); clearTimer=null; }
        clearHistory();
        return;
      }
      setEng({clearArm:true});                // 第一次点击 → 进入待确认
      if(clearTimer) clearTimeout(clearTimer);
      clearTimer=setTimeout(()=>{ clearTimer=null; setEng({clearArm:false}); }, 3500);
    }
    let audDbg={rx:0, played:0, err:''};   // 诊断: 收到字节 / 播放次数 / 错误
    // 语音能量(RMS) → 驱动浮点球动画. target=麦克风实时能量; display=平滑现值(rAF 插值)
    const micEnergyTgt={current:0};
    const micEnergyDisp={current:0};
    function ensurePlay(){
      if(!playCtx){
        try{ playCtx=new AudioContext(); }
        catch(e){ audDbg.err='newCtx:'+String(e.message||e); return null; }
      }
      if(!playGain){ try{ playGain=playCtx.createGain(); playGain.gain.value=playVolume; playGain.connect(playCtx.destination); }catch(e){} }
      try{
        if(playCtx.state==='suspended'){ playCtx.resume().catch(e=>{audDbg.err='resume:'+String(e&&(e.message||e));}); }
      }catch(e){ audDbg.err='resumeThrow:'+String(e.message||e); }
      return playCtx;
    }
    // 逐片累积解码后的 Float32 片段 (每个 chunk 自身 base64 合法)
    let aiSamples=[];
    let playSources=[];   // 正在播放的 AudioBufferSource[], 用于打断时立即 stop 防叠音
    function _stopPlayback(){
      for(const s of playSources){ try{ s.onended=null; s.stop(); try{s.disconnect();}catch(e){} }catch(e){} }
      playSources=[];
    }
    function playAi(b64){
      if(typeof b64!=='string'||!b64){ audDbg.err='audio字段空/非字符串'; setEng({aud:false}); return; }
      audDbg.rx+=b64.length;
      try{
        const bin=atob(b64), n=bin.length/2, seg=new Float32Array(n);
        for(let i=0;i<n;i++){ const s=bin.charCodeAt(2*i)|(bin.charCodeAt(2*i+1)<<8); seg[i]=s>32767?(s-65536)/32768:s/32768; }
        aiSamples.push(seg);
      }catch(e){ audDbg.err='chunkDecode:'+String((e&&e.message)||e); }
      setEng({aud:true});
    }
    function stopAudio(){
      _stopPlayback();
      if(proc){try{proc.disconnect();}catch(e){} proc=null;}
      if(muteG){try{muteG.disconnect();}catch(e){} muteG=null;}
      if(actx){try{actx.close();}catch(e){} actx=null;}
      // ★ v0.8.1 修（用户报「没点说话也在收录 / 上轮没正常关闭，只是按钮变了」）：
      //   原实现只断开了音频处理链路、关掉了 AudioContext，**从未释放麦克风设备本身**
      //   （startMic 拿到 MediaStream 后没保存引用，track 永远停不掉）。
      //   后果：macOS 侧麦克风一直被本进程占用（指示灯常亮），
      //         按钮变回「● 说话」只代表【不再把音频发给桥】，不代表设备已释放。
      //   本域四份语音入口对照：dsh-plugin-voice 有 getTracks() 释放，本插件此前 0 处。
      if(micStream){ try{ micStream.getTracks().forEach(t=>t.stop()); }catch(e){} micStream=null; }
      aiSamples=[]; aiBuf='';
    }
    function startMic(cb){
      // 真正保障在 toggleRec 同步调用 ensurePlay(手势解锁)
      // 用硬件回声消除(echoCancellation)替代手工 micOff 送静音: 后者会干扰模型对用户语音的感知
      return navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation:true, noiseSuppression:true, autoGainControl:true }
      }).then(st=>{
        micStream=st;                    // ★ v0.8.1: 保存引用，供停止时释放
        actx=new AudioContext({sampleRate:16000});
        const src=actx.createMediaStreamSource(st);
        proc=actx.createScriptProcessor(2048,1,1);
        proc.onaudioprocess=ev=>{
          const d=ev.inputBuffer.getChannelData(0), b=new Int16Array(d.length);
          let sum=0; for(let i=0;i<d.length;i++){ const v=d[i]; sum+=v*v; }
          micEnergyTgt.current=Math.min(1, Math.sqrt(sum/d.length)*3.8); // RMS→0..1 能量目标(30%口语≈0.28)
          for(let i=0;i<d.length;i++){ const s=Math.max(-1,Math.min(1,d[i])); b[i]=s<0?s*0x8000:s*0x7FFF; }
          cb(b.buffer);
        };
        src.connect(proc);
        muteG=actx.createGain(); muteG.gain.value=0;
        proc.connect(muteG); muteG.connect(actx.destination);
      });
    }
    // 播放累积的 Float32 片段. 单个连续 buffer 播放(避免多段 start 产生的断裂/异音感), 仅在超长时切块
    function flushAi(){
      if(!aiSamples.length){ setEng({aud:false, playing:false}); return; }
      try{
        const c=ensurePlay(); if(!c){ setEng({aud:false,playing:false,errWin:audDbg.err||'noCtx'}); return; }
        if(c.state==='suspended'){ try{ c.resume().catch(()=>{}); }catch(e){} }
        _stopPlayback();   // 新一段回答开播前, 停掉上一轮未播完的音源 → 防叠音
        const SR=24000;
        // 把所有片段拼成一个大 Float32(每片已各自解码)
        let total=0; for(const s of aiSamples) total+=s.length;
        const f=new Float32Array(total); let pos=0;
        for(const s of aiSamples){ f.set(s, pos); pos+=s.length; }
        // 单 buffer 无缝播放(避免多段 start 的接缝/异音), 仅当超长(>45s)才切块
        const MAXLEN=SR*45, SAFE=SR*40;
        if(f.length<=MAXLEN){
          const ab=c.createBuffer(1, f.length, SR); ab.copyToChannel(f,0);
          const src=c.createBufferSource(); src.buffer=ab; src.connect(playGain||c.destination);
          src.onended=()=>{ const i=playSources.indexOf(src); if(i>=0) playSources.splice(i,1); };
          src.start(); playSources.push(src); audDbg.played++; setEng({playing:true});
        } else {
          for(let off=0; off<f.length; off+=SAFE){
            const len=Math.min(SAFE, f.length-off);
            const seg=f.slice(off, off+len);
            const ab=c.createBuffer(1, len, SR); ab.copyToChannel(seg,0);
            const src=c.createBufferSource(); src.buffer=ab; src.connect(playGain||c.destination);
            src.onended=()=>{ const i=playSources.indexOf(src); if(i>=0) playSources.splice(i,1); };
            src.start(); playSources.push(src); audDbg.played++; setEng({playing:true});
          }
        }
      }catch(e){ audDbg.err='play:'+String(e.message||e); }
      aiSamples=[];
      setEng({aud:false, playing:false, errWin:audDbg.err});
    }
    function onBridgeMsg(ev){
      try{
        const d=JSON.parse(ev.data);
        if(d.type==='pack'){
          // 服务端回告本次会话实际生效的语音包(诊断行展示, 便于确认切换成功)
          packNote='🗣 '+(d.pack||'')+(d.dialect?('·'+d.dialect):'');
          setEng({pack:d.pack, packNote:packNote});
        }
        else if(d.type==='transcript_delta'){
          // 用户又开始说话 → 若是打断(TTS 仍在播/在说), 立即停播 + 通知桥 cancel, 防叠音
          if(playSources.length||eng.aiTalking){
            _stopPlayback();
            if(ws&&ws.readyState===1){ try{ws.send(JSON.stringify({type:'cancel'}));}catch(e){} }
          }
          userFinal+=d.delta; setEng({live:userFinal, aiTalking:false});
        }
        else if(d.type==='text_delta'){ setEng({aiLive:eng.aiLive+d.delta}); }
        else if(d.type==='audio_delta'){
          roundGotAudio=true;
          // ★ 兜底音频在窗口内到达 ⇒ 取消重连判定（这一轮其实是好的）
          if(pendingFail){ pendingFail=false; if(reconnTimer){ clearTimeout(reconnTimer); reconnTimer=null; } }
          eng.aiTalking=true; playAi(d.audio);
        }
        else if(d.type==='audio_done'){ flushAi(); setEng({aiTalking:false,listening:true}); }
        else if(d.type==='done'){
          flushAi();
          // ★ v0.8.0: 本轮结束。
          //   ① 先照常落行（**绝不因重连而吞掉内容** —— 这是受控对照发现的第一版缺陷：
          //      原实现在无音频时直接 return，把正常轮次的内容也吞了，测试 5 项全败）。
          //   ② 再判断是否要等「兜底窗口」；无音频时把本轮分片存为快照，供可能的重连回放。
          const rows=eng.rows;
          // ★ P3 + 对话态（B/C）：优先级 = 结束对话 > 说「发给X」 > 对话态直投 > 常规落行
          //   · 说「结束对话」⇒ 退出对话态
          //   · 说「发给 X：内容」⇒ 投递（成功后由 sendToNamedSession 自动进入对话态 = B）
          //   · 已在对话态且非上述 ⇒ 【直接投给目标】，不必每次再说「发给 X」
          {
            const _txt = String(userFinal || '').trim();
            if (_txt && /结束对话|退出对话/.test(_txt)) {
              exitTalk('已退出对话态');
              userFinal = ''; eng.aiLive = '';
            } else {
              const _t = parseSendTarget(_txt);
              if (_t) {
                sendToNamedSession(_t.name, _t.body, '');
                userFinal = ''; eng.aiLive = '';
              } else if (talkTarget && _txt) {
                sendToTalk(_txt);
                userFinal = ''; eng.aiLive = '';
              }
            }
          }
          if(userFinal.trim()) rows.push({role:'user',text:userFinal.trim(),at:Date.now()});   // ★ at=真实发生时刻（修「所有轮次同一时刻」）
          if(eng.aiLive.trim()) rows.push({role:'ai',text:eng.aiLive.trim(),at:Date.now()});
          setEng({rows, live:'', aiLive:'', aiTalking:false, listening:true, note:null});
          userFinal='';
          if(!roundGotAudio && eng.rec){
            lastRoundBuf=roundBuf.slice();      // 快照本轮音频（重连时回放用）
            roundBuf=[]; roundBufBytes=0;       // 本轮分片已入快照，清空以便下一轮独立累计
            scheduleReconnectCheck();           // 不立即重连，先等兜底窗口
          } else {
            resetRound();
          }
        } else if(d.type==='err'){ setEng({err:d.msg, rec:false}); }
      }catch(e){ audDbg.err='onmsg:'+String((e&&e.message)||e); }
    }
    // v0.8.0: 抽出 openWs —— 初次连接与【重连】共用。
    //   reuseMic=true 时不重启麦克风（重连场景麦克风仍在跑，重启会得到第二条流）
    function openWs(opts){
      opts=opts||{};
      try{ ws=new WebSocket(bridgeUrl()); }catch(e){ setEng({err:'桥连接失败',rec:false}); return; }
      ws.binaryType='arraybuffer';
      ws.onmessage=onBridgeMsg;
      ws.onerror=()=>setEng({err:'无法连接语音桥(8905)',rec:false});
      ws.onopen=()=>{
        if(opts.reuseMic){ if(opts.onReady) opts.onReady(); return; }
        startMic(buf=>{
          pushRoundBuf(buf);
          if(ws&&ws.readyState===1){ try{ws.send(buf);}catch(e){} }
        })
          .then(()=>{ setEng({listening:true}); if(opts.onReady) opts.onReady(); })
          .catch(e=>setEng({err:'麦克风:'+String(e.message||e),rec:false}));
      };
    }
    function pushRoundBuf(buf){
      if(roundBufBytes>=ROUNDBUF_CAP) return;   // 超上限不再缓存（仍照常实时发送）
      roundBuf.push(buf); roundBufBytes+=(buf&&buf.byteLength)||0;
    }
    // ★ v0.8.0 核心：关掉这场哑会话 → 开新会话 → 回放本轮已说的音频 → 自动补 commit。
    //   用户无需重说。返回 false 表示已达重连上限（不再重试）。
    function autoReconnect(){
      if(reconnTries>=RECONN_MAX) return false;
      reconnTries++;
      pendingFail=false;
      if(reconnTimer){ clearTimeout(reconnTimer); reconnTimer=null; }
      const replay=lastRoundBuf.slice();
      lastRoundBuf=[]; roundBuf=[]; roundBufBytes=0; roundGotAudio=false;
      userFinal='';                                        // 旧会话的转录作废（回放后会重新转写）
      try{ ws&&ws.close(); }catch(e){}
      ws=null;
      setEng({note:`本次连接未出声，已自动重连 ${reconnTries}/${RECONN_MAX} 并回放你刚说的话…`,
              err:null, aiLive:'', live:''});
      openWs({reuseMic:true, onReady:()=>{
        for(const b of replay){ try{ ws.send(b); }catch(e){} }
        try{ ws.send(JSON.stringify({type:'commit'})); }catch(e){}
      }});
      return true;
    }
    // ★ 延后判定（v0.8.0 关键修正，由受控对照发现）：
    //   生产环境下「本轮无音频」会触发【桥的 TTS 兜底】——duplex_bridge 在 response.done 时
    //   若发现本轮 0 字节且有文本，会发 speech_text_buffer.commit 强制合成，音频【稍后】才到。
    //   ⇒ 不能一见到「无音频的 done」就重连，否则会把「兜底马上就要出声」的轮次误判为坏会话，
    //     把一次正常回答变成一次多余的重连（实测：真实案例中正是这条把正常轮次判成坏的）。
    //   ⇒ 改为：先等 FALLBACK_WAIT_MS，窗口内若音频到达则取消；仍无才重连。
    function scheduleReconnectCheck(){
      if(reconnTimer) clearTimeout(reconnTimer);
      pendingFail=true;
      reconnTimer=setTimeout(()=>{
        reconnTimer=null;
        if(!pendingFail) return;                    // 期间已收到音频 / 已重连
        if(roundGotAudio){ pendingFail=false; resetRound(); return; }
        if(!eng.rec){ pendingFail=false; return; }   // 用户已停止，不重连
        if(reconnTries>=RECONN_MAX){
          // ★ v0.8.0 修：重试耗尽原来是【静默放弃】——用户视角是「说了话、什么都没发生、不知为何」。
          //   实测（复核方 n=6 + 生产日志）：失败可连片 2~3 场 ⇒ 上限用尽是真会发生的路径，不能无提示。
          //   此处用 err（红）——它确实是失败，不是自愈过程；并给出可执行的下一步。
          pendingFail=false; resetRound();
          setEng({err:`连续 ${RECONN_MAX+1} 次连接都未出声（服务端故障，非本机麦克风）。请点 ⏹ 停止后重新开始。`,
                  listening:false});
          return;
        }
        autoReconnect();
      }, FALLBACK_WAIT_MS);
    }
    function resetRound(){
      pendingFail=false;
      if(reconnTimer){ clearTimeout(reconnTimer); reconnTimer=null; }
      roundBuf=[]; roundBufBytes=0; lastRoundBuf=[]; roundGotAudio=false; reconnTries=0;
    }
    // ---------- P3 定向投递（2026-10-10）----------
    // 用户需求：唤醒/录音后说「发给<会话名>：内容」→ 投进 CLD 里那个指定会话。
    // 解析与投递都在服务端做（名字在 CLD 会话侧，投递口在 agent-bus 侧）；
    // 本入口只负责【识别出这句话并转发】。
    // ---------- 对话态（2026-10-10 用户指定：B+C 都做）----------
    // B = 说「发给 X：内容」投递成功后【自动进入】对话态（意图已明确：就是要跟它说话）
    // C = 显式开关（面板按钮）可手动进出
    // 对话态内：说的话【直接投给该会话】，不必每次再说「发给 X」；回话由轮询取回并念出。
    // 退出：说「结束对话」/ 面板开关 / 投递失败。
    let talkTarget = null;   // {id, title}
    let talkAsk = false;
    let talkAskBuf = '';   // 内联输入的当前值（Enter 或点确定时提交）     // ★ C 的输入态：点「进入对话态」后，在面板内联出一个输入框

    // ★ 2026-10-11 修（用户实测：「我理解的名字跟你们实际的名字有很大差异」）：
    //   实测：301 个有 title 的会话里只有 80 个（27%）像人类可读的名字，
    //   192 个（64%）其实是首条消息片段（「背景：本机（mac-mini…」），且重名严重
    //   （单个 title 最多被 86 个会话共用）⇒ 凭记忆输入名字在多数会话上不可行。
    //   ⇒ 改为【选，而不是猜】：拉 /voice/sessions 的真实名单，按最近活跃排序，点即进。
    //   附带好处：列表项自带 id ⇒ 直接进对话态，**绕开 /voice/resolve 的歧义判定**。
    let talkList = [];
    // ★ 2026-10-11 改（用户设计的第三层落地后）：对话态入口【先读目标清单】。
    //   原实现列的是 /voice/sessions 的原始 title —— 而实测 301 个有 title 的会话里
    //   只有 80 个（27%）像人类可读的名字，192 个（64%）是首句片段（「背景：本机（mac-mini…」），
    //   重名最高 ×86 ⇒ **列出来用户也认不出**。
    //   ⇒ 现在优先列【用户自己在配置页里启用并起过别名的目标】；
    //     没有配置过才回落到原始会话列表，并提示去配置。
    function loadTalkCandidates() {
      setEng({ talkAsk: true, talkLoading: true });
      fetch('/voice/targets')
        .then(function (r) { return r.json(); })
        .then(function (d) {
          const on = ((d && d.targets) || []).filter(function (t) { return t.enabled !== false; })
            .map(function (t) { return { id: t.id, title: t.alias || t.title || '(未命名)', raw: t.title || '' }; });
          if (on.length) {
            talkList = on;
            setEng({ talkAsk: true, talkLoading: false, talkMode: 'targets', talkCount: on.length });
            return null;
          }
          setEng({ talkMode: 'fallback' });   // 没配置过 ⇒ 回落
          return fetch('/voice/sessions').then(function (r2) { return r2.json(); }).then(function (s) {
            const arr = ((s && s.sessions) || []).filter(function (x) { return (x.title || '').trim(); });
            arr.sort(function (a, b) { return (b.ts || 0) - (a.ts || 0); });
            talkList = arr.slice(0, 15).map(function (x) { return { id: x.id, title: x.title, raw: '' }; });
            setEng({ talkAsk: true, talkLoading: false, talkNamed: (s && s.named) || 0 });
          });
        })
        .catch(function (e) {
          setEng({ talkAsk: true, talkLoading: false, err: '拉取目标清单失败：' + String((e && e.message) || e) });
        });
    }
    // 配置页地址：由当前 CLD 基址拼出（同一端口同时提供 /voice/*）
    // ★ 2026-10-11 修：原实现直接返 location.origin + '/voice/config'，
    //   但该端点属插件【服务端代码】，插件未重载时它是 404
    //   ⇒ 用户点「⚙ 配置」会看到一坨 {"ok":false,"error":"unknown endpoint"}（实测发生）。
    //   ⇒ 改为【先探测再打开】：本体端点不通时，回落到已知的预览服务端口。
    //   ★ 顺序有意如此：插件端点是"正主"，预览服务只是临时兜底；
    //     一旦插件重载，第一个就通，不会再落到预览。
    const CONFIG_FALLBACKS = ['http://127.0.0.1:8799/voice/config'];
    function openConfig() {
      const base = (function () { try { return location.origin; } catch (e) { return ''; } })();
      const urls = [base + '/voice/config'].concat(CONFIG_FALLBACKS);
      let i = 0;
      const tryNext = function () {
        if (i >= urls.length) {
          setEng({ note: '配置页打不开：插件端点未上线，且预览服务未运行' });
          return;
        }
        const u = urls[i++];
        fetch(u, { method: 'GET' })
          .then(function (r) {
            if (r.status === 200) { try { window.open(u, '_blank'); } catch (e) {} setEng({ note: null }); }
            else tryNext();
          })
          .catch(function () { tryNext(); });
      };
      tryNext();
    }
    function relTime(ts) {
      if (!ts) return '';
      const m = Math.floor((Date.now() - ts) / 60000);
      if (m < 1) return '刚刚';
      if (m < 60) return m + ' 分前';
      const h = Math.floor(m / 60);
      return h < 24 ? h + ' 小时前' : Math.floor(h / 24) + ' 天前';
    }
    // 选择器单独造（不塞进渲染树里嵌套 —— 那里括号层级深，实测已两次因括号数错而语法失败）
    // 对话态入口的选择器。★ 2026-10-11：改为优先列【用户在配置页启用过的目标】。
    //   两种模式：targets（用户的清单，显示其别名）/ fallback（未配置 ⇒ 原始会话列表）。
    function TalkPicker(s) {
      if (!s.talkAsk) return null;
      const box = { marginTop: 6, border: '1px solid #334155', borderRadius: 8, padding: 8, background: '#0b1626' };
      const isTargets = s.talkMode === 'targets';
      // 配置入口（两种模式都给 —— 让用户随时能去增删目标）
      const cfgBtn = React.createElement('button', {
        type: 'button',
        title: '打开配置页：搜索本机会话、点选加入、起你自己的名字、决定它能否作为语音对象',
        onClick: function (e) { e.stopPropagation(); try { openConfig(); } catch (err) {} },
        style: { flex: 'none', background: 'transparent', border: '1px solid #334155', borderRadius: 6, color: '#7dd3fc', cursor: 'pointer', fontSize: 10, padding: '2px 7px' },
      }, '⚙ 配置');

      if (s.talkLoading) {
        return React.createElement('div', { style: box },
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8 } },
            React.createElement('span', { style: { flex: 1, fontSize: 11, color: '#94a3b8' } }, '正在拉取语音目标…'),
            cfgBtn));
      }

      const headText = isTargets
        ? ('你启用的语音目标 · 共 ' + (s.talkCount || 0) + ' 个')
        : ('未配置语音目标 ⇒ 暂列最近活跃的会话 · 共 ' + (s.talkNamed || 0) + ' 个有名字的');
      const head = React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 } },
        React.createElement('span', { style: { flex: 1, fontSize: 11, color: isTargets ? '#a7f3d0' : '#94a3b8' } }, headText),
        cfgBtn);

      const rows = talkList.length
        ? talkList.map(function (it, k) {
            return React.createElement('button', {
              key: k, type: 'button',
              onClick: function (e) { e.stopPropagation(); talkAsk = false; enterTalk(it.title, it.id); },
              title: (it.raw ? it.raw + '\n' : '') + String(it.id || ''),
              style: { textAlign: 'left', background: 'transparent', border: '1px solid #1e293b', borderRadius: 6, padding: '5px 8px', color: '#cbd5e1', cursor: 'pointer', fontSize: 12, display: 'flex', gap: 8, alignItems: 'baseline' },
            },
              React.createElement('span', { style: { flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, it.title),
              it.raw ? React.createElement('span', { style: { flex: 'none', color: '#475569', fontSize: 10, maxWidth: 110, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, it.raw) : null);
          })
        : [React.createElement('div', { key: 'none', style: { fontSize: 11, color: '#94a3b8', lineHeight: 1.6 } },
            isTargets ? '清单是空的（可能都停用了）—— 点右上「⚙ 配置」去启用。'
                      : '没有拉到会话（缓存可能为空）。点右上「⚙ 配置」搜索并选一个。')];

      if (!isTargets) {
        rows.push(React.createElement('div', { key: 'hint', style: { fontSize: 10, color: '#64748b', marginTop: 4 } },
          '★ 未配置时列的是原始 title，多数认不出 —— 建议点「⚙ 配置」选出你真正用的那几个。'));
      }
      return React.createElement('div', { style: box }, head,
        React.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 190, overflowY: 'auto' } }, rows));
    }
                             //   为什么不用 window.prompt：Electron 的 renderer 不实现 prompt，
                             //   调用返回 undefined ⇒ 用户点了「没反应」（2026-10-10 用户实测报告）。
    function enterTalk(title, id) {
      talkTarget = { title: String(title||''), id: String(id||'') };
      setEng({ talk: talkTarget.title,
               note: '★ 对话态：直接说即可发给「' + talkTarget.title + '」· 说「结束对话」退出' });
      return talkTarget;
    }
    function exitTalk(why) {
      talkTarget = null;
      setEng({ talk: null, note: why || '已退出对话态' });
    }
    function resolveAndTalk(name) {
      const nm = String(name||'').trim();
      if (!nm) { setEng({ err: '请先输入会话名' }); return; }
      setEng({ note: '正在解析「' + nm + '」…' });
      fetch('/voice/resolve', { method:'POST', headers:{'content-type':'application/json'},
        body: JSON.stringify({ name: nm }) })
        .then(function(r){ return r.json(); })
        .then(function(j){
          if (!j || !j.ok) { setEng({ err: '解析失败' }); return; }
          if (j.verdict === 'not_found') { setEng({ err: '没找到叫「' + nm + '」的会话' }); return; }
          if (j.verdict === 'ambiguous') {
            const cs = (j.candidates||[]).map(function(c){ return c.title; }).join('  /  ');
            setEng({ err: '匹配到多个：「' + cs + '」，请说全名' }); return;
          }
          const c0 = (j.candidates||[])[0] || {};
          talkAsk = false;
          enterTalk(c0.title, c0.id);
        })
        .catch(function(e){ setEng({ err: '解析失败：' + String((e&&e.message)||e) }); });
    }

    function sendToTalk(text) {
      const t = String(text||'').trim();
      if (!t) return;
      if (!talkTarget) return;
      setEng({ note: '发给「' + talkTarget.title + '」…' });
      fetch('/voice/send', {
        method:'POST', headers:{'content-type':'application/json'},
        body: JSON.stringify({ to: talkTarget.id || undefined, name: talkTarget.title,
                               text: t, sender: 'ui', origin: 'floatball-talk' }),
      }).then(function(r){ return r.json(); })
        .then(function(j){
          if (j && j.ok) { setEng({ note: '已发给「' + (j.title || talkTarget.title) + '」· 等它回话' }); return; }
          setEng({ err: '对话投递失败：' + ((j && j.error) || '未知') });
          if (j && (j.error === 'not_found' || j.error === 'ambiguous')) exitTalk('目标不可达，已退出对话态');
        })
        .catch(function(e){ setEng({ err: '对话投递失败：' + String((e&&e.message)||e) }); });
    }


    function parseSendTarget(text) {
      const t = String(text || '');
      const i = t.indexOf('发给');
      if (i < 0) return null;
      const rest = t.slice(i + 2).trim();
      if (!rest) return null;
      for (const sep of ['：', ':', '，', ',', '。']) {
        const j = rest.indexOf(sep);
        if (j > 0) {
          const name = rest.slice(0, j).trim();
          const body = rest.slice(j + 1).trim();
          if (name) return { name: name, body: body };
        }
      }
      return { name: rest, body: '' };
    }
    function sendToNamedSession(name, body, fallbackText) {
      const text = (body && body.trim()) ? body.trim() : String(fallbackText || '').trim();
      if (!text) { setEng({ err: '没有要发送的内容' }); return; }
      setEng({ note: '正在投递给「' + name + '」…', err: null });
      fetch('/voice/send', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ name: name, text: text, sender: 'ui', origin: 'floatball-voice' }),
      }).then(function (r) { return r.json().then(function (j) { return { code: r.status, j: j }; }); })
        .then(function (x) {
          const j = x.j || {};
          if (j.ok) { enterTalk(j.title || name, j.to || '');   // ★ B：投递成功即进入对话态（必须在 return 前）
                      setEng({ note: '已投递给「' + (j.title || name) + '」· 对话态中，直接说即可' }); return; }
          if (j.error === 'ambiguous') {
            const names = (j.candidates || []).map(function (c) { return c.title; }).join(' / ');
            setEng({ err: '匹配到多个：「' + names + '」，请说全名' });
            return;
          }
          if (j.error === 'not_found') { setEng({ err: '没有找到叫「' + name + '」的会话' }); return; }
          setEng({ err: '投递失败：' + (j.error || ('HTTP ' + x.code)) });
        })
        .catch(function (e) { setEng({ err: '投递请求失败：' + String((e && e.message) || e) }); });
    }


    // ---------- 回话播报（2026-10-10 · 复用本插件自己的播放链路）----------
    // 用户指定：「复用悬浮球的播放链路」⇒ 不新写播放器，直接用本文件已有的
    //   playAi(b64)（逐片解 16bit LE PCM → Float32 累积）
    //   flushAi()（24kHz 播放）· ensurePlay()（解锁 AudioContext）
    // 后端配套：POST http://127.0.0.1:8902/api/tts {text} → base64 PCM@24k（与 playAi 期望格式一致，已实测）
    let replySince = Date.now();   // ★ 以启动时刻为起点：绝不播报历史积压（实测库里有 17+ 条旧回复）
    let replyTimer = null;
    // ★★★ 2026-10-12 加（用户实测「一堆的语音同时播放」）：
    //   原 pollReplies 用 `for (const rep of d.replies) speakOneReply(rep)` ——
    //   ① 无去重 ⇒ 同一批被反复念；② 无串行 ⇒ **多条同时发声**；
    //   ③ 每条都 playAi+flushAi ⇒ **音频叠进同一缓冲 ⇒ 一起响**（实测症状）。
    //   ⇒ 现改为：只念【最新一条】+ 去重 + 播报中不叠。
    let lastSpokenReply = '';
    let replySpeaking = false;
    // ★★★ 2026-10-12（播报池迭代：用户实测驱动）
    //   ① 串行队列 —— 原实现一个窗口内【只念最后一条】，前面的被【丢弃】⇒ 用户可能永远听不到
    //   ② only 过滤 —— 只收【当前对话对象】的回话；不在对话态 ⇒ none ⇒ 不念任何东西
    //      依据：用户实测「为什么突然由另一个会话给我发了一条状态播报的语音」
    const replyQueue = [];
    const REPLY_QUEUE_MAX = 5;

    // ★ 投递确认音：本地合成、不调 TTS ⇒ 零延迟。
    //   与 C（菜单栏）的 Tink 同语义。依据：用户实测「不知道你有没有真的在听」。
    function ackTone(){
      try{
        ensurePlay();
        const c = (typeof playCtx !== 'undefined') ? playCtx : null;
        if(!c) return;
        const o = c.createOscillator(), g = c.createGain();
        o.type = 'sine'; o.frequency.value = 880;
        const t0 = c.currentTime;
        g.gain.setValueAtTime(0.0001, t0);
        g.gain.exponentialRampToValueAtTime(0.12, t0 + 0.01);
        g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.16);
        o.connect(g); g.connect(c.destination);
        o.start(t0); o.stop(t0 + 0.18);
      }catch(e){}
    }

    // ★ 失败时归还认领 —— 否则认领方播报失败 ⇒【两边都不念】
    function releaseClaim(key){
      try{
        fetch('/voice/release', { method: 'POST', headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ key: key, who: 'B-floatball' }) }).catch(function(){});
      }catch(e){}
    }

    function drainQueue(){
      if (replySpeaking) return;
      const next = replyQueue.shift();
      if (!next) return;
      if (replyQueue.length) setEng({ note: '正在念回话（还有 ' + replyQueue.length + ' 条排队）' });
      speakOneReply(next);
    }

    function speakOneReply(rep) {
      const txt = String((rep && rep.text) || '').trim();
      if (!txt) { replySpeaking = false; drainQueue(); return; }
      replySpeaking = true;
      setEng({ note: '收到回话：' + txt.slice(0, 44) });
      const _ck = String(Math.round(Number(rep && rep.at) || 0)) + '|' + txt.slice(0, 40);
      fetch('/voice/claim', { method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ key: _ck, who: 'B-floatball' }) })
        .then(function (r) { return r.json(); })
        .then(function (c) {
          if (c && c.ok && c.claimed === false) {
            setEng({ note: '本条回话已由另一入口播报，跳过（避免重复）' });
            replySpeaking = false; drainQueue();
            return;
          }
          _speakOneReplyDo(rep, txt, _ck);
        })
        .catch(function () { _speakOneReplyDo(rep, txt, _ck); });
    }

    function _speakOneReplyDo(rep, txt, _ck) {
      void rep;
      fetch('http://127.0.0.1:8902/api/tts', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ text: txt.slice(0, 600) }),
      }).then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d || !d.ok || !d.audio) {
            setEng({ err: '回话播报失败：' + ((d && d.error) || '无音频') });
            releaseClaim(_ck);
            replySpeaking = false; drainQueue();
            return;
          }
          ensurePlay();
          playAi(d.audio);
          flushAi();
          setTimeout(function () { replySpeaking = false; drainQueue(); }, 1200);
        })
        .catch(function (e) {
          setEng({ err: '回话播报失败：' + String((e && e.message) || e) });
          releaseClaim(_ck);
          replySpeaking = false; drainQueue();
        });
    }

    function pollReplies() {
      const only = (talkTarget && talkTarget.id) ? talkTarget.id : 'none';
      fetch('/voice/replies?since=' + replySince + '&only=' + encodeURIComponent(only))
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d || !d.ok) return;
          if (d.newest && d.newest > replySince) replySince = d.newest;
          for (const rep of (d.replies || [])) {
            const _t = String((rep && rep.text) || '').trim();
            if (!_t || _t === lastSpokenReply) continue;
            lastSpokenReply = _t;
            replyQueue.push(rep);
          }
          let dropped = 0;
          while (replyQueue.length > REPLY_QUEUE_MAX) { replyQueue.shift(); dropped++; }
          if (dropped) setEng({ note: '回话积压，已丢弃最旧 ' + dropped + ' 条' });
          else if (d.filtered) setEng({ note: '本窗口有 ' + d.filtered + ' 条来自非当前对话对象，未播报' });
          drainQueue();
        })
        .catch(function () {});
    }
    function startReplyPolling() {
      if (replyTimer) return;
      replyTimer = setInterval(pollReplies, 8000);
    }


    function toggleRec(){
      // 必须在用户手势(点●)内同步 create+resume playCtx, 否则 Chromium autoplay 把它挂起 → 无声
      ensurePlay();
      if(eng.rec){ // 停止并触发 AI 收尾
        if(ws&&ws.readyState===1){ try{ws.send(JSON.stringify({type:'commit'}));}catch(e){} }
        // ★★★ 2026-10-12 加（用户实测「不知道你有没有真的在听」）：
        //   用户点「⏹ 停止」= 话已说完 ⇒ 【立刻】给一声确认音（本地合成，不调 TTS ⇒ 零延迟）。
        //   与 C（菜单栏）的 Tink 同语义。★ 这是「收到即确认」最小实现。
        ackTone();
        stopAudio();                       // ★ 立刻释放麦克风（含 track.stop，见 stopAudio 内注）
        // ★ v0.8.1 修（用户报「显示未在听却仍在收 / 没点自己就开始收」）：
        //   原实现把 setEng({rec:false}) 放在 1200ms 的 setTimeout 里 ⇒ 点停止后
        //   ① 按钮仍显示「录音中」1.2 秒（UI 与真实状态脱节）
        //   ② 期间 eng.rec 仍为 true ⇒ 【自动重连的守卫 if(!eng.rec) 失效】
        //      ⇒ 若重连计时器在此窗口内触发，会在用户已停止之后【重新开连接并保持麦克风】
        //      —— 这正是「没点任何按钮它自己就开始收」的机制。
        //   现改为：状态立即翻转 + 取消已排期的重连判定；仅 ws.close() 保留 1.2s
        //   （那是为了让 commit 触发的最后一段回复能回来，与麦克风无关）。
        pendingFail=false;
        if(reconnTimer){ clearTimeout(reconnTimer); reconnTimer=null; }
        setEng({rec:false, listening:false, aiTalking:false, live:'', aiLive:'', note:null});
        const closing=ws;
        setTimeout(()=>{ try{ closing && closing.close(); }catch(e){} if(ws===closing) ws=null; },1200);
        return;
      }
      setEng({rec:true,listening:false,err:null});
      resetRound();
      openWs({});
    }

    // ---------- 成稿 / 修订 / 采用 / 回退（2026-10-10 用户迭代需求）----------
    // 用户原话：「点完成注入后文本会自动插入上下文，导致我无法 ① 提修改意见 ② 二次端到端沟通
    //   ③ 二次录入 ④ 手动修改生成的文本。我需要具备上述交互过程的功能。」
    //
    // 旧实现的两个封死点（均已移除）：
    //   · setTimeout(()=>inputActions.submit(), 300)  → 填入后 300ms 自动发送，来不及看/改
    //   · setEng({rows:[], open:false})               → 注入即清空讨论、关闭面板，切断二次沟通
    // 新语义：
    //   ✅ 成稿  → 结果只进面板内【可编辑成稿区】，不碰输入框、不发送
    //   🔄 重出稿 → 带上当前成稿作为 base ⇒ 后端走【增量修订】：只改你提到的部分，其余逐字保留
    //   📋 采用  → 把（你改过的）成稿填入输入框；是否自动发送由下方开关决定
    //   ↩ 上一版 → 回退到修订前的稿子
    function makeDraft(){
      setEng({err:null});
      // 关键: 带上 role(user/ai), 否则成稿引擎无法区分用户与 AI → 需求提炼乱/留痕无角色
      // ★★★ 2026-10-10 修（短判决位实害报告）：原实现 ts 取【生成那一刻】的
      //   new Date() ⇒ 所有轮次被盖上同一个时刻（报告实证：留痕时刻全是 11:25:24），
      //   而假时刻会「长得像真时刻」被下游当成发生时刻引用。
      //   ⇒ 改用每行落库时记下的真实时刻（x.at，见 rows.push 处）；缺失才回退。
      const _hhmmss = (t)=>{ try{ return new Date(t||Date.now()).toISOString().slice(11,19); }catch(e){ return ''; } };
      const disc=eng.rows.map(x=>({role:x.role==='user'?'user':'ai',ts:_hhmmss(x.at),text:x.text}));
      if(!disc.length){ setEng({err:'还没有对话内容'}); return; }
      const base=eng.draftText||'';                 // 已有成稿 ⇒ 作为底稿做增量修订
      setEng({draftBusy:true, draftNote:base?'正在按你的意见增量修订…':'正在成稿…'});
      fetch('/voice/draft',{method:'POST',headers:{'content-type':'application/json'},
        body:JSON.stringify({discussion:disc,title:'语音会议记录',base})})
        .then(r=>r.json()).then(d=>{
          if(d.ok&&d.content){
            const src=(d.stats&&d.stats.source)||'?';
            const kind=base?('增量修订 · '+src):('成稿 · '+src);
            setEng({ draftPrev: base||eng.draftPrev, draftText:d.content, draftId:d.id||'',
                     draftBusy:false, draftNote:kind+' · '+d.content.length+' 字 · 可直接在下方编辑',
                     err:null });
          } else {
            setEng({draftBusy:false, err:'成稿失败:'+((d&&d.error)||'未知原因')});
          }
        }).catch(e=>setEng({draftBusy:false, err:'成稿错误:'+String(e.message||e)}));
    }

    function applyDraft(inputActions){
      const t=(eng.draftText||'').trim();
      if(!t){ setEng({err:'还没有成稿，先点 ✅ 成稿'}); return; }
      if(!(inputActions&&inputActions.setDraft)){ setEng({err:'当前环境不支持填入输入框'}); return; }
      try{ inputActions.setDraft('【语音会议记录】\n'+t.slice(0,3000)); }
      catch(e){ setEng({err:'填入失败:'+String(e.message||e)}); return; }
      if(eng.autoSend){
        setTimeout(()=>{ try{inputActions.submit();}catch(e){} },300);
        setEng({err:null, draftNote:'已填入输入框并发送（「填入后自动发送」已开启）'});
      } else {
        setEng({err:null, draftNote:'已填入输入框 · 请检查/修改后自行发送（面板与讨论都保留，可继续聊）'});
      }
      // ★ 刻意不清空 rows、不关闭面板：保住二次沟通 / 二次录入的上下文
    }

    function revertDraft(){
      if(!eng.draftPrev){ setEng({err:'没有上一版可回退'}); return; }
      setEng({draftText:eng.draftPrev, draftPrev:'', draftNote:'已回退到上一版（再点 🔄 重出稿可重新修订）'});
    }

    function toggleAutoSend(){
      const v=!eng.autoSend;
      try{ localStorage.setItem('cldvoice_autosend', v?'1':'0'); }catch(e){}
      setEng({autoSend:v});
    }

    // ---------- 语音浮点球样式(可切换, 用户自选) ----------
    const ORB_STYLES=[
      {id:'tech',   label:'🔵 科技环', hint:'圆环粒子(默认)'},
      {id:'aurora', label:'🌟 极光', hint:'有机流动'},
      {id:'taiji',  label:'☯ 太极图', hint:'阴阳流转'},
      {id:'wave',   label:'🌊 声波雷达', hint:'脉冲波纹'},
      {id:'nebula', label:'🌌 星云', hint:'粒子汇聚'},
    ];
    let orbStyle = 'nebula';   // 默认=星云
    try{ orbStyle = localStorage.getItem('cldvoice_orb_style_v3') || 'nebula'; }catch(e){}
    function setOrbStyle(id){ orbStyle=id; try{localStorage.setItem('cldvoice_orb_style_v3',id);}catch(e){} setEng({orbStyle:id}); }

    // ---------- 科技感语音浮点球(canvas 动画, 随麦克风能量变化; 多种样式可切换) ----------
    function VisualOrb(props){
      const s=useEng();
      const cvRef=React.useRef(null);
      const dragRef=React.useRef(null);
      const movedRef=React.useRef(false);
      // 挂载时同步已存样式到面板高亮
      React.useEffect(()=>{ try{ if(localStorage.getItem('cldvoice_orb_style_v3')) setEng({orbStyle:localStorage.getItem('cldvoice_orb_style_v3')}); }catch(e){} },[]);
      // 拖拽(与浮球一致)
      React.useEffect(()=>{
        const el=dragRef.current; if(!el) return;
        let dragging=false, ox=0, oy=0, sx=0, sy=0;
        const down=(e)=>{ dragging=true; movedRef.current=false; ox=e.clientX-el.offsetLeft; oy=e.clientY-el.offsetTop; sx=e.clientX; sy=e.clientY; };
        const move=(e)=>{ if(!dragging)return; if(Math.abs(e.clientX-sx)>4||Math.abs(e.clientY-sy)>4) movedRef.current=true; el.style.left=(e.clientX-ox)+'px'; el.style.top=(e.clientY-oy)+'px'; el.style.right='auto'; el.style.bottom='auto'; };
        const up=()=>{ dragging=false; };
        el.addEventListener('mousedown',down); document.addEventListener('mousemove',move); document.addEventListener('mouseup',up);
        return ()=>{ el.removeEventListener('mousedown',down); document.removeEventListener('mousemove',move); document.removeEventListener('mouseup',up); };
      },[]);
      // canvas 动画环
      React.useEffect(()=>{
        let raf=0;
        const cv=cvRef.current; if(!cv) return;
        const ctx=cv.getContext('2d');
        const W=cv.width, H=cv.height, cx=W/2, cy=H/2;
        const N=48; const parts=[];
        for(let i=0;i<N;i++) parts.push({a:Math.random()*Math.PI*2, sp:(0.4+Math.random()*0.9), r:0.5+Math.random()*1.4, ph:Math.random()*Math.PI*2});
        function draw(){
          let tgt=micEnergyTgt.current || 0;
          if(s.aiTalking||s.playing){ tgt=Math.max(tgt, 0.3+0.3*Math.abs(Math.sin(performance.now()/140))); }
          micEnergyDisp.current += (tgt-micEnergyDisp.current)*0.32;
          const e=micEnergyDisp.current || 0;
          const baseR=58; const R=baseR + e*86;   // 更大画布(460)后有空间, 球随声音涨幅明显且不被裁
          const t=performance.now()/1000;
          ctx.clearRect(0,0,W,H);
          const st=orbStyle;
          if(st==='aurora'){ drawAurora(ctx,cx,cy,R,e,t); }
          else if(st==='taiji'){ drawTaiji(ctx,cx,cy,R,e,t); }
          else if(st==='wave'){ drawWave(ctx,cx,cy,R,e,t); }
          else if(st==='nebula'){ drawNebula(ctx,cx,cy,R,e,t,parts); }
          else { drawTech(ctx,cx,cy,R,e,t,parts); }
          raf=requestAnimationFrame(draw);
        }
        raf=requestAnimationFrame(draw);
        return ()=>cancelAnimationFrame(raf);
      },[]);

      // 样式切换器
      // 画布加大到 460, 确保最大光晕(R*1.5≤213)不受 canvas 边界裁切 → 球自由放大不被"方框约束"
      const box={position:'fixed',right:'50%',transform:'translateX(50%)',bottom:230,width:460,height:460,zIndex:2147483646,cursor:'grab',userSelect:'none',
        pointerEvents:'auto'};
      const wrap=React.createElement('div',{ref:dragRef,style:box,title:'语音能量球(可拖拽)'},
        React.createElement('canvas',{ref:cvRef,width:460,height:460}),
        React.createElement('div',{style:{position:'absolute',bottom:-16,left:0,right:0,textAlign:'center',color:'#7dd3fc',fontSize:13,fontFamily:'system-ui'}},
          (s.listening?'● 聆听中':'')+(s.aiTalking?' · AI 回答':'')+(s.rec?' · 说话中':'')));
      return wrap;
    }

    // 样式绘制函数
    function _drawGlow(ctx,cx,cy,R,e,c1,c2){
      const g=ctx.createRadialGradient(cx,cy,4,cx,cy,R*1.5);
      g.addColorStop(0,'rgba('+c1+','+(0.5+e*0.5)+')');
      g.addColorStop(0.5,'rgba('+c2+','+(0.28+e*0.35)+')');
      g.addColorStop(1,'rgba(2,6,23,0)');
      ctx.fillStyle=g; ctx.beginPath(); ctx.arc(cx,cy,R*1.5,0,7); ctx.fill();
    }
    // ① 极光(灵气/有机流动)
    function drawAurora(ctx,cx,cy,R,e,t){
      _drawGlow(ctx,cx,cy,R,e,'56,189,248','16,185,129');
      // 流动光斑(上下波动的花瓣状)
      for(let i=0;i<6;i++){
        const a=i/6*Math.PI*2 + t*0.5;
        const wob=Math.sin(t*2+i)*0.35;
        const px=cx+Math.cos(a)*R*(0.5+wob*0.4);
        const py=cy+Math.sin(a)*R*(0.5+wob*0.4);
        const rr=R*(0.28+e*0.35)+Math.abs(Math.sin(t*2+i))*6;
        const gg=ctx.createRadialGradient(px,py,0,px,py,rr);
        gg.addColorStop(0,'rgba('+(i%2?'129,140,248':'45,212,191')+','+(0.5+e*0.4)+')');
        gg.addColorStop(1,'rgba(2,6,23,0)');
        ctx.fillStyle=gg; ctx.beginPath(); ctx.arc(px,py,rr,0,7); ctx.fill();
      }
      // 中央亮核
      const cg=ctx.createRadialGradient(cx,cy,0,cx,cy,12+e*8);
      cg.addColorStop(0,'rgba(255,255,255,'+(0.9+e*0.1)+')');
      cg.addColorStop(1,'rgba(56,189,248,0)');
      ctx.fillStyle=cg; ctx.beginPath(); ctx.arc(cx,cy,10+e*7,0,7); ctx.fill();
    }
    // ☯ 太极图(线描透底版) —— 无实心色块, 只留轮廓, 半边有/半边无
    function drawTaiji(ctx,cx,cy,R,e,t){
      _drawGlow(ctx,cx,cy,R,e,'56,189,248','16,185,129');
      const r=R*0.74 + e*6;
      ctx.save(); ctx.translate(cx,cy); ctx.rotate(t*0.4 + e*0.6);
      const main='rgba(125,211,252,'+(0.55+e*0.4)+')';   // 阳(显)描边
      const faint='rgba(125,211,252,'+(0.18+e*0.2)+')';   // 阴(隐)描边
      // 外圈
      ctx.strokeStyle=main; ctx.lineWidth=2.6;
      ctx.beginPath(); ctx.arc(0,0,r,0,7); ctx.stroke();
      // S 曲线(标准太极蛇形): 上段凸左, 下段凸右
      ctx.strokeStyle=main; ctx.lineWidth=2;
      ctx.beginPath();
      ctx.moveTo(0,-r);
      ctx.arc(0,-r/2,r/2, -Math.PI/2, Math.PI/2, true);   // 上段→(0,0) 凸左
      ctx.arc(0, r/2,r/2, -Math.PI/2, Math.PI/2, false);  // 下段→(0,r) 凸右
      ctx.stroke();
      // 阴阳眼: 上=实心亮(阳·有), 下=空心(阴·无)
      ctx.fillStyle='rgba(255,255,255,'+(0.9+e*0.08)+')';
      ctx.beginPath(); ctx.arc(0,-r/2,r*0.09,0,7); ctx.fill();
      ctx.strokeStyle=faint; ctx.lineWidth=1.6;
      ctx.beginPath(); ctx.arc(0,r/2,r*0.09,0,7); ctx.stroke();
      ctx.restore();
    }
    // ② 科技环(圆环+粒子)
    function drawTech(ctx,cx,cy,R,e,t,parts){
      _drawGlow(ctx,cx,cy,R,e,'56,189,248','16,185,129');
      ctx.strokeStyle='rgba(125,211,252,'+(0.5+e*0.4)+')'; ctx.lineWidth=2.5;
      ctx.beginPath(); ctx.arc(cx,cy,R,0,7); ctx.stroke();
      ctx.strokeStyle='rgba(52,211,153,'+(0.35+e*0.35)+')';
      ctx.beginPath(); ctx.arc(cx,cy,R*(0.72+e*0.12),0,7); ctx.stroke();
      for(const p of parts){
        const ang=p.a+t*p.sp*1.4;
        const pr=R*(0.55+e*0.5)+Math.sin(t*2.4+p.a)*2.5;
        const px=cx+Math.cos(ang)*pr, py=cy+Math.sin(ang)*pr;
        ctx.fillStyle='rgba('+(p.sp>0.9?'129,140,248':'125,211,252')+','+(0.4+e*0.55)+')';
        ctx.beginPath(); ctx.arc(px,py,p.r,0,7); ctx.fill();
      }
      const cg=ctx.createRadialGradient(cx,cy,0,cx,cy,10+e*7);
      cg.addColorStop(0,'rgba(255,255,255,'+(0.9+e*0.1)+')'); cg.addColorStop(1,'rgba(56,189,248,0)');
      ctx.fillStyle=cg; ctx.beginPath(); ctx.arc(cx,cy,8+e*6,0,7); ctx.fill();
    }
    // ③ 声波雷达(脉冲波纹)
    function drawWave(ctx,cx,cy,R,e,t){
      _drawGlow(ctx,cx,cy,R,e,'56,189,248','16,185,129');
      // 向外扩散的波纹
      for(let k=0;k<4;k++){
        const phase=((t*0.6)+k/4)%1;
        const rr=R*(0.35+phase*0.9);
        const al=(1-phase)*(0.5+e*0.4);
        ctx.strokeStyle='rgba(125,211,252,'+al+')'; ctx.lineWidth=2;
        ctx.beginPath(); ctx.arc(cx,cy,rr,0,7); ctx.stroke();
      }
      const cg=ctx.createRadialGradient(cx,cy,0,cx,cy,12+e*8);
      cg.addColorStop(0,'rgba(255,255,255,'+(0.95+e*0.05)+')'); cg.addColorStop(1,'rgba(56,189,248,0)');
      ctx.fillStyle=cg; ctx.beginPath(); ctx.arc(cx,cy,10+e*7,0,7); ctx.fill();
    }
    // ④ 星云(粒子汇聚)
    function drawNebula(ctx,cx,cy,R,e,t,parts){
      _drawGlow(ctx,cx,cy,R,e,'129,140,248','56,189,248');
      for(const p of parts){
        const ang=p.a+t*p.sp*0.7;
        const pr=R*(0.35+e*0.6)+Math.sin(t+p.a)*8;
        const px=cx+Math.cos(ang)*pr, py=cy+Math.sin(ang)*pr;
        const rr=p.r*(1+e*0.8);
        const gg=ctx.createRadialGradient(px,py,0,px,py,rr*2.2);
        gg.addColorStop(0,'rgba('+(p.sp>0.9?'129,140,248':'125,211,252')+','+(0.5+e*0.4)+')');
        gg.addColorStop(1,'rgba(2,6,23,0)');
        ctx.fillStyle=gg; ctx.beginPath(); ctx.arc(px,py,rr*2.2,0,7); ctx.fill();
      }
      const cg=ctx.createRadialGradient(cx,cy,0,cx,cy,12+e*8);
      cg.addColorStop(0,'rgba(255,255,255,'+(0.9+e*0.1)+')'); cg.addColorStop(1,'rgba(129,140,248,0)');
      ctx.fillStyle=cg; ctx.beginPath(); ctx.arc(cx,cy,10+e*7,0,7); ctx.fill();
    }

    // ---------- 悬浮球 UI(portal 到 body) ----------
    function FloatBall(props){
      const s=useEng();
      const resizeRef=React.useRef(null);
      // ★★★ 2026-10-12 加：面板可拖拽缩放（用户需求：框固定太挤，要能拉大缩小）
      //   ★ 面板 right/bottom 定位 ⇒ 把手放【左上角】：往左拖=变宽，往上拖=变高（符合直觉）
      //   ★ 拖拽期间直接改 DOM 尺寸（不走 React 重渲染，避免卡顿）；松手才写 localStorage。
      React.useEffect(()=>{
        const el=resizeRef.current; if(!el) return;
        const panelEl=()=>el.parentElement;   // 把手是面板的第一个子元素
        let on=false, sx=0, sy=0, sw=0, sh=0;
        const down=(e)=>{ const p=panelEl(); if(!p) return;
          on=true; sx=e.clientX; sy=e.clientY; sw=p.offsetWidth; sh=p.offsetHeight;
          e.preventDefault(); e.stopPropagation(); };
        const move=(e)=>{ if(!on) return; const p=panelEl(); if(!p) return;
          const w=Math.max(260, Math.min(Math.round(window.innerWidth*0.92), sw+(sx-e.clientX)));
          const h=Math.max(200, Math.min(Math.round(window.innerHeight*0.88), sh+(sy-e.clientY)));
          p.style.width=w+'px'; p.style.height=h+'px'; p.style.maxHeight='88vh';
          e.preventDefault(); };
        const up=()=>{ if(!on) return; on=false; const p=panelEl(); if(!p) return;
          try{ localStorage.setItem('cldvoice_panel_w', String(p.offsetWidth));
            localStorage.setItem('cldvoice_panel_h', String(p.offsetHeight)); }catch(e){} };
        el.addEventListener('mousedown',down);
        document.addEventListener('mousemove',move);
        document.addEventListener('mouseup',up);
        return ()=>{ el.removeEventListener('mousedown',down);
          document.removeEventListener('mousemove',move);
          document.removeEventListener('mouseup',up); };
      },[s.open]);   // ★★★ 必须依赖 s.open：面板是条件渲染的，
      //   首次渲染时 s.open=false ⇒ 把手不在 DOM ⇒ resizeRef.current 为 null ⇒ 提前 return。
      //   若依赖是 []，effect 永不重跑 ⇒ 监听器从未注册 ⇒ 用户拖拽【没反应】（实测现象）。
      // ★ 把手要【看得出可以拖】—— 只放一块渐变没人会去拖它。
      //   ⇒ 三段斜线（常见的 resize 视觉语汇）+ hover 变亮 + 大一点的命中区。
      const resizeGrip=React.createElement('div',{
        ref:resizeRef,
        title:'↖ 拖拽调整面板大小（往左拖变宽 · 往上拖变高）',
        style:{position:'absolute',left:0,top:0,width:22,height:22,cursor:'nwse-resize',
          zIndex:6,borderTopLeftRadius:12,display:'flex',alignItems:'flex-start',
          justifyContent:'flex-start',padding:'3px 0 0 3px',boxSizing:'border-box',
          background:'rgba(51,65,85,.55)'},
        onMouseEnter:(e)=>{ e.currentTarget.style.background='rgba(14,165,233,.55)'; },
        onMouseLeave:(e)=>{ e.currentTarget.style.background='rgba(51,65,85,.55)'; },
        onClick:(e)=>e.stopPropagation()},
        // 三段斜线（纯 CSS，无图片）
        React.createElement('div',{style:{display:'flex',flexDirection:'column',gap:2}},
          [0,1,2].map(function(n){
            return React.createElement('div',{key:n,style:{width:3+n*4,height:2,
              background:'#94a3b8',borderRadius:1}});
          })));
      const dragRef=React.useRef(null);
      const movedRef=React.useRef(false);
      // 挂载时同步已存音量到面板(播放时已在 ensurePlay 应用)
      React.useEffect(()=>{ try{ if(localStorage.getItem('cldvoice_play_volume')) setEng({volume:parseFloat(localStorage.getItem('cldvoice_play_volume'))}); }catch(e){} },[]);
      // 挂载时同步已存语音包 + 拉取可选包清单(v0.5.0)
      React.useEffect(()=>{
        try{ const p=localStorage.getItem('cldvoice_voice_pack'); if(p){ voicePack=p; } }catch(e){}
        setEng({pack:voicePack});
        loadPacks();
      },[]);
      React.useEffect(()=>{
        const el=dragRef.current; if(!el) return;
        let dragging=false, ox=0, oy=0, sx=0, sy=0;
        const down=(e)=>{ dragging=true; movedRef.current=false; ox=e.clientX-el.offsetLeft; oy=e.clientY-el.offsetTop; sx=e.clientX; sy=e.clientY; e.preventDefault&&e.preventDefault(); };
        const move=(e)=>{ if(!dragging)return; if(Math.abs(e.clientX-sx)>4||Math.abs(e.clientY-sy)>4) movedRef.current=true; el.style.left=(e.clientX-ox)+'px'; el.style.top=(e.clientY-oy)+'px'; el.style.right='auto'; el.style.bottom='auto'; };
        const up=()=>{ dragging=false; };
        el.addEventListener('mousedown',down);
        document.addEventListener('mousemove',move);
        document.addEventListener('mouseup',up);
        return ()=>{ el.removeEventListener('mousedown',down); document.removeEventListener('mousemove',move); document.removeEventListener('mouseup',up); };
      },[]);

      const ballStyle={position:'fixed',right:26,bottom:96,width:50,height:50,borderRadius:'50%',
        background:s.rec?'#ef4444':'linear-gradient(135deg,#10b981,#0ea5e9)',
        color:'#fff',display:'flex',alignItems:'center',justifyContent:'center',fontSize:22,
        cursor:'grab',boxShadow:'0 4px 16px rgba(0,0,0,.4)',zIndex:2147483646,userSelect:'none',
        transition:'background .2s, transform .15s'};

      const dotC=s.aiTalking?'#a78bfa':(s.listening?'#34d399':'#94a3b8');
      const rows=(s.rows||[]).map((x,i)=>React.createElement('div',{key:i,style:{margin:'4px 0'}},
        React.createElement('b',{style:{color:x.role==='user'?'#38bdf8':'#a78bfa'}},x.role==='user'?'你:':'AI:'),
        React.createElement('span',{style:{marginLeft:5}},x.text)));
      const liveEl=s.live?React.createElement('div',{style:{color:'#34d399',margin:'4px 0'}},'▍'+s.live):null;
      const aiLiveEl=s.aiLive?React.createElement('div',{style:{color:'#a78bfa',margin:'4px 0',whiteSpace:'pre-wrap'}},'AI: '+s.aiLive):null;
      // ★ 中性状态行（v0.8.0）：自动重连这类【正常自愈过程】不该用报错样式显示。
      //   err 是红的(#f87171)+⚠️，用来报故障；note 用灰蓝、无警告图标，用来报「正在做的事」。
      const noteEl=s.note?React.createElement('div',{style:{color:'#94a3b8',marginTop:4}},'· '+s.note):null;
      const errEl=s.err?React.createElement('div',{style:{color:'#f87171',marginTop:4}},'⚠️ '+s.err):null;

      // ★★★ 2026-10-12 改（用户需求：「点开麦克风之后的框是固定的非常挤，要让点开后的那个框可以允许用户自定义拉大缩小」）：
      //   原为 width:330 / maxHeight:340 写死 ⇒ 内容变多后很挤。
      //   ⇒ 宽高改为读【上次拖拽后记忆的值】，未设过则用默认。
      const _pw=(()=>{try{const v=parseInt(localStorage.getItem('cldvoice_panel_w')||'',10);return (v&&v>=260&&v<=2000)?v:330;}catch(e){return 330;}})();
      const _ph=(()=>{try{const v=parseInt(localStorage.getItem('cldvoice_panel_h')||'',10);return (v&&v>=200&&v<=1600)?v:340;}catch(e){return 340;}})();
      const panelStyle={position:'fixed',right:26,bottom:158,width:_pw,height:_ph,maxWidth:'92vw',maxHeight:'88vh',
        background:'#0f172a',border:'1px solid #1e293b',borderRadius:12,color:'#cbd5e1',fontSize:13,
        boxShadow:'0 12px 40px rgba(0,0,0,.55)',zIndex:2147483645,display:'flex',flexDirection:'column',overflow:'hidden'};

      // ★★★ 2026-10-12 加（用户实测原话：「那个进入对话态的交互还是没有改进，
      //   我都不知道什么时候可以说话什么时候说话没用」）：
      //   ★ 原状态提示全在【面板最底部】，且只是【按钮变色】⇒ 用户看不出「此刻能不能说话」。
      //   ⇒ 加【顶部常驻状态条】：圆点 + 一句话，直接回答「现在能不能说」。
      const talkState = s.rec
        ? {dot:'#ef4444', bg:'rgba(239,68,68,.16)', text:'正在听你说话 —— 说完点下面的「⏹ 停止」'}
        : (s.talk
          ? {dot:'#22c55e', bg:'rgba(34,197,94,.16)', text:'现在可以说话 —— 点下面「🎙 说话」开始 · 发给「'+String(s.talk).slice(0,16)+'」'}
          : {dot:'#64748b', bg:'rgba(100,116,139,.12)', text:'未在对话态 —— 此时说话不会发出去 · 点下面「💬 进入对话态」'});
      const stateBar = React.createElement('div',{
        style:{padding:'6px 12px',background:talkState.bg,borderBottom:'1px solid #1e293b',
          color:'#e2e8f0',fontSize:11.5,fontWeight:600,display:'flex',alignItems:'center',gap:7},
        onClick:(e)=>e.stopPropagation()},
        React.createElement('span',{style:{width:8,height:8,borderRadius:4,background:talkState.dot,flexShrink:0}}),
        React.createElement('span',{},talkState.text));
      const head=React.createElement('div',{style:{padding:'8px 12px',background:'#111c2e',borderBottom:'1px solid #1e293b',display:'flex',alignItems:'center',gap:8,fontWeight:600,color:'#6ea8ff'}},
        React.createElement('span',{},'🎙 语音会议记录'),
        (s.rows&&s.rows.length)?React.createElement('span',{style:{color:'#475569',fontSize:10,fontWeight:400}},(s.rows.length+' 条')):null,
        React.createElement('span',{style:{flex:1}}),
        React.createElement('button',{
          title:'★ 清屏 = 结束本轮：① 先把当前成稿【自动归档】到历史（可在 8902/drafts 翻查）② 清空讨论 ③ 清空底稿 ⇒ 下一轮从零起稿，不再与上一轮混淆。★ 若只想【丢弃】这份成稿而不归档，用旁边的「🧽 清成稿」',
          onClick:(e)=>{ e.stopPropagation(); armClear(); },
          style:{border:'1px solid '+(s.clearArm?'#ef4444':'#1e293b'),
            background:(s.clearArm?'#7f1d1d':'transparent'),
            color:(s.clearArm?'#fecaca':'#94a3b8'),
            fontSize:11,fontWeight:400,cursor:'pointer',borderRadius:5,padding:'3px 7px',whiteSpace:'nowrap'}},
          s.clearArm?'确认清空?':'🧹 清屏'),
        React.createElement('button',{onClick:()=>setEng({open:false}),style:{border:'none',background:'none',color:'#64748b',fontSize:16,cursor:'pointer'}},'✕'));
      // 语音包选择器：只有多于 1 个包时才显示（避免"只有一个选项"的无效 UI）
      const _packOpts=(s.packs&&s.packs.length?s.packs:packList);
      const packRow=_packOpts.length>1?React.createElement('div',{style:{display:'flex',gap:8,marginTop:6,alignItems:'center'}},
        React.createElement('span',{style:{color:'#64748b',fontSize:11,whiteSpace:'nowrap'}},'🗣 语音包:'),
        React.createElement('select',{
          value:s.pack||voicePack,
          title:'切换语音包（音色+方言）。语音包在建会话时生效，切换后需重新点 ● 说话。',
          onClick:(e)=>e.stopPropagation(),
          onChange:(e)=>{e.stopPropagation(); setVoicePack(e.target.value);},
          style:{flex:1,background:'#111c2e',color:'#cbd5e1',border:'1px solid #1e293b',borderRadius:6,padding:'3px 6px',fontSize:11,cursor:'pointer'}},
          _packOpts.map(p=>React.createElement('option',{key:p.id,value:p.id},
            p.name+(p.desc?(' — '+p.desc):'')))),
        s.packNote?React.createElement('span',{style:{color:'#34d399',fontSize:10,whiteSpace:'nowrap'}},s.packNote):null):null;
      const packHint=_packOpts.length>1?React.createElement('div',{style:{color:'#475569',fontSize:10,marginTop:3}},
        '语音包含音色+方言。切换后需重新点 ● 说话 才生效。'):null;
      // 成稿区（2026-10-10）：成稿不再直接发出去，而是停在这里让你看、改、再采用
      const draftArea=(s.draftText||s.draftBusy)?React.createElement('div',{style:{marginTop:8,borderTop:'1px solid #1e293b',paddingTop:8}},
        React.createElement('div',{style:{display:'flex',alignItems:'center',gap:6,marginBottom:4}},
          React.createElement('span',{style:{color:'#f5b942',fontWeight:600,fontSize:12}},'📄 成稿（可直接编辑）'),
          React.createElement('span',{style:{flex:1}}),
          s.draftPrev?React.createElement('button',{title:'回退到修订前的上一版',onClick:(e)=>{e.stopPropagation(); revertDraft();},
            style:{border:'1px solid #334155',background:'#111c2e',color:'#94a3b8',borderRadius:6,padding:'2px 8px',fontSize:11,cursor:'pointer'}},'↩ 上一版'):null),
        React.createElement('textarea',{value:s.draftText||'',onClick:(e)=>e.stopPropagation(),
          onChange:(e)=>{e.stopPropagation(); setEng({draftText:e.target.value});},
          rows:7,placeholder:'成稿会出现在这里；可继续 ● 说话提意见后点 🔄 重出稿…',
          style:{width:'100%',boxSizing:'border-box',background:'#0b1220',color:'#e2e8f0',border:'1px solid #1e293b',borderRadius:6,padding:'6px 8px',fontSize:11,lineHeight:1.55,resize:'vertical',fontFamily:'ui-monospace,SFMono-Regular,Menlo,monospace'}}),
        s.draftNote?React.createElement('div',{style:{color:'#7dd3fc',fontSize:10,marginTop:3}},'ℹ '+s.draftNote):null):null;
      const body=React.createElement('div',{style:{padding:'10px 12px',overflowY:'auto'}},
        React.createElement('div',{style:{display:'flex',alignItems:'center',gap:6,marginBottom:8,color:'#94a3b8',fontSize:12}},
          React.createElement('span',{style:{width:8,height:8,borderRadius:4,background:dotC,display:'inline-block'}}),
          React.createElement('span',{}, (s.aiTalking?'AI 回答中…':(s.listening?'● 聆听…':'点 ● 说话 → ✅ 成稿 → 可改可续聊 → 📋 采用'))),
          React.createElement('span',{style:{flex:1}}),
          s.playing?React.createElement('span',{style:{color:'#34d399',fontWeight:700}},'🔊'):(s.aud?React.createElement('span',{style:{color:'#f5b942'}},'⏳'):null)),
        s.rows&&s.rows.length?rows:React.createElement('div',{style:{color:'#64748b',fontSize:12}},'还没有对话, 点 ● 开始说需求'),
        liveEl, aiLiveEl, noteEl, errEl,
        React.createElement('div',{style:{marginTop:6,padding:'5px 8px',background:'#111c2e',borderRadius:6,color:'#7dd3fc',fontSize:11,fontFamily:'monospace'}},
          '🔊 音频: 收 '+(audDbg.rx/1024).toFixed(0)+'KB / 播 '+audDbg.played+' 次 / ctx '+((playCtx&&playCtx.state)||'未建')+
          (audDbg.err?(' / ⚠ '+audDbg.err):'')),
        React.createElement('div',{style:{display:'flex',gap:6,marginTop:6,flexWrap:'wrap',alignItems:'center'}},
          React.createElement('span',{style:{color:'#64748b',fontSize:11}},'球样式:'),
          ORB_STYLES.map(st=>React.createElement('button',{key:st.id,title:st.hint,
            onClick:(e)=>{e.stopPropagation(); setOrbStyle(st.id);},
            style:{border:'1px solid '+(s.orbStyle===st.id?'#38bdf8':'#1e293b'),background:(s.orbStyle===st.id?'#0ea5e9':'#111c2e'),color:(s.orbStyle===st.id?'#fff':'#94a3b8'),borderRadius:6,padding:'3px 8px',fontSize:11,cursor:'pointer'}},st.label))),
        React.createElement('div',{style:{display:'flex',gap:8,marginTop:6,alignItems:'center'}},
          React.createElement('span',{style:{color:'#64748b',fontSize:11}},'🔊 音量:'),
          React.createElement('input',{type:'range',min:0.3,max:2.5,step:0.05,value:playVolume,
            onChange:(e)=>{e.stopPropagation(); setPlayVolume(parseFloat(e.target.value));},
            style:{flex:1,accentColor:'#38bdf8',cursor:'ew-resize'}}),
          React.createElement('span',{style:{color:'#94a3b8',fontSize:11,width:34,textAlign:'right'}},Math.round(playVolume*100)+'%')),
        packRow,
        packHint,
        draftArea);
      const foot=React.createElement('div',{style:{padding:'8px 12px',borderTop:'1px solid #1e293b'}},
        React.createElement('div',{style:{display:'flex',gap:8}},
          React.createElement('button',{onClick:()=>toggleRec(),style:{flex:1,border:'none',borderRadius:6,padding:'7px 0',background:s.rec?'#ef4444':(s.talk?'#0ea5e9':'#10b981'),color:'#fff',cursor:'pointer',fontWeight:600}},
            // ★★★ 2026-10-12 修（用户实测原话：「进入对话态之后我没有交互按钮，也不知道我应该怎么样唤醒」）：
            //   ● 按钮一直存在，但在面板最底部，且文案不体现对话态 ⇒ 用户看不出该按哪里说话。
            //   ⇒ 对话态下：按钮变蓝 + 文案写明「发给谁」。
            s.rec?'⏹ 停止':(s.talk?('🎙 说话 → 发给「'+String(s.talk).slice(0,14)+'」'):'● 说话')),
          React.createElement('button',{title:'用当前讨论出稿；若已有成稿，则按其底稿做增量修订（只改你提到的部分，不覆盖）',
            onClick:()=>makeDraft(),disabled:!!s.draftBusy,
            style:{flex:1,border:'none',borderRadius:6,padding:'7px 0',background:s.draftBusy?'#475569':'#f5b942',color:'#0f172a',cursor:s.draftBusy?'default':'pointer',fontWeight:600}},
            s.draftBusy?'… 处理中':(s.draftText?'🔄 重出稿':'✅ 成稿')),
          // ★ 独立清成稿（用户实测诉求：成稿没有清理的地方）
          s.draftText?React.createElement('button',{type:'button',
            title:'清空当前成稿。★ 只清成稿、不动讨论记录 —— 下一轮将从零起稿，不再把旧成稿当底稿（否则两轮成稿会互相混淆）',
            onClick:(e)=>{e.stopPropagation(); clearDraft();},
            style:{flex:'none',background:'transparent',border:'1px solid #475569',borderRadius:6,padding:'7px 10px',color:'#94a3b8',cursor:'pointer',fontSize:12}},
            '🧽 清成稿'):null,
          React.createElement('button',{title:'把成稿区里（你改过的）文本填入输入框；是否自动发送见下方开关',
            onClick:()=>applyDraft(props.inputActions),
            style:{flex:1,border:'none',borderRadius:6,padding:'7px 0',background:'#38bdf8',color:'#0f172a',cursor:'pointer',fontWeight:600}},'📋 采用')),
        // ★ C（用户指定）：显式进出对话态。B（说「发给X」自动进）= 上面 sendToNamedSession 里那处。
        React.createElement('div',{style:{display:'flex',gap:6,marginTop:6,alignItems:'center'}},
          React.createElement('button',{title:'对话态：进入后直接说话即发给该会话，回话自动念出；说「结束对话」或再点此退出',
            onClick:(e)=>{e.stopPropagation();
              if(s.talk){ exitTalk('已退出对话态'); return; }
              if(s.talkAsk){ talkAsk=false; setEng({talkAsk:false}); return; }
              loadTalkCandidates();
            },
            style:{flex:1,border:'1px solid '+(s.talk?'#34d399':'#334155'),borderRadius:6,padding:'7px 0',background:s.talk?'rgba(52,211,153,.22)':'transparent',color:s.talk?'#a7f3d0':'#cbd5e1',cursor:'pointer',fontSize:12}},
            s.talk?('★ 对话中：'+s.talk+'（点此退出）'):'💬 进入对话态'),
          React.createElement('span',{style:{color:'#475569',fontSize:10}},
            s.talk?'直接说话即发给它 · 说「结束对话」退出':'进入后不必每次说「发给 X」')),
        // ★ C 的内联输入行（不用 window.prompt —— Electron renderer 不实现它，调用返回 undefined ⇒ 点了没反应）
        TalkPicker(s),
        React.createElement('div',{style:{display:'flex',alignItems:'center',gap:6,marginTop:6}},
          React.createElement('label',{style:{display:'flex',alignItems:'center',gap:5,color:'#94a3b8',fontSize:11,cursor:'pointer'},
            onClick:(e)=>e.stopPropagation()},
            React.createElement('input',{type:'checkbox',checked:!!s.autoSend,onChange:()=>toggleAutoSend(),style:{cursor:'pointer'}}),
            '填入后自动发送'),
          React.createElement('span',{style:{flex:1}}),
          React.createElement('span',{style:{color:'#475569',fontSize:10}},
            s.autoSend?'（关掉即可在发送前修改）':'（默认：只填入，由你发送）')));

      const panel=React.createElement('div',{style:panelStyle},resizeGrip,head,stateBar,body,foot);
      const ball=React.createElement('div',{ref:dragRef,title:'语音会议记录',style:ballStyle,
        onClick:(e)=>{ if(e.detail>1)return; if(movedRef.current){ movedRef.current=false; return; } setEng({open:!s.open}); }},'🎤');

      const ui=React.createElement(React.Fragment,null,
        ball,
        s.open?panel:null,
        s.rec?React.createElement(VisualOrb,null):null);
      if(ReactDOM&&ReactDOM.createPortal) return ReactDOM.createPortal(ui, document.body);
      // 降级: 直接内联挂载(仍 fixed)
      return ui;
    }

    function safeReg(slots,opts,comp){ try{return slots.register(opts,comp);}catch(e){console.error('cldvoice reg fail',e);return()=>{};} }

    module.exports={
      inject:['slots'],
      apply(ctx){
        // ★ 启动回话播报轮询（游标在模块加载时已设为当时刻 ⇒ 不会播历史积压）
        // ★ 2026-10-10 隔离：回话轮询【默认不启动】。用户报告「几个入口都听不到我说话、没有收音反馈」，
        //   而它是本轮唯一新增的后台音频行为（8s 轮询 + 命中即 ensurePlay/playAi/flushAi 播放）。
        //   按科学方法先摘掉这个变量再测：确认收音恢复 ⇒ 元凶是它；仍不正常 ⇒ 与它无关，回头再查。
        // ★ 2026-10-10 开回：隔离已出结论 —— 收音中断的根因是【USB 麦克风输出数字静音】
        //   （captured_frames=192000 一帧不差但 rms=0/peak=0/zero_ratio=1.0），用户拔插后恢复，
        //   与本轮询无关。⇒ 恢复启动。且播放上下文改用系统默认速率（见 ensurePlay），
        //   不再制造「与麦克风 48kHz 并存的两个不同采样率上下文」这一条件。
        startReplyPolling();
        const registerSlots=(scope)=>{
          const slots=scope&&scope.slots?scope.slots:(ctx.slots||null);
          if(!slots) return;
          ctx.effect(()=>safeReg(slots,{name:'conversation.input.right',id:'cldvoice-floatball',order:62,label:'语音会议记录'},FloatBall),'cldvoice: floatball');
        };
        if(typeof ctx.inject==='function'){
          ctx.effect(()=>ctx.inject(['slots'],(scope)=>{ registerSlots(scope); }),'cldvoice: inject-slots');
        } else registerSlots(ctx);
        // 全局一次性手势: 任意点击/按键都尝试解锁 AudioContext(兜底 autoplay)
        this._unlock=()=>{ _primeAudio(); };
        if(typeof document!=='undefined') document.addEventListener('pointerdown',this._unlock,{once:true});
        return ()=>{ stopAudio(); if(typeof document!=='undefined'&&this._unlock) document.removeEventListener('pointerdown',this._unlock); };
      }
    };
    return module.exports;
  },
});
