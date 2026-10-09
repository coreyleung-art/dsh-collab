# CLD-Voice 部署包 · v0.4.9（悬浮球语音记录稳定版）

> 发包方：MBP 节点 ｜ 2026-09-10 ｜ 遵循 `dsh-collab/devices/deploy-safety-scheme.md` 跨设备部署规范
> 接收方：mac-mini（请按第五段"接收端自检"执行后反馈）
>
> **包版本 v0.4.9 = 插件 v0.4.8（字节未改）+ 后端补漏修复。** 变更明细见 `PACKAGE-CHANGELOG.md`。
> v0.4.9 相对 v0.4.8 的修复：① 补齐漏打的 `backend/stream_bridge.py`（8903 桥）② 修复其凭证解析不兼容 `refs:` 缩进格式的缺陷 ③ 清除误带入的 `__pycache__`。
>
> ⚠️ **首次真实跨设备部署（MBP→mac-mini）实测踩到的坑，接收端请先读 `PACKAGE-CHANGELOG.md` 末节「接收端额外注意事项」**：凭证可能为 `refs:` 嵌套格式、`GLM_API_KEY` 可能缺失、8903 可能与遗留服务冲突、非交互 SSH 的 PATH 缺 `node`。

---

## 〇、取包方式（星桥中枢黑板，公网可达）

包已发布到**中枢黑板**（无需 Tailscale，公网直连）：

```bash
# 方式A: 一键取包(推荐)
python3 fetch-release.py --name cldvoice --version v0.4.9 --out /tmp

# 方式B: 手动(读 manifest → 取各分片 → 拼接 → base64 解码)
CB=http://106.53.214.108:8792
KEY=data/mbp/release/cldvoice-v0.4.9
curl -s "$CB/$KEY/manifest"                    # 读 manifest(sha256/分片数)
for i in $(seq 0 <parts-1>); do curl -s "$CB/$KEY/part-$i"; done   # 拼各片 seg 字段
# → 拼接 base64 → base64 -d → tar -xzf → 得本包
```

**校验**：sha256 以 manifest 中的值为准（`fetch-release.py` 会自动校验）。

---

## 一、包内容

```
cldvoice-package-v0.4.9/
├── plugin/dsh-plugin-cldvoice/   # CLD 插件 v0.4.8 (host + client) —— 自包含, 无外部 npm 依赖
├── backend/                      # 语音后端 (Python)
│   ├── voice_service.py          # 全双工内核 :8905 WS / :8906 HTTP (产品化, 多会话)
│   ├── duplex_bridge.py          # Seeduplex 全双工内核 (被 voice_service 复用)
│   ├── asr_server.py             # 成稿引擎 :8902 (LLM 主动提炼) + UI
│   └── stream_bridge.py          # 火山流式桥 :8903 (由 asr_server 内部启动) ← v0.4.9 补齐
├── launchd/                      # launchd 常驻服务模板 (com.dsh.voice-service / com.dsh.cld-voice)
├── sdk/                          # voice-sdk.js (跨端接入库) + demo.html
├── docs/                         # protocol.md / SOUND-FIXES.md / VoiceKit-README.md / embedded-plugin-design.md
├── requirements.txt              # Python 依赖
├── deploy-check.sh               # 接收端自检脚本
├── fetch-release.py              # 从中枢黑板取包
├── publish-release.py            # 发包方发布到中枢黑板
├── PACKAGE-CHANGELOG.md          # 包版本变更 + 接收端注意事项 ★先读
└── INSTALL.md                    # 本文件
```

## 二、宿主 API 要求（接收端核对）

| 要求 | 说明 |
|------|------|
| CLD / DSH profile | web profile（`~/.dsh/profiles/web/`），支持 `dsh.profile.bundles` + `cordis.patch.yml` |
| Cordis | 4.x（插件用**约定式定义**：`export const name/inject` + `export function apply(ctx)`，非 `definePlugin`） |
| host 服务 | `ctx.webServer.register({kind:'exact', path, handler})`（**不是** `ctx.services` / `webServer.route`） |
| client 运行时 | 提供 `require('react')` / `require('react-dom')`（CLD client runtime 已内置） |
| Node | ≥ 18（host 只用 `node:fs/promises` / `node:os` / `node:path` 内置模块） |

**插件依赖自包含**：host 仅用 Node 内置模块；client 用宿主提供的 react/react-dom → **无需打包 node_modules**。

## 三、安装步骤

### 1) 插件安装（CLD 内嵌悬浮球）
```bash
PKG=<本包解压路径>
PROFILE=~/.dsh/profiles/web        # 按实际 profile 调整

# a. 放插件(建议放 ~/dsh-collab/devices/ 或任意稳定路径)
mkdir -p ~/dsh-collab/devices/
cp -R "$PKG/plugin/dsh-plugin-cldvoice" ~/dsh-collab/devices/

# b. symlink 进 profile node_modules
ln -sfn ~/dsh-collab/devices/dsh-plugin-cldvoice "$PROFILE/node_modules/dsh-plugin-cldvoice"

# c. profile package.json 追加依赖 + bundle
#    dependencies:  "dsh-plugin-cldvoice": "link:~/dsh-collab/devices/dsh-plugin-cldvoice"
#    dsh.profile.bundles 追加:  "dsh-plugin-cldvoice"
python3 - <<'PY'
import json, os
p = os.path.expanduser("~/.dsh/profiles/web/package.json")
d = json.load(open(p))
d.setdefault("dependencies", {})["dsh-plugin-cldvoice"] = "link:" + os.path.expanduser("~/dsh-collab/devices/dsh-plugin-cldvoice")
b = d.setdefault("dsh", {}).setdefault("profile", {}).setdefault("bundles", [])
if "dsh-plugin-cldvoice" not in b: b.append("dsh-plugin-cldvoice")
json.dump(d, open(p, "w"), ensure_ascii=False, indent=2)
print("profile package.json updated")
PY

# d. 安装依赖(本地 link 不需要联网; 若 pnpm 卡住可跳过, symlink 已足够)
# cd "$PROFILE" && pnpm install --prefer-offline
```

### 2) 后端服务安装
```bash
cd ~/dsh-collab/cld-voice/backend 2>/dev/null || mkdir -p ~/dsh-collab/cld-voice/backend
cp "$PKG/backend/"*.py ~/dsh-collab/cld-voice/backend/

# 建 venv + 装依赖
cd ~/dsh-collab/cld-voice/backend
python3 -m venv venv
./venv/bin/pip install -r "$PKG/requirements.txt"     # or: pip install -r <包>/requirements.txt
```

### 3) 凭证（必须）
在 `~/.dsh/.credentials.yaml` 写入（从你的火山/智谱控制台取）：
```yaml
VOLC_ASR_API_KEY: <火山语音 key>      # Seeduplex 全双工 / ASR
GLM_API_KEY: <智谱 key>              # 成稿引擎 LLM 提炼
```
> 说明：无 `GLM_API_KEY` 时成稿引擎自动回退关键词模式（不断链，但质量下降）。无 `VOLC_ASR_API_KEY` 则语音不可用。

### 4) launchd 常驻服务
```bash
# 修改 plist 里的路径为你的实际用户/路径
cp "$PKG/launchd/"*.plist ~/Library/LaunchAgents/
sed -i '' "s#/Users/coreyleung#${HOME}#g" ~/Library/LaunchAgents/com.dsh.voice-service.plist ~/Library/LaunchAgents/com.dsh.cld-voice.plist

# 加载
launchctl load ~/Library/LaunchAgents/com.dsh.voice-service.plist
launchctl load ~/Library/LaunchAgents/com.dsh.cld-voice.plist

# 验证
curl -s http://127.0.0.1:8906/v1/health     # 期望 {"ok":true,...}
curl -s http://127.0.0.1:8902/api/drafts    # 期望 {"drafts":[...]}
```

### 5) 重启 CLD
> host 插件改动需**完全退出 CLD 再重开**（Cmd+Q → 重新打开），Cmd+R 只重载 renderer。

## 四、验证清单

1. `/voice/health` 在 CLD 渲染端口返回 `{"ok":true,"service":"cldvoice",...}`
   - 渲染端口查看：`lsof -nP -iTCP -sTCP:LISTEN | grep -i CLD`（非 31888 那个）
2. 悬浮球出现（对话输入区右下角 🎤，fixed 可拖拽）
3. 点悬浮球 → 展开「语音会议记录」面板 → ●说话 → 有转写文字
4. 面板诊断行显示 `🔊 音频: 收 N KB / 播 N 次 / ctx running`
5. ✅完成注入 → 成稿（背景/功能需求/非功能需求/决策记录）自动填进会话输入框并发送
6. 声音：AI 语音可听（面板可用"🔊 音量"滑块 30%~250% 调整）

## 五、接收端自检要求（deploy-safety-scheme §5，必做并反馈）

1. **依赖完整性**：静态四段审查（package.json 合法 / bundles 顺序 / cordis.patch 存在 / `node --check lib/*.js`）
2. **工具链版本核对**：Cordis 4.x；`node --check` 通过
3. **隔离模拟**：`DSH_HOME=/tmp/dsh-test-home` 隔离启动存活 30s 不崩（生产 ~/.dsh 零接触）
4. **配置树核对**：`dsh --profile web --dump-config | grep cldvoice` 确认入树
5. **配套反馈**：自检结果回报发包方（MBP），**通过才上生产重启**
6. **包完整性交叉核对（v0.4.9 新增，血泪教训）**：`deploy-check.sh` 只审**包内已有**文件，**查不出"该有但没打进来"的文件**。安装后必须把已装后端目录与发包方生产目录逐文件比对：
   ```bash
   for f in ~/dsh-collab/cld-voice/backend/*.py; do
     curl -s "http://<发包方>:<port>/..." >/dev/null   # 或直接向发包方索取生产目录清单
   done
   # 至少确认 4 个 .py 齐全：voice_service.py duplex_bridge.py asr_server.py stream_bridge.py
   ```
   v0.4.8 正是漏打了 `stream_bridge.py`，导致 8903 桥静默缺失且自检全绿。

## 六、已知特性 / 注意事项

- **偶发纯文字回应**：火山 Seeduplex 对个别对话（开场/短句）偶发只回文字不产语音（`audio bytes=0`）。已用强化 instructions"必须用语音回答"缓解；如需 100% 有声需独立火山 TTS 凭证。详见 `docs/SOUND-FIXES.md`。
- **端口**：内核 `:8905`(WS) / `:8906`(HTTP)；成稿引擎 `:8902`。若与现有服务冲突请改 plist 参数。
- **音频不回传云端**：音频仅本地 → 火山直连，不落盘（草稿 .md 除外）。
- **回退**：卸载 = 从 profile `dsh.profile.bundles` 移除 `dsh-plugin-cldvoice` + 移除 symlink + Cmd+Q 重启。

## 七、版本
- 插件 `dsh-plugin-cldvoice` v0.4.8
- voice-service v1.2.0 ｜ 成稿引擎(LLM 提炼) v1.1.0 ｜ 协议 v1
