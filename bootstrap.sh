#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

suite="first-wave"
emit=".microcosm/cold_clone_probe.json"

usage() {
  cat <<'USAGE'
Usage: ./bootstrap.sh [--suite SUITE] [--emit RECEIPT_PATH]

Run the Microcosm cold-clone probe from the repository root.

Options:
  --suite SUITE          Probe suite to run (default: first-wave)
  --emit RECEIPT_PATH    Receipt path to write (default: .microcosm/cold_clone_probe.json)
  -h, --help             Show this help message without running the probe

Environment:
  MICROCOSM_PYTHON       Python executable override for public bootstrap runs
  PYTHON                 Fallback Python executable override
USAGE
}

require_value() {
  local flag="$1"
  local value="${2:-}"
  if [[ -z "$value" || "$value" == --* ]]; then
    echo "missing value for $flag" >&2
    usage >&2
    exit 2
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --suite)
      require_value "$1" "${2:-}"
      suite="${2:-}"
      shift 2
      ;;
    --emit)
      require_value "$1" "${2:-}"
      emit="${2:-}"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}src"
if [[ -n "${MICROCOSM_PYTHON:-}" ]]; then
  python_bin="$MICROCOSM_PYTHON"
elif [[ -n "${PYTHON:-}" ]]; then
  python_bin="$PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  python_bin="python3"
elif command -v python >/dev/null 2>&1; then
  python_bin="python"
else
  echo "python3 or python is required" >&2
  exit 127
fi

"$python_bin" -m microcosm_core.cold_clone_probe --suite "$suite" --emit "$emit"

printf 'Microcosm cold-clone probe passed\n'
printf 'suite: %s\n' "$suite"
printf 'receipt: %s\n' "$emit"
