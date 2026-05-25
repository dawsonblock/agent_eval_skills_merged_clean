from __future__ import annotations
# mypy: disable-error-code=import-untyped

from pathlib import Path
from typing import Any

from skillforge_ai.errors import SkillForgeDependencyError


_INSTALL_HINT = (
    "Missing dependency: ruamel.yaml. "
    "Run: cd ToolForge && python -m pip install -e '.[dev]'"
)


def dump_yaml(payload: dict[str, Any], output_path: Path) -> None:
    """Write YAML using ruamel.yaml, then PyYAML, else fail with clear guidance."""
    try:
        from ruamel.yaml import YAML  # type: ignore

        yaml = YAML()
        yaml.default_flow_style = False
        with output_path.open("w", encoding="utf-8") as handle:
            yaml.dump(payload, handle)
        return
    except ModuleNotFoundError:
        pass

    try:
        import yaml as pyyaml  # type: ignore

        with output_path.open("w", encoding="utf-8") as handle:
            pyyaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=False)
        return
    except ModuleNotFoundError as exc:
        raise SkillForgeDependencyError(_INSTALL_HINT) from exc
