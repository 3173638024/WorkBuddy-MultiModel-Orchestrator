# 编排工作流详细说明

## 核心变更（与 v2 相比）

| 变更项 | v2 | v3 |
|--------|----|----|
| 任务分析 | spawn agent | 编排者自己做 |
| 最大 agent 数 | 无限制（子任务数） | 3（按 rating 合并） |
| fallback | 1 个模型 | models 数组，按顺序切 |
| 超时 | 无 | 120s |
| 整合 | spawn merger agent | 编排者自己做 |
| 审查 | spawn reviewer agent | 编排者自己做 |
| 反馈循环 | 最多 3 次 | 最多 2 次 |
| 输出传递 | SendMessage | 写文件 |
| 快车道 | 无 | 子任务 ≤2 时直通 |

## Step 1: 快速评估（编排者自己做）

不要 spawn agent。直接分析任务，自己判断。

**分析内容：**
- 整体复杂度（simple / moderate / complex）
- 子任务拆分方案
- 子任务之间的依赖关系

**输出格式示例：**
```json
{
  "overall_complexity": "moderate",
  "estimated_subtasks": 4,
  "dependencies": [["subtask-3", "subtask-1"]],
  "merge_strategy": "sequential",  // sequential: 按顺序合并；parallel: 独立输出，编排者整合
  "subtasks": [
    {
      "id": "subtask-1",
      "title": "CSS 样式系统",
      "description": "实现全局样式、响应式布局、主题色",
      "rating": "intermediate"
    },
    {
      "id": "subtask-2",
      "title": "文章数据与首页",
      "description": "定义文章数据结构和首页渲染",
      "rating": "intermediate"
    }
  ]
}
```

### 快车道判断

子任务数 ≤ 2：走快车道，不 spawn agent，直接用 `config.roles.advanced.models[0]` 直出。

## Step 2: 执行子任务（并行 + 分级 + 多模型 fallback）

### 分组规则

1. 将子任务按 rating 分组（advanced / intermediate / basic）
2. 同组的子任务合并到一条 prompt 中，spawn 一个 agent 处理
3. 最多 3 个 agent（每个 rating 最多 1 个）

### Agent prompt 模板

```
你的任务：处理以下 {rating} 级子任务。

=== 原始任务 ===
{原始需求}

=== 你的子任务列表 ===
{subtask-1 的 title 和 description}
{subtask-2 的 title 和 description}
...

=== 输出要求 ===
1. 将每个子任务的结果写入独立的文件
2. 文件路径：{workspace}/orchestrate-output/{agent-name}-{subtask-id}.md
3. 输出结束后，在最终回复中附上已写入的文件路径列表
4. 如果某个子任务无法完成，注明原因
```

### 多模型 failover

尝试顺序：
```
models[0] → 失败 → models[1] → 失败 → models[2] → 失败 → 降级下一 tier models[0]
```

每次尝试设 timeout = config.settings.agent_timeout_ms（默认 120s）。

### 进度报告

每完成一个 agent，输出进度：
```
🧊 编排进度：
  Step 1 ✅ 任务评估
  Step 2 🔄 执行中（{completed}/{total} 组完成）
```

## Step 3: 整合（编排者自己做）

所有 agent 完成后：
1. 读取 agent 写入的输出文件
2. 合并为一个完整结果
3. 格式统一、去重
4. 失败子任务生成占位符
5. 写入 `{workspace}/orchestrate-output/merged.md`

## Step 4: 审查（编排者自己做）

自己审查整合结果，检查：
1. **完整性** — 覆盖所有需求点
2. **一致性** — 命名、格式跨子任务统一
3. **正确性** — 逻辑无误

## Step 5: 反馈循环（最多 2 次）

发现问题时：
- 格式/命名问题 → 编排者直接修复
- 内容质量问题 → 重新 spawn 对应 agent，强制用该 tier 的 models[0]

## 边界情况处理

| 场景 | 处理方式 |
|------|---------|
| 任务过于简单（1-2 子任务） | 快车道：用 advanced.models[0] 直出 |
| 子代理执行失败 | 按 models 数组顺序 try，全失败降级下一 tier |
| 子代理超时（>120s） | 标记为超时，切下一个模型 |
| 子代理输出为空 | 标记为失败，审查时生成占位符 |
| 反馈循环超过 2 次 | 交付中间结果，注明未通过部分 |
