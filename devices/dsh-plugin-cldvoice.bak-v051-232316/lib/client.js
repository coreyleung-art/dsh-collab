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
    let eng = { open:false, rec:false, listening:false, aiTalking:false, live:'', aiLive:'', rows:[], err:null, aud:false, playing:false, errWin:'', orbStyle:'nebula', volume:1.35, pack:'zh', packs:[], clearArm:false };
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
    let packList=[{id:'zh',name:'国语·灿灿',desc:'标准普通话（默认）',dialect:'普通话'},
                  {id:'yue',name:'粤语·灿灿',desc:'地道粤语口语',dialect:'yue'}];
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
      setEng({rows:[], live:'', aiLive:'', aiTalking:false, clearArm:false});
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
        try{ playCtx=new AudioContext({sampleRate:24000}); }
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
      aiSamples=[]; aiBuf='';
    }
    function startMic(cb){
      // 真正保障在 toggleRec 同步调用 ensurePlay(手势解锁)
      // 用硬件回声消除(echoCancellation)替代手工 micOff 送静音: 后者会干扰模型对用户语音的感知
      return navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation:true, noiseSuppression:true, autoGainControl:true }
      }).then(st=>{
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
        else if(d.type==='audio_delta'){ eng.aiTalking=true; playAi(d.audio); }
        else if(d.type==='audio_done'){ flushAi(); setEng({aiTalking:false,listening:true}); }
        else if(d.type==='done'){
          flushAi();
          const rows=eng.rows;
          if(userFinal.trim()) rows.push({role:'user',text:userFinal.trim()});
          if(eng.aiLive.trim()) rows.push({role:'ai',text:eng.aiLive.trim()});
          setEng({rows, live:'', aiLive:'', aiTalking:false, listening:true});
          userFinal='';
        } else if(d.type==='err'){ setEng({err:d.msg, rec:false}); }
      }catch(e){ audDbg.err='onmsg:'+String((e&&e.message)||e); }
    }
    function toggleRec(){
      // 必须在用户手势(点●)内同步 create+resume playCtx, 否则 Chromium autoplay 把它挂起 → 无声
      ensurePlay();
      if(eng.rec){ // 停止并触发 AI 收尾
        if(ws&&ws.readyState===1){ try{ws.send(JSON.stringify({type:'commit'}));}catch(e){} }
        stopAudio();
        setTimeout(()=>{try{ws&&ws.close();}catch(e){} ws=null; setEng({rec:false,listening:false,aiTalking:false});},1200);
        return;
      }
      setEng({rec:true,listening:false,err:null});
      try{ ws=new WebSocket(bridgeUrl()); }catch(e){ setEng({err:'桥连接失败',rec:false}); return; }
      ws.binaryType='arraybuffer';
      ws.onmessage=onBridgeMsg;
      ws.onerror=()=>setEng({err:'无法连接语音桥(8905)',rec:false});
      ws.onopen=()=>{
        startMic(buf=>{ if(ws&&ws.readyState===1){ try{ws.send(buf);}catch(e){} } })
          .then(()=>setEng({listening:true}))
          .catch(e=>setEng({err:'麦克风:'+String(e.message||e),rec:false}));
      };
    }

    // 成稿 → 注入 CLD 当前会话输入框并发送
    function completeInject(inputActions){
      setEng({err:null});
      // 关键: 带上 role(user/ai), 否则成稿引擎无法区分用户与 AI → 需求提炼乱/留痕无角色
      const disc=eng.rows.map(x=>({role:x.role==='user'?'user':'ai',ts:new Date().toISOString().slice(11,19),text:x.text}));
      if(!disc.length){ setEng({err:'还没有对话内容'}); return; }
      const origin=(typeof location!=='undefined'&&location.origin)||'?';
      audDbg.err='注入@'+origin+': '+disc.length+'条'; setEng({errWin:audDbg.err});
      fetch('/voice/draft',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({discussion:disc,title:'语音会议记录'})})
        .then(r=>r.json()).then(d=>{
          audDbg.err='draft ok='+!!d.ok+' contentLen='+((d.content||'').length);
          if(d.ok&&d.content){
            if(inputActions&&inputActions.setDraft){
              audDbg.err+=' 注入前'+((d.content||'').slice(0,40).replace(/\n/g,' '));
              inputActions.setDraft('【语音会议记录】\n'+d.content.slice(0,3000));
              setTimeout(()=>{ try{inputActions.submit();}catch(e){} },300);
            } else { audDbg.err+=' 无setDraft'; }
            setEng({rows:[],open:false});
          } else { audDbg.err+=' 无content'; setEng({err:'成稿失败:'+(d.error||'')}); }
          setEng({errWin:audDbg.err});
        }).catch(e=>{ audDbg.err='draft错:'+String(e.message||e); setEng({err:'成稿错误:'+String(e.message||e),errWin:audDbg.err}); });
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
      const errEl=s.err?React.createElement('div',{style:{color:'#f87171',marginTop:4}},'⚠️ '+s.err):null;

      const panelStyle={position:'fixed',right:26,bottom:158,width:330,maxWidth:'92vw',maxHeight:340,
        background:'#0f172a',border:'1px solid #1e293b',borderRadius:12,color:'#cbd5e1',fontSize:13,
        boxShadow:'0 12px 40px rgba(0,0,0,.55)',zIndex:2147483645,display:'flex',flexDirection:'column',overflow:'hidden'};

      const head=React.createElement('div',{style:{padding:'8px 12px',background:'#111c2e',borderBottom:'1px solid #1e293b',display:'flex',alignItems:'center',gap:8,fontWeight:600,color:'#6ea8ff'}},
        React.createElement('span',{},'🎙 语音会议记录'),
        (s.rows&&s.rows.length)?React.createElement('span',{style:{color:'#475569',fontSize:10,fontWeight:400}},(s.rows.length+' 条')):null,
        React.createElement('span',{style:{flex:1}}),
        React.createElement('button',{
          title:'清空面板里的历史记录（只清显示内容；已注入到会话的成稿不受影响）',
          onClick:(e)=>{ e.stopPropagation(); armClear(); },
          style:{border:'1px solid '+(s.clearArm?'#ef4444':'#1e293b'),
            background:(s.clearArm?'#7f1d1d':'transparent'),
            color:(s.clearArm?'#fecaca':'#94a3b8'),
            fontSize:11,fontWeight:400,cursor:'pointer',borderRadius:5,padding:'3px 7px',whiteSpace:'nowrap'}},
          s.clearArm?'确认清空?':'🧹 清屏'),
        React.createElement('button',{onClick:()=>setEng({open:false}),style:{border:'none',background:'none',color:'#64748b',fontSize:16,cursor:'pointer'}},'✕'));
      const body=React.createElement('div',{style:{padding:'10px 12px',overflowY:'auto'}},
        React.createElement('div',{style:{display:'flex',alignItems:'center',gap:6,marginBottom:8,color:'#94a3b8',fontSize:12}},
          React.createElement('span',{style:{width:8,height:8,borderRadius:4,background:dotC,display:'inline-block'}}),
          React.createElement('span',{}, (s.aiTalking?'AI 回答中…':(s.listening?'● 聆听…':'点 ● 说话, 👉 说完点 ✅ 完成注入'))),
          React.createElement('span',{style:{flex:1}}),
          s.playing?React.createElement('span',{style:{color:'#34d399',fontWeight:700}},'🔊'):(s.aud?React.createElement('span',{style:{color:'#f5b942'}},'⏳'):null)),
        s.rows&&s.rows.length?rows:React.createElement('div',{style:{color:'#64748b',fontSize:12}},'还没有对话, 点 ● 开始说需求'),
        liveEl, aiLiveEl, errEl,
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
        React.createElement('div',{style:{display:'flex',gap:8,marginTop:6,alignItems:'center'}},
          React.createElement('span',{style:{color:'#64748b',fontSize:11,whiteSpace:'nowrap'}},'🗣 语音包:'),
          React.createElement('select',{
            value:s.pack||voicePack,
            title:'切换语音包（音色+方言）。语音包在建会话时生效，切换后需重新点 ● 说话。',
            onClick:(e)=>e.stopPropagation(),
            onChange:(e)=>{e.stopPropagation(); setVoicePack(e.target.value);},
            style:{flex:1,background:'#111c2e',color:'#cbd5e1',border:'1px solid #1e293b',borderRadius:6,padding:'3px 6px',fontSize:11,cursor:'pointer'}},
            (s.packs&&s.packs.length?s.packs:packList).map(p=>React.createElement('option',{key:p.id,value:p.id},
              p.name+(p.desc?(' — '+p.desc):'')))),
          s.packNote?React.createElement('span',{style:{color:'#34d399',fontSize:10,whiteSpace:'nowrap'}},s.packNote):null),
        React.createElement('div',{style:{color:'#475569',fontSize:10,marginTop:3}},
          '语音包含音色+方言（粤语/四川话/东北话/陕西话）。切换后需重新点 ● 说话 才生效。'));
      const foot=React.createElement('div',{style:{display:'flex',gap:8,padding:'8px 12px',borderTop:'1px solid #1e293b'}},
        React.createElement('button',{onClick:()=>toggleRec(),style:{flex:1,border:'none',borderRadius:6,padding:'7px 0',background:s.rec?'#ef4444':'#10b981',color:'#fff',cursor:'pointer',fontWeight:600}},
          s.rec?'⏹ 停止':'● 说话'),
        React.createElement('button',{onClick:()=>completeInject(props.inputActions),style:{flex:1,border:'none',borderRadius:6,padding:'7px 0',background:'#f5b942',color:'#0f172a',cursor:'pointer',fontWeight:600}},'✅ 完成注入'));

      const panel=React.createElement('div',{style:panelStyle},head,body,foot);
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
