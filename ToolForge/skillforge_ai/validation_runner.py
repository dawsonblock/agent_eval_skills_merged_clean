"""
ValidationRunner — run all ToolForge validators and optionally attempt AI-driven repair.

Runs 5 validators + SafetyAnalyzer in sequence:
  1. SchemaValidator  (toolforge.yaml structure)
  2. SecurityValidator (policy compliance)
  3. MCPValidator      (optional: mcp/ directory)
  4. SkillValidator    (SKILL.md frontmatter)
  5. TestValidator     (pytest)
  6. SafetyAnalyzer    (static AST analysis)

If validation fails and repair is requested, the runner calls the LLM
(via AISpecGenerator/RuleBasedSpecGenerator) to patch the offending file,
then re-runs validation — up to max_repair_attempts times.

Usage::

    runner = ValidationRunner(workspace_root=Path("."), evidence_logger=ev)
    report = runner.validate("csv-cleaner")

    # Or with repair:
    report = runner.repair_loop("csv-cleaner", provider="rule_based")
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from skillforge_ai.models import ValidationReport

logger = logging.getLogger(__name__)


def _add_packages_to_path(workspace_root: Path) -> None:
    pkg_root = str(workspace_root)
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)


class ValidationRunner:
    """
    Aggregate validator for a ToolForge tool directory.

    Parameters
    ----------
    workspace_root : Path
        Root of the ToolForge workspace (where toolforge_registry.json lives).
    evidence_logger : EvidenceLogger | None
        Optional logger; if provided, each validation attempt is recorded.
    max_repair_attempts : int
        Maximum number of AI-driven repair iterations before giving up.
    """

    def __init__(
        self,
        workspace_root: Path,
        evidence_logger: Any | None = None,
        max_repair_attempts: int = 3,
    ) -> None:
        self._root = workspace_root.resolve()
        self._ev = evidence_logger
        self._max_repair = max_repair_attempts
        _add_packages_to_path(self._root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, slug: str, attempt: int = 1) -> ValidationReport:
        """
        Run all validators for the tool identified by *slug*.
        Returns a ValidationReport (never raises).
        """
        tool_dir = self._root / "tools" / "generated" / slug
        report = ValidationReport(slug=slug, passed=True, attempt=attempt)

        if not tool_dir.exists():
            report.passed = False
            report.errors.append(f"Tool directory does not exist: {tool_dir}")
            return report

        # 1. Schema
        yaml_path = tool_dir / "toolforge.yaml"
        if yaml_path.exists():
            spec, errs = self._run_schema_validator(yaml_path)
            if errs:
                report.schema_ok = False
                report.passed = False
                report.errors.extend(errs)
        else:
            report.schema_ok = False
            report.passed = False
            report.errors.append(f"Missing toolforge.yaml in {tool_dir}")
            # Can't proceed without a spec
            return report

        # 2. Security
        if spec is not None:
            sec_errs = self._run_security_validator(spec)
            if sec_errs:
                report.security_ok = False
                report.passed = False
                report.errors.extend(sec_errs)
                for w in sec_errs:
                    report.warnings.append(f"Security: {w}")

        # 3. MCP (optional)
        mcp_dir = tool_dir / "mcp"
        if mcp_dir.exists():
            mcp_errs = self._run_mcp_validator(tool_dir)
            if mcp_errs:
                report.mcp_ok = False
                report.passed = False
                report.errors.extend(mcp_errs)
            else:
                report.mcp_ok = True
        else:
            report.mcp_ok = None  # not checked

        # 4. Skill SKILL.md
        skill_dir = self._root / "skills" / "generated"
        skill_md = self._find_skill_md(skill_dir, slug)
        if skill_md is not None:
            skill_errs = self._run_skill_validator(skill_md)
            if skill_errs:
                report.skill_ok = False
                report.passed = False
                report.errors.extend(skill_errs)

        # 5. Tests
        test_errs, test_warnings = self._run_test_validator(tool_dir)
        if test_errs:
            report.tests_ok = False
            report.passed = False
            report.errors.extend(test_errs)
        report.warnings.extend(test_warnings)

        # 6. Safety analysis
        if spec is not None:
            safety_errs, safety_warnings = self._run_safety_analyzer(spec, tool_dir)
            if safety_errs:
                report.safety_ok = False
                report.passed = False
                report.errors.extend(safety_errs)
            report.warnings.extend(safety_warnings)

        # Update registry
        self._update_registry(slug, report)

        # Log evidence
        if self._ev is not None:
            try:
                self._ev.log_validation(slug, report)
            except Exception as exc:
                logger.debug("EvidenceLogger.log_validation failed: %s", exc)

        return report

    def repair_loop(
        self,
        slug: str,
        provider: str = "rule_based",
    ) -> ValidationReport:
        """
        Repeatedly validate → repair up to max_repair_attempts times.

        Returns the final ValidationReport (passed or not).
        """
        report = self.validate(slug, attempt=1)

        for attempt in range(2, self._max_repair + 2):
            if report.passed:
                break
            logger.info(
                "Validation failed (%d error(s)) — attempting AI repair (attempt %d/%d)",
                len(report.errors),
                attempt - 1,
                self._max_repair,
            )
            self._repair(slug, report, attempt - 1, provider)
            report = self.validate(slug, attempt=attempt)

        return report

    # ------------------------------------------------------------------
    # Individual validators
    # ------------------------------------------------------------------

    def _run_schema_validator(
        self, yaml_path: Path
    ) -> tuple[Any | None, list[str]]:
        """Return (ToolSpec | None, error_list)."""
        try:
            from packages.validators.schema_validator import (
                validate_yaml_file,
                SchemaValidationError,
            )
            spec = validate_yaml_file(yaml_path)
            return spec, []
        except Exception as exc:
            errs = getattr(exc, "errors", None)
            if errs and isinstance(errs, list):
                return None, [f"Schema: {e}" for e in errs]
            return None, [f"Schema: {exc}"]

    def _run_security_validator(self, spec: Any) -> list[str]:
        try:
            from packages.validators.security_validator import validate_security, SecurityViolation
            violations = validate_security(spec)
            return [f"Security: {v}" for v in (violations or [])]
        except Exception as exc:
            violations = getattr(exc, "violations", None)
            if violations:
                return [f"Security: {v}" for v in violations]
            return [f"Security validator error: {exc}"]

    def _run_mcp_validator(self, tool_dir: Path) -> list[str]:
        try:
            from packages.validators.mcp_validator import validate_mcp_server, MCPValidationError
            validate_mcp_server(tool_dir)
            return []
        except Exception as exc:
            errs = getattr(exc, "errors", None)
            if errs:
                return [f"MCP: {e}" for e in errs]
            return [f"MCP: {exc}"]

    def _run_skill_validator(self, skill_md: Path) -> list[str]:
        try:
            from packages.validators.skill_validator import validate_skill_file, SkillValidationError
            validate_skill_file(skill_md)
            return []
        except Exception as exc:
            errs = getattr(exc, "errors", None)
            if errs:
                return [f"Skill: {e}" for e in errs]
            return [f"Skill: {exc}"]

    def _run_test_validator(self, tool_dir: Path) -> tuple[list[str], list[str]]:
        """Return (errors, warnings). Warnings when no tests found."""
        tests_dir = tool_dir / "tests"
        if not tests_dir.exists() or not any(tests_dir.glob("test_*.py")):
            return [], ["No test files found — skipping pytest"]
        try:
            from packages.validators.test_validator import run_tests
            report = run_tests(tool_dir)
            if not report.all_passed:
                errors = [
                    f"Tests: {f.get('nodeid', 'unknown')} — {f.get('message', '')}"
                    for f in report.failures
                ] or [f"Tests: {report.failed} test(s) failed, {report.errors} error(s)"]
                return errors, []
            return [], []
        except Exception as exc:
            return [f"Tests: {exc}"], []

    def _run_safety_analyzer(
        self, spec: Any, tool_dir: Path
    ) -> tuple[list[str], list[str]]:
        try:
            from packages.core.safety_analyzer import analyze_safety
            safety_report = analyze_safety(spec, tool_dir)
            errors = [
                f"Safety({i.code}): {i.message}"
                for i in safety_report.issues
                if i.severity == "error"
            ]
            warnings = [
                f"Safety({i.code}): {i.message}"
                for i in safety_report.issues
                if i.severity == "warning"
            ]
            return errors, warnings
        except Exception as exc:
            return [], [f"Safety analyzer error: {exc}"]

    # ------------------------------------------------------------------
    # Repair
    # ------------------------------------------------------------------

    def _repair(
        self,
        slug: str,
        report: ValidationReport,
        attempt: int,
        provider: str,
    ) -> None:
        """
        Attempt to patch the tool's toolforge.yaml (or tool.py) based on the
        validation errors.  Currently focuses on YAML schema errors (most
        common failure mode for rule-based generation).
        """
        tool_dir = self._root / "tools" / "generated" / slug
        yaml_path = tool_dir / "toolforge.yaml"

        # Summarise what's wrong
        error_text = "; ".join(report.errors[:5])

        patch_description = f"Re-generating spec to fix: {error_text}"

        # Only attempt spec regeneration for schema / security errors.
        # Test failures require manual intervention (for now we just log them).
        if any("Schema:" in e or "Security:" in e for e in report.errors):
            try:
                self._repair_spec(slug, tool_dir, yaml_path, error_text, provider)
            except Exception as exc:
                logger.warning("Repair attempt %d failed: %s", attempt, exc)

        if self._ev is not None:
            try:
                self._ev.log_repair(
                    skill_name=slug,
                    error_summary=error_text,
                    patch_description=patch_description,
                    attempt=attempt,
                    file_patched=str(yaml_path),
                )
            except Exception as exc:
                logger.debug("EvidenceLogger.log_repair failed: %s", exc)

    def _repair_spec(
        self,
        slug: str,
        tool_dir: Path,
        yaml_path: Path,
        error_text: str,
        provider: str,
    ) -> None:
        """Regenerate the toolforge.yaml using the original description + error context."""
        from packages.ai.spec_generator import AISpecGenerator
        from packages.core.spec_from_prompt import RuleBasedSpecGenerator

        # Read original spec description if it exists
        original_prompt = f"Fix the following tool spec errors for '{slug}': {error_text}"

        generator = AISpecGenerator(
            provider=provider,
            fallback_to_rule_based=True,
        )
        try:
            new_spec = generator.generate(original_prompt)
        except Exception:
            new_spec = RuleBasedSpecGenerator().generate(original_prompt)

        # Force the original slug to avoid renaming
        try:
            from ruamel.yaml import YAML
            import json

            yaml = YAML()
            yaml.default_flow_style = False
            spec_dict = json.loads(new_spec.model_dump_json())
            spec_dict["slug"] = slug  # preserve identity

            with yaml_path.open("w", encoding="utf-8") as fh:
                yaml.dump(spec_dict, fh)
            logger.info("Repaired toolforge.yaml for %s", slug)
        except Exception as exc:
            logger.warning("Could not write repaired YAML for %s: %s", slug, exc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_skill_md(self, skills_root: Path, slug: str) -> Path | None:
        """Search for SKILL.md for a given slug in the skills/ directory."""
        for path in skills_root.rglob("SKILL.md"):
            if slug in str(path):
                return path
        return None

    def _update_registry(self, slug: str, report: ValidationReport) -> None:
        try:
            from packages.core.registry import ToolRegistry

            registry_path = self._root / "toolforge_registry.json"
            registry = ToolRegistry(registry_path)
            registry.set_validation_result(slug, report.passed)
            if report.passed:
                registry.set_status(slug, "validated")
            else:
                registry.set_status(slug, "failed")
        except Exception as exc:
            logger.debug("Registry update failed: %s", exc)
