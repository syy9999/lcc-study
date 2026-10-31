"""s11 · Background Tasks —— 我的实现

格言：慢操作丢后台，agent 继续思考

目标：
    让慢命令在后台线程执行，主循环继续；完成后通过通知队列把结果送回模型。

运行：
    python s11_background_tasks/code.py

关键设计：
    BackgroundManager.start()             → 启动线程
    BackgroundManager.poll()/results      → 查询状态与结果
    collect_background_results()          → 在回合边界注入通知
    显式请求（如 run_in_background）优先；也可按命令特征判断

写完再对照：
    ../learn-claude-code-main/s11_background_tasks/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。