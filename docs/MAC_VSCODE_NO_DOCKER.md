# Mac / VS Code / No-Docker Setup

This repository should be validated with Python 3.12 and Node 20+.

## Python

```bash
brew install python@3.12
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
pip install pytest
pip install -e "ToolForge[dev]"
```

## Node

```bash
brew install node
node --version
npm --version
```

## Agent Skills

```bash
cd agent-skills-curated
npm install
node bin/cli.js list
node bin/cli.js eval --json
cd ..
```

## Toolathlon smoke profile

```bash
cd toolathlon-gym-curated
./scripts/build_smoke_artifacts.sh
./scripts/run_smoke_profile.sh
cd ..
```

## Full validation

```bash
./scripts/validate_release_smoke.sh
```

The full Toolathlon profile is experimental unless explicitly release-gated.
