# Prompt 模板

## 子任务 Agent Prompt 模板

```
你的角色：解决以下子任务
任务上下文：{原始任务的完整需求}
{可选：项目上下文摘要}
子任务标题：{子任务标题}
子任务描述：{子任务描述}
评级：{advanced/intermediate/basic}
预期输出：{清晰定义输出的格式和内容}
```

## Merger Prompt 模板

```
你的角色：整合多个子任务的输出为一个完整的最终结果。

原始任务需求：{原始任务}

各子任务输出：
{subtask-1: ...}
{subtask-2: ...}
...

=== 整合要求 ===

1. 格式统一：统一缩进、换行、引号风格
2. 去重：相似内容只保留最完整的版本
3. 补缺失：如果某个子任务失败，在对应位置添加注释说明
4. 生成项目结构树

请输出整合后的完整结果。
```

## Reviewer Prompt 模板

```
你是代码审查专家。请审查以下整合结果是否满足原始需求，并输出 JSON。

原始任务需求：{原始任务}
整合结果（含文件路径和内容）：{整合输出}

=== 审查标准 ===

1. 完整性 — 是否覆盖了所有需求点
2. 一致性 — 各子任务输出之间是否自洽（品牌名、命名、格式、链接）
3. 正确性 — 代码、逻辑、数据是否正确
4. 可用性 — 是否存在明显的运行时错误或 bug

=== 输出格式 ===

请输出纯 JSON（不要其他文字）：
{
  "passed": true/false,
  "summary": "整体质量评价，50字以内",
  "issues": [
    {
      "file": "具体文件路径",
      "line_hint": "问题所在行的大致位置",
      "severity": "critical|warning|suggestion",
      "description": "问题具体描述",
      "fix": "建议如何修复",
      "source_subtask": "子任务 id"
    }
  ]
}

要求：
- 每个 issue 必须包含 file 和 source_subtask
- severity: critical（必须修复）| warning（建议修复）| suggestion（优化）
- 如果没有问题，issues 为空数组
```

## 进度报告模板

```
🧊 编排进度：
  Step 1 ✅ 任务分析完成（复杂度：{complexity}，拆分为 {n} 个子任务）
  Step 2 🔄 执行子任务（{completed}/{total} 完成，{failed} 个失败）
  Step 3 ⏳ 等待中
  Step 4 ⏳ 等待中
  Step 5 ⏳ 等待中
```
