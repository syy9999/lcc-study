# s08 · Context Compact —— 学习笔记

> 本章教程：[README.md](./README.md) · 参考实现：`../learn-claude-code-main/s08_context_compact/code.py`

> **格言**：上下文总会满，要有办法腾地方 —— 四步压缩：先整理工具结果，仍然超限时再生成历史摘要

## 学习目标

- 理解四步压缩：`tool_result_budget → snip_compact → micro_compact → compact_history`
- 实现工具结果的截断 / 摘要，并保证 `tool_use` 与 `tool_result` 配对完整
- 处理 API 因上下文超限而拒绝后的补救

## 本章要回答的问题

1. 为什么先整理工具结果，最后才做历史摘要？
2. 压缩时如何保证 `tool_use` 与 `tool_result` 不被拆散？
3. 压缩后必须保留哪些信息，agent 才能继续任务？

## 我的笔记

<!-- 合上参考代码，用自己的话写。记"为什么"，而不只是"是什么"。 -->

## 实现记录

- [ ] 先自己写 `code.py`
- [ ] 构造长对话，观察每一步压缩前后的 token 变化
- [ ] 对照参考实现，记录关键差异
- [ ] 用自己的话回答上面的问题

### 与参考实现的差异

<!-- 我哪里写得不一样？哪种更好？为什么？ -->

## 踩坑与疑问

<!-- 报错、失败尝试、还没想通的地方 -->

## 参考

- 本章教程：[README.md](./README.md)
- 参考实现：`../learn-claude-code-main/s08_context_compact/code.py`
- 原始仓库：<https://github.com/shareAI-lab/learn-claude-code>
