from __future__ import annotations

import re
from pathlib import Path

from skillforge_ai.orchestrator import AIOrchestrator
from skillforge_ai.planner import PlannerResult, SkillPlanner


class ChatRuntime:
    def __init__(
        self,
        workspace_root: Path,
        provider: str = "rule_based",
    ) -> None:
        self._planner = SkillPlanner()
        self._orchestrator = AIOrchestrator(
            workspace_root=workspace_root,
            provider=provider,
        )

    def handle_message(self, message: str) -> dict[str, str]:
        plan = self._planner.build_plan(message)
        response = self._dispatch_plan(plan, message)
        return {
            "mode": plan.mode,
            "skill_name": plan.skill_name,
            "response": response,
        }

    def _dispatch_plan(self, plan: PlannerResult, message: str) -> str:
        """
        Route planner-intent modes to deterministic orchestrator prompts.
        """
        if plan.mode == "list_skills":
            return self._orchestrator.chat("list all skills")

        if plan.mode == "validate_workspace":
            return self._orchestrator.chat("doctor workspace")

        if plan.mode == "call_tool":
            slug = self._extract_skill_slug(message, fallback=plan.skill_name)
            if not slug:
                return (
                    "Please specify a tool name, "
                    "e.g. 'call tool csv-cleaner'."
                )
            return self._orchestrator.chat(f"run {slug}")

        return self._orchestrator.chat(message)

    @staticmethod
    def _extract_skill_slug(message: str, fallback: str = "") -> str:
        pattern = r"\b([a-z][a-z0-9-]{1,40})\b"
        for slug_match in re.finditer(pattern, message.lower()):
            candidate = slug_match.group(1)
            if candidate not in {"call", "tool", "run", "execute"}:
                return candidate

        if fallback and fallback != "generated-skill":
            return fallback

        return ""

    def run_loop(self) -> None:
        while True:
            try:
                message = input("skillforge-chat> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break
            if not message:
                continue
            if message.lower() in {"quit", "exit", "q"}:
                print("Goodbye.")
                break
            result = self.handle_message(message)
            print(f"[{result['mode']}] {result['response']}")
