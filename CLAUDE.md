# CLAUDE.md

本仓库是个人学习仓库：跟随 learn-claude-code 课程，手写每一章的 Agent Harness 实现并做笔记。

## 协作约定

- **默认引导式**：我先自己写。请优先解释思路、指出方向、给最小提示，不要直接输出完整实现。
- 如果我说"给答案 / 直接写 / 帮我实现"，再给出完整代码。
- 不要覆盖 `s*/code.py` 里已有的实现；建议改动时先说明原因，并给出 diff 或修改建议。
- 笔记和解释使用中文；代码标识符使用英文。
- 参考仓库在 `../learn-claude-code-main/`，只在需要对照或我明确要求时读取。

## 结构约定

- 每章一个目录 `sNN_topic/`，与参考仓库同名。
- `README.md` = 从参考仓库导入的中文教程，由 `scripts/import_tutorials.py` 维护，不要手改。
- `NOTES.md` = 学习目标 + 我的笔记 + 与参考实现的差异。
- `code.py` = 我的独立实现，可单文件直接运行。
- `images/` = 教程配图；`skills/` = s07 技能示例。
- 跨章节笔记放 `notes/`；进度记录在 `PROGRESS.md`。

## 模型服务

- 供应商：阿里云百炼（DashScope），不是 Anthropic 官方 API。
- 协议：继续使用 `anthropic` SDK 的 Messages API，但 `base_url` 指向百炼的 Anthropic 兼容端点。
- 环境变量：`DASHSCOPE_API_KEY`、`DASHSCOPE_BASE_URL`、`MODEL_ID=deepseek-v4.1-flash-1017`。
- 不要引入 `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` 配置；创建客户端时显式传参：
  `Anthropic(api_key=os.environ["DASHSCOPE_API_KEY"], base_url=os.environ["DASHSCOPE_BASE_URL"])`。
- 导入的教程里如出现 `ANTHROPIC_*` 示例，已由 `scripts/import_tutorials.py` 替换为 `DASHSCOPE_*`。
- conda 环境名为 `lcc-study`。

## 常用命令

- 环境自检：`conda run --no-capture-output -n lcc-study python scripts/check_setup.py`
- 运行章节：`conda run --no-capture-output -n lcc-study python s01_agent_loop/code.py`
- 测试：`conda run --no-capture-output -n lcc-study python -m pytest`
- 与参考实现对比：`diff s01_agent_loop/code.py ../learn-claude-code-main/s01_agent_loop/code.py`

> Windows 上 `conda run` 捕获中文输出可能触发 GBK 编码错误，统一加 `--no-capture-output`。