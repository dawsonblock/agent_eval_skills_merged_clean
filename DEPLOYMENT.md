# Deployment Guide

Prerequisite: run smoke validation and ensure required evidence artifacts pass before using this guide for release promotion. See [VALIDATION_EVIDENCE.md](VALIDATION_EVIDENCE.md) and [ACCEPTANCE_CHECKLIST_PHASE_13.md](ACCEPTANCE_CHECKLIST_PHASE_13.md).

Status claims in packaged ZIPs are advisory unless the matching evidence artifact bundle is published for the same archive hash.

Current smoke release-candidate archive SHA256: `9f206ffbdcfe83a2772579ea830c9124b930e6fae4240ee1817b2fac31616251` (see [RELEASE_ATTESTATION_2026-05-22.md](RELEASE_ATTESTATION_2026-05-22.md)).

Canonical attested pair:

- `agent_eval_skills_merged_clean-pruned-smoke.zip`
  - SHA256: `9f206ffbdcfe83a2772579ea830c9124b930e6fae4240ee1817b2fac31616251`
- `agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip`
  - SHA256: `f365e50185cc1a37a0127c7c048a63e9ffb1a5e3aa755517bdaa45c5fd26f3c3`

Wrapper/source ZIP uploads and independently regenerated ZIPs are not the attested release unless their hashes match the attestation.

## System Requirements

- Python 3.9-3.12 (3.12 preferred for release-proof validation runs)
- PostgreSQL 14+ (for toolathlon-gym-curated)
- Docker & Docker Compose (optional, for sandboxed execution)
- 2GB free disk space
- 512MB RAM minimum

## Installation

### From Source

```bash
# Clone the repository
git clone <repository-url>
cd agent_eval_skills_merged_clean

# Install ToolForge
cd ToolForge
pip install -e .

# Install toolathlon-gym-curated
cd ../toolathlon-gym-curated
pip install -e .

# Install agent-skills-curated dependencies
cd ../agent-skills-curated
npm install  # if running Node CLI
```

### From PyPI (Coming Soon)

```bash
pip install toolforge
```

## Configuration

### 1. Environment Setup

Copy and configure environment variables:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Logging configuration
TOOLFORGE_LOG_LEVEL=INFO
TOOLFORGE_SANDBOX_LEVEL=2
TOOLFORGE_DOCKER_ENABLED=true

# Model configuration
MODEL_PLATFORM=openai_compatible
MODEL_NAME=claude-sonnet-4-5
MODEL_API_KEY=sk-your-key
MODEL_API_URL=https://api.example.com/v1

# Database configuration
DATABASE_URL=postgresql://user:password@localhost:5432/toolathlon
```

### 2. Database Setup (Toolathlon)

```bash
# Start PostgreSQL
docker compose -f toolathlon-gym-curated/docker-compose.yml up -d postgres

# Initialize database (auto-runs on first start)
# Check logs to confirm initialization
docker compose -f toolathlon-gym-curated/docker-compose.yml logs postgres
```

### 3. Install Development Dependencies

```bash
cd ToolForge
pip install -e ".[dev]"

# Optional: Install security tools
pip install bandit pip-audit
```

## Verification

### Test ToolForge Installation

```bash
# Check version
toolforge --version

# List available commands
toolforge --help

# Run test suite
cd ToolForge
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=packages --cov=apps
```

### Test Toolathlon MCP Servers

```bash
cd toolathlon-gym-curated

# List all server tools
python test_mcp_servers.py --list-tools

# Test specific server
python test_mcp_servers.py arxiv-latex-mcp --list-tools

# Verbose output with errors
python test_mcp_servers.py --list-tools --verbose
```

### Test Agent Skills CLI

```bash
cd agent-skills-curated

# List available skills
node bin/cli.js list

# Evaluate a skill
node bin/cli.js evaluate skills/coding-agents-and-ides/skill-creator
```

## Development Workflow

### 1. Setup Pre-commit Hooks

Pre-commit hooks automatically lint and format code before commits:

```bash
pip install pre-commit
pre-commit install
```

The hooks will:

- Format code with ruff
- Check type hints with mypy
- Remove trailing whitespace
- Validate YAML/JSON

### 2. Run Tests Locally

```bash
cd ToolForge

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_tool_spec.py -v

# Run with coverage
pytest tests/ --cov --cov-report=html
# Open htmlcov/index.html to view coverage

# Run in watch mode (requires pytest-watch)
ptw tests/
```

### 3. Type Checking

```bash
cd ToolForge

# Check all code
mypy packages/ apps/

# Check with strict mode (strict mode recommended)
mypy packages/ apps/ --strict
```

### 4. Security Scanning

```bash
cd ToolForge

# Check for hardcoded secrets, path traversal, etc.
bandit -r packages/ apps/

# Check dependencies for known vulnerabilities
pip-audit
```

## Controlled Deployment

## Distribution ZIP Hygiene

Use the canonical release packager (recommended):

```bash
make release-zip
```

This calls `scripts/create_release_zip.sh`, which both builds the archive and validates that forbidden metadata/cache entries are not present.

Optional output path override:

```bash
RELEASE_ZIP_OUTPUT=dist/pruned-smoke-rc.zip make release-zip
```

Optional hash lock (fail closed on byte drift):

```bash
EXPECTED_RELEASE_SHA256=9f206ffbdcfe83a2772579ea830c9124b930e6fae4240ee1817b2fac31616251 \
RELEASE_ZIP_OUTPUT=dist/agent_eval_skills_merged_clean-pruned-smoke.zip \
make release-zip
```

Compatibility command matching the pruned smoke release naming in checklists:

```bash
bash scripts/package_clean_zip.sh
```

Optional output path for the compatibility command:

```bash
OUT=/tmp/agent_eval_skills_merged_clean-pruned-smoke.zip bash scripts/package_clean_zip.sh
```

Canonical pair verification before distribution (required):

```bash
make verify-release-pair
```

Equivalent local pre-publish gate alias:

```bash
make prepublish-gate
```

Override paths when artifacts are stored outside the repository root:

```bash
bash scripts/verify_release_pair.sh \
   --release /path/to/agent_eval_skills_merged_clean-pruned-smoke.zip \
   --evidence /path/to/agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip
```

If verification fails, classify the package as an unbound wrapper/source bundle and do not publish as release-candidate until a new matching manifest + attestation is issued.

Uploaded wrapper/source triage before release claims:

```bash
make classify-release-upload RELEASE_ZIP=/path/to/uploaded-wrapper.zip
```

Optional pair-aware triage with evidence and JSON verdict output:

```bash
make classify-release-upload \
   RELEASE_ZIP=/path/to/uploaded-wrapper.zip \
   EVIDENCE_ZIP=/path/to/agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip \
   JSON_OUTPUT=.validation_logs/release_upload_triage_verdict.json
```

Without matching canonical release+evidence hash verification, classify as unbound wrapper/source bundle.

### CI Pre-Publish Gate (Recommended)

Two CI checks are now available:

1. Automatic check on `push`/`pull_request`: `Validate Workspace / Verify Canonical Attested Pair`
2. Manual pre-publish gate: `Release Attested Pair Gate`
3. Manual upload triage gate: `Release Upload Triage`

Run the manual workflow before any release upload/distribution step.

1. Workflow: `.github/workflows/release-attested-gate.yml`
2. Behavior:
   - Runs `scripts/verify_release_pair.sh`
   - Hard-fails on filename/hash mismatch or forbidden metadata entries
   - Runs `scripts/verify_evidence_bundle.sh` for evidence-value enforcement
   - Uploads verified canonical pair as run artifact only when checks pass

Uploaded wrapper triage workflow:

1. Workflow: `.github/workflows/release-upload-triage.yml`
2. Behavior:
   - Runs `scripts/classify_release_upload.sh`
   - Verifies canonical attested release/evidence pair classification
   - Uploads `.validation_logs/release_upload_triage_verdict.json` for audit

For third-party uploaded wrapper/source artifacts, use local operator triage:

```bash
make operator-release-upload-triage RELEASE_ZIP=/path/to/uploaded-wrapper.zip
```

Optional pair-aware local triage:

```bash
make operator-release-upload-triage \
   RELEASE_ZIP=/path/to/uploaded-wrapper.zip \
   EVIDENCE_ZIP=/path/to/agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip \
   JSON_OUTPUT=.validation_logs/release_upload_triage_verdict.json
```

Treat this workflow as a required pre-publish approval gate in repository policy.

For exact GitHub settings click-paths, follow [RELEASE_GATE_RUNBOOK.md](RELEASE_GATE_RUNBOOK.md).

### Repository Rule Configuration (Required)

To prevent accidental wrapper/source bundle publication, enforce the following in GitHub branch protection or repository rulesets for `main`:

1. Require status checks to pass before merging.
2. Mark `Validate Workspace / Unified Workspace Validation` as required.
3. Mark `Validate Workspace / Verify Canonical Attested Pair` as required for release PRs or release-branch promotion flow.
4. Mark `Validate Workspace / Classify Uploaded Release Artifact` as required for release PRs or release-branch promotion flow.
5. Require pull request reviews before merging release workflow or attestation/manifest changes.

Operational recommendation:

1. Keep `Release Attested Pair Gate` as a manual approval gate before any release upload action.
2. If your release process uses a dedicated release branch, enforce the same required check set on that branch.
3. Do not treat uploaded artifacts as release-candidate unless the gate run succeeded for the exact pair being published.

Manual fallback (if you need direct zip invocation):

When creating release ZIP files on macOS, exclude metadata files and cache artifacts so distributed archives do not include `__MACOSX` or `._*` entries.

```bash
zip -r dist/agent_eval_skills_merged_clean.zip . \
   -x "*/__MACOSX/*" \
   -x "*/._*" \
   -x "*/.DS_Store" \
   -x "*/node_modules/*" \
   -x "*/.validation_logs/*" \
   -x "*/__pycache__/*" \
   -x "*/.pytest_cache/*"
```

If metadata files already exist, remove them before packaging:

```bash
find . -name ".DS_Store" -delete
find . -name "._*" -delete
find . -name "__MACOSX" -type d -prune -exec rm -rf {} +
```

### Via Docker Compose

```bash
cd toolathlon-gym-curated

# Build images
docker compose build

# Start services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### Manual Deployment (Controlled Environments Only)

1. **Install in controlled environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -e ToolForge/
   ```

2. **Set environment variables:**

   ```bash
   export TOOLFORGE_LOG_LEVEL=WARNING
   export TOOLFORGE_SANDBOX_LEVEL=3
   export MODEL_API_KEY=<environment-key>
   ```

3. **Run service:**

   ```bash
   # As CLI
   toolforge eval my-tool --task-dir /data/tasks
   
   # As MCP server
   python -m fastmcp run
   ```

## Troubleshooting

### Python Version Issues

```bash
# Verify Python version
python --version  # Should be 3.9-3.12 (3.12 preferred for release-proof runs)

# If using pyenv
pyenv local 3.12.12
pyenv rehash
```

### Import Errors

```bash
# Reinstall in development mode
cd ToolForge
pip install -e . --force-reinstall --no-cache-dir

# Clear cached files
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

### Test Failures

```bash
# Run with verbose output
pytest tests/ -vv

# Run single test with debug
pytest tests/test_tool_spec.py::test_name -vv --pdb

# Check environment
pip list | grep -E "pydantic|pytest|click"
```

### MCP Server Issues

```bash
# Check server startup
python test_mcp_servers.py arxiv-latex-mcp --list-tools --verbose

# Check logs
tail -f ~/.toolforge/logs/mcp.log

# Verify configuration
cat configs/mcp_servers/arxiv-latex-mcp.yaml
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql "postgresql://user:password@localhost:5432/toolathlon" -c "SELECT 1"

# Check Docker status
docker ps | grep postgres
docker logs <container-id>

# Reset database
docker compose down
docker volume rm <volume-name>
docker compose up
```

## Performance Optimization

### For Local Development

```bash
# Disable Docker sandbox (faster iteration)
export TOOLFORGE_SANDBOX_LEVEL=1

# Enable debug logging
export TOOLFORGE_LOG_LEVEL=DEBUG
```

### For Controlled Environments

```bash
# Use Docker sandbox (safer)
export TOOLFORGE_SANDBOX_LEVEL=4

# Disable debug logging
export TOOLFORGE_LOG_LEVEL=WARNING

# Set reasonable timeouts
export TOOLFORGE_TOOL_TIMEOUT=300  # 5 minutes
```

## Monitoring & Logs

### View ToolForge Logs

Logs are output to stdout in JSON format by default. Pipe to a tool for better viewing:

```bash
# Pretty-print JSON logs
toolforge eval my-tool 2>&1 | jq .

# Filter by level
toolforge eval my-tool 2>&1 | jq 'select(.level=="ERROR")'

# Monitor in real-time
tail -f ~/.toolforge/logs/toolforge.log | jq .
```

### Check Service Health

```bash
# ToolForge
toolforge --version

# MCP Servers
python test_mcp_servers.py --list-tools

# Database
psql "$DATABASE_URL" -c "SELECT version();"
```

## Updating

### Update Dependencies

```bash
cd ToolForge
pip install -U -e .

# Update toolathlon
cd ../toolathlon-gym-curated
pip install -U -e .
```

### Update Code

```bash
git pull origin main
pip install -e ToolForge/ --force-reinstall
pytest ToolForge/tests/ -v  # Verify nothing broke
```

## Support

For issues or questions:

1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Review [GitHub Issues](https://github.com/yourusername/agent_eval_skills_merged_clean/issues)
3. See [CONTRIBUTING.md](CONTRIBUTING.md) for development questions
4. Review [SECURITY.md](SECURITY.md) for security concerns
