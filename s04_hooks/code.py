"""
s04_hooks.py - Hooks

Hooks run callbacks at fixed points in the agent loop:

    User prompt
         |
         v
    UserPromptSubmit
         |
         v
    +----------+      +-------+      +------------+      +-------+
    | messages | ---> |  LLM  | ---> | PreToolUse | ---> | Tool  |
    +----------+      +---+---+      | permission |      +---+---+
         ^                | stop     | log        |          |
         |                v          +------------+          v
         |            Stop hook                         PostToolUse
         |                                               |
         +---------------- tool_result ------------------+
"""

import os
import re
import subprocess
from pathlib import Path

try:
    import readline
    readline.parse_and_bind('set bind-tty-special-chars off')
    readline.parse_and_bind('set input-meta on')
    readline.parse_and_bind('set output-meta on')
    readline.parse_and_bind('set convert-meta off')
except ImportError:
    pass

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
# E:\llm-learning\learn-claude-code\lcc-study\s04_hooks

ENVIRONMENT_PROMPT = (
    "Windows: the bash tool runs through cmd.exe; use cmd.exe syntax, not Unix "
    "Bash or PowerShell syntax, and prefer dedicated file tools for file operations"
    if os.name == "nt"
    else "Unix-like: the bash tool runs the system shell"
)
SYSTEM = (
    f"You are a coding agent at {WORKDIR}. Environment: {ENVIRONMENT_PROMPT}. "
    "Use tools to solve tasks. Act, don't explain."
)

# -- From s02-s03: tool implementations --

def run_bash(command: str) -> str:
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, errors="replace", timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"

def run_read(path: str, limit: int | None = None) -> str:
    try:
        file_path = (WORKDIR / path).resolve()
        lines = file_path.read_text(encoding="utf-8").splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"

def run_write(path: str, content: str) -> str:
    try:
        file_path = (WORKDIR / path).resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"

def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        file_path = (WORKDIR / path).resolve()
        text = file_path.read_text(encoding="utf-8")
        if old_text not in text:
            return f"Error: text not found in {path}"
        file_path.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"

def run_glob(pattern: str) -> str:
    import glob as g
    try:
        matches = sorted({
            match for match in g.glob(
                pattern, root_dir=WORKDIR, recursive=True)
            if (WORKDIR / match).resolve().is_relative_to(WORKDIR)
        })
        shown = matches[:200]
        if len(matches) > 200:
            shown.append("... (more matches omitted; narrow the pattern)")
        return "\n".join(shown) if shown else "(no matches)"
    except Exception as e:
        return f"Error: {e}"

TOOLS = [
    {
        'name': 'bash',
        'description': "Run a shell command",
        'input_schema': {
            'type': 'object',
            'properties': {
                'command': {
                    'type': 'string',
                    "description": "The shell command to run.",
                },
            },
            'required': ['command'],
        },
    },
    {
        "name": "raad_file",
        "description": "Read file contents",
        "input_schema": {
            "type": "object",
            "properties": {
                "path" : {
                    "type": "string",
                    "description": "The path of the file to read.",
                },
                "limit" : {
                    "type": "integer",
                    "description": "The maximum number of lines to read.",
                },
            },
            "required": ["path"],
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path" : {
                    "type": "string",
                    "description": "The path of the file to write.",
                },
                "content" : {
                    "type": "string",
                    "description": "The content to write.",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace exact text in a file once",
        "input_schema": {
            "type": "object",
            "properties": {
                "path" : {
                    "type": "string",
                },
                "old_text" : {
                    "type": "string",
                },
                "new_text" : {
                    "type": "string",
                },
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "glob",
        "description": "Find files matching a glob pattern; ** matches recursively.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern" : {
                    "type": "string",
                },
            },
            'required': ['pattern'],
        },
    },
]

TOOL_HANDLERS = {
    "bash": run_bash, "read_file": run_read, "edit_file": run_edit,
    "glob": run_glob, "write_file": run_write,
}

# -- New in s04: hook system (s03 permission logic now uses hooks) --

# - `HOOKS` 是一个字典：**键是事件名，值是一个回调函数列表**。
# - 刚开始列表都是空的，后面谁想在某个事件上 "插一脚"，就把自己的函数 append 进去
HOOKS = {
    "UserPromptSubmit": [], # 触发时机: 用户输入提交后, 进入LLM之前, 用于输入验证, 注入上下文
    "PreToolUse": [], # 工具执行前, 用于权限检查, 日志记录
    "PostToolUse": [], # 工具执行后, 用于自动 git add 等, 输出检查
    "Stop": [], # 循环即将退出时, 用于收尾清理, 决定是否继续循环
}
# 扩展通过 register_hook() 添加, 循环只调用 trigger_hooks()

# 注册函数, 把一个回调函数放入指定事件的列表末尾
def register_hook(event:str, callback):
    HOOKS[event].append(callback)

def trigger_hooks(event:str, *args):
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None: # 返回值 != None -> hook 说停
            return result
    return None
# PreToolUse 返回非 None 时，本次工具执行被阻止；Stop 返回非 None 时，循环继续。
# UserPromptSubmit 和 PostToolUse 的返回值不参与控制流。

# UserPromptSubmit 在用户输入提交后、进入 LLM 前触发。以下 hook 记录当前工作目录：
def context_inject_hook(query: str) -> str | None:
    """Inject current working directory info into every prompt."""
    print(f"\033[90m[HOOK] UserPromptSubmit: working in {WORKDIR}\033[0m")
    return None   # return None = no modification, let prompt through

register_hook("UserPromptSubmit", context_inject_hook)



# s03 permission check logic, now wrapped as a hook
DENY_LIST = ["rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if="]
DESTRUCTIVE_COMMAND_WORD = re.compile(
    r"(?i)(?:^|[;&|()\n])\s*(?:rm|del)(?=\s|$|[;&|()])"
)
DESTRUCTIVE = ["rm ", "> /etc/", "chmod 777"]


def contains_destructive_command(command: str) -> bool:
    return bool(DESTRUCTIVE_COMMAND_WORD.search(command))

# PreToolUse / PostToolUse，工具执行前后的 hook。
# s03 的权限检查逻辑现在包装成 PreToolUse hook，再加一个日志 hook 和一个大输出提醒：

# PreToolUse: 权限检查（s03 的逻辑，从循环移到 hook）
def permission_hook(block):
    if block.name == "bash":
        for pattern in DENY_LIST:
            if pattern in block.input.get("command", ""):
                return "Permission denied by the deny list"
    if block.name in ("read_file", "write_file", "edit_file"):
        path = block.input.get("path", "")
        if not (WORKDIR / path).resolve().is_relative_to(WORKDIR):
            choice = input("   Allow? [y/N] ").strip().lower()
            if choice not in ("y", "yes"):
                return "Permission denied by user"
        return None

# PreToolUse: 日志
def log_hook(block):
    print(f"[HOOK] {block.name}(...)")

# PostToolUse: 大文件提醒
def large_output_hook(block, output):
    if len(str(output)) > 100000:
        print(f"[HOOK] ⚠ Large output from {block.name}")

register_hook("PreToolUse", permission_hook)
register_hook("PreToolUse", log_hook)
register_hook("PostToolUse", large_output_hook)


# Stop 在循环即将退出时触发。以下 hook 打印收尾统计：
def summary_hook(messages: list) -> str | None:
    """Print a summary when the loop is about to stop."""

    tool_count = 0

    for m in messages:  # 遍历每条消息
        content = m.get("content")
        if not isinstance(content, list):  # content 不是块数组（纯文本）→ 跳过
            continue
        for b in content:  # 遍历消息里的每个块
            if isinstance(b, dict) and b.get("type") == "tool_result":
                tool_count += 1  # 命中一个工具结果，计数 +1

    # tool_count = sum(1 for m in messages
    #                  for b in (m.get("content") if isinstance(m.get("content"), list) else [])
    #                  if isinstance(b, dict) and b.get("type") == "tool_result")

    print(f"\033[90m[HOOK] Stop: session used {tool_count} tool calls\033[0m")
    return None   # return None = allow stop, return string = force continuation

register_hook("Stop", summary_hook)


# -- Agent loop: same structure as s03, but no hard-coded check --
# s03: if not check_permission(block): ...
# s04: if trigger_hooks("PreToolUse", block): ...
def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            messages=messages,
            model=MODEL,
            system=SYSTEM,
            tools=TOOLS,
            max_tokens=8000,
        )
        messages.append({"role":"assistant", "content": response.content})

        tool_calls = [block for block in response.content if block.type == "tool_use"]

        if not tool_calls:
            # 没有工具调用, 执行 Stop 的 hook 逻辑, ← 退出之前
            force = trigger_hooks("Stop", messages)
            if force is not None:
                # hook returned a message → inject it and continue
                messages.append({"role":"assistant", "content": force})
                continue
            return

        # 有工具调用
        results = []
        for block in tool_calls:
            # s03: if not check_permission(block): ...
            # s04: hook 替代硬编码
            blocked = trigger_hooks("PreToolUse", block)
            # hook 拒绝执行这个 tool
            if blocked is not None:
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(blocked),
                })
                continue

            handler = TOOL_HANDLERS.get(block.name)
            output = handler(**block.input) if handler else f"Unknown: {block.name}"

            # 触发执行完工具的 hook
            trigger_hooks("PostToolUse", block, output)

            # 把结果拼接回messages
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})

        messages.append({"role": "user", "content": results})  # 把结果回写历史

# 四个 hook 覆盖了 agent cycle 的关键节点：输入→执行前→执行后→退出。
# 循环只负责调用 trigger_hooks()，具体逻辑全在 hook 回调里。


if __name__ == "__main__":
    print("s04: Hooks - extension logic on hooks, loop stays clean")
    print("Enter a question, press Enter to send. Type q to quit.\n")

    history = []
    while True:
        try:
            # \001/\002 tell Readline the ANSI escapes have zero display width.
            query = input("\001\033[36m\002s04 >> \001\033[0m\002")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        trigger_hooks("UserPromptSubmit", query) # ← 进入 LLM 之前
        history.append({"role": "user", "content": query})
        agent_loop(history)
        for block in history[-1]["content"]:
            if getattr(block, "type", None) == "text":
                print(block.text)
        print()