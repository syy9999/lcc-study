"""string_tools：s06 示例用的字符串工具函数。

只依赖标准库，方便直接导入或跑 doctest 验证：

- :func:`slugify`  把任意文本变成 URL 友好的 slug
"""

from __future__ import annotations

import re

__all__ = ["slugify"]

# 连续的非字母数字字符（含下划线、标点、空白）统一压成一个分隔符
_SLUG_SEPARATOR = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """把文本转换成 slug：小写、单词之间用单个 ``-`` 连接。

    >>> slugify("Hello, Claude Code!")
    'hello-claude-code'
    >>> slugify("  -- Multiple   Spaces --  ")
    'multiple-spaces'
    >>> slugify("")
    ''
    >>> slugify("Already-slugged_Text 123")
    'already-slugged-text-123'
    """
    if not isinstance(text, str):
        raise TypeError(f"text 必须是 str，得到 {type(text).__name__}")

    # 注意：中文字符不在 [a-z0-9] 范围内，会被当作分隔符处理，
    # 所以 slugify("中文") == ""。需要保留中文时应另写 transliterate 逻辑。
    return _SLUG_SEPARATOR.sub("-", text.lower()).strip("-")