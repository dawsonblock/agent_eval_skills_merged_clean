"""
Schema contract tests for SkillForge metadata and registry artifacts.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate


def _load_schema(root: Path, name: str) -> dict:
    path = root / "skillforge_ai" / "schemas" / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_skill_schema_accepts_valid_payload() -> None:
    root = Path(__file__).resolve().parents[2]
    schema = _load_schema(root, "skill_schema.json")

    payload = {
        "name": "csv-cleaner",
        "description": "Cleans CSV files.",
        "category": "data",
        "version": "0.1.0",
        "inputs": [{"name": "input_path", "type": "string", "required": True}],
        "outputs": [
            {"name": "output_path", "type": "string", "required": True}
        ],
        "tools_required": ["tool/main.py"],
        "mcp_servers": [],
        "permissions": ["read_files", "write_files"],
        "risk_level": "low",
        "validation": {
            "metadata": "pending",
            "syntax": "pending",
            "tests": "pending",
            "package": "pending",
            "smoke": "pending",
        },
    }

    validate(instance=payload, schema=schema)


def test_skill_schema_rejects_unknown_category() -> None:
    root = Path(__file__).resolve().parents[2]
    schema = _load_schema(root, "skill_schema.json")

    payload = {
        "name": "csv-cleaner",
        "description": "Cleans CSV files.",
        "category": "not-a-real-category",
        "version": "0.1.0",
        "inputs": [{"name": "input_path", "type": "string", "required": True}],
        "outputs": [
            {"name": "output_path", "type": "string", "required": True}
        ],
        "tools_required": ["tool/main.py"],
        "mcp_servers": [],
        "permissions": ["read_files"],
        "risk_level": "low",
        "validation": {
            "metadata": "pending",
            "syntax": "pending",
            "tests": "pending",
            "package": "pending",
            "smoke": "pending",
        },
    }

    with pytest.raises(ValidationError):
        validate(instance=payload, schema=schema)


def test_skill_schema_rejects_unknown_permission() -> None:
    root = Path(__file__).resolve().parents[2]
    schema = _load_schema(root, "skill_schema.json")

    payload = {
        "name": "csv-cleaner",
        "description": "Cleans CSV files.",
        "category": "data",
        "version": "0.1.0",
        "inputs": [{"name": "input_path", "type": "string", "required": True}],
        "outputs": [
            {"name": "output_path", "type": "string", "required": True}
        ],
        "tools_required": ["tool/main.py"],
        "mcp_servers": [],
        "permissions": ["unknown_permission"],
        "risk_level": "low",
        "validation": {
            "metadata": "pending",
            "syntax": "pending",
            "tests": "pending",
            "package": "pending",
            "smoke": "pending",
        },
    }

    with pytest.raises(ValidationError):
        validate(instance=payload, schema=schema)


def test_registry_schema_accepts_valid_payload() -> None:
    root = Path(__file__).resolve().parents[2]
    schema = _load_schema(root, "registry_schema.json")

    payload = [
        {
            "name": "csv-cleaner",
            "path": "skills/csv-cleaner",
            "category": "data",
            "description": "Cleans CSV files.",
            "permissions": ["read_files", "write_files"],
            "risk_level": "low",
            "validation_status": "passed",
            "package_hash": None,
            "last_run": None,
        }
    ]

    validate(instance=payload, schema=schema)


def test_permission_schema_accepts_valid_payload() -> None:
    root = Path(__file__).resolve().parents[2]
    schema = _load_schema(root, "permission_schema.json")

    payload = {
        "version": "0.1.0",
        "default_mode": "interactive",
        "rules": [
            {"action": "read_files", "tier": "safe"},
            {
                "action": "shell_commands",
                "tier": "approval_required",
                "reason": "can modify host state",
            },
        ],
        "approvals": [
            {
                "action": "shell_commands",
                "approved": True,
                "timestamp": "2026-05-24T12:00:00Z",
                "reason": "User approved this run",
            }
        ],
    }

    validate(instance=payload, schema=schema)
