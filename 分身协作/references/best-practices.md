# 最佳实践

## 何时使用 Orchestrate

✅ **适合：**
- 需要多步骤、多角色的复杂任务（3+ 子任务）
- 不同子任务对推理能力要求差异大（充分利用多模型链）
- 产出物需要审查和迭代

❌ **不适合：**
- 单步骤简单任务 → 快车道直通，不用编排
- 需要实时交互的任务
- 对上下文连续性要求极高的任务

## 模型配置建议

### 多模型链配置策略

每个 tier 的 models 数组按优先级排列，建议：

**高级模型（最前面最强，后面的做 fallback）：**
```
models: ["step-3.7-flash", "deepseek-v4-pro", "gpt-5.5"]
```

**中级模型（均衡稳定优先）：**
```
models: ["deepseek-v4-flash", "gemini-2.5-flash", "deepseek-v4-flash-202605"]
```

**下级模型（速度快优先）：**
```
models: ["agnes-2.0-flash", "glm-4.5-air", "freemodel/gpt-5.4-mini"]
```

### 跨 tier 降级规则

- advanced 全失败 → 用 intermediate.models[0]
- intermediate 全失败 → 用 basic.models[0]
- basic 全失败 → 标记失败，审查时生成占位符

## 任务描述建议

1. **明确产出物**
2. **说明约束**（技术栈、风格、格式）
3. **提供上下文**（相关文件、参考资料）
