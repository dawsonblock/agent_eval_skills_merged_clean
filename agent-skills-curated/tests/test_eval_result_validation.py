import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..")))
import pytest
import tempfile
import os
import json
from eval_py.models import SkillEvaluationResult, DescriptionJudgeResult, ContentJudgeResult
from eval_py.io import save_json, load_json

def make_valid_result():
    d = DescriptionJudgeResult(
        rationale="Good.", clarity=80, specificity=80, usefulness=80, normalized_score=0.8
    )
    c = ContentJudgeResult(
        rationale="Solid.", completeness=80, actionability=80, technical_quality=80, documentation_quality=80, normalized_score=0.8
    )
    return SkillEvaluationResult(
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

def test_save_and_load_json():
    result = make_valid_result()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "result.json")
        # Use model_dump for Pydantic v2+ compatibility
        save_json(result.model_dump(), path)
        loaded = load_json(path)
        assert loaded["skill_name"] == "TestSkill"
        # Validate with Pydantic
        SkillEvaluationResult(**loaded)

def test_invalid_json_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "bad.json")
        with open(path, "w") as f:
            f.write("not a json")
        with pytest.raises(Exception):
            load_json(path)
