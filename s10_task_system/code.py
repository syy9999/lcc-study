"""s10 · Task System —— 我的实现

格言：大目标拆成小任务，排好序，持久化

目标：
    实现一个落盘的任务系统：任务图、依赖、认领、完成、跨会话恢复。

运行：
    python s10_task_system/code.py

关键设计：
    TaskRecord = {id, subject, description, status, blockedBy, owner}
    状态机     = pending → in_progress → completed
    can_start  → 所有 blockedBy 都 completed 才可开始
    claim_task → 原子地把 pending 改成 in_progress
    持久化     → .tasks/ 目录，每个任务一个 JSON 文件

写完再对照：
    ../learn-claude-code-main/s10_task_system/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。