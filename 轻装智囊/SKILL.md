---
name: 轻装智囊
description: "🪶 零依赖多模型编排——不需要 openai、langchain 等任何 AI 库，只靠 requests 就能调用 GPT-5.5、Claude、DeepSeek、GLM 等多个大模型并行分析。功能与智囊团完全对等，但更轻量。适合 Docker、离线环境、安全审计场景。当用户说「轻装智囊」「零依赖编排」「裸调API」时触发。"
agent_created: true
---

# 🪶 轻装智囊 — 零依赖多模型编排

> 不需要装任何 AI 库。`import requests`，GPT-5.5 + Claude + DeepSeek + GLM 同时为你工作。

---

## ⚡ 一句话搞定

| 你说 | 效果 |
|------|------|
| **「轻装智囊，分析xxx」** | 拆解→并行→聚合，纯 requests 实现 |
| **「裸调 API 对比四个模型」** | 并行多模型，HTTP 层完全可控 |

---

## 🎯 和智囊团的区别

| 场景 | 用哪个 |
|------|--------|
| 日常 WorkBuddy 里分析 | 🧠 智囊团（openai 库接口更规范） |
| Docker/服务器/离线环境 | 🪶 轻装智囊（只需 `pip install requests`） |
| 安全审计要求不能引入 openai 库 | 🪶 轻装智囊 |
| 想完全控制 HTTP 请求细节 | 🪶 轻装智囊 |

**功能完全一样。** 拆解→并行→聚合，进度反馈、失败重试、自动同步 models.json——全有。

---

## 🔧 零依赖意味着什么？

- **不装 openai（100MB+），不装 langchain（200MB+）** — 一个 `requests` 库打天下
- **HTTP 层完全透明** — 请求体、响应头、状态码全在你手里
- **API 调用失败不黑盒** — 直接给你 HTTP 状态码和响应体原文

---

## 🏆 实测效果

和智囊团一样快——并行 10-30 秒，完整编排 60-90 秒。`ThreadPoolExecutor` 真并行，GPT-5.5、Claude、DeepSeek、GLM 互不阻塞。
