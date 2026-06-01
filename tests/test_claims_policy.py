from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TARGET_DOCS = [
    "README.md",
    "CLAIMS_MATRIX.md",
    "VALIDATION_EVIDENCE.md",
    "DEPLOYMENT.md",
    "WORKSPACE_HEALTH_DASHBOARD.md",
]

FORBIDDEN_PHRASES = [
    "production-ready",
    "fully autonomous",
    "proven safe",
    "builds any tool",
    "full benchmark validated",
]

SAFE_CONTEXT_TOKENS = [
    "not",
    "no",
    "unless",
    "outside",
    "unsupported",
    "must not",
    "only with",
    "requires",
]


def _load_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _window(lines: list[str], index: int, radius: int = 1) -> str:
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)
    return "\n".join(lines[start:end]).lower()


def test_release_docs_do_not_make_unqualified_overclaims() -> None:
    violations: list[str] = []

    for rel in TARGET_DOCS:
        path = REPO_ROOT / rel
        assert path.exists(), f"Missing required claims doc: {rel}"
        lines = _load_lines(path)

        for idx, line in enumerate(lines):
            lowered = line.lower()
            for phrase in FORBIDDEN_PHRASES:
                if phrase in lowered:
                    window = _window(lines, idx)
                    if not any(token in window for token in SAFE_CONTEXT_TOKENS):
                        violations.append(f"{rel}:{idx + 1}: {line.strip()}")

    assert not violations, "Unqualified overclaim phrases found:\n" + "\n".join(violations)


def test_claims_matrix_contains_required_guardrails() -> None:
    claims = (REPO_ROOT / "CLAIMS_MATRIX.md").read_text(encoding="utf-8")
    rows = _claims_matrix_rows(claims)

    smoke = rows["Toolathlon smoke"]
    assert smoke["status"] == "Pass"
    assert "rail_12306" in smoke["allowed wording"]
    assert "filesystem" in smoke["allowed wording"]

    assert rows["Full Toolathlon"]["status"] == "Not claimed"
    assert rows["Production security"]["status"] == "Not claimed"
    assert rows["Hostile-code safety"]["status"] == "Not claimed"
    assert rows["Builds any tool"]["status"] == "Not claimed"
    assert "controlled local framework" in rows["Builds any tool"]["allowed wording"]


def _claims_matrix_rows(markdown: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("|-"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 4 or cells[0] == "Claim":
            continue
        rows[cells[0]] = {
            "allowed wording": cells[1],
            "evidence file": cells[2],
            "status": cells[3],
        }
    return rows
