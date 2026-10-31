#!/usr/bin/env python3
"""检查 lcc-study 的学习环境是否就绪。

用法：
    python scripts/check_setup.py          # 只做本地检查
    python scripts/check_setup.py --ping   # 额外发送一次最小 API 请求（会产生少量费用）
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_PYTHON = (3, 10)
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/apps/anthropic"
PLACEHOLDER_MARKERS = ("sk-xxx", "请替换", "your-api-key", "<your")

# Windows 控制台默认可能是 GBK，统一输出为 UTF-8，避免中文乱码。
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

# 课程代码使用 anthropic SDK 的 Messages API；
# 通过 DASHSCOPE_BASE_URL 指向阿里云百炼的 Anthropic 兼容端点。
REQUIRED_PACKAGES = {
    "anthropic": "anthropic SDK（百炼兼容客户端）",
    "dotenv": "python-dotenv",
    "yaml": "pyyaml",
}


def report(ok: bool, message: str) -> bool:
    print(f"[{'OK' if ok else 'FAIL'}] {message}")
    return ok


def check_python() -> bool:
    version = sys.version_info
    return report(
        version >= MIN_PYTHON,
        f"Python {version.major}.{version.minor}.{version.micro}（需要 >= 3.10）",
    )


def check_packages() -> bool:
    ok = True
    for module, package in REQUIRED_PACKAGES.items():
        found = importlib.util.find_spec(module) is not None
        hint = "" if found else " → pip install -r requirements.txt"
        ok &= report(found, f"{package}{hint}")
    return ok


def check_env() -> bool:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return report(False, ".env 不存在 → 复制 .env.example 为 .env 并填写")

    try:
        from dotenv import load_dotenv
    except ImportError:
        return report(False, "python-dotenv 未安装，无法读取 .env")

    load_dotenv(env_path, override=True)

    ok = True
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    placeholder = any(marker in api_key.lower() for marker in PLACEHOLDER_MARKERS)
    key_ok = bool(api_key) and not placeholder
    ok &= report(
        key_ok,
        "DASHSCOPE_API_KEY 已配置" if key_ok else "DASHSCOPE_API_KEY 未配置或仍是占位符",
    )

    model = os.getenv("MODEL_ID", "").strip()
    ok &= report(bool(model), f"MODEL_ID = {model}" if model else "MODEL_ID 未配置")

    base_url = os.getenv("DASHSCOPE_BASE_URL", "").strip()
    ok &= report(
        bool(base_url),
        f"DASHSCOPE_BASE_URL = {base_url}" if base_url else "DASHSCOPE_BASE_URL 未配置",
    )
    if base_url and base_url.rstrip("/") != DEFAULT_BASE_URL:
        print(f"[INFO] 当前使用自定义端点；百炼默认端点为 {DEFAULT_BASE_URL}")
    return ok


def check_chapters() -> bool:
    chapters = sorted(path for path in ROOT.glob("s[0-9][0-9]_*") if path.is_dir())
    ok = report(len(chapters) == 17, f"章节目录 {len(chapters)}/17")

    missing = [path.name for path in chapters if not (path / "README.md").is_file()]
    ok &= report(not missing, "章节 README 齐全" if not missing else f"缺少 README：{', '.join(missing)}")

    missing_code = [path.name for path in chapters if not (path / "code.py").is_file()]
    ok &= report(not missing_code, "章节 code.py 齐全" if not missing_code else f"缺少 code.py：{', '.join(missing_code)}")
    return ok


def ping() -> bool:
    try:
        from anthropic import Anthropic
    except ImportError:
        return report(False, "anthropic SDK 未安装，无法 ping")

    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    model = os.getenv("MODEL_ID", "").strip()
    base_url = os.getenv("DASHSCOPE_BASE_URL", "").strip() or DEFAULT_BASE_URL
    if not api_key or not model:
        return report(False, "缺少 DASHSCOPE_API_KEY 或 MODEL_ID，跳过 ping")

    try:
        client = Anthropic(api_key=api_key, base_url=base_url)
        response = client.messages.create(
            model=model,
            max_tokens=8,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
        text = "".join(
            block.text for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()
        return report(True, f"API 连通，模型返回：{text[:40]!r}")
    except Exception as exc:  # noqa: BLE001 - 自检脚本需要把任何失败原因打印出来
        return report(False, f"API 调用失败：{exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 lcc-study 学习环境")
    parser.add_argument(
        "--ping",
        action="store_true",
        help="发送一次最小 API 请求验证连通性（会产生少量费用）",
    )
    args = parser.parse_args()

    print("lcc-study 环境自检")
    print("=" * 46)

    checks = [
        check_python(),
        check_packages(),
        check_env(),
        check_chapters(),
    ]
    if args.ping:
        checks.append(ping())

    print("=" * 46)
    if all(checks):
        print("全部通过。开始 s01 吧：python s01_agent_loop/code.py")
        return 0

    print("有检查项未通过，请按上面的提示修复。")
    return 1


if __name__ == "__main__":
    sys.exit(main())