# macOS + VS Code (No Docker)

Use this flow when Docker is unavailable and you only need smoke-profile validation.

## Bootstrap

```bash
brew install python@3.12 node
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e "ToolForge[dev]"
pip install pytest
```

## Install workspace dependencies

```bash
cd agent-skills-curated
npm install
cd ..

cd toolathlon-gym-curated
./scripts/build_smoke_artifacts.sh
cd ..
```

## Validate smoke release

```bash
./scripts/validate_release_smoke.sh
```

Expected outputs are written under:

- `release_artifacts/validation_logs/`
