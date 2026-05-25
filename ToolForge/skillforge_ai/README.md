# SkillForge AI

SkillForge AI provides a local, deterministic workflow for creating and operating skills.

## Development setup

```bash
cd ToolForge
python -m pip install -e ".[dev]"
```

## Run tests

```bash
cd ToolForge
PYTHONPATH=. pytest -q tests/test_skillforge_ai
```

## CLI smoke flow

```bash
cd ToolForge
PYTHONPATH=. python -m skillforge_ai.cli create "make a skill that cleans CSV files"
PYTHONPATH=. python -m skillforge_ai.cli validate csv-cleaner
PYTHONPATH=. python -m skillforge_ai.cli run csv-cleaner --input input_path=skills/csv-cleaner/examples/messy.csv
PYTHONPATH=. python -m skillforge_ai.cli package csv-cleaner
```
