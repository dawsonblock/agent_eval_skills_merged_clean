from __future__ import annotations

from pathlib import Path

from skillforge_ai.chat_runtime import ChatRuntime


def run_chat(workspace_root: Path, provider: str = "rule_based") -> None:
    ChatRuntime(workspace_root=workspace_root, provider=provider).run_loop()
