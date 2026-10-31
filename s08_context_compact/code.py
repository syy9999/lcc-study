"""s08 · Context Compact —— 我的实现

格言：上下文总会满，要有办法腾地方

目标：
    实现四步压缩管线，在上下文接近上限时腾出空间，
    同时不破坏 tool_use / tool_result 的配对。

运行：
    python s08_context_compact/code.py

关键设计：
    1. tool_result_budget  截断超长工具输出
    2. snip_compact        丢弃较早的完整回合
    3. micro_compact       对中间结果做局部摘要
    4. compact_history     生成整体历史摘要
    + API 拒绝后的补救路径

写完再对照：
    ../learn-claude-code-main/s08_context_compact/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。