# Contributing to ToolForge

## Local development prerequisites

```bash
cd ToolForge
python -m pip install -e ".[dev]"
```

## SkillForge AI test gate

Run this before submitting SkillForge AI changes:

```bash
cd ToolForge
PYTHONPATH=. pytest -q tests/test_skillforge_ai
```

## Notes

- Keep changes scoped and deterministic.
- Prefer workspace-relative paths in registries.
- Avoid introducing optional runtime dependencies without guarded fallbacks.
