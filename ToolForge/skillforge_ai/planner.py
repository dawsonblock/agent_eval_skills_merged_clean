from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


PLANNER_MODES = {
    "build_skill",
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
        if any(token in text for token in ("validate", "check workspace")):
            return "validate_workspace"
        if any(token in text for token in ("repair", "fix", "debug")):
            return "repair_skill"
        if any(token in text for token in ("inspect", "details", "show info")):
            return "inspect_skill"
        if any(token in text for token in ("package", "zip", "bundle")):
            return "package_skill"
        if any(token in text for token in ("install", "import")):
            return "install_skill"
        if any(token in text for token in ("list skills", "list")):
            return "list_skills"
        if any(token in text for token in ("call tool", "tool call")):
            return "call_tool"
        if any(token in text for token in ("run", "execute")):
            return "run_skill"
        return "build_skill"

    def build_plan(self, request: str) -> PlannerResult:
        mode = self.classify_mode(request)
        skill_name = self._derive_skill_name(request)
        requires_mcp = any(token in request.lower() for token in ("mcp", "server", "toolathon", "browser"))

        if mode != "build_skill":
            return PlannerResult(
                intent=mode,
                skill_name=skill_name,
                category="generated",
                requires_tool_code=False,
                requires_mcp=requires_mcp,
                permissions=["read_files"],
                risk_level="low",
                files_to_create=[],
                validation_plan=["workspace validation"],
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
                "python syntax",
                "unit tests",
                "skill schema validation",
                "package validation",
            ],
            mode=mode,
        )

    @staticmethod
    def _derive_skill_name(request: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", request.lower()).strip("-")
        for common in ("build-me-a-skill-that", "make-a-skill-that", "create-a-skill-that"):
            if normalized.startswith(common):
                normalized = normalized[len(common):].strip("-")
                break
        if "csv" in normalized and "clean" in normalized:
            return "csv-cleaner"
        if not normalized:
            return "generated-skill"
        return "-".join(normalized.split("-")[:4])

    @staticmethod
    def _infer_category(request: str) -> str:
        text = request.lower()
        if any(token in text for token in ("pdf", "doc", "document")):
            return "documents"
        if any(token in text for token in ("csv", "json", "table", "data")):
            return "data"
        if any(token in text for token in ("web", "url", "scrape", "browser")):
            return "web"
        return "general"
