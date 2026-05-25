from __future__ import annotations

import re
import zipfile
from pathlib import Path

from skillforge_ai.orchestrator import AIOrchestrator
from skillforge_ai.planner import PlannerResult, SkillPlanner


class ChatRuntime:
    def __init__(
        self,
        workspace_root: Path,
        provider: str = "rule_based",
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._planner = SkillPlanner()
        self._orchestrator = AIOrchestrator(
            workspace_root=self._workspace_root,
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

        if plan.mode == "install_skill":
            from skillforge_ai.commands.install import run_install

            archive_path = self._extract_zip_path(message)
            if archive_path is None:
                return (
                    "Please provide a .zip archive path, "
                    "e.g. 'install /path/to/skill.zip'."
                )
            if not archive_path.exists() or not archive_path.is_file():
                return f"Install failed: file not found: {archive_path}"
            if not zipfile.is_zipfile(archive_path):
                return f"Install failed: not a valid zip file: {archive_path}"

            slug, dest, sha256 = run_install(
                self._workspace_root,
                archive_path,
            )
            return (
                f"Installed '{slug}' to {dest}. "
                f"Archive SHA256: {sha256}"
            )

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

    @staticmethod
    def _extract_zip_path(message: str) -> Path | None:
        # Handle quoted paths first so spaces are preserved.
        quoted = re.search(r"\"([^\"]+\.zip)\"|'([^']+\.zip)'", message)
        if quoted:
            value = quoted.group(1) or quoted.group(2)
            return Path(value).expanduser()

        # Fallback to unquoted path-like token ending in .zip
        unquoted = re.search(r"(?P<path>[^\s]+\.zip)\b", message)
        if unquoted:
            return Path(unquoted.group("path")).expanduser()

        return None

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
