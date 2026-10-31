"""s07 · Skill Loading —— 我的实现

格言：用到时再加载，别全塞 prompt 里

目标：
    扫描技能目录，把"技能名 + 描述"放进 system prompt；
    模型需要时通过工具加载完整 SKILL.md。

运行：
    python s07_skill_loading/code.py

关键设计：
    SkillLoader.scan()        → 技能目录（轻量）
    SkillLoader.load(name)    → 完整正文（按需）
    system prompt 只包含目录；正文通过 tool_result 注入

写完再对照：
    ../learn-claude-code-main/s07_skill_loading/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。