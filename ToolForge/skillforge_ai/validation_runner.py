"""
ValidationRunner for ToolForge with optional repair attempts.

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
# mypy: disable-error-code=import-untyped

# pyright: reportMissingTypeStubs=false

from __future__ import annotations

import logging
import sys
import json
import py_compile
from pathlib import Path
from typing import Any

from skillforge_ai.models import ValidationReport
from skillforge_ai.yaml_utils import dump_yaml

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
        if mcp_dir.exists() and spec is not None:
            mcp_errs = self._run_mcp_validator(spec, tool_dir)
            if mcp_errs:
                report.mcp_ok = False
                report.passed = False
                report.errors.extend(mcp_errs)
            else:
                report.mcp_ok = True
        else:
            report.mcp_ok = None  # not checked

        # 4. Skill files and metadata schema
        canonical_skill_dir = self._root / "skills" / slug
        check_results = {
            "metadata": "failed",
            "skill_md": "failed",
            "readme": "failed",
            "syntax": "failed",
            "tests": "failed",
            "examples": "failed",
            "package": "failed",
        }

        metadata_path = canonical_skill_dir / "metadata.json"
        if canonical_skill_dir.exists():
            skill_md_path = canonical_skill_dir / "SKILL.md"
            if skill_md_path.exists():
                check_results["skill_md"] = "passed"
            else:
                report.passed = False
                report.skill_ok = False
                report.errors.append(f"Skill file missing: {skill_md_path}")

            if metadata_path.exists():
                check_results["metadata"] = "passed"
            else:
                report.passed = False
                report.schema_ok = False
                report.errors.append(f"Metadata file missing: {metadata_path}")

            readme_path = canonical_skill_dir / "README.md"
            if readme_path.exists():
                check_results["readme"] = "passed"
            else:
                report.passed = False
                report.errors.append(f"README missing: {readme_path}")

            skill_tool_dir = canonical_skill_dir / "tool"
            if skill_tool_dir.exists():
                syntax_errors = self._run_python_syntax_check(skill_tool_dir)
                if syntax_errors:
                    report.passed = False
                    report.errors.extend(syntax_errors)
                else:
                    check_results["syntax"] = "passed"

            skill_tests_dir = canonical_skill_dir / "tests"
            if (
                skill_tests_dir.exists()
                and any(skill_tests_dir.glob("test_*.py"))
            ):
                check_results["tests"] = "passed"
            else:
                report.passed = False
                report.tests_ok = False
                report.errors.append(f"Tests missing in {skill_tests_dir}")

            examples_dir = canonical_skill_dir / "examples"
            if examples_dir.exists() and any(examples_dir.iterdir()):
                check_results["examples"] = "passed"
            else:
                report.passed = False
                report.errors.append(f"Examples missing in {examples_dir}")

            if all(
                check_results[name] == "passed"
                for name in (
                    "metadata",
                    "skill_md",
                    "readme",
                    "syntax",
                    "tests",
                    "examples",
                )
            ):
                check_results["package"] = "passed"

        if canonical_skill_dir.exists():
            skill_dir = canonical_skill_dir
        else:
            skill_dir = self._root / "skills" / "generated"
        skill_md = self._find_skill_md(skill_dir, slug)
        if skill_md is not None:
            skill_errs = self._run_skill_validator(skill_md)
            if skill_errs:
                report.skill_ok = False
                report.passed = False
                report.errors.extend(skill_errs)
            else:
                check_results["skill_md"] = "passed"

        if canonical_skill_dir.exists():
            metadata_errs = self._run_skill_schema_validator(metadata_path)
            if metadata_errs:
                report.schema_ok = False
                report.passed = False
                report.errors.extend(metadata_errs)
            else:
                check_results["metadata"] = "passed"

        # 5. Tests
        test_errs, test_warnings = self._run_test_validator(
            tool_dir,
            canonical_skill_dir,
        )
        if test_errs:
            report.tests_ok = False
            report.passed = False
            report.errors.extend(test_errs)
        else:
            check_results["tests"] = "passed"
        report.warnings.extend(test_warnings)

        # 6. Safety analysis
        if spec is not None:
            safety_errs, safety_warnings = self._run_safety_analyzer(
                spec,
                tool_dir,
            )
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

        self._write_skill_validation_report(slug, report, check_results)

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
                (
                    "Validation failed (%d error(s)) — attempting "
                    "AI repair (attempt %d/%d)"
                ),
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
            from packages.validators.security_validator import (
                validate_security,
            )
            violations_raw = validate_security(spec)
            violations = list(violations_raw or [])
            return [f"Security: {v}" for v in violations]
        except Exception as exc:
            violations_attr = getattr(exc, "violations", None)
            if violations_attr:
                return [f"Security: {v}" for v in violations_attr]
            return [f"Security validator error: {exc}"]

    def _run_mcp_validator(self, spec: Any, tool_dir: Path) -> list[str]:
        try:
            from packages.validators.mcp_validator import validate_mcp_server
            mcp_dir = tool_dir / "mcp"
            return validate_mcp_server(spec, mcp_dir)
        except Exception as exc:
            errs = getattr(exc, "errors", None)
            if errs:
                return [f"MCP: {e}" for e in errs]
            return [f"MCP: {exc}"]

    def _run_skill_validator(self, skill_md: Path) -> list[str]:
        try:
            from packages.validators.skill_validator import validate_skill_file
            validate_skill_file(skill_md)
            return []
        except Exception as exc:
            errs = getattr(exc, "errors", None)
            if errs:
                return [f"Skill: {e}" for e in errs]
            return [f"Skill: {exc}"]

    def _run_test_validator(
        self,
        tool_dir: Path,
        canonical_skill_dir: Path,
    ) -> tuple[list[str], list[str]]:
        """Return (errors, warnings). Warnings when no tests found."""
        candidate_root = tool_dir
        tests_dir = tool_dir / "tests"

        skill_tests_dir = canonical_skill_dir / "tests"
        if skill_tests_dir.exists() and any(skill_tests_dir.glob("test_*.py")):
            candidate_root = canonical_skill_dir
            tests_dir = skill_tests_dir

        if not tests_dir.exists() or not any(tests_dir.glob("test_*.py")):
            return [], ["No test files found — skipping pytest"]
        try:
            from packages.validators.test_validator import run_tests
            report = run_tests(candidate_root)
            if not report.all_passed:
                errors = [
                    (
                        f"Tests: {f.get('nodeid', 'unknown')}"
                        f" — {f.get('message', '')}"
                    )
                    for f in report.failures
                ] or [
                    (
                        f"Tests: {report.failed} test(s) failed, "
                        f"{report.errors} error(s)"
                    )
                ]
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

    def _run_skill_schema_validator(self, metadata_path: Path) -> list[str]:
        if not metadata_path.exists():
            return [f"Metadata: Missing metadata.json at {metadata_path}"]
        try:
            from jsonschema import ValidationError, validate

            schema_path = (
                Path(__file__).resolve().parent
                / "schemas"
                / "skill_schema.json"
            )
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            validate(instance=payload, schema=schema)
            return []
        except ValidationError as exc:
            return [f"Metadata: {exc.message}"]
        except Exception as exc:
            return [f"Metadata schema validator error: {exc}"]

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
                self._repair_spec(
                    slug,
                    tool_dir,
                    yaml_path,
                    error_text,
                    provider,
                )
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
        """
        Regenerate toolforge.yaml using original description and error context.
        """
        from packages.ai.spec_generator import AISpecGenerator
        from packages.core.spec_from_prompt import RuleBasedSpecGenerator

        # Read original spec description if it exists
        original_prompt = (
            f"Fix the following tool spec errors for '{slug}': "
            f"{error_text}"
        )

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
            spec_dict = json.loads(new_spec.model_dump_json())
            spec_dict["slug"] = slug  # preserve identity
            dump_yaml(spec_dict, yaml_path)
            logger.info("Repaired toolforge.yaml for %s", slug)
        except Exception as exc:
            logger.warning(
                "Could not write repaired YAML for %s: %s",
                slug,
                exc,
            )

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
            from skillforge_ai.skill_registry import SkillRegistry
            from skillforge_ai.tool_registry import SkillForgeRegistry

            registry_path = self._root / "toolforge_registry.json"
            registry = ToolRegistry(registry_path)
            registry.set_validation_result(slug, report.passed)
            if report.passed:
                registry.set_status(slug, "validated")
            else:
                registry.set_status(slug, "failed")

            skill_registry = SkillRegistry(self._root)
            skill_entry = skill_registry.get(slug)
            if skill_entry is not None:
                skill_entry["validation_status"] = (
                    "passed" if report.passed else "failed"
                )
                skill_entry["status"] = (
                    "validated" if report.passed else "failed"
                )
                skill_registry.upsert(skill_entry)

                tool_registry = SkillForgeRegistry(self._root)
                tool_refs = skill_entry.get("tool_refs", [])
                if isinstance(tool_refs, list):
                    for tool_name in tool_refs:
                        if isinstance(tool_name, str):
                            tool_registry.mark_tool_validated(
                                tool_name,
                                report.passed,
                            )

                tool_registry.mark_tool_validated(
                    f"{slug.replace('-', '_')}_tool",
                    report.passed,
                )
        except Exception as exc:
            logger.debug("Registry update failed: %s", exc)

    def _write_skill_validation_report(
        self,
        slug: str,
        report: ValidationReport,
        checks: dict[str, str] | None = None,
    ) -> None:
        skill_dir = self._root / "skills" / slug
        if not skill_dir.exists():
            return
        out_path = skill_dir / "validation_report.json"
        payload = {
            "skill": slug,
            "status": "passed" if report.passed else "failed",
            "checks": checks
            or {
                "metadata": "passed" if report.schema_ok else "failed",
                "skill_md": "passed" if report.skill_ok else "failed",
                "readme": "failed",
                "syntax": "passed" if report.schema_ok else "failed",
                "tests": "passed" if report.tests_ok else "failed",
                "examples": "failed",
                "package": "passed" if report.safety_ok else "failed",
            },
            "errors": report.errors,
            "warnings": report.warnings,
        }
        out_path.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )

    def _run_python_syntax_check(self, tool_dir: Path) -> list[str]:
        errors: list[str] = []
        for source in tool_dir.rglob("*.py"):
            try:
                py_compile.compile(str(source), doraise=True)
            except py_compile.PyCompileError as exc:
                errors.append(f"Syntax: {source}: {exc.msg}")
        return errors
