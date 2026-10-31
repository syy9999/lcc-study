# lcc-study · 手写 Claude Code 的 Agent Harness

> 个人学习仓库：跟着 [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) 的 17 章课程，
> **自己敲代码、自己写笔记、自己踩坑**，从零实现一个编程 Agent 的 harness。

## 仓库定位

| 项目 | 说明 |
|---|---|
| 参考仓库 | `../learn-claude-code-main/`（课程原文 + 完整参考实现） |
| 本仓库 | 我的独立实现 + 学习笔记 + 实验记录 |

参考仓库刻意**不复制**进来，避免"照着抄一遍"的假学习。每章的对照入口写在章节 `README.md` 底部。

## 核心认知

- **Agent = 模型 + Harness**。Agency 来自模型，harness 提供工具、知识、观察、行动接口和权限边界。
- 17 章每章增加一个 harness 机制，最终都挂回同一个 agent loop。
- 这里练的是 **harness 工程**：造载具，而不是训练驾驶者，也不是用 if-else 编排提示词。

```
Agent Loop:
    User → messages[] → LLM → 有 tool_use? → 执行工具 → 追加 tool_result → 回到 LLM
                                   └─ 没有 tool_use → 返回文本，循环结束
```

## 学习方式

每章按同样的节奏推进：

1. **读**：打开参考仓库的 `README.zh.md`，理解这一章要解决什么问题。
2. **写**：合上参考代码，自己实现本章的 `code.py`。
3. **跑**：用一个真实任务验证，记录输入、输出和报错。
4. **对照**：写完之后再看参考实现，把差异写进章节 `README.md`。
5. **复盘**：用自己的话回答"本章要回答的问题"。

> 关键原则：**先自己写，再对照**。直接抄一遍参考实现，学习效果接近于零。

## 目录结构

```text
lcc-study/
├── README.md                 # 本文件：仓库说明与 17 章地图
├── PROGRESS.md               # 17 章进度追踪
├── CLAUDE.md                 # 给 Claude Code 的协作约定
├── requirements.txt          # 运行依赖
├── requirements-dev.txt      # 开发依赖（pytest / ruff）
├── .env.example              # 环境变量模板
├── notes/                    # 跨章节笔记、术语表
├── scripts/
│   └── check_setup.py        # 环境自检
├── tests/                    # 我自己补充的测试
├── s01_agent_loop/           # 每章一个文件夹，与参考仓库同名
│   ├── README.md             #   学习目标 + 我的笔记 + 差异记录
│   └── code.py               #   我自己的实现
├── s02_tool_use/
├── ...
└── s17_goal_loop/
```

## 快速开始

```sh
# 1. 创建虚拟环境（在仓库根目录）
python -m venv .venv

# Git Bash
source .venv/Scripts/activate
# CMD:      .venv\Scripts\activate.bat
# PowerShell: .venv\Scripts\Activate.ps1

# 2. 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt   # 可选：测试与格式化

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY 和 MODEL_ID
# 使用 Anthropic 兼容服务时，再设置 ANTHROPIC_BASE_URL

# 4. 环境自检
python scripts/check_setup.py

# 5. 运行某一章
python s01_agent_loop/code.py
```

## 17 章地图

| 阶段 | 章节 | 主题 | 本章新增的 harness 机制 |
|---|---|---|---|
| ① 能动手 | [s01](./s01_agent_loop/) | Agent Loop | 一个循环 + bash |
| ① 能动手 | [s02](./s02_tool_use/) | Tool Use | 工具注册表 / dispatch map |
| ① 能动手 | [s03](./s03_permission/) | Permission | 执行前的权限判断 |
| ① 能动手 | [s04](./s04_hooks/) | Hooks | PreToolUse / PostToolUse 扩展点 |
| ② 做复杂任务 | [s05](./s05_todo_write/) | TodoWrite | 先计划、再执行 |
| ② 做复杂任务 | [s06](./s06_subagent/) | Subagent | 独立 messages[] 的子 agent |
| ② 做复杂任务 | [s08](./s08_context_compact/) | Context Compact | 四步上下文压缩 |
| ③ 跨会话记忆 | [s09](./s09_memory/) | Memory | 选择 / 提取 / 整理 |
| ④ 长期运行 | [s10](./s10_task_system/) | Task System | 持久化任务图与依赖 |
| ④ 长期运行 | [s11](./s11_background_tasks/) | Background Tasks | 后台线程 + 通知队列 |
| ④ 长期运行 | [s12](./s12_cron_scheduler/) | Cron Scheduler | 持久化定时触发 |
| ⑤ 多 Agent 协作 | [s13](./s13_agent_teams/) | Agent Teams | 队友 / 消息总线 / 原子认领 / worktree |
| ⑥ 扩展与合体 | [s07](./s07_skill_loading/) | Skill Loading | 技能目录 + 按需加载 |
| ⑥ 扩展与合体 | [s14](./s14_mcp_plugin/) | MCP Plugin | 外部工具接入同一工具池 |
| ⑥ 扩展与合体 | [s15](./s15_integrated_harness/) | Integrated Harness | 多种机制归入一个循环 |
| ⑦ 编排与目标 | [s16](./s16_workflow_runtime/) | Workflow Runtime | 脚本编排 + journal 续跑 |
| ⑦ 编排与目标 | [s17](./s17_goal_loop/) | Goal Loop | 独立判断器决定循环是否结束 |

## 约定

- 章节目录与参考仓库**同名**，方便直接对比：`diff s01_agent_loop/code.py ../learn-claude-code-main/s01_agent_loop/code.py`。
- `code.py` 是"我的实现"。引用或改写参考代码时，在文件头注明来源。
- 笔记用中文，代码标识符用英文，注释可中英混用。
- 课程运行时生成的 `.memory/`、`.tasks/`、`.worktrees/` 等状态目录已被 `.gitignore` 忽略。
- 每完成一章，更新 [`PROGRESS.md`](./PROGRESS.md)；跨章节的总结放 `notes/`。

## 进度

→ [PROGRESS.md](./PROGRESS.md)

## 参考

- 课程仓库：<https://github.com/shareAI-lab/learn-claude-code>
- 本地参考：`../learn-claude-code-main`
- 心法：**Agency 来自模型，Harness 让 agency 落地。造好 Harness，模型会完成剩下的。**

## License

个人学习仓库。参考课程内容的版权归原作者；本仓库的代码与笔记采用 MIT。