"""s05 示例：最小可运行的问候脚本。

这个文件是 s05 教程「试一个」里的重构练习对象——原始版本只有 5 行，
没有类型标注、没有文档、也没有 ``main`` 守卫，用来演示 Agent 先把任务
拆成 TODO 再动手。重构后仍然保持「直接运行即可看到一句问候」的行为。

运行方式（在 example/ 目录下）：

    python hello.py
"""

from __future__ import annotations

DEFAULT_NAME = "Claude"


def greet(name: str) -> str:
    """打印一句问候语，并把这条消息返回给调用方。

    打印和返回都保留，是为了既满足脚本用法（屏幕上直接看到结果），
    又方便在测试里断言返回值。

    Args:
        name: 被问候的名字，会原样拼进消息里。

    Returns:
        实际打印出去的那条消息，形如 ``Hello, Claude``。

    >>> greet("Claude")
    Hello, Claude
    'Hello, Claude'
    """
    message = f"Hello, {name}"
    print(message)
    return message


def main() -> None:
    """脚本入口：用默认名字跑一遍 :func:`greet`。"""
    greet(DEFAULT_NAME)


if __name__ == "__main__":
    main()
