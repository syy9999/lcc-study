# s01 手把手：从零写出 Agent Loop

> 配套阅读：[README.md](./README.md)（原理）· [NOTES.md](./NOTES.md)（笔记）· 参考实现：`../learn-claude-code-main/s01_agent_loop/code.py`
>
> README 讲的是“骨架”，这份教程补的是三样东西：**协议细节**（一次请求/响应到底长什么样）、**状态变化**（`messages` 每一轮怎么增长）、**验证方法**（每写一段，怎么知道它是对的）。
>
> 建议分 3～4 次写完，不要一次写完再运行。每通过一个“检查点”再往下走。

---

## 0. 最终你会得到什么

一个单文件程序 `s01_agent_loop/code.py`，运行后可以和模型连续对话。模型可以决定执行 shell 命令，看到结果后继续推理，直到它不再调用工具为止。

一次典型交互（示意）：

```text
s01 >> Create hello.py that prints "Hello, World!", then run it.

$ echo print("Hello, World!") > hello.py
(no output)
$ python hello.py
Hello, World!

Done. I created hello.py and ran it; the output was "Hello, World!".
```

文件只有 6 个部分，按这个顺序写：

| 部分 | 作用 | 这一部分的学习价值 |
|---|---|---|
| 1. 配置 | 读取 `.env`，创建 API 客户端 | 低（照抄即可） |
| 2. System Prompt | 告诉模型“你是谁、在哪个目录、用什么 shell” | 中 |
| 3. `TOOLS` | 用 JSON Schema 描述 bash 工具 | 高 |
| 4. `run_bash` | 真正执行命令，把结果变成字符串 | 高 |
| 5. `agent_loop` | 整个 harness 的核心 | **最高** |
| 6. 交互入口 | 读用户输入，维护多轮对话 | 低 |

一句话概括这一章：

> **模型负责决定“下一步做什么”，循环负责“把决定变成行动，再把结果交还给模型”。**

---

## 1. 先搞清楚：谁在做什么

### 1.1 模型不能执行任何东西

你让模型“列出当前目录的文件”，它不会真的去读磁盘。它能做的是：**生成一段结构化的文字，表示“我想调用 bash，命令是 `dir`”**。

真正执行命令的是你的 Python 程序。执行完以后，你把输出再发回给模型。模型看到输出，才能继续推理。

所以这里有两个角色：

| 角色 | 职责 |
|---|---|
| 模型 | 决策：要不要调工具、调哪个、参数是什么、什么时候停 |
| Harness（你的 `code.py`） | 执行：发请求、跑工具、把结果写回对话、决定循环是否继续 |

注意最后一条：**“什么时候停”也是模型决定的**。你的代码只检查“这一轮有没有 `tool_use`”，有就继续，没有就退出。代码不判断任务是否完成。

### 1.2 每次 API 调用都是无状态的

`client.messages.create(...)` 不是“接着上次聊”，而是**一次全新的请求**。服务端不保存你的对话历史。

模型之所以能“记得”上一轮，是因为你每次把完整的 `messages` 列表重新发给它。`messages` 就是模型的全部短期记忆。

这也解释了两个常见现象：

- 为什么 `messages` 会越来越长？因为每一轮都要把历史全部带上。
- 为什么后面需要 s08 Context Compact？因为 `messages` 最终会超出上下文窗口。

### 1.3 循环的唯一状态是 `messages`

整个 Agent Loop 不维护别的状态。你不需要一个 `current_task`、`step_count`、`is_done` 之类的变量。循环每转一圈，只做一件事：**往 `messages` 里追加内容**。

```text
messages: [user]
   ↓ 调模型
messages: [user, assistant(tool_use)]
   ↓ 执行工具
messages: [user, assistant(tool_use), user(tool_result)]
   ↓ 再调模型
messages: [user, assistant(tool_use), user(tool_result), assistant(text)]
   ↓ 没有 tool_use
结束
```

把这张图记住，后面写代码时就不会乱。

---

## 2. 一次工具调用在协议里长什么样

这一节不写代码，但非常重要。看不懂协议，后面报错会一头雾水。

### 2.1 请求

你发给模型的东西，简化后是这样：

```json
{
  "model": "deepseek-v4.1-flash-1017",
  "system": "You are a coding agent at ...",
  "messages": [
    {"role": "user", "content": "List the Python files in this directory."}
  ],
  "tools": [
    {
      "name": "bash",
      "description": "Run a shell command.",
      "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"]
      }
    }
  ],
  "max_tokens": 8000
}
```

几个字段的含义：

| 字段 | 含义 |
|---|---|
| `model` | 用哪个模型 |
| `system` | 系统提示，不属于 `messages`；每次请求都要带上 |
| `messages` | 到目前为止的完整对话 |
| `tools` | 模型“可以申请使用”的工具清单；每次请求都要带上 |
| `max_tokens` | 这次响应最多生成多少 token（是输出上限，不是上下文上限） |

### 2.2 响应

模型如果决定调用工具，响应大致是：

```json
{
  "role": "assistant",
  "content": [
    {"type": "text", "text": "I'll list the Python files."},
    {
      "type": "tool_use",
      "id": "toolu_01ABC...",
      "name": "bash",
      "input": {"command": "dir /b *.py"}
    }
  ],
  "stop_reason": "tool_use"
}
```

要点：

- `content` 是一个**列表**，可能同时包含 `text` 和 `tool_use`。
- `tool_use` 里有三个关键字段：`id`、`name`、`input`。
- `stop_reason` 是 `tool_use`，表示“我停下来是因为我要调工具”。
- 此时命令**还没有执行**。`input` 只是模型填好的参数。

模型如果给出最终回答，响应大致是：

```json
{
  "role": "assistant",
  "content": [{"type": "text", "text": "There are 3 Python files: ..."}],
  "stop_reason": "end_turn"
}
```

### 2.3 工具结果怎么回传

执行完命令后，你要新增一条 **user 角色**的消息：

```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01ABC...",
      "content": "a.py\nb.py\nc.py"
    }
  ]
}
```

注意三个细节：

1. `tool_result` 必须放在 `user` 消息里。虽然它不是“用户说的话”，但协议就是这么规定的。
2. `tool_use_id` 必须等于之前那个 `tool_use` 的 `id`。API 靠它把“调用”和“结果”配对。
3. 在这条 `tool_result` 之前，**必须先把包含 `tool_use` 的 assistant 消息追加进 `messages`**。否则 API 会认为你在返回一个“不存在于对话中的调用结果”。

配对关系可以画成这样：

```text
assistant 消息:  tool_use(id="toolu_01ABC", name="bash", input={...})
                              │
                              │  同一个 id
                              ▼
user 消息:       tool_result(tool_use_id="toolu_01ABC", content="...")
```

### 2.4 为什么用“有没有 `tool_use`”判断是否继续

`stop_reason` 也能告诉你模型为什么停，但循环判断用 `tool_use` block 更直接：

- 有 `tool_use` → 模型在等你执行工具 → 执行、回传、继续。
- 没有 `tool_use` → 模型已经给出最终回答 → 退出。

`stop_reason` 还有 `max_tokens`、`end_turn`、`stop_sequence` 等情况，适合用来诊断，不适合作为唯一的循环条件。

---

## 3. 准备环境

在仓库根目录执行：

```sh
conda run --no-capture-output -n lcc-study python scripts/check_setup.py
```

全部 OK 再继续。如果 `--ping` 也通过，说明 API Key、端点、模型 ID 都没问题：

```sh
conda run --no-capture-output -n lcc-study python scripts/check_setup.py --ping
```

确认 `.env` 里至少有这三项：

```dotenv
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/apps/anthropic
MODEL_ID=deepseek-v4.1-flash-1017
```

> `DASHSCOPE_BASE_URL` 只写到 `/apps/anthropic`，不要自己加 `/v1/messages`；SDK 会自动拼接。

> **不要在代码里写死 Key**，也不要把 `.env` 提交到 git。

> **安全提示**：从第 7 节开始，程序会执行**模型生成的 shell 命令**。建议第一次先在一个临时目录里测试，不要在有重要文件或密钥的目录里运行。本章的 `dangerous` 列表只是最低限度护栏，不是安全边界；真正的权限控制在 s03。
>
> 本教程用 `ROOT / ".env"` 的绝对路径读取配置，所以你可以从任意目录运行 `code.py`。想让 agent 在临时目录里工作，就 `cd` 到临时目录后再运行。

### ✅ 检查点 0

- [ ] `check_setup.py` 全部通过
- [ ] 你知道 `.env` 在仓库根目录
- [ ] 你知道 `check_setup.py` 要在仓库根目录执行

---

## 4. 先搭一个空骨架

打开 `s01_agent_loop/code.py`，先把配置写进去。**这一步只写配置，不写循环。**

```python
"""s01 · Agent Loop —— 我的实现

一个循环 + 一个 bash 工具 = 最小 Agent。
运行：python s01_agent_loop/code.py
"""

import os
import subprocess
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

# .env 在仓库根目录。用绝对路径，避免“从哪个目录运行”影响读取。
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

client = Anthropic(
    api_key=os.environ["DASHSCOPE_API_KEY"],
    base_url=os.environ["DASHSCOPE_BASE_URL"],
)
MODEL = os.environ["MODEL_ID"]
```

逐行解释：

| 代码 | 为什么这么写 |
|---|---|
| `ROOT = Path(__file__).resolve().parent.parent` | `code.py` 在 `s01_agent_loop/` 下，往上两级就是仓库根目录 |
| `load_dotenv(ROOT / ".env", override=True)` | 显式指定 `.env` 路径，比依赖当前工作目录可靠 |
| `Anthropic(api_key=..., base_url=...)` | 显式传参，不使用 `ANTHROPIC_*` 环境变量；这是本仓库的约定 |
| `MODEL = os.environ["MODEL_ID"]` | 模型 ID 也放在 `.env`，方便切换 |

> **为什么不用 `load_dotenv()` 不带参数？** 它默认从当前工作目录找 `.env`。如果你在别的目录运行 `python E:\...\s01_agent_loop\code.py`，就会找不到。显式路径少一个坑。

### ✅ 检查点 1

先别调用 API。在文件末尾临时加：

```python
if __name__ == "__main__":
    print("MODEL =", MODEL)
    print("client ready")
```

然后运行：

```sh
conda run --no-capture-output -n lcc-study python s01_agent_loop/code.py
```

看到 `client ready` 就说明配置没问题。确认后把这段临时入口删掉（或替换成后面的正式入口）。

---

## 5. 第 1 步：让模型先开口（不带工具）

现在写第一段真正调用 API 的代码。**先不加工具**，只确认链路通。

在配置下面追加：

```python
ENVIRONMENT_PROMPT = (
    "Windows: the bash tool runs through cmd.exe; use cmd.exe syntax, "
    "not Unix Bash or PowerShell syntax"
    if os.name == "nt"
    else "Unix-like: the bash tool runs the system shell"
)

SYSTEM = (
    f"You are a coding agent at {os.getcwd()}. "
    f"Environment: {ENVIRONMENT_PROMPT}. "
    "Use bash to solve tasks. Act, don't explain."
)
```

然后写一个临时实验：

```python
messages = [{"role": "user", "content": "用一句话介绍你自己"}]

response = client.messages.create(
    model=MODEL,
    system=SYSTEM,
    messages=messages,
    max_tokens=8000,
)

print("stop_reason:", response.stop_reason)
for block in response.content:
    print("type:", block.type)
    if block.type == "text":
        print("text:", block.text)
```

运行后应该看到类似：

```text
stop_reason: end_turn
type: text
text: 我是一个编程助手……
```

### 5.1 这段代码在验证什么

- `.env` 能读到；
- Key 和 `base_url` 正确；
- 模型能返回文本；
- 你能正确访问 `response.content` 里的 block。

### 5.2 两个容易踩的坑

**坑 1：把 block 当字典用。**

```python
block["type"]   # ❌ 报错：'TextBlock' object is not subscriptable
block.type      # ✅ SDK 返回的是对象，用属性访问
```

**坑 2：以为 `response.content` 是字符串。**

它是 block 列表。要拿文本，必须遍历并判断 `block.type == "text"`。

### ✅ 检查点 2

- [ ] 打印出了 `stop_reason: end_turn`
- [ ] 打印出了至少一个 `type: text`
- [ ] 没有出现 `tool_use`（因为这次请求根本没传 `tools`）

> 到这里先停一下。确认上面全部通过，再继续。不要带着配置错误往下写。

---

## 6. 第 2 步：告诉模型“你有一个 bash 工具”

现在加上工具定义。工具不是 Python 函数，而是一段**给模型看的说明书**：

```python
TOOLS = [{
    "name": "bash",
    "description": "Run a shell command in the current working directory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to run.",
            },
        },
        "required": ["command"],
    },
}]
```

三个字段分别是什么意思：

| 字段 | 作用 | 写不好会怎样 |
|---|---|---|
| `name` | 工具名；模型在 `tool_use.name` 里返回它 | 和你的执行逻辑对不上 |
| `description` | 告诉模型“这个工具能干什么” | 太模糊，模型可能不调用 |
| `input_schema` | 参数的 JSON Schema | 参数缺失或类型不对 |

`input_schema` 里：

- `type: "object"`：参数是一个对象；
- `properties.command.type: "string"`：有一个字符串字段 `command`；
- `required: ["command"]`：这个字段必填。

模型看到这份说明后，才知道“我可以申请执行一条 shell 命令，参数放在 `input.command` 里”。

### 6.1 做一次“只观察、不执行”的实验

把上一次的实验改成：

```python
messages = [
    {"role": "user", "content": "List the Python files in the current directory."}
]

response = client.messages.create(
    model=MODEL,
    system=SYSTEM,
    messages=messages,
    tools=TOOLS,          # ← 新增
    max_tokens=8000,
)

print("stop_reason:", response.stop_reason)
for block in response.content:
    print("—")
    print("type:", block.type)
    if block.type == "text":
        print("text:", block.text)
    elif block.type == "tool_use":
        print("id:", block.id)
        print("name:", block.name)
        print("input:", block.input)
```

你大概率会看到：

```text
stop_reason: tool_use
—
type: text
text: I'll list the Python files in the current directory.
—
type: tool_use
id: toolu_01...
name: bash
input: {'command': 'dir /b *.py'}
```

（Windows 上模型应该给 `dir`；如果它给了 `ls`，说明 system prompt 里的 cmd.exe 提示没生效，见第 12 节。）

### 6.2 这一实验最重要的结论

**模型没有执行任何东西。** `input` 里的命令只是模型“想让你执行”的参数。当前目录没有被读取，文件列表也不在响应里。

模型只是把“我要做什么”翻译成了结构化数据。执行权在你的 harness 手里。

### ✅ 检查点 3

- [ ] `stop_reason` 是 `tool_use`
- [ ] `response.content` 里能找到 `type: tool_use`
- [ ] 你能读出 `block.id`、`block.name`、`block.input["command"]`
- [ ] 你观察到：此时命令还没有被执行

---

## 7. 第 3 步：真正执行 bash 命令

现在写 `run_bash`。它的职责只有一句话：**接收命令字符串，返回可以回传给模型的文本结果**。

```python
def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(item in command for item in dangerous):
        return "Error: Dangerous command blocked"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=120,
        )
        output = (result.stdout + result.stderr).strip()
        return output[:50_000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as exc:
        return f"Error: {exc}"
```

### 7.1 每个参数为什么这么选

| 写法 | 原因 |
|---|---|
| `shell=True` | 允许模型写管道、重定向、复合命令，而不只是单个可执行文件 |
| `cwd=os.getcwd()` | 和 system prompt 里告诉模型的目录保持一致 |
| `capture_output=True` | 不让工具输出直接打到终端；由 harness 收集后回传给模型 |
| `text=True` | 返回 `str`，而不是 `bytes` |
| `errors="replace"` | Windows 中文输出可能不是 UTF-8，解码失败时替换而不是崩溃 |
| `timeout=120` | 防止模型跑一个永远不结束的命令 |
| `stdout + stderr` | 模型需要看到错误信息，才能纠正下一步 |
| `out[:50_000]` | 防止一次输出撑爆上下文 |
| 异常返回字符串 | **工具失败不应该让 harness 崩溃**；错误也是模型需要观察的结果 |
| `dangerous` 列表 | 最低限度护栏，不是安全边界；真正的权限控制在 s03 |

### 7.2 为什么错误要“返回”而不是“抛出”

如果 `run_bash` 直接抛异常，整个程序就退出了，模型永远没机会知道“刚才那条命令错了”。

把错误变成字符串返回，模型下一轮会看到：

```text
Error: 'foo' is not recognized as an internal or external command
```

然后它可能自己改成正确的命令。**把错误当作观察结果交还给模型**，这是 harness 设计里一个很重要的原则。

### 7.3 Windows 上特别注意

`shell=True` 在 Windows 上走的是 `COMSPEC`，通常是 `cmd.exe`，**不是 Git Bash**。所以：

- `dir`、`type`、`copy`、`findstr` 可用；
- `ls`、`cat`、`grep` 不一定可用；
- 模型如果按 Unix 习惯发命令，就会报“不是内部或外部命令”。

这就是为什么 `SYSTEM` 里要明确写：

> Windows: the bash tool runs through cmd.exe; use cmd.exe syntax, not Unix Bash or PowerShell syntax

工具名字叫 `bash` 只是沿用了课程命名；实际解释器由运行环境决定。

### 7.4 单独测试 `run_bash`

在写循环之前，先直接测试工具函数：

```python
if __name__ == "__main__":
    print(run_bash("dir" if os.name == "nt" else "ls"))
```

### ✅ 检查点 4

- [ ] 直接调用 `run_bash` 能看到当前目录内容
- [ ] 运行一个不存在的命令，返回的是 `Error: ...` 字符串，程序没有崩
- [ ] 运行 `timeout` 类命令不会让程序永久卡住（可选测试）

---

## 8. 第 4 步：完成一次“工具往返”（先不要写循环）

这是全章最关键的一步。先做**一次**完整的往返，不要急着包 `while True`。

一次往返包含 5 个动作：

1. 发请求；
2. 把 assistant 的这一轮追加进 `messages`；
3. 找出所有 `tool_use`；
4. 执行工具，构造 `tool_result`；
5. 把 `tool_result` 作为 user 消息追加，然后再请求一次。

### 8.1 动作 1：发请求

```python
response = client.messages.create(
    model=MODEL,
    system=SYSTEM,
    messages=messages,
    tools=TOOLS,
    max_tokens=8000,
)
```

### 8.2 动作 2：追加 assistant 消息

```python
messages.append({"role": "assistant", "content": response.content})
```

为什么必须追加？因为下一轮你要把 `tool_result` 发回去。API 要求：**每个 `tool_result` 前面，必须有一条包含对应 `tool_use` 的 assistant 消息**。如果不追加，模型在它的对话历史里看不到自己刚才发起过这个调用，API 会报错。

注意这里追加的是 `response.content`（block 列表），不是 `block.text`。文本只是 assistant 这一轮的一部分。

### 8.3 动作 3：找出所有 `tool_use`

```python
tool_calls = [
    block for block in response.content
    if block.type == "tool_use"
]
```

为什么要用列表？因为模型可能在一个响应里发出**多个** `tool_use` block。s01 只定义了 bash 一个工具，但模型仍然可能一次要求执行多条命令。你要全部执行，而不是只看第一个。

判断循环是否继续，也在这里：

```python
if not tool_calls:
    return
```

> 注意：`return` 只能写在函数里。第 8 节如果你把代码直接写在模块顶层做实验，先不要加这一行；等第 9 节包成 `agent_loop(messages)` 函数后再加。

### 8.4 动作 4：执行并构造结果

```python
results = []
for block in tool_calls:
    output = run_bash(block.input["command"])
    results.append({
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": output,
    })
```

逐字段对照协议：

| 字段 | 值 | 说明 |
|---|---|---|
| `type` | `"tool_result"` | 固定 |
| `tool_use_id` | `block.id` | 必须和调用方的 id 完全一致 |
| `content` | `output` | 工具返回的字符串 |

常见错误：

- 写成 `block.input` 而不是 `block.input["command"]`：`input` 是 dict，不是字符串；
- 写成 `block["id"]`：SDK 对象要用属性；
- 把 `tool_use_id` 写成 `block.name` 或自己编一个 id：配对失败；
- 只执行第一个 block：模型会缺少部分结果。

### 8.5 动作 5：追加结果，再请求一次

```python
messages.append({"role": "user", "content": results})

response = client.messages.create(
    model=MODEL,
    system=SYSTEM,
    messages=messages,
    tools=TOOLS,
    max_tokens=8000,
)
```

第二次请求时，模型看到的历史是：

```text
user:      List the Python files...
assistant: [text, tool_use(id=toolu_01...)]
user:      [tool_result(tool_use_id=toolu_01..., content="a.py\nb.py")]
```

于是它会基于真实结果生成下一次响应。这里有两种可能：

- 模型认为还需要工具 → 响应里再次出现 `tool_use`，你还要再执行一轮；
- 模型认为够了 → `stop_reason` 是 `end_turn`，`content` 里只有 `text`。

第一种可能正是第 9 节要写循环的原因：**你无法预先知道需要几轮，只能让模型自己决定。**

### 8.6 调试时打印一份可读的 `messages`

写循环之前，强烈建议加这个临时函数。它比 `print(messages)` 有用得多：

```python
def dump_messages(messages: list) -> None:
    for i, msg in enumerate(messages):
        content = msg["content"]
        if isinstance(content, str):
            print(i, msg["role"], "text:", content[:80])
        else:
            kinds = [
                getattr(block, "type", type(block).__name__)
                for block in content
            ]
            print(i, msg["role"], kinds)
```

调用一次后，你应该看到类似：

```text
0 user text: List the Python files...
1 assistant ['text', 'tool_use']
2 user ['tool_result']
```

第二次响应还没有追加。第 9 节的循环会在下一轮开头先追加它，再判断是否继续。

如果第 1 条就缺了 `tool_use`，或者第 2 条的 id 对不上，问题就很明显。

### ✅ 检查点 5

- [ ] 一次完整往返后，模型给出了基于真实命令输出的最终回答
- [ ] `dump_messages` 显示前三条是 `user → assistant → user`（把第二次响应也追加后，最后会多一条 assistant）
- [ ] 第 2 条 user 消息里是 `tool_result`，且 `tool_use_id` 与第 1 条 assistant 里的 `id` 一致
- [ ] 你能说清楚：为什么 assistant 消息必须在 tool_result 之前追加

---

## 9. 第 5 步：把一次往返包成 `while True`

现在把第 8 节的流程重复执行，直到模型不再调用工具。

### 9.1 循环算法

```text
while True:
    1. 发请求（带上完整 messages 和 tools）
    2. 把 assistant 的这一轮追加进 messages
    3. 收集所有 tool_use
    4. 如果没有 tool_use → return（模型说完了）
    5. 逐个执行工具，构造 results
    6. 把 results 作为 user 消息追加
    7. 回到 1
```

写成一个函数：

```python
def agent_loop(messages: list) -> None:
    while True:
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
        )

        # TODO 1: 把 assistant 这一轮追加进 messages

        # TODO 2: 收集 tool_use；如果没有就 return

        # TODO 3: 逐个执行工具，构造 results

        # TODO 4: 把 results 作为 user 消息追加，继续循环
```

### 9.2 四个 TODO 的验收标准

| TODO | 必须满足 | 常见错误 |
|---|---|---|
| 1 | `role="assistant"`，`content=response.content` | 只追加了文本；忘了追加 |
| 2 | 遍历 `response.content`，判断 `block.type == "tool_use"`；空列表就 `return` | 只看第一个 block；用 `stop_reason` 代替 |
| 3 | 对每个 block 调用 `run_bash(block.input["command"])`；结果字典包含 `type`、`tool_use_id`、`content` | id 写错；只执行一个；把异常抛出去 |
| 4 | `role="user"`，`content=results`（列表） | 写成 assistant；写成一个字符串 |

### 9.3 卡住时的最小提示

先自己写。如果 10 分钟还没写出来，再逐条对照：

- TODO 1：`messages.append({"role": "assistant", "content": response.content})`
- TODO 2：`tool_calls = [block for block in response.content if block.type == "tool_use"]`，然后 `if not tool_calls: return`
- TODO 3：`results = []`；`for block in tool_calls:`；`output = run_bash(block.input["command"])`；`results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})`
- TODO 4：`messages.append({"role": "user", "content": results})`

### 9.4 为什么用 `return` 而不是 `break`

`agent_loop` 的返回值是 `None`，它通过**原地修改 `messages`** 把对话留在外面。`return` 表示“这个函数的工作结束了”，调用方之后仍然能读到完整的 `messages`。

如果你用 `break`，要小心后续代码的执行位置；用 `return` 更不容易写错。

### 9.5 为什么不需要“任务完成”的判断

循环的停止条件是：**这一轮响应里没有 `tool_use`**。

也就是说，模型不再申请工具，就说明它认为自己已经可以给出最终回答了。你的代码不判断“文件是否创建成功”“测试是否通过”，这些判断都由模型完成。

这正是“Agency 来自模型，Harness 让 agency 落地”的含义。

### 9.6 可选：调试用的步数保护

最小实现不需要步数上限。但初学阶段，如果模型陷入“命令失败 → 重试 → 再失败”的死循环，程序会一直跑。

调试时可以临时加：

```python
for step in range(20):
    # 循环体
    ...
else:
    print("Stopped after 20 steps")
```

确认稳定后，再改回 `while True`。这不是 s01 的核心机制；s17 会讨论“谁来真正决定循环结束”。

### ✅ 检查点 6

- [ ] 一个需要多轮工具调用的任务能跑通（例如“创建文件再运行”）
- [ ] 模型不再调用工具时，函数正常返回
- [ ] 返回后，`messages` 的最后一条是 assistant 的最终文本
- [ ] 你能用 `dump_messages` 解释每一轮新增了什么

---

## 10. 第 6 步：写交互入口

最后加一个 `if __name__ == "__main__":`，让程序可以连续对话。

```python
if __name__ == "__main__":
    print("s01: Agent Loop")
    print("Enter a question, press Enter to send. Type q to quit.\n")

    history = []
    while True:
        try:
            query = input("s01 >> ")
        except (EOFError, KeyboardInterrupt):
            break

        if query.strip().lower() in ("q", "exit", ""):
            break

        history.append({"role": "user", "content": query})
        agent_loop(history)

        last_content = history[-1]["content"]
        if isinstance(last_content, list):
            for block in last_content:
                if getattr(block, "type", None) == "text":
                    print(block.text)
        print()
```

### 10.1 关键点

| 代码 | 为什么 |
|---|---|
| `history = []` 在 `while` 外面 | 多轮对话共享同一份历史；如果放在里面，每轮都会失忆 |
| `history.append(user)` | 每轮先追加用户输入，再进入 loop |
| `agent_loop(history)` | 原地修改；函数返回后 `history` 已经包含完整的工具往返 |
| `history[-1]["content"]` | loop 退出时，最后一条一定是 assistant 的最终回答 |
| `isinstance(last_content, list)` | assistant 的 content 是 block 列表 |
| `getattr(block, "type", None)` | 兼容不同类型的 block，避免属性不存在时报错 |
| `EOFError` / `KeyboardInterrupt` | Ctrl+D / Ctrl+C 时优雅退出 |

### 10.2 为什么最终文本在 `history[-1]`

因为 `agent_loop` 只有在“这一轮没有 `tool_use`”时才返回。而在返回之前，它已经把这一轮 assistant 消息追加进去了。所以最后一条就是模型的最终回答。

### 10.3 可选：把工具调用过程打印出来

调试时，在 `agent_loop` 执行工具的地方加两行：

```python
print(f"$ {block.input['command']}")
print(output[:500])
```

这样你能看到模型每一轮到底跑了什么。正式使用时可以去掉。

### ✅ 检查点 7

- [ ] 能连续问两个问题，且第二个问题能用上第一个问题的上下文
- [ ] 输入 `q`、`exit` 或空行能退出
- [ ] Ctrl+C 不会打印一大段 traceback

多轮记忆测试：

```text
s01 >> My name is Alice.
...
s01 >> What is my name?
...
```

如果第二个回答是 Alice，说明 `history` 在外面维护是对的。

---

## 11. 跑通验收：用真实任务测试

### 11.1 三个基础任务

默认在仓库根目录运行：

```sh
conda run --no-capture-output -n lcc-study python s01_agent_loop/code.py
```

（如果按第 3 节的安全提示在临时目录测试，把 `s01_agent_loop/code.py` 换成绝对路径即可；`.env` 仍会从仓库根目录读取。）

| Prompt | 期望行为 |
|---|---|
| `List all Python files in this directory` | 调用 bash；看到真实文件列表；给出总结 |
| `Create hello.py that prints "Hello, World!", then run it` | 至少两轮：写文件、运行文件；最终报告输出 |
| `What is the current git branch?` | 调用 `git branch --show-current` 或类似命令；返回分支名 |

### 11.2 一个正常的 trace 长什么样

用 `dump_messages` 观察，应该是这个形状（具体命令因模型而异）：

```text
0 user text: Create hello.py that prints "Hello, World!", then run it
1 assistant ['text', 'tool_use']
2 user ['tool_result']
3 assistant ['text', 'tool_use']
4 user ['tool_result']
5 assistant ['text']
```

观察重点：

- 第 1 轮：模型先写文件；
- 第 2 轮：模型看到写文件的结果，再运行；
- 第 3 轮：模型看到运行输出，给出最终回答；
- 每轮 `tool_result` 的 `tool_use_id` 都和上一轮 `tool_use.id` 对应。

### 11.3 故意制造一个错误

试试让它执行一个不存在的命令，比如：

```text
Run the command `definitely_not_a_real_command --help`
```

观察模型是否：

1. 收到 `Error: ...`；
2. 在下一轮调整命令或向你解释失败原因。

如果它直接崩溃，说明 `run_bash` 的异常处理没做好；如果它反复重试同一条错误命令，说明它没有利用错误信息，可以换一个更明确的 prompt 再试。

### ✅ 检查点 8（本章完成）

- [ ] 三个基础任务都能跑通
- [ ] 至少观察过一次多轮工具调用
- [ ] 至少观察过一次工具报错被模型处理
- [ ] 能用 `dump_messages` 解释任意一轮的 `messages` 结构

---

## 12. 调试手册

### 12.1 先按这个顺序排查

1. **配置层**：`.env` 读到了吗？Key、`base_url`、`MODEL_ID` 对吗？
2. **协议层**：请求里带 `tools` 了吗？`messages` 的角色顺序对吗？`tool_use_id` 对得上吗？
3. **执行层**：`run_bash` 单独调用能跑吗？命令在当前 shell 里合法吗？
4. **循环层**：是否在追加 assistant 之前就执行了工具？是否在空 `tool_calls` 时没有退出？

### 12.2 常见报错对照表

| 现象 | 最可能的原因 | 怎么修 |
|---|---|---|
| `KeyError: 'DASHSCOPE_API_KEY'` | `.env` 没读到、变量名写错、仍是占位符 | 确认 `.env` 在仓库根目录；用 `ROOT / ".env"`；跑 `check_setup.py` |
| `AuthenticationError` / 401 | Key 错误、过期、前后有空格；用了别的平台的 Key | 重新复制百炼 Key；确认 `base_url` 是百炼兼容端点 |
| `NotFoundError` / model not found | `MODEL_ID` 与控制台不一致 | 以百炼控制台为准；检查 `.env` |
| 400 `tool_use ids were found without tool_result blocks` | 没追加 assistant、id 对不上、结果没紧跟调用 | 用 `dump_messages` 检查角色顺序和 id |
| 模型只聊天、不调工具 | 忘了 `tools=TOOLS`、description 太模糊、模型认为不需要工具 | 检查请求参数；把工具描述写具体；换一个必须操作文件的 prompt |
| `stop_reason == "max_tokens"` | 输出被截断，`tool_use` 的 JSON 可能不完整 | 增大 `max_tokens`，或把任务拆小 |
| 循环停不下来 | 工具总报错/输出为空，模型反复重试；命令在等待输入 | 打印每轮命令和输出；临时加最大步数；避免交互式命令 |
| Windows 报 `'ls' is not recognized` | `shell=True` 用 cmd.exe，模型却发了 Unix 命令 | 在 `SYSTEM` 里明确 cmd.exe；或让模型改用 `dir` / `type` |
| 中文乱码 / `UnicodeDecodeError` | Windows 控制台 GBK；subprocess 解码失败 | `errors="replace"`；`conda run --no-capture-output`；终端切 UTF-8 |
| `'ToolUseBlock' object is not subscriptable` | 把 SDK block 当 dict | 用 `block.type` / `block.input` / `block.id` |
| `json.dumps(messages)` 报错 | `messages` 里有 SDK 对象 | 不要直接序列化；调试时只打印 role 和 block 类型 |
| 工具输出太长 / 上下文爆炸 | 命令输出了整个大文件/目录 | `out[:50_000]`；prompt 要求只输出必要信息；s08 会系统解决 |
| 命令卡住 120 秒 | 交互式命令、网络命令、等待输入 | 避免 `vim` / `more` / `pause`；`timeout` 会把错误返回给模型 |

### 12.3 重点问题展开

#### 问题 A：400，`tool_use` 和 `tool_result` 配不上

先打印：

```python
dump_messages(messages)
```

正确的形状必须是：

```text
assistant ['tool_use']
user      ['tool_result']   # tool_use_id == 上一条的 id
```

错误的形状通常有：

```text
user      ['tool_result']   # 前面没有 assistant tool_use
assistant ['tool_use']
assistant ['tool_result']   # 角色写错
user      ['tool_result']   # id 不匹配
```

修复顺序：

1. 确认 `messages.append({"role": "assistant", "content": response.content})` 在构造结果之前；
2. 确认 `tool_use_id` 用的是 `block.id`；
3. 确认所有结果都在**同一条** user 消息里，而不是每条结果单独发一条（s01 的写法是一起发）。

#### 问题 B：模型不调用工具

按这个顺序查：

1. 请求里有没有 `tools=TOOLS`？
2. `TOOLS` 是不是空列表，或者 schema 写错了？
3. `description` 是否清楚说明“可以执行 shell 命令”？
4. Prompt 是否是一个必须动手才能完成的任务？问“Python 是什么”这种知识题，模型不需要工具。
5. `stop_reason` 是什么？如果是 `max_tokens`，响应可能被截断了。

#### 问题 C：Windows 上模型一直发 Unix 命令

`shell=True` 不会自动给你一个 Unix shell。它用的是 `cmd.exe`。所以：

- `SYSTEM` 必须明确写“cmd.exe, not Bash/PowerShell”；
- 如果模型仍然发 `ls`，可以在 `SYSTEM` 里加一句“For listing files use `dir`”；
- 不要为了省事去装一个假的 `ls`，先让模型理解环境。

#### 问题 D：无限循环

典型原因是工具返回了模型无法利用的结果：

- 命令一直失败，但错误信息不清晰；
- 命令输出 `(no output)`，模型以为没执行；
- 命令等待输入（比如 `more`、`pause`、交互式 Python）。

调试方法：

1. 打印每轮的 `command` 和 `output[:500]`；
2. 临时加 `for step in range(10)`；
3. 看模型是在重复同一条命令，还是在换着试；
4. 如果是重复同一条，考虑在 `SYSTEM` 里加“If a command fails, read the error and change your approach.”

### 12.4 调试时不要做的事

- 不要把完整 API Key 打印出来；
- 不要把整个 `messages` 直接 `print`（SDK 对象很难读）；
- 不要一上来就怀疑模型；先检查请求参数和消息角色；
- 不要同时改三个地方。每次只改一个变量，再运行。

---

## 13. 写完之后：对照、笔记、下一步

### 13.1 和参考实现对照

```sh
diff s01_agent_loop/code.py ../learn-claude-code-main/s01_agent_loop/code.py
```

差异是正常的。重点看这些地方：

| 对照点 | 你的实现 | 参考实现 |
|---|---|---|
| 客户端初始化 | 显式 `api_key` + `base_url` | 依赖环境变量和 `ANTHROPIC_BASE_URL` |
| `.env` 读取 | `ROOT / ".env"` | `load_dotenv(override=True)` 依赖 cwd |
| 工具执行 | `run_bash` | 基本一致 |
| 循环 | `while True` + `tool_use` 判断 | 基本一致 |
| 交互入口 | `input()` + `history` | 额外有 readline 修复和颜色输出 |
| 危险命令 | 简化 blocklist | 类似 |

> 注意：参考实现里的 `Anthropic(base_url=...)` 依赖 `ANTHROPIC_API_KEY`，而本仓库不配置这个变量。你的显式 `api_key` + `base_url` 写法才是对的，不要为了“和参考一致”改回去。

**不要因为“和参考不一样”就改。** 先问：哪种更适合你的运行环境？为什么？

### 13.2 在 NOTES.md 里回答三个问题

1. `messages` 列表在循环中如何增长？每一轮的角色分别是什么？
2. 模型凭什么知道该调用工具、以及什么时候停止？
3. 为什么说“循环是 agent 的，机制是 harness 的”？

用你自己的话写。写不出来，说明还没真正理解，回去用 `dump_messages` 再跑一遍。

### 13.3 记录踩坑

在 `NOTES.md` 的“踩坑与疑问”里记：

- 你遇到的第一条报错原文；
- 你怎么定位的；
- 修复后你学到了什么。

这比抄一遍正确代码有价值得多。

### 13.4 下一章预告

s01 只有 bash 一个工具。读文件要 `cat`/`type`，写文件要 `echo >`，找文件要 `find`/`dir /s`，又丑又容易出错。

s02 会加入多个真正的工具（读、写、编辑、glob、grep），并引入 **dispatch map**：

```python
TOOL_HANDLERS = {
    "bash": run_bash,
    "read_file": read_file,
    "write_file": write_file,
}
```

关键问题是：**工具从 1 个变成 N 个，`agent_loop` 需要改吗？**

如果你写对了 s01，答案应该是：几乎不用改。这就是这一章的意义。

---

## 附录 A：代码结构自检

写完后，对照这张表检查文件结构：

| 部分 | 应该有什么 | 检查 |
|---|---|---|
| 配置 | `ROOT`、`load_dotenv`、`client`、`MODEL` | [ ] |
| System Prompt | `ENVIRONMENT_PROMPT`、`SYSTEM` | [ ] |
| 工具定义 | `TOOLS`，包含 `name` / `description` / `input_schema` | [ ] |
| 工具执行 | `run_bash`，处理成功、错误、超时、空输出 | [ ] |
| 核心循环 | `agent_loop(messages)`，每轮追加 assistant + tool_result | [ ] |
| 交互入口 | `if __name__ == "__main__":`，维护 `history` | [ ] |
| 调试辅助 | 可选：`dump_messages`、命令打印 | [ ] |

## 附录 B：本章术语速查

| 术语 | 一句话解释 |
|---|---|
| Agent Loop | `messages → LLM → tool_use → 执行工具 → tool_result → 回到 LLM` 的循环 |
| Harness | 围绕模型的一切：工具、提示、执行、权限、观察接口 |
| `tool_use` | 模型返回的结构化工具调用块，包含 `id`、`name`、`input` |
| `tool_result` | 工具执行结果，用 `tool_use_id` 与调用配对，放在 user 消息里 |
| `stop_reason` | 模型为什么停止生成；`tool_use` 表示要调工具，`end_turn` 表示说完了 |
| 无状态请求 | 每次 `messages.create` 都是新请求，模型不保存上次的对话 |
| System Prompt | 每次请求都带的全局指令，不属于 `messages` |

## 附录 C：最小实现的功能边界

s01 故意不做这些事，留到后面章节：

| 没做的事 | 留到 |
|---|---|
| 权限判断（哪些命令能跑） | s03 |
| PreToolUse / PostToolUse 扩展点 | s04 |
| 多工具注册与 dispatch | s02 |
| 上下文压缩 | s08 |
| 任务计划（Todo） | s05 |
| 子 agent | s06 |
| 跨会话记忆 | s09 |
| 真正的安全沙箱 | s03 及之后 |

在 s01 阶段，不要提前实现这些。先把“一个循环 + 一个工具”跑通，理解每一轮 `messages` 的变化。

---

> 写完并跑通后，回到 [NOTES.md](./NOTES.md) 更新“实现记录”和“与参考实现的差异”。
>
> 记住这一章的一句话：**模型决定下一步，循环负责把下一步变成现实。**