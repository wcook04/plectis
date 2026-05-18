#!/usr/bin/env bash
set -u

suite="first-wave"
emit="receipts/cold_clone_probe.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --suite)
      suite="${2:-}"
      shift 2
      ;;
    --emit)
      emit="${2:-}"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}src"
if command -v python >/dev/null 2>&1; then
  python -m microcosm_core.cold_clone_probe --suite "$suite" --emit "$emit"
else
  python3 -m microcosm_core.cold_clone_probe --suite "$suite" --emit "$emit"
fi
