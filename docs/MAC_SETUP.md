# macOS Setup (Python 3.12)

This project recommends Python 3.12 for release smoke validation.

## Option A: pyenv

```bash
brew install pyenv
pyenv install 3.12.7
pyenv local 3.12.7
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e "ToolForge[dev]"
```

## Option B: Homebrew Python

```bash
brew install python@3.12
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e "ToolForge[dev]"
```

## Verification

```bash
python --version
cd ToolForge
python -m pytest -q
toolforge doctor
```
