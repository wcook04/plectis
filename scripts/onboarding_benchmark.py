from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def _run(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    result = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    elapsed = time.monotonic() - started
    return {
        "argv": argv,
        "cwd": str(cwd),
        "returncode": result.returncode,
        "seconds": round(elapsed, 3),
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }


def _bin_dir(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts"
    return venv_dir / "bin"


def _fail(payload: dict[str, Any], out: Path, code: int) -> None:
    payload["status"] = "fail"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raise SystemExit(code)


def _clone_checkout(repo_url: str, ref: str | None, work_dir: Path) -> tuple[Path, dict[str, Any]]:
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)
    checkout = work_dir / "plectis"
    step = _run(["git", "clone", "--depth", "1", "--no-tags", repo_url, str(checkout)], cwd=work_dir)
    if step["returncode"] != 0:
        return checkout, step
    if ref:
        checkout_step = _run(["git", "checkout", "--detach", ref], cwd=checkout)
        if checkout_step["returncode"] != 0:
            fetch_step = _run(["git", "fetch", "--depth", "1", "origin", ref], cwd=checkout)
            if fetch_step["returncode"] != 0:
                step["returncode"] = fetch_step["returncode"]
                step["stderr_tail"] = fetch_step["stderr_tail"]
                return checkout, step
            checkout_step = _run(["git", "checkout", "--detach", "FETCH_HEAD"], cwd=checkout)
        if checkout_step["returncode"] != 0:
            step["returncode"] = checkout_step["returncode"]
            step["stderr_tail"] = checkout_step["stderr_tail"]
            return checkout, step
    return checkout, step


def run_benchmark(args: argparse.Namespace) -> int:
    out = args.out.resolve()
    source_root = args.source_root.resolve()
    work_dir = args.work_dir.resolve()
    started = time.monotonic()
    payload: dict[str, Any] = {
        "schema_version": "plectis_onboarding_benchmark_v1",
        "status": "running",
        "repo_url": args.repo_url,
        "ref": args.ref,
        "source_mode": "cold_clone" if args.repo_url else "existing_checkout",
        "clone_seconds": None,
        "bootstrap_seconds": None,
        "smoke_seconds": None,
        "install_seconds": None,
        "installed_tour_seconds": None,
        "total_seconds": None,
        "commands": [],
        "budgets": {
            "bootstrap_seconds": 15,
            "smoke_seconds": 90,
            "cold_install_total_seconds": 300,
        },
        "budget_status": "not_checked",
    }

    checkout = source_root
    if args.repo_url:
        checkout, clone_step = _clone_checkout(args.repo_url, args.ref, work_dir)
        payload["commands"].append({"name": "clone", **clone_step})
        payload["clone_seconds"] = clone_step["seconds"]
        if clone_step["returncode"] != 0:
            _fail(payload, out, int(clone_step["returncode"]))

    env = {
        **os.environ,
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    }
    env["PYTHONPATH"] = "src"
    if args.python:
        env["PYTHON"] = args.python
        env["MICROCOSM_PYTHON"] = args.python

    steps: list[tuple[str, list[str], str]] = [
        ("bootstrap", ["./bootstrap.sh"], "bootstrap_seconds"),
        ("smoke", ["make", "smoke"], "smoke_seconds"),
        ("install", ["make", "install"], "install_seconds"),
    ]
    for name, argv, field in steps:
        step = _run(argv, cwd=checkout, env=env)
        payload["commands"].append({"name": name, **step})
        payload[field] = step["seconds"]
        if step["returncode"] != 0:
            _fail(payload, out, int(step["returncode"]))

    plectis = _bin_dir(checkout / ".venv") / ("plectis.exe" if os.name == "nt" else "plectis")
    installed_env = {**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
    installed_step = _run(
        [str(plectis), "tour", "--format", "text", "."],
        cwd=checkout,
        env=installed_env,
    )
    payload["commands"].append({"name": "installed_tour", **installed_step})
    payload["installed_tour_seconds"] = installed_step["seconds"]
    if installed_step["returncode"] != 0:
        _fail(payload, out, int(installed_step["returncode"]))

    payload["total_seconds"] = round(time.monotonic() - started, 3)
    budget_status = "pass"
    if payload["bootstrap_seconds"] is not None and payload["bootstrap_seconds"] > 15:
        budget_status = "watch"
    if payload["smoke_seconds"] is not None and payload["smoke_seconds"] > 90:
        budget_status = "watch"
    if payload["total_seconds"] is not None and payload["total_seconds"] > 300:
        budget_status = "watch"
    payload["budget_status"] = budget_status
    payload["status"] = "pass"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.keep_work_dir and args.repo_url:
        shutil.rmtree(work_dir, ignore_errors=True)
    print(f"Plectis onboarding benchmark: {payload['status']}")
    print(f"receipt: {out}")
    print(f"total_seconds: {payload['total_seconds']}")
    print(f"budget_status: {payload['budget_status']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record Plectis cold-clone onboarding timings.")
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--repo-url", default="")
    parser.add_argument("--ref", default="")
    parser.add_argument("--out", type=Path, default=Path(".microcosm/onboarding-benchmark.json"))
    parser.add_argument("--work-dir", type=Path, default=Path("/tmp/plectis-onboarding-benchmark"))
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--keep-work-dir", action="store_true")
    args = parser.parse_args(argv)
    return run_benchmark(args)


if __name__ == "__main__":
    raise SystemExit(main())
