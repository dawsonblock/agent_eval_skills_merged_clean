"""
Tests for skillforge_ai.models — Pydantic models and enums.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from skillforge_ai.models import (
    InputSpec,
    IntentResult,
    Mode,
    OrchestratorState,
    OutputSpec,
    Plan,
    PlanStep,
    RiskLevel,
    SkillManifest,
    ToolCallRequest,
    ValidationReport,
)


class TestRiskLevel:
    def test_values_exist(self):
        assert RiskLevel.SAFE
        assert RiskLevel.APPROVAL_REQUIRED
        assert RiskLevel.BLOCKED


class TestMode:
    def test_all_modes_exist(self):
        for mode_name in ("BUILD", "RUN", "REPAIR", "INSPECT", "PACKAGE", "BENCHMARK", "ADMIN", "UNKNOWN"):
            assert hasattr(Mode, mode_name)


class TestSkillManifest:
    def test_minimal_valid(self):
        m = SkillManifest(
            name="csv-cleaner",
            description="Cleans CSV files",
            category="data",
        )
        assert m.name == "csv-cleaner"
        assert m.category == "data"
        assert m.risk_level == "low"

    def test_with_inputs_outputs(self):
        m = SkillManifest(
            name="csv-cleaner",
            description="Cleans CSV files",
            category="data",
            inputs=[InputSpec(name="input_path", type="str", required=True, description="CSV file path")],
            outputs=[OutputSpec(name="result", type="str", description="Cleaned CSV path")],
        )
        assert len(m.inputs) == 1
        assert len(m.outputs) == 1

    def test_mcp_servers_defaults_empty(self):
        m = SkillManifest(name="x", description="y", category="misc")
        assert m.mcp_servers == []


class TestValidationReport:
    def test_defaults(self):
        r = ValidationReport(slug="csv-cleaner", passed=True)
        assert r.slug == "csv-cleaner"
        assert r.passed is True
        assert r.errors == []
        assert r.warnings == []
        assert r.attempt == 1

    def test_schema_ok_defaults_true(self):
        r = ValidationReport(slug="x", passed=True)
        assert r.schema_ok is True
        assert r.security_ok is True
        assert r.tests_ok is True
        assert r.safety_ok is True

    def test_mcp_ok_nullable(self):
        r = ValidationReport(slug="x", passed=True, mcp_ok=None)
        assert r.mcp_ok is None


class TestToolCallRequest:
    def test_minimal(self):
        req = ToolCallRequest(tool="mcp", action="clean_csv")
        assert req.tool == "mcp"
        assert req.arguments == {}

    def test_with_arguments(self):
        req = ToolCallRequest(tool="mcp", action="clean_csv", arguments={"path": "/tmp/a.csv"})
        assert req.arguments["path"] == "/tmp/a.csv"


class TestIntentResult:
    def test_defaults(self):
        ir = IntentResult(mode=Mode.BUILD, description="build a tool")
        assert ir.skill_name is None
        assert ir.parameters == {}

    def test_with_skill_name(self):
        ir = IntentResult(mode=Mode.INSPECT, description="inspect csv-cleaner", skill_name="csv-cleaner")
        assert ir.skill_name == "csv-cleaner"


class TestOrchestratorState:
    def test_defaults(self):
        state = OrchestratorState(mode=Mode.UNKNOWN)
        assert state.current_skill is None
        assert state.last_error is None


class TestPlan:
    def test_plan_with_steps(self):
        plan = Plan(
            intent="Build a CSV cleaner",
            skill_name="csv-cleaner",
            mode=Mode.BUILD,
            steps=[
                PlanStep(step_id=0, description="Generate spec", action="generate_spec"),
                PlanStep(step_id=1, description="Scaffold tool", action="scaffold_tool"),
            ],
        )
        assert len(plan.steps) == 2
        assert plan.steps[0].step_id == 0
