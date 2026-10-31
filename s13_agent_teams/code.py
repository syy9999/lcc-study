"""s13 · Agent Teams —— 我的实现

格言：一个 Agent 顾不过来，就让队友分工协作

目标：
    实现持久队友、消息总线、原子任务认领、任务绑定的 worktree。

运行：
    python s13_agent_teams/code.py

关键设计：
    Teammate       = 独立 messages[] + 自己的 agent loop
    MessageBus     = 收件箱事件，不进入模型上下文
    claim_task     = 原子操作，避免两个队友抢同一任务
    worktree       = 每个任务一个独立工作目录，互不污染
    IDLE 顺序      = 先看收件箱，再找 ready task

写完再对照：
    ../learn-claude-code-main/s13_agent_teams/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。