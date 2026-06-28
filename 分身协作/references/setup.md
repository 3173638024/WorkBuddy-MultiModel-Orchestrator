# 设置向导

配置文件：`~/.workbuddy/skills/orchestrate/config.json`

## 首次使用流程

### 1. 读取 models.json

读取 `~/.workbuddy/models.json`，提取所有模型的 `id`、`name`、`vendor`，按 vendor 分组。

### 2. 弹出技能介绍（SKILL.md 的 Step 0 中处理）

由 SKILL.md 的设置向导第一步处理，此处跳过。

### 3. 模型配置弹窗（核心步骤）

依次弹出 3 个配置问题，每个 tier 选 3 个模型。

**每个问题的说明文本包含：**
- 该 tier 在编排中的角色
- 推荐选什么类型的模型
- 模型数量要求（选 3 个，按优先级排列）

#### 高级模型配置

```javascript
AskUserQuestion({
  questions: [{
    question: "【高级模型】—— 架构师角色\n\n" +
              "负责最烧脑的任务：复杂推理、架构设计、深度分析、关键技术决策。\n\n" +
              "推荐选择你所有模型中推理能力最强的 3 个。\n" +
              "按优先级排列：第一个是首选，出问题了自动切到第二个，以此类推。\n\n" +
              "可用模型列表：\n{models_list_advanced}\n\n" +
              "选择 3 个模型（按优先级顺序勾选）：",
    header: "高级模型",
    multiSelect: true,
    options: [{label: "1. " + name, description: id} for each model]
  }]
})
```

#### 中级模型配置

```javascript
AskUserQuestion({
  questions: [{
    question: "【中级模型】—— 技术主管角色\n\n" +
              "负责均衡型任务：任务拆解分析、代码审查、模块级实现、质量把关。\n\n" +
              "推荐选择均衡稳定的模型，推理能力强但比顶级模型便宜。\n" +
              "选 3 个，按优先级排列。\n\n" +
              "可用模型列表：\n{models_list_intermediate}\n\n" +
              "选择 3 个模型（按优先级顺序勾选）：",
    header: "中级模型",
    multiSelect: true,
    options: [{label: "2. " + name, description: id} for each model]
  }]
})
```

#### 下级模型配置

```javascript
AskUserQuestion({
  questions: [{
    question: "【下级模型】—— 工程师角色\n\n" +
              "负责简单任务：结果整合、格式统一、信息检索、FAQ 撰写、数据格式化。\n\n" +
              "推荐选择速度快、成本低的轻量模型。\n" +
              "这个 tier 是最容易 fallback 的，所以选便宜的就行，挂了不心疼。\n" +
              "选 3 个，按优先级排列。\n\n" +
              "可用模型列表：\n{models_list_basic}\n\n" +
              "选择 3 个模型（按优先级顺序勾选）：",
    header: "下级模型",
    multiSelect: true,
    options: [{label: "3. " + name, description: id} for each model]
  }]
})
```

**注意：** `multiSelect: true` 允许一次选多个。按优先级顺序勾选，第一个是你最想用的。

### 4. 写入 config.json（version 3 格式）

```json
{
  "version": 3,
  "model_source": "~/.workbuddy/models.json",
  "roles": {
    "advanced": {
      "label": "高级模型",
      "models": ["用户选的模型1", "用户选的模型2", "用户选的模型3"],
      "max_turns": 20
    },
    "intermediate": {
      "label": "中级模型",
      "models": ["用户选的模型1", "用户选的模型2", "用户选的模型3"],
      "max_turns": 12
    },
    "basic": {
      "label": "下级模型",
      "models": ["用户选的模型1", "用户选的模型2", "用户选的模型3"],
      "max_turns": 6
    }
  },
  "settings": {
    "max_agents": 3,
    "agent_timeout_ms": 120000,
    "max_review_rounds": 2
  }
}
```

### 5. 确认

```
✅ Orchestrate v3 就绪！
高级 = {model1} → {model2} → {model3}
中级 = {model1} → {model2} → {model3}
下级 = {model1} → {model2} → {model3}
settings: 最多 3 组 agent、120s 超时、最多 2 轮反馈

现在可以用 @orchestrate 编排复杂任务了。
```
