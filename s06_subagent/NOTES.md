# s06 · Subagent —— 学习笔记

> 本章教程：[README.md](./README.md) · 参考实现：`../learn-claude-code-main/s06_subagent/code.py`

> **格言**：给子任务全新的 `messages[]`，最终文本作为一条工具结果返回

## 学习目标

- 用 Agent 工具派生一个子 agent
- 理解上下文隔离：子 agent 拥有独立的 `messages[]` 和工具循环
- 只把子 agent 的最终文本回传给父 agent

## 本章要回答的问题

1. 为什么子 agent 不共享父 agent 的 `messages`？
2. 子 agent 的中间过程为什么不需要回传？
3. 什么任务适合拆给子 agent，什么任务自己做完更好？

## 我的笔记

这里这个 deepseek-v4.1-flash-1017 模型倾向于直接回答, 不想在子 agent 里面调用工具, 我加强 SUB_SYSTEM，明确要求使用工具

## 实现记录

- [ ] 先自己写 `code.py`
- [ ] 让主 agent 派生两个子任务，验证上下文互不污染
- [ ] 对照参考实现，记录关键差异
- [ ] 用自己的话回答上面的问题

### 与参考实现的差异

<!-- 我哪里写得不一样？哪种更好？为什么？ -->

## 踩坑与疑问

<!-- 报错、失败尝试、还没想通的地方 -->

## 参考

- 本章教程：[README.md](./README.md)
- 参考实现：`../learn-claude-code-main/s06_subagent/code.py`
- 原始仓库：<https://github.com/shareAI-lab/learn-claude-code>
