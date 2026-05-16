"""Tests for local-file-hasher tool."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from tool import hash_file  # noqa: E402


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    p = tmp_path / "sample.txt"
    p.write_bytes(b"Hello, ToolForge!\n")
    return p


def test_sha256(sample_file: Path) -> None:
    result = hash_file(str(sample_file), "sha256")
    expected = hashlib.sha256(sample_file.read_bytes()).hexdigest()
    assert result["hash"] == expected
    assert result["algorithm"] == "sha256"


def test_md5(sample_file: Path) -> None:
    result = hash_file(str(sample_file), "md5")
    expected = hashlib.md5(sample_file.read_bytes()).hexdigest()  # noqa: S324
    assert result["hash"] == expected


def test_sha512(sample_file: Path) -> None:
    result = hash_file(str(sample_file), "sha512")
    assert len(result["hash"]) == 128  # sha512 hex length


def test_size_bytes(sample_file: Path) -> None:
    result = hash_file(str(sample_file))
    assert result["size_bytes"] == sample_file.stat().st_size


def test_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        hash_file("/nonexistent/path/file.txt")


def test_unsupported_algorithm(sample_file: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported algorithm"):
        hash_file(str(sample_file), "md4")
