# external-link-policy 封装前源码审查（七维）

- 审查人：session-0e84e65c（依赖/供应链专员）
- 对象：dsh-plugin-external-link-policy@0.1.0（~/dsh-plugin-local-projects/external-link-policy，本地 link 挂载）
- 时间：2026-08-18 · 用途：封装为 github:#commit 可分发插件包前的装前审查

---

## 一、七维审查结论

| 维度 | 结论 | 说明 |
|------|------|------|
| ① 依赖面 | 🟢 干净 | 唯一 dep = @deepseek-ai/schemastery ^3.18.1（宿主已有）；7 个 peerDeps 全部 @deepseek-ai/dsh-* rc.6（宿主提供）——无第三方运行时依赖 |
| ② channel.send 薄壳 | 🟢 安全 | POST /external-link-policy/send → execFile('curl', [固定数组参数]) → 127.0.0.1:8790/send。**数组参数无 shell 注入**；目标固定 localhost；text 截断 2000 字符；15s 超时；错误回 JSON 不崩溃 |
| ③ 引擎引用 | 🟢 合理 | 复用 external-link-mcp 引擎（webhook 8790/send），非自研发送——薄壳仅转发，分级/去重/汇总逻辑在引擎侧（单一职责正确） |
| ④ 密钥面 | 🟢 无密钥 | 全源码无 token/secret/key/password/credential 处理——凭据完全由引擎侧（~/.dsh/channels.json 0600 + keyring）管理，薄壳不接触 |
| ⑤ 高危操作 | 🟢 低危 | src：仅 execFile('curl', 固定参数)（无 shell）；scripts/build.mjs：execSync(tsc/esbuild) + rm -f lib/.client.tmp.js（构建产物清理，作用域受限） |
| ⑥ 端点暴露 | 🟡 注意 | 4 个端点挂 webServer prefix `/external-link-policy`：stats/channels/queue（只读）+ send（POST）。**send 端点无认证**——暴露面取决于 webServer 是否仅内网可达（dsh web 常规内网部署，风险可控；若未来公网暴露需加认证） |
| ⑦ 构建封装 | 🟢 标准 | build.mjs：tsc + esbuild client + __ModuleLoader__ 包装——与现有插件（voice/waimai 等）同模式；files 字段含 lib + cordis.patch.yml，可分发 |

## 二、封装建议（供用户确认执行）

1. **可封装**：工程结构完整（package.json/cordis.patch.yml/build.mjs/lib/src 齐备），零第三方依赖、无密钥面、薄壳安全——符合 github:#commit 分发条件
2. **封装前建议**：
   - a) send 端点加简单认证头（可选：token 校验或仅允许内网）——防御性加固，防未来公网暴露
   - b) README 补充安装/配置说明（当前无 README）
   - c) 版本号 0.1.0 可保留，封装时打 tag
3. **分发后**：profiles/web 的 link: 依赖切换为 github:#commit 钉死；本地开发目录保留作源仓库
4. **依赖面注意**：peerDeps 的 dsh-client-* rc.6 与宿主 runtime 一致（已核实 dsh-web-app 0.1.0-rc.6）——分发后无版本漂移风险

## 三、供应链判定

**🟢 可封装分发**（7 维中 6 绿 1 黄，黄项为可选的防御性加固非阻塞）
- 零第三方依赖 = 无供应链攻击面
- 无密钥处理 = 无凭据泄露风险
- 薄壳仅转发 = 逻辑风险集中在引擎侧（已生产运行）
- 唯一注意：send 端点认证（当前内网部署可接受，公网暴露前需加）

## 四、交接

- 审查结论已交付 b241741f，转用户确认封装执行
- 若封装执行：我配合 profiles/web 依赖切换（link: → github:#commit）+ 装后验证
