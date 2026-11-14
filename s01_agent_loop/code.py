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


import os
import subprocess
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

# 初始化客户端
client = Anthropic(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
)

MODEL=os.getenv("MODEL_ID")

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

# 接收命令字符串，返回可以回传给模型的文本结果。
# 如果 run_bash 直接抛异常，整个程序就退出了，模型永远没机会知道“刚才那条命令错了”
def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"] # 最低限度护栏，不是安全边界
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
    # 工具失败不应该让 harness 崩溃；错误也是模型需要观察的结果
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as exc:
        return f"Error: {exc}"


def _kind(block) -> str:
    if isinstance(block, dict):
        return block.get("type", "dict")
    return getattr(block, "type", type(block).__name__)

def dump_messages(messages: list) -> None:
    for i, msg in enumerate(messages):
        content = msg["content"]
        if isinstance(content, str):
            print(i, msg["role"], "text:", content[:80])
        else:
            kinds = [
                _kind(block)
                for block in content
            ]
            print(i, msg["role"], kinds)

# 完成 agent_loop 主循环
def agent_loop(messages: list) -> None:
    while True:

        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
        )

        # 把 assistant 这一轮追加进 messages
        messages.append({"role": "assistant", "content": response.content})

        print(messages)

        # 收集 tool_use, 没有就直接 return
        tool_calls = [block for block in response.content if block.type == "tool_use"]
        if not tool_calls:
            return

        # 逐个执行工具, 构造 results
        results = []
        for block in tool_calls:
            output=run_bash(block.input["command"])
            print(f"$ {block.input['command']}")
            print(output[:500])
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            })

        # 把 results 作为 user 消息追加，继续循环
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    print("s01: Agent Loop")
    print("Enter a question, press Enter to send. Type q to quit.\n")

    # 多轮对话共享同一份历史；如果放在里面，每轮都会失忆
    history = []
    while True:
        dump_messages(history)
        try:
            query = input("s01 >> ")
        except (EOFError, KeyboardInterrupt):
            break

        if query.strip().lower() in ("q", "exit", ""):
            break

        history.append({"role": "user", "content": query})
        agent_loop(history)

        # loop 退出时，最后一条一定是 assistant 的最终回答
        last_content = history[-1]["content"]
        if isinstance(last_content, list):
            for block in last_content:

                if getattr(block, "type", None) == "text":
                    print(block.text)
        print()