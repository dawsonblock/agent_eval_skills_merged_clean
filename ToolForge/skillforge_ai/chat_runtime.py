from __future__ import annotations
# mypy: disable-error-code=import-untyped

import json
import re
import zipfile
from pathlib import Path
from skillforge_ai.orchestrator import AIOrchestrator
from skillforge_ai.planner import PlannerResult, SkillPlanner
from skillforge_ai.response_cleaner import clean_response_text
from skillforge_ai.skill_registry import SkillRegistry
from skillforge_ai.tool_registry import SkillForgeRegistry


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
        self._provider = provider
        self._current_skill: str = ""

    def handle_message(self, message: str) -> dict[str, str]:
        plan = self._planner.build_plan(message)
        response = self._dispatch_plan(plan, message)
        return {
            "mode": plan.mode,
            "skill_name": plan.skill_name,
            "response": clean_response_text(response),
        }

    def _dispatch_plan(self, plan: PlannerResult, message: str) -> str:
        """
        Route planner-intent modes to deterministic orchestrator prompts.
        """
        if plan.mode == "build_skill":
            from skillforge_ai.commands.create import run_create

            _, manifest = run_create(
                workspace_root=self._workspace_root,
                prompt=message,
                provider=self._provider,
                name=(
                    plan.skill_name
                    if plan.skill_name != "generated-skill"
                    else None
                ),
            )
            self._current_skill = manifest.name
            return f"Built skill '{manifest.name}'."

        if plan.mode == "validate_skill":
            from skillforge_ai.commands.validate import run_validate

            slug = self._resolve_skill_slug(message, fallback=plan.skill_name)
            if not slug:
                return "Please specify which skill to validate."
            report = run_validate(
                workspace_root=self._workspace_root,
                slug=slug,
                repair=False,
                provider=self._provider,
            )
            self._current_skill = slug
            status = "passed" if report.passed else "failed"
            return f"Validation {status} for '{slug}'."

        if plan.mode == "run_skill":
            from skillforge_ai.commands.run import run_skill

            slug = self._resolve_skill_slug(message, fallback=plan.skill_name)
            if not slug:
                return "Please specify which skill to run."
            input_path = self._extract_input_file_path(message)
            inputs: dict[str, str] = {}
            if input_path is not None:
                inputs["input_path"] = str(input_path)
            result = run_skill(self._workspace_root, slug, inputs)
            self._current_skill = slug
            if result.exit_code != 0:
                return f"Run failed for '{slug}': {result.error}"
            return f"Run passed for '{slug}': {result.output.strip()}"

        if plan.mode == "package_skill":
            from skillforge_ai.commands.package import run_package

            slug = self._resolve_skill_slug(message, fallback=plan.skill_name)
            if not slug:
                return "Please specify which skill to package."
            package_path, sha = run_package(
                self._workspace_root, slug, output=None
            )
            self._current_skill = slug
            return f"Packaged '{slug}' at {package_path} (sha256={sha})."

        if plan.mode == "list_skills":
            return self._orchestrator.chat("list all skills")

        if plan.mode == "validate_workspace":
            return self._orchestrator.chat("doctor workspace")

        if plan.mode == "call_tool":
            slug = self._extract_skill_slug(message, fallback=plan.skill_name)
            if not slug:
                return (
                    "Please specify a tool name, e.g. 'call tool csv-cleaner'."
                )
            return self._orchestrator.chat(f"run {slug}")

        if plan.mode == "inspect_skill" and "tool" in message.lower():
            slug = self._resolve_skill_slug(message, fallback=plan.skill_name)
            if not slug:
                return "Please specify which skill to inspect."
            skill_entry = SkillRegistry(self._workspace_root).get(slug)
            tool_entries = SkillForgeRegistry(
                self._workspace_root
            ).list_registered_tools()
            if skill_entry is None:
                return f"Skill '{slug}' is not registered."
            refs = skill_entry.get("tool_refs", [])
            controlled = [t for t in tool_entries if t.get("name") in refs]
            if not controlled:
                return f"Skill '{slug}' controls no registered tools."
            return json.dumps({"skill": slug, "tools": controlled}, indent=2)

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
            return f"Installed '{slug}' to {dest}. Archive SHA256: {sha256}"

        return self._orchestrator.chat(message)

    def _resolve_skill_slug(self, message: str, fallback: str = "") -> str:
        lower = message.lower()
        if self._current_skill and any(
            token in lower
            for token in (
                " that skill",
                "validate that skill",
                "run it",
                "package it",
                "show me what tools it controls",
            )
        ):
            return self._current_skill

        resolved = self._extract_skill_slug(message, fallback=fallback)
        if resolved and resolved != "generated-skill":
            return resolved
        if self._current_skill:
            return self._current_skill
        return ""

    @staticmethod
    def _extract_input_file_path(message: str) -> Path | None:
        quoted = re.search(r'"([^"]+)"|\'([^\']+)\'', message)
        if quoted:
            value = quoted.group(1) or quoted.group(2)
            if value:
                return Path(value).expanduser()

        token_match = re.search(
            r"(?P<path>[^\s]+\.(?:csv|pdf|txt|md|json))\b",
            message,
            flags=re.IGNORECASE,
        )
        if token_match:
            return Path(token_match.group("path")).expanduser()
        return None

    @staticmethod
    def _extract_skill_slug(message: str, fallback: str = "") -> str:
        pattern = r"\b([a-z][a-z0-9-]{1,40})\b"
        ignored = {
            "call",
            "tool",
            "run",
            "execute",
            "it",
            "that",
            "this",
            "skill",
            "file",
            "on",
            "the",
            "a",
            "an",
            "me",
            "show",
            "what",
            "controls",
            "validate",
            "package",
        }
        for slug_match in re.finditer(pattern, message.lower()):
            candidate = slug_match.group(1)
            if candidate not in ignored:
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
