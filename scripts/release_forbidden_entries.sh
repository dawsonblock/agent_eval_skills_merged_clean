#!/usr/bin/env bash
# Shared forbidden-entry policy for release and evidence ZIP hygiene checks.

set -euo pipefail

FORBIDDEN_POLICY_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_FORBIDDEN_CONFIG_PATH="${RELEASE_FORBIDDEN_CONFIG_PATH:-$FORBIDDEN_POLICY_SCRIPT_DIR/../.release-config/forbidden_entries.txt}"

if [ ! -f "$RELEASE_FORBIDDEN_CONFIG_PATH" ]; then
	echo "Error: forbidden-entry config file missing: $RELEASE_FORBIDDEN_CONFIG_PATH" >&2
	return 1 2>/dev/null || exit 1
fi

declare -a RELEASE_FORBIDDEN_TOKENS=()
declare -a RELEASE_FORBIDDEN_ZIP_EXCLUDES=()
RELEASE_FORBIDDEN_ENTRY_REGEX=''

_escape_regex_token() {
	local token="$1"
	printf '%s' "$token" | sed -e 's/[.[\^$(){}+?|]/\\&/g'
}

load_release_forbidden_policy() {
	local line
	local token
	local regex_parts=()
	RELEASE_FORBIDDEN_TOKENS=()
	RELEASE_FORBIDDEN_ZIP_EXCLUDES=()

	while IFS= read -r line || [ -n "$line" ]; do
		token="${line%%#*}"
		token="${token%${token##*[![:space:]]}}"
		token="${token#${token%%[![:space:]]*}}"

		if [ -z "$token" ]; then
			continue
		fi

		RELEASE_FORBIDDEN_TOKENS+=("$token")

		case "$token" in
			"._*")
				regex_parts+=("\\._")
				RELEASE_FORBIDDEN_ZIP_EXCLUDES+=("._*" "*/._*")
				;;
			".DS_Store")
				regex_parts+=("\\.DS_Store$")
				RELEASE_FORBIDDEN_ZIP_EXCLUDES+=(".DS_Store" "*/.DS_Store")
				;;
			*)
				regex_parts+=("$(_escape_regex_token "$token")/")
				RELEASE_FORBIDDEN_ZIP_EXCLUDES+=("$token/*" "*/$token/*")
				;;
		esac
	done < "$RELEASE_FORBIDDEN_CONFIG_PATH"

	if [ "${#regex_parts[@]}" -eq 0 ]; then
		echo "Error: forbidden-entry config has no entries: $RELEASE_FORBIDDEN_CONFIG_PATH" >&2
		return 1
	fi

	RELEASE_FORBIDDEN_ENTRY_REGEX="(^|/)($(IFS='|'; echo "${regex_parts[*]}"))"
}

load_release_forbidden_policy
