"""Repository hygiene checks for merge markers and duplicated legacy trees."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


_TEXT_SUFFIXES = {
    ".md",
    ".json",
    ".js",
    ".mjs",
    ".py",
    ".pyi",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}

_SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "__pycache__",
    "venv",
}

_MARKER_LEFT = "<" * 7
_MARKER_MID = "=" * 7
_MARKER_RIGHT = ">" * 7


@dataclass
class HygieneIssue:
    kind: str
    path: str
    line: int | None = None
    message: str = ""


@dataclass
class HygieneReport:
    issues: list[HygieneIssue] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)


def _should_skip(path: Path) -> bool:
    return any(part in _SKIP_DIRS for part in path.parts)


def _iter_text_files(root: Path):
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        if _should_skip(file_path):
            continue
        if file_path.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        yield file_path


def scan_conflict_markers(root: Path) -> list[HygieneIssue]:
    issues: list[HygieneIssue] = []
    for file_path in _iter_text_files(root):
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if (
                stripped.startswith(f"{_MARKER_LEFT} ")
                or stripped == _MARKER_MID
                or stripped.startswith(f"{_MARKER_RIGHT} ")
            ):
                issues.append(
                    HygieneIssue(
                        kind="conflict_marker",
                        path=str(file_path),
                        line=line_number,
                        message=f"Merge marker found: {stripped}",
                    )
                )
    return issues


def scan_legacy_trees(root: Path) -> list[HygieneIssue]:
    issues: list[HygieneIssue] = []
    legacy_root = root / "legacy"
    if not legacy_root.exists():
        return issues

    for legacy_dir in sorted(p for p in legacy_root.iterdir() if p.is_dir()):
        issues.append(
            HygieneIssue(
                kind="legacy_tree",
                path=str(legacy_dir),
                message="Duplicated legacy tree should not be present in the current workspace",
            )
        )
    return issues


def scan_repo_hygiene(root: Path) -> HygieneReport:
    report = HygieneReport()
    report.issues.extend(scan_conflict_markers(root))
    report.issues.extend(scan_legacy_trees(root))
    return report