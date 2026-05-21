#!/usr/bin/env python3
"""Profile helpers for Toolathlon validation scripts."""
from __future__ import annotations

import json
import os
from pathlib import Path


class ProfileConfigError(RuntimeError):
    """Raised when profile configuration is invalid or unavailable."""


def get_profile_name() -> str:
    return os.environ.get("TOOLATHLON_PROFILE", "smoke").strip() or "smoke"


def get_profile_dir(repo_root: Path, profile: str) -> Path:
    return repo_root / "profiles" / profile


def _load_profile_json(repo_root: Path, profile: str, filename: str) -> dict:
    profile_file = get_profile_dir(repo_root, profile) / filename
    if not profile_file.exists():
        raise ProfileConfigError(
            f"Profile file not found: {profile_file}. "
            f"Set TOOLATHLON_PROFILE to an existing profile (e.g. smoke/full)."
        )

    try:
        payload = json.loads(profile_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProfileConfigError(
            f"Invalid JSON in profile file {profile_file}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise ProfileConfigError(
            f"Profile file must contain a JSON object: {profile_file}"
        )

    return payload


def load_profile_servers(
    repo_root: Path,
    profile: str | None = None,
) -> list[str]:
    effective_profile = profile or get_profile_name()
    payload = _load_profile_json(
        repo_root,
        effective_profile,
        "mcp_servers.json",
    )

    servers = payload.get("servers")
    if not isinstance(servers, list) or not servers:
        raise ProfileConfigError(
            "Profile "
            f"{effective_profile} must define a non-empty 'servers' list"
        )

    normalized: list[str] = []
    for server in servers:
        if not isinstance(server, str) or not server.strip():
            raise ProfileConfigError(
                "Profile "
                f"{effective_profile} contains an invalid server entry: "
                f"{server!r}"
            )
        normalized.append(server.strip())

    return normalized
