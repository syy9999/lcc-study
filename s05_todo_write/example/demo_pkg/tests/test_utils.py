"""demo_pkg.utils 的单元测试。

运行方式（在 example/ 目录下）：

    cd s05_todo_write/example
    python -m pytest demo_pkg/tests -q          # ✅ 推荐
    python -m pytest --doctest-modules demo_pkg # ✅ 顺便验证 utils.py 里的 doctest

注意要用 ``python -m pytest`` 而不是裸 ``pytest``：前者会把当前工作目录
加进 ``sys.path``，``import demo_pkg`` 才找得到包；后者只会把
``demo_pkg/tests`` 加进 ``sys.path``，于是报 ``ModuleNotFoundError``。
"""

from __future__ import annotations

import pytest

from demo_pkg import __version__
from demo_pkg.utils import chunk, flatten, normalize_whitespace, slugify

# ---------------------------------------------------------------- slugify


def test_slugify_basic():
    assert slugify("Hello, Claude Code!") == "hello-claude-code"


def test_slugify_collapses_separators_and_strips():
    assert slugify("  -- Multiple   Spaces --  ") == "multiple-spaces"


def test_slugify_empty_string():
    assert slugify("") == ""


def test_slugify_rejects_non_str():
    with pytest.raises(TypeError):
        slugify(None)


# ---------------------------------------------------------------- chunk


def test_chunk_even_split():
    assert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_chunk_last_block_can_be_short():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_chunk_size_larger_than_input():
    assert chunk(["a", "b"], 10) == [["a", "b"]]


def test_chunk_empty_sequence():
    assert chunk([], 3) == []


def test_chunk_accepts_any_sequence():
    assert chunk("abcd", 3) == [["a", "b", "c"], ["d"]]
    assert chunk((1, 2, 3), 1) == [[1], [2], [3]]


@pytest.mark.parametrize("bad_size", [0, -1])
def test_chunk_rejects_non_positive_size(bad_size):
    with pytest.raises(ValueError):
        chunk([1, 2, 3], bad_size)


def test_chunk_rejects_non_int_size():
    with pytest.raises(TypeError):
        chunk([1, 2, 3], 1.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        chunk([1, 2, 3], True)  # bool 不算合法的 size


# --------------------------------------------------- normalize_whitespace


def test_normalize_whitespace_collapses_all_kinds():
    assert normalize_whitespace("  a\n\tb   c  ") == "a b c"


def test_normalize_whitespace_all_blank():
    assert normalize_whitespace("   \n\t ") == ""


def test_normalize_whitespace_rejects_non_str():
    with pytest.raises(TypeError):
        normalize_whitespace(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------- flatten


def test_flatten_mixed_iterables():
    assert flatten([[1, 2], (3,), []]) == [1, 2, 3]


def test_flatten_empty():
    assert flatten([]) == []


# ---------------------------------------------------------------- package


def test_package_exports_public_api():
    import demo_pkg

    assert demo_pkg.slugify is slugify
    assert demo_pkg.chunk is chunk
    assert demo_pkg.normalize_whitespace is normalize_whitespace
    assert __version__ == "0.1.0"
    assert "flatten" not in demo_pkg.__all__
