#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch-publish-package-contentaddressed.py —— 把发包键改为「内容寻址」

【为什么】（2026-10-03 对端抓到两处卡/板漂移，根因都是我）
  我发完卡后又原地重发**同一个板键**（v3→v4→v5→v6→v7），卡上写的 sha256/文件数
  必然追不上板 —— 对端按卡去核对，看到的是"卡文与板值不一致"。
  对端提议「PUT 后冻结、对端按 version 取」——**约定正确，但约定会被忘**。
  ⇒ **结构解**：板键带**内容哈希后缀** ⇒ 键本身即内容指纹
     · 换内容 ⇒ **换键**（不会原地覆盖）⇒ 旧卡永远指向旧键，**漂移在结构上不可能**
     · 对端只需"按卡上的键取 + 校验哈希"两步，无需再比 version
"""
import io
import os
import re

p = os.path.expanduser("~/dsh-collab/tools/publish-package.py")
s = io.open(p, encoding="utf-8").read()

# ① 默认键改为内容寻址：<base>-<sha8>.tgz-b64
old = '    key = a.key or ("data/packages/%s.tgz-b64" % base)'
new = '''    # ★ 内容寻址键（2026-10-03）：键后缀 = 内容哈希前 8 位
    #   ⇒ 换内容必换键 ⇒ **旧卡不会因为板被覆盖而与板漂移**（对端按卡上的键取即可）
    key = a.key or ("data/packages/%s-%s.tgz-b64" % (base, sha[:8]))
    if a.key and not a.force_inplace and "\\u002d" not in a.key:
        print("  ⚠️ 你指定了固定键 `%s`：该键会被后续重发**原地覆盖**，"
              "卡文将与板漂移。若非必要，建议用内容寻址键（默认行为）。" % a.key)'''
assert old in s, "键锚点未命中"
s = s.replace(old, new, 1)

# ② 加 --force-inplace 参数
old2 = '    ap.add_argument("--selftest", action="store_true")'
new2 = ('    ap.add_argument("--force-inplace", action="store_true",\n'
        '                    help="显式允许对固定键原地覆盖（默认内容寻址，防卡/板漂移）")\n'
        '    ap.add_argument("--selftest", action="store_true")')
assert old2 in s, "参数锚点未命中"
s = s.replace(old2, new2, 1)

# ③ 片段里补「板 version」与「内容寻址说明」
old3 = '    print("  板键: %s" % key)'
new3 = ('    print("  板键: %s  ← **内容寻址（后缀=%s）**" % (key, sha[:8]))\n'
        '    print("  用法: 对端按**卡上的键**取即可；换内容会自动换键，不会原地覆盖 ⇒ 无卡/板漂移")')
assert old3 in s, "片段锚点未命中"
s = s.replace(old3, new3, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("✅ publish-package.py 已改为内容寻址键（+ --force-inplace 逃生门 + 片段补说明）")
