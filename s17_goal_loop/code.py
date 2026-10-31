"""s17 · Goal Loop —— 我的实现

格言：目标决定循环什么时候真正结束

目标：
    实现 /goal：模型每轮准备停止时，由独立判断器审查目标；
    未完成则自动续轮，直到完成或触发退出条件。

运行：
    python s17_goal_loop/code.py

关键设计：
    /goal <完成条件>     → 设置会话级目标
    Stop hook           → 模型想停止时触发判断
    judge（独立模型）    → 根据对话记录判断 completed / not_completed / impossible
    续跑上限             → 防止无限循环
    出口                → 已完成 / 不可能 / 执行失败 / 超限 → 交还用户

写完再对照：
    ../learn-claude-code-main/s17_goal_loop/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。