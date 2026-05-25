from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


PLANNER_MODES = {
    "build_skill",
    "validate_skill",
    "run_skill",
    "repair_skill",
    "inspect_skill",
    "package_skill",
    "install_skill",
    "list_skills",
    "call_tool",
    "validate_workspace",
}


@dataclass(frozen=True)
class PlannerResult:
    intent: str
    skill_name: str
    category: str
    requires_tool_code: bool
    requires_mcp: bool
    permissions: list[str]
    risk_level: str
    files_to_create: list[str]
    validation_plan: list[str]
    mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "skill_name": self.skill_name,
            "category": self.category,
            "requires_tool_code": self.requires_tool_code,
            "requires_mcp": self.requires_mcp,
            "permissions": self.permissions,
            "risk_level": self.risk_level,
            "files_to_create": self.files_to_create,
            "validation_plan": self.validation_plan,
            "mode": self.mode,
        }


class SkillPlanner:
    def classify_mode(self, request: str) -> str:
        text = request.lower()
        if any(
            token in text
            for token in (
                "validate workspace",
                "check workspace",
                "validate all",
            )
        ):
            return "validate_workspace"
        if "validate" in text:
            return "validate_skill"
        if any(
            token in text
            for token in ("call tool", "tools call", "invoke tool")
        ):
            return "call_tool"
        if any(token in text for token in ("repair", "fix", "debug")):
            return "repair_skill"
        if any(token in text for token in ("inspect", "details", "show info")):
            return "inspect_skill"
        if any(token in text for token in ("package", "zip", "bundle")):
            return "package_skill"
        if any(token in text for token in ("install", "import")):
            return "install_skill"
        if any(
            token in text
            for token in ("list skills", "list skill", "list all skills")
        ):
            return "list_skills"
        if any(token in text for token in ("run", "execute")):
            return "run_skill"
        return "build_skill"

    def build_plan(self, request: str) -> PlannerResult:
        mode = self.classify_mode(request)
        skill_name = self._derive_skill_name(request)
        requires_mcp = any(
            token in request.lower()
            for token in ("mcp", "server", "toolathon", "browser")
        )

        if mode != "build_skill":
            intent_specs: dict[str, dict[str, Any]] = {
                "run_skill": {
                    "permissions": ["read_files"],
                    "risk": "low",
                    "validation": ["registry lookup", "runtime smoke"],
                },
                "validate_skill": {
                    "permissions": ["read_files"],
                    "risk": "low",
                    "validation": ["skill validation"],
                },
                "repair_skill": {
                    "permissions": ["read_files", "write_files"],
                    "risk": "low",
                    "validation": [
                        "metadata validation",
                        "syntax validation",
                        "tests",
                    ],
                },
                "inspect_skill": {
                    "permissions": ["read_files"],
                    "risk": "low",
                    "validation": ["registry lookup"],
                },
                "package_skill": {
                    "permissions": ["read_files", "write_files"],
                    "risk": "low",
                    "validation": [
                        "metadata validation",
                        "package validation",
                    ],
                },
                "install_skill": {
                    "permissions": ["read_files", "write_files"],
                    "risk": "medium",
                    "validation": ["archive validation", "registry update"],
                },
                "list_skills": {
                    "permissions": ["read_files"],
                    "risk": "low",
                    "validation": ["registry lookup"],
                },
                "call_tool": {
                    "permissions": ["read_files"],
                    "risk": "medium",
                    "validation": ["tool registry lookup", "mcp smoke"],
                },
                "validate_workspace": {
                    "permissions": ["read_files"],
                    "risk": "low",
                    "validation": ["workspace validation"],
                },
            }
            spec = intent_specs.get(mode, intent_specs["validate_workspace"])
            return PlannerResult(
                intent=mode,
                skill_name=skill_name,
                category="generated",
                requires_tool_code=False,
                requires_mcp=requires_mcp,
                permissions=spec["permissions"],
                risk_level=spec["risk"],
                files_to_create=[],
                validation_plan=spec["validation"],
                mode=mode,
            )

        return PlannerResult(
            intent="build_skill",
            skill_name=skill_name,
            category=self._infer_category(request),
            requires_tool_code=True,
            requires_mcp=requires_mcp,
            permissions=["read_files", "write_files"],
            risk_level="low",
            files_to_create=[
                "SKILL.md",
                "metadata.json",
                "README.md",
                "tool/main.py",
                f"tests/test_{skill_name.replace('-', '_')}.py",
            ],
            validation_plan=[
                "metadata validation",
                "python syntax",
                "unit tests",
                "package validation",
            ],
            mode=mode,
        )

    @staticmethod
    def _derive_skill_name(request: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", request.lower()).strip("-")
        for common in (
            "build-me-a-skill-that",
            "make-a-skill-that",
            "create-a-skill-that",
        ):
            if normalized.startswith(common):
                normalized = normalized[len(common) :].strip("-")
                break
        if normalized in {
            "repair",
            "run",
            "execute",
            "list",
            "inspect",
            "validate",
            "package",
            "install",
            "call-tool",
            "call",
        }:
            return "generated-skill"
        if "csv" in normalized and "clean" in normalized:
            return "csv-cleaner"
        if not normalized:
            return "generated-skill"
        return "-".join(normalized.split("-")[:4])

    @staticmethod
    def _infer_category(request: str) -> str:
        text = request.lower()
        if any(token in text for token in ("web", "url", "scrape", "browser")):
            return "browser"
        if any(token in text for token in ("pdf", "doc", "document")):
            return "documents"
        if any(token in text for token in ("csv", "json", "table", "data")):
            return "data"
        if any(
            token in text
            for token in ("code", "python", "typescript", "lint", "compile")
        ):
            return "coding"
        if any(
            token in text
            for token in ("calendar", "email", "todo", "task", "productivity")
        ):
            return "productivity"
        if any(
            token in text
            for token in ("automation", "workflow", "pipeline", "batch")
        ):
            return "automation"
        if any(
            token in text for token in ("audio", "video", "image", "media")
        ):
            return "media"
        if any(
            token in text
            for token in ("research", "search", "summarize", "analysis")
        ):
            return "research"
        return "custom"
