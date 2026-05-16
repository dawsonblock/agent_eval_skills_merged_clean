"""Tests for repository hygiene scanning."""
from __future__ import annotations

from pathlib import Path

from packages.core.repo_hygiene import scan_repo_hygiene


def test_repo_hygiene_detects_conflict_markers(tmp_path: Path) -> None:
    root = tmp_path / "ToolForge"
    root.mkdir()
    (root / "sample.py").write_text(
        """def ok():
    return 1

<<<<<<< HEAD
=======
>>>>>>> branch
""",
        encoding="utf-8",
    )

    report = scan_repo_hygiene(root)

    assert report.has_issues
    assert any(issue.kind == "conflict_marker" for issue in report.issues)


def test_repo_hygiene_detects_legacy_tree(tmp_path: Path) -> None:
    root = tmp_path / "ToolForge"
    legacy_dir = root / "legacy" / "agent-skills-curated"
    legacy_dir.mkdir(parents=True)

    report = scan_repo_hygiene(root)

    assert report.has_issues
    assert any(issue.kind == "legacy_tree" for issue in report.issues)


def test_repo_hygiene_accepts_clean_tree(tmp_path: Path) -> None:
    root = tmp_path / "ToolForge"
    root.mkdir()
    (root / "README.md").write_text("# Clean tree\n", encoding="utf-8")

    report = scan_repo_hygiene(root)

    assert not report.has_issues