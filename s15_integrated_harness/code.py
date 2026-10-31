"""s15 · Integrated Harness —— 我的实现

格言：多种机制，一个循环

目标：
    把前面章节的机制接回同一个 agent loop，形成可用的集成 harness。

运行：
    python s15_integrated_harness/code.py

建议顺序：
    1. 先搭回 s01-s02 的 loop + 工具池
    2. 挂权限与 hooks（s03-s04）
    3. 加 todo、subagent、skill、compact（s05-s08）
    4. 加 memory、task、background、cron（s09-s12）
    5. 加团队与 MCP（s13-s14）
    6. 保持主循环可读：每个机制一个挂载点

写完再对照：
    ../learn-claude-code-main/s15_integrated_harness/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。