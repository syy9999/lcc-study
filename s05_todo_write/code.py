"""s05 · TodoWrite —— 我的实现

格言：没有计划的 agent 走哪算哪

目标：
    给 agent 一个 todo_write 工具，让它先列计划、再执行、并持续更新状态。

运行：
    python s05_todo_write/code.py

关键设计：
    TodoItem   = {content, status, activeForm}
    todo_write = 用完整列表覆盖当前计划（不是增量修改）
    system / tool description 明确要求：复杂任务先写 todo

写完再对照：
    ../learn-claude-code-main/s05_todo_write/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。