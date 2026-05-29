import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
from eval_py.scorer import calculate_overall_score, determine_quality_gate
from types import SimpleNamespace

def make_judge(norm_score):
    return SimpleNamespace(normalized_score=norm_score)

def test_overall_score_basic():
    d = make_judge(0.9)
    c = make_judge(0.8)
    score = calculate_overall_score(d, c)
    assert 0 <= score <= 100
    assert score == int(round(0.5 * 90 + 0.5 * 80)) or score == int(round(0.4 * 90 + 0.4 * 80 + 0.1 * 90 + 0.1 * 80))

def test_overall_score_with_extras():
    d = make_judge(0.8)
    c = make_judge(0.7)
    score = calculate_overall_score(d, c, 60, 70, 80)
    assert 0 <= score <= 100

def test_quality_gate_pass():
    assert determine_quality_gate(85, [], False) == "pass"

def test_quality_gate_fail():
    assert determine_quality_gate(40, [], False) == "fail"
    assert determine_quality_gate(90, ["blocker"], False) == "fail"

def test_quality_gate_warn():
    assert determine_quality_gate(75, [], False) == "warn"
    assert determine_quality_gate(85, [], True) == "warn"

def test_quality_gate_unscored():
    assert determine_quality_gate(None, [], False) == "unscored"
