# dsh-pet 插件定制与彻底禁用实录（2026-08-16，session-75815fa9 提供）

> 来源：DSH GUI「电子宠物」定制会话。可复用于 DSH web 插件运维/排查。

## 背景
GUI（CLD 内的 dsh web）有一只 `@linxin666/dsh-pet` 浮游宠物（鲸鱼娘 whale-girl），来自 web-ui-all 全家桶。本会话完成了：图形替换（正脸骆驼）、改名（驼哥）、文案骆驼化，最终按用户要求**彻底禁用**（enabled:false，连召唤按钮一起消失，非仅隐藏）。

## 关键机制（可复用的运维知识）
1. **客户端插件代码实时读盘**：浏览器加载的 `/plugins/<pkg>/client.js` 按请求从 `~/.dsh/profiles/web/node_modules/<pkg>/lib/client.js` 读取，响应头 `cache-control: no-cache` —— 改文件刷新页面即生效，**无需重启**。
2. **启动清单 rev 是实时 sha1 前缀**：页面 `window.__DSH_BOOT__` 的 entries[].rev 每请求按当前文件内容重算（sha1 前 12 位），不是启动时固定。
3. **settings.yaml 被 chokidar 热监听**（`dsh-settings-file`，`watch: true`，debounce 100ms）：直接改 `~/.dsh/settings.yaml` 会被运行中服务热加载 → 插件 `onChange` 触发 → `setEnabled(false)` + 移除 `/api/pet/*` 路由 + 客户端 `syncUi()` 卸载宠物 UI（**无需刷新即可让已开页面移除**）。验证：改后 `/api/pet/*` 全部 404。
4. **隐藏 ≠ 禁用**：`visible:false` 只隐藏角色，仍会渲染「召唤」按钮（残留来源）；要无残留需 `enabled:false`。
5. 宠物状态双写：`~/.dsh/pet.json`（持久化：名字/亲密度/display）+ settings.yaml `pet:` 段（设置文档）。API：`/api/pet/state|pets|interact|set-visible|set-config|set-name|set-pet`。
6. 宠物注册表：内置 `assets/*/pet.json` + 自定义 `~/.codex/pets/<id>/pet.json`（8列×9行 192×208 贴图契约，行序 idle/running-right/running-left/waving/jumping/failed/waiting/running/review，帧数 [6,8,8,4,5,8,6,6,6]）。注册表**启动时构建**，新增宠物需重启。

## 资产备份（可恢复/复用）
- `~/.dsh/pet-backup/`：`spritesheet.whale-original.webp`（原版鲸鱼）、`spritesheet.webp`（侧脸骆驼）、`spritesheet-front.webp`（正脸骆驼，当前）、`draw_front_camel.py`（PIL 生成脚本）、`build_spritesheet.py`、`camel.png`（OpenMoji 素材，CC BY-SA）。

## 文案替换点（改文件即生效的清单）
- 亲密度等级：`lib/state-CFyJv0sQ.js` + `lib/types/affinity.js`（幼鲸→幼驼、深海羁绊→沙漠羁绊）
- 互动反应：同两文件（摸头/喂食气泡台词，服务端内存，**需重启生效**）
- 零食标签：`lib/client.js` + `lib/types/client/locales.js`（小鱼干→仙人掌，客户端刷新生效）
- 默认名/介绍：`lib/index.js`、`lib/types/persist.js`、`assets/whale/pet.json`

## 教训
- 服务端内存中的文案（applyInteraction 反应、等级名）改文件**不会热生效**，需重启 CLD（会话存 `~/.dsh/sessions` 不丢）。
- 客户端文案/贴图改完刷新即生效（no-cache + 实时读盘）。
