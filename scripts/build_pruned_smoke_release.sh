#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DEFAULT="$ROOT/dist/agent_eval_skills_merged_clean-pruned-smoke-candidate.zip"
OUT="$OUT_DEFAULT"

usage() {
	cat <<'USAGE'
Usage: bash scripts/build_pruned_smoke_release.sh [--output PATH] [--canonical]

Options:
	--output PATH  Write archive to PATH.
	--canonical    Overwrite canonical archive path at repo root.
USAGE
}

while [ "$#" -gt 0 ]; do
	case "$1" in
		--output)
			if [ "$#" -lt 2 ]; then
				echo "Missing value for --output" >&2
				exit 1
			fi
			OUT="$2"
			shift 2
			;;
		--canonical)
			OUT="$ROOT/agent_eval_skills_merged_clean-pruned-smoke.zip"
			shift
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			echo "Unknown argument: $1" >&2
			usage >&2
			exit 1
			;;
	esac
done

cd "$ROOT"

mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"

# Reuse canonical packaging policy from create_release_zip.sh.
RELEASE_ZIP_OUTPUT="$OUT" bash scripts/create_release_zip.sh

echo "Built pruned smoke release archive: $OUT"
shasum -a 256 "$OUT"
