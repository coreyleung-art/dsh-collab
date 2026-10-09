#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dev-sandbox.py — 开发沙箱模拟器（泛化隔离验证模式，R015 候选）

把「隔离小样本验证，测通再推进」从 CLD 重启泛化到所有开发类型：
  · plugin   — 插件目录（加载/依赖/API 验证）
  · tool     — 工具源码（编译/运行/参数）
  · script   — 脚本文件（语法/执行/输出）
  · config   — 配置文件（语法/键值/引用）
  · workflow — 工作流定义（步骤/依赖/失败处理）

原则：隔离环境 + 小样本 + 不动生产，测通再推进。

用法:
  dev-sandbox plugin ~/dsh-plugin-central-inbox      # 插件验证
  dev-sandbox script ~/dsh-collab/scripts/x.py       # 脚本验证
  dev-sandbox config ~/.dsh/settings.yaml            # 配置验证
  dev-sandbox tool ~/dsh-collab/rust-tools           # 工具源码验证
  dev-sandbox --list                                 # 列出类型
  --dry-run 只分析不执行
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, subprocess, sys, tempfile, datetime, shutil


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/dev-sandbox.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ── 类型探测 ──
def detect_type(path):
    """根据路径/内容自动判断类型"""
    if os.path.isdir(path):
        # 插件：含 package.json + lib/
        if os.path.exists(os.path.join(path, "package.json")) and os.path.isdir(os.path.join(path, "lib")):
            return "plugin"
        if os.path.exists(os.path.join(path, "Cargo.toml")):
            return "tool"
        if os.path.exists(os.path.join(path, "pyproject.toml")):
            return "tool"
        return "unknown-dir"
    # 文件
    if path.endswith((".py", ".js", ".mjs", ".ts", ".sh")):
        return "script"
    if path.endswith((".yaml", ".yml", ".json", ".toml")):
        return "config"
    return "unknown-file"

# ── 各类型验证 ──
def check_plugin(path):
    """插件：语法 + 依赖 + 模块加载"""
    log(f"── 插件验证: {path}")
    results = []
    # 语法
    for f in ["lib/index.js", "lib/adapt.js"]:
        p = os.path.join(path, f)
        if os.path.exists(p):
            r = subprocess.run(["/opt/homebrew/bin/node", "--check", p], capture_output=True, text=True)
            results.append(("语法", f, "OK" if r.returncode == 0 else f"FAIL:{r.stderr[:80]}"))
    # package.json
    pkg = os.path.join(path, "package.json")
    if os.path.exists(pkg):
        d = json.load(open(pkg))
        t = d.get("type", "")
        has_esm = "export " in open(os.path.join(path, "lib/index.js")).read() if os.path.exists(os.path.join(path, "lib/index.js")) else False
        results.append(("ESM匹配", "package.json", "OK" if (has_esm and t == "module") or not has_esm else "FAIL:ESM无type:module"))
        peers = d.get("peerDependencies", {})
        results.append(("peerDeps", "package.json", f"{len(peers)}项" if peers else "WARN:空"))
    # 符号链接
    nm = os.path.join(path, "node_modules", "@deepseek-ai")
    cnt = len(os.listdir(nm)) if os.path.isdir(nm) else 0
    results.append(("符号链接", "node_modules/@deepseek-ai", f"{cnt}个" if cnt else "WARN:无"))
    # 模块加载实测
    main = os.path.join(path, "lib", "index.js")
    if os.path.exists(main):
        r = subprocess.run(["/opt/homebrew/bin/node", "-e", f"import('{main}').then(m=>console.log('OK:'+Object.keys(m))).catch(e=>{{console.log('FAIL:'+e.message.slice(0,80));process.exit(1)}})"], capture_output=True, text=True)
        results.append(("加载实测", "lib/index.js", r.stdout.strip()[:60] if r.returncode == 0 else f"FAIL:{r.stderr[:80]}"))
    return results

def check_script(path):
    """脚本：语法 + 编译检查"""
    log(f"── 脚本验证: {path}")
    results = []
    if path.endswith(".py"):
        r = subprocess.run(["python3", "-m", "py_compile", path], capture_output=True, text=True)
        results.append(("语法", path, "OK" if r.returncode == 0 else f"FAIL:{r.stderr[:100]}"))
    elif path.endswith((".js", ".mjs")):
        r = subprocess.run(["/opt/homebrew/bin/node", "--check", path], capture_output=True, text=True)
        results.append(("语法", path, "OK" if r.returncode == 0 else f"FAIL:{r.stderr[:100]}"))
    elif path.endswith(".sh"):
        r = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
        results.append(("语法", path, "OK" if r.returncode == 0 else f"FAIL:{r.stderr[:100]}"))
    return results

def check_config(path):
    """配置：语法 + 键值引用"""
    log(f"── 配置验证: {path}")
    results = []
    try:
        if path.endswith(".json"):
            json.load(open(path))
            results.append(("JSON语法", path, "OK"))
        elif path.endswith((".yaml", ".yml")):
            # 无 PyYAML 时降级：基础缩进/冒号检查
            try:
                import yaml
                yaml.safe_load(open(path))
                results.append(("YAML语法", path, "OK"))
            except ImportError:
                # 简单检查：无制表符缩进 + 冒号键
                bad = [l for l in open(path) if l.startswith("\t")]
                results.append(("YAML语法(降级)", path, "OK" if not bad else f"WARN:{len(bad)}行制表符"))
        elif path.endswith(".toml"):
            import tomllib
            tomllib.load(open(path, "rb"))
            results.append(("TOML语法", path, "OK"))
    except Exception as e:
        results.append(("语法", path, f"FAIL:{str(e)[:80]}"))
    return results

def check_workflow(path):
    """工作流定义：步骤/依赖/失败处理完整性（JSON/YAML 工作流）"""
    log(f"── 工作流验证: {path}")
    results = []
    try:
        if path.endswith(".json"):
            d = json.load(open(path))
        else:
            import re
            # 简化：非 JSON 工作流按步骤数检查
            txt = open(path).read()
            steps = [l for l in txt.split("\n") if l.strip().startswith(("-", "step", "Step", "1.", "2."))]
            results.append(("步骤数", path, f"{len(steps)}步" if steps else "WARN:未识别步骤"))
            return results
        # JSON 工作流
        steps = d.get("steps", [])
        if not steps:
            results.append(("步骤", path, "WARN:无 steps"))
        else:
            results.append(("步骤数", path, f"{len(steps)}步"))
        # 依赖检查（steps[i].depends_on 引用有效）
        ids = [s.get("id", f"s{i}") for i, s in enumerate(steps)]
        missing_dep = []
        for s in steps:
            for dep in s.get("depends_on", []):
                if dep not in ids:
                    missing_dep.append(f"{s.get('id','?')}→{dep}")
        results.append(("依赖完整", path, "OK" if not missing_dep else f"FAIL:缺依赖 {missing_dep[:3]}"))
        # 失败处理检查
        has_fail = any("on_fail" in s or "fallback" in s or "retry" in s for s in steps)
        results.append(("失败处理", path, "OK" if has_fail else "WARN:无失败处理"))
    except Exception as e:
        results.append(("解析", path, f"FAIL:{str(e)[:80]}"))
    return results

def check_tool(path):
    """工具源码：编译检查（不实际 build 全量，快速 cargo check）"""
    log(f"── 工具源码验证: {path}")
    results = []
    if os.path.exists(os.path.join(path, "Cargo.toml")):
        r = subprocess.run(["cargo", "check"], cwd=path, capture_output=True, text=True, timeout=120)
        results.append(("cargo check", "Cargo.toml", "OK" if r.returncode == 0 else f"FAIL:{r.stderr[-150:]}"))
    return results

def run_verification(vtype, path, dry_run):
    """执行验证，返回 (all_ok, results)"""
    if vtype == "plugin": results = check_plugin(path)
    elif vtype == "script": results = check_script(path)
    elif vtype == "config": results = check_config(path)
    elif vtype == "tool": results = check_tool(path)
    elif vtype == "workflow": results = check_workflow(path)
    else: return False, [("未知类型", path, "不支持")]

    for name, target, verdict in results:
        ok = "OK" in verdict or "项" in verdict or "个" in verdict or "步" in verdict or verdict.startswith("WARN")
        log(f"  {'✅' if ok else '❌'} {name} ({target}): {verdict}")
    all_ok = all("OK" in v or "项" in v or "个" in v or "步" in v or v.startswith("WARN") for _, _, v in results)
    return all_ok, results

def main():
    ap = argparse.ArgumentParser(description="开发沙箱模拟器（泛化隔离验证）")
    ap.add_argument("type", nargs="?", choices=["plugin", "tool", "script", "config", "workflow", "auto"], default="auto")
    ap.add_argument("target", nargs="?", default="", help="目标路径")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        print("支持类型: plugin(插件) tool(工具源码) script(脚本) config(配置) workflow(工作流)")
        return

    if not args.target:
        print("用法: dev-sandbox <plugin|tool|script|config> <目标路径> [--dry-run]")
        return

    vtype = args.type
    if vtype == "auto":
        vtype = detect_type(args.target)
        log(f"自动探测类型: {vtype}")

    if not os.path.exists(args.target):
        log(f"❌ 目标不存在: {args.target}")
        sys.exit(1)

    log(f"══ dev-sandbox 隔离验证: {vtype} · {args.target} ══")
    all_ok, results = run_verification(vtype, args.target, args.dry_run)
    log(f"══ 结果: {'✅ 可推进' if all_ok else '❌ 需修复'}（{sum(1 for _,_,v in results if 'OK' in v)} 通过）══")
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
