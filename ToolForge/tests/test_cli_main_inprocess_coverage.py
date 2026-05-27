"""Lightweight in-process CLI coverage for command wiring and branch handling."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from apps.cli.toolforge_cli.main import cli


@dataclass
class _DummySpec:
    slug: str = "dummy-tool"
    name: str = "Dummy Tool"
    version: str = "0.1.0"
    description: str = "dummy"
    tags: list[str] = None
    author: str | None = None
    language: SimpleNamespace = None
    mcp: SimpleNamespace = None
    skill: SimpleNamespace = None
    eval: SimpleNamespace = None

    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = ["dummy"]
        if self.language is None:
            self.language = SimpleNamespace(value="python")
        if self.mcp is None:
            self.mcp = SimpleNamespace(enabled=True)
        if self.skill is None:
            self.skill = SimpleNamespace(enabled=True)
        if self.eval is None:
            self.eval = SimpleNamespace(enabled=True)

    def model_copy(self, update: dict) -> "_DummySpec":
        copied = _DummySpec(
            slug=self.slug,
            name=self.name,
            version=self.version,
            description=self.description,
            tags=list(self.tags),
            author=self.author,
        )
        for key, value in update.items():
            setattr(copied, key, value)
        return copied


class _DummyRegistry:
    _spec: _DummySpec | None = None
    _meta: dict[str, object] = {}

    def __init__(self, _path: Path) -> None:
        pass

    def register(self, spec: _DummySpec) -> None:
        _DummyRegistry._spec = spec
        _DummyRegistry._meta.setdefault("status", "generated")

    def set_mcp_path(self, _slug: str, path: Path) -> None:
        _DummyRegistry._meta["mcp_path"] = str(path)

    def set_skill_path(self, _slug: str, path: Path) -> None:
        _DummyRegistry._meta["skill_path"] = str(path)

    def set_eval_path(self, _slug: str, path: Path) -> None:
        _DummyRegistry._meta["eval_path"] = str(path)

    def set_validation_result(self, _slug: str, ok: bool) -> None:
        _DummyRegistry._meta["validation_passed"] = ok

    def set_status(self, _slug: str, status: str) -> None:
        _DummyRegistry._meta["status"] = status

    def set_last_run(self, _slug: str, **kwargs: object) -> None:
        _DummyRegistry._meta.update({"last_run": "now", **kwargs})

    def set_eval_score(self, _slug: str, score: float) -> None:
        _DummyRegistry._meta["eval_score"] = score
        _DummyRegistry._meta["last_eval"] = "now"

    def set_package_path(self, _slug: str, path: Path) -> None:
        _DummyRegistry._meta["package_path"] = str(path)

    def list_all(self) -> list[_DummySpec]:
        return [_DummyRegistry._spec] if _DummyRegistry._spec else []

    def search_by_tag(self, tag: str) -> list[_DummySpec]:
        if _DummyRegistry._spec and tag in (_DummyRegistry._spec.tags or []):
            return [_DummyRegistry._spec]
        return []

    def find(self, slug: str) -> _DummySpec | None:
        if _DummyRegistry._spec and _DummyRegistry._spec.slug == slug:
            return _DummyRegistry._spec
        return None

    def get_metadata(self, _slug: str) -> dict[str, object]:
        return dict(_DummyRegistry._meta)


def test_cli_command_wiring_inprocess(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    import packages.core.registry as registry_mod
    import packages.core.spec_from_prompt as spec_mod
    import packages.core.tool_generator as tool_gen_mod
    import packages.core.mcp_generator as mcp_gen_mod
    import packages.core.skill_generator as skill_gen_mod
    import packages.core.eval_generator as eval_gen_mod
    import packages.core.package_builder as pkg_mod
    import packages.core.tool_spec as tool_spec_mod
    import packages.runners.eval_runner as eval_runner_mod
    import packages.runners.tool_runner as tool_runner_mod
    import packages.validators.mcp_validator as mcp_val_mod
    import packages.validators.schema_validator as schema_mod
    import packages.validators.security_validator as sec_mod
    import packages.validators.skill_validator as skill_val_mod
    import packages.validators.test_validator as test_val_mod
    import packages.integrations.agent_skills.importer as importer_mod
    import packages.core.repo_hygiene as hygiene_mod

    dummy = _DummySpec(slug="dummy-tool", tags=["dummy", "tag"])
    monkeypatch.setattr(registry_mod, "ToolRegistry", _DummyRegistry)

    monkeypatch.setattr(
        spec_mod,
        "generate_spec_from_prompt",
        lambda *_args, **_kwargs: dummy,
    )

    def _scaffold(spec: _DummySpec, output_root: Path, overwrite: bool = False):
        del overwrite
        tool_dir = output_root / spec.slug
        (tool_dir / "tests").mkdir(parents=True, exist_ok=True)
        (tool_dir / "examples").mkdir(parents=True, exist_ok=True)
        (tool_dir / "skill").mkdir(parents=True, exist_ok=True)
        (tool_dir / "evals" / "cases").mkdir(parents=True, exist_ok=True)
        (tool_dir / "toolforge.yaml").write_text("slug: dummy-tool\n", encoding="utf-8")
        (tool_dir / "skill" / "SKILL.md").write_text("# skill\n", encoding="utf-8")
        (tool_dir / "evals" / "task_config.json").write_text("{}", encoding="utf-8")
        (tool_dir / "evals" / "cases" / "case-01.json").write_text("{}", encoding="utf-8")
        return [tool_dir / "toolforge.yaml"]

    monkeypatch.setattr(tool_gen_mod, "scaffold_tool", _scaffold)
    monkeypatch.setattr(mcp_gen_mod, "generate_mcp_server", lambda *_a, **_k: [tmp_path / "mcp" / "server.py"])
    monkeypatch.setattr(skill_gen_mod, "generate_skill", lambda *_a, **_k: [tmp_path / "skill" / "SKILL.md"])
    monkeypatch.setattr(eval_gen_mod, "generate_eval", lambda *_a, **_k: [tmp_path / "evals" / "task_config.json"])

    monkeypatch.setattr(tool_spec_mod.ToolSpec, "from_yaml", classmethod(lambda _cls, _path: dummy))

    monkeypatch.setattr(schema_mod, "validate_yaml_file", lambda _path: dummy)
    monkeypatch.setattr(sec_mod, "validate_security", lambda _spec: [])
    monkeypatch.setattr(mcp_val_mod, "validate_mcp_server", lambda _spec, _mcp_dir: [])
    monkeypatch.setattr(skill_val_mod, "validate_skill_file", lambda _path: [])

    pass_report = SimpleNamespace(all_passed=True, passed=1, failed=0, errors=0, skipped=0, failures=[])
    monkeypatch.setattr(test_val_mod, "run_tests", lambda _td: pass_report)
    monkeypatch.setattr(test_val_mod, "run_safety_checks", lambda _spec, _td: pass_report)

    monkeypatch.setattr(
        tool_runner_mod,
        "run_tool",
        lambda *_a, **_k: SimpleNamespace(success=True, output='{"ok": true}', error="", exit_code=0),
    )

    eval_report = SimpleNamespace(
        pass_rate=1.0,
        overall_pass=True,
        results=[SimpleNamespace(case_id="case-1", passed=True, score=1.0, details="ok", error="")],
    )
    monkeypatch.setattr(eval_runner_mod, "run_evals", lambda *_a, **_k: eval_report)

    monkeypatch.setattr(pkg_mod, "build_package", lambda *_a, **_k: tmp_path / "dist" / "dummy-tool-0.1.0.zip")
    monkeypatch.setattr(importer_mod, "import_skill", lambda *_a, **_k: [tmp_path / "skills" / "generated" / "SKILL.md"])
    monkeypatch.setattr(hygiene_mod, "scan_repo_hygiene", lambda _root: SimpleNamespace(has_issues=False, issues=[]))

    assert runner.invoke(cli, ["init", str(tmp_path)]).exit_code == 0
    assert runner.invoke(cli, ["new", "tool", "--from-prompt", "dummy prompt"]).exit_code == 0
    assert runner.invoke(cli, ["generate", "mcp", "dummy-tool"]).exit_code == 0
    assert runner.invoke(cli, ["generate", "skill", "dummy-tool"]).exit_code == 0
    assert runner.invoke(cli, ["generate", "eval", "dummy-tool"]).exit_code == 0
    assert runner.invoke(cli, ["validate", "dummy-tool"]).exit_code == 0
    assert runner.invoke(cli, ["run", "dummy-tool", "--input", "k=v"]).exit_code == 0
    assert runner.invoke(cli, ["eval", "dummy-tool"]).exit_code == 0
    assert runner.invoke(cli, ["package", "dummy-tool"]).exit_code == 0
    assert runner.invoke(cli, ["registry", "list"]).exit_code == 0
    assert runner.invoke(cli, ["registry", "search", "tag"]).exit_code == 0
    assert runner.invoke(cli, ["registry", "info", "dummy-tool"]).exit_code == 0

    skill_file = tmp_path / "legacy" / "SKILL.md"
    skill_file.parent.mkdir(parents=True, exist_ok=True)
    skill_file.write_text("# legacy\n", encoding="utf-8")
    assert runner.invoke(cli, ["install", str(skill_file)]).exit_code == 0
    assert runner.invoke(cli, ["doctor"]).exit_code == 0


def test_cli_run_invalid_input_and_eval_failure(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    import packages.core.registry as registry_mod
    import packages.core.tool_spec as tool_spec_mod
    import packages.runners.eval_runner as eval_runner_mod
    import packages.runners.tool_runner as tool_runner_mod

    dummy = _DummySpec(slug="dummy-tool")
    monkeypatch.setattr(registry_mod, "ToolRegistry", _DummyRegistry)
    monkeypatch.setattr(tool_spec_mod.ToolSpec, "from_yaml", classmethod(lambda _cls, _path: dummy))
    monkeypatch.setattr(
        tool_runner_mod,
        "run_tool",
        lambda *_a, **_k: SimpleNamespace(success=False, output="", error="resolved outside allowed_read_paths", exit_code=1),
    )

    fail_report = SimpleNamespace(
        pass_rate=0.0,
        overall_pass=False,
        results=[SimpleNamespace(case_id="case-1", passed=False, score=0.0, details="", error="boom")],
    )
    monkeypatch.setattr(eval_runner_mod, "run_evals", lambda *_a, **_k: fail_report)

    tool_dir = tmp_path / "tools" / "generated" / "dummy-tool"
    tool_dir.mkdir(parents=True, exist_ok=True)
    (tool_dir / "toolforge.yaml").write_text("slug: dummy-tool\n", encoding="utf-8")

    assert runner.invoke(cli, ["run", "dummy-tool", "--input", "bad-format"]).exit_code == 1
    assert runner.invoke(cli, ["run", "dummy-tool", "--input", "k=v"]).exit_code == 1
    assert runner.invoke(cli, ["eval", "dummy-tool"]).exit_code == 1


def test_registry_info_missing_tool(tmp_path: Path) -> None:
    runner = CliRunner()
    init_result = runner.invoke(cli, ["init", str(tmp_path)], catch_exceptions=False)
    assert init_result.exit_code == 0
    result = runner.invoke(cli, ["registry", "info", "missing"], catch_exceptions=False)
    assert result.exit_code == 1


def test_validate_accepts_skipped_only_test_report(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    import packages.core.registry as registry_mod
    import packages.core.tool_spec as tool_spec_mod
    import packages.validators.mcp_validator as mcp_val_mod
    import packages.validators.schema_validator as schema_mod
    import packages.validators.security_validator as sec_mod
    import packages.validators.skill_validator as skill_val_mod
    import packages.validators.test_validator as test_val_mod

    dummy = _DummySpec(slug="dummy-tool")
    monkeypatch.setattr(registry_mod, "ToolRegistry", _DummyRegistry)
    monkeypatch.setattr(tool_spec_mod.ToolSpec, "from_yaml", classmethod(lambda _cls, _path: dummy))
    monkeypatch.setattr(schema_mod, "validate_yaml_file", lambda _path: dummy)
    monkeypatch.setattr(sec_mod, "validate_security", lambda _spec: [])
    monkeypatch.setattr(mcp_val_mod, "validate_mcp_server", lambda _spec, _mcp_dir: [])
    monkeypatch.setattr(skill_val_mod, "validate_skill_file", lambda _path: [])

    skipped_report = SimpleNamespace(
        all_passed=True,
        passed=0,
        failed=0,
        errors=0,
        skipped=1,
        failures=[],
    )
    monkeypatch.setattr(test_val_mod, "run_tests", lambda _td: skipped_report)
    monkeypatch.setattr(test_val_mod, "run_safety_checks", lambda _spec, _td: skipped_report)

    tool_dir = tmp_path / "tools" / "generated" / "dummy-tool"
    (tool_dir / "tests").mkdir(parents=True, exist_ok=True)
    (tool_dir / "evals" / "cases").mkdir(parents=True, exist_ok=True)
    (tool_dir / "skill").mkdir(parents=True, exist_ok=True)
    (tool_dir / "toolforge.yaml").write_text("slug: dummy-tool\n", encoding="utf-8")
    (tool_dir / "evals" / "task_config.json").write_text("{}", encoding="utf-8")
    (tool_dir / "evals" / "cases" / "case-01.json").write_text("{}", encoding="utf-8")
    (tool_dir / "skill" / "SKILL.md").write_text("# skill\n", encoding="utf-8")

    result = runner.invoke(cli, ["validate", "dummy-tool"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "All validations passed." in result.output
