"""s12 · Cron Scheduler —— 我的实现

格言：定时触发，不需要人推

目标：
    实现 cron 调度：解析五段式表达式，持久化任务，到期入队，agent 空闲时交付。

运行：
    python s12_cron_scheduler/code.py

关键设计：
    CronJob      = {id, cron, prompt, enabled, last_fired}
    parse_cron() → 字段集合
    matches()    → 当前时间是否命中
    到期任务先进入 pending 队列；空闲时注入对话
    持久化       → .scheduled_tasks.json

写完再对照：
    ../learn-claude-code-main/s12_cron_scheduler/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。