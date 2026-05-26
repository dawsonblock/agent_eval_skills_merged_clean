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
# mypy: disable-error-code=import-untyped

# pyright: reportMissingTypeStubs=false

from __future__ import annotations

import logging
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from skillforge_ai.models import SkillManifest

from skillforge_ai.yaml_utils import dump_yaml

logger = logging.getLogger(__name__)

_ALLOWED_SKILL_CATEGORIES = {
    "data",
    "documents",
    "coding",
    "browser",
    "automation",
    "media",
    "3d",
    "game-dev",
    "robotics",
    "hardware",
    "research",
    "productivity",
    "custom",
}

_CATEGORY_ALIASES = {
    "file-processing": "data",
    "file_processing": "data",
    "generated": "custom",
}

_CAPABILITY_PERMISSION_MAP = {
    "read_files": "read_files",
    "write_files": "write_files",
    "call_http": "network_access",
    "execute_code": "shell_commands",
    "run_shell": "shell_commands",
}


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
        toolforge_yaml = self._ensure_toolforge_yaml(spec, tool_dir)
        if toolforge_yaml is not None:
            files_created.append(toolforge_yaml)

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

        # 8. Materialize canonical SkillForge layout under skills/<slug>/
        skill_layout_files = self._materialize_skill_layout(manifest, tool_dir)
        files_created.extend(skill_layout_files)

        # 9. Log evidence
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

    def _materialize_skill_layout(
        self,
        manifest: SkillManifest,
        tool_dir: Path,
    ) -> list[Path]:
        skill_root = self._root / "skills" / manifest.name
        tool_root = skill_root / "tool"
        tests_root = skill_root / "tests"
        examples_root = skill_root / "examples"

        tool_root.mkdir(parents=True, exist_ok=True)
        tests_root.mkdir(parents=True, exist_ok=True)
        examples_root.mkdir(parents=True, exist_ok=True)

        files: list[Path] = []

        skill_md = skill_root / "SKILL.md"
        skill_md.write_text(
            "\n".join(
                [
                    "---",
                    f"name: {manifest.name}",
                    f"description: {manifest.description}",
                    "---",
                    "",
                    "Generated by SkillForge AI.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        files.append(skill_md)

        metadata = {
            "name": manifest.name,
            "description": manifest.description,
            "category": manifest.category,
            "version": "0.1.0",
            "inputs": [
                {"name": i.name, "type": i.type, "required": i.required}
                for i in manifest.inputs
            ],
            "outputs": [
                {"name": o.name, "type": o.type, "required": True}
                for o in manifest.outputs
            ],
            "tools_required": manifest.tools_required,
            "mcp_servers": manifest.mcp_servers,
            "permissions": manifest.permissions,
            "risk_level": manifest.risk_level,
            "validation": {
                "metadata": "pending",
                "syntax": "pending",
                "tests": "pending",
                "package": "pending",
                "smoke": "pending",
            },
        }
        metadata_path = skill_root / "metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, indent=2) + "\n",
            encoding="utf-8",
        )
        files.append(metadata_path)

        readme = skill_root / "README.md"
        readme.write_text(
            "\n".join(
                [
                    f"# {manifest.name}",
                    "",
                    manifest.description,
                    "",
                    "## Run",
                    f"skillforge run {manifest.name} --input key=value",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        files.append(readme)

        validation_report = skill_root / "validation_report.json"
        validation_report.write_text(
            json.dumps(
                {
                    "skill": manifest.name,
                    "status": "pending",
                    "checks": {
                        "metadata": "pending",
                        "skill_md": "pending",
                        "syntax": "pending",
                        "tests": "pending",
                        "package": "pending",
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        files.append(validation_report)

        source_tool = tool_dir / "tool.py"
        if not source_tool.exists():
            nested_tools = sorted(
                candidate
                for candidate in tool_dir.rglob("tool.py")
                if candidate.is_file() and "__pycache__" not in candidate.parts
            )
            if nested_tools:
                source_tool = nested_tools[0]
        target_tool = tool_root / "main.py"
        if source_tool.exists():
            shutil.copy2(source_tool, target_tool)
        else:
            target_tool.write_text(
                (
                    "def main() -> int:\n"
                    "    return 0\n\n\n"
                    "if __name__ == '__main__':\n"
                    "    raise SystemExit(main())\n"
                ),
                encoding="utf-8",
            )
        files.append(target_tool)

        tool_init = tool_root / "__init__.py"
        tool_init.write_text(
            (
                "try:\n"
                "    from .main import run\n"
                "except Exception:\n"
                "    def run(*args, **kwargs):\n"
                "        raise NotImplementedError('run is not implemented in tool/main.py')\n"
                "\n"
                "__all__ = ['run']\n"
            ),
            encoding="utf-8",
        )
        files.append(tool_init)

        src_tests_dir = tool_dir / "tests"
        if not src_tests_dir.exists():
            nested_test_dirs = sorted(
                candidate
                for candidate in tool_dir.rglob("tests")
                if candidate.is_dir() and "__pycache__" not in candidate.parts
            )
            if nested_test_dirs:
                src_tests_dir = nested_test_dirs[0]
        copied_test = False
        if src_tests_dir.exists():
            for test_file in src_tests_dir.glob("test_*.py"):
                shutil.copy2(test_file, tests_root / test_file.name)
                files.append(tests_root / test_file.name)
                copied_test = True
        if not copied_test:
            fallback_test = (
                tests_root / f"test_{manifest.name.replace('-', '_')}.py"
            )
            fallback_test.write_text(
                "def test_placeholder() -> None:\n    assert True\n",
                encoding="utf-8",
            )
            files.append(fallback_test)

        example_file = examples_root / "messy.csv"
        if not example_file.exists():
            example_file.write_text(
                "name, value\n Alice , 1\n\nBob,2\n",
                encoding="utf-8",
            )
        files.append(example_file)

        return files

    def _ensure_toolforge_yaml(self, spec: Any, tool_dir: Path) -> Path | None:
        yaml_path = tool_dir / "toolforge.yaml"
        if yaml_path.exists():
            return None

        tool_dir.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] | None = None
        model_dump = getattr(spec, "model_dump", None)
        if callable(model_dump):
            try:
                dumped = model_dump(mode="json")
                if isinstance(dumped, dict):
                    payload = dumped
            except Exception:
                payload = None

        if payload is None:
            model_dump_json = getattr(spec, "model_dump_json", None)
            if callable(model_dump_json):
                try:
                    dumped_json = model_dump_json()
                    parsed = json.loads(dumped_json)
                    if isinstance(parsed, dict):
                        payload = parsed
                except Exception:
                    payload = None

        if payload is None:
            payload = {
                "name": getattr(
                    spec,
                    "name",
                    getattr(spec, "slug", "generated-tool"),
                ),
                "slug": getattr(spec, "slug", "generated-tool"),
                "description": getattr(
                    spec,
                    "description",
                    "Generated by SkillForge",
                ),
                "version": "0.1.0",
                "language": "python",
                "entry_point": str(getattr(spec, "entry_point", "tool.py")),
                "parameters": [],
                "output": {"type": "string", "description": "result"},
                "security": {},
                "mcp": {"enabled": True},
                "skill": {
                    "enabled": True,
                    "category": getattr(spec, "category", "general"),
                },
                "eval": {"enabled": True},
            }

        dump_yaml(payload, yaml_path)
        return yaml_path

    # ------------------------------------------------------------------
    # Internal steps
    # ------------------------------------------------------------------

    def _generate_spec(self, request: str, skill_name: str | None) -> Any:
        """Call AISpecGenerator and return a ToolSpec."""
        from packages.ai.spec_generator import (
            AISpecGenerator,
        )

        # If skill_name given, incorporate it in the prompt
        prompt = request
        if skill_name:
            prompt = f"Create a tool named '{skill_name}' that {request}"

        generator = AISpecGenerator(
            provider=self._provider,
            fallback_to_rule_based=True,
        )
        try:
            spec = generator.generate(prompt)
        except Exception as exc:
            logger.error(
                "AISpecGenerator failed: %s — falling back to rule_based",
                exc,
            )
            from packages.core.spec_from_prompt import (
                RuleBasedSpecGenerator,
            )
            spec = RuleBasedSpecGenerator().generate(prompt)

        return self._override_generated_identity(spec, skill_name)

    @staticmethod
    def _override_generated_identity(spec: Any, skill_name: str | None) -> Any:
        if not skill_name:
            return spec

        human_name = skill_name.replace("-", " ").strip().title()
        model_copy = getattr(spec, "model_copy", None)
        if callable(model_copy):
            return model_copy(update={"slug": skill_name, "name": human_name})

        if hasattr(spec, "slug"):
            spec.slug = skill_name
        if hasattr(spec, "name"):
            spec.name = human_name
        return spec

    @staticmethod
    def _normalize_generated_description(description: str | None) -> str:
        text = " ".join((description or "").split())
        if not text:
            return "Generated by SkillForge AI."

        text = re.sub(
            r"^Create a tool named ['\"][^'\"]+['\"] that\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^(build|make|create) me a skill that\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )

        if text:
            text = text[0].upper() + text[1:]
        if not text.endswith("."):
            text += "."
        return text

    def _scaffold(self, spec: Any, tool_dir: Path) -> list[Path]:
        """Scaffold the tool directory using the existing generator."""
        from packages.core.tool_generator import (
            scaffold_tool,
        )

        try:
            files = scaffold_tool(spec, tool_dir, overwrite=self._overwrite)
            return files if isinstance(files, list) else list(files)
        except Exception as exc:
            logger.error("scaffold_tool failed for %s: %s", spec.slug, exc)
            return []

    def _generate_mcp(self, spec: Any, tool_dir: Path) -> list[Path]:
        from packages.core.mcp_generator import (
            generate_mcp_server,
        )

        try:
            return generate_mcp_server(
                spec,
                tool_dir,
                overwrite=self._overwrite,
            )
        except Exception as exc:
            logger.warning("generate_mcp_server failed: %s", exc)
            return []

    def _generate_skill(self, spec: Any) -> list[Path]:
        from packages.core.skill_generator import (
            generate_skill,
        )

        skills_root = self._root / "skills" / "generated"
        skills_root.mkdir(parents=True, exist_ok=True)
        try:
            return generate_skill(spec, skills_root, overwrite=self._overwrite)
        except Exception as exc:
            logger.warning("generate_skill failed: %s", exc)
            return []

    def _generate_eval(self, spec: Any) -> list[Path]:
        from packages.core.eval_generator import (
            generate_eval,
        )

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
        from skillforge_ai.models import (
            InputSpec,
            OutputSpec,
            SkillManifest,
        )

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

        security = getattr(spec, "security", None)
        permissions: list[str] = []
        required_capabilities = getattr(
            security,
            "required_capabilities",
            [],
        ) or []
        for cap in required_capabilities:
            permission = _CAPABILITY_PERMISSION_MAP.get(
                getattr(cap, "value", str(cap))
            )
            if permission and permission not in permissions:
                permissions.append(permission)

        if security is not None:
            read_paths = getattr(security, "allowed_read_paths", []) or []
            write_paths = getattr(security, "allowed_write_paths", []) or []
            if (
                getattr(security, "requires_filesystem", False)
                or read_paths
            ) and "read_files" not in permissions:
                permissions.append("read_files")
            if (
                getattr(security, "requires_filesystem", False)
                or write_paths
            ) and "write_files" not in permissions:
                permissions.append("write_files")
            if getattr(security, "requires_network", False):
                if "network_access" not in permissions:
                    permissions.append("network_access")
            if getattr(security, "requires_shell", False):
                if "shell_commands" not in permissions:
                    permissions.append("shell_commands")

        risky_permissions = {
            "network_access",
            "shell_commands",
            "docker_access",
            "external_api",
            "hardware_access",
            "read_secrets",
        }
        risk = "medium" if any(
            permission in risky_permissions for permission in permissions
        ) else "low"

        mcp_servers: list[str] = []
        if spec.mcp.enabled:
            mcp_servers.append(f"{spec.slug}-mcp")

        raw_category = str(
            getattr(spec.skill, "category", "generated")
        ).strip().lower()
        category = _CATEGORY_ALIASES.get(raw_category, raw_category)
        if category not in _ALLOWED_SKILL_CATEGORIES:
            category = "custom"

        return SkillManifest(
            name=spec.slug,
            description=self._normalize_generated_description(spec.description),
            category=category,
            inputs=inputs,
            outputs=outputs,
            tools_required=[spec.entry_point],
            mcp_servers=mcp_servers,
            permissions=permissions,
            risk_level=risk,
        )
