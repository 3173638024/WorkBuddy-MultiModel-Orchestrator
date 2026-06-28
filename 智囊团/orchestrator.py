#!/usr/bin/env python3
"""
多模型编排器 v2（openai 库 / 配置驱动 / 自动同步 / 失败重试 / 成本统计）
====================================================================
优化：
  1. 自动从 ~/.workbuddy/models.json 同步 api_key/base_url
  2. 子任务失败自动在同 tier 内重试下一个模型
  3. Token 成本统计（¥）
"""

import json
import time
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path

from openai import OpenAI

# ── 路径 ──────────────────────────────────────────────────
SKILL_DIR = Path(__file__).parent
CONFIG_PATH = SKILL_DIR / "config.json"
MODELS_JSON_PATH = Path.home() / ".workbuddy" / "models.json"

# ── 内置默认 ────────────────────────────────────────────
DEFAULT_CONFIG = {
    "version": 2,
    "platforms": {
        "deepseek": {"name": "DeepSeek", "enabled": True, "api_key": "YOUR_DEEPSEEK_API_KEY", "base_url": "https://api.deepseek.com/v1", "tier": "advanced", "models": ["deepseek-chat"]},
        "stepfun": {"name": "StepFun", "enabled": True, "api_key": "YOUR_STEPFUN_API_KEY", "base_url": "https://api.stepfun.com/step_plan/v1", "tier": "intermediate", "models": ["step-3.7-flash"]},
        "dashscope": {"name": "阿里百炼", "enabled": True, "api_key": "YOUR_DASHSCOPE_API_KEY", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "tier": "advanced", "models": ["qwen3.6-flash"]},
        "agnes": {"name": "Agnes AI", "enabled": True, "api_key": "YOUR_AGNES_API_KEY", "base_url": "https://apihub.agnes-ai.com/v1", "tier": "basic", "models": ["agnes-2.0-flash"]},
        "xiaomi": {"name": "小米 MiMo", "enabled": False, "api_key": "YOUR_XIAOMI_API_KEY", "base_url": "https://token-plan-cn.xiaomimimo.com/v1", "tier": "intermediate", "models": ["mimo-v2.5-pro"]},
    },
    "settings": {"default_mode": "orchestrate", "timeout": 120, "max_retries": 2, "default_splitter_platform": "deepseek"},
}


# ═══════════════════════════════════════════════════════════
# 配置加载 + 自动同步
# ═══════════════════════════════════════════════════════════
def _load_config() -> dict:
    cfg = DEFAULT_CONFIG
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # 合并：loaded 覆盖 default
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

    # ── 优化1: 从 models.json 自动同步 api_key/base_url ──
    _sync_from_models_json(cfg)
    return cfg


def _sync_from_models_json(cfg: dict):
    """从 WorkBuddy 的 models.json 自动更新 api_key 和 base_url"""
    if not MODELS_JSON_PATH.exists():
        return

    try:
        with open(MODELS_JSON_PATH, "r", encoding="utf-8") as f:
            wb_models = json.load(f)
    except Exception:
        return

    # 构建 URL 前缀 → 平台 key 的映射
    url_map = {}
    for key, plat in cfg["platforms"].items():
        # 提取域名做匹配
        base = plat.get("base_url", "")
        host = base.replace("https://", "").replace("http://", "").split("/")[0]
        url_map[host] = key

    # 遍历 models.json，找到匹配的模型
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
                    # 去掉末尾的 /chat/completions 或 /completions，openai 客户端会自动拼
                    clean_url = re.sub(r"/(chat/)?completions/?$", "", wb_model["url"])
                    plat["base_url"] = clean_url


_config = _load_config()
_ENABLED = {k: v for k, v in _config["platforms"].items() if v.get("enabled", True)}
MAX_RETRIES = _config["settings"].get("max_retries", 2)
TIMEOUT = _config["settings"].get("timeout", 120)

# 构建客户端
CLIENTS = {}
for key, cfg in _ENABLED.items():
    try:
        CLIENTS[key] = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
    except Exception:
        CLIENTS[key] = None

# 模型 → 平台映射
MODEL_MAP = {}
for key, cfg in _ENABLED.items():
    for model in cfg.get("models", []):
        MODEL_MAP[model] = (key, model)

# tier → 模型列表
TIER_MODELS = {"advanced": [], "intermediate": [], "basic": []}
for key, cfg in _ENABLED.items():
    tier = cfg.get("tier", "intermediate")
    for model in cfg.get("models", []):
        TIER_MODELS.setdefault(tier, []).append(model)


# ═══════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════
@dataclass
class CallResult:
    model_id: str
    response: str
    elapsed: float
    tokens: int = 0
    error: Optional[str] = None
    platform: str = ""
    retries: int = 0


# ═══════════════════════════════════════════════════════════
# 优化2: 带重试的模型调用
# ═══════════════════════════════════════════════════════════
def _get_fallback_models(model_id: str) -> list[str]:
    """获取同 tier 内的 fallback 模型列表"""
    tier = None
    for t, models in TIER_MODELS.items():
        if model_id in models:
            tier = t
            break
    if tier is None:
        return []
    return [m for m in TIER_MODELS[tier] if m != model_id]


def call_model(model_id: str, prompt: str, system: str = "",
               timeout: int = None, retry: bool = False) -> CallResult:
    if timeout is None:
        timeout = TIMEOUT

    candidates = [model_id]
    if retry:
        candidates += _get_fallback_models(model_id)

    last_error = None
    for attempt, cand in enumerate(candidates):
        if cand not in MODEL_MAP:
            last_error = f"未知模型: {cand}"
            continue

        platform_key, real_model = MODEL_MAP[cand]
        client = CLIENTS.get(platform_key)
        if client is None:
            last_error = f"平台 {platform_key} 未初始化"
            continue

        t0 = time.time()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = client.chat.completions.create(
                model=real_model, messages=messages,
                temperature=0.7, max_tokens=4096, timeout=timeout,
            )
            elapsed = time.time() - t0
            msg = resp.choices[0].message
            content = msg.content or ""
            if not content:
                content = getattr(msg, "reasoning_content", "") or msg.model_extra.get("reasoning_content", "")
            tokens = resp.usage.total_tokens if resp.usage else 0
            return CallResult(
                model_id=cand, response=content, elapsed=elapsed,
                tokens=tokens, platform=platform_key, retries=attempt,
            )
        except Exception as e:
            elapsed = time.time() - t0
            last_error = str(e)[:300]

    return CallResult(
        model_id=model_id, response="", elapsed=0,
        error=f"重试{len(candidates)}次均失败: {last_error}", retries=len(candidates),
    )


# ═══════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════
def list_available_models() -> list:
    return list(MODEL_MAP.keys())


def platform_status() -> dict:
    result = {}
    for key, cfg in _ENABLED.items():
        result[key] = {"name": cfg["name"], "tier": cfg["tier"], "models": cfg["models"], "base_url": cfg["base_url"]}
    return result


# ═══════════════════════════════════════════════════════════
# 三模式
# ═══════════════════════════════════════════════════════════
def parallel_call(assignments: dict, timeout: int = None, retry: bool = False,
                 on_progress=None) -> dict:
    if timeout is None:
        timeout = TIMEOUT

    results = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(call_model, mid, prompt, "", timeout, retry): mid for mid, prompt in assignments.items()}
        for future in as_completed(futures):
            r = future.result()
            status = "✅" if not r.error else f"❌ (retry={r.retries})"
            if on_progress:
                on_progress(r.model_id, status, round(r.elapsed, 1))
            results[r.model_id] = {
                "response": r.response, "elapsed": round(r.elapsed, 1),
                "tokens": r.tokens, "error": r.error, "retries": r.retries,
                "platform": r.platform,
            }

    return results


def pipeline_call(stages: list, timeout: int = None, retry: bool = False) -> dict:
    if timeout is None:
        timeout = TIMEOUT

    results = []
    context = ""
    for i, stage in enumerate(stages):
        mid, prompt = stage["model"], stage["prompt"]
        full_prompt = f"前面的输出:\n```\n{context}\n```\n\n当前: {prompt}" if context else prompt
        r = call_model(mid, full_prompt, timeout=timeout, retry=retry)
        results.append({"stage": i + 1, "model": r.model_id, "response": r.response, "elapsed": round(r.elapsed, 1), "tokens": r.tokens, "error": r.error, "retries": r.retries})
        if r.error:
            break
        context = r.response

    return {"stages": results, "final_output": context}


def orchestrate(task: str, splitter: str = None, timeout: int = None,
                verbose: bool = True) -> dict:
    if timeout is None:
        timeout = TIMEOUT
    if splitter is None:
        adv = TIER_MODELS.get("advanced", [])
        splitter = adv[0] if adv else list(MODEL_MAP.keys())[0]

    t_start = time.time()

    # ── Step 1: 拆解（优化2: 崩了自动换模型）────────────
    if verbose:
        print("  [1/3] 拆解任务...", end=" ", flush=True)

    split_candidates = [splitter] + [m for m in TIER_MODELS.get("advanced", []) if m != splitter]
    split = None
    split_prompt = f"拆成 3 个独立子任务，JSON数组返回，每项: id,title,prompt,difficulty(1-3)。\n任务: {task}"
    for cand in split_candidates:
        split = call_model(cand, split_prompt, timeout=timeout, retry=False)
        if not split.error:
            if verbose:
                print(f"✅ ({split.model_id}, {split.elapsed:.1f}s)")
            break
        if verbose:
            print(f"❌ {split.model_id}: {split.error[:50]}", end=" ")

    if split.error:
        if verbose:
            print("💀 全部拆解模型崩了")
        return {"error": f"拆解失败: {split.error}"}

    # 解析子任务
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
        pool = TIER_MODELS.get(tier, [splitter]) or [splitter]
        model = pool[i % len(pool)]
        assignments[model] = sub["prompt"]
        if verbose:
            print(f"    [{sub['id']}] 难度{d} → {model} ({tier})")

    # 进度回调
    completed = [0]
    total = len(assignments)
    def show_progress(mid, status, elapsed):
        completed[0] += 1
        print(f"    [{completed[0]}/{total}] {mid}: {status} ({elapsed}s)")

    sub_raw = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(call_model, mid, prompt, "", timeout, True): mid
                   for mid, prompt in assignments.items()}
        for future in as_completed(futures):
            r = future.result()
            sub_raw[r.model_id] = r
            show_progress(r.model_id, "✅" if not r.error else f"❌ retry={r.retries}", round(r.elapsed, 1))

    sub_results = {}
    for mid, r in sub_raw.items():
        sub_results[mid] = {
            "response": r.response, "elapsed": round(r.elapsed, 1),
            "tokens": r.tokens, "error": r.error, "retries": r.retries,
            "platform": r.platform,
        }

    # ── Step 3: 聚合 ────────────────────────────────────
    if verbose:
        print("  [3/3] 聚合...", end=" ", flush=True)

    pieces = "\n\n---\n\n".join(
        f"## {mid}\n{info['response']}" for mid, info in sub_results.items() if not info.get("error")
    )
    merge = call_model(splitter, f"整合为 Markdown 报告:\n任务: {task}\n\n{pieces}", timeout=timeout, retry=True)

    if verbose:
        status = "✅" if not merge.error else "❌"
        elapsed = time.time() - t_start
        print(f"{status} ({elapsed:.1f}s)")

    return {
        "task": task, "subtasks": subtasks, "sub_results": sub_results,
        "final_report": merge.response, "total_elapsed": round(time.time() - t_start, 1),
    }


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("python orchestrator.py {status|models|orchestrate|parallel|pipeline|sync} ...")
        print("  sync   从 models.json 重新同步 api_key")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "status":
        print(json.dumps(platform_status(), ensure_ascii=False, indent=2))
    elif cmd == "models":
        print(json.dumps(list_available_models(), ensure_ascii=False, indent=2))
    elif cmd == "sync":
        # 强制重新同步并写入 config
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(_config, f, ensure_ascii=False, indent=2)
        print("✅ 已从 models.json 同步并写入 config.json")
    elif cmd == "orchestrate" and len(sys.argv) >= 3:
        result = orchestrate(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif cmd == "parallel" and len(sys.argv) >= 3:
        result = parallel_call(json.loads(sys.argv[2]), retry=False)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif cmd == "pipeline" and len(sys.argv) >= 3:
        result = pipeline_call(json.loads(sys.argv[2]), retry=False)
        print(json.dumps(result, ensure_ascii=False, indent=2))
