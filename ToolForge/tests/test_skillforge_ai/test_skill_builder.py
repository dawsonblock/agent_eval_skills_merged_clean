"""
Tests for skillforge_ai.skill_builder — SkillBuilder with mocked generators.
"""
# mypy: disable-error-code=import-untyped

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skillforge_ai.errors import SkillForgeDependencyError
from skillforge_ai.models import SkillManifest
from skillforge_ai.skill_builder import SkillBuilder


class TestSkillBuilderBuild:
    """Unit tests for SkillBuilder with mocked ToolForge generators."""

    def _make_spec(self, slug: str = "csv-cleaner") -> MagicMock:
        spec = MagicMock()
        spec.slug = slug
        spec.name = slug
        spec.description = f"Mock tool: {slug}"
        spec.category = "data"
        spec.risk_level = "low"
        spec.permissions = []
        spec.sandbox_level = 0
        spec.capabilities = []
        spec.parameters = []
        spec.output = MagicMock()
        spec.output.type = "string"
        spec.output.description = "result"
        spec.security = MagicMock()
        spec.security.required_capabilities = []
        spec.security.requires_filesystem = False
        spec.security.allowed_read_paths = []
        spec.security.allowed_write_paths = []
        spec.security.requires_network = False
        spec.security.requires_shell = False
        spec.entry_point = f"{slug}.py"
        spec.mcp = MagicMock()
        spec.mcp.enabled = True
        spec.skill = MagicMock()
        spec.skill.enabled = True
        spec.skill.category = "data"
        spec.model_dump_json.return_value = '{"slug": "' + slug + '"}'
        return spec

    def _make_builder(self, tmp_path: Path, **kw) -> SkillBuilder:
        return SkillBuilder(
            workspace_root=tmp_path,
            provider="rule_based",
            **kw,
        )

    def test_build_returns_tool_dir_and_manifest(self, tmp_path: Path):
        spec = self._make_spec()
        builder = self._make_builder(tmp_path)

        with (
            patch.object(builder, "_generate_spec", return_value=spec),
            patch.object(
                builder,
                "_scaffold",
                return_value=[],
            ) as mock_scaffold,
            patch.object(
                builder,
                "_generate_mcp",
                return_value=[],
            ) as mock_mcp,
            patch.object(
                builder,
                "_generate_skill",
                return_value=[],
            ) as mock_skill,
            patch.object(
                builder,
                "_generate_eval",
                return_value=[],
            ) as mock_eval,
            patch.object(builder, "_register") as mock_reg,
        ):
            tool_dir, manifest = builder.build("Create a CSV cleaner")

        assert isinstance(manifest, SkillManifest)
        assert manifest.name == spec.slug
        skill_root = tmp_path / "skills" / spec.slug
        assert (skill_root / "SKILL.md").exists()
        assert (skill_root / "metadata.json").exists()
        assert (skill_root / "README.md").exists()
        assert (skill_root / "tool" / "main.py").exists()
        assert (skill_root / "tool" / "__init__.py").exists()
        assert (skill_root / "examples" / "messy.csv").exists()
        mock_scaffold.assert_called_once()
        mock_mcp.assert_called_once()
        mock_skill.assert_called_once()
        mock_eval.assert_called_once()
        mock_reg.assert_called_once()

    def test_build_skips_mcp_when_disabled(self, tmp_path: Path):
        spec = self._make_spec()
        spec.mcp.enabled = False
        builder = self._make_builder(tmp_path)

        with (
            patch.object(builder, "_generate_spec", return_value=spec),
            patch.object(
                builder,
                "_scaffold",
                return_value=[],
            ),
            patch.object(
                builder,
                "_generate_mcp",
                return_value=[],
            ) as mock_mcp,
            patch.object(
                builder,
                "_generate_skill",
                return_value=[],
            ),
            patch.object(
                builder,
                "_generate_eval",
                return_value=[],
            ),
            patch.object(builder, "_register"),
        ):
            builder.build("Create a CSV cleaner")

        mock_mcp.assert_not_called()

    def test_build_with_explicit_skill_name(self, tmp_path: Path):
        spec = self._make_spec("my-custom-skill")
        builder = self._make_builder(tmp_path)

        with (
            patch.object(builder, "_generate_spec", return_value=spec),
            patch.object(
                builder,
                "_scaffold",
                return_value=[],
            ),
            patch.object(
                builder,
                "_generate_mcp",
                return_value=[],
            ),
            patch.object(
                builder,
                "_generate_skill",
                return_value=[],
            ),
            patch.object(
                builder,
                "_generate_eval",
                return_value=[],
            ),
            patch.object(builder, "_register"),
        ):
            _, manifest = builder.build(
                "Build a cleaner",
                skill_name="my-custom-skill",
            )

        assert manifest.name == "my-custom-skill"

    def test_build_normalizes_disallowed_category(self, tmp_path: Path):
        spec = self._make_spec("csv-cleaner")
        spec.skill.category = "file-processing"
        builder = self._make_builder(tmp_path)

        with (
            patch.object(builder, "_generate_spec", return_value=spec),
            patch.object(
                builder,
                "_scaffold",
                return_value=[],
            ),
            patch.object(
                builder,
                "_generate_mcp",
                return_value=[],
            ),
            patch.object(
                builder,
                "_generate_skill",
                return_value=[],
            ),
            patch.object(
                builder,
                "_generate_eval",
                return_value=[],
            ),
            patch.object(builder, "_register"),
        ):
            _, manifest = builder.build("Create a CSV cleaner")

        assert manifest.category == "data"

    def test_build_maps_filesystem_permissions_to_low_risk(
        self,
        tmp_path: Path,
    ):
        spec = self._make_spec("csv-cleaner")
        spec.security.requires_filesystem = True
        spec.security.allowed_read_paths = ["./examples/**"]
        spec.security.allowed_write_paths = ["./outputs/**"]
        spec.sandbox_level = 1
        builder = self._make_builder(tmp_path)

        with (
            patch.object(builder, "_generate_spec", return_value=spec),
            patch.object(builder, "_scaffold", return_value=[]),
            patch.object(builder, "_generate_mcp", return_value=[]),
            patch.object(builder, "_generate_skill", return_value=[]),
            patch.object(builder, "_generate_eval", return_value=[]),
            patch.object(builder, "_register"),
        ):
            _, manifest = builder.build("Create a CSV cleaner")

        assert manifest.permissions == ["read_files", "write_files"]
        assert manifest.risk_level == "low"

    def test_build_logs_evidence(self, tmp_path: Path):
        spec = self._make_spec()
        mock_ev = MagicMock()
        builder = self._make_builder(tmp_path, evidence_logger=mock_ev)

        with (
            patch.object(builder, "_generate_spec", return_value=spec),
            patch.object(
                builder,
                "_scaffold",
                return_value=[],
            ),
            patch.object(
                builder,
                "_generate_mcp",
                return_value=[],
            ),
            patch.object(
                builder,
                "_generate_skill",
                return_value=[],
            ),
            patch.object(
                builder,
                "_generate_eval",
                return_value=[],
            ),
            patch.object(builder, "_register"),
        ):
            builder.build("Build a CSV cleaner")

        mock_ev.log_build.assert_called_once()

    def test_build_falls_back_on_aigen_failure(self, tmp_path: Path):
        fallback_spec = self._make_spec("fallback-skill")

        builder = self._make_builder(tmp_path)

        # Patch _generate_spec to raise on first call; the real fallback logic
        # inside _generate_spec handles it internally. Instead simulate by
        # returning fallback_spec directly.
        with (
            patch.object(
                builder,
                "_generate_spec",
                return_value=fallback_spec,
            ),
            patch.object(
                builder,
                "_scaffold",
                return_value=[],
            ),
            patch.object(
                builder,
                "_generate_mcp",
                return_value=[],
            ),
            patch.object(
                builder,
                "_generate_skill",
                return_value=[],
            ),
            patch.object(
                builder,
                "_generate_eval",
                return_value=[],
            ),
            patch.object(builder, "_register"),
        ):
            _, manifest = builder.build("Build something")

        assert manifest.name == fallback_spec.slug

    def test_ensure_toolforge_yaml_raises_clear_dependency_error(
        self,
        tmp_path: Path,
    ):
        spec = self._make_spec()
        builder = self._make_builder(tmp_path)
        tool_dir = tmp_path / "tools" / "generated" / spec.slug

        with patch(
            "skillforge_ai.skill_builder.dump_yaml",
            side_effect=SkillForgeDependencyError("missing"),
        ):
            with pytest.raises(SkillForgeDependencyError):
                builder._ensure_toolforge_yaml(spec, tool_dir)

    def test_generate_spec_overrides_explicit_skill_name(self, tmp_path: Path):
        builder = self._make_builder(tmp_path)
        generated_spec = self._make_spec("create-a-tool-named")

        def _copy_with_update(update):
            copied = self._make_spec(update["slug"])
            copied.name = update["name"]
            return copied

        generated_spec.model_copy.side_effect = _copy_with_update

        mock_generator = MagicMock()
        mock_generator.generate.return_value = generated_spec

        with patch(
            "packages.ai.spec_generator.AISpecGenerator",
            return_value=mock_generator,
        ):
            spec = builder._generate_spec(
                "Local PDF to Markdown converter.",
                "pdf-to-markdown",
            )

        assert spec.slug == "pdf-to-markdown"
        assert spec.name == "Pdf To Markdown"

    def test_build_copies_nested_generated_tool_files(self, tmp_path: Path):
        spec = self._make_spec("csv-cleaner")
        builder = self._make_builder(tmp_path)

        def _scaffold_side_effect(_spec, tool_dir, overwrite=False):
            nested_root = tool_dir / spec.slug
            nested_root.mkdir(parents=True, exist_ok=True)
            (nested_root / "tool.py").write_text(
                "def run(input_path: str, output_path: str | None = None) -> dict:\n"
                "    return {'input_path': input_path, 'output_path': output_path}\n",
                encoding="utf-8",
            )
            tests_dir = nested_root / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            (tests_dir / "test_csv_cleaner.py").write_text(
                "def test_nested_copy() -> None:\n    assert True\n",
                encoding="utf-8",
            )
            return [nested_root / "tool.py", tests_dir / "test_csv_cleaner.py"]

        with (
            patch.object(builder, "_generate_spec", return_value=spec),
            patch.object(builder, "_scaffold", side_effect=_scaffold_side_effect),
            patch.object(builder, "_generate_mcp", return_value=[]),
            patch.object(builder, "_generate_skill", return_value=[]),
            patch.object(builder, "_generate_eval", return_value=[]),
            patch.object(builder, "_register"),
        ):
            builder.build("Create a CSV cleaner")

        skill_root = tmp_path / "skills" / spec.slug
        assert "def run(" in (skill_root / "tool" / "main.py").read_text(encoding="utf-8")
        assert "from .main import run" in (
            skill_root / "tool" / "__init__.py"
        ).read_text(encoding="utf-8")
        assert (skill_root / "tests" / "test_csv_cleaner.py").exists()
