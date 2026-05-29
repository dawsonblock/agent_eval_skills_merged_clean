import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
from eval_py.prompts import HUMAN_TEMPLATE

def test_human_template_contains_rubric():
    assert "Rubric" in HUMAN_TEMPLATE
    assert "clarity" in HUMAN_TEMPLATE
    assert "completeness" in HUMAN_TEMPLATE
    assert "Do not include step-by-step reasoning" in HUMAN_TEMPLATE
