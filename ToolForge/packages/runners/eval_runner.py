"""
Eval runner — iterates a tool's eval cases, invokes the tool, and scores results.
"""
from __future__ import annotations

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
    results: list[EvalResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

    @property
    def overall_pass(self) -> bool:
        return self.pass_rate >= (self._baseline or 0.8)

    # Stash baseline so overall_pass can see it
    _baseline: float = 0.8


def _score_result(
    spec: ToolSpec, result: ToolRunResult, expected_output: str | None
) -> tuple[bool, float, str]:
    """
    Score a single ToolRunResult against the eval criteria.
    Returns (passed, score, details).
    """
    if not result.success:
        return False, 0.0, f"Tool exited with code {result.exit_code}: {result.error}"

    criteria = spec.eval.criteria if spec.eval else []
    if not criteria:
        # No criteria → pass/fail based on exit code only
        return result.success, 1.0 if result.success else 0.0, ""

    scores: list[float] = []
    detail_parts: list[str] = []

    for criterion in criteria:
        weight = criterion.weight

        if criterion.type == EvalCriterionType.EXACT_MATCH:
            if expected_output is not None and result.output.strip() == str(expected_output).strip():
                scores.append(weight)
                detail_parts.append(f"{criterion.name}: exact match ✓")
            else:
                scores.append(0.0)
                detail_parts.append(f"{criterion.name}: exact match ✗")

        elif criterion.type == EvalCriterionType.CONTAINS:
            if expected_output is not None and str(expected_output) in result.output:
                scores.append(weight)
                detail_parts.append(f"{criterion.name}: contains ✓")
            else:
                scores.append(0.0)
                detail_parts.append(f"{criterion.name}: contains ✗")

        elif criterion.type == EvalCriterionType.NO_ERROR:
            ok = result.exit_code == 0 and not result.error.strip()
            scores.append(weight if ok else 0.0)
            detail_parts.append(f"{criterion.name}: no error {'✓' if ok else '✗'}")

        elif criterion.type == EvalCriterionType.PERFORMANCE:
            # Passes if elapsed_ms < threshold_ms (default 5000)
            threshold_ms = float(criterion.threshold or 5000)
            ok = result.elapsed_ms < threshold_ms
            scores.append(weight if ok else 0.0)
            detail_parts.append(
                f"{criterion.name}: {result.elapsed_ms:.0f}ms < {threshold_ms:.0f}ms {'✓' if ok else '✗'}"
            )

        else:
            # SEMANTIC and RUBRIC require external judge — skip with neutral score
            scores.append(weight * 0.5)
            detail_parts.append(f"{criterion.name}: skipped (requires judge)")

    total_weight = sum(c.weight for c in criteria) or 1.0
    final_score = sum(scores) / total_weight
    passed = final_score >= 0.5
    return passed, round(final_score, 4), "; ".join(detail_parts)


def run_evals(
    spec: ToolSpec,
    tool_dir: Path,
    timeout_s: float = 30.0,
) -> EvalReport:
    """
    Run all eval cases defined in *spec.eval* and return an EvalReport.
    """
    report = EvalReport(tool_slug=spec.slug)

    if not spec.eval or not spec.eval.cases:
        return report

    report._baseline = spec.eval.baseline_pass_rate

    for case in spec.eval.cases:
        try:
            tool_result = run_tool(
                spec=spec,
                tool_dir=tool_dir,
                inputs=case.inputs,
                timeout_s=timeout_s,
            )
            passed, score, details = _score_result(
                spec, tool_result, case.expected_output
            )
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
