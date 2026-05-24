"""
Tests for skillforge_ai.evidence_logger — EvidenceLogger.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from skillforge_ai.evidence_logger import EvidenceLogger
from skillforge_ai.models import ValidationReport


class TestEvidenceLogger:
    def _make_logger(self, tmp_path: Path) -> EvidenceLogger:
        return EvidenceLogger(log_dir=tmp_path, skill_name="test-skill")

    def test_log_path_created(self, tmp_path: Path):
        ev = self._make_logger(tmp_path)
        assert ev.log_path.parent.exists()

    def test_log_build_writes_jsonl(self, tmp_path: Path):
        ev = self._make_logger(tmp_path)
        ev.log_build("test-skill", files_created=[], spec={"slug": "test-skill"})
        lines = ev.log_path.read_text().splitlines()
        assert len(lines) >= 1
        record = json.loads(lines[0])
        assert record["event"] == "build"
        assert record["skill"] == "test-skill"

    def test_log_validation_writes_jsonl(self, tmp_path: Path):
        ev = self._make_logger(tmp_path)
        report = ValidationReport(slug="test-skill", passed=True)
        ev.log_validation("test-skill", report)
        lines = ev.log_path.read_text().splitlines()
        record = json.loads(lines[0])
        assert record["event"] == "validation"
        assert record["passed"] is True

    def test_log_repair_writes_jsonl(self, tmp_path: Path):
        ev = self._make_logger(tmp_path)
        ev.log_repair(
            skill_name="test-skill",
            error_summary="schema error",
            patch_description="fixed yaml",
            attempt=1,
            file_patched="toolforge.yaml",
        )
        lines = ev.log_path.read_text().splitlines()
        record = json.loads(lines[0])
        assert record["event"] == "repair"
        assert record["attempt"] == 1

    def test_finalize_creates_summary(self, tmp_path: Path):
        ev = self._make_logger(tmp_path)
        ev.log_message("test_event", info="hello")
        summary_path = ev.finalize()
        assert summary_path.exists()
        data = json.loads(summary_path.read_text())
        assert "counts" in data

    def test_context_manager_finalizes(self, tmp_path: Path):
        with EvidenceLogger(log_dir=tmp_path, skill_name="ctx-test") as ev:
            ev.log_message("inside")
        assert ev.summary_path.exists()

    def test_log_message_generic(self, tmp_path: Path):
        ev = self._make_logger(tmp_path)
        ev.log_message("custom_event", foo="bar", num=42)
        record = json.loads(ev.log_path.read_text().splitlines()[0])
        assert record["event"] == "custom_event"
        assert record["foo"] == "bar"

    def test_counts_increment(self, tmp_path: Path):
        ev = self._make_logger(tmp_path)
        ev.log_build("test-skill", files_created=[])
        ev.log_build("test-skill", files_created=[])
        assert ev._counts["builds"] == 2

    def test_log_package_records_sha(self, tmp_path: Path):
        ev = self._make_logger(tmp_path)
        # Create a dummy zip file
        import zipfile

        zip_path = tmp_path / "dummy.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("hello.txt", "hello")

        ev.log_package("test-skill", zip_path)
        record = json.loads(ev.log_path.read_text().splitlines()[0])
        assert record["event"] == "package"
        assert len(record.get("sha256", "")) == 64
