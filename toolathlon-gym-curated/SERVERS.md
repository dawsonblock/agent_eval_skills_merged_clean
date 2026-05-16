# Toolathlon MCP Servers

**Total:** 25 servers | **Operational:** 11 | **Require External Setup:** 13 | **Missing:** 1

## Operational Servers (11/25) ✅

These servers have no external dependencies and are ready to use:

### ✅ arxiv-latex-mcp (4 tools)
LaTeX paper processing and analysis. Extract and process academic papers in LaTeX format.

### ✅ arxiv_local (4 tools)
ArXiv local search without external API. Query academic papers from local cache.

### ✅ emails (25 tools)
Email management operations. Send, read, and manage emails programmatically.

### ✅ excel (25 tools)
Excel spreadsheet operations. Read, write, and manipulate Excel files.

### ✅ pdf-tools (9 tools)
PDF processing. Extract text, images, and metadata from PDF documents.

### ✅ pptx (37 tools)
PowerPoint presentation generation. Create and modify PPTX files programmatically.

### ✅ scholarly_search (2 tools)
Academic search functionality. Query scholarly sources and papers.

### ✅ snowflake (14 tools)
Snowflake SQL query execution. Execute queries against Snowflake data warehouse.

### ✅ terminal (2 tools)
Shell command execution. Run shell commands safely in subprocess context.

### ✅ word (54 tools)
Word document operations. Create and modify DOCX files programmatically.

### ✅ yahoo-finance (10 tools)
Financial data retrieval. Get stock prices, historical data, and financial metrics.

---

## Servers Requiring External Setup (13/25) ⚠️

These servers return `[ERROR] Broken pipe` because they require external credentials, services, or API keys to function. The error is expected and indicates the server attempted to initialize but cannot proceed without proper setup.

| Server | Requires | Setup Instructions |
|--------|----------|-------------------|
| **12306** | Chinese train API | Register at [12306.com](https://www.12306.cn/), obtain API credentials |
| **canvas** | Canvas LMS instance | Self-hosted Canvas installation or institutional account |
| **filesystem** | Filesystem access | Security-restricted by design; configure allowed paths |
| **google_calendar** | Google OAuth token | Create [Google Cloud project](https://console.cloud.google.com/), enable Calendar API, generate OAuth credentials |
| **google_forms** | Google OAuth token | Create [Google Cloud project](https://console.cloud.google.com/), enable Forms API, generate OAuth credentials |
| **google_sheet** | Google OAuth token | Create [Google Cloud project](https://console.cloud.google.com/), enable Sheets API, generate OAuth credentials |
| **howtocook** | Database seed | Initialize database with sample recipes/meals data |
| **memory** | Knowledge base | Configure embeddings model and knowledge base storage |
| **notion** | Notion API token | Create [Notion integration](https://www.notion.so/my-integrations), obtain access token |
| **npx-fetch** | NPM registry access | Requires network access to npm package registry |
| **playwright_with_chunk** | Browser instance | Requires Chrome/Chromium browser (install via `playwright install`) |
| **woocommerce** | WooCommerce store | Configure store URL, API key, API secret |
| **youtube** | YouTube API key | Create [Google Cloud project](https://console.cloud.google.com/), enable YouTube Data API, generate API key |

### Setup Examples

#### Google APIs (google_calendar, google_forms, google_sheet)

```bash
# 1. Create Google Cloud project
gcloud projects create my-toolathlon-project

# 2. Enable APIs
gcloud services enable calendar.googleapis.com
gcloud services enable forms.googleapis.com
gcloud services enable sheets.googleapis.com

# 3. Create OAuth credentials
# Navigate to https://console.cloud.google.com/apis/credentials
# Create "OAuth 2.0 Client ID" for "Desktop application"
# Download credentials JSON

# 4. Set environment variable or config
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

#### Notion API

```bash
# 1. Create Notion integration
# Visit https://www.notion.so/my-integrations

# 2. Click "Create new integration"
# Follow the prompts

# 3. Copy "Internal Integration Token"
# Set as environment variable
export NOTION_API_TOKEN=secret_xxxxx
```

#### WooCommerce

```bash
# 1. Get store URL, API key, API secret from WordPress admin

# 2. Set environment variables
export WOOCOMMERCE_URL=https://mystore.com
export WOOCOMMERCE_KEY=ck_xxxxx
export WOOCOMMERCE_SECRET=cs_xxxxx
```

#### YouTube API

```bash
# 1. Create Google Cloud project
gcloud projects create my-youtube-project

# 2. Enable YouTube Data API v3
gcloud services enable youtube.googleapis.com

# 3. Create API key
# Visit https://console.cloud.google.com/apis/credentials
# Click "Create Credentials" → "API Key"

# 4. Set environment variable
export YOUTUBE_API_KEY=AIzaSy_xxxxx
```

---

## Missing Server (1/25) ❌

### ❌ youtube_transcript

**Status:** Missing local server directory  
**Issue:** Configuration references non-existent server implementation  
**Solution:** Either implement the server or remove from `configs/mcp_servers/` directory

---

## Running Servers Locally

### List All Servers and Their Tools

```bash
cd toolathlon-gym-curated

python test_mcp_servers.py --list-tools
```

Expected output:
```
Testing 25 MCP server(s)...
  [OK_LIST] arxiv-latex-mcp              tools=4
  [OK_LIST] arxiv_local                  tools=4
  [OK_LIST] emails                       tools=25
  [OK_LIST] excel                        tools=25
  [OK_LIST] pdf-tools                    tools=9
  [OK_LIST] pptx                         tools=37
  [OK_LIST] scholarly_search             tools=2
  [OK_LIST] snowflake                    tools=14
  [OK_LIST] terminal                     tools=2
  [OK_LIST] word                         tools=54
  [OK_LIST] yahoo-finance                tools=10
  [ERROR] 12306                          tools=0  err=[Errno 32] Broken pipe
  ... (other external servers)
  
Results: 11/25 passed, 14 failed
```

### Test Specific Server

```bash
# Test arxiv-latex-mcp
python test_mcp_servers.py arxiv-latex-mcp --list-tools

# Verbose output with error details
python test_mcp_servers.py arxiv-latex-mcp --list-tools --verbose
```

### Verbose Testing

```bash
# Show detailed output including stderr
python test_mcp_servers.py --list-tools --verbose
```

---

## Server Configuration

Each server has a configuration file in `configs/mcp_servers/{server-name}.yaml`:

```yaml
# Example: configs/mcp_servers/arxiv-latex-mcp.yaml
name: arxiv-latex-mcp
command:
  - python
  - -m
  - arxiv_latex_mcp
environment: {}
```

### Adding a New Server

1. Create server implementation in `local_servers/{server-name}/`
2. Create configuration in `configs/mcp_servers/{server-name}.yaml`
3. Add entry to `test_mcp_servers.py` if needed
4. Test with: `python test_mcp_servers.py {server-name} --list-tools`

---

## Server Status Legend

| Status | Meaning | Action |
|--------|---------|--------|
| `[OK_LIST]` | Server operational, tools listed | Ready to use |
| `[ERROR] Broken pipe` | Server crashed on init | Check external dependencies |
| `[INIT_FAIL]` | Initialization error | Check server configuration |
| ❌ Missing | Directory not found | Implement or remove |

---

## Common Issues

### "Broken pipe" on all servers

**Cause:** Missing dependencies or incorrect Python version

**Solution:**
```bash
# Reinstall dependencies
pip install -e .

# Verify Python version
python --version  # Should be 3.12+
```

### Specific server fails with "ModuleNotFoundError"

**Solution:**
```bash
# Check if server module is installed
pip list | grep server-name

# Reinstall
pip install -e . --force-reinstall
```

### Google API servers fail with "credentials not found"

**Solution:**
```bash
# Set authentication environment variable
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Or configure in .env
echo "GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json" >> .env
```

### Notion server returns "Invalid API token"

**Solution:**
```bash
# Verify token format
echo $NOTION_API_TOKEN  # Should start with "secret_"

# Regenerate token if needed
# Visit https://www.notion.so/my-integrations
```

---

## Performance Notes

- **Operational servers (11):** Should complete `--list-tools` in <2 seconds
- **External servers (13):** May take 5-30 seconds depending on network/timeouts
- **Missing server (1):** Should fail immediately with file not found

Total test run: ~1-2 minutes for full suite with network delays

---

## Contributing

To add a new MCP server:

1. Implement server in `local_servers/{name}/`
2. Add configuration in `configs/mcp_servers/{name}.yaml`
3. Test: `python test_mcp_servers.py {name} --list-tools`
4. Update this document with server details

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.
