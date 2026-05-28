#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_PREFIXES = (
    "tests/",
    "fixtures/",
    "examples/",
    "toolathlon-gym-curated/tasks/",
    "toolathlon-gym-curated/local_servers/",
)
SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    "release_artifacts",
}
PATTERNS = {
    "openai_like": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_pat": re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    "pem_private_key": re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "generic_token": re.compile(r"\b(token|api[_-]?key|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{24,}"),
}


def should_skip(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return True
    if path.suffix.lower() in {".zip", ".gz", ".tar", ".tgz", ".png", ".jpg", ".jpeg", ".pdf"}:
        return True
    return False


def allowed_path(rel: str) -> bool:
    return rel.startswith(ALLOWED_PREFIXES)


def main() -> int:
    hits: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or should_skip(path):
            continue
        rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in PATTERNS.items():
            if pattern.search(text) and not allowed_path(rel):
                hits.append(f"{rel}: {label}")

    if hits:
        print("FAIL: potential real secrets detected outside fixture paths")
        for hit in hits:
            print(f"- {hit}")
        return 1

    print("PASS: no disallowed real-looking secrets found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
