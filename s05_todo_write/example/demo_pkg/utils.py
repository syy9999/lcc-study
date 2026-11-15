"""demo_pkg 的工具函数集合。

三个函数都只依赖标准库，方便直接跑测试验证：

- :func:`slugify`            把任意标题变成 URL 友好的 slug
- :func:`chunk`              把序列切分成固定大小的块
- :func:`normalize_whitespace` 合并多余空白（含换行、制表符）
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import TypeVar

__all__ = ["chunk", "normalize_whitespace", "slugify"]

T = TypeVar("T")

# 连续的非字母数字字符（含下划线、标点、空白）统一压成一个分隔符
_SLUG_SEPARATOR = re.compile(r"[^a-z0-9]+")
_MULTI_WHITESPACE = re.compile(r"\s+")


def slugify(text: str) -> str:
    """把文本转换成 slug：小写、单词之间用单个 ``-`` 连接。

    >>> slugify("Hello, Claude Code!")
    'hello-claude-code'
    >>> slugify("  -- Multiple   Spaces --  ")
    'multiple-spaces'
    >>> slugify("")
    ''
    """
    if not isinstance(text, str):
        raise TypeError(f"text 必须是 str，得到 {type(text).__name__}")

    # 注意：中文字符不在 [a-z0-9] 范围内，会被当作分隔符处理，
    # 所以 slugify("中文") == ""。需要保留中文时应另写 transliterate 逻辑。
    return _SLUG_SEPARATOR.sub("-", text.lower()).strip("-")


def chunk(items: Sequence[T], size: int) -> list[list[T]]:
    """把 ``items`` 按 ``size`` 切片成若干块，最后一块可能不满。

    >>> chunk([1, 2, 3, 4, 5], 2)
    [[1, 2], [3, 4], [5]]
    >>> chunk([], 3)
    []
    """
    if not isinstance(size, int) or isinstance(size, bool):
        raise TypeError(f"size 必须是 int，得到 {type(size).__name__}")
    if size <= 0:
        raise ValueError(f"size 必须为正整数，得到 {size}")

    sequence = list(items)
    return [sequence[i : i + size] for i in range(0, len(sequence), size)]


def normalize_whitespace(text: str) -> str:
    """把连续空白（空格 / 换行 / 制表符）压成单个空格，并去掉首尾空白。

    >>> normalize_whitespace("  a\\n\\tb   c  ")
    'a b c'
    """
    if not isinstance(text, str):
        raise TypeError(f"text 必须是 str，得到 {type(text).__name__}")

    return _MULTI_WHITESPACE.sub(" ", text).strip()


def flatten(nested: Iterable[Iterable[T]]) -> list[T]:
    """把一层嵌套的可迭代对象展开成平铺列表。

    （内部辅助函数，没有写进 ``__all__``，测试里会一起覆盖。）

    >>> flatten([[1, 2], (3,), []])
    [1, 2, 3]
    """
    return [item for group in nested for item in group]
