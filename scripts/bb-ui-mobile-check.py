#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-ui-mobile-check.py — SystemGraph 移动端体验判据门（A5）

出件：明鉴 v3（session-a190c54c）· 2026-10-12
依据：docs/systemgraph-mobile-ux-plan-20261012.md §4（六条可机械测的验收判据）
配套：bb-gallery-ui.css / bb-gallery-ui.js / bb-blueprint-gallery.py

★ 为什么需要它（今晚两次教训）：
  「无门 ⇒ 静默回归」—— 判据若不能机械复跑，改好之后会被人（或生成器）改回去而无人发现。
  ★ 实例：r006-retrofit-apply.py 于 2026-10-09 把 Node 自检注入浏览器脚本 ⇒
    整个 UI 静默失效数日，直到用户在手机上发现。**当时没有任何门能提前拦住。**

★ 六条判据（逐条对应规划 §4）
  A1 横向溢出      —— 每页 documentElement.scrollWidth <= innerWidth + 1（需浏览器）
  A2 零桌面措辞    —— 用户可见字符串里不得有 滚轮 / hover / 右键 / 双击
  A2b 触摸等价     —— JS 里的 mousemove/mouseenter 驱动型交互，必须有 pointer/touch 等价
  A3 安全区在位    —— viewport-fit=cover 且 CSS 有 env(safe-area-inset-*)
  A4 固定宽覆盖    —— 所有 width:Npx (N>390) 都能被某条 CSS 规则接住
  A6 首屏可交互    —— 由浏览器侧计时（本器只做静态部分，浏览器部分标注未覆盖）

★ 三态用词：OK / FAIL / UNCOVERED（不可判，**不得**读作通过）
  ★ 若本机无 Chrome，则 A1/A6 记为 UNCOVERED，**不得**因为「跑不起来」就报通过。

用法：
  python3 bb-ui-mobile-check.py                # 静态 + 浏览器（有 Chrome 时）
  python3 bb-ui-mobile-check.py --static-only  # 只跑静态项
  python3 bb-ui-mobile-check.py --selftest     # ★ 负控矩阵（判据必须会红）
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CSS = os.path.join(HERE, "bb-gallery-ui.css")
JS = os.path.join(HERE, "bb-gallery-ui.js")
PY = os.path.join(HERE, "bb-blueprint-gallery.py")
BASE = "http://127.0.0.1:8798"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

MOBILE_W = 390          # iPhone 16 Pro 逻辑宽
DESKTOP_WORDS = ("滚轮", "hover", "右键", "双击")


def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


# ══════════════ A2 · 用户可见字符串里不得有桌面词 ══════════════
def check_a2(js_src, py_src):
    """★ 只看【字符串字面量】（三类引号）——CSS 的 :hover 是视觉增强，不算。"""
    bad = []
    for name, src in (("bb-gallery-ui.js", js_src), ("bb-blueprint-gallery.py", py_src)):
        for m in re.finditer(r"'([^'\\\n]{3,300})'|\"([^\"\\\n]{3,300})\"|`([^`\\\n]{3,300})`", src):
            t = m.group(1) or m.group(2) or m.group(3) or ""
            if not re.search(r"[\u4e00-\u9fff]", t):
                continue                      # 无中文 ⇒ 多半是选择器/键名，跳过
            for w in DESKTOP_WORDS:
                if w in t:
                    bad.append((name, w, t[:80]))
    return (len(bad) == 0, bad)


# ══════════════ A2b · 鼠标驱动型交互必须有触摸等价 ══════════════
def check_a2b(js_src):
    """★ 口径：`mousemove`/`mouseenter` 驱动的【提示/详情】必须能被 touch/pointer 触发。
    ★ 不是「零 mousemove」—— 鼠标路径要保留；是「不能【只有】鼠标路径」。"""
    has_mouse = "addEventListener('mousemove'" in js_src or "addEventListener('mouseenter'" in js_src
    has_touch = "pointerdown" in js_src or "touchstart" in js_src
    if not has_mouse:
        return True, "无 mousemove/mouseenter 驱动型交互（无需等价）"
    if has_touch:
        return True, "有 mousemove 且有 pointerdown/touchstart 等价"
    return False, "★ 有 mousemove/mouseenter 但无任何 pointerdown/touchstart 等价"


# ══════════════ A3 · 安全区在位 ══════════════
def check_a3(py_src, css):
    ok_vp = "viewport-fit=cover" in py_src
    ok_env = "env(safe-area-inset" in css
    why = []
    if not ok_vp:
        why.append("viewport meta 缺 viewport-fit=cover")
    if not ok_env:
        why.append("CSS 无 env(safe-area-inset-*)")
    return (ok_vp and ok_env), ("; ".join(why) or "viewport-fit=cover + env(safe-area-inset-*) 均在位")


# ══════════════ A4 · 固定宽都能被接住 ══════════════
def check_a4(js_src, css):
    """JS 内联样式里所有 width:Npx（N > MOBILE_W）都要能被 CSS 里某条规则覆盖。

    ★★ 2026-10-12 修一处【判据自身的假阳性】：原来用 `width:(\\d+)px` 匹配，
      而它会连 `max-width:640px` 一起命中（子串）⇒ 把浮层上限（**手机上无害**）
      误报成「未被覆盖的固定宽」。实测由本器负控矩阵抓出。
      ⇒ 改用负向后顾 `(?<![-\\w])width:`，只匹配【真正的 width 属性】。
      ★ 判据的域：模式是子串，对象是属性 —— 二者不同域。
    """
    widths = set()
    for m in re.finditer(r"(?<![-\w])width:(\d+)px", js_src):
        n = int(m.group(1))
        if n > MOBILE_W:
            widths.add(n)
    uncovered = []
    for n in sorted(widths):
        # CSS 覆盖规则形如 [style*="width:620px"] —— 精确匹配该宽度
        if ('width:%dpx"' % n) not in css.replace(" ", ""):
            uncovered.append(n)
    detail = ("固定宽 %s 全部有 CSS 覆盖规则" % sorted(widths)) if not uncovered \
        else ("★ 未被覆盖的固定宽: %s" % uncovered)
    return (len(uncovered) == 0), detail


# ══════════════ A1/A6 · 浏览器侧（横向溢出 / 首屏）══════════════
def _chrome_render(url, out_html, mobile=True):
    if not os.path.exists(CHROME):
        return None, "无 Chrome"
    d = tempfile.mkdtemp(prefix="bbuim-")
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--user-data-dir=" + d, "--virtual-time-budget=9000", "--dump-dom"]
    if mobile:
        cmd.insert(3, "--window-size=%d,844" % MOBILE_W)
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        open(out_html, "w", encoding="utf-8").write(r.stdout or "")
        return r.stdout or "", ""
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def check_a1(tab):
    """★ 横向溢出：渲染后从 DOM 侧无法直接拿 scrollWidth ⇒ 用【固定宽元素是否仍超视口】间接判。
    更准确的做法需 CDP；本器用可判定的替代口径，并在输出里【显式声明口径】。"""
    out = os.path.join(tempfile.gettempdir(), "bbuim-%s.html" % tab.replace("/", "_"))
    html, err = _chrome_render("%s/#%s" % (BASE, tab), out)
    if html is None:
        return None, "UNCOVERED（%s）" % err
    body = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S)
    # 口径：渲染体里若出现 >390px 的【内联固定宽】元素 ⇒ 溢出未修
    over = [int(n) for n in re.findall(r"style=\"[^\"]*width:(\d+)px", body) if int(n) > MOBILE_W]
    if over:
        return False, "★ 渲染体里仍有 >390px 的固定宽元素: %s" % sorted(set(over))
    return True, "渲染体中无 >390px 内联固定宽（口径：内联 width，非完整 scrollWidth）"


# ══════════════ 自检 · 负控矩阵 ══════════════
def selftest():
    """★ 判据必须会红 —— 否则它只是日志。"""
    fails = []
    def ck(name, cond, detail=""):
        print("  %s %-54s %s" % ("OK  " if cond else "FAIL", name, detail))
        if not cond:
            fails.append(name)

    js = _read(JS); css = _read(CSS); py = _read(PY)

    # A2 负控：造一个含桌面词的中文字面量 ⇒ 必须红
    fake_js = js + "\nconst _x='🖱 拖拽 · 滚轮缩放 · hover 高亮';\n"
    ok, bad = check_a2(fake_js, py)
    ck("★ 负控 A2：含「滚轮/hover」的字面量必须红", not ok and len(bad) >= 1, "命中 %d" % len(bad))
    # A2 正控
    ok, bad = check_a2(js, py)
    ck("正控 A2：当前源码必须绿", ok, "命中 %d" % len(bad))

    # A2b 负控：只有 mousemove 没有 pointerdown ⇒ 必须红
    ok, d = check_a2b("cv.addEventListener('mousemove',f)")
    ck("★ 负控 A2b：只有 mousemove 必须红", not ok, d)
    ok, d = check_a2b(js)
    ck("正控 A2b：当前源码必须绿", ok, d)

    # A3 负控：去掉 viewport-fit ⇒ 必须红
    ok, d = check_a3(py.replace("viewport-fit=cover", ""), css)
    ck("★ 负控 A3：去掉 viewport-fit 必须红", not ok, d)
    ok, d = check_a3(py, css)
    ck("正控 A3：当前源码必须绿", ok, d)

    # A4 负控：造一个未覆盖的 999px ⇒ 必须红
    ok, d = check_a4(js + "\ncard.style.cssText='position:fixed;width:999px';", css)
    ck("★ 负控 A4：未覆盖的 999px 必须红", not ok, d)
    ok, d = check_a4(js, css)
    ck("正控 A4：当前源码必须绿", ok, d)

    print("\n  %s" % ("负控矩阵全过（%d 项）" % 8 if not fails else "失败: %s" % ", ".join(fails)))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--static-only", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        print("════ bb-ui-mobile-check · 负控矩阵 ════")
        return selftest()

    print("════ SystemGraph 移动端体验判据门 ════")
    js, css, py = _read(JS), _read(CSS), _read(PY)
    print("  被测：bb-gallery-ui.css / .js / bb-blueprint-gallery.py")
    print("  视口口径：%d x 844（iPhone 16 Pro 逻辑尺寸）" % MOBILE_W)
    print()
    rows = []
    ok, d = check_a2(js, py);  rows.append(("A2  零桌面措辞", ok, d if not ok else d))
    ok, d = check_a2b(js);     rows.append(("A2b 触摸等价", ok, d))
    ok, d = check_a3(py, css); rows.append(("A3  安全区在位", ok, d))
    ok, d = check_a4(js, css); rows.append(("A4  固定宽覆盖", ok, d))
    if a.static_only:
        rows.append(("A1  横向溢出", None, "UNCOVERED（--static-only）"))
    else:
        for tab in ("dash", "relations"):
            ok, d = check_a1(tab)
            rows.append(("A1  %s 无溢出" % tab, ok, d))
    print("  %-20s %-10s %s" % ("判据", "结果", "说明"))
    print("  " + "─" * 84)
    hard_fail = 0
    for name, ok, d in rows:
        tag = "OK" if ok is True else ("UNCOVERED" if ok is None else "FAIL")
        if ok is False:
            hard_fail += 1
        print("  %-20s %-10s %s" % (name, tag, d))
    print("  " + "─" * 84)
    print("  ★ UNCOVERED 不等于通过 —— 它是「本机跑不了该项」，须另行覆盖。")
    print("  总判：%s" % ("★ 红（%d 项 FAIL）" % hard_fail if hard_fail else "通过（无 FAIL）"))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
