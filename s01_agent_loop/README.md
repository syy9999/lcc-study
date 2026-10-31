# s01 · Agent Loop

> **格言**：One loop & Bash is all you need —— 一个工具 + 一个循环 = 一个 Agent

## 学习目标

- 理解 Agent 的最小循环：`messages → LLM → tool_use → tool_result → messages`
- 手写一个不依赖任何 Agent 框架的 `agent_loop`
- 体会"由模型决定何时调用工具、何时停止"，代码只负责执行

## 本章要回答的问题

1. `messages` 列表在循环中如何增长？每一轮的角色分别是什么？
2. 模型凭什么知道该调用工具、以及什么时候停止？
3. 为什么说"循环是 agent 的，机制是 harness 的"？

## 我的笔记

<!-- 合上参考代码，用自己的话写。记"为什么"，而不只是"是什么"。 -->

## 实现记录

- [ ] 先自己写 `code.py`
- [ ] 跑通一个真实任务（例如：让 agent 查看当前目录）
- [ ] 对照参考实现，记录关键差异
- [ ] 用自己的话回答上面的问题

### 与参考实现的差异

<!-- 我哪里写得不一样？哪种更好？为什么？ -->

## 踩坑与疑问

<!-- 报错、失败尝试、还没想通的地方 -->

## 参考

- 章节讲解：`../learn-claude-code-main/s01_agent_loop/README.zh.md`
- 参考实现：`../learn-claude-code-main/s01_agent_loop/code.py`