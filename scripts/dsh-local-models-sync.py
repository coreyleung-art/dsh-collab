#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dsh-local-models-sync.py — 把本机 Ollama / LM Studio 的模型同步进 DSH 模型选择器。

为什么需要它
------------
DSH 的 llm-pi-ai 路由目录**不会自我刷新**（见 dsh-llm-pi-ai README：
「路由的 catalog 不会自我刷新……路由要多一个模型，得有人写进去」）。
所以 `ollama pull` 或 LM Studio 里新下载模型之后，必须重新把模型清单写进
`$DSH_HOME/settings.yaml` 的 `llm-pi-ai.providers` 才能在选择器里看到。
本脚本把这一步做成一条可复跑的命令。

它做什么
--------
1. 探测 Ollama    GET http://127.0.0.1:11434/api/tags        （能力 / 上下文 / 参数规模）
2. 探测 LM Studio GET http://127.0.0.1:1234/api/v0/models    （类型 / 是否已加载 / 实际上下文）
3. 过滤掉只能做 embedding 的模型（它们不能服务对话，接进来是个坏选项）
4. 只重写 `llm-pi-ai.providers` 下的**托管路由**，其余 provider 文本原样保留（含注释）

托管路由
--------
  ollama           → Ollama 全部可对话模型
  lmstudio-local   → LM Studio 全部可对话模型
  lmstudio         → 只补一个缺了就会 404 的 Authorization 头（模型列表不动）

★ 关于 `lmstudio`：它是 MCP Station 的视觉路由（displayName「MCP Station Vision」），
  由 dsh-plugin-mcp-station 的 saveVision() 写入，那个函数会**整段替换**该 route 的
  profile。所以「用户自己的 LM Studio 模型」放在独立的 lmstudio-local 里，
  不被它覆盖；本脚本只负责把被覆盖掉的 Authorization 头补回来。

写盘安全
--------
默认 **dry-run**（只打印，不落笔）。`--apply` 才真写，且写前自动备份到
`settings.yaml.bak-models-sync-<时间戳>`，只保留最近 3 个。

用法
----
  dsh-local-models-sync.py                 # 预演
  dsh-local-models-sync.py --apply         # 写入（无需重启 DSH，热重载生效）
  dsh-local-models-sync.py --apply --ollama-ctx 32768 --lmstudio-ctx-cap 32768
  dsh-local-models-sync.py --json          # 只输出探测结果，供别的脚本消费
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request

DSH_HOME = os.environ.get("DSH_HOME") or os.path.expanduser("~/.dsh")
SETTINGS = os.path.join(DSH_HOME, "settings.yaml")

OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434")
LMSTUDIO_BASE = os.environ.get("LMSTUDIO_BASE", "http://127.0.0.1:1234")

# Ollama 用这个环境变量决定每个模型的默认上下文；装 Ollama.app 时默认 4096。
# 实测：`ollama ps` 的 CONTEXT 列 = 4096 时，llama-server argv 里就是 `-c 4096`。
OLLAMA_DEFAULT_CTX = 4096

ROUTE_OLLAMA = "ollama"
ROUTE_LMSTUDIO = "lmstudio-local"
ROUTE_VISION = "lmstudio"

# 本地服务不校验密钥，但 pi-ai 的 openai-completions 实现要求
# 「有 key 或有 Authorization 头」二者之一，否则直接抛
# `No API key for provider: <route>`。给个占位头即可。
AUTH_HEADER_VALUE = "Bearer local"

BACKUP_KEEP = 3


# ────────────────────────────── 探测 ──────────────────────────────

def _get_json(url, timeout=6):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def probe_ollama():
    """返回 (models, error)。models 元素为 dict。"""
    try:
        data = _get_json(OLLAMA_BASE + "/api/tags")
    except Exception as exc:  # noqa: BLE001 — 如实报错，不假装成功
        return None, "{} 不可达：{}".format(OLLAMA_BASE, exc)

    out = []
    for m in data.get("models") or []:
        name = m.get("name")
        if not name:
            continue
        details = m.get("details") or {}
        caps = m.get("capabilities")
        # capabilities 缺失时按「有 completion 能力」保守放行（老版本 Ollama 不返回该字段）
        chat_capable = True if caps is None else ("completion" in caps)
        out.append({
            "id": name,
            "chat_capable": bool(chat_capable),
            "capabilities": caps or [],
            "vision": bool(caps is not None and "vision" in caps),
            "tools": bool(caps is not None and "tools" in caps),
            "model_max_ctx": details.get("context_length") or 0,
            "parameter_size": details.get("parameter_size") or "",
            "quantization": details.get("quantization_level") or "",
        })
    return out, None


def probe_lmstudio():
    """返回 (models, error)。先试原生 /api/v0/models（带实际上下文），退回 /v1/models。"""
    try:
        data = _get_json(LMSTUDIO_BASE + "/api/v0/models")
        rich = True
    except Exception:
        try:
            data = _get_json(LMSTUDIO_BASE + "/v1/models")
            rich = False
        except Exception as exc:  # noqa: BLE001
            return None, "{} 不可达：{}".format(LMSTUDIO_BASE, exc)

    out = []
    for m in data.get("data") or []:
        mid = m.get("id")
        if not mid:
            continue
        mtype = (m.get("type") or "llm") if rich else "llm"
        caps = m.get("capabilities") or []
        out.append({
            "id": mid,
            "chat_capable": mtype != "embeddings",
            "type": mtype,
            "vision": mtype == "vlm",
            "tools": "tool_use" in caps,
            "model_max_ctx": m.get("max_context_length") or 0,
            # 已加载的模型，LM Studio 会报它**实际**用多少上下文（按显存自动算）；
            # 未加载时是 None —— 那时只能报模型上限。
            "loaded_ctx": m.get("loaded_context_length"),
            "state": m.get("state") or "",
            "quantization": m.get("quantization") or "",
            "publisher": m.get("publisher") or "",
        })
    return out, None


def ollama_serving_ctx():
    """Ollama 实际提供的上下文长度。模型上限常远大于它，写错会让 DSH 静默截断。"""
    for src in (os.environ.get("OLLAMA_CONTEXT_LENGTH"),):
        if src and str(src).strip().isdigit():
            return int(str(src).strip())
    # launchctl getenv：Ollama.app 由 launchd 启动时环境变量落在这里
    try:
        import subprocess
        val = subprocess.run(
            ["launchctl", "getenv", "OLLAMA_CONTEXT_LENGTH"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        if val.isdigit():
            return int(val)
    except Exception:  # noqa: BLE001
        pass
    return OLLAMA_DEFAULT_CTX


# ────────────────────────── 组装路由 YAML ──────────────────────────

def q(s):
    """YAML 双引号标量 —— JSON 字符串恰好是合法的 YAML 双引号形式。"""
    return json.dumps(str(s), ensure_ascii=False)


def render_route(key, display_name, base_url, models, default_max_tokens):
    lines = [
        "    {}:".format(key),
        "      displayName: {}".format(q(display_name)),
        "      api: openai-completions",
        "      baseURL: {}".format(q(base_url)),
        "      # pi-ai 的 openai-completions 实现要求「有 key 或有 Authorization 头」，",
        "      # 否则抛 `No API key for provider`。本地服务不校验该头，给占位值即可。",
        "      headers:",
        "        Authorization: {}".format(q(AUTH_HEADER_VALUE)),
        "      # 官方 providers.zh.md：pi-ai 对不认识的地址按 OpenAI 本身对待，",
        "      # 会发 role=developer 与 max_completion_tokens —— 本地端点多数拒绝这两样。",
        "      compat:",
        "        supportsDeveloperRole: false",
        "        maxTokensField: max_tokens",
        "      defaultMaxTokens: {}".format(default_max_tokens),
        "      models:",
    ]
    for m in models:
        lines.append("        - id: {}".format(q(m["id"])))
        lines.append("          name: {}".format(q(m["name"])))
        if m.get("context_window"):
            lines.append("          contextWindow: {}".format(m["context_window"]))
        if m.get("max_tokens"):
            lines.append("          maxTokens: {}".format(m["max_tokens"]))
        lines.append("          input:")
        lines.append("            - text")
        if m.get("vision"):
            lines.append("            - image")
    return lines


def humanize(m, kind):
    """给模型一个便于在选单里认出来的名字，并把限制写在名字里。"""
    if kind == "ollama":
        base = m["id"]
        if m.get("parameter_size"):
            base += "（{}）".format(m["parameter_size"])
    else:
        base = m["id"]
    notes = []
    if m.get("vision"):
        notes.append("视觉")
    if m.get("chat_capable") and not m.get("tools"):
        notes.append("无工具调用")
    if notes:
        base += " · " + " · ".join(notes)
    return base


def build_plan(args):
    report = {"ok": True, "warnings": [], "routes": {}}

    # ── Ollama ──
    ollama_models, ollama_err = probe_ollama()
    if ollama_err:
        report["warnings"].append("Ollama：" + ollama_err + "（跳过该路由，其余照常）")
        ollama_models = []
    serving = args.ollama_ctx or ollama_serving_ctx()
    o_models = []
    excluded_o = []
    for m in ollama_models:
        if not m["chat_capable"]:
            excluded_o.append(m["id"])
            continue
        # 取「模型上限」与「Ollama 实际提供」的较小者：写大了 DSH 会以为装得下而静默截断。
        cap = m["model_max_ctx"] or serving
        ctx = min(cap, serving)
        o_models.append({
            "id": m["id"],
            "name": humanize(m, "ollama"),
            "context_window": ctx,
            "max_tokens": max(512, min(8192, ctx // 2)),
            "vision": m["vision"],
        })
    if o_models and serving < (min(x["model_max_ctx"] or serving for x in ollama_models if x["chat_capable"]) if any(
            x["chat_capable"] for x in ollama_models) else serving):
        report["warnings"].append(
            "Ollama 实际只提供 {} token 上下文（远小于模型上限）。若要放开，"
            "执行 `launchctl setenv OLLAMA_CONTEXT_LENGTH 32768` 后重启 Ollama，再重跑本脚本。".format(serving))
    report["routes"][ROUTE_OLLAMA] = {
        "display_name": "Ollama 本地",
        "base_url": OLLAMA_BASE + "/v1",
        "models": o_models,
        "default_max_tokens": max(512, min(8192, serving // 2)),
        "excluded": excluded_o,
    }

    # ── LM Studio ──
    lms_models, lms_err = probe_lmstudio()
    if lms_err:
        report["warnings"].append("LM Studio：" + lms_err + "（跳过该路由，其余照常）")
        lms_models = []
    l_models = []
    excluded_l = []
    for m in lms_models:
        if not m["chat_capable"]:
            excluded_l.append(m["id"])
            continue
        ctx = m["loaded_ctx"] or m["model_max_ctx"] or 32768
        if args.lmstudio_ctx_cap:
            ctx = min(ctx, args.lmstudio_ctx_cap)
        l_models.append({
            "id": m["id"],
            "name": humanize(m, "lmstudio"),
            "context_window": ctx,
            "max_tokens": max(512, min(8192, ctx // 4)),
            "vision": m["vision"],
        })
        if not m["loaded_ctx"]:
            report["warnings"].append(
                "LM Studio「{}」当前未加载，contextWindow 取的是模型上限 {}；"
                "LM Studio 载入时会按显存自动决定实际上下文".format(m["id"], ctx)
                + "（可用 `~/.lmstudio/bin/lms ps` 查看实际值，加载后重跑本脚本即取实际值）。")
    report["routes"][ROUTE_LMSTUDIO] = {
        "display_name": "LM Studio 本地",
        "base_url": LMSTUDIO_BASE + "/v1",
        "models": l_models,
        "default_max_tokens": 8192,
        "excluded": excluded_l,
    }
    return report


# ─────────────────── settings.yaml 文本级外科手术 ───────────────────

def find_llm_piai_providers(lines):
    """定位 llm-pi-ai 段里 providers 子块的 (start, end) 半开区间（不含 providers 行本身）。"""
    sec = None
    for i, ln in enumerate(lines):
        if re.match(r"^llm-pi-ai:\s*$", ln):
            sec = i
            break
    if sec is None:
        raise SystemExit("✗ settings.yaml 里找不到顶层键 `llm-pi-ai:` —— 请先在 GUI 里添加过一个"
                         "自定义提供方，或手工建好该段；本脚本不负责从零创建。")

    sec_end = len(lines)
    for j in range(sec + 1, len(lines)):
        ln = lines[j]
        if ln.strip() == "" or ln.lstrip().startswith("#"):
            continue
        if not ln.startswith((" ", "\t")):
            sec_end = j
            break

    prov = None
    for j in range(sec + 1, sec_end):
        if re.match(r"^  providers:\s*$", lines[j]):
            prov = j
            break
    if prov is None:
        raise SystemExit("✗ `llm-pi-ai:` 段里找不到 `  providers:` 子块。")
    return prov + 1, sec_end


def split_provider_chunks(lines, start, end):
    """把 providers 块切成 [(name|None, [lines])]，None 表示块首的注释/空行头。"""
    chunks = []
    head = []
    cur_name = None
    cur = None
    for ln in lines[start:end]:
        m = re.match(r"^    ([A-Za-z0-9_.\-]+):\s*$", ln)
        if m:
            if cur_name is not None:
                chunks.append((cur_name, cur))
            elif head and any(x.strip() for x in head):
                chunks.append((None, head))
            head = []
            cur_name = m.group(1)
            cur = [ln]
        elif cur_name is None:
            head.append(ln)
        else:
            cur.append(ln)
    if cur_name is not None:
        chunks.append((cur_name, cur))
    elif head and any(x.strip() for x in head):
        chunks.append((None, head))
    return chunks


def strip_trailing_blank(lines):
    out = list(lines)
    while out and out[-1].strip() == "":
        out.pop()
    return out


def ensure_vision_auth(chunk):
    """给 lmstudio 视觉路由补上缺了就会 404 的 Authorization 头（模型列表一个不动）。"""
    if any("Authorization:" in ln for ln in chunk):
        return chunk, False
    out = []
    inserted = False
    for ln in chunk:
        out.append(ln)
        if not inserted and re.match(r"^      baseURL:", ln):
            out += [
                "      # 本地服务不需要密钥，但 pi-ai 要求「有 key 或有 Authorization 头」，",
                "      # 缺它则该路由每次请求都抛 `No API key for provider`（视觉链路会整个失效）。",
                "      headers:",
                "        Authorization: {}".format(q(AUTH_HEADER_VALUE)),
            ]
            inserted = True
    if not inserted:  # 没有 baseURL 行（异常形态）→ 不动
        return chunk, False
    return out, True


def splice(original_text, plan, fix_vision=True):
    lines = original_text.split("\n")
    start, end = find_llm_piai_providers(lines)
    chunks = split_provider_chunks(lines, start, end)

    rendered = {}
    for key, spec in plan["routes"].items():
        if not spec["models"]:
            continue  # 探测失败 → 不写出空路由（空模型列表会被适配器判为非法）
        rendered[key] = render_route(
            key, spec["display_name"], spec["base_url"], spec["models"], spec["default_max_tokens"])

    out_chunks = []
    seen = set()
    vision_fixed = False
    for name, body in chunks:
        if name is None:
            out_chunks.append(strip_trailing_blank(body))
            continue
        if name in rendered:
            out_chunks.append(rendered[name])
            seen.add(name)
            continue
        if name == ROUTE_VISION and fix_vision and not any(
                v for k, v in rendered.items() if k == ROUTE_VISION):
            body, changed = ensure_vision_auth(strip_trailing_blank(body))
            vision_fixed = vision_fixed or changed
            out_chunks.append(body)
            continue
        out_chunks.append(strip_trailing_blank(body))

    for key in (ROUTE_OLLAMA, ROUTE_LMSTUDIO):
        if key in rendered and key not in seen:
            out_chunks.append(rendered[key])

    block = []
    for c in out_chunks:
        if not c:
            continue
        if block:
            block.append("")
        block += c

    new_lines = lines[:start] + block + [""] + lines[end:]
    return "\n".join(new_lines), vision_fixed


# ────────────────────────────── 写盘 ──────────────────────────────

def backup(path):
    ts = time.strftime("%Y%m%d-%H%M%S")
    dst = "{}.bak-models-sync-{}".format(path, ts)
    shutil.copy2(path, dst)
    # 滚动保留
    import glob
    olds = sorted(glob.glob(path + ".bak-models-sync-*"))
    for old in olds[:-BACKUP_KEEP]:
        try:
            os.remove(old)
        except OSError:
            pass
    return dst


def main():
    ap = argparse.ArgumentParser(description="把 Ollama / LM Studio 模型同步进 DSH 的 llm-pi-ai 路由")
    ap.add_argument("--apply", action="store_true", help="真写 settings.yaml（默认只预演）")
    ap.add_argument("--json", action="store_true", help="只输出探测结果 JSON")
    ap.add_argument("--ollama-ctx", type=int, default=0, help="覆盖 Ollama 实际提供的上下文长度")
    ap.add_argument("--lmstudio-ctx-cap", type=int, default=0, help="给 LM Studio 的 contextWindow 设上限")
    ap.add_argument("--no-vision-fix", action="store_true", help="不给 lmstudio 视觉路由补 Authorization 头")
    ap.add_argument("--settings", default=SETTINGS, help="settings.yaml 路径")
    args = ap.parse_args()

    plan = build_plan(args)

    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0 if plan["ok"] else 1

    print("═══ 探测结果 ═══")
    for key, spec in plan["routes"].items():
        print("\n[{}]  {}  ←  {}".format(key, spec["display_name"], spec["base_url"]))
        if spec["models"]:
            for m in spec["models"]:
                print("   · {:<38} ctx={:<8} max={:<6} {}".format(
                    m["id"], m["context_window"], m["max_tokens"],
                    "图片" if m["vision"] else "纯文本"))
        else:
            print("   （无可用模型）")
        if spec["excluded"]:
            print("   ⊘ 已排除（仅能做 embedding，不能对话）：{}".format("、".join(spec["excluded"])))

    if plan["warnings"]:
        print("\n═══ 注意 ═══")
        for w in plan["warnings"]:
            print("  ⚠ " + w)

    path = args.settings
    if not os.path.exists(path):
        print("\n✗ 找不到 {}".format(path))
        return 2
    with open(path, "r", encoding="utf-8") as fh:
        original = fh.read()

    new_text, vision_fixed = splice(original, plan, fix_vision=not args.no_vision_fix)
    if vision_fixed:
        print("\n  ℹ 已给 `{}` 视觉路由补上缺失的 Authorization 头（原缺失会让该路由每次请求都报 "
              "No API key for provider）".format(ROUTE_VISION))

    if new_text == original:
        print("\n＝ 无变化，settings.yaml 已是目标状态。")
        return 0

    if not args.apply:
        print("\n═══ 预演：将要写入的内容（未落盘）═══")
        print("─" * 70)
        print(new_text)
        print("─" * 70)
        print("\n⇒ 这是 dry-run。加 --apply 才真写。")
        return 0

    dst = backup(path)
    # settings.yaml 通常是 0600；os.replace 换上的是新 inode，不显式带上权限就会落到 umask 默认值。
    mode = os.stat(path).st_mode & 0o777
    tmp = path + ".tmp-sync"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    print("\n✅ 已写入 {}（备份：{}）".format(path, dst))
    print("   DSH 用 chokidar 监听该文件，100ms 去抖后热重载 —— 不需要重启 CLD。")
    print("   打开 设置 → 模型 即可在选择器里看到新模型。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
