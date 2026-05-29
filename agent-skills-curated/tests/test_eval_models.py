import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
from eval_py.models import DescriptionJudgeResult, ContentJudgeResult, SkillEvaluationResult
from datetime import datetime, timezone

def test_description_judge_result_valid():
    d = DescriptionJudgeResult(
        rationale="Clear and specific.",
        clarity=90,
        specificity=85,
        usefulness=95,
        normalized_score=0.9,
        strengths=["Concise"],
        weaknesses=[],
        suggestions=["Add more examples"]
    )
    assert d.clarity == 90
    assert d.normalized_score == 0.9

def test_content_judge_result_valid():
    c = ContentJudgeResult(
        rationale="Complete and actionable.",
        completeness=92,
        actionability=88,
        technical_quality=90,
        documentation_quality=85,
        normalized_score=0.88,
        missing_elements=[],
        strengths=["Well documented"],
        weaknesses=["Minor typos"]
    )
    assert c.completeness == 92
    assert c.technical_quality == 90

def test_skill_evaluation_result_valid():
    d = DescriptionJudgeResult(
        rationale="Good.", clarity=80, specificity=80, usefulness=80, normalized_score=0.8
    )
    c = ContentJudgeResult(
        rationale="Solid.", completeness=80, actionability=80, technical_quality=80, documentation_quality=80, normalized_score=0.8
    )
    s = SkillEvaluationResult(
        skill_name="TestSkill",
        category="TestCategory",
        skill_path="skills/test/path",
        description_judge=d,
        content_judge=c,
        overall_score=80,
        quality_gate="pass",
        confidence=0.95,
        judge_provider="test",
        judge_model="test-model"
    )
    assert s.skill_name == "TestSkill"
    assert s.quality_gate == "pass"
    assert isinstance(s.evaluated_at, datetime)
    assert s.evaluated_at.tzinfo == timezone.utc
