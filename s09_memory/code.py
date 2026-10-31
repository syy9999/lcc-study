"""s09 · Memory —— 我的实现

格言：记住该记的，忘掉该忘的

目标：
    实现跨会话记忆：回合结束后提取可复用信息，存成一条一个文件；
    下次会话先选相关记忆，再加载正文。

运行：
    python s09_memory/code.py

关键设计：
    selection    → 根据当前任务挑选相关记忆（先看索引/描述）
    extraction   → 回合结束后判断值不值得保存
    consolidation → 合并重复、更新过期、删除无用
    存储         → .memory/ 目录，一条记忆一个 Markdown 文件

写完再对照：
    ../learn-claude-code-main/s09_memory/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。