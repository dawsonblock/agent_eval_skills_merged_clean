# ToolForge Release Verification (Prototype)

Date: 2026-05-17
Scope: Clean-environment acceptance verification and shutdown/hang reliability checks.
Repository: agent_eval_skills_merged_clean
Subproject: ToolForge

## Environment
- OS: macOS
- Fresh venv: `/tmp/tf_release_venv`
- Install mode: editable (`pip install -e ".[dev]"`)
- Timeout parity: GNU timeout available as `gtimeout` (installed via Homebrew `coreutils`)

## 1) Baseline installability and health
Command:
```bash
source /tmp/tf_release_venv/bin/activate
cd ToolForge
python -m pip install -e ".[dev]"
toolforge doctor
toolforge --help
```
Result:
- Dependency install succeeded.
- `toolforge doctor` passed all checks.
- `toolforge --help` displayed full command set.

## 2) CSV cleaner proof path (clean workspace)
Workspace: `/tmp/tf_release_csv`

Command sequence:
```bash
toolforge init .
toolforge new tool --from-prompt "Create a tool that cleans CSV files"
toolforge generate mcp csv-cleaner
toolforge generate skill csv-cleaner
toolforge generate eval csv-cleaner
toolforge validate csv-cleaner
toolforge run csv-cleaner --input input_path=examples/input.csv
(toolforge run csv-cleaner --input input_path=../../../etc/passwd && exit 1 || true)
toolforge eval csv-cleaner
toolforge package csv-cleaner
```
Result:
- Full flow passed end-to-end.
- Traversal attack was blocked with path validation failure.
- Eval pass rate: 100.0%.
- Package built: `/tmp/tf_release_csv/dist/csv-cleaner-0.1.0.zip`.

## 3) Full test suite and quality gates
Command:
```bash
cd ToolForge
pytest -q
ruff check packages apps
mypy packages apps
```
Result:
- `pytest -q`: 79 passed, clean exit.
- Coverage gate passed: 63.33% (required 60%).
- Ruff passed.
- Mypy passed.

## 4) JSON schema validator no-hang check
Workspace: `/tmp/tf_release_json`

Primary command (strict timeout parity):
```bash
gtimeout 30 toolforge eval json-schema-validator
```
Result:
- Completed with exit code 0 under GNU timeout wrapper.
- Eval pass rate: 100.0%.
- No hang observed.

(Compatibility fallback used earlier before `gtimeout` was installed: Python subprocess timeout=30s, also passed.)

## 5) Local-file-hasher flow (ToolForge generated-tool preservation)
Workspace: `/tmp/tf_release_hash`

Command sequence:
```bash
toolforge init .
toolforge new tool --from-prompt "Create a tool that computes SHA256 hashes for local files"
toolforge generate mcp local-file-hasher
toolforge generate skill local-file-hasher
toolforge generate eval local-file-hasher
toolforge validate local-file-hasher
toolforge run local-file-hasher --input file_path=examples/sample.txt
(toolforge run local-file-hasher --input file_path=../../../etc/passwd && exit 1 || true)
toolforge eval local-file-hasher
toolforge package local-file-hasher
```
Result:
- Full flow passed end-to-end.
- Traversal attack blocked correctly.
- Eval pass rate: 100.0%.
- Package built successfully.

## 6) Root demo verification
Command:
```bash
cd /Users/dawsonblock/Downloads/agent_eval_skills_merged_clean
bash scripts/demo_csv_cleaner.sh
```
Result:
- Demo completed successfully with all steps passing.

## 7) CSV package content checks
Artifact:
- `/tmp/tf_release_csv/dist/csv-cleaner-0.1.0.zip`

Verification result:
- `required_missing = []`
- `forbidden_found = []`

Interpretation:
- Required generated artifacts present.
- No stale runtime/test/cache junk bundled.

## Final status
This verification pass meets the requested acceptance checks in a clean environment, including strict timeout parity on macOS via `gtimeout`, and confirms no observable eval shutdown hang in the validated scenarios.

Note: This report describes prototype verification outcomes for this run only; it is not a claim of production readiness.
