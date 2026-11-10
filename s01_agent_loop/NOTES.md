# s01 · Agent Loop —— 学习笔记

> 本章教程：[README.md](./README.md) · 手把手实现教程：[TUTORIAL.md](./TUTORIAL.md) · 参考实现：`../learn-claude-code-main/s01_agent_loop/code.py`

> **格言**：One loop & Bash is all you need —— 一个工具 + 一个循环 = 一个 Agent

## 学习目标

- 理解 Agent 的最小循环：`messages → LLM → tool_use → tool_result → messages`
- 手写一个不依赖任何 Agent 框架的 `agent_loop`
- 体会"由模型决定何时调用工具、何时停止"，代码只负责执行

## 本章要回答的问题

1. `messages` 列表在循环中如何增长？每一轮的角色分别是什么？
2. 模型凭什么知道该调用工具、以及什么时候停止？
3. 为什么说"循环是 agent 的，机制是 harness 的"？

## 我的笔记

### 1. messages 是怎么"长"起来的

一轮完整的工具往返，`messages` 固定增加两条：

1. `assistant`：这一轮模型产出的**整个 content block 列表**（`thinking` + 可能的 `text` + 一个或多个 `tool_use`）；
2. `user`：把所有 `tool_result` 打包成**一条**消息，每个结果用 `tool_use_id` 指回对应的 `tool_use.id`。

关键理解：不是"一个 block 一条消息"，而是"一轮 response 一条 assistant 消息、一轮结果一条 user 消息"。拆成多条会让 `tool_use` 和 `tool_result` 的配对关系断掉，协议层直接不认。

### 2. 模型凭什么知道该调用工具、什么时候停

模型看不到我的 Python 代码，它只看到两样东西：`system` 和 `messages`。

- **知道能调工具**：因为请求里带了 `tools`（工具名、描述、`input_schema`）。工具描述就是模型对这个工具的唯一认知。
- **决定停止**：它这一轮不再输出 `tool_use` block。我的循环只是读到"没有 tool_use"就 `return`。

所以停止条件本质上是**模型的输出**，不是我写的业务逻辑。`while True` 只是个空壳节律，真正控制循环走几圈的是模型。

### 3. 循环是 agent 的，机制是 harness 的

- **Agent（循环）**：决策节律——要不要继续、调什么工具、何时停。控制权在模型手里。
- **Harness（机制）**：确定性基础设施——API 调用、历史记账、工具执行、超时/截断、错误转字符串、协议约束。

这个划分对调试很有用：agent 做了蠢决定（乱用工具、该停不停）→ 查 prompt / 工具描述；harness 出问题（崩溃、丢上下文、配对错乱、超时）→ 查机制代码。

### 4. content block 的协议细节

- `content` 可以是**字符串**（纯文本快捷写法），也可以是 **block 列表**；每个 block 按 `type` 判别，并且和 role 绑定：
  - user：`text`、`image`、`document`、`tool_result`
  - assistant：`text`、`thinking`、`tool_use`、`redacted_thinking`
- SDK 响应给的是 pydantic 对象（`TextBlock`、`ToolUseBlock`...），我手写的是 dict，两者序列化后是同一份 JSON，都能传回去。
- `tool_result` 只能放在 user 消息里，且要放在该消息 content 的开头；`thinking` block 必须原样回传，不能删也不能改。
- 这些约束解释了为什么"整个 `response.content` 一起 append"最稳：逐块挑着 append 很容易漏掉 `thinking` 或打乱配对。

### 5. 一个观察：system prompt 决定了 agent 的行为边界

我让 agent 回答"Python 是什么"，它却跑了 4 轮工具（查版本、列目录、读 `hello.py`、跑示例），共 5 次 API 请求。原因是 `SYSTEM` 里写了 `"Use bash to solve tasks. Act, don't explain."`，而它只有 bash 一个工具——所有问题都会被它当成"用 bash 解决的任务"。

结论：**工具集 + system prompt 共同框定了 agent 的行为**。只有 bash 时，它会把一切往 bash 上靠。这也解释了后面章节为什么要加更多工具、写更细的 prompt。

### 6. run_bash 的设计原则

- **工具失败不能让 harness 崩溃**：超时、`OSError` 都转成 `"Error: ..."` 字符串——错误本身也是模型需要观察的结果。
- **输出要截断**（50k）：避免一次 `dir /s` 把上下文撑爆。
- **危险命令名单只是最低限度护栏**，不是安全边界；真正的隔离要靠后面的权限/沙箱机制。
- `shell=True` 在 Windows 上走 cmd.exe，所以 system prompt 里要明确告诉模型"用 cmd 语法，不是 Unix Bash / PowerShell"。

### 7. 留给自己验证的问题

- `stop_reason == "max_tokens"` 且没有 `tool_use` 时，当前会静默 `return`，输出其实是被截断的——要不要显式提示？
- `block.input["command"]` 换成 `.get("command")` 是否更稳？模型偶尔会发出不合 schema 的 input。
- 同一轮有多个 `tool_use` 时，现在是串行执行，要不要并发？并发的话结果顺序和 `tool_use_id` 配对怎么保证？

## 实现记录

- [ ] 先自己写 `code.py`
- [ ] 跑通一个真实任务（例如：让 agent 查看当前目录）
- [ ] 对照参考实现，记录关键差异
- [ ] 用自己的话回答上面的问题

### 与参考实现的差异

<!-- 我哪里写得不一样？哪种更好？为什么？ -->

## 踩坑与疑问

### 输入"Python 是什么"，agent 却跑去敲了一堆命令

**现象**：问的是知识性问题，agent 却连跑 4 轮工具（查版本、列目录、读 `hello.py`、跑示例），共 5 次 API 请求，最后还自己补了一句"需要我帮你做哪一项？"。

**原因**：不是 loop 的问题，而是 `SYSTEM` 写了 `"Use bash to solve tasks. Act, don't explain."`，加上手头只有 bash 一个工具——模型会把所有输入都当成"用 bash 解决的任务"，知识性问题也只能靠跑命令来"演示"。

**结论**：agent 的行为边界由 **system prompt + 工具集**共同决定，harness 本身没有错。这正好是后面章节要加工具、写更细 prompt 的动机。

**待验证**：在 `SYSTEM` 里加一句类似 "If the question needs no tool, answer directly"，再问同样的问题，对比工具调用次数和回答质量。

## 参考

- 本章教程：[README.md](./README.md)
- 参考实现：`../learn-claude-code-main/s01_agent_loop/code.py`
- 原始仓库：<https://github.com/shareAI-lab/learn-claude-code>
