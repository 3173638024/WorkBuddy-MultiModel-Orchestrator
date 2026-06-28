# 配置验证规范

配置文件：`~/.workbuddy/skills/orchestrate/config.json`
模型注册表：`~/.workbuddy/models.json`

## 验证时机

每次调用 `@orchestrate` 时，在进入编排工作流前执行。

## 验证步骤

### 1. 检查 config.json 存在性

- 文件不存在 → 进入设置向导（见 references/setup.md）
- 文件存在 → 继续

### 2. 检查必要字段

```json
{
  "version": 3,           // 必填，版本 >= 3
  "model_source": "~/.workbuddy/models.json",  // 必填，字符串
  "roles": { ... },       // 必填，对象
  "settings": { ... }     // 必填，对象
}
```

### 3. 检查 roles 结构

每个 role（advanced / intermediate / basic）必须包含：

```json
{
  "advanced": {
    "label": "高级模型",
    "models": ["id-1", "id-2", "id-3"],  // 必填，非空数组
    "max_turns": 20                        // 可选，数字
  }
}
```

### 4. 验证每个 model_id 存在于 models.json

遍历每个 role 的 `models` 数组，检查每个 model_id 是否在 `~/.workbuddy/models.json` 中存在。

### 5. 验证 settings 字段

```json
{
  "settings": {
    "max_agents": 3,          // 1-5 之间的整数
    "agent_timeout_ms": 120000,  // 正整数
    "max_review_rounds": 2    // 1-3 之间的整数
  }
}
```

## 版本迁移

如果检测到 config.json 的版本 < 3：
1. 输出提示：旧版本配置检测到，需要升级
2. 读取旧配置中的 model_id 和 fallback
3. 自动构建新的 models 数组：[原 model_id, 原 fallback]。如果两者相同，尝试从 models.json 推荐一个同 vendor 的模型
4. 写入新的 config.json（version 3 格式）
5. 确认用户：配置已升级

## 验证结果处理

### 验证通过

输出：
```
✅ 配置验证通过（version {version}）
- 高级模型链：{models[0]} → {models[1]} → {models[2]} → 降级中级
- 中级模型链：{models[0]} → {models[1]} → {models[2]} → 降级下级
- 下级模型链：{models[0]} → {models[1]} → {models[2]}
- 超时设置：{agent_timeout_ms}ms
```

进入编排工作流。

### 验证失败

输出具体的错误信息：

```
❌ 配置验证失败：

错误 1：role "advanced" 的 models 数组为空
错误 2：model_id "gpt-5.5" 在 models.json 中不存在（role: advanced）
错误 3：settings.agent_timeout_ms 缺失

请编辑 ~/.workbuddy/skills/orchestrate/config.json 修复上述问题后重试。
```

不进入编排流程，等待用户修复。
