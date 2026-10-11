import fs from 'node:fs';
const P='/Users/coreyleung/dsh-plugin-agent-bus/lib/index.js';
const lines = fs.readFileSync(P,'utf8').split('\n');
let start=-1,end=-1;
for (let i=0;i<lines.length;i++){ if(lines[i].startsWith('function writeExpiredAlert')){start=i;break;} }
for (let i=start+1;i<lines.length;i++){ if(lines[i]==='}'){end=i;break;} }
if(start<0||end<0){ console.log('MISS: 未找到函数'); process.exit(1); }
const body = lines.slice(start,end+1).join('\n');
console.log('提取行号: '+(start+1)+'-'+(end+1)+' | 字节 '+body.length);

const calls=[];
const fakeFetch=(u,o)=>{ calls.push({url:u, method:o&&o.method, body:o&&o.body}); return Promise.resolve({ok:true}); };
const okProcess={env:{}};
const mk=(fetchImpl,proc)=>new Function('fetch','process', body+'\nreturn writeExpiredAlert;')(fetchImpl,proc);

const fn = mk(fakeFetch, okProcess);
fn(3,[{id:'m1'},{id:'m2'}]);
await new Promise(r=>setTimeout(r,120));

console.log('\n【测一】正常调用 count=3');
console.log('  调用次数: '+calls.length+(calls.length===1?' ✅':' ❌'));
const c=calls[0]||{};
console.log('  method: '+c.method+(c.method==='PUT'?' ✅':' ❌'));
console.log('  URL: '+c.url);
console.log('  键形正确: '+(/data\/ops\/bus-expired-alert\/\d+$/.test(c.url||'')?'✅':'❌'));
try{
  const b=JSON.parse(c.body);
  console.log('  count 字段: '+b.count+(b.count===3?' ✅':' ❌'));
  console.log('  sample 条数: '+(b.sample||[]).length+(Array.isArray(b.sample)?' ✅':' ❌'));
  console.log('  type: '+b.type);
}catch(e){ console.log('  ❌ body 解析失败: '+e.message); }

console.log('\n【测二】黑板不可达（fetch reject）');
let threw2=false;
try{ mk(()=>Promise.reject(new Error('boom')), okProcess)(1,[]); }catch(e){ threw2=true; }
console.log('  同步抛出: '+threw2+(threw2?' ❌ 应不抛':' ✅ 不阻塞主流程'));

console.log('\n【测三】fetch 不存在');
let threw3=false;
try{ mk(undefined, okProcess)(1,[]); }catch(e){ threw3=true; }
console.log('  抛出: '+threw3+(threw3?' ❌':' ✅ 恰当降级'));

console.log('\n【测四】sample 截断（传 30 条应只存 20）');
const c2=[]; const f2=(u,o)=>{c2.push(o.body);return Promise.resolve({ok:true});};
mk(f2, okProcess)(30, Array.from({length:30},(_,i)=>({id:'x'+i})));
await new Promise(r=>setTimeout(r,120));
try{ const b=JSON.parse(c2[0]); console.log('  sample 条数: '+(b.sample||[]).length+((b.sample||[]).length===20?' ✅':' ❌')); }catch(e){ console.log('  ❌ '+e.message); }
