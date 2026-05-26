#!/usr/bin/env bash
# Verify structural hygiene of the source/release bundle.
# Checks:
#   1) Required top-level paths exist inside the ZIP
#   2) No forbidden metadata/cache entries (per shared policy)
#   3) release_classification field == SOURCE_BUNDLE (from RELEASE_STATUS.json)
#   4) No absolute local paths embedded in any bundled non-documentation file
#   5) Claims-matrix consistency: CLAIMS_MATRIX.md present and non-empty
#   6) RELEASE_STATUS.json structural required fields
#
# Usage: bash scripts/verify_source_bundle_hygiene.sh --zip PATH

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

FORBIDDEN_POLICY_FILE="$SCRIPT_DIR/release_forbidden_entries.sh"
if [ ! -f "$FORBIDDEN_POLICY_FILE" ]; then
  echo "Error: forbidden-entry policy file missing: $FORBIDDEN_POLICY_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$FORBIDDEN_POLICY_FILE"

ZIP_PATH=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --zip)
      ZIP_PATH="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: bash scripts/verify_source_bundle_hygiene.sh --zip PATH"
      exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [ -z "$ZIP_PATH" ]; then
  echo "Error: --zip is required" >&2
  echo "Usage: bash scripts/verify_source_bundle_hygiene.sh --zip PATH" >&2
  exit 1
fi

if [ ! -f "$ZIP_PATH" ]; then
  echo "Error: ZIP not found: $ZIP_PATH" >&2
  exit 1
fi

FAILURES=0
fail() { echo "FAIL: $1" >&2; FAILURES=$((FAILURES + 1)); }
pass() { echo "PASS: $1"; }

echo "== Source Bundle Hygiene Check =="
echo "ZIP: $ZIP_PATH"
echo ""

# Pre-compute ZIP listing to a temp file to avoid SIGPIPE issues.
# Under set -o pipefail, "echo $BIG_VAR | grep -q pattern" can fail because
# grep -q closes the pipe after the first match, causing echo/zipinfo to receive
# SIGPIPE, which pipefail then propagates as a non-zero exit even inside an if.
# Writing to a tmpfile and grep-ing the file avoids this entirely.
ZIP_LISTING_TMP="$(mktemp)"
trap 'rm -f "$ZIP_LISTING_TMP"' EXIT

python3 -c "
import zipfile, sys
with zipfile.ZipFile(sys.argv[1]) as z:
    for n in z.namelist():
        print(n)
" "$ZIP_PATH" > "$ZIP_LISTING_TMP"

# 1. Required layout paths
REQUIRED_PATHS=(
  "ToolForge/"
  "agent-skills-curated/"
  "toolathlon-gym-curated/"
  "RELEASE_STATUS.json"
  "RELEASE_MANIFEST.json"
  "CLAIMS_MATRIX.md"
)

for req in "${REQUIRED_PATHS[@]}"; do
  # Support both flat (entry starts at top-level) and rooted (prefixed by one dir) layouts
  if grep -qE "^${req}|^[^/]+/${req}" "$ZIP_LISTING_TMP"; then
    pass "Required path present: $req"
  else
    fail "Required path missing: $req"
  fi
done

# 2. Forbidden metadata/cache entries
if [ -n "$RELEASE_FORBIDDEN_ENTRY_REGEX" ]; then
  FORBIDDEN="$(grep -E "$RELEASE_FORBIDDEN_ENTRY_REGEX" "$ZIP_LISTING_TMP" || true)"
else
  FORBIDDEN=""
fi
if [ -z "$FORBIDDEN" ]; then
  pass "No forbidden metadata/cache entries"
else
  fail "Forbidden entries found in ZIP:"
  echo "$FORBIDDEN" >&2
fi

# 3. RELEASE_STATUS.json release_classification
RELEASE_STATUS_JSON="$REPO_ROOT/RELEASE_STATUS.json"
if [ -f "$RELEASE_STATUS_JSON" ]; then
  CLASSIFICATION="$(python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
print(d.get('release_classification', ''))
" "$RELEASE_STATUS_JSON")"
  if [ "$CLASSIFICATION" = "SOURCE_BUNDLE" ]; then
    pass "release_classification=SOURCE_BUNDLE"
  else
    if [ -n "$CLASSIFICATION" ]; then
      fail "release_classification expected SOURCE_BUNDLE, got: $CLASSIFICATION"
    else
      pass "release_classification field absent (acceptable for older format)"
    fi
  fi
else
  fail "RELEASE_STATUS.json not found in repo root"
fi

# 4. No absolute local paths in bundled non-documentation files.
# DOC_EXTS (.md/.txt/.rst) may legitimately contain shell examples with absolute
# paths (e.g., "cd /Users/..."). Scan only structured data/code file extensions.
# Also skip .trunk/out/ build-cache files and test fixtures with generic usernames.
ABS_PATH_HITS="$(python3 - "$ZIP_PATH" <<'PYEOF'
import zipfile, re, sys
pat = re.compile(r'/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/')
DOC_EXTS = {'.md', '.txt', '.rst'}
CODE_EXTS = {'.json', '.env', '.py', '.sh', '.cfg', '.toml', '.yaml', '.yml', '.ts', '.js'}
# Generic placeholder usernames used in test fixtures -- not real local paths
PLACEHOLDER_USERS = re.compile(r'/(Users|home)/(alice|bob|charlie|david\w*|example|user|test|foo|bar|username)/')
# Build-cache dirs that are runtime-generated, not hygiene-sensitive, including release artifacts
SKIP_PATH_PREFIX = ('.trunk/out/', '.trunk/plugins/', 'release_artifacts/', '.vscode/')
SKIP_DIR_CONTAINS = ('/__tests__/',)
# Skip known example/template config files (upstream vendored, users edit them)
SKIP_BASENAME = {'mcp-config.json'}
hits = []
with zipfile.ZipFile(sys.argv[1]) as z:
    for info in z.infolist():
        name = info.filename
        if any(name.startswith(p) for p in SKIP_PATH_PREFIX):
            continue
        if any(d in ('/' + name) for d in SKIP_DIR_CONTAINS):
            continue
        base = name.rsplit('/', 1)[-1]
        if base in SKIP_BASENAME:
            continue
        ext = ('.' + base.rsplit('.', 1)[-1].lower()) if '.' in base else ''
        if ext in DOC_EXTS:
            continue
        if ext not in CODE_EXTS:
            continue
        try:
            content = z.read(info).decode('utf-8', errors='ignore')
        except Exception:
            continue
        for lineno, line in enumerate(content.splitlines(), 1):
            if pat.search(line) and not PLACEHOLDER_USERS.search(line):
                hits.append(f'{name}:{lineno}: {line.strip()[:120]}')
                if len(hits) >= 10:
                    break
        if len(hits) >= 10:
            break
for h in hits:
    print(h)
PYEOF
)"

if [ -z "$ABS_PATH_HITS" ]; then
  pass "No absolute local paths in non-documentation bundled files"
else
  fail "Absolute local paths found in bundle (first 10 hits):"
  echo "$ABS_PATH_HITS" >&2
fi

# 5. Claims-matrix consistency: CLAIMS_MATRIX.md must be present and non-empty in repo
CLAIMS_MATRIX="$REPO_ROOT/CLAIMS_MATRIX.md"
if [ ! -f "$CLAIMS_MATRIX" ]; then
  fail "CLAIMS_MATRIX.md missing from repo root"
elif [ ! -s "$CLAIMS_MATRIX" ]; then
  fail "CLAIMS_MATRIX.md is empty"
else
  pass "CLAIMS_MATRIX.md present and non-empty"
fi

# 6. RELEASE_STATUS.json structural required fields
REQUIRED_STATUS_FIELDS=(
  "canonical_release_zip"
  "release_classification"
  "toolathlon_profile"
  "uploaded_archive_sha256"
  "canonical_release_sha256"
)
if [ -f "$RELEASE_STATUS_JSON" ]; then
  for field in "${REQUIRED_STATUS_FIELDS[@]}"; do
    VALUE="$(python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
v = d.get(sys.argv[2])
print('' if v is None else str(v))
" "$RELEASE_STATUS_JSON" "$field")"
    if [ -n "$VALUE" ]; then
      pass "RELEASE_STATUS.$field is set"
    else
      fail "RELEASE_STATUS.$field is missing or null"
    fi
  done
fi

echo ""
if [ "$FAILURES" -eq 0 ]; then
  echo "Source bundle hygiene check passed."
  exit 0
else
  echo "Source bundle hygiene check failed with $FAILURES failure(s)." >&2
  exit 1
fi
