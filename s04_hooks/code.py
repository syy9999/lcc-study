"""s04 · Hooks —— 我的实现

格言：挂在循环上，不写进循环里

目标：
    在工具执行前后提供扩展点（PreToolUse / PostToolUse），
    把权限、日志等横切逻辑从主循环里移出去。

运行：
    python s04_hooks/code.py

关键设计：
    HOOKS = {"PreToolUse": [...], "PostToolUse": [...]}
    run_hooks(event, context) → 可修改参数 / 阻止执行 / 记录结果
    agent_loop 只多了一次 hook 调用

写完再对照：
    ../learn-claude-code-main/s04_hooks/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。