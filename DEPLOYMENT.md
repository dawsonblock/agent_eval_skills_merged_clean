# Deployment Guide

## System Requirements

- Python 3.12+
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

## Production Deployment

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

### Manual Deployment

1. **Install in production environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -e ToolForge/
   ```

2. **Set environment variables:**
   ```bash
   export TOOLFORGE_LOG_LEVEL=WARNING
   export TOOLFORGE_SANDBOX_LEVEL=3
   export MODEL_API_KEY=<production-key>
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
python --version  # Should be 3.12+

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

### For Production

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
