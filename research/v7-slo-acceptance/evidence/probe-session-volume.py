#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S7 单会话体积 / 事件数 —— 现测口径

★ 事件数须解压 zstd 才能数 ⇒ 慢。默认只对**体积最大者**计数（可 --top N 增加）。
★ 且必须声明：这是【磁盘体积】与【行数】，不是运行时【活跃窗口事件数】—— 两者不是同一个量。
"""
import glob, os, sys, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--top", type=int, default=1)
ap.add_argument("--root", default=os.path.expanduser("~/.dsh/sessions"))
a = ap.parse_args()

files = glob.glob(os.path.join(a.root, "**", "session.jsonl.zstd"), recursive=True)
if not files:
    print("分母 = 0（未找到任何 session.jsonl.zstd）⇒ ★ 不可判")
    sys.exit(3)

sized = sorted(((os.path.getsize(f), f) for f in files), reverse=True)
print("会话文件总数（分母）= %d" % len(files))
print("体积最大前 %d：" % min(a.top, len(sized)))

try:
    import zstandard
    has_zstd = True
except ImportError:
    has_zstd = False

for sz, f in sized[:a.top]:
    line = "  %.1f MiB  %s" % (sz / 1048576.0, os.path.basename(os.path.dirname(f)))
    if has_zstd:
        d = zstandard.ZstdDecompressor()
        n = raw = 0
        with open(f, "rb") as fh, d.stream_reader(fh) as r:
            while True:
                c = r.read(1 << 22)
                if not c:
                    break
                raw += len(c); n += c.count(b"\n")
        line += "  → 解压 %.1f MiB · 事件行数 %d" % (raw / 1048576.0, n)
    else:
        line += "  → 事件数不可判（无 zstandard 模块）"
    print(line)

print()
tot = sum(s for s, _ in sized)
print("全部会话文件字节合计 = %.1f MiB" % (tot / 1048576.0))
print("★ 目标口径提醒：§12 写「单会话 ≤200MB + 事件数入监控」。")
print("★ 上列体积是【磁盘上压缩后的文件体积】；zstd 解压后体积**大于**它 ⇒ 与 200MB 目标比较前必须先声明比的是哪一个。")
