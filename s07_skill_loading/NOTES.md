# s07 · Skill Loading —— 学习笔记

> 本章教程：[README.md](./README.md) · 参考实现：`../learn-claude-code-main/s07_skill_loading/code.py`

> **格言**：用到时再加载，别全塞 prompt 里 —— 技能先列目录，用到时再展开

## 学习目标

- 实现 `SkillLoader`：扫描技能目录、生成技能清单
- system prompt 里只放技能名和描述，正文按需加载
- 体会"知识的分层注入"如何节省上下文

## 本章要回答的问题

1. 技能目录和完整技能正文分别何时进入上下文？
2. 如何避免技能命名冲突？如何让模型知道什么时候该用哪个技能？
3. 什么知识适合做成 skill，而不是工具或直接写进 system prompt？

## 我的笔记

<!-- 合上参考代码，用自己的话写。记"为什么"，而不只是"是什么"。 -->

## 实现记录

- [ ] 先自己写 `code.py`
- [ ] 自带 2 个技能，验证模型会先查目录、再加载正文
- [ ] 对照参考实现，记录关键差异
- [ ] 用自己的话回答上面的问题

### 与参考实现的差异

<!-- 我哪里写得不一样？哪种更好？为什么？ -->

## 踩坑与疑问

<!-- 报错、失败尝试、还没想通的地方 -->

## 参考

- 本章教程：[README.md](./README.md)
- 参考实现：`../learn-claude-code-main/s07_skill_loading/code.py`
- 技能示例：`../learn-claude-code-main/skills/`
- 原始仓库：<https://github.com/shareAI-lab/learn-claude-code>
