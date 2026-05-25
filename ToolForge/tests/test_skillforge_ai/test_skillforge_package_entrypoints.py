from __future__ import annotations


from skillforge_ai import cli_main


def test_skillforge_ai_exposes_cli_entrypoint() -> None:
    assert callable(cli_main)
