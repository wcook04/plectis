#!/usr/bin/env bash
set -u

suite="first-wave"
emit="receipts/cold_clone_probe.json"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --suite)
      suite="${2:-}"
      shift 2
      ;;
    --emit)
      emit="${2:-}"
      shift 2
      ;;
    --help|-h)
      echo "usage: ./bootstrap.sh --suite first-wave --emit receipts/cold_clone_probe.json"
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "$(dirname "$emit")" receipts/first_wave

if [ -n "${PYTHONPATH:-}" ]; then
  export PYTHONPATH="src:${PYTHONPATH}"
else
  export PYTHONPATH="src"
fi
export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"

if [ -n "${MICROCOSM_PYTHON:-}" ]; then
  py_bin="$MICROCOSM_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  py_bin="python3"
elif command -v python >/dev/null 2>&1; then
  py_bin="python"
else
  echo "missing Python interpreter: set MICROCOSM_PYTHON or install python3" >&2
  exit 127
fi

"$py_bin" -m microcosm_core.cold_clone_probe --suite "$suite" --emit "$emit"
