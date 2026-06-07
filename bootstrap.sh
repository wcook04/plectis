#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

suite="first-wave"
emit=".microcosm/cold_clone_probe.json"
dry_run=0
show_version=0
supported_suites="first-wave"

usage() {
  cat <<'USAGE'
Usage: ./bootstrap.sh [--suite SUITE] [--emit RECEIPT_PATH] [--dry-run] [--version]

Run the Microcosm cold-clone probe from the repository root.

Options:
  --suite SUITE          Probe suite to run (default: first-wave; supported: first-wave)
  --emit RECEIPT_PATH    Receipt path to write (default: .microcosm/cold_clone_probe.json)
  --dry-run              Show the probe command without running or writing receipts
  --version              Show the Microcosm package version without running the probe
  -h, --help             Show this help message without running the probe

Environment:
  MICROCOSM_PYTHON       Python executable override for public bootstrap runs
  PYTHON                 Fallback Python executable override

Success output:
  Microcosm cold-clone probe passed
  suite: <suite>
  receipt: <receipt path>
  check: make smoke
  next: README.md#public-repo-map and README.md#component-map
USAGE
}

package_version() {
  awk -F'"' '/^version = / { print $2; exit }' pyproject.toml
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

validate_suite() {
  case "$suite" in
    first-wave)
      ;;
    *)
      echo "unknown suite: $suite" >&2
      echo "supported suites: $supported_suites" >&2
      usage >&2
      exit 2
      ;;
  esac
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
    --dry-run)
      dry_run=1
      shift
      ;;
    --version)
      show_version=1
      shift
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

validate_suite

if [[ "$show_version" == "1" ]]; then
  version="$(package_version)"
  if [[ -z "$version" ]]; then
    echo "could not read version from pyproject.toml" >&2
    exit 1
  fi
  printf 'microcosm %s\n' "$version"
  exit 0
fi

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

if [[ "$dry_run" == "1" ]]; then
  printf 'Microcosm cold-clone probe dry run\n'
  printf 'suite: %s\n' "$suite"
  printf 'receipt: %s\n' "$emit"
  printf 'python: %s\n' "$python_bin"
  printf 'pythonpath: %s\n' "$PYTHONPATH"
  printf 'command:'
  printf ' %q' "PYTHONPATH=$PYTHONPATH" "$python_bin" -m microcosm_core.cold_clone_probe --suite "$suite" --emit "$emit"
  printf '\n'
  printf 'check: make smoke\n'
  printf 'next: README.md#public-repo-map and README.md#component-map\n'
  exit 0
fi

"$python_bin" -m microcosm_core.cold_clone_probe --suite "$suite" --emit "$emit"

printf 'Microcosm cold-clone probe passed\n'
printf 'suite: %s\n' "$suite"
printf 'receipt: %s\n' "$emit"
printf 'check: make smoke\n'
printf 'next: README.md#public-repo-map and README.md#component-map\n'
