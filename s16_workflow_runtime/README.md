# s16 · Workflow Runtime

> **格言**：编排形状固定时，就把它写进代码 —— 保存好的 workflow 使用 journal 续跑

## 学习目标

- 用脚本定义固定编排，单步仍由模型决定
- 实现生命周期事件、结构化输出和 journal
- 用 `runId` 续跑，复用未变更的步骤

## 本章要回答的问题

1. 什么场景适合 workflow，而不是自由 agent loop？
2. journal 需要记录哪些信息，才能可靠续跑？
3. 子 agent 如何返回结构化输出，而不是一段散文？

## 我的笔记

<!-- 合上参考代码，用自己的话写。记"为什么"，而不只是"是什么"。 -->

## 实现记录

- [ ] 先自己写 `code.py`
- [ ] 跑一个 workflow，中断后用同一个 runId 续跑
- [ ] 对照参考实现，记录关键差异
- [ ] 用自己的话回答上面的问题

### 与参考实现的差异

<!-- 我哪里写得不一样？哪种更好？为什么？ -->

## 踩坑与疑问

<!-- 报错、失败尝试、还没想通的地方 -->

## 参考

- 章节讲解：`../learn-claude-code-main/s16_workflow_runtime/README.zh.md`
- 参考实现：`../learn-claude-code-main/s16_workflow_runtime/code.py`