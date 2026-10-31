# s10 · Task System —— 学习笔记

> 本章教程：[README.md](./README.md) · 参考实现：`../learn-claude-code-main/s10_task_system/code.py`

> **格言**：大目标拆成小任务，排好序，持久化 —— 文件持久化的任务图，多 agent 协作的基础

## 学习目标

- 实现 `TaskRecord`：状态、依赖（`blockedBy`）、owner
- 实现 `create_task` / `update_task` / `claim_task` / `complete_task` / `get_task`
- 把任务落到磁盘，支持跨会话恢复

## 本章要回答的问题

1. 任务状态机有哪些状态、哪些合法转移？
2. 依赖检查应该在哪一步做？完成后如何解锁下游任务？
3. 为什么认领（claim）必须是原子的？

## 我的笔记

<!-- 合上参考代码，用自己的话写。记"为什么"，而不只是"是什么"。 -->

## 实现记录

- [ ] 先自己写 `code.py`
- [ ] 构造一个带依赖的任务图，重启后验证状态还在
- [ ] 对照参考实现，记录关键差异
- [ ] 用自己的话回答上面的问题

### 与参考实现的差异

<!-- 我哪里写得不一样？哪种更好？为什么？ -->

## 踩坑与疑问

<!-- 报错、失败尝试、还没想通的地方 -->

## 参考

- 本章教程：[README.md](./README.md)
- 参考实现：`../learn-claude-code-main/s10_task_system/code.py`
- 原始仓库：<https://github.com/shareAI-lab/learn-claude-code>
