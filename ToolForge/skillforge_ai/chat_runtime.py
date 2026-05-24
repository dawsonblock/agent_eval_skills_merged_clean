from __future__ import annotations

from pathlib import Path

from skillforge_ai.orchestrator import AIOrchestrator
from skillforge_ai.planner import SkillPlanner


class ChatRuntime:
    def __init__(self, workspace_root: Path, provider: str = "rule_based") -> None:
        self._planner = SkillPlanner()
        self._orchestrator = AIOrchestrator(workspace_root=workspace_root, provider=provider)

    def handle_message(self, message: str) -> dict[str, str]:
        plan = self._planner.build_plan(message)
        response = self._orchestrator.chat(message)
        return {
            "mode": plan.mode,
            "skill_name": plan.skill_name,
            "response": response,
        }

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
