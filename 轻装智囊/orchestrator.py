#!/usr/bin/env python3
"""
多模型编排器 v2（纯 requests / 零 AI 库依赖 / 自动同步 / 失败重试 / 进度反馈）
============================================================================
不需要 openai、langchain 等任何 AI 库。
只依赖 Python 标准库 + requests。
与 multi-model-orchestrator v3 功能对等。
"""

import json
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

import requests

# ── 路径 ──────────────────────────────────────────────────
SKILL_DIR = Path(__file__).parent
CONFIG_PATH = SKILL_DIR / "config.json"
MODELS_JSON_PATH = Path.home() / ".workbuddy" / "models.json"

DEFAULT_CONFIG = {
    "version": 2,
    "platforms": {
        "deepseek": {"name": "DeepSeek", "enabled": True, "tier": "advanced", "url": "https://api.deepseek.com/v1/chat/completions", "api_key": "YOUR_DEEPSEEK_API_KEY", "model": "deepseek-chat"},
        "stepfun": {"name": "StepFun", "enabled": True, "tier": "intermediate", "url": "https://api.stepfun.com/step_plan/v1/chat/completions", "api_key": "YOUR_STEPFUN_API_KEY", "model": "step-3.7-flash"},
        "dashscope": {"name": "阿里百炼", "enabled": True, "tier": "advanced", "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "api_key": "YOUR_DASHSCOPE_API_KEY", "model": "qwen3.6-flash"},
        "agnes": {"name": "Agnes AI", "enabled": True, "tier": "basic", "url": "https://apihub.agnes-ai.com/v1/chat/completions", "api_key": "YOUR_AGNES_API_KEY", "model": "agnes-2.0-flash"},
    },
    "settings": {"timeout": 120, "max_retries": 2, "default_splitter_platform": "deepseek"},
}


def _load_config() -> dict:
    cfg = DEFAULT_CONFIG
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if "platforms" in loaded:
                for k, v in loaded["platforms"].items():
                    if k in cfg["platforms"]:
                        cfg["platforms"][k].update(v)
                    else:
                        cfg["platforms"][k] = v
            if "settings" in loaded:
                cfg["settings"].update(loaded["settings"])
        except Exception:
            pass

    # 自动同步 models.json
    _sync_from_models_json(cfg)
    return cfg


def _sync_from_models_json(cfg: dict):
    if not MODELS_JSON_PATH.exists():
        return
    try:
        with open(MODELS_JSON_PATH, "r", encoding="utf-8") as f:
            wb_models = json.load(f)
    except Exception:
        return

    url_map = {}
    for key, plat in cfg["platforms"].items():
        base = plat.get("url", "")
        host = base.replace("https://", "").replace("http://", "").split("/")[0]
        url_map[host] = key

    for wb_model in wb_models:
        wb_url = wb_model.get("url", "")
        wb_host = wb_url.replace("https://", "").replace("http://", "").split("/")[0] if wb_url else ""
        if wb_host in url_map:
            plat_key = url_map[wb_host]
            plat = cfg["platforms"][plat_key]
            if plat.get("enabled", True):
                if wb_model.get("apiKey"):
                    plat["api_key"] = wb_model["apiKey"]
                if wb_model.get("url"):
                    clean = re.sub(r"/(chat/)?completions/?$", "", wb_model["url"])
                    plat["url"] = clean + "/chat/completions"


_config = _load_config()
_ENABLED = {k: v for k, v in _config["platforms"].items() if v.get("enabled", True)}
TIMEOUT = _config["settings"].get("timeout", 120)
MAX_RETRIES = _config["settings"].get("max_retries", 2)

_TIER_MODELS = {"advanced": [], "intermediate": [], "basic": []}
for k, v in _ENABLED.items():
    _TIER_MODELS.setdefault(v.get("tier", "intermediate"), []).append(k)


@dataclass
class CallResult:
    model_id: str
    response: str
    elapsed: float
    tokens: int = 0
    error: Optional[str] = None
    retries: int = 0


# ═══════════════════════════════════════════════════════════
# 带重试的模型调用
# ═══════════════════════════════════════════════════════════
def _get_fallback(model_id: str) -> list[str]:
    for tier, models in _TIER_MODELS.items():
        if model_id in models:
            return [m for m in models if m != model_id]
    return []


def call_model(model_id: str, prompt: str, system: str = "", retry: bool = False) -> CallResult:
    candidates = [model_id]
    if retry:
        candidates += _get_fallback(model_id)

    last_error = None
    for attempt, cand in enumerate(candidates):
        if cand not in _ENABLED:
            last_error = f"未知模型: {cand}"
            continue

        cfg = _ENABLED[cand]
        t0 = time.time()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = requests.post(
                cfg["url"],
                json={"model": cfg["model"], "messages": messages, "temperature": 0.7, "max_tokens": 4096},
                headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
                timeout=TIMEOUT,
            )
            elapsed = time.time() - t0

            if resp.status_code == 200:
                body = resp.json()
                content = body["choices"][0]["message"].get("content") or body["choices"][0]["message"].get("reasoning_content", "")
                tokens = body.get("usage", {}).get("total_tokens", 0)
                return CallResult(model_id=cand, response=content, elapsed=elapsed, tokens=tokens, retries=attempt)
            else:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            elapsed = time.time() - t0
            last_error = str(e)[:300]

    return CallResult(model_id=model_id, response="", elapsed=0, error=last_error, retries=len(candidates))


# ═══════════════════════════════════════════════════════════
def list_models() -> list:
    return [{"key": k, "name": v["name"], "tier": v["tier"]} for k, v in _ENABLED.items()]


def parallel_call(assignments: dict, retry: bool = False, on_progress=None) -> dict:
    results = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(call_model, mid, prompt, "", retry): mid for mid, prompt in assignments.items()}
        for future in as_completed(futures):
            r = future.result()
            status = "✅" if not r.error else f"❌ r={r.retries}"
            if on_progress:
                on_progress(r.model_id, status, round(r.elapsed, 1))
            results[r.model_id] = {"response": r.response, "elapsed": round(r.elapsed, 1), "tokens": r.tokens, "error": r.error, "retries": r.retries}
    return results


def pipeline_call(stages: list, retry: bool = False) -> dict:
    results = []
    context = ""
    for i, stage in enumerate(stages):
        mid, prompt = stage["model"], stage["prompt"]
        full = f"前面的输出:\n```\n{context}\n```\n\n当前: {prompt}" if context else prompt
        r = call_model(mid, full, retry=retry)
        results.append({"stage": i + 1, "model": r.model_id, "response": r.response, "elapsed": round(r.elapsed, 1), "tokens": r.tokens, "error": r.error, "retries": r.retries})
        if r.error:
            break
        context = r.response
    return {"stages": results, "final_output": context}


def orchestrate(task: str, splitter: str = None, verbose: bool = True) -> dict:
    if splitter is None:
        splitter = _config["settings"].get("default_splitter_platform", "deepseek")

    t_start = time.time()

    # ── Step 1: 拆解（带 fallback）───────────────────────
    if verbose:
        print("  [1/3] 拆解...", end=" ", flush=True)

    candidates = [splitter] + [m for m in _TIER_MODELS.get("advanced", []) if m != splitter]
    split = None
    split_prompt = f"拆成 3 个独立子任务，JSON数组返回，每项: id,title,prompt,difficulty(1-3)。\n任务: {task}"
    for cand in candidates:
        split = call_model(cand, split_prompt)
        if not split.error:
            if verbose:
                print(f"✅ ({split.model_id}, {split.elapsed:.1f}s)")
            break
        if verbose:
            print(f"❌ {cand}", end=" ")

    if split.error:
        if verbose:
            print("💀")
        return {"error": f"拆解失败: {split.error}"}

    try:
        subtasks = json.loads(re.sub(r"```json|```", "", split.response).strip())
    except Exception:
        m = re.search(r"\[.*\]", split.response, re.DOTALL)
        subtasks = json.loads(m.group()) if m else []
    if not subtasks:
        return {"error": "无法解析子任务"}

    if verbose:
        print(f"  [{len(subtasks)}个子任务]")

    # ── Step 2: 分配 + 并行 ─────────────────────────────
    if verbose:
        print("  [2/3] 并行执行...")

    assignments = {}
    for i, sub in enumerate(subtasks):
        d = sub.get("difficulty", 2)
        tier = "advanced" if d >= 3 else ("basic" if d == 1 else "intermediate")
        pool = _TIER_MODELS.get(tier, [splitter]) or [splitter]
        model = pool[i % len(pool)]
        assignments[model] = sub["prompt"]
        if verbose:
            print(f"    [{sub['id']}] 难度{d} → {model} ({tier})")

    completed = [0]
    total = len(assignments)
    def show_progress(mid, status, elapsed):
        completed[0] += 1
        print(f"    [{completed[0]}/{total}] {mid}: {status} ({elapsed}s)")

    sub_results = parallel_call(assignments, retry=True, on_progress=show_progress)

    # ── Step 3: 聚合 ────────────────────────────────────
    if verbose:
        print("  [3/3] 聚合...", end=" ", flush=True)

    pieces = "\n\n---\n\n".join(f"## {mid}\n{info['response']}" for mid, info in sub_results.items() if not info.get("error"))
    merge = call_model(splitter, f"整合为 Markdown 报告:\n任务: {task}\n\n{pieces}", retry=True)

    elapsed = time.time() - t_start
    if verbose:
        total_tok = sum(r.get("tokens", 0) for r in sub_results.values()) + merge.tokens
        s = "✅" if not merge.error else "❌"
        print(f"{s} ({elapsed:.1f}s, {total_tok}tok)")

    return {
        "task": task, "subtasks": subtasks, "sub_results": sub_results,
        "final_report": merge.response, "total_elapsed": round(elapsed, 1),
    }


# ── CLI ──────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("python orchestrator.py {models|sync|orchestrate|parallel|pipeline} ...")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "models":
        print(json.dumps(list_models(), ensure_ascii=False, indent=2))
    elif cmd == "sync":
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(_config, f, ensure_ascii=False, indent=2)
        print("✅ 已从 models.json 同步并写入 config.json")
    elif cmd == "orchestrate" and len(sys.argv) >= 3:
        r = orchestrate(sys.argv[2])
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif cmd == "parallel" and len(sys.argv) >= 3:
        r = parallel_call(json.loads(sys.argv[2]))
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif cmd == "pipeline" and len(sys.argv) >= 3:
        r = pipeline_call(json.loads(sys.argv[2]))
        print(json.dumps(r, ensure_ascii=False, indent=2))
