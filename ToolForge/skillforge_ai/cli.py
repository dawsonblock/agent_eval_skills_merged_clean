from __future__ import annotations

from importlib import import_module


def main() -> None:
    """Run the SkillForge CLI from the skillforge_ai package namespace."""
    cli_module = import_module("apps.cli.skillforge_cli.main")
    cli_module.main(standalone_mode=True)


if __name__ == "__main__":
    main()
