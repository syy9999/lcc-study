"""s06 · Subagent —— 我的实现

格言：给子任务全新的 messages[]，最终文本作为一条工具结果返回

目标：
    实现 Agent 工具：父 agent 派生子 agent，子 agent 在独立上下文里跑完整循环，
    父 agent 只收到最终文本。

运行：
    python s06_subagent/code.py

关键设计：
    run_subagent(prompt, description) → 新建 messages[] → 跑 agent_loop → 返回最终文本
    父 agent 看到的是：一次 tool_use + 一条 tool_result（文本）

写完再对照：
    ../learn-claude-code-main/s06_subagent/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。