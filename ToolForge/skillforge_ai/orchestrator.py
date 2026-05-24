"""
AIOrchestrator — central routing and execution engine for SkillForge.

Intent parsing maps natural-language messages to Modes:
  BUILD     → create / generate / build / scaffold / make a tool/skill
  RUN       → run / execute / invoke / use a tool
  REPAIR    → fix / repair / debug / patch
  INSPECT   → show / list / describe / inspect
  PACKAGE   → package / zip / export / bundle
  BENCHMARK → benchmark / eval / measure / test
  ADMIN     → init / configure / install / set up / doctor

The orchestrator wires together all other SkillForge AI modules:
  PermissionBroker, EvidenceLogger, SkillBuilder, ValidationRunner,
  MCPController, SkillForgeRegistry.

Usage::

    orch = AIOrchestrator(
        workspace_root=Path("."),
        provider="rule_based",
        interactive=True,
    )
    response = orch.chat("Build a tool that converts JSON to CSV")
    orch.run_chat_loop()  # Rich REPL
"""
from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skillforge_ai.models import (
    IntentResult,
    Mode,
    OrchestratorState,
    Plan,
    PlanStep,
    RiskLevel,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent patterns  (order matters — first match wins)
# ---------------------------------------------------------------------------

_INTENT_RULES: list[tuple[re.Pattern, Mode]] = [
    (re.compile(r"\b(build|create|generate|scaffold|make|new|write)\b.*\b(tool|skill|function)\b", re.IGNORECASE), Mode.BUILD),
    (re.compile(r"\b(create|build|generate|scaffold|make|new)\b", re.IGNORECASE), Mode.BUILD),
    (re.compile(r"\b(repair|fix|debug|patch|heal|correct)\b", re.IGNORECASE), Mode.REPAIR),
    (re.compile(r"\b(package|zip|export|bundle|release)\b", re.IGNORECASE), Mode.PACKAGE),
    (re.compile(r"\b(benchmark|eval|evaluate|measure|perf|performance)\b", re.IGNORECASE), Mode.BENCHMARK),
    (re.compile(r"\b(run|execute|invoke|use|call)\b", re.IGNORECASE), Mode.RUN),
    (re.compile(r"\b(show|list|describe|inspect|info|status|what)\b", re.IGNORECASE), Mode.INSPECT),
    (re.compile(r"\b(init|initialize|configure|install|setup|doctor)\b", re.IGNORECASE), Mode.ADMIN),
]

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _parse_skill_name(message: str) -> str | None:
    """
    Try to extract an explicit skill/tool name from the message.
    Looks for patterns like: "for csv-cleaner", "the csv-cleaner tool", etc.
    """
    m = re.search(r"(?:for|the|tool|skill)\s+['\"]?([a-z][a-z0-9-]{1,40})['\"]?", message, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    # Last word as slug candidate if it looks like a slug
    words = message.strip().rstrip("?!.").split()
    if words and re.match(r"^[a-z][a-z0-9-]{1,40}$", words[-1], re.IGNORECASE):
        return words[-1].lower()
    return None


def _derive_slug(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-") or "generated-skill"


class AIOrchestrator:
    """
    Routes natural-language requests to the appropriate SkillForge handler.

    Parameters
    ----------
    workspace_root : Path
        Root of the SkillForge / ToolForge workspace.
    provider : str
        LLM provider for generation (default: "rule_based").
    interactive : bool
        When True, prompts the user for approval of APPROVAL_REQUIRED actions.
    auto_approve : bool
        When True, automatically approves all APPROVAL_REQUIRED actions.
    """

    def __init__(
        self,
        workspace_root: Path,
        provider: str = "rule_based",
        interactive: bool = True,
        auto_approve: bool = False,
    ) -> None:
        self._root = workspace_root.resolve()
        self._provider = provider

        _add_packages_to_path(self._root)

        # Lazy-initialised sub-components
        self._perm: Any | None = None
        self._ev: Any | None = None
        self._builder: Any | None = None
        self._val_runner: Any | None = None
        self._mcp_ctrl: Any | None = None
        self._registry: Any | None = None

        self._interactive = interactive
        self._auto_approve = auto_approve

        self._state = OrchestratorState(mode=Mode.UNKNOWN)

    # ------------------------------------------------------------------
    # Sub-component accessors (lazy initialisation)
    # ------------------------------------------------------------------

    @property
    def _permission_broker(self) -> Any:
        if self._perm is None:
            from skillforge_ai.permissions import PermissionBroker
            self._perm = PermissionBroker(
                interactive=self._interactive,
                auto_approve=self._auto_approve,
            )
        return self._perm

    @property
    def _evidence_logger(self) -> Any:
        if self._ev is None:
            from skillforge_ai.evidence_logger import EvidenceLogger
            log_dir = self._root / ".skillforge" / "evidence"
            log_dir.mkdir(parents=True, exist_ok=True)
            self._ev = EvidenceLogger(log_dir=log_dir, skill_name="session")
        return self._ev

    @property
    def _skill_builder(self) -> Any:
        if self._builder is None:
            from skillforge_ai.skill_builder import SkillBuilder
            self._builder = SkillBuilder(
                workspace_root=self._root,
                provider=self._provider,
                evidence_logger=self._evidence_logger,
            )
        return self._builder

    @property
    def _validation_runner(self) -> Any:
        if self._val_runner is None:
            from skillforge_ai.validation_runner import ValidationRunner
            self._val_runner = ValidationRunner(
                workspace_root=self._root,
                evidence_logger=self._evidence_logger,
            )
        return self._val_runner

    @property
    def _mcp_controller(self) -> Any:
        if self._mcp_ctrl is None:
            from skillforge_ai.mcp_controller import MCPController
            self._mcp_ctrl = MCPController(evidence_logger=self._evidence_logger)
        return self._mcp_ctrl

    @property
    def _skill_registry(self) -> Any:
        if self._registry is None:
            from skillforge_ai.tool_registry import SkillForgeRegistry
            self._registry = SkillForgeRegistry(workspace_root=self._root)
        return self._registry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(self, message: str) -> str:
        """
        Process a single natural-language *message* and return a text response.
        """
        intent = self._parse_intent(message)
        self._state.mode = intent.mode
        self._state.current_skill = intent.skill_name

        try:
            if intent.mode == Mode.BUILD:
                return self._handle_build(intent, message)
            if intent.mode == Mode.REPAIR:
                return self._handle_repair(intent, message)
            if intent.mode == Mode.RUN:
                return self._handle_run(intent, message)
            if intent.mode == Mode.INSPECT:
                return self._handle_inspect(intent, message)
            if intent.mode == Mode.PACKAGE:
                return self._handle_package(intent, message)
            if intent.mode == Mode.BENCHMARK:
                return self._handle_benchmark(intent, message)
            if intent.mode == Mode.ADMIN:
                return self._handle_admin(intent, message)
        except Exception as exc:
            self._state.last_error = str(exc)
            logger.error("Orchestrator error in mode %s: %s", intent.mode, exc)
            return f"Error: {exc}"

        return (
            "I'm not sure what you'd like to do. Try: "
            "\"create a tool that ...\", \"list tools\", \"validate <slug>\", \"run <slug>\""
        )

    def run_chat_loop(self) -> None:
        """
        Launch an interactive REPL.  Uses Rich for a nicer prompt when
        available; falls back to plain ``input()``.
        """
        _print_banner()
        print("Type 'exit' or 'quit' to leave.\n")

        while True:
            try:
                user_input = _read_input("skillforge> ")
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break

            stripped = user_input.strip()
            if not stripped:
                continue
            if stripped.lower() in {"exit", "quit", "q"}:
                print("Goodbye.")
                break

            response = self.chat(stripped)
            print(f"\n{response}\n")

    # ------------------------------------------------------------------
    # Intent parsing
    # ------------------------------------------------------------------

    def _parse_intent(self, message: str) -> IntentResult:
        mode = Mode.UNKNOWN
        for pattern, candidate_mode in _INTENT_RULES:
            if pattern.search(message):
                mode = candidate_mode
                break

        skill_name = _parse_skill_name(message)

        # Extract parameters (simple key=value pairs)
        params: dict[str, str] = {}
        for m in re.finditer(r"(\w+)\s*=\s*\"([^\"]+)\"", message):
            params[m.group(1)] = m.group(2)

        return IntentResult(
            mode=mode,
            skill_name=skill_name,
            description=message,
            parameters=params,
            raw_message=message,
        )

    # ------------------------------------------------------------------
    # Mode handlers
    # ------------------------------------------------------------------

    def _handle_build(self, intent: IntentResult, message: str) -> str:
        # Check permission
        from skillforge_ai.permissions import PermissionDeniedError, ApprovalRequiredError
        try:
            self._permission_broker.check("scaffold_tool", None)
        except PermissionDeniedError as exc:
            return str(exc)
        except ApprovalRequiredError as exc:
            if not self._prompt_approval(f"Build skill from: '{message}'"):
                return "Build cancelled by user."

        tool_dir, manifest = self._skill_builder.build(
            request=message,
            skill_name=intent.skill_name,
        )

        # Register in SkillForgeRegistry
        try:
            self._skill_registry.register_skill(manifest, tool_dir)
        except Exception as exc:
            logger.debug("register_skill failed: %s", exc)

        lines = [
            f"Skill '{manifest.name}' generated successfully.",
            f"  Location: {tool_dir}",
            f"  Category: {manifest.category}",
            f"  Risk level: {manifest.risk_level}",
        ]
        if manifest.mcp_servers:
            lines.append(f"  MCP servers: {', '.join(manifest.mcp_servers)}")
        lines.append(f"\nNext: skillforge validate {manifest.name}")
        return "\n".join(lines)

    def _handle_run(self, intent: IntentResult, message: str) -> str:
        from skillforge_ai.permissions import PermissionDeniedError, ApprovalRequiredError
        try:
            self._permission_broker.check("run_tool", None)
        except PermissionDeniedError as exc:
            return str(exc)
        except ApprovalRequiredError:
            if not self._prompt_approval(f"Run tool: {intent.skill_name}"):
                return "Run cancelled by user."

        slug = intent.skill_name
        if not slug:
            return "Please specify a tool name, e.g. 'run csv-cleaner'"

        tool_dir = self._root / "tools" / "generated" / slug
        if not tool_dir.exists():
            return f"Tool '{slug}' not found. Use 'create' to build it first."

        try:
            _add_packages_to_path(self._root)
            from packages.runners.tool_runner import run_tool
            result = run_tool(tool_dir, intent.parameters)
            return f"Tool '{slug}' completed.\n  Output: {result.output or '(none)'}"
        except Exception as exc:
            return f"Run failed: {exc}"

    def _handle_repair(self, intent: IntentResult, message: str) -> str:
        slug = intent.skill_name
        if not slug:
            return "Please specify which tool to repair, e.g. 'repair csv-cleaner'"

        report = self._validation_runner.repair_loop(slug, provider=self._provider)
        if report.passed:
            return f"Repair complete — '{slug}' passes all validators."
        return (
            f"Repair incomplete after {self._validation_runner._max_repair} attempt(s).\n"
            f"  Remaining errors:\n"
            + "\n".join(f"    - {e}" for e in report.errors[:5])
        )

    def _handle_inspect(self, intent: IntentResult, message: str) -> str:
        # "list" vs "inspect one"
        lower = message.lower()
        if any(w in lower for w in ("list", "all", "show all", "what skills", "what tools")):
            skills = self._skill_registry.list_skills()
            if not skills:
                return "No skills registered yet. Use 'create' to build one."
            lines = [f"{'Name':<30} {'Status':<12} {'Validated':<10} {'Risk'}", "-" * 65]
            for s in skills:
                lines.append(
                    f"{s['name']:<30} {s['status']:<12} {str(s['validated']):<10} {s['risk_level']}"
                )
            return "\n".join(lines)

        slug = intent.skill_name
        if not slug:
            # Fall through to listing
            return self._handle_inspect(intent, "list all")

        skill = self._skill_registry.get_skill(slug)
        if skill is None:
            return f"Skill '{slug}' not found in registry."

        lines = [f"Skill: {slug}"]
        for k, v in skill.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    def _handle_package(self, intent: IntentResult, message: str) -> str:
        from skillforge_ai.permissions import PermissionDeniedError, ApprovalRequiredError
        try:
            self._permission_broker.check("package_skill", None)
        except PermissionDeniedError as exc:
            return str(exc)
        except ApprovalRequiredError:
            if not self._prompt_approval(f"Package: {intent.skill_name}"):
                return "Package cancelled by user."

        slug = intent.skill_name
        if not slug:
            return "Please specify a skill name, e.g. 'package csv-cleaner'"

        tool_dir = self._root / "tools" / "generated" / slug
        if not tool_dir.exists():
            return f"Tool directory not found for '{slug}'."

        import zipfile
        import datetime

        out_dir = self._root / "dist"
        out_dir.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = out_dir / f"{slug}-{ts}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in tool_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(tool_dir))

        self._skill_registry.mark_packaged(slug)

        if self._ev:
            try:
                self._evidence_logger.log_package(slug, zip_path)
            except Exception:
                pass

        return f"Packaged '{slug}' → {zip_path}"

    def _handle_benchmark(self, intent: IntentResult, message: str) -> str:
        slug = intent.skill_name
        if not slug:
            return "Please specify a skill name, e.g. 'benchmark csv-cleaner'"

        report = self._validation_runner.validate(slug)
        lines = [
            f"Benchmark / eval for '{slug}':",
            f"  Validation passed: {report.passed}",
            f"  Schema OK:   {report.schema_ok}",
            f"  Security OK: {report.security_ok}",
            f"  MCP OK:      {report.mcp_ok}",
            f"  Tests OK:    {report.tests_ok}",
            f"  Safety OK:   {report.safety_ok}",
        ]
        if report.errors:
            lines.append("  Errors:")
            for e in report.errors:
                lines.append(f"    - {e}")
        return "\n".join(lines)

    def _handle_admin(self, intent: IntentResult, message: str) -> str:
        lower = message.lower()

        if "init" in lower or "initialize" in lower:
            return self._cmd_init()

        if "doctor" in lower:
            return self._cmd_doctor()

        if "install" in lower:
            return "Use `pip install -e '.[dev,llm]'` to install all dependencies."

        return (
            "Admin commands:\n"
            "  init    — initialise .skillforge/ workspace\n"
            "  doctor  — check workspace health\n"
            "  install — install dependencies"
        )

    # ------------------------------------------------------------------
    # Admin helpers
    # ------------------------------------------------------------------

    def _cmd_init(self) -> str:
        sf_dir = self._root / ".skillforge"
        sf_dir.mkdir(exist_ok=True)
        (sf_dir / "evidence").mkdir(exist_ok=True)
        (sf_dir / "config.json").write_text(
            '{"provider": "rule_based", "version": "0.1.0"}\n',
            encoding="utf-8",
        )
        return f"Workspace initialised at {sf_dir}"

    def _cmd_doctor(self) -> str:
        lines = ["Workspace health check:"]
        checks = {
            ".skillforge/":       (self._root / ".skillforge").exists(),
            "toolforge_registry.json": (self._root / "toolforge_registry.json").exists(),
            "tools/generated/":   (self._root / "tools" / "generated").exists(),
            "skills/generated/":  (self._root / "skills" / "generated").exists(),
            "evals/generated/":   (self._root / "evals" / "generated").exists(),
        }
        all_ok = True
        for name, ok in checks.items():
            status = "OK" if ok else "MISSING"
            if not ok:
                all_ok = False
            lines.append(f"  {status:<8} {name}")
        lines.append("")
        lines.append("Overall: " + ("healthy" if all_ok else "action needed"))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Approval helper
    # ------------------------------------------------------------------

    def _prompt_approval(self, description: str) -> bool:
        if self._auto_approve:
            return True
        if not self._interactive:
            return False
        resp = input(f"Approve: {description}? [y/N] ").strip().lower()
        return resp in ("y", "yes")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_packages_to_path(workspace_root: Path) -> None:
    pkg_root = str(workspace_root)
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)


def _print_banner() -> None:
    try:
        from rich.console import Console
        console = Console()
        console.print("[bold cyan]SkillForge AI[/bold cyan] — AI-powered skill orchestration", highlight=False)
    except ImportError:
        print("SkillForge AI — AI-powered skill orchestration")


def _read_input(prompt: str) -> str:
    try:
        from rich.prompt import Prompt
        return Prompt.ask(prompt)
    except ImportError:
        return input(prompt)
