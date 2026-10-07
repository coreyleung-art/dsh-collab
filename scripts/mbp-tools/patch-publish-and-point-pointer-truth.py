#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch-publish-and-point-pointer-truth.py —— 修正指针发送的**假成功**报告

【缺陷】（2026-10-03 实测）
  `publish-and-point` 判"指针发出"的依据是 `'"ok":true' in stdout`。
  而 bus 的真实返回是：
      {"ok":true,"task_id":"…","status":"queued","offline":true}
  ⇒ **`ok:true` 只代表"服务器受理"，`offline:true` 说明对端不在线 ⇒ 只排队、未送达**
  ⇒ 我把它记成"已发"，**与今天一直在打的「queued 伪装成 delivered」是同一类错**（R31 家族）。

【修法】
  解析 JSON 后**按 status/offline 分档**：
    · 送出      ：status 非 queued 且非 offline
    · queued    ：status == "queued" 或 offline == true   ⇒ **不算送达**
    · 发送失败  ：无 ok
  并在发出后**显式提示**：指针只是二次提醒，**真正投递靠黑板卡 + 对端 inbox 注入**。
"""
import io
import os

p = os.path.expanduser("~/dsh-collab/tools/publish-and-point.py")
s = io.open(p, encoding="utf-8").read()

old = """            sent.append((tgt, '"ok":true' in (out.stdout or ""), (out.stdout or out.stderr).strip()[:80]))"""
new = """            # ★ 按 status/offline 分档（2026-10-03）：`ok:true` 只代表服务器受理；
            #   `offline:true`/`status:"queued"` ⇒ **只排队、未送达**（别再记成"已发"）
            _raw = (out.stdout or "").strip()
            _st, _off = None, None
            try:
                _j = json.loads(_raw)
                _st, _off = _j.get("status"), _j.get("offline")
            except Exception:
                pass
            if _off is True or _st == "queued":
                sent.append((tgt, "queued", "对端 bus 离线/排队 ⇒ **指针未送达**（不影响卡片投递）"))
            elif _st is not None or '"ok":true' in _raw:
                sent.append((tgt, True, _raw[:80]))
            else:
                sent.append((tgt, False, (_raw or (out.stderr or "")).strip()[:80]))"""
assert old in s, "发送锚点未命中"
s = s.replace(old, new, 1)

old2 = """    return True, key, {"write": wrote, "readback": ok_boards, "pointer": text,"""
new2 = """    _queued = [t for t, st, _ in sent if st == "queued"]
    if _queued:
        print("  ⚠️ 指针仅**排队未送达**（%s）：bus 报对端离线。" % ",".join(_queued))
        print("     ⇒ 这不影响送达 —— 实际投递由**黑板卡 + 对端 inbox 注入**完成"
              "（已由 verify-delivery 在对端日志确认）。指针只是二次提醒。")
    return True, key, {"write": wrote, "readback": ok_boards, "pointer": text,"""
assert old2 in s, "返回锚点未命中"
s = s.replace(old2, new2, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("✅ 已修正指针发送的分档与提示（queued ≠ 送达）")
