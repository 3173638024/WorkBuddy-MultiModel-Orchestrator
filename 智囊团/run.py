#!/usr/bin/env python3
"""
CLI 入口：多模型编排器
用法:
  python run.py status               查看平台状态
  python run.py models               列出可用模型
  python run.py parallel '{"model1":"prompt1","model2":"prompt2"}'
  python run.py pipeline '[{"model":"x","prompt":"y"},...]'
  python run.py orchestrate "任务描述"
  python run.py single <model> "prompt"
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orchestrator import (
    parallel_call, pipeline_call, orchestrate, call_model,
    list_available_models, platform_status,
)


def main():
    if len(sys.argv) < 2:
        print("多模型编排器 CLI")
        print()
        print("用法: python run.py {status|models|parallel|pipeline|orchestrate|single} <参数>")
        print()
        print("  status        查看平台状态")
        print("  models        列出可用模型")
        print('  parallel      python run.py parallel \'{"deepseek-chat":"...", "step-3.7-flash":"..."}\'')
        print('  pipeline      python run.py pipeline \'[{"model":"x","prompt":"y"}]\'')
        print('  orchestrate   python run.py orchestrate "复杂任务"')
        print('  single        python run.py single deepseek-chat "prompt"')
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "status":
        print(json.dumps(platform_status(), ensure_ascii=False, indent=2))

    elif mode == "models":
        print(json.dumps(list_available_models(), ensure_ascii=False, indent=2))

    elif mode == "parallel":
        assignments = json.loads(sys.argv[2])
        result = parallel_call(assignments)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif mode == "pipeline":
        stages = json.loads(sys.argv[2])
        result = pipeline_call(stages)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif mode == "orchestrate":
        task = sys.argv[2]
        result = orchestrate(task)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif mode == "single":
        model = sys.argv[2]
        prompt = sys.argv[3]
        result = call_model(model, prompt)
        print(json.dumps({
            "model": result.model_id,
            "response": result.response,
            "elapsed": round(result.elapsed, 1),
            "tokens": result.tokens,
            "error": result.error,
        }, ensure_ascii=False, indent=2))

    else:
        print(f"未知模式: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
