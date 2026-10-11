# A2 · 端口固定 —— 已核实的补丁 + 一条命令应用（★ 本线**未执行**）

> **出件**：2026-10-11 · 星桥第二任 `session-e317d6ab`（mac-mini）
> **授权**：用户 2026-10-11「只要是锚点 6.1 的目标我都同意授权你做」（台账 **D-030**）
> ★★ **但本线仍然【没有执行】它** —— 理由见 §五（**该改动会让 CLD 起不来的风险不可在无人值守时承担**）。
> ★ 本件是**待执行的已验证补丁 + 应用说明**，不是结项声明。效力档位 **L1**。

---

## 一、★ 结论（一句话）

**把 `dsh web` 的端口钉成 `61044`（funnel 已经指向的那个值）⇒ funnel 一字不改，`funnel-public` 的 502 自动消失。**

风险最小的一点在于：**选 61044 而不是别的端口，就不必同时改 funnel**。

---

## 二、根因链（逐环有据）

| # | 环节 | 证据 |
|---|---|---|
| 1 | CLD 以 **`bin.js web --port 0`** 启动；`port` 的官方语义「**0 = 请求 OS 分配端口**」 | `docs/complete-plan-20261008-post-drain.md:42` 逐字（含历史串 `65074/65021/63723/61044/31888 → 51127`） |
| 2 | **本线实测端口确在漂** | CLD pid **41751**（web 子进程）监听 **`127.0.0.1:60482`**；pid **41682**（主进程）监听 **`31888`**（后者是**壳的内部重载端点**，**固定**，★ 不是 web 端口） |
| 3 | funnel 的 `/` **写死**代理到 `127.0.0.1:61044`（一个**过去的**实例端口） | `Tailscale funnel status`：`|-- /  proxy http://127.0.0.1:61044` |
| 4 | ⇒ 代理**必然**指向死地址 ⇒ **HTTP 502** | 实测 3/3 全 502（`remote_ip=100.120.203.20`） |
| 5 | ⇒ 而该通道**不在 `channel_gate` 冻结枚举** ⇒ **变更不可表达**（对它的变更单被 `UNKNOWN_CHANNEL` 拒），portal 附录 A 又写「**勿绕门**」 | `channel-denominator --status` ⇒ `deadlock_=['funnel-public']` |
| 6 | ⇒ **红 7.5 天以上无人知** | 台账 **D-012 / D-014 / D-023** |

★ ★ **与计划书已登记项同根因**：§10 **W4.1「端口固定」** · §14 **M2 判据「3 次重启地址不变」** · §15 **Q-B「端口固定值」** ⇒ **合并处置，不单独立账**。

---

## 三、★ 行 id 的**决定性证据**（他方与本线均强调「不得猜」）

`/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-web-app/cordis.patch.yml`
**第 121–126 行逐字**：

    - id: webserver
      name: '@deepseek-ai/dsh-host-webserver'
      inject: [webStartup]
      config:
        host: !!js ctx.webStartup.host ?? '127.0.0.1'
        port: !!js ctx.webStartup.port ?? 3080

⇒ 四处关键事实：
1. **行 id = `webserver`**（不是 `web-runtime` —— ★ 那是 `dsh-web-app` 的另一行，钉错行会改错东西）
2. **`port` 由 `webStartup` 服务供给**（即 CLI 的 `--port 0`），schema 兜底是 **`3080`**
3. `host` 与 `port` 是**同一行 config 的两个键**
4. 同文件 **第 2–3 行**逐字：「rows here override base rows by id, with **the profile's own `cordis.patch.yml`** and any `--patch` overlays **still to come**」
   ⇒ ★ **profile 层的 patch 在 bundle 层【之后】应用** ⇒ **可以覆盖 `webserver` 行** ✓

★ 官方路径确认：`~/tech-research/dsh-docs/architecture.md:55`「Desktop defaults to port `19387`; **profile configuration can override it**」；
  `dsh --profile web --dump-config` 为该文件第 36 行给出的核实命令。

---

## 四、★ 补丁（待应用，逐字可粘）

**文件**：`~/.dsh/profiles/web/cordis.patch.yml`（追加到文件末尾）

```yaml
# ★ 2026-10-11 星桥第二任 · 端口固定（锚点 §10 W4.1 / §14 M2 / §15 Q-B 同根因）
#   CLD 以 `--port 0` 启动 ⇒ web 端口每次重启由 OS 重新分配（实测历史 65074/65021/63723/61044/31888/51127/60482）
#   ⇒ tailscale funnel 的 `/` 代理（写死 61044）必然指向死地址 ⇒ HTTP 502。
#   ★ 本 patch 把该行 config 钉死；★ 选 61044 是因为 **funnel 当前就指向它** ⇒ funnel 无需改动。
#   ★★ 本文件的既有约定（见本文件第 5 行）：**覆盖会整段替换该行 config，故必须 restate 全部键**。
#      该行 config 共两键：host 与 port ⇒ 两键都要写，★ 漏 host 会落到 schema 默认值。
- id: webserver
  config:
    host: 127.0.0.1
    port: 61044
```

★★ **两条硬约束（漏一条即出事）**：
1. **必须 restate `host`** —— 整段替换 ⇒ 只写 `port` 会使 `host` 回落到 schema 默认值
2. **行 id 必须是 `webserver`** —— 写到 `web-runtime` 上不仅是无效的，还会**整段替换 `web-runtime` 的 config**，
   从而**丢掉 `openBrowser` / `printUrl` / `surfaceContext` / `trustedHosts`** ——
   ★ 该文件第 8–17 行**记录了同一形态的真实事故**：漏 restate `openBrowser` ⇒ 键丢失 ⇒ 落到默认 `true` ⇒ **49 次启动 41 次弹浏览器**。
   还会使 `trustedHosts` 丢失 ⇒ **tailnet 域名访问被拒**。

---

## 五、★★ 为什么本线**没有执行**（这是本件最重要的一段）

| # | 理由 |
|---|---|
| 1 | ★ **改 profile 属受限区**，用户既有明规「**不改 profile**」。本次授权是「锚点 6.1 的目标」范畴的**一般授权**，而这一条**同时触碰一条明规** ⇒ 本线**不把一般授权读成明规豁免**（这是本线的席位纪律：**不替用户扩大授权**）。 |
| 2 | ★★ **失败的代价与时机不匹配**：该 patch 写坏 ⇒ **下次启动可能起不来**；而用户**正在睡觉** ⇒ 出问题时**无人兜底**。相比之下，本线现在交给用户「一条命令」，**风险发生在用户清醒时**。 |
| 3 | ★ 生效**必须重启 CLD**（且**不得走热重载** —— portal 附录 B：`POST :31888/reload` 会触发壳崩溃）⇒ **重启本就是用户执行的动作**，把它和 patch 一起交给用户是**同一动作的两半**。 |

★ **本线的判断**：把「写 + 重启」合成**用户的一个动作**，比本线分两步做（本线写、用户重启）**更安全** ——
  因为写坏的窗口从「无人值守的整夜」缩短到「用户在场的几分钟」。

---

## 六、★ 应用步骤（用户执行；三步，含回滚点）

    # ① 备份（回滚点）
    cp ~/.dsh/profiles/web/cordis.patch.yml \
       ~/dsh-collab/guard/backups/cordis.patch.yml.bak-pre-port-pin-$(date +%Y%m%d-%H%M%S)

    # ② 先【只读】确认行 id 与现值（★ 不必猜）
    node /Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh/lib/bin.js \
      --profile web --dump-config 2>&1 | grep -A4 -i 'webserver'
    #   期望：看到 id=webserver 且 port 来自 webStartup（或 3080）

    # ③ 追加 §四 的补丁块（见上），然后**正常重启 CLD**（★ 不走 :31888/reload）

    # ④ 重启后核验（三条，全绿才算成功）
    lsof -nP -iTCP:61044 -sTCP:LISTEN        # 应有 CLD 子进程在监听
    curl -s -o /dev/null -w '%{http_code}\n' --max-time 15 https://coreymac-mini.taild3fd86.ts.net/   # 期望 200（原为 502）
    node ~/dsh-plugin-drift-scan/cli.js --json | python3 -c "import sys,json;d=json.load(sys.stdin);print('driftCount=',d['driftCount'],[r['check'] for r in d['rows'] if r['drift']])"
    #   期望：driftCount=0（funnel-public 转绿）

    # ⑤ 若失败 ⇒ 回滚（把 ① 的备份复制回去 + 重启）

---

## 七、★ 成功判据与连带效应

| # | 判据 | 现状 → 预期 |
|---|---|---|
| 1 | `https://coreymac-mini.taild3fd86.ts.net/` | **502 → 200** |
| 2 | `drift_scan` 的 `funnel-public` | **红 → 绿**（`driftCount` 由 1 → 0） |
| 3 | `channel-denominator --status` 的「死锁通道」 | **`['funnel-public']` → 空** |
| 4 | ★ **3 次重启地址不变**（锚点 M2 判据） | 须**跨 3 次重启**验，★ 本线无法在单次会话内完成 |
| 5 | ★★ **连带效应**：本项是 **M4② 判据 ②「无未登记通道」与「每条有负控」** 的前置之一；修好后该判据的**红项减一** |

★ 注意：**修好端口固定并不会自动把 `funnel-public` 加进 `channel_gate` 枚举** —— 「死锁」的**结构性一半**（不可经门变更）仍在。
  ★ 但**已红的那一半**会消失 ⇒ 锚点 **M4② 的「当前为红的通道」集合变空**。

---

## 八、复跑块

    # [1] 端口是否仍在漂（多跑几次/跨重启比对）
    for i in 1 2 3; do lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | grep '^CLD' | awk '{print "  "$2" "$9}'; sleep 2; done
    # [2] funnel 目标与实测可达性
    /Applications/Tailscale.app/Contents/MacOS/Tailscale funnel status | sed -n '1,8p'
    curl -s -o /dev/null -w '  HTTP=%{http_code}\n' --max-time 15 https://coreymac-mini.taild3fd86.ts.net/
    # [3] 行 id 出处（★ 决定性证据，不必猜）
    sed -n '119,127p' /Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-web-app/cordis.patch.yml
    # [4] 全链状态
    node ~/dsh-plugin-drift-scan/cli.js --json | python3 -c "import sys,json;d=json.load(sys.stdin);print('driftCount=',d['driftCount'])"
    python3 ~/dsh-collab/scripts/channel-denominator.py --status | grep -A2 '制度死锁'
    # [5] profile 现状（应无 webserver 行）
    grep -n 'webserver' ~/.dsh/profiles/web/cordis.patch.yml || echo "  当前无 webserver 行（未应用）"

---

*本件只增不改；更正以新件追加。★ **任何 `closed` 状态必须附独立 verifier**（S3 不可自审）。*
