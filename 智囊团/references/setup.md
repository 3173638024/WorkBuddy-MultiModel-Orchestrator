# 设置向导

配置文件：`~/.workbuddy/skills/智囊团/config.json`

## 首次使用流程

### 1. 读取 models.json

读取 `~/.workbuddy/models.json`，提取所有模型的 `id`、`name`、`url`、`apiKey`、`vendor`。

按平台（url 前缀）分组：
- `api.deepseek.com` → DeepSeek
- `api.stepfun.com` → StepFun
- `dashscope.aliyuncs.com` → 阿里百炼
- `api.freemodel.dev` → FreeModel（⚠️不稳定，默认不启用）
- `apihub.agnes-ai.com` → Agnes AI
- `token-plan-cn.xiaomimimo.com` → 小米 MiMo
- `chat.intern-ai.org.cn` → 上海 AI Lab
- `integrate.api.nvidia.com` → NVIDIA

### 2. 技能介绍弹窗

由 SKILL.md 的处理流程第一步处理。

### 3. 平台启用电弹窗

```javascript
AskUserQuestion({
  questions: [{
    question: "选择要启用的模型平台。\n\n" +
              "未被选中的平台在编排时不会调用。\n" +
              "建议至少启用 2 个不同平台的模型，方便 fallback。\n\n" +
              "可用平台：\n- DeepSeek (deepseek-chat) ✅稳定\n" +
              "- StepFun (step-3.7-flash) ✅稳定\n" +
              "- 阿里百炼 (qwen3.6-flash) ✅稳定\n" +
              "- Agnes AI (agnes-2.0-flash) ✅稳定\n" +
              "- 小米 MiMo (mimo-v2.5-pro) ⚠️偶尔不稳定\n" +
              "- FreeModel (gpt-5.5) ❌经常502，不推荐\n\n" +
              "勾选要启用的平台：",
    header: "选择平台",
    multiSelect: true,
    options: [
      {label: "DeepSeek", description: "deepseek-chat — 最稳定"},
      {label: "StepFun", description: "step-3.7-flash — 均衡"},
      {label: "阿里百炼", description: "qwen3.6-flash — 强推理"},
      {label: "Agnes AI", description: "agnes-2.0-flash — 轻量"},
      {label: "小米 MiMo", description: "mimo-v2.5-pro — 偶有波动"},
      {label: "FreeModel", description: "gpt-5.5 — 不推荐，经常502"}
    ]
  }]
})
```

### 4. 指定各平台用途

为每个启用的平台选一个 tier：

```javascript
AskUserQuestion({
  questions: [{
    question: "为 {platform_name} 指定用途：\n\n" +
              "• 高级：负责拆解任务、复杂推理、最终聚合\n" +
              "• 中级：负责难度中等的子任务\n" +
              "• 基础：负责简单的查询/格式化任务",
    header: "{platform_name} 用途",
    options: [
      {label: "🚀 高级", description: "拆解+聚合+复杂推理"},
      {label: "💡 中级", description: "中等难度子任务"},
      {label: "⚡ 基础", description: "简单查询和格式化"}
    ]
  }]
})
```

### 5. 写入 config.json

```json
{
  "version": 1,
  "platforms": {
    "deepseek": {
      "name": "DeepSeek",
      "enabled": true,
      "api_key": "YOUR_API_KEY",
      "base_url": "https://api.deepseek.com/v1",
      "tier": "advanced",
      "models": ["deepseek-chat"]
    },
    "stepfun": {
      "name": "StepFun",
      "enabled": true,
      "api_key": "YOUR_STEPFUN_KEY",
      "base_url": "https://api.stepfun.com/step_plan/v1",
      "tier": "intermediate",
      "models": ["step-3.7-flash"]
    }
  },
  "settings": {
    "default_mode": "orchestrate",
    "timeout": 120,
    "default_splitter": "deepseek"
  }
}
```

### 6. 确认

```
✅ 多模型编排器就绪！

启用的平台：
  🚀 deepseek (DeepSeek) — 高级
  💡 stepfun (StepFun) — 中级
  ⚡ agnes (Agnes AI) — 基础

默认模式：orchestrate（完整编排）
超时：120s

现在可以用了。说「并行调三个模型分析...」或「编排这个任务」即可。
```
