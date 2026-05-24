"""
SkillBuilder — AI-driven skill scaffolding layer.

Orchestrates the full generate → register flow using existing ToolForge
generators while recording every file created in the EvidenceLogger.

Usage::

    builder = SkillBuilder(
        workspace_root=Path("."),
        provider="rule_based",
        evidence_logger=ev_logger,
    )
    tool_dir, manifest = builder.build("tool that cleans CSV files")
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from skillforge_ai.models import SkillManifest

logger = logging.getLogger(__name__)


def _add_packages_to_path(workspace_root: Path) -> None:
    """Ensure ToolForge's packages/ directory is importable."""
    pkg_root = str(workspace_root)
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)


class SkillBuilder:
    """
    Build a SkillForge skill from a natural-language request.

    Wraps:
      - AISpecGenerator (spec generation)
      - scaffold_tool   (implementation + tests)
      - generate_mcp_server (MCP wrapper, optional)
      - generate_skill  (SKILL.md)
      - generate_eval   (eval harness)
      - ToolRegistry    (lifecycle tracking)
    """

    def __init__(
        self,
        workspace_root: Path,
        provider: str = "rule_based",
        evidence_logger: Any | None = None,
        generate_mcp: bool = True,
        generate_skill_md: bool = True,
        generate_eval_harness: bool = True,
        overwrite: bool = False,
    ) -> None:
        self._root = workspace_root.resolve()
        self._provider = provider
        self._ev = evidence_logger
        self._gen_mcp = generate_mcp
        self._gen_skill = generate_skill_md
        self._gen_eval = generate_eval_harness
        self._overwrite = overwrite

        _add_packages_to_path(self._root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        request: str,
        skill_name: str | None = None,
    ) -> tuple[Path, SkillManifest]:
        """
        Generate a complete skill from *request*.

        Returns
        -------
        (tool_dir, manifest) where tool_dir is the generated tool directory
        and manifest is the SkillForge-layer SkillManifest.
        """

        # 1. Generate ToolSpec from natural language
        spec = self._generate_spec(request, skill_name)

        # 2. Scaffold full tool directory
        tool_dir = self._root / "tools" / "generated" / spec.slug
        files_created = self._scaffold(spec, tool_dir)

        # 3. Generate MCP server (optional)
        if self._gen_mcp and spec.mcp.enabled:
            mcp_files = self._generate_mcp(spec, tool_dir)
            files_created.extend(mcp_files)

        # 4. Generate SKILL.md
        if self._gen_skill and spec.skill.enabled:
            skill_files = self._generate_skill(spec)
            files_created.extend(skill_files)

        # 5. Generate eval harness
        if self._gen_eval:
            eval_files = self._generate_eval(spec)
            files_created.extend(eval_files)

        # 6. Register in ToolRegistry
        self._register(spec)

        # 7. Build manifest
        manifest = self._spec_to_manifest(spec)

        # 8. Log evidence
        if self._ev is not None:
            try:
                import json as _json
                self._ev.log_build(
                    skill_name=spec.slug,
                    files_created=files_created,
                    spec=_json.loads(spec.model_dump_json()),
                )
            except Exception as exc:
                logger.debug("EvidenceLogger.log_build failed: %s", exc)

        return tool_dir, manifest

    # ------------------------------------------------------------------
    # Internal steps
    # ------------------------------------------------------------------

    def _generate_spec(self, request: str, skill_name: str | None) -> Any:
        """Call AISpecGenerator and return a ToolSpec."""
        from packages.ai.spec_generator import AISpecGenerator

        # If skill_name given, incorporate it in the prompt
        prompt = request
        if skill_name:
            prompt = f"Create a tool named '{skill_name}' that {request}"

        generator = AISpecGenerator(
            provider=self._provider,
            fallback_to_rule_based=True,
        )
        try:
            return generator.generate(prompt)
        except Exception as exc:
            logger.error("AISpecGenerator failed: %s — falling back to rule_based", exc)
            from packages.core.spec_from_prompt import RuleBasedSpecGenerator
            return RuleBasedSpecGenerator().generate(prompt)

    def _scaffold(self, spec: Any, tool_dir: Path) -> list[Path]:
        """Scaffold the tool directory using the existing generator."""
        from packages.core.tool_generator import scaffold_tool

        try:
            files = scaffold_tool(spec, tool_dir, overwrite=self._overwrite)
            return files if isinstance(files, list) else list(files)
        except Exception as exc:
            logger.error("scaffold_tool failed for %s: %s", spec.slug, exc)
            return []

    def _generate_mcp(self, spec: Any, tool_dir: Path) -> list[Path]:
        from packages.core.mcp_generator import generate_mcp_server

        try:
            return generate_mcp_server(spec, tool_dir, overwrite=self._overwrite)
        except Exception as exc:
            logger.warning("generate_mcp_server failed: %s", exc)
            return []

    def _generate_skill(self, spec: Any) -> list[Path]:
        from packages.core.skill_generator import generate_skill

        skills_root = self._root / "skills" / "generated"
        skills_root.mkdir(parents=True, exist_ok=True)
        try:
            return generate_skill(spec, skills_root, overwrite=self._overwrite)
        except Exception as exc:
            logger.warning("generate_skill failed: %s", exc)
            return []

    def _generate_eval(self, spec: Any) -> list[Path]:
        from packages.core.eval_generator import generate_eval

        evals_root = self._root / "evals" / "generated"
        evals_root.mkdir(parents=True, exist_ok=True)
        try:
            return generate_eval(spec, evals_root, overwrite=self._overwrite)
        except Exception as exc:
            logger.warning("generate_eval failed: %s", exc)
            return []

    def _register(self, spec: Any) -> None:
        from packages.core.registry import ToolRegistry

        registry_path = self._root / "toolforge_registry.json"
        try:
            registry = ToolRegistry(registry_path)
            registry.register(spec, status="generated")
        except Exception as exc:
            logger.warning("ToolRegistry.register failed: %s", exc)

    # ------------------------------------------------------------------
    # Manifest conversion
    # ------------------------------------------------------------------

    def _spec_to_manifest(self, spec: Any) -> SkillManifest:
        from skillforge_ai.models import SkillManifest, InputSpec, OutputSpec

        inputs = [
            InputSpec(
                name=p.name,
                type=p.type,
                required=p.required,
                description=p.description,
            )
            for p in spec.parameters
        ]
        outputs = [
            OutputSpec(
                name="result",
                type=spec.output.type,
                description=spec.output.description,
            )
        ]

        permissions: list[str] = []
        for cap in spec.capabilities:
            permissions.append(cap.value)

        risk = "high" if spec.sandbox_level >= 3 else (
            "medium" if spec.sandbox_level >= 1 else "low"
        )

        mcp_servers: list[str] = []
        if spec.mcp.enabled:
            mcp_servers.append(f"{spec.slug}-mcp")

        return SkillManifest(
            name=spec.slug,
            description=spec.description,
            category=getattr(spec.skill, "category", "generated"),
            inputs=inputs,
            outputs=outputs,
            tools_required=[spec.entry_point],
            mcp_servers=mcp_servers,
            permissions=permissions,
            risk_level=risk,
        )
