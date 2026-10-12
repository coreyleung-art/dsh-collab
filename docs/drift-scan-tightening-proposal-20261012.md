# 收紧类建议单 · `dsh-plugin-drift-scan` 两条判据（v7 M9-①②）

> **提出**：2026-10-12T22:49:06+08:00 · 星桥第二任（`session-e317d6ab`）
> **被建议件**：`~/.dsh/profiles/web/node_modules/dsh-plugin-drift-scan/lib/{core.js,channel-matrix.json}`
> **★ 本单只提建议，未改被建议件一字**（★ 依「不改对方件」纪律；★ 且该件【归属不明】——
>   登记卡 `data/registry/dsh-plugin-drift-scan` 的 owner/author/steward **三字段皆 `None`**，见跳过册 S1）
> **★ 本单不主张任何事项已闭合**（S3）

---

## 建议 1 · `bus-8791` 的 `probe` 缺 `expectStatus` ⇒ 对非 2xx 无判别力

**现测原文**（`channel-matrix.json:28-35`）：

```json
"bus-8791": {
  "kind": "endpoint-token",
  "expect": "http://xingqiao.meetfunbp.com:8791/bus/receive?target=mac-mini",
  "tokenFile": "~/.dsh/bus-bridge-token",
  "tokenPerm": "0600",
  "probe": { "expectBodyContains": "ok" }      ← ★★ 无 expectStatus
}
```

**消费侧原文**（`core.js` `checkEndpoint`）：

```javascript
let drift = false, actual = `HTTP ${r.status}`;
if (spec.probe.expectStatus !== undefined) drift = r.status !== spec.probe.expectStatus;  // ★ 跳过
if (spec.probe.expectBodyContains !== undefined) {
  const hit = r.body.includes("ok");     // ★★ 只看这一个
  drift = drift || !hit;
}
```

**⇒ 问题（★ 三态）**：

| 响应 | ★ 现判据 | ★ 应判 |
|---|---|---|
| `200` + body 含 `ok` | ✅ 无 drift | ✅ 无 drift |
| **`401`** + body 含 `ok`（★ 如 `{"error":"...not ok"}`） | ★★ **绿（假绿）** | ❌ **drift** |
| **`403`** + 同上 | ★★ **绿** | ❌ **drift** |
| **`500`** + 同上 | ★★ **绿** | ❌ **drift** |
| `200` + body 不含 `ok` | ❌ drift | ❌ drift |

★ **⇒ 即：该判据对【整片 HTTP 失败域】无判别力**（★ W4 原话，本线独立复现并复核其原文）。

### ★ 建议（★ 最小改动）

```json
"probe": { "expectStatus": 200, "expectBodyContains": "ok" }
```

★★ **并建议在 `checkEndpoint` 里把 status 判据【改为无条件】**：

```javascript
// ★ 现状：expectStatus 未给 ⇒ 完全不看 status
// ★ 建议：至少要求 2xx，否则一律 drift
if (spec.probe.expectStatus !== undefined) {
  drift = r.status !== spec.probe.expectStatus;
} else {
  drift = !(r.status >= 200 && r.status < 300);   // ★ 缺省要求 2xx
}
```

★ **负控（★ 建议补的）**：★ 造一个「返 401 且 body 含 `ok`」的输入 ⇒ **必须判 drift**。

---

## 建议 2 · `tailscale-direct` 的行匹配【同形缺陷】

**现测原文**（`core.js:92-98`）：

```javascript
function checkTailscale(name, spec) {
  let out = '';
  try { out = runWhitelisted('/usr/local/bin/tailscale', ['status']); }
  catch (e) { return { ..., drift: true }; }
  const missing = spec.expect.filter((peer) =>
    !out.split('\n').some((l) => l.includes(peer) && l.includes('active')));   // ★★ 判据在这里
  return { ..., actual: missing.length === 0 ? '对端均 active' : '缺失/非 active: ' + ... };
}
```

**⇒ 问题**：★ **本机 `tailscale status` 实测同一行里同时含两种状态**：

```
100.112.111.120  macbook-pro-2  coreyleung@  macOS
                 active; relay "hkg"; offline, last seen 19m ago, tx ... rx ...
```

★ 该行 `l.includes(peer)` = **true**（★ 有 peer 名）· `l.includes('active')` = **true**（★ 有 `active;`）
★★ **⇒ 判「对端 active」** —— ★ **而它其实是 `offline`**。

### ★ 建议（★ 用更精确的判据）

```javascript
// ★ 建议：positive 与 negative 都要看 —— 「active 且【不含】offline」
out.split('\n').some((l) => l.includes(peer) && l.includes('active') && !l.includes('offline'))
```

★ **或**（★ 更稳）：★ **只取行首字段**（★ `tailscale status` 的状态列是固定位置）：

```javascript
const cols = l.trim().split(/\s{2,}/);
// cols[0]=IP cols[1]=host cols[2]=owner cols[3]=OS cols[4]=状态
return cols[1] === peer && /^active/.test((cols[4] || '').trim());
```

★ **负控（★ 建议补的）**：★ 造一个「peer 在线但其行含 `offline`」的样本 ⇒ **必须判 drift**。

---

## ★ 两条的共性（★ 这是本单最想说的）

> ★★★ **两条的缺陷【形状相同】：「用子串出现」代替「用语义判定」。**
>
> ★ **①** `body.includes('ok')` —— ★ **不区分【哪个词里的 ok】**；
> ★ **②** `l.includes('active')` —— ★ **不区分【哪一列里的 active】。**

★★ **⇒ 建议的通则：★ 凡「子串命中即判通过」，必问【这个子串会不会出现在【反例】里】。**
★ **若会 ⇒ 该判据无判别力。**

---

## ★ 本单对自己的两条声明

- ★★ **本单只提建议** —— ★ 未改被建议件；★ 且被建议件**归属不明**（★ 见跳过册 S1）。
- ★ **本单的两条问题均为【读原文 + 本机实测】得出** —— ★ 但**未在其内部造负控实测**（★ 那需改件）。
  ★★ **⇒ 故本单不主张「已证」** —— ★ 主张的是「原文如此 + 反例存在」，★ **闭环需属主在件内补负控**。

★ 本单不主张任何事项已闭合（S3）。
