"""s16 · Workflow Runtime —— 我的实现

格言：编排形状固定时，就把它写进代码

目标：
    实现一个 workflow 运行时：脚本决定编排，模型决定单步；
    journal 记录每个稳定调用，支持按 runId 续跑。

运行：
    python s16_workflow_runtime/code.py

关键设计：
    workflow meta   → 启动前校验名称、参数、预算
    编排原语        → sequence / parallel / agent 调用
    journal         → 每个稳定 key 记录一次结果；命中缓存则跳过
    snapshot        → 保存 runId、workflowName、args
    resume          → 用同一 runId 继续，未变更的步骤直接复用

写完再对照：
    ../learn-claude-code-main/s16_workflow_runtime/code.py
"""

# TODO: 从零实现本章。先不要看参考代码。