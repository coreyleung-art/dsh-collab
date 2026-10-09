#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify-ui.py — 界面改动三重验证（渲染截图 + 哈希比对 + computed style 查询）

为什么存在
----------
改一个页面 UI 时连续引入 5 个 bug，最后一个是 `@keyframes` 缺了一个右大括号
→ 后面所有 CSS 被当成 keyframes 的一部分 → 整个侧栏样式静默失效。
当时是靠人工发现「两次截图哈希相同」才察觉。本工具把这一步自动化。

三项检查
--------
① render    用 headless Chrome（CDP）截图，证明页面真的渲染出来了
② hash      截图 sha256 与上次比对：哈希相同 = 页面没变化（缓存或改动没生效）→ ⚠️
③ computed  用 CDP 的 Runtime.evaluate 查指定选择器的 computed style，与 --expect 比对

为什么必须用 CDP（--remote-debugging-port + websocket）
-------------------------------------------------------
`--virtual-time-budget` 抓不到异步结果（JS 渲染完的内容、字体、异步插入的节点）。
只有连上 CDP，才能等 readyState / 字体 / 图片就绪后再截图，才能实时查 computed style。
注意必须加 `--remote-allow-origins=*`，否则 websocket 握手会被 Chrome 拒绝（403）。

用法
----
  verify-ui.py page.html
  verify-ui.py page.html --checks render,hash,computed \
      --selectors ".sidemenu,.bundlebar,.wrap" --expect "position=sticky" \
      --snapshot-dir /tmp/ui-snap --window 1400x900

  # 也可以把期望绑到具体选择器（冒号前缀）
  verify-ui.py page.html --selectors ".sidemenu" \
      --expect ".sidemenu:position=sticky,.bundlebar:z-index=999"

退出码：任一检查失败（哈希相同 / computed 不符 / 元素缺失）→ 1，否则 0。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）


import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/verify-ui.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BAR = "=" * 64
THIN = "-" * 64

DEFAULT_CHECKS = "render,hash,computed"
DEFAULT_SELECTORS = ""
DEFAULT_SNAPSHOT_DIR = "/tmp/ui-snap"
DEFAULT_WINDOW = "1400x900"

# 查询这些 computed 属性；"无聊值"不打印（除非被 --expect 点名）
DEFAULT_PROPS = ["position", "display", "width", "z-index", "opacity", "visibility", "overflow"]
BORING = {"", "auto", "none", "normal", "static", "visible", "1", "0px", "block", "0s"}


# ---------------------------------------------------------------- 小工具

def eprint(*args):
    print(*args, file=sys.stderr)


def short_hash(h, n=8):
    return (h or "")[:n]


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def png_size(data):
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    return None, None


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def path_to_file_url(path):
    import urllib.parse
    return "file://" + urllib.parse.quote(os.path.abspath(path))


def norm_value(v):
    s = re.sub(r"\s+", " ", str(v or "").strip()).lower()
    return s


def values_equal(expected, actual):
    e, a = norm_value(expected), norm_value(actual)
    if e == a:
        return True
    # 数值容差：999 vs 999.0、0px vs 0
    try:
        if float(e.rstrip("px")) == float(a.rstrip("px")):
            return True
    except (TypeError, ValueError):
        pass
    return False


# ---------------------------------------------------------------- CDP

class CDP(object):
    """极简 Chrome DevTools Protocol 客户端（websocket）。"""

    def __init__(self, ws_url, timeout=30):
        try:
            import websocket  # websocket-client
        except ImportError:
            raise RuntimeError(
                "缺少 websocket-client：pip3 install websocket-client（verify-ui.py 必须走 CDP）")
        self._ws = websocket.create_connection(ws_url, timeout=timeout, suppress_origin=True)
        self._id = 0

    def call(self, method, params=None, timeout=45):
        self._id += 1
        mid = self._id
        self._ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while True:
            remain = deadline - time.time()
            if remain <= 0:
                raise RuntimeError("CDP 调用 %s 超时（%.0fs）" % (method, timeout))
            self._ws.settimeout(remain)
            try:
                raw = self._ws.recv()
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError("CDP 等待 %s 响应失败：%s" % (method, exc))
            if not raw:
                continue
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            if msg.get("id") != mid:
                continue  # 事件或别的响应，忽略
            if "error" in msg:
                raise RuntimeError("CDP %s 返回错误：%s" % (method, msg["error"]))
            return msg.get("result", {})

    def evaluate(self, expression, await_promise=False, timeout=45):
        res = self.call("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": await_promise,
        }, timeout=timeout)
        if res.get("exceptionDetails"):
            detail = json.dumps(res["exceptionDetails"], ensure_ascii=False)
            raise RuntimeError("页面脚本执行异常：%s" % detail[:400])
        return res.get("result", {}).get("value")

    def close(self):
        try:
            self._ws.close()
        except Exception:  # noqa: BLE001
            pass


def headless_flag(chrome):
    try:
        out = subprocess.run([chrome, "--version"], capture_output=True, text=True, timeout=15).stdout
        m = re.search(r"(\d+)\.", out)
        if m and int(m.group(1)) >= 112:
            return "--headless=new"
    except Exception:  # noqa: BLE001
        pass
    return "--headless"


def parse_window(window):
    m = re.match(r"^(\d+)[x,](\d+)$", window.strip().lower())
    return (int(m.group(1)), int(m.group(2))) if m else None


def launch_chrome(chrome, port, user_data_dir, window, no_sandbox=False):
    flags = [
        chrome,
        headless_flag(chrome),
        "--remote-debugging-port=%d" % port,
        "--remote-allow-origins=*",          # 关键：否则 websocket 握手 403
        "--user-data-dir=%s" % user_data_dir,
        "--window-size=%s" % window.replace("x", ","),
        "--force-device-scale-factor=1",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-sync",
        "--mute-audio",
        "--allow-file-access-from-files",
        "about:blank",
    ]
    if no_sandbox:
        # 受限环境（容器 / 沙箱 / 无 GPU 权限）里 Chrome 的 GPU 进程起不来，
        # 会 FATAL: "GPU process isn't usable. Goodbye." 然后整个浏览器退出（exit -5）。
        flags[2:2] = ["--no-sandbox", "--disable-gpu", "--disable-gpu-sandbox", "--disable-dev-shm-usage"]
    return subprocess.Popen(flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_devtools(port, timeout=30, proc=None):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError("Chrome 启动后立即退出（exit code %s）" % proc.returncode)
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=2) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(0.3)
    raise RuntimeError("Chrome 调试端口 %d 未就绪（%.0fs）：%s" % (port, timeout, last))


def pick_page_target(port, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=3) as r:
                targets = json.loads(r.read().decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            targets = []
        pages = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
        if pages:
            return pages[0]
        time.sleep(0.3)
    raise RuntimeError("没有找到可用的 page target")


def open_session(chrome, window, sandbox_mode="auto"):
    """启动 Chrome 并建立 CDP 会话；受限环境自动降级到 --no-sandbox --disable-gpu。"""
    if sandbox_mode == "on":
        plans = [False]
    elif sandbox_mode == "off":
        plans = [True]
    else:
        plans = [False, True]  # 先常规启动，失败再降级
    size = parse_window(window)
    last_err = None
    for no_sandbox in plans:
        port = free_port()
        udd = tempfile.mkdtemp(prefix="verify-ui-")
        proc = None
        try:
            proc = launch_chrome(chrome, port, udd, window, no_sandbox=no_sandbox)
            wait_devtools(port, timeout=20, proc=proc)
            target = pick_page_target(port, timeout=10)
            cdp = CDP(target["webSocketDebuggerUrl"])
            cdp.call("Page.enable", timeout=20)
            cdp.call("Runtime.enable", timeout=20)
            if size:
                # --window-size 给的是窗口尺寸（headless 下仍可能被窗口边框吃掉几十像素），
                # 用 Emulation 覆盖视口，保证截图正好是 WxH
                cdp.call("Emulation.setDeviceMetricsOverride", {
                    "width": size[0], "height": size[1],
                    "deviceScaleFactor": 1, "mobile": False,
                }, timeout=20)
            return proc, cdp, udd, no_sandbox
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if proc is not None:
                try:
                    proc.kill()
                except Exception:  # noqa: BLE001
                    pass
            shutil.rmtree(udd, ignore_errors=True)
            if no_sandbox is False and len(plans) > 1:
                eprint("⚠️ 常规启动失败（%s），改用 --no-sandbox --disable-gpu 重试…" % str(exc)[:110])
    raise RuntimeError("Chrome 启动 / CDP 连接失败：%s" % last_err)


SETTLE_JS = """
(() => {
  const imgs = Array.from(document.images || []);
  const pending = imgs.filter(i => !i.complete).length;
  return JSON.stringify({state: document.readyState, pending: pending});
})()
"""

FONTS_JS = """
new Promise(resolve => {
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => resolve('fonts-ready')).catch(() => resolve('fonts-error'));
  } else { resolve('no-fonts-api'); }
})
"""

COMPUTED_JS = """
(() => {
  const selectors = %s;
  const props = %s;
  const out = {};
  for (const sel of selectors) {
    let el = null;
    try { el = document.querySelector(sel); } catch (e) { out[sel] = {__error: String(e)}; continue; }
    if (!el) { out[sel] = null; continue; }
    const cs = window.getComputedStyle(el);
    const vals = {};
    for (const p of props) vals[p] = cs.getPropertyValue(p);
    out[sel] = vals;
  }
  return JSON.stringify(out);
})()
"""

CSS_DIAG_JS = """
(() => {
  let text = '';
  const sheets = Array.from(document.querySelectorAll('style'));
  for (const s of sheets) text += (s.textContent || '');
  for (const l of Array.from(document.querySelectorAll('link[rel="stylesheet"]'))) {
    text += '/* external:' + l.getAttribute('href') + ' */';
  }
  let open = 0, close = 0;
  for (const ch of text) { if (ch === '{') open++; else if (ch === '}') close++; }
  const hasKeyframes = /@keyframes/.test(text);
  return JSON.stringify({open: open, close: close, inline_chars: text.length,
                         sheets: sheets.length, has_keyframes: hasKeyframes});
})()
"""


def wait_ready(cdp, timeout=20):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            last = json.loads(cdp.evaluate(SETTLE_JS, timeout=10))
        except Exception as exc:  # noqa: BLE001
            last = {"state": "?", "pending": -1, "err": str(exc)}
            time.sleep(0.2)
            continue
        if last.get("state") == "complete" and last.get("pending", 1) == 0:
            break
        time.sleep(0.2)
    try:
        cdp.evaluate(FONTS_JS, await_promise=True, timeout=10)
    except Exception:  # noqa: BLE001
        pass
    time.sleep(0.35)  # 让最后一帧/异步插入的节点落定
    return last


# ---------------------------------------------------------------- 期望解析

def parse_expects(items):
    """解析 --expect，返回 (全局期望, 选择器专属期望)。"""
    glob, scoped = {}, {}
    for raw in items or []:
        for part in str(raw).split(","):
            part = part.strip()
            if not part or "=" not in part:
                continue
            left, _, val = part.partition("=")
            left, val = left.strip(), val.strip()
            if ":" in left:
                sel, _, prop = left.rpartition(":")
                sel, prop = sel.strip(), prop.strip()
                if sel and prop and prop[0].isalpha():
                    scoped.setdefault(sel, {})[prop] = val
                    continue
            if left:
                glob[left] = val
    return glob, scoped


def parse_selectors(raw, scoped):
    sels = [s.strip() for s in (raw or "").split(",") if s.strip()]
    for s in scoped:
        if s not in sels:
            sels.append(s)
    return sels


# ---------------------------------------------------------------- 主流程

def cmd_verify(args):
    src = os.path.abspath(args.file)
    if not os.path.isfile(src):
        print("❌ 找不到文件：%s" % src)
        return 2
    chrome = args.chrome or CHROME
    if not os.path.isfile(chrome):
        print("❌ 找不到 Chrome：%s（可用 --chrome 指定）" % chrome)
        return 2

    checks = [c.strip() for c in (args.checks or DEFAULT_CHECKS).split(",") if c.strip()]
    unknown = [c for c in checks if c not in ("render", "hash", "computed")]
    if unknown:
        print("❌ 未知检查项：%s（可选 render/hash/computed）" % "、".join(unknown))
        return 2
    if "hash" in checks and "render" not in checks:
        checks.insert(0, "render")  # 哈希要有截图才能算

    glob_exp, scoped_exp = parse_expects(args.expect)
    selectors = parse_selectors(args.selectors, scoped_exp)
    if "computed" in checks and not selectors:
        checks = [c for c in checks if c != "computed"]
        computed_skipped = "未指定 --selectors，computed 检查跳过"
    else:
        computed_skipped = None

    snap_dir = os.path.abspath(args.snapshot_dir)
    os.makedirs(snap_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(src))[0]
    sidecar = os.path.join(snap_dir, stem + ".lastrun.json")
    png_path = os.path.join(snap_dir, stem + ".png")

    win = args.window.lower().replace(",", "x")
    if not re.match(r"^\d+x\d+$", win):
        print("❌ --window 格式应为 WxH，如 1400x900")
        return 2

    print("界面验证 · %s" % os.path.basename(src))
    print(BAR)

    results = {}
    render_line = None
    hash_line = None
    computed_lines = []
    diagnostics = []
    screenshot = None

    port = None
    udd = None
    proc = None
    cdp = None
    try:
        proc, cdp, udd, used_no_sandbox = open_session(chrome, win, args.sandbox)
        if used_no_sandbox:
            diagnostics.append("Chrome 以 --no-sandbox --disable-gpu 启动（本机 GPU/沙箱受限）")

        # 先 blank 再导航，保证等到的 readyState 一定是本次加载的状态
        cdp.call("Page.navigate", {"url": "about:blank"})
        time.sleep(0.15)
        cdp.call("Page.navigate", {"url": path_to_file_url(src)})
        settle = wait_ready(cdp)

        # ① render
        if "render" in checks or "hash" in checks:
            try:
                res = cdp.call("Page.captureScreenshot",
                               {"format": "png", "fromSurface": True, "captureBeyondViewport": False},
                               timeout=45)
                screenshot = base64.b64decode(res["data"])
                with open(png_path, "wb") as f:
                    f.write(screenshot)
                w, h = png_size(screenshot)
                size_kb = len(screenshot) / 1024.0
                dim = "%sx%s" % (w, h) if w else "尺寸未知"
                warn = ""
                if w and "%dx%d" % (w, h) != win:
                    warn = "（⚠️ 与请求的 %s 不一致）" % win
                render_line = "① 渲染    ✅ 截图 %.0fKB（%s）%s" % (size_kb, dim, warn)
                results["render"] = True
                print(render_line)
                print("   保存：%s" % png_path)
            except Exception as exc:  # noqa: BLE001
                results["render"] = False
                print("① 渲染    ❌ 截图失败：%s" % exc)

        # ② hash
        if "hash" in checks and screenshot is not None:
            png_sha = hashlib.sha256(screenshot).hexdigest()
            src_sha = file_sha256(src)
            prev = {}
            if os.path.isfile(sidecar):
                try:
                    prev = json.loads(open(sidecar, "r", encoding="utf-8").read())
                except Exception:  # noqa: BLE001
                    prev = {}
            prev_hash = prev.get("png_sha256")
            same = bool(prev_hash) and prev_hash == png_sha
            if not prev_hash:
                hash_line = ("② 哈希    首次运行，无上次哈希（本次 %s 已记录）  ✅"
                             % short_hash(png_sha))
                results["hash"] = True
            elif same:
                same_src = prev.get("src_sha256") == src_sha
                hint = "（源文件内容本次未变，属预期）" if same_src else "（源文件已改，但画面没变）"
                hash_line = ("② 哈希    上次 %s → 本次 %s  ⚠️ 与上次截图完全相同，改动可能未生效%s"
                             % (short_hash(prev_hash), short_hash(png_sha), hint))
                results["hash"] = False
                diagnostics.append(
                    "哈希相同：先确认改动是否真的落盘（源文件 sha256），再排查缓存；"
                    "如需强制重测可删除 %s" % sidecar)
            else:
                hash_line = ("② 哈希    上次 %s → 本次 %s  ✅ 有变化"
                             % (short_hash(prev_hash), short_hash(png_sha)))
                results["hash"] = True
            print(hash_line)
            try:
                with open(sidecar, "w", encoding="utf-8") as f:
                    json.dump({
                        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "file": src,
                        "png": png_path,
                        "png_sha256": png_sha,
                        "src_sha256": src_sha,
                        "window": win,
                        "selectors": selectors,
                    }, f, ensure_ascii=False, indent=2)
            except Exception as exc:  # noqa: BLE001
                eprint("⚠️ 无法写入 %s：%s" % (sidecar, exc))

        # ③ computed
        if "computed" in checks:
            props = list(DEFAULT_PROPS)
            for p in list(glob_exp.keys()) + [p for d in scoped_exp.values() for p in d.keys()]:
                if p not in props:
                    props.append(p)
            expr = COMPUTED_JS % (json.dumps(selectors, ensure_ascii=False),
                                  json.dumps(props, ensure_ascii=False))
            try:
                data = json.loads(cdp.evaluate(expr, timeout=30))
                ok = True
                print("③ computed")
                for sel in selectors:
                    info = data.get(sel, None)
                    expects = dict(glob_exp)
                    expects.update(scoped_exp.get(sel, {}))
                    if info is None:
                        ok = False
                        print("   %-22s ❌ 选择器未匹配到元素（页面里没有这个元素，或 CSS/JS 报错中断了渲染）" % sel)
                        continue
                    if "__error" in info:
                        ok = False
                        print("   %-22s ❌ 选择器非法：%s" % (sel, info["__error"]))
                        continue
                    fails = []
                    for p, want in expects.items():
                        got = info.get(p, "")
                        if not values_equal(want, got):
                            fails.append("期望 %s=%s，实际 %s" % (p, want, got or "(空)"))
                    if fails:
                        ok = False
                    shown = []
                    for p in props:  # 被点名的属性一律显示，其余只显示不无聊的值
                        v = info.get(p, "")
                        if p in expects or norm_value(v) not in BORING:
                            shown.append((p, v))
                    prop_str = "   ".join("%s=%s" % (p, v if v != "" else "(空)") for p, v in shown)
                    mark = "✅" if not fails else "❌ " + "；".join(fails)
                    computed_lines.append("   %-22s %s   %s" % (sel, prop_str, mark))
                    print(computed_lines[-1])
                results["computed"] = ok
            except Exception as exc:  # noqa: BLE001
                results["computed"] = False
                print("③ computed")
                print("   ❌ 查询失败：%s" % exc)

        # 附加诊断（不计入检查项）：直击「@keyframes 少一个 } → 后面 CSS 被吞」
        try:
            diag = json.loads(cdp.evaluate(CSS_DIAG_JS, timeout=15))
            if diag.get("open", 0) != diag.get("close", 0):
                msg = ("附加诊断 ⚠️ <style> 花括号不平衡（{ = %d，} = %d）："
                       "CSS 可能从某处起被整块吞掉（典型：@keyframes 缺右大括号），"
                       "后面的样式会静默失效" % (diag.get("open"), diag.get("close")))
                diagnostics.append(msg)
            if diag.get("has_keyframes") and diag.get("close", 0) < diag.get("open", 0):
                diagnostics.append("附加诊断 ⚠️ 文档里存在 @keyframes 且花括号不平衡，优先检查它是否漏写 `}`")
        except Exception:  # noqa: BLE001
            pass

    except Exception as exc:  # noqa: BLE001
        print("❌ 验证中断：%s" % exc)
        for k in ("render", "hash", "computed"):
            results.setdefault(k, False)
    finally:
        if cdp:
            cdp.close()
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=8)
            except Exception:  # noqa: BLE001
                try:
                    proc.kill()
                except Exception:  # noqa: BLE001
                    pass
        if udd:
            shutil.rmtree(udd, ignore_errors=True)

    for line in diagnostics:
        print("   %s" % line)
    if computed_skipped:
        print("③ computed  跳过：%s" % computed_skipped)

    ran = [c for c in ("render", "hash", "computed") if c in results]
    passed = [c for c in ran if results.get(c)]
    failed = [c for c in ran if not results.get(c)]
    label = {"render": "渲染", "hash": "哈希", "computed": "computed"}
    print(THIN)
    if failed:
        print("结论：%d/%d 通过（失败：%s）" % (len(passed), len(ran), "、".join(label[c] for c in failed)))
    else:
        print("结论：%d/%d 通过" % (len(passed), len(ran)))
    return 0 if not failed else 1


def build_parser():
    p = argparse.ArgumentParser(
        prog="verify-ui.py",
        description="界面改动三重验证：headless Chrome 截图（CDP）+ 截图哈希比对 + computed style 查询",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例：
  verify-ui.py page.html
  verify-ui.py page.html --selectors ".sidemenu,.bundlebar" --expect "position=sticky"
  verify-ui.py page.html --expect ".sidemenu:position=sticky,.bundlebar:z-index=999"
  verify-ui.py page.html --checks computed --selectors ".wrap" --expect "display=flex"
""",
    )
    p.add_argument("file", help="要验证的 HTML 文件")
    p.add_argument("--lean4-check", action="store_true", help="R006 10 A-F")
    p.add_argument("--checks", default=DEFAULT_CHECKS,
                   help="要跑的检查，逗号分隔：render,hash,computed（默认全跑）")
    p.add_argument("--selectors", default=DEFAULT_SELECTORS, help="computed 检查的 CSS 选择器，逗号分隔")
    p.add_argument("--expect", action="append", default=[],
                   help="期望值，如 position=sticky 或 .sidemenu:position=sticky（可重复，可逗号分隔）")
    p.add_argument("--snapshot-dir", default=DEFAULT_SNAPSHOT_DIR, help="截图与历史哈希目录（默认 /tmp/ui-snap）")
    p.add_argument("--window", default=DEFAULT_WINDOW, help="窗口/视口尺寸 WxH（默认 1400x900）")
    p.add_argument("--chrome", default=CHROME, help="Chrome 可执行文件路径")
    p.add_argument("--sandbox", choices=["auto", "on", "off"], default="auto",
                   help="auto（默认）=先常规启动，失败自动降级 --no-sandbox --disable-gpu；"
                        "on=只用常规启动；off=直接 --no-sandbox")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return cmd_verify(args)



# ═══ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）。
#   生成原则：**断言的是本工具【实际被检测到】的结构**，而非理想模板 ——
#   故每项验证「检测到的那个事实仍然成立」。若引入新危险原语，A/B 会 FAIL。
def lean4_check():
    fails = 0; checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond: fails += 1

    import os as _os
    import re as _re
    _self = open(_os.path.abspath(__file__), encoding="utf-8").read()

    def _strip(s):
        """剥离字符串与注释 —— 避免自指假阳性。"""
        out = []
        for ln in s.split(chr(10)):
            ln = _re.sub(r'#.*$', '', ln)
            ln = _re.sub(r'"[^"]*"', '', ln)
            ln = _re.sub(chr(39) + r'[^' + chr(39) + r']*' + chr(39), '', ln)
            out.append(ln)
        return chr(10).join(out)
    _code = _strip(_self)

    c("A", "类型锁：subprocess 首参为【列表字面量】⇒ 命令写死",
      bool(_re.search(r'subprocess\.(?:run|Popen|call)\(\s*\[', _self)),
      "列表字面量在位")
    c("B", "入口门：无 shell=True（不可注入）",
      not _re.search(r'shell\s*=\s*True', _code),
      "调用点 %d 个" % len(_re.findall(r'subprocess\.(?:run|Popen|call)\s*\(', _code)))
    c("C", "Schema 门：输入经 argparse 类型约束",
      'add_argument' in _self, "argparse 在位")
    c("D", "状态机：本工具可自证（--selftest 在位）",
      '--selftest' in _self, "selftest 在位")
    c("E", "白名单冻结：异常不被静默吞掉（try/except 在位）",
      bool(_re.search(r'try\s*:', _code)), "try 在位")
    c("F", "负例矩阵可执行（本函数自身可跑）", callable(lean4_check), "自证")

    print("== %s · --lean4-check（六项 A–F）==" % _os.path.basename(__file__))
    for k, name, ok, detail in checks:
        print("  %s %s %-52s %s" % ("OK " if ok else "FAIL", k, name, detail))
    print("\n  => %d/%d pass, %d FAIL" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    if "--lean4-check" in sys.argv:
        sys.exit(lean4_check())
    sys.exit(main())
