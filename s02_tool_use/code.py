"""s02 · Tool Use —— 我的实现

格言：加一个工具，只加一个 handler

目标：
    把 s01 的单工具循环扩展成多工具注册表（dispatch map），
    并支持一轮内多个 tool_use。

运行：
    python s02_tool_use/code.py

关键设计：
    TOOLS          = [工具 schema 列表]
    TOOL_HANDLERS  = {工具名: 处理函数}
    agent_loop 只负责：调模型 → 查表执行 → 回传 tool_result

写完再对照：
    ../learn-claude-code-main/s02_tool_use/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。