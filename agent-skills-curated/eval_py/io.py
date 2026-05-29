"""
I/O utilities for prompt/response audit logging and result saving.
"""

import json
from pathlib import Path
from typing import Any


def save_json(obj: Any, path: str):
    def _default(o):
        # Handle datetime and other non-serializable types
        if hasattr(o, 'isoformat'):
            return o.isoformat()
        return str(o)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, default=_default)


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def log_raw_prompt_response(prompt: str, response: str, log_dir: str, suffix: str = "") -> str:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    idx = 1
    while True:
        fname = f"raw_prompt_response{suffix}_{idx}.json"
        fpath = Path(log_dir) / fname
        if not fpath.exists():
            break
        idx += 1
    data = {"prompt": prompt, "response": response}
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return str(fpath)
