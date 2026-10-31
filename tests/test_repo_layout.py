"""检查学习仓库的目录骨架是否完整。"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

CHAPTERS = [
    "s01_agent_loop",
    "s02_tool_use",
    "s03_permission",
    "s04_hooks",
    "s05_todo_write",
    "s06_subagent",
    "s07_skill_loading",
    "s08_context_compact",
    "s09_memory",
    "s10_task_system",
    "s11_background_tasks",
    "s12_cron_scheduler",
    "s13_agent_teams",
    "s14_mcp_plugin",
    "s15_integrated_harness",
    "s16_workflow_runtime",
    "s17_goal_loop",
]


def test_chapter_count() -> None:
    assert len(CHAPTERS) == 17


@pytest.mark.parametrize("name", CHAPTERS)
def test_chapter_has_readme_and_code(name: str) -> None:
    chapter = ROOT / name
    assert chapter.is_dir(), f"缺少章节目录：{name}"
    assert (chapter / "README.md").is_file(), f"缺少中文教程：{name}/README.md"
    assert (chapter / "NOTES.md").is_file(), f"缺少学习笔记：{name}/NOTES.md"
    assert (chapter / "code.py").is_file(), f"缺少实现文件：{name}/code.py"


@pytest.mark.parametrize("name", CHAPTERS)
def test_chapter_tutorial_is_imported(name: str) -> None:
    tutorial = (ROOT / name / "README.md").read_text(encoding="utf-8")
    assert "教程来源" in tutorial, f"{name}/README.md 不是导入的教程"
    assert "NOTES.md" in tutorial, f"{name}/README.md 缺少笔记入口"


def test_skills_imported() -> None:
    assert (ROOT / "skills" / "code-review" / "SKILL.md").is_file()


@pytest.mark.parametrize(
    "filename",
    ["README.md", "PROGRESS.md", "requirements.txt", ".env.example", ".gitignore"],
)
def test_root_file_exists(filename: str) -> None:
    assert (ROOT / filename).is_file(), f"缺少根文件：{filename}"