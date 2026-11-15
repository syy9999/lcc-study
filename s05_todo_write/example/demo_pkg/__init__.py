"""demo_pkg —— 一个用于演示 Agent 多步任务的小型 Python 包。

它被创建出来主要是为了给 s05 的 `todo_write` 工具练手：任务本身是
"建包 -> 写实现 -> 写测试 -> 跑测试"，正好可以拆成几条 todo 逐步推进。

对外公开的 API：

    >>> from demo_pkg import slugify, chunk, normalize_whitespace
    >>> slugify("Hello, Claude Code!")
    'hello-claude-code'
"""

from .utils import chunk, normalize_whitespace, slugify

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "chunk",
    "normalize_whitespace",
    "slugify",
]
