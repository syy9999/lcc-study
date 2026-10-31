"""s03 · Permission —— 我的实现

格言：先划边界，再给自由

目标：
    在工具执行前加入权限管线：放行 / 询问用户 / 拒绝。
    权限判断属于 harness，不属于工具实现。

运行：
    python s03_permission/code.py

关键设计：
    PermissionRule  → 匹配工具与参数
    check_permission → allow / ask / deny
    agent_loop       → 执行工具前先过权限

写完再对照：
    ../learn-claude-code-main/s03_permission/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。