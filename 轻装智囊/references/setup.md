# 设置向导

配置文件：`~/.workbuddy/skills/轻装智囊/config.json`

## 和 multi-model-orchestrator 的区别

| | multi-model-orchestrator | 轻装智囊 |
|---|---|---|
| 依赖 | openai 库 | requests 库 |
| 接口风格 | `client.chat.completions.create()` | `requests.post()` |
| 流式 | 原生支持 | 需手动 SSE 解析 |
| 异常类型 | openai 库类型安全 | HTTP status code 判断 |
| 适用 | 生产环境 | 零依赖 / 极致控制 |

## 配置模板

```json
{
  "version": 1,
  "platforms": {
    "deepseek": {
      "name": "DeepSeek", "enabled": true, "tier": "advanced",
      "url": "https://api.deepseek.com/v1/chat/completions",
      "api_key": "sk-xxx", "model": "deepseek-chat"
    },
    "stepfun": {
      "name": "StepFun", "enabled": true, "tier": "intermediate",
      "url": "https://api.stepfun.com/step_plan/v1/chat/completions",
      "api_key": "xxx", "model": "step-3.7-flash"
    }
  },
  "settings": {
    "timeout": 120,
    "default_splitter_platform": "deepseek"
  }
}
```
