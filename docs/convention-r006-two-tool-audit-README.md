# r006-two-tool-audit — R006 十项审查器（中文说明）

## 用途
对 `scripts/` 共享族形态的工具做 R006 十项（可适用部分）审查，每项【实跑或实测】，不采信声明。

## 用法
```
python3 scripts/r006-two-tool-audit.py [--tool <path>] [--json]
python3 scripts/r006-two-tool-audit.py --selftest   # 4 负例 + 1 正例
python3 scripts/r006-two-tool-audit.py --selfcheck  # 声明与实现一致性
python3 scripts/r006-two-tool-audit.py --lean4-check
```

## 两种剥离面（★ 不可混用）
- `strip_strings_and_comments`：抹除【字符串+注释】⇒ 用于【防自指】类判据
- `strip_comments_only`：抹除【仅注释】，保留字符串 ⇒ 用于【硬编码路径/版本】类判据
- ★ 混用会造成漏报（2026-10-10 本器内实测犯过三次）

## 豁免
带 `★ 检测器模式` 标记的行不作硬编码判定（与 drg 的显式豁免同构）。

## 已知不判
⑧ 自动落链按「本机索引收录即通过」口径，与本器静态判据不同 ⇒ 标 UNCHECKED。
