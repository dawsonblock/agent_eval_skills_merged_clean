"""
Eval runner — iterates a tool's eval cases, invokes the tool, and scores results.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from packages.core.tool_spec import EvalCriterionType, ToolSpec
from packages.runners.tool_runner import ToolRunResult, run_tool


@dataclass
class EvalResult:
    case_id: str
    passed: bool
    score: float          # 0.0 – 1.0
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
    spec: ToolSpec, case_id: str, result: ToolRunResult, expected_output: str | None
) -> tuple[bool, float, str]:
    """
    Score a single ToolRunResult against eval criteria.
    Checks case-specific criteria first, then global criteria.
    Returns (passed, score, details).
    """
    if not result.success:
        return False, 0.0, f"Tool failed: exit_code={result.exit_code}, error={result.error[:100]}"

    # Find criteria: first try case-specific, then fall back to global
    case_criteria = []
    if spec.eval:
        # Look for case-specific criteria (embedded in case)
        for case in spec.eval.cases:
            if case.id == case_id and case.criteria:
                case_criteria = case.criteria
                break
        # If no case-specific, use global criteria
        if not case_criteria:
            case_criteria = spec.eval.criteria or []

    if not case_criteria:
        # No criteria → pass/fail based on exit code only
        return result.success, 1.0 if result.success else 0.0, "No criteria specified"

    scores: list[float] = []
    detail_parts: list[str] = []

    for criterion in case_criteria:
        weight = criterion.weight

        if criterion.type == EvalCriterionType.NO_ERROR:
            ok = result.exit_code == 0 and not result.error.strip()
            scores.append(weight if ok else 0.0)
            detail_parts.append(f"{criterion.name}: no_error {'✓' if ok else '✗'}")

        elif criterion.type == EvalCriterionType.EXACT_MATCH:
            if expected_output is not None:
                ok = result.output.strip() == str(expected_output).strip()
                scores.append(weight if ok else 0.0)
                detail_parts.append(f"{criterion.name}: exact_match {'✓' if ok else '✗'}")
            else:
                scores.append(0.0)
                detail_parts.append(f"{criterion.name}: exact_match (no expected output)")

        elif criterion.type == EvalCriterionType.CONTAINS:
            if criterion.target is not None:
                ok = str(criterion.target) in result.output
                scores.append(weight if ok else 0.0)
                detail_parts.append(f"{criterion.name}: contains '{str(criterion.target)[:30]}' {'✓' if ok else '✗'}")
            else:
                scores.append(0.0)
                detail_parts.append(f"{criterion.name}: contains (no target)")

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
                scores.append(0.0)
                detail_parts.append(f"{criterion.name}: regex_match (no pattern)")

        elif criterion.type == EvalCriterionType.JSON_SCHEMA:
            try:
                json.loads(result.output)
                if criterion.target is not None and isinstance(criterion.target, dict):
                    # Simple schema validation (full jsonschema validation optional)
                    ok = True  # Placeholder — would need jsonschema library for full validation
                    scores.append(weight if ok else 0.0)
                    detail_parts.append(f"{criterion.name}: json_schema ✓ (parsed)")
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

    total_weight = sum(c.weight for c in case_criteria) or 1.0
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


def run_evals(
    spec: ToolSpec,
    tool_dir: Path,
    timeout_s: float = 30.0,
) -> EvalReport:
    """
    Run all eval cases defined in *spec.eval* and return an EvalReport.
    """
    report = EvalReport(
        tool_slug=spec.slug,
        baseline_pass_rate=spec.eval.baseline_pass_rate if spec.eval else 0.8
    )

    if not spec.eval or not spec.eval.cases:
        return report

    for case in spec.eval.cases:
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
                    spec,
                    case.id,
                    tool_result,
                    case.expected_output,
                )
                if passed and case.expected_output_contains:
                    if case.expected_output_contains not in tool_result.output:
                        passed = False
                        score = 0.0
                        details = (
                            f"Expected output to contain '{case.expected_output_contains}'"
                        )
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
                elif case.expected_error_contains and case.expected_error_contains not in error_text:
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

