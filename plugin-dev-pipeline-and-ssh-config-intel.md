# 插件开发链路实测参数 + dsh-ssh 配置源情报

> 来源：dsh-plugin-local-projects 会话（session-e0c391f7-25ba-47d0-8329-636177be84ea）
> 用途：① 插件热重载/验证流水线设计文档的实测输入；② sysops × dsh-ssh 单一主机配置源方案评估输入
> 落盘：2026-08-17（协调者授权后正式落盘），协作约定 v1（~/dsh-collab + 广播声明路径）

## 一、插件「改码→重建→GUI 验证」链路实测参数

### 1.1 插件项目结构（以 dsh-plugin-local-projects 为实测样本）

```
package.json          # dsh.bundle.patch + dsh.client.inject/platform 元数据
cordis.patch.yml      # 宿主注入补丁（patch.applied=true）
src/index.ts          # node 端（服务端逻辑）
src/client/index.tsx  # client 端（React UI）
scripts/build.mjs     # 构建脚本（tsc + esbuild + __ModuleLoader__.load 包装）
scripts/restart-web.sh# 一键重启 dsh web
lib/index.js          # node 端产物（tsc 输出）
lib/client.js         # client 端产物（esbuild 打包 + __ModuleLoader__.load 包装）
lib/types/client/index.d.ts  # client 类型占位
```

### 1.2 构建产物与格式（实测）

| 产物 | 生成方式 | 格式 | 关键点 |
|---|---|---|---|
| lib/index.js | npx tsc -p tsconfig.json | ESM（type: module） | node 端直接加载 |
| lib/client.js | npx esbuild src/client/index.tsx --bundle --format=cjs --platform=browser --target=es2022 --external:react --external:react/jsx-runtime --external:@deepseek-ai/* | CJS bundle | 必须用 window.__ModuleLoader__.load({id, factory}) 包装，factory 内承接 module/exports |

client 端 esbuild 关键参数：--external:react --external:react/jsx-runtime --external:@deepseek-ai/*（全部 @deepseek-ai/* 外部化）。

### 1.3 加载与生效链路

1. 宿主（CLD.app → dsh-runtime）按 cordis.patch.yml 注入插件；
2. node 端经 cordis 插件系统加载 lib/index.js；
3. client 端经 dsh.bundle.client.inject 注入 Web GUI，__ModuleLoader__.load 注册；
4. 插件生效依赖 **dsh web（GUI）重启或刷新**：
   - node 端改动 → 需重启 dsh web 进程（restart-web.sh：lsof 找 :3080 → kill → nohup dsh web → 健康检查 3080/200）；
   - client 端改动 → 需重建 lib/client.js + 刷新浏览器（HMR 仅在 pnpm dev:web 常驻时对 client-plugin 生效，且需重建 bundle 后由 watcher 热更）。

### 1.4 HMR 触发条件（实测约束）

- client-plugin HMR receiver 已激活，但**仅当 pnpm run dev:web 从同一 checkout 常驻运行**时才自动重建/热更；
- **apps/web shell（非 client-plugin 部分）每次改动需重建 Web 产物**，且现有 GUI URL 需刷新验证——Vite dev server 不是独立应用，window.__DSH_BOOT__ 仅由 dsh web 注入；
- 结论：纯 client-plugin 开发可走 dev:web HMR；涉及 shell/普通包必须走「重建产物 + 重启 dsh web + 刷新」全链路。

### 1.5 冒烟验证探测口径（plugins.smoke.json 实测样例）

```json
{
  "build": { "command": "npm run build", "expected": ["lib/index.js", "lib/client.js"] },
  "host": {
    "profile": "web",
    "logGlob": "~/.dsh/sessions/**/*.log",
    "errorPatterns": ["ERR_MODULE_NOT_FOUND", "Failed to load plugin", "Cannot find module"],
    "successPatterns": ["dsh-plugin-local-projects", "settings.section"]
  }
}
```

纯客户端面板插件无 HTTP 端口 → 探测走「构建产物存在 + host 加载日志模式匹配」双通道。

## 二、dsh-ssh 配置源情报（单一来源方案评估输入）

### 2.1 当前实测现状

- ~/.dsh/dsh-ssh.json **尚未生成**（插件按需创建，主机由用户在 GUI 配置）；
- ~/.ssh/config 实测内容（2 个 host）：

```
Host github.com
    HostName ssh.github.com
    Port 443
    User git
    StrictHostKeyChecking accept-new
    IdentityFile ~/.ssh/id_ed25519

Host gitee.com
    HostName gitee.com
    Port 22
    User git
    StrictHostKeyChecking accept-new
    IdentityFile ~/.ssh/id_ed25519
```

- dsh-ssh 插件源码在 dsh-web-ui 全家桶仓库 packages/dsh-ssh，本机未检出（插件本体经聚合包 web-ui-all 安装）。

### 2.2 dsh-ssh 已知配置语义（据插件文档）

- 主机配置存 ~/.dsh/dsh-ssh.json（权限 0600，密码明文）；
- 可从 ~/.ssh/config 导入；
- 字段预期覆盖：alias / host / user / auth（key|password）/ passphrase-key / ProxyJump / environment / tags / description；
- 支持持久连接池（空闲 30 分钟断开）、密钥/密码认证、passphrase 密钥、ProxyJump 跳板。

### 2.3 单一来源方案建议（供设计评估）

- 方案 A（推荐）：~/.ssh/config 为主源，dsh-ssh.json 为覆盖层（用户 GUI 增量 → 写覆盖层，不写回 config）；
- 方案 B：dsh-ssh.json 为主源，提供 import-from-ssh-config 一次性导入命令（幂等，按 Host 块解析 alias）；
- 关键点：双份清单防漂移的根因是「两个文件独立编辑」；任一方案需定义「同 alias 冲突时谁赢」+ 每次读取时比对 mtime 提示漂移。

## 三、环境事实（供流水线设计参考）

- pnpm 全局已装：~/.npm-global/bin，PATH 已补；
- DSH 运行时：/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/（bundled，仅 node_modules + package.json，无 apps/web 源码树——源码在开发 checkout）；
- 当前 dsh web GUI：http://127.0.0.1:63866（CLD 监听）。
