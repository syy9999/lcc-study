"""s01 · Agent Loop —— 我的实现

格言：One loop & Bash is all you need

目标：
    一个循环 + 一个 bash 工具，完成一个最小 Agent。

运行：
    python s01_agent_loop/code.py

流程：
    messages → LLM → 有 tool_use？ → 执行工具 → 追加 tool_result → 回到 LLM
                        └─ 没有 tool_use → 输出文本，循环结束

写完再对照：
    ../learn-claude-code-main/s01_agent_loop/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。