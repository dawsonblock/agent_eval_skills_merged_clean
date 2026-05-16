"""
local-file-hasher — compute cryptographic hash of a local file.

Inputs (via TOOLFORGE_INPUTS env var, JSON dict):
  file_path  (str, required)  — path to file
  algorithm  (str, optional)  — md5 | sha256 (default) | sha512
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

_SUPPORTED = {"md5", "sha256", "sha512"}


def hash_file(file_path: str, algorithm: str = "sha256") -> dict:
    alg = algorithm.lower().strip()
    if alg not in _SUPPORTED:
        raise ValueError(f"Unsupported algorithm '{alg}'. Choose from: {', '.join(_SUPPORTED)}")

    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    h = hashlib.new(alg)
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)

    return {
        "file": str(p.resolve()),
        "algorithm": alg,
        "hash": h.hexdigest(),
        "size_bytes": p.stat().st_size,
    }


def main() -> None:
    raw = os.environ.get("TOOLFORGE_INPUTS", "{}")
    try:
        inputs = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Error parsing inputs: {e}", file=sys.stderr)
        sys.exit(1)

    file_path = inputs.get("file_path")
    if not file_path:
        print("Error: 'file_path' is required.", file=sys.stderr)
        sys.exit(1)

    algorithm = inputs.get("algorithm", "sha256")

    try:
        result = hash_file(file_path, algorithm)
        print(json.dumps(result, indent=2))
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
