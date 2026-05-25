"""
Tests for skillforge_ai.validation_runner — ValidationRunner with repair loop.
"""
# mypy: disable-error-code=import-untyped

# pyright: reportMissingTypeStubs=false

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from skillforge_ai.models import ValidationReport


def _make_tool_dir(tmp_path: Path, slug: str = "csv-cleaner") -> Path:
    """Create a minimal tool directory structure."""
    d = tmp_path / "tools" / "generated" / slug
    d.mkdir(parents=True)
    yaml_path = d / "toolforge.yaml"
    yaml_path.write_text(
        f"slug: {slug}\nname: {slug}\ndescription: test\ncategory: data\n",
        encoding="utf-8",
    )
    return d


def _make_registry_json(tmp_path: Path) -> None:
    (tmp_path / "toolforge_registry.json").write_text("{}", encoding="utf-8")


class TestValidationRunnerValidate:
    def test_validate_all_pass(self, tmp_path: Path):
        slug = "csv-cleaner"
        _make_tool_dir(tmp_path, slug)
        _make_registry_json(tmp_path)

        from skillforge_ai.validation_runner import (
            ValidationRunner,
        )

        runner = ValidationRunner(workspace_root=tmp_path)
        with patch.object(
            runner,
            "_run_schema_validator",
            return_value=(object(), []),
        ), patch.object(
            runner,
            "_run_security_validator",
            return_value=[],
        ), patch.object(
            runner,
            "_run_test_validator",
            return_value=([], []),
        ), patch.object(
            runner,
            "_run_safety_analyzer",
            return_value=([], []),
        ), patch.object(
            runner,
            "_update_registry",
            return_value=None,
        ):
            report = runner.validate(slug)

        assert report.schema_ok is True
        assert report.security_ok is True
        assert report.safety_ok is True
        assert report.passed is True

    def test_validate_fails_on_security_violation(self, tmp_path: Path):
        slug = "csv-cleaner"
        _make_tool_dir(tmp_path, slug)
        _make_registry_json(tmp_path)

        from skillforge_ai.validation_runner import (
            ValidationRunner,
        )

        runner = ValidationRunner(workspace_root=tmp_path)
        with patch.object(
            runner,
            "_run_schema_validator",
            return_value=(object(), []),
        ), patch.object(
            runner,
            "_run_security_validator",
            return_value=["Security: Disallowed import: os"],
        ), patch.object(
            runner,
            "_run_test_validator",
            return_value=([], []),
        ), patch.object(
            runner,
            "_run_safety_analyzer",
            return_value=([], []),
        ), patch.object(
            runner,
            "_update_registry",
            return_value=None,
        ):
            report = runner.validate(slug)

        assert report.security_ok is False
        assert report.passed is False
        assert any("Disallowed" in e for e in report.errors)

    def test_validate_schema_error(self, tmp_path: Path):
        slug = "csv-cleaner"
        _make_tool_dir(tmp_path, slug)
        _make_registry_json(tmp_path)

        from skillforge_ai.validation_runner import (
            ValidationRunner,
        )

        runner = ValidationRunner(workspace_root=tmp_path)
        with patch.object(
            runner,
            "_run_schema_validator",
            return_value=(None, ["Schema: missing required field: slug"]),
        ), patch.object(
            runner,
            "_run_test_validator",
            return_value=([], []),
        ), patch.object(
            runner, "_update_registry", return_value=None
        ):
            report = runner.validate(slug)

        assert report.schema_ok is False
        assert report.passed is False

    def test_validation_report_contains_required_check_keys(
        self,
        tmp_path: Path,
    ):
        slug = "csv-cleaner"
        _make_tool_dir(tmp_path, slug)
        _make_registry_json(tmp_path)

        skill_dir = tmp_path / "skills" / slug
        (skill_dir / "tool").mkdir(parents=True)
        (skill_dir / "tests").mkdir(parents=True)
        (skill_dir / "examples").mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
        (skill_dir / "README.md").write_text("# README\n", encoding="utf-8")
        (skill_dir / "metadata.json").write_text(
            (
                '{"name":"csv-cleaner","description":"x",'
                '"category":"data","version":"0.1.0","inputs":[],'
                '"outputs":[],"tools_required":[],"mcp_servers":[],'
                '"permissions":[],"risk_level":"low","validation":'
                '{"metadata":"pending","syntax":"pending",'
                '"tests":"pending","package":"pending",'
                '"smoke":"pending"}}\n'
            ),
            encoding="utf-8",
        )
        (skill_dir / "tool" / "main.py").write_text(
            "print('ok')\n",
            encoding="utf-8",
        )
        (skill_dir / "tests" / "test_basic.py").write_text(
            "def test_ok():\n    assert True\n",
            encoding="utf-8",
        )
        (skill_dir / "examples" / "messy.csv").write_text(
            "a,b\n1,2\n",
            encoding="utf-8",
        )

        from skillforge_ai.validation_runner import (
            ValidationRunner,
        )

        runner = ValidationRunner(workspace_root=tmp_path)
        with patch.object(
            runner,
            "_run_schema_validator",
            return_value=(object(), []),
        ), patch.object(
            runner,
            "_run_security_validator",
            return_value=[],
        ), patch.object(
            runner,
            "_run_test_validator",
            return_value=([], []),
        ), patch.object(
            runner,
            "_run_safety_analyzer",
            return_value=([], []),
        ), patch.object(
            runner,
            "_update_registry",
            return_value=None,
        ):
            runner.validate(slug)

        payload = (skill_dir / "validation_report.json").read_text(
            encoding="utf-8",
        )
        assert '"readme"' in payload
        assert '"examples"' in payload
        assert '"package"' in payload


class TestValidationRunnerRepairLoop:
    def test_repair_loop_succeeds_on_second_attempt(self, tmp_path: Path):
        slug = "csv-cleaner"
        _make_tool_dir(tmp_path, slug)
        _make_registry_json(tmp_path)

        from skillforge_ai.validation_runner import (
            ValidationRunner,
        )

        runner = ValidationRunner(
            workspace_root=tmp_path,
            max_repair_attempts=3,
        )

        first_fail = ValidationReport(
            slug=slug,
            passed=False,
            attempt=1,
            errors=["Schema: bad field"],
        )
        second_pass = ValidationReport(
            slug=slug,
            passed=True,
            attempt=2,
        )

        with patch.object(
            runner,
            "validate",
            side_effect=[first_fail, second_pass],
        ), patch.object(runner, "_repair", return_value=None):
            report = runner.repair_loop(slug, provider="rule_based")

        assert report.passed is True

    def test_repair_loop_exhausts_max_attempts(self, tmp_path: Path):
        slug = "csv-cleaner"
        _make_tool_dir(tmp_path, slug)
        _make_registry_json(tmp_path)

        from skillforge_ai.validation_runner import (
            ValidationRunner,
        )

        runner = ValidationRunner(
            workspace_root=tmp_path,
            max_repair_attempts=2,
        )

        fail1 = ValidationReport(
            slug=slug,
            passed=False,
            attempt=1,
            errors=["Schema: persistent error"],
        )
        fail2 = ValidationReport(
            slug=slug,
            passed=False,
            attempt=2,
            errors=["Schema: persistent error"],
        )
        fail3 = ValidationReport(
            slug=slug,
            passed=False,
            attempt=3,
            errors=["Schema: persistent error"],
        )

        with patch.object(
            runner,
            "validate",
            side_effect=[fail1, fail2, fail3],
        ), patch.object(runner, "_repair", return_value=None):
            report = runner.repair_loop(slug, provider="rule_based")

        assert report.passed is False
        assert report.attempt >= 2
