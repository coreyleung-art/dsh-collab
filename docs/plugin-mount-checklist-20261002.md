# 插件挂载三要素 Checklist（2026-10-02 两次启动崩溃的教训）

> 背景：4 个新工具挂载导致 CLD 启动崩溃**两次**，分别命中两个独立 bug + 一个解析缺口。
> 本清单 = 新插件挂载进 profile 前必须逐项核验的三要素（对照生产基准 dsh-plugin-guard）。

## 三要素

| # | 要素 | 崩溃证据 | 正确形态（guard 同款） |
|---|---|---|---|
| 1 | `cordis.patch.yml` 的 `name` = **完整包名** | 崩溃#1：ERR_MODULE_NOT_FOUND（短名当模块说明符解析） | `name: dsh-plugin-<x>`（id 可任意唯一） |
| 2 | `lib/index.js` 用 **defineTool 契约** | 崩溃#1：TypeError output 缺 render | `defineTool({ name, description, parameters, output: makeOutput(), execute })` + `ctx.effect(() => ctx.tools.register(tool))`；`makeOutput()` = `{ schema: {type:'json'}, render: (_a,v)=>[{type:'text', text: JSON.stringify(v,null,2)}] }` |
| 3 | 插件目录 `node_modules/@deepseek-ai/dsh-tools` = **symlink → `~/.dsh/profiles/node_modules/@deepseek-ai/dsh-tools`**（+ cordis 同款） | 崩溃#2：宿主 loader 从插件 realpath 解析 peer，目录无 node_modules 链则 ERR_MODULE_NOT_FOUND | `ln -s ~/.dsh/profiles/node_modules/@deepseek-ai/dsh-tools <plugin>/node_modules/@deepseek-ai/dsh-tools` |

## 挂载前验证命令（全部通过才进 bundles）

```bash
# 1) patch name 完整包名
grep "name:" <plugin>/cordis.patch.yml   # 必须 = 完整包名 dsh-plugin-<x>
# 2) 契约冒烟（真 dsh-tools 环境，symlink 在位的状态下跑）
cd ~/.dsh/profiles/web && node --input-type=module -e "
const mod = await import('<pkg>/lib/index.js');
const r = []; mod.apply({tools:{register:(d)=>r.push(d)},effect:(f)=>f()},{});
const d = r[0];
console.assert(r.length===1 && typeof d.execute==='function' && d.output.schema!==undefined && typeof d.output.render==='function', '契约不符');
console.log('✓ 契约冒烟通过');
"
# 3) dump-config 无告警
node /Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh/lib/bin.js --profile web --dump-config 2>&1 | grep -ciE 'error|not found'  # 必须 0
```

## 反例（本事故踩过的）

- 自编桩 ctx `register:(name, def)` 假契约 → 冒烟假绿放过了违规（崩溃#1 未被预检拦下的根因）。
- 验证时建**临时** symlink 跑通后删除 → 真实宿主仍然解析不到（崩溃#2）——symlink 是运行时依赖，必须常驻。
- `--dump-config` 不执行插件代码，它绿 ≠ 能加载（两次崩溃前它都绿）。

## 教训一句话

**挂载验证的黄金标准 = 与生产基准逐项同构 + 真 dsh-tools 环境执行 apply**；任何「看起来等价」的自造替代（假桩、临时解析）都会假绿。
