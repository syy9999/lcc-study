"""s02 · Tool Use —— 我的实现

格言：加一个工具，只加一个 handler

目标：
    把 s01 的单工具循环扩展成多工具注册表（dispatch map），
    并支持一轮内多个 tool_use。

运行：
    python s02_tool_use/code.py

关键设计：
    TOOLS          = [工具 schema 列表]
    TOOL_HANDLERS  = {工具名: 处理函数}
    agent_loop 只负责：调模型 → 查表执行 → 回传 tool_result

写完再对照：
    ../learn-claude-code-main/s02_tool_use/code.py
"""

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

def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_read(path: str, limit: int | None = None) -> str:
    try:
        lines = safe_path(path).read_text(encoding="utf-8").splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)
    except Exception as exc:
        return f"Error: {exc}"

def run_write(path: str, content: str) -> str:
    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Wrote {file_path.stat().st_size} bytes to {path}"
    except Exception as exc:
        return f"Error: {exc}"

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

TOOL_HANDLERS = {
    "bash": run_bash,
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "glob": run_glob,
}

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
        messages.append({"role":"assistant", "content": response.content})

        # TODO 2: 收集所有 tool_use；没有就 return
        tool_calls = []
        for block in response.content:
            if block.type == 'tool_use':
                tool_calls.append(block)

        if not tool_calls:
            return

        # TODO 3: 逐个查表执行，构造 results
        # 注意：未知工具、参数错误、handler 异常都要变成 result 字符串
        results = []
        for block in tool_calls:
            print(f"> {block.name} {block.input}")
            handler = TOOL_HANDLERS.get(block.name)
            if handler is None:
                output = f"Unknown tool: {block.name}"
            else:
                try:
                    output = handler(**block.input)
                except Exception as exc:
                    output = f"Error: {type(exc).__name__}"

            print(str(output[:500]))
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(output),
            })

        # TODO 4: 把所有 results 作为一条 user 消息追加
        messages.append({"role":"user", "content":results})

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

