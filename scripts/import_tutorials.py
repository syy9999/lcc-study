#!/usr/bin/env python3
"""把参考仓库的中文教程、配图和技能示例导入本学习仓库。

规则：
- 参考仓库的 sNN/README.zh.md  -> 本仓库 sNN/README.md（中文教程）
- 本仓库原有的 sNN/README.md   -> sNN/NOTES.md（只迁移一次，不覆盖已有 NOTES.md）
- 参考仓库的 sNN/images/       -> 本仓库 sNN/images/（只复制中文版，跳过 *.en.* / *.ja.*）
- 参考仓库的 skills/           -> 本仓库 skills/
- 参考仓库的 LICENSE           -> 本仓库 licenses/learn-claude-code-LICENSE.txt

参考实现 code.py 不会被复制；本仓库的 sNN/code.py 是学习者自己的实现。

用法（在仓库根目录）：
    python scripts/import_tutorials.py
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

STUDY_ROOT = Path(__file__).resolve().parent.parent
REF_ROOT = STUDY_ROOT.parent / "learn-claude-code-main"

TUTORIAL_BANNER = (
    "> 教程来源：[shareAI-lab/learn-claude-code]"
    "(https://github.com/shareAI-lab/learn-claude-code)（MIT）"
    " · 中文教程副本 · 学习笔记见 [NOTES.md](./NOTES.md)"
)

LANG_SWITCHER = re.compile(r"^\[English\]\(README\.md\).*$", re.MULTILINE)

# 本地化教程里的配置示例：本项目使用阿里云百炼的 DASHSCOPE_* 变量。
CONFIG_REPLACEMENTS = {
    "ANTHROPIC_API_KEY": "DASHSCOPE_API_KEY",
    "ANTHROPIC_AUTH_TOKEN": "DASHSCOPE_API_KEY",
    "ANTHROPIC_BASE_URL": "DASHSCOPE_BASE_URL",
}

# skills/ 里的示例脚本还带有 Anthropic 官方端点和模型默认值，一并本地化。
# 注意：完整 URL 的替换必须放在通用 ANTHROPIC_BASE_URL 替换之前。
SKILL_REPLACEMENTS = {
    "ANTHROPIC_BASE_URL=https://api.anthropic.com": "DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/apps/anthropic",
    **CONFIG_REPLACEMENTS,
    "MODEL_NAME": "MODEL_ID",
    "claude-sonnet-4-20250514": "deepseek-v4.1-flash-1017",
}
SKILL_TEXT_SUFFIXES = {".py", ".md", ".txt", ".yaml", ".yml", ".json"}

# 配图命名：无后缀的是中文版，*.en.* / *.ja.* 是英文/日文版，导入时跳过。
IMAGE_LANG_SUFFIX = re.compile(r"\.(en|ja)\.(svg|png|jpe?g|webp|gif)$", re.IGNORECASE)


def sync_images(src: Path, dst: Path) -> int:
    """只复制中文版配图，并清理之前导入的外文版本。"""
    dst.mkdir(parents=True, exist_ok=True)
    for existing in dst.iterdir():
        if existing.is_file() and IMAGE_LANG_SUFFIX.search(existing.name):
            existing.unlink()

    copied = 0
    for path in src.iterdir():
        if path.is_file() and not IMAGE_LANG_SUFFIX.search(path.name):
            shutil.copy2(path, dst / path.name)
            copied += 1
    return copied


def localize_skills(skills_dir: Path) -> int:
    """替换 skills/ 下文本文件中的 Anthropic 配置，返回修改的文件数。"""
    changed = 0
    for path in skills_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SKILL_TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        updated = text
        for old, new in SKILL_REPLACEMENTS.items():
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def migrate_notes(chapter: str, notes_path: Path) -> bool:
    """把旧的 README 笔记模板迁移成 NOTES.md。只迁移一次。"""
    target = notes_path.with_name("NOTES.md")
    if target.exists() or not notes_path.is_file():
        return False

    text = notes_path.read_text(encoding="utf-8")
    # 只迁移我们自己生成的笔记模板，避免误把教程当笔记。
    if "## 我的笔记" not in text:
        return False

    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines[0] = f"{lines[0]} —— 学习笔记"
        lines[1:1] = [
            "",
            f"> 本章教程：[README.md](./README.md) · 参考实现：`../learn-claude-code-main/{chapter}/code.py`",
        ]
    text = "\n".join(lines) + "\n"
    text = text.replace(
        f"- 章节讲解：`../learn-claude-code-main/{chapter}/README.zh.md`",
        "- 本章教程：[README.md](./README.md)",
    )
    if "原始仓库" not in text:
        text = text.rstrip() + "\n- 原始仓库：<https://github.com/shareAI-lab/learn-claude-code>\n"

    target.write_text(text, encoding="utf-8")
    return True


def import_chapter(chapter_dir: Path) -> tuple[bool, bool]:
    name = chapter_dir.name
    ref_dir = REF_ROOT / name
    tutorial_src = ref_dir / "README.zh.md"
    if not tutorial_src.is_file():
        return False, False

    notes_migrated = migrate_notes(name, chapter_dir / "README.md")

    text = tutorial_src.read_text(encoding="utf-8")
    text = LANG_SWITCHER.sub(TUTORIAL_BANNER, text, count=1)
    for old, new in CONFIG_REPLACEMENTS.items():
        text = text.replace(old, new)
    (chapter_dir / "README.md").write_text(text, encoding="utf-8")

    images_src = ref_dir / "images"
    if images_src.is_dir():
        sync_images(images_src, chapter_dir / "images")
    return True, notes_migrated


def main() -> int:
    if not REF_ROOT.is_dir():
        print(f"找不到参考仓库：{REF_ROOT}")
        return 1

    chapters = sorted(path for path in STUDY_ROOT.glob("s[0-9][0-9]_*") if path.is_dir())
    imported = 0
    migrated = 0
    missing: list[str] = []

    for chapter_dir in chapters:
        ok, notes_migrated = import_chapter(chapter_dir)
        if not ok:
            missing.append(chapter_dir.name)
            continue
        imported += 1
        migrated += int(notes_migrated)

    skills_src = REF_ROOT / "skills"
    skills_changed = 0
    if skills_src.is_dir():
        shutil.copytree(skills_src, STUDY_ROOT / "skills", dirs_exist_ok=True)
        skills_changed = localize_skills(STUDY_ROOT / "skills")

    license_src = REF_ROOT / "LICENSE"
    if license_src.is_file():
        license_dir = STUDY_ROOT / "licenses"
        license_dir.mkdir(exist_ok=True)
        shutil.copy2(license_src, license_dir / "learn-claude-code-LICENSE.txt")

    print(f"导入教程：{imported}/{len(chapters)} 章")
    print(f"迁移笔记：{migrated} 章（README.md -> NOTES.md）")
    print(f"本地化技能示例：{skills_changed} 个文件")
    if missing:
        print(f"缺少中文教程：{', '.join(missing)}")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())