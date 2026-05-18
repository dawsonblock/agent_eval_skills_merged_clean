"""Comprehensive tests for ToolRegistry to improve coverage.

Covers initialization, registration, metadata updates, querying, persistence,
edge cases, and error handling.
"""
import logging
import tempfile
from pathlib import Path

import pytest

from packages.core.registry import ToolRegistry
from packages.core.tool_spec import ToolSpec


@pytest.fixture
def sample_spec() -> ToolSpec:
    """Minimal valid ToolSpec for testing."""
    return ToolSpec(
        name="Test Tool",
        slug="test-tool",
        description="A test tool for registry coverage.",
        parameters=[
            {"name": "input_path", "type": "string", "description": "Input file", "required": True}
        ],
        output={"type": "string", "description": "Processed output"},
    )


@pytest.fixture
def temp_registry_path() -> Path:
    """Temporary registry file path (cleaned up automatically)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "toolforge_registry.json"


class TestToolRegistryInit:
    """Tests for ToolRegistry initialization and persistence loading."""

    def test_init_empty_registry(self, temp_registry_path: Path):
        """New registry file does not exist -> starts empty."""
        reg = ToolRegistry(temp_registry_path)
        assert len(reg) == 0
        assert list(reg) == []

    def test_init_with_corrupt_file_logs_warning(self, temp_registry_path: Path, caplog):
        """Corrupt JSON triggers warning and empty start."""
        temp_registry_path.write_text("{invalid json}", encoding="utf-8")
        with caplog.at_level(logging.WARNING):
            reg = ToolRegistry(temp_registry_path)
        assert len(reg) == 0
        assert "corrupt or unreadable" in caplog.text.lower()

    def test_init_loads_existing_valid_registry(self, temp_registry_path: Path, sample_spec: ToolSpec):
        """Valid existing registry is loaded correctly."""
        reg = ToolRegistry(temp_registry_path)
        reg.register(sample_spec)
        # Re-instantiate to test loading
        reg2 = ToolRegistry(temp_registry_path)
        assert len(reg2) == 1
        loaded = reg2.find("test-tool")
        assert loaded is not None
        assert loaded.slug == "test-tool"


class TestToolRegistryRegister:
    """Tests for register() and basic mutation."""

    def test_register_new_tool(self, temp_registry_path: Path, sample_spec: ToolSpec):
        reg = ToolRegistry(temp_registry_path)
        reg.register(sample_spec)
        assert len(reg) == 1
        assert reg.find("test-tool") is not None

    def test_register_updates_existing(self, temp_registry_path: Path, sample_spec: ToolSpec):
        reg = ToolRegistry(temp_registry_path)
        reg.register(sample_spec)
        # Modify and re-register
        sample_spec.description = "Updated description"
        reg.register(sample_spec)
        assert len(reg) == 1  # Still one entry
        loaded = reg.find("test-tool")
        assert loaded.description == "Updated description"

    def test_register_sets_initial_metadata(self, temp_registry_path: Path, sample_spec: ToolSpec):
        reg = ToolRegistry(temp_registry_path)
        reg.register(sample_spec, status="validated")
        meta = reg.get_metadata("test-tool")
        assert meta is not None
        assert meta["status"] == "validated"
        assert "registered_at" in meta
        assert meta["eval_score"] is None


class TestToolRegistryStatusAndMetadata:
    """Tests for set_* methods."""

    def test_set_status_success_and_failure(self, temp_registry_path: Path, sample_spec: ToolSpec):
        reg = ToolRegistry(temp_registry_path)
        reg.register(sample_spec)
        assert reg.set_status("test-tool", "eval_passed") is True
        meta = reg.get_metadata("test-tool")
        assert meta["status"] == "eval_passed"
        assert "status_updated_at" in meta

        assert reg.set_status("nonexistent", "failed") is False

    def test_set_eval_score(self, temp_registry_path: Path, sample_spec: ToolSpec):
        reg = ToolRegistry(temp_registry_path)
        reg.register(sample_spec)
        assert reg.set_eval_score("test-tool", 0.95) is True
        meta = reg.get_metadata("test-tool")
        assert meta["eval_score"] == 0.95
        assert meta["last_eval"] is not None

    def test_set_validation_result(self, temp_registry_path: Path, sample_spec: ToolSpec):
        reg = ToolRegistry(temp_registry_path)
        reg.register(sample_spec)
        assert reg.set_validation_result("test-tool", True) is True
        meta = reg.get_metadata("test-tool")
        assert meta["validation_passed"] is True

    def test_set_last_run(self, temp_registry_path: Path, sample_spec: ToolSpec):
        reg = ToolRegistry(temp_registry_path)
        reg.register(sample_spec)
        assert reg.set_last_run("test-tool", success=True, run_type="normal") is True
        meta = reg.get_metadata("test-tool")
        assert meta["last_run_success"] is True
        assert meta["last_successful_run"] is not None

        assert reg.set_last_run("test-tool", success=False) is True
        meta = reg.get_metadata("test-tool")
        assert meta["last_run_success"] is False
        assert meta["last_failed_run"] is not None

    def test_set_paths(self, temp_registry_path: Path, sample_spec: ToolSpec):
        reg = ToolRegistry(temp_registry_path)
        reg.register(sample_spec)
        assert reg.set_package_path("test-tool", "/tmp/pkg.zip") is True
        assert reg.set_mcp_path("test-tool", "/tmp/mcp") is True
        assert reg.set_skill_path("test-tool", "/tmp/skill.md") is True
        assert reg.set_eval_path("test-tool", "/tmp/eval") is True

        meta = reg.get_metadata("test-tool")
        assert meta["package_path"] == "/tmp/pkg.zip"


class TestToolRegistryQuery:
    """Tests for find, list, search, and iteration."""

    def test_find_nonexistent(self, temp_registry_path: Path):
        reg = ToolRegistry(temp_registry_path)
        assert reg.find("does-not-exist") is None

    def test_list_all_and_len_and_iter(self, temp_registry_path: Path, sample_spec: ToolSpec):
        reg = ToolRegistry(temp_registry_path)
        reg.register(sample_spec)
        specs = reg.list_all()
        assert len(specs) == 1
        assert len(reg) == 1
        assert list(reg)[0].slug == "test-tool"

    def test_list_by_status(self, temp_registry_path: Path, sample_spec: ToolSpec):
        reg = ToolRegistry(temp_registry_path)
        reg.register(sample_spec, status="generated")
        generated = reg.list_by_status("generated")
        assert len(generated) == 1
        validated = reg.list_by_status("validated")
        assert len(validated) == 0

    def test_search_by_tag(self, temp_registry_path: Path, sample_spec: ToolSpec):
        reg = ToolRegistry(temp_registry_path)
        sample_spec.tags = ["data", "csv", "cleaning"]
        reg.register(sample_spec)
        results = reg.search_by_tag("data")
        assert len(results) == 1
        results_case = reg.search_by_tag("DATA")
        assert len(results_case) == 1
        no_results = reg.search_by_tag("nonexistent-tag")
        assert len(no_results) == 0


class TestToolRegistryDeregister:
    """Tests for deregister."""

    def test_deregister_existing(self, temp_registry_path: Path, sample_spec: ToolSpec):
        reg = ToolRegistry(temp_registry_path)
        reg.register(sample_spec)
        assert reg.deregister("test-tool") is True
        assert len(reg) == 0
        assert reg.find("test-tool") is None

    def test_deregister_nonexistent(self, temp_registry_path: Path):
        reg = ToolRegistry(temp_registry_path)
        assert reg.deregister("ghost") is False


class TestToolRegistryCorruptSpecHandling:
    """Tests graceful handling of corrupt spec data in queries."""

    def test_find_corrupt_spec(self, temp_registry_path: Path, caplog):
        reg = ToolRegistry(temp_registry_path)
        # Manually insert corrupt entry
        reg._entries["bad-slug"] = {"spec": {"invalid": "data"}}
        reg._save()
        with caplog.at_level(logging.WARNING):
            result = reg.find("bad-slug")
        assert result is None
        assert "corrupt spec" in caplog.text.lower()

    def test_list_all_skips_corrupt(self, temp_registry_path: Path, sample_spec: ToolSpec, caplog):
        reg = ToolRegistry(temp_registry_path)
        reg.register(sample_spec)
        reg._entries["bad"] = {"spec": "not-a-dict"}
        reg._save()
        with caplog.at_level(logging.WARNING):
            specs = reg.list_all()
        assert len(specs) == 1  # Only the good one
        assert any("corrupt entry" in msg.lower() for msg in caplog.messages)


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
