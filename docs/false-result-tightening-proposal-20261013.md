# 收紧类建议单 ② · 假结果形态 12 处（v7 §0.2.1 门报出）

> **提出**：2026-10-13T00:29:21+08:00 · 星桥第二任
> **依据**：★ `tools/false-result-patterns.py`（★ 自证 6/6）· ★ 已接进 `beacon-check`（★ 每次必跑报红）
> **★ 本单只提建议，未改被建议件一字**（★ 依「不改对方件」纪律；★ 且多数件归属不明）
> ★ **本单不主张任何事项已闭合**（S3）

---

## ★ 命中明细（★ 按文件归并）

| 件 | ★ 处数 | ★ 类 | ★ 行 |
|---|---|---|---|
| `scripts/bb-copy.py` | **4** | P1 | 174,536,537,537 |
| `scripts/bb-put-verify.py` | **1** | P2 | 194 |
| `scripts/bb-upgrade.py` | **1** | P1 | 95 |
| `scripts/drift-scan-cron.py` | **3** | P1 | 118,199,231 |
| `scripts/self-report-gate.py` | **1** | P2 | 287 |
| `tools/beacon-check.py` | **2** | P1 | 106,107 |

---

## ★★ 两类各是什么

### P1 · subprocess 结果取 `.status`（★ 应为 `.returncode`）

**立据**：★ 本纳 2026-10-12 用 `p2.status`（★ 正确是 `returncode`）跑 341 个自证 ⇒
★★ **全部被记成 `ERR:AttributeError`** ⇒ 报告说「341 个全坏」，★ 而手动跑一个 ⇒ `exit=0`（D-228/D-231）。

**建议修法**（★ 逐处）：

```python
# ★ 现状（★ 该属性不存在 ⇒ 抛 AttributeError ⇒ 异常路径与失败同形）
rc = r.status

# ★ 建议
rc = r.returncode
```

★★ **或**（★ 若该 `r` 其实是 HTTP 响应）：★ **改名**（★ 如 `resp`）以免混淆。

### P2 · `None` 被当绿

**立据**：★ 本纳曾用 `not in (0, None)` 过滤 ⇒ ★ **异常产生的 `None` 与成功 `0` 被一同放行**，
★★ 于是「30/30 全绿」是假的（D-231）。

**建议修法**：

```python
# ★ 现状（★ None 与 0 同被放行）
bad = [r for r in rows if r.get("rc") not in (0, None)]

# ★ 建议（★ None 单列，★ 不得当绿）
bad = [r for r in rows if r.get("rc") not in (0,)]
unknown = [r for r in rows if r.get("rc") is None]   # ★ 单列
```

---

## ★★ 本单的已知局限（★ 如实声明）

★ **P1 的变量判定是【文件级】而非逐处数据流** —★ 若同名变量既做过 subprocess 又做过 HTTP，
★★ 则本单会**误报**那些 HTTP 的 `.status`（★ 实测 `scripts/bb-copy.py` 的 `r`）。
★ **故本单的每一处【必须人工核】**，★ 命中 ≠ 缺陷。

---

## ★ 与跳过册的关系

★ 明细里 **`scripts/bb-upgrade.py`** 已在本线跳过册 **S2**（★ 通道自举）里 —★ **两者是同一个件的不同面**。

★ 本单不主张任何事项已闭合（S3）。
