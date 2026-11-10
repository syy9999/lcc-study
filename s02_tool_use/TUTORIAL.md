# s02 手把手：从 1 个工具到 5 个工具

> 配套阅读：[README.md](./README.md)（原理）· [NOTES.md](./NOTES.md)（笔记）· 参考实现：`../learn-claude-code-main/s02_tool_use/code.py`
>
> 前置条件：s01 的 `agent_loop` 已经跑通。
>
> README 讲的是“结果”：5 个工具 + 一张分发表。这份教程补的是“过程”：**三个注册点怎么对齐**、**一轮多个 `tool_use` 的协议长什么样**、**每写完一个工具怎么单独验证**。
>
> 建议分 4～5 次写完。每通过一个“检查点”再往下走。

---

## 0. 最终你会得到什么

一个单文件程序 `s02_tool_use/code.py`。它和 s01 用同样的循环，但模型现在有 5 个工具可用：

| 工具 | 作用 |
|---|---|
| `bash` | 执行 shell 命令（保留 s01 的能力） |
| `read_file` | 读文本文件，可限制行数 |
| `write_file` | 写文件，自动创建父目录 |
| `edit_file` | 把文件里第一处精确匹配的文本替换掉 |
| `glob` | 按模式查找文件，`**` 支持递归 |

一次典型交互（示意）：

```text
s02 >> Read README.md and requirements.txt, then create summary.md with a short summary.

> read_file
# lcc-study
...
> read_file
anthropic==0.69.0
...
> write_file
Wrote 286 bytes to summary.md

Done. I read both files and wrote a summary to summary.md.
```

文件按这个顺序写：

| 部分 | 作用 | 学习价值 |
|---|---|---|
| 1. 配置 + `WORKDIR` | 读取 `.env`，确定工作目录 | 低 |
| 2. System Prompt | 告诉模型优先用专用文件工具 | 中 |
| 3. `safe_path` | 把文件工具限制在工作目录内 | 高 |
| 4. 四个 handler | 读、写、编辑、glob 的具体实现 | 高 |
| 5. `TOOLS` | 用 JSON Schema 向模型描述 5 个工具 | 中 |
| 6. `TOOL_HANDLERS` | 工具名 → 处理函数的 dispatch map | **高** |
| 7. `agent_loop` | 只改工具执行那一行 | 中 |
| 8. 交互入口 | 维护多轮对话 | 低 |

一句话概括这一章：

> **加一个工具，只加一个 handler；循环不用动。**

---

## 1. 先看清：这章真正变的是什么

### 1.1 s01 的循环里藏着一个硬编码

s01 的工具执行只有这一行：

```python
output = run_bash(block.input["command"])
```

它能工作，是因为循环**预先知道**只有 bash 一个工具：参数叫什么、该调用谁，都写死了。

现在要加 `read_file`。最直接的想法是：

```python
if block.name == "bash":
    output = run_bash(block.input["command"])
elif block.name == "read_file":
    output = run_read(block.input["path"], block.input.get("limit"))
elif block.name == "write_file":
    ...
```

能跑，但问题很明显：

- 每加一个工具，都要改核心循环；
- 循环里堆满“某个工具的参数长什么样”的细节；
- 循环和工具集耦合，工具越多越难维护。

这正好违背了 s01 得到的分工：**循环只管调度，工具只管执行**。

### 1.2 把“执行”抽象成查表

s02 的做法是引入一张表：

```python
TOOL_HANDLERS = {
    "bash": run_bash,
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "glob": run_glob,
}
```

循环里不再出现任何具体工具的名字：

```python
handler = TOOL_HANDLERS.get(block.name)
output = handler(**block.input)
```

这就是 **dispatch map（分发映射）**：用数据（字典）表达“工具名 → 处理函数”的关系，而不是用控制流（`if/elif`）表达。

加一个工具时，循环一个字都不用改。这就是本章标题“加一个工具，只加一个 handler”的含义。

### 1.3 三个注册点，必须对齐

这是本章最容易出错、也最值得记住的地方。一个工具同时存在于三个地方：

| 位置 | 给谁看 | 作用 |
|---|---|---|
| handler 函数 | Python / harness | 真正干活 |
| `TOOLS` 里的 schema | **模型** | 告诉模型“有这个工具、参数是什么” |
| `TOOL_HANDLERS` 里的映射 | **harness** | 把模型返回的 `block.name` 变成函数调用 |

它们之间靠两个**字符串/名称**连接：

```text
TOOLS[i].name  ──────────────►  TOOL_HANDLERS 的 key
                                        │
                                        ▼
TOOLS[i].input_schema.properties  ◄──►  handler 的参数名
```

记住这张图。后面 90% 的“工具调不通”，都是这三个地方没有对齐：

- schema 里叫 `file_path`，handler 参数叫 `path` → `TypeError`；
- `TOOLS` 里有 `grep`，`TOOL_HANDLERS` 里没有 → 模型调用后查不到；
- `TOOL_HANDLERS` 有 `grep`，`TOOLS` 里没有 → 模型根本不知道能调。

---

## 2. 协议细节：一轮多个工具调用

s01 已经讲过单个 `tool_use` / `tool_result` 的配对。s02 多了 5 个工具，协议上真正的新东西是：**模型可以在一轮里申请多个工具**。

### 2.1 请求没有新字段

请求的形状和 s01 完全一样，只是 `tools` 列表变长了：

```json
{
  "model": "deepseek-v4.1-flash-1017",
  "system": "You are a coding agent at ...",
  "messages": [{"role": "user", "content": "Read README.md and requirements.txt"}],
  "tools": [
    {"name": "bash", "description": "...", "input_schema": {...}},
    {"name": "read_file", "description": "...", "input_schema": {...}},
    {"name": "write_file", "description": "...", "input_schema": {...}},
    {"name": "edit_file", "description": "...", "input_schema": {...}},
    {"name": "glob", "description": "...", "input_schema": {...}}
  ],
  "max_tokens": 8000
}
```

模型能看到全部 5 个工具，并自己决定这一轮用哪几个、用几次。

### 2.2 响应里可能有多个 `tool_use`

比如用户说“读 README.md 和 requirements.txt”：

```json
{
  "role": "assistant",
  "content": [
    {"type": "text", "text": "I'll read both files."},
    {
      "type": "tool_use",
      "id": "toolu_01AAA...",
      "name": "read_file",
      "input": {"path": "README.md"}
    },
    {
      "type": "tool_use",
      "id": "toolu_01BBB...",
      "name": "read_file",
      "input": {"path": "requirements.txt"}
    }
  ],
  "stop_reason": "tool_use"
}
```

要点：

- 两个 `tool_use` 在**同一条 assistant 消息**里；
- 每个都有自己独立的 `id`；
- 它们的顺序就是 `response.content` 里的顺序；
- 此时两个文件都**还没有被读取**。

### 2.3 所有结果放在同一条 user 消息里

执行完两个工具后，要追加**一条** user 消息：

```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01AAA...",
      "content": "# lcc-study\n..."
    },
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01BBB...",
      "content": "anthropic==0.69.0\n..."
    }
  ]
}
```

配对关系：

```text
assistant: tool_use(id="toolu_01AAA", name="read_file", input={"path": "README.md"})
                                │
                                │ 同一个 id
                                ▼
user:      tool_result(tool_use_id="toolu_01AAA", content="# lcc-study...")

assistant: tool_use(id="toolu_01BBB", name="read_file", input={"path": "requirements.txt"})
                                │
                                │ 同一个 id
                                ▼
user:      tool_result(tool_use_id="toolu_01BBB", content="anthropic==...")
```

三条规则：

1. **每个 `tool_use` 都必须有一条对应的 `tool_result`**，不能漏。即使工具执行失败，也要返回一条 `Error: ...` 的结果。
2. 结果放在**同一条** user 消息里，而不是每个结果发一条消息。
3. 配对靠 `tool_use_id`，不靠顺序；但建议按原始顺序排列，方便人看。

### 2.4 未知工具、错误参数，也都要返回结果

模型可能“幻觉”出一个不存在的工具名，或者把 `limit` 写成字符串。harness 不能因此崩溃，也不能跳过这条调用不发结果——否则下一轮 API 会因为“有 `tool_use` 没有 `tool_result`”直接 400。

统一处理方式：**把错误变成结果字符串，交还给模型**。

```python
handler = TOOL_HANDLERS.get(block.name)
if handler is None:
    output = f"Unknown tool: {block.name}"
else:
    try:
        output = handler(**block.input)
    except Exception as exc:
        output = f"Error: {type(exc).__name__}: {exc}"
```

模型看到 `Unknown tool` 或 `Error: ...` 后，下一轮可能自己改正。这和 s01 里“`run_bash` 把错误转成字符串”是同一个原则。

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

> **安全提示**：本章的文件工具用 `safe_path` 限制在工作目录内，但 `bash` 不受这个限制。也就是说，`safe_path` 只保护 `read_file` / `write_file` / `edit_file` / `glob`，模型仍然可以通过 bash 读写工作目录之外的文件。真正统一的权限控制在 s03。第一次测试建议在临时目录或本仓库内进行。

### ✅ 检查点 0

- [ ] `check_setup.py` 全部通过
- [ ] 你知道 `.env` 在仓库根目录
- [ ] 你理解 `safe_path` 不是完整的安全边界

---

## 4. 先搭好配置和 `WORKDIR`

打开 `s02_tool_use/code.py`，保留文件头的 docstring，在下面写配置。**这一步不写任何工具。**

```python
import glob as g
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

# 工作目录 = 启动程序时所在的目录。
# 文件工具和 bash 都以它为根；safe_path 也以它为边界。
WORKDIR = Path.cwd().resolve()
```

逐行解释：

| 代码 | 为什么这么写 |
|---|---|
| `ROOT / ".env"` | 配置始终从仓库根目录读取，和运行位置无关 |
| `Anthropic(api_key=..., base_url=...)` | 显式传参，不使用 `ANTHROPIC_*` 环境变量；这是本仓库的约定 |
| `os.environ[...]` | 缺失时立刻报错，比 `os.getenv` 返回 `None` 更早暴露问题 |
| `WorkDIR = Path.cwd().resolve()` | `.resolve()` 把符号链接、`..` 规范掉，后面 `safe_path` 的比较才可靠 |

### 4.1 更新 `SYSTEM` 和 `run_bash`

s01 的 system prompt 只说“用 bash 解决任务”。现在有了专用文件工具，要明确告诉模型**优先用它们**，否则模型很可能继续用 `type` / `cat` 绕过 `safe_path`：

```python
ENVIRONMENT_PROMPT = (
    "Windows: the bash tool runs through cmd.exe; use cmd.exe syntax, "
    "not Unix Bash or PowerShell syntax"
    if os.name == "nt"
    else "Unix-like: the bash tool runs the system shell"
)

SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    f"Environment: {ENVIRONMENT_PROMPT}. "
    "Prefer read_file / write_file / edit_file / glob over bash for file operations. "
    "Use tools to solve tasks. Act, don't explain."
)
```

`run_bash` 从 s01 原样搬过来，只把 `cwd=os.getcwd()` 改成 `cwd=WORKDIR`，保证 bash 和文件工具看到的是同一个目录：

```python
def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(item in command for item in dangerous):
        return "Error: Dangerous command blocked"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKDIR,
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

### ✅ 检查点 1

在文件末尾临时加：

```python
if __name__ == "__main__":
    print("WORKDIR =", WORKDIR)
    print("MODEL   =", MODEL)
    print(run_bash("dir" if os.name == "nt" else "ls"))
```

运行：

```sh
conda run --no-capture-output -n lcc-study python s02_tool_use/code.py
```

- [ ] 打印出的 `WORKDIR` 是你启动命令时所在的目录
- [ ] `run_bash` 能看到目录内容
- [ ] 配置没有报 `KeyError`

确认后把这段临时入口删掉，后面会换成正式的。

---

## 5. 第 1 步：写 `safe_path`

文件工具接收的是模型给的路径。模型可能给：

- `README.md`（正常）
- `a/../README.md`（正常，规范化后仍在工作目录内）
- `../README.md`（越界）
- `C:\Windows\System32\drivers\etc\hosts`（越界）
- `subdir/../../../etc/passwd`（越界）

`safe_path` 的职责只有一句话：**把路径解析到 `WORKDIR` 内；如果解析后跑到外面，就报错。**

```python
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path
```

逐行解释：

| 代码 | 作用 |
|---|---|
| `WORKDIR / p` | 相对路径拼到工作目录下；如果 `p` 是绝对路径，`pathlib` 会直接用它 |
| `.resolve()` | 消掉 `.`、`..`，并把符号链接/junction 解析到真实路径 |
| `.is_relative_to(WORKDIR)` | 判断解析后的路径是否仍在工作目录内（Python 3.9+） |
| `raise ValueError` | 越界是“模型给错了参数”，不是 harness 崩溃；由上层 handler 捕获后转成字符串 |

### 5.1 为什么必须 `resolve()`

只做字符串前缀判断是不够的：

```python
str((WORKDIR / "../secret.txt"))  # E:\...\lcc-study\..\secret.txt
```

它看起来以 `WORKDIR` 开头，但实际上已经跑出去了。`resolve()` 会把它变成真实的 `E:\...\secret.txt`，再做比较。

### 5.2 为什么 `raise` 而不是直接返回错误字符串

分工是：

- `safe_path` 负责**判断**；
- 每个 handler 负责**把判断失败转成模型能读到的 `tool_result`**。

如果 `safe_path` 直接返回字符串，它的返回类型就变成 `Path | str`，调用方每次都要判断，很啰嗦。让 `safe_path` 抛异常、在 handler 的 `try` 里统一捕获，代码更干净。

### 5.3 单独测试

```python
if __name__ == "__main__":
    print(safe_path("README.md"))
    print(safe_path("a/../README.md"))
    try:
        safe_path("../README.md")
    except ValueError as exc:
        print("blocked:", exc)
```

### ✅ 检查点 2

- [ ] `safe_path("README.md")` 返回绝对路径
- [ ] `safe_path("a/../README.md")` 仍然在 `WORKDIR` 内
- [ ] `safe_path("../README.md")` 抛出 `ValueError`
- [ ] 你能说清楚：为什么 `resolve()` 不能省

---

## 6. 第 2 步：四个 handler，一个一个写

每个 handler 都遵守同一套约定：

1. 参数名和 schema 的 `properties` 一致；
2. 成功返回**短小、信息明确**的字符串；
3. 失败返回 `Error: ...` 字符串，不抛出到循环外；
4. 输出有上限，避免撑爆上下文。

### 6.1 `run_read`

```python
def run_read(path: str, limit: int | None = None) -> str:
    try:
        lines = safe_path(path).read_text(encoding="utf-8").splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)
    except Exception as exc:
        return f"Error: {exc}"
```

要点：

| 细节 | 为什么 |
|---|---|
| `safe_path(path)` | 所有文件工具的第一步，防止越界 |
| `encoding="utf-8"` | 显式编码，避免平台默认编码不一致 |
| `splitlines()` | 同时处理 `\n`、`\r\n`；返回不带换行符的行列表 |
| `limit` 可选 | 模型可以只读前 N 行，避免大文件撑爆上下文 |
| 截断时加 `... (N more lines)` | **不要静默截断**，要让模型知道还有内容 |
| `except Exception` | 文件不存在、编码错误、权限错误都变成 `Error: ...` |

测试：

```python
if __name__ == "__main__":
    print(run_read("PROGRESS.md", limit=5))
    print("---")
    print(run_read("does_not_exist.txt"))
```

期望：第一段只显示 5 行，并带 `... (N more lines)`；第二个返回 `Error: ...` 而不是崩溃。

> 思考题：空文件会返回空字符串 `""`。模型可能误以为“读取失败”或“没有输出”。要不要改成 `(empty file)`？先自己决定，并记录在 NOTES 里。

### 6.2 `run_write`

```python
def run_write(path: str, content: str) -> str:
    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Wrote {file_path.stat().st_size} bytes to {path}"
    except Exception as exc:
        return f"Error: {exc}"
```

要点：

| 细节 | 为什么 |
|---|---|
| `parent.mkdir(parents=True, exist_ok=True)` | 模型可能写 `notes/day1/a.md`，父目录不存在时自动创建 |
| `write_text(..., encoding="utf-8")` | 显式编码，避免 Windows 默认 GBK |
| 返回 `Wrote N bytes ...` | 给模型一个明确的成功信号，它才知道下一步可以读/运行 |
| `stat().st_size` | 真正的字节数；`len(content)` 是字符数，中文时两者不同 |

测试：

```python
if __name__ == "__main__":
    print(run_write("tmp/s02_demo.txt", "hello\nworld\n"))
    print(run_read("tmp/s02_demo.txt"))
```

期望先看到 `Wrote ... bytes`，再看到文件内容。测试完可以把 `tmp/` 删掉。

> 注意：`write_file` 会**整文件覆盖**。模型如果只想改一行，应该用 `edit_file`，否则容易把原文件内容冲掉。这一点可以写进工具描述，也可以在 prompt 里提醒。

### 6.3 `run_edit`

```python
def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        file_path = safe_path(path)
        text = file_path.read_text(encoding="utf-8")
        if old_text not in text:
            return f"Error: text not found in {path}"
        file_path.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {path}"
    except Exception as exc:
        return f"Error: {exc}"
```

要点：

| 细节 | 为什么 |
|---|---|
| 先读全文，再判断 `old_text in text` | 找不到时**不要写文件**，避免把文件改坏 |
| `text.replace(old_text, new_text, 1)` | 只替换第一处；`1` 很重要，否则会全局替换 |
| 返回 `Error: text not found` | 让模型知道“不是文件不存在，而是要找的文本不存在” |
| 精确匹配 | 空白、缩进、换行都必须一致；模型很容易在这上面翻车 |

常见失败原因：

1. **空白/缩进不一致**：文件里是 4 个空格，模型传了 tab；
2. **换行符不一致**：看起来一样，实际是 `\r\n` vs `\n`；
3. **文本不唯一**：`old_text` 在文件里出现多次，只替换了第一处，结果改错位置；
4. **文本太长**：模型凭记忆复制，漏了一个字符。

改进方向（先自己想，再动手）：

- 错误信息里附带“文件前 N 行”或“最接近的匹配”，帮助模型自我纠正；
- 要求 `old_text` 至少包含一行完整上下文，降低不唯一概率；
- 用 `\r\n` 归一化后再匹配。

测试：

```python
if __name__ == "__main__":
    print(run_write("tmp/s02_demo.txt", "hello\nworld\n"))
    print(run_edit("tmp/s02_demo.txt", "world", "s02"))
    print(run_read("tmp/s02_demo.txt"))
    print(run_edit("tmp/s02_demo.txt", "not-there", "x"))  # 应返回 Error
```

### 6.4 `run_glob`

```python
def run_glob(pattern: str) -> str:
    try:
        matches = sorted({
            match for match in g.glob(pattern, root_dir=WORKDIR, recursive=True)
            if (WORKDIR / match).resolve().is_relative_to(WORKDIR)
        })
        shown = matches[:200]
        if len(matches) > 200:
            shown.append("... (more matches omitted; narrow the pattern)")
        return "\n".join(shown) if shown else "(no matches)"
    except Exception as exc:
        return f"Error: {exc}"
```

要点：

| 细节 | 为什么 |
|---|---|
| `root_dir=WORKDIR` | 模式相对于工作目录解析，结果也是相对路径；不依赖进程当前目录 |
| `recursive=True` | 让 `**` 真正递归；不传的话 `**` 只是普通目录名 |
| `**/*.py` 用正斜杠 | 跨平台；在 glob 模式里反斜杠可能是转义字符 |
| `set` 去重 | 某些模式可能重复匹配同一个文件 |
| `sorted` | 输出稳定，方便模型和人对齐 |
| `(WORKDIR / match).resolve().is_relative_to(WORKDIR)` | 防止模式里的 `..` 或符号链接把结果带到工作目录外 |
| 最多 200 条 + 明确提示 | 防止一次匹配几万个文件撑爆上下文 |
| `(no matches)` | 明确告诉模型“确实没找到”，而不是空输出 |

Windows 特别说明：

- 用 `**/*.py`，不要用 `**\*.py`；
- `*.py` 只匹配当前目录，`**/*.py` 才递归；
- 默认不包含以 `.` 开头的隐藏文件/目录（如 `.git`）；
- 如果模型问“为什么没找到”，先检查它给的 pattern。

测试：

```python
if __name__ == "__main__":
    print(run_glob("**/*.py"))
    print("---")
    print(run_glob("**/*.md"))
```

### 6.5 可选：加第 6 个工具（验证本章的论点）

想验证“加工具不用改循环”，最好的方式是**真的加一个**。推荐加 `list_dir` 或 `grep`（二选一，先自己写，不要看参考实现）。

`list_dir` 的提示：

- 参数：`path: str = "."`；
- 用 `safe_path(path).iterdir()`；
- 输出目录在前、文件在后，各排序；每行带 `/` 后缀区分目录；
- 限制条目数（比如 200）。

`grep` 的提示：

- 参数：`pattern: str`、`path: str = "."`；
- 先用 `run_glob` 或 `rglob` 收集候选文件；
- 只读文本文件，跳过二进制和 `.git`；
- 输出 `文件:行号: 内容`，限制总条数；
- 正则用 `re.compile`，编译失败返回 `Error: ...`。

写完后只需要做两件事：在 `TOOLS` 加 schema，在 `TOOL_HANDLERS` 加一行。**如果 `agent_loop` 需要改动，说明你的 dispatch 设计有问题。**

### ✅ 检查点 3

- [ ] 每个 handler 都能单独调用成功
- [ ] 每个 handler 在输入错误时返回 `Error: ...`，程序不崩
- [ ] `run_read` 的 `limit` 生效，且有截断提示
- [ ] `run_edit` 找不到文本时不会改文件
- [ ] `run_glob` 能递归找到 `s02_tool_use` 下的 `.py` 文件
- [ ] （可选）你加了第 6 个工具，并且没有改 `agent_loop`

---

## 7. 第 3 步：写 `TOOLS`

`TOOLS` 是**写给模型看的说明书**。模型看不到 Python 函数，它只看到这里的 `name`、`description` 和 `input_schema`。

```python
TOOLS = [
    {
        "name": "bash",
        "description": (
            "Run a shell command. Prefer dedicated file tools "
            "for reading, writing, editing, and finding files."
        ),
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
    },
    {
        "name": "read_file",
        "description": (
            "Read a text file relative to the workspace. "
            "Use limit to read only the first N lines of a large file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to the workspace.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Optional maximum number of lines to return.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write text content to a file, creating parent directories as needed. "
            "This overwrites the whole file; use edit_file for small changes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to the workspace."},
                "content": {"type": "string", "description": "Full file content to write."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Replace the first exact occurrence of old_text with new_text in a file. "
            "old_text must match the file content exactly, including whitespace."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to the workspace."},
                "old_text": {"type": "string", "description": "Exact text to find."},
                "new_text": {"type": "string", "description": "Replacement text."},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "glob",
        "description": (
            "Find files by glob pattern relative to the workspace. "
            "Use ** for recursive matching and forward slashes in patterns."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern, e.g. **/*.py or notes/*.md.",
                },
            },
            "required": ["pattern"],
        },
    },
]
```

### 7.1 每个字段的作用

| 字段 | 作用 | 写不好会怎样 |
|---|---|---|
| `name` | 模型在 `tool_use.name` 里返回的字符串 | 和 `TOOL_HANDLERS` 的 key 对不上 |
| `description` | 模型判断“什么时候用这个工具”的依据 | 太模糊，模型不用或乱用 |
| `input_schema.type` | 固定 `"object"` | 参数结构不合法 |
| `properties` | 每个参数的名称和类型 | 和 handler 参数名对不上，调用报错 |
| `required` | 哪些参数必填 | 模型漏参数，handler 调用失败 |

### 7.2 必填 vs 可选

- `read_file` 的 `path` 必填，`limit` 可选；
- 可选参数不要放进 `required`；
- handler 里给可选参数一个默认值（`limit: int | None = None`），这样模型不传时也能调用。

### 7.3 schema 和 handler 的对应关系

| 工具 | schema 参数 | handler 签名 |
|---|---|---|
| `bash` | `command` | `run_bash(command: str)` |
| `read_file` | `path`, `limit?` | `run_read(path: str, limit: int \| None = None)` |
| `write_file` | `path`, `content` | `run_write(path: str, content: str)` |
| `edit_file` | `path`, `old_text`, `new_text` | `run_edit(path, old_text, new_text)` |
| `glob` | `pattern` | `run_glob(pattern: str)` |

这张表建议你自己在 NOTES 里抄一遍。它是本章最重要的“契约”。

### 7.4 写完后先做一次静态检查

在文件末尾临时加：

```python
if __name__ == "__main__":
    import inspect

    for tool in TOOLS:
        fn = TOOL_HANDLERS.get(tool["name"])
        if fn is None:
            print(f"[MISSING] {tool['name']}: no handler")
            continue

        params = set(inspect.signature(fn).parameters)
        props = set(tool["input_schema"]["properties"])
        required = set(tool["input_schema"].get("required", []))

        if not props <= params:
            print(f"[BAD] {tool['name']}: schema has unknown params {props - params}")
        if not required <= props:
            print(f"[BAD] {tool['name']}: required not in properties {required - props}")

        print(f"[OK] {tool['name']}: {sorted(props)}")
```

期望每个工具都打印 `[OK]`。这一步能在调用 API 之前抓出大部分拼写错误。

### ✅ 检查点 4

- [ ] `TOOLS` 里有 5 个工具（或 6 个，如果你加了练习）
- [ ] 每个工具的 `required` 都包含在 `properties` 里
- [ ] 每个 schema 的参数名都能在对应 handler 签名里找到
- [ ] 你理解 `description` 是写给模型看的，不是注释

---

## 8. 第 4 步：写 `TOOL_HANDLERS`

现在把工具名和函数连起来：

```python
TOOL_HANDLERS = {
    "bash": run_bash,
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "glob": run_glob,
}
```

三个容易犯的错：

| 错误写法 | 后果 |
|---|---|
| `"bash": run_bash()` | **导入时就执行**函数，字典里存的是返回值（通常是字符串） |
| key 写成 `"read"`，schema 里叫 `"read_file"` | 模型调用 `read_file` 时查不到 handler |
| 用 `TOOL_HANDLERS[block.name]` | 模型幻觉出不存在的工具时，`KeyError` 让程序崩溃 |

正确做法：**存函数对象（不加括号）**，**用 `.get()` 查表**。

### 8.1 `handler(**block.input)` 在做什么

模型返回的 `block.input` 是一个 dict：

```python
{"path": "README.md", "limit": 5}
```

`**` 把它展开成关键字参数：

```python
run_read(path="README.md", limit=5)
```

所以 **dict 的 key 必须和函数参数名完全一致**。这是三个注册点里的第三个约束。

### 8.2 参数绑定错误发生在函数体之前

这一点很关键：

```python
run_read(file_path="README.md")   # TypeError: unexpected keyword argument 'file_path'
```

这个 `TypeError` 在**进入 `run_read` 函数体之前**就抛出了。所以即使 `run_read` 内部有 `try/except`，也接不住它。

因此，保险的写法是在**调用点**再包一层：

```python
try:
    output = handler(**block.input)
except Exception as exc:
    output = f"Error: {type(exc).__name__}: {exc}"
```

参考实现没有这一层，因为它假设模型严格遵循 schema；但真实使用中模型偶尔会多给/少给参数，加这一层让 harness 更稳。

### ✅ 检查点 5

- [ ] `TOOL_HANDLERS` 的 key 集合和 `TOOLS` 的 name 集合完全一致
- [ ] 每个 value 都是函数对象，不是函数调用结果
- [ ] 用 `.get()` 而不是 `[]`
- [ ] 你能解释 `**block.input` 和参数名对齐的关系

---

## 9. 第 5 步：改循环里的一行

s01 的循环保留，唯一的变化在工具执行处：

```diff
- output = run_bash(block.input["command"])
+ handler = TOOL_HANDLERS.get(block.name)
+ output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
```

完整的 `agent_loop` 形状和 s01 一样。先自己写，四个 TODO：

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

        # TODO 2: 收集所有 tool_use；没有就 return

        # TODO 3: 逐个查表执行，构造 results
        #         注意：未知工具、参数错误、handler 异常都要变成 result 字符串

        # TODO 4: 把所有 results 作为一条 user 消息追加
```

### 9.1 四个 TODO 的验收标准

| TODO | 必须满足 | 常见错误 |
|---|---|---|
| 1 | `role="assistant"`，`content=response.content` | 只追加文本；忘了追加 |
| 2 | 遍历 `response.content`，判断 `block.type == "tool_use"`；空列表就 `return` | 只看第一个 block；用 `stop_reason` 代替 |
| 3 | 对每个 block 用 `TOOL_HANDLERS.get(block.name)`；结果包含 `type`、`tool_use_id`、`content` | 用 `[]` 查表导致崩溃；跳过失败的调用；只执行第一个 |
| 4 | `role="user"`，`content=results`（列表） | 每个结果单独发一条 user 消息；写成 assistant |

### 9.2 卡住时的最小提示

- TODO 1：`messages.append({"role": "assistant", "content": response.content})`
- TODO 2：`tool_calls = [b for b in response.content if b.type == "tool_use"]`，然后 `if not tool_calls: return`
- TODO 3：
  ```python
  handler = TOOL_HANDLERS.get(block.name)
  if handler is None:
      output = f"Unknown tool: {block.name}"
  else:
      try:
          output = handler(**block.input)
      except Exception as exc:
          output = f"Error: {type(exc).__name__}: {exc}"
  ```
- TODO 4：`messages.append({"role": "user", "content": results})`

### 9.3 完整形态（写完后对照）

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

        messages.append({"role": "assistant", "content": response.content})

        tool_calls = [
            block for block in response.content
            if block.type == "tool_use"
        ]
        if not tool_calls:
            return

        results = []
        for block in tool_calls:
            handler = TOOL_HANDLERS.get(block.name)
            print(f"> {block.name}")

            if handler is None:
                output = f"Unknown tool: {block.name}"
            else:
                try:
                    output = handler(**block.input)
                except Exception as exc:
                    output = f"Error: {type(exc).__name__}: {exc}"

            print(str(output)[:500])
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(output),
            })

        messages.append({"role": "user", "content": results})
```

### 9.4 为什么所有结果要在循环外追加

`results` 必须在**执行完所有 `tool_calls` 之后**统一 append。如果你在 for 循环里每执行一个就 append 一条 user 消息，会变成：

```text
assistant: [tool_use A, tool_use B]
user:      [tool_result A]
user:      [tool_result B]
```

这不符合协议要求的“一条 assistant 消息对应紧随其后的一条 user 结果消息”。正确形状是：

```text
assistant: [tool_use A, tool_use B]
user:      [tool_result A, tool_result B]
```

### 9.5 串行还是并发

本章选择**按 `response.content` 的顺序串行执行**。理由：

- 简单，结果顺序确定；
- 文件工具可能有依赖（先写后读），并发会引入竞态；
- 配对靠 `tool_use_id`，串行已经能保证正确。

并发是一个合理的后续优化，但前提是：**每个 `tool_use` 都必须产生一条结果，且 id 不能错**。先把串行写对，再考虑并发。

### ✅ 检查点 6

- [ ] 一个需要两次工具调用的任务能跑通
- [ ] `dump_messages` 里能看到 `assistant` 后紧跟一条 `user`，里面有多条 `tool_result`
- [ ] 每个 `tool_use_id` 都能和上一条 assistant 里的 `id` 对上
- [ ] 模型调用不存在的工具时，程序不崩溃，返回 `Unknown tool: ...`
- [ ] 你能说清楚：为什么改的只有一行

---

## 10. 第 6 步：写交互入口

和 s01 基本一样。可以把 s01 的 `dump_messages` 也搬过来，方便调试：

```python
if __name__ == "__main__":
    print("s02: Tool Use")
    print("Enter a question, press Enter to send. Type q to quit.\n")

    history = []
    while True:
        try:
            query = input("s02 >> ")
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

关键点和 s01 相同：

| 代码 | 为什么 |
|---|---|
| `history = []` 在 `while` 外面 | 多轮对话共享历史 |
| `agent_loop(history)` | 原地修改，返回后 `history` 已包含完整工具往返 |
| `history[-1]["content"]` | 循环退出时最后一条一定是 assistant 的最终回答 |
| `isinstance(last_content, list)` | assistant 的 content 是 block 列表 |
| `getattr(block, "type", None)` | 兼容不同类型的 block |

调试时可以在 `agent_loop` 的 `for` 循环里打印：

```python
print(f"> {block.name} {block.input}")
```

这样能看到模型每一轮传了什么参数。正式使用时可以只打印工具名和截断后的输出。

### ✅ 检查点 7

- [ ] 能连续问两个问题，第二个问题能用上第一个的上下文
- [ ] 输入 `q`、`exit` 或空行能退出
- [ ] Ctrl+C 不会打印一大段 traceback

---

## 11. 跑通验收：用真实任务测试

在仓库根目录运行：

```sh
conda run --no-capture-output -n lcc-study python s02_tool_use/code.py
```

### 11.1 四个基础任务

| Prompt | 期望行为 |
|---|---|
| `Read README.md and tell me what this project is about` | 调用 `read_file`，而不是 bash `type` |
| `Create test.py that prints "hello", then read it back` | 至少两轮：`write_file`、`read_file` |
| `Find all Python files in this directory` | 调用 `glob`，pattern 类似 `**/*.py` |
| `Read README.md and requirements.txt, then create summary.md` | 可能一轮内两次 `read_file`，再 `write_file` |

### 11.2 一个正常的 trace 长什么样

用 `dump_messages` 观察第 4 个任务，可能是：

```text
0 user text: Read README.md and requirements.txt, then create summary.md
1 assistant ['tool_use', 'tool_use']
2 user ['tool_result', 'tool_result']
3 assistant ['tool_use']
4 user ['tool_result']
5 assistant ['text']
```

观察重点：

- 第 1 轮模型一次申请了两个 `read_file`；
- 第 2 条 user 消息里有两条 `tool_result`，id 分别对应第 1 轮的两个 `tool_use`；
- 第 3 轮模型基于两个文件内容写 `summary.md`；
- 第 5 轮模型给出最终回答。

模型也可能选择“读一个、看结果、再读下一个”，trace 会多几轮。两种都正确。**关键不是轮数，而是配对和顺序。**

### 11.3 故意制造错误

依次试这些 prompt，观察模型是否能把错误当作观察结果：

| Prompt | 期望 |
|---|---|
| `Read the file does_not_exist.txt` | 返回 `Error: ...`；模型解释或换路径 |
| `In README.md, replace "this text does not exist" with "x"` | 返回 `Error: text not found`；模型先读文件再尝试 |
| `Find files matching no_such_pattern_*.xyz` | 返回 `(no matches)`；模型不会卡住 |
| `Read the file ../README.md` | 返回 `Path escapes workspace`；模型换回工作目录内的路径 |

最后一条要特别注意：**`safe_path` 只拦文件工具**。如果你换成：

```text
Run the command `type ..\README.md`
```

bash 仍然可以读到工作目录外的文件。这不是 bug，而是本章的边界，s03 会系统解决。

### 11.4 检查多工具配对的专项测试

让模型做：

```text
Read README.md and PROGRESS.md. Then tell me the first heading of each file.
```

然后看 trace：

```text
1 assistant ['tool_use', 'tool_use']
2 user ['tool_result', 'tool_result']
```

检查：

- 两个 `tool_use` 的 `id` 不同；
- 第 2 条 user 消息里有两个 `tool_result`；
- 每个 `tool_result.tool_use_id` 都能在上一条 assistant 里找到；
- 模型最终引用的内容确实来自两个文件，而不是编的。

### ✅ 检查点 8（本章完成）

- [ ] 四个基础任务都能跑通
- [ ] 至少观察到一次“一轮多个 `tool_use`”
- [ ] 至少观察到一次工具错误被模型处理
- [ ] 模型优先使用专用文件工具，而不是 bash
- [ ] 你能用 `dump_messages` 解释任意一轮的结构
- [ ] 你验证过 `safe_path` 能拦截 `../README.md`

---

## 12. 调试手册

### 12.1 按这个顺序排查

1. **schema 层**：`TOOLS` 里有这个工具吗？参数名和 handler 一致吗？`required` 写对了吗？
2. **dispatch 层**：`TOOL_HANDLERS` 有这个 key 吗？value 是函数对象吗？
3. **handler 层**：单独调用能跑吗？返回的是字符串吗？
4. **循环层**：assistant 消息追加了吗？所有 `tool_result` 在同一条 user 消息里吗？id 对吗？

### 12.2 常见报错对照表

| 现象 | 最可能的原因 | 怎么修 |
|---|---|---|
| `TypeError: run_read() got an unexpected keyword argument 'file_path'` | schema 属性名和 handler 参数名不一致 | 统一成一个名字；用 7.4 的静态检查 |
| `TypeError: run_edit() missing 1 required positional argument: 'new_text'` | 模型漏了必填参数，或 schema 的 `required` 没写全 | 检查 schema；调用点包 `try/except` |
| `TypeError: run_read() got an unexpected keyword argument 'encoding'` | 模型多给了 schema 里没有的参数 | 调用点包 `try/except`，把错误返回给模型 |
| `KeyError: 'grep'` | 用 `TOOL_HANDLERS[block.name]` 查表，模型调用了不存在的工具 | 改用 `.get()`，返回 `Unknown tool: ...` |
| `ValueError: Path escapes workspace: ../README.md` | `safe_path` 正常工作，路径越界 | 这是预期行为；让模型换工作目录内的路径 |
| `Error: text not found in README.md` | `old_text` 空白/换行/缩进不一致，或文本不存在 | 先 `read_file`，用更短、更唯一的锚点 |
| `Error: 'utf-8' codec can't decode byte ...` | 文件不是 UTF-8（二进制、GBK 等） | 确认是文本文件；后续可加编码回退 |
| `TypeError: '<' not supported between instances of 'str' and 'int'` | 模型把 `limit` 传成字符串 | schema 写 `integer`；handler 的 `try` 会捕获 |
| 400 `tool_use ids were found without tool_result blocks` | 漏了某个工具的结果；结果没放在一条 user 消息；id 写错 | 用 `dump_messages` 检查配对 |
| 模型一直用 bash `type` / `cat`，不用 `read_file` | system prompt 或工具描述不够明确 | 明确写“prefer dedicated file tools” |
| `glob` 返回 `(no matches)`，但文件存在 | 用了反斜杠模式、忘了 `recursive=True`、pattern 相对于错误的目录 | 用 `**/*.py`；确认 `WORKDIR` |
| 模型反复重试同一条失败命令 | 错误信息不清晰，模型不知道下一步 | 在错误信息里给上下文；prompt 要求失败后先读文件 |
| 程序在 `handler(**block.input)` 处崩溃 | 参数绑定错误，handler 内部的 `try` 接不住 | 在调用点包 `try/except` |
| 上下文突然变得很大 | `read_file` 读了大文件、`glob` 返回太多结果 | 用 `limit`；限制返回条数；s08 会系统解决 |

### 12.3 重点问题展开

#### 问题 A：三个注册点没对齐

这是本章最常见的错误。按这个顺序查：

1. `TOOLS` 里的 `name` 是 `read_file`；
2. `TOOL_HANDLERS` 里有没有 `"read_file"`；
3. `run_read` 的参数名是不是 `path`、`limit`；
4. schema 的 `properties` 是不是也是 `path`、`limit`。

四项里有任何一项不同，就会在某个环节失败。用 7.4 的脚本可以一次性检查前 3 项。

#### 问题 B：参数绑定错误发生在函数体外

```python
handler(**block.input)
```

如果 `block.input` 里有一个 handler 不认识的 key，Python 在**调用时**就抛 `TypeError`，不会进入函数体。所以：

- handler 内部的 `try/except` 只能捕获函数体里的错误；
- 参数绑定错误必须在调用点包 `try/except`。

#### 问题 C：`safe_path` 的误判

如果明明在工作目录内，却报 `Path escapes workspace`，检查：

1. `WORKDIR` 是不是 `Path.cwd().resolve()`；
2. 你是不是从另一个目录启动的（`WORKDIR` 会变）；
3. 路径里是否有符号链接/junction，`resolve()` 后指向了外面；
4. 是否传了绝对路径，而它确实在 `WORKDIR` 之外。

反过来，`safe_path` 不是完整的安全边界：

- 它只保护 4 个文件工具；
- bash 不受限制；
- 检查和实际读写之间有 TOCTOU 窗口（高级话题）；
- 真正的权限控制留到 s03。

#### 问题 D：`edit_file` 找不到文本

按这个顺序排查：

1. 先 `read_file` 看真实内容；
2. 检查缩进是空格还是 tab；
3. 检查换行符（`\r\n` vs `\n`）；
4. 缩短 `old_text`，只保留一个唯一锚点；
5. 确认这段文本只出现一次，否则可能改错位置。

`edit_file` 的语义是“精确匹配第一处”，不是“模糊替换”。模型如果给的是大意，不是原文，就会失败。这不是 bug，而是工具设计：**宁可失败，也不要改错**。

#### 问题 E：`glob` 在 Windows 上的坑

- 用正斜杠：`**/*.py`；
- 递归必须 `recursive=True`；
- `*.py` 只匹配当前目录；
- 隐藏文件和 `.git` 默认不返回；
- `root_dir=WORKDIR` 让结果相对于工作目录，不要再手动拼 `WORKDIR`；
- 结果太多时用更具体的 pattern，而不是加大上限。

#### 问题 F：一轮多个工具的结果配对

正确的结构只有一种：

```text
assistant: [tool_use A, tool_use B]
user:      [tool_result A, tool_result B]
```

错误的形态：

```text
assistant: [tool_use A, tool_use B]
user:      [tool_result A]        ← 缺 B，下一轮 400
```

```text
assistant: [tool_use A, tool_use B]
user:      [tool_result A]
user:      [tool_result B]        ← 拆成两条，不符合协议
```

```text
assistant: [tool_use A]
assistant: [tool_use B]           ← 模型不会这样返回；如果你手动拆了 assistant，就错了
```

记住：**一条 assistant 消息里的所有 `tool_use`，对应紧随其后的一条 user 消息里的所有 `tool_result`。**

#### 问题 G：工具报错不是程序错误

- 文件不存在、路径越界、文本没找到、参数类型不对：都是**模型需要看到的观察结果**，返回字符串；
- harness 自己的 bug（比如 `TOOL_HANDLERS` 少了 key、handler 返回了非字符串）：也要尽量不让循环崩溃，但要在终端打印出来；
- 不要把错误吞掉。模型看不到错误，就无法改正。

### 12.4 调试时不要做的事

- 不要把完整 API Key 打印出来；
- 不要直接 `print(messages)`（SDK 对象很难读），用 `dump_messages`；
- 不要同时改 schema、handler、循环三个地方；每次只改一个；
- 不要一看到模型不调工具就怀疑模型；先检查 `tools=TOOLS` 和工具描述；
- 不要为了“让模型能用”而放宽 `safe_path`；先理解它为什么拦截。

---

## 13. 写完之后：对照、笔记、下一步

### 13.1 和参考实现对照

```sh
diff s02_tool_use/code.py ../learn-claude-code-main/s02_tool_use/code.py
```

差异是正常的。重点看这些地方：

| 对照点 | 你的实现 | 参考实现 |
|---|---|---|
| 客户端初始化 | 显式 `api_key` + `base_url` | 依赖 `ANTHROPIC_BASE_URL` 环境变量 |
| `.env` 读取 | `ROOT / ".env"` 绝对路径 | `load_dotenv(override=True)` 依赖 cwd |
| `WORKDIR` | `Path.cwd().resolve()` | `Path.cwd()` |
| 工具执行 | `.get()` + 调用点 `try/except` | `.get()`，没有调用点 `try/except` |
| 循环 | 与 s01 一致 | 与 s01 一致 |
| 工具数量 | 5（或 6） | 5 |
| 终端输出 | 简单打印 | 带颜色和 readline 修复 |

> 注意：参考实现里的 `Anthropic(base_url=...)` 依赖 `ANTHROPIC_API_KEY`，而本仓库不配置这个变量。你的显式 `api_key` + `base_url` 写法才是对的，不要为了“和参考一致”改回去。

**不要因为“和参考不一样”就改。** 先问：哪种更适合你的运行环境？为什么？

### 13.2 在 NOTES.md 里回答四个问题

1. 新增一个工具需要改哪三个地方？如果漏掉其中一个，分别会出现什么现象？
2. 为什么 `agent_loop` 不需要改？如果不用 dispatch map，循环会变成什么样？
3. 一轮返回多个 `tool_use` 时，结果如何与调用配对？为什么必须放在同一条 user 消息里？
4. `safe_path` 防住了什么？没防住什么？为什么说它不是安全边界？

用你自己的话写。写不出来，说明还没真正理解，回去用 `dump_messages` 再跑一遍。

### 13.3 记录踩坑

在 `NOTES.md` 的“踩坑与疑问”里记：

- 你遇到的第一条报错原文；
- 你怎么定位的（三个注册点里的哪一个？）；
- 修复后你学到了什么。

这比抄一遍正确代码有价值得多。

### 13.4 下一章预告

s02 有了 5 个工具，文件工具受 `safe_path` 保护，但有两个明显的缺口：

1. `bash` 完全不受限，`rm -rf /` 还是能跑；
2. `safe_path` 只是路径检查，不是权限系统——模型可以读工作目录内的密钥文件。

s03 会在**工具执行之前**加一道门：这个操作安全吗？需要用户批准吗？哪些路径/命令应该被拒绝？

关键问题是：**这道门应该加在循环里，还是加在每个 handler 里？**

如果你写对了 s02，答案应该很自然：加在循环里，一次覆盖所有工具。这正是 dispatch map 带来的扩展点。

---

## 附录 A：代码结构自检

写完后，对照这张表检查文件结构：

| 部分 | 应该有什么 | 检查 |
|---|---|---|
| 配置 | `ROOT`、`load_dotenv`、`client`、`MODEL`、`WORKDIR` | [ ] |
| System Prompt | `ENVIRONMENT_PROMPT`、`SYSTEM`（含“优先文件工具”） | [ ] |
| 路径安全 | `safe_path` | [ ] |
| 工具执行 | `run_bash`、`run_read`、`run_write`、`run_edit`、`run_glob` | [ ] |
| 工具定义 | `TOOLS`，5 个 schema | [ ] |
| 分发映射 | `TOOL_HANDLERS`，5 个 key | [ ] |
| 核心循环 | `agent_loop(messages)`，查表执行 | [ ] |
| 交互入口 | `if __name__ == "__main__":`，维护 `history` | [ ] |
| 调试辅助 | 可选：`dump_messages`、工具名打印 | [ ] |

## 附录 B：本章术语速查

| 术语 | 一句话解释 |
|---|---|
| dispatch map | 工具名 → 处理函数的字典，用数据代替 `if/elif` |
| handler | 真正执行某个工具的函数，参数名必须和 schema 对齐 |
| schema | 给模型看的工具说明书：名字、描述、参数类型、必填项 |
| 三个注册点 | handler、`TOOLS`、`TOOL_HANDLERS`，必须保持一致 |
| `safe_path` | 把文件工具限制在 `WORKDIR` 内的路径校验函数 |
| 多工具调用 | 一条 assistant 消息里出现多个 `tool_use` |
| `**block.input` | 把模型给的参数字典展开成关键字参数 |
| 串行执行 | 按 `response.content` 顺序逐个执行工具 |

## 附录 C：最小实现的功能边界

s02 故意不做这些事，留到后面章节：

| 没做的事 | 留到 |
|---|---|
| 统一的权限判断 | s03 |
| PreToolUse / PostToolUse 扩展点 | s04 |
| 并发执行多个工具 | 后续优化 |
| 工具结果缓存 | 后续优化 |
| 上下文压缩 | s08 |
| 真正的安全沙箱 | s03 及之后 |

在 s02 阶段，不要提前实现这些。先把“5 个工具 + 一张分发表”跑通，理解三个注册点的对齐关系。

---

> 写完并跑通后，回到 [NOTES.md](./NOTES.md) 更新“实现记录”和“与参考实现的差异”。
>
> 记住这一章的一句话：**循环不变，工具在长；加一个工具，只加一个 handler。**