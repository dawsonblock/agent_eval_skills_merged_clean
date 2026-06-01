"""
Eval runner — iterates a tool's eval cases, invokes the tool, and scores results.
"""

from __future__ import annotations

import json
import re
import jsonschema
from dataclasses import dataclass, field
from pathlib import Path

from packages.core.tool_spec import EvalCase, EvalCriterion, EvalCriterionType, ToolSpec
from packages.runners.tool_runner import ToolRunResult, run_tool


@dataclass
class EvalResult:
    case_id: str
    passed: bool
    score: float  # 0.0 – 1.0
    details: str
    error: str = ""


@dataclass
class EvalReport:
    tool_slug: str
    baseline_pass_rate: float = field(default=0.8)
    results: list[EvalResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

    @property
    def overall_pass(self) -> bool:
        return self.pass_rate >= self.baseline_pass_rate


def _score_result(
    case: EvalCase,
    result: ToolRunResult,
    global_criteria: list[EvalCriterion],
) -> tuple[bool, float, str]:
    """
    Score a single ToolRunResult against eval criteria.
    Checks case-specific criteria first, then global criteria.
    Returns (passed, score, details).
    """
    if not result.success:
        return False, 0.0, f"Tool failed: exit_code={result.exit_code}, error={result.error[:100]}"

    # Case-specific criteria override global criteria.
    case_criteria = case.criteria or global_criteria

    if not case_criteria:
        # No criteria → pass/fail based on exit code only
        return result.success, 1.0 if result.success else 0.0, "No criteria specified"

    scores: list[float] = []
    detail_parts: list[str] = []

    for criterion in case_criteria:
        weight = criterion.weight

        if criterion.type == EvalCriterionType.NO_ERROR:
            # Pass when the tool exits cleanly; stderr warnings do not count
            # as errors since many well-behaved Python tools write to stderr.
            ok = result.exit_code == 0
            scores.append(weight if ok else 0.0)
            detail_parts.append(f"{criterion.name}: no_error {'✓' if ok else '✗'}")

        elif criterion.type == EvalCriterionType.EXACT_MATCH:
            if case.expected_output is not None:
                ok = result.output.strip() == str(case.expected_output).strip()
                scores.append(weight if ok else 0.0)
                detail_parts.append(f"{criterion.name}: exact_match {'✓' if ok else '✗'}")
            else:
                scores.append(0.0)
                detail_parts.append(f"{criterion.name}: exact_match (no expected output)")

        elif criterion.type == EvalCriterionType.CONTAINS:
            if criterion.target is not None:
                ok = str(criterion.target) in result.output
                scores.append(weight if ok else 0.0)
                detail_parts.append(
                    f"{criterion.name}: contains '{str(criterion.target)[:30]}' {'✓' if ok else '✗'}"
                )
            else:
                raise ValueError(
                    f"Criterion '{criterion.name}' has type CONTAINS but no target specified"
                )

        elif criterion.type == EvalCriterionType.REGEX_MATCH:
            if criterion.target is not None:
                try:
                    ok = bool(re.search(str(criterion.target), result.output))
                    scores.append(weight if ok else 0.0)
                    detail_parts.append(f"{criterion.name}: regex_match {'✓' if ok else '✗'}")
                except re.error as e:
                    scores.append(0.0)
                    detail_parts.append(f"{criterion.name}: regex_match (invalid pattern: {e})")
            else:
                raise ValueError(
                    f"Criterion '{criterion.name}' has type REGEX_MATCH but no target specified"
                )

        elif criterion.type == EvalCriterionType.JSON_SCHEMA:
            try:
                parsed_output = json.loads(result.output)
                if criterion.target is not None and isinstance(criterion.target, dict):
                    try:
                        jsonschema.validate(instance=parsed_output, schema=criterion.target)
                        scores.append(weight)
                        detail_parts.append(f"{criterion.name}: json_schema ✓ (schema valid)")
                    except jsonschema.ValidationError as schema_err:
                        scores.append(0.0)
                        detail_parts.append(
                            f"{criterion.name}: json_schema ✗ ({schema_err.message[:80]})"
                        )
                else:
                    scores.append(weight)
                    detail_parts.append(f"{criterion.name}: json_schema ✓ (valid JSON)")
            except (json.JSONDecodeError, TypeError):
                scores.append(0.0)
                detail_parts.append(f"{criterion.name}: json_schema ✗ (invalid JSON)")

        elif criterion.type == EvalCriterionType.PERFORMANCE:
            # Passes if elapsed_ms < max_duration_ms (default 5000)
            threshold_ms = criterion.max_duration_ms or 5000.0
            ok = result.elapsed_ms < threshold_ms
            scores.append(weight if ok else 0.0)
            detail_parts.append(
                f"{criterion.name}: {result.elapsed_ms:.0f}ms < {threshold_ms:.0f}ms {'✓' if ok else '✗'}"
            )

        elif criterion.type == EvalCriterionType.SEMANTIC_SIMILARITY:
            # Requires external LLM judge — skip with neutral score
            scores.append(weight * 0.5)
            detail_parts.append(f"{criterion.name}: semantic_similarity (skipped, requires judge)")

        elif criterion.type == EvalCriterionType.CUSTOM_SCRIPT:
            # Would require running a custom evaluator script
            scores.append(weight * 0.5)
            detail_parts.append(f"{criterion.name}: custom_script (skipped, not implemented)")

        else:
            scores.append(weight * 0.5)
            detail_parts.append(f"{criterion.name}: {criterion.type.value} (skipped)")

    total_weight = sum(c.weight for c in case_criteria)
    final_score = sum(scores) / total_weight if total_weight > 0 else 0.0
    passed = final_score >= 0.5
    return passed, round(final_score, 4), "; ".join(detail_parts)


def _check_expected_files(tool_dir: Path, case) -> tuple[bool, str]:
    if not getattr(case, "expected_files", None):
        return True, ""
    failures: list[str] = []
    for expected in case.expected_files:
        path = (tool_dir / expected.path).resolve(strict=False)
        exists = path.exists()
        if expected.should_exist and not exists:
            failures.append(f"Expected file missing: {expected.path}")
        if not expected.should_exist and exists:
            failures.append(f"Unexpected file exists: {expected.path}")
    if failures:
        return False, "; ".join(failures)
    return True, ""


def _load_eval_cases(
    spec: ToolSpec,
    tool_dir: Path,
) -> tuple[list[EvalCase], list[EvalResult]]:
    """Load eval cases from tool-local eval files, with YAML fallback."""
    case_dir = tool_dir / "evals" / "cases"
    load_failures: list[EvalResult] = []

    if case_dir.exists():
        loaded_cases: list[EvalCase] = []
        for case_file in sorted(case_dir.glob("*.json")):
            try:
                raw = json.loads(case_file.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and "id" not in raw:
                    raw["id"] = case_file.stem
                loaded_cases.append(EvalCase.model_validate(raw))
            except Exception as exc:  # noqa: BLE001
                load_failures.append(
                    EvalResult(
                        case_id=case_file.stem,
                        passed=False,
                        score=0.0,
                        details="",
                        error=f"Failed to load eval case file {case_file.name}: {exc}",
                    )
                )
        if loaded_cases:
            return loaded_cases, load_failures

    if spec.eval and spec.eval.cases:
        return list(spec.eval.cases), load_failures

    return [], load_failures


def run_evals(
    spec: ToolSpec,
    tool_dir: Path,
    timeout_s: float = 30.0,
) -> EvalReport:
    """
    Run all eval cases defined in *spec.eval* and return an EvalReport.
    """
    report = EvalReport(
        tool_slug=spec.slug, baseline_pass_rate=spec.eval.baseline_pass_rate if spec.eval else 0.8
    )

    if not spec.eval:
        return report

    cases, load_failures = _load_eval_cases(spec, tool_dir)
    if load_failures:
        report.results.extend(load_failures)
    if not cases:
        return report

    global_criteria = spec.eval.criteria or []

    for case in cases:
        try:
            tool_result = run_tool(
                spec=spec,
                tool_dir=tool_dir,
                inputs=case.inputs,
                timeout_s=timeout_s,
            )
            expected_success = getattr(case, "expected_success", True)

            if expected_success:
                passed, score, details = _score_result(
                    case,
                    tool_result,
                    global_criteria,
                )
                if passed and case.expected_output_contains:
                    if case.expected_output_contains not in tool_result.output:
                        passed = False
                        score = 0.0
                        details = f"Expected output to contain '{case.expected_output_contains}'"
                if passed:
                    files_ok, file_details = _check_expected_files(tool_dir, case)
                    if not files_ok:
                        passed = False
                        score = 0.0
                        details = file_details
            else:
                error_text = (tool_result.error or "") + "\n" + (tool_result.output or "")
                if tool_result.success:
                    passed = False
                    score = 0.0
                    details = "Case expected failure, but tool succeeded"
                elif (
                    case.expected_error_contains and case.expected_error_contains not in error_text
                ):
                    passed = False
                    score = 0.0
                    details = (
                        "Case failed as expected, but error text did not contain "
                        f"'{case.expected_error_contains}'"
                    )
                else:
                    passed = True
                    score = 1.0
                    details = "Expected failure observed"

            report.results.append(
                EvalResult(
                    case_id=case.id,
                    passed=passed,
                    score=score,
                    details=details,
                )
            )
        except Exception as exc:  # noqa: BLE001
            report.results.append(
                EvalResult(
                    case_id=case.id,
                    passed=False,
                    score=0.0,
                    details="",
                    error=str(exc),
                )
            )

    return report
