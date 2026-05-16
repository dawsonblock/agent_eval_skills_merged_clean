"""Unit tests for rule-based spec generation from prompt."""
from __future__ import annotations

from packages.core.spec_from_prompt import generate_spec_from_prompt


def test_json_schema_validator_prompt_generation() -> None:
    spec = generate_spec_from_prompt(
        "Create a tool that validates JSON files against a schema"
    )

    assert spec.slug == "json-schema-validator"
    param_names = [p.name for p in spec.parameters]
    assert param_names == ["data_path", "schema_path", "output_path"]
    assert spec.security.allowed_extensions == [".json"]
    assert any(case.id == "case-03-safety-boundary" for case in spec.eval.cases)


def test_local_file_hasher_prompt_generation() -> None:
    spec = generate_spec_from_prompt(
        "Create a tool that computes sha256 checksums of local files"
    )

    assert spec.slug == "local-file-hasher"
    param_names = [p.name for p in spec.parameters]
    assert param_names == ["file_path", "algorithm", "output_path"]
    assert spec.security.allowed_read_paths
    assert any(case.id == "case-03-safety-boundary" for case in spec.eval.cases)
