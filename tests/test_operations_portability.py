"""Real isolated imports and generated-worker execution without the old runtime."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib
import venv

import pytest


ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "scripts/release/verify_operations_install.py"

COMPONENT_KERNELS = {
    "budget_packing": "BudgetPacking", "dependency_reachability": "DependencyReachability",
    "egress_policy": "EgressPolicy", "evidence_diff": "EvidenceDiff",
    "information_flow": "InformationFlow", "mcp_authority": "McpAuthority",
    "navigation_metrics": "NavigationMetrics", "ownership_classification": "OwnershipClassification",
    "premise_ranking": "PremiseRanking", "sandbox_policy": "SandboxPolicy",
    "tactic_selection": "TacticSelection", "walkthrough_validation": "WalkthroughValidation",
}


@pytest.fixture
def isolated_python(tmp_path):
    """A stdlib-only installation with neither pip nor distribution metadata."""
    environment = tmp_path / "venv"
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    completed = subprocess.run(
        [str(python), "-I", "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        capture_output=True, text=True, check=True, timeout=15,
    )
    library = Path(completed.stdout.strip())
    working = tmp_path / "unrelated-project"
    working.mkdir()
    return python, library, working


def copy_components(library):
    shutil.copytree(ROOT / "src/plectis", library / "plectis",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def copy_formal_resources(python):
    prefix = python.parent.parent
    resources = (prefix / "share/plectis/formal/components").resolve()
    shutil.copytree(ROOT / "formal/components", resources)
    return resources


def run_smoke(python, working, *arguments, isolated=True):
    # A caller's source checkout must never rescue an incomplete installation.
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join((str(working), str(ROOT / "src"))),
                   "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [str(python), *(["-I"] if isolated else []), "-B", str(SMOKE), *arguments],
        cwd=working, env=environment, capture_output=True, text=True, timeout=120,
    )


def test_components_work_as_the_only_copied_package(isolated_python):
    python, library, working = isolated_python
    copy_components(library)
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    # Establish that this proves copy portability, not an accidental dependency
    # on the old runtime or a pip-generated plectis.dist-info directory.
    probe = subprocess.run(
        [str(python), "-I", "-c",
         "import importlib.util, importlib.metadata; "
         f"import plectis; assert plectis.__version__ == {version!r}; "
         "assert importlib.util.find_spec('microcosm_core') is None; "
         "assert importlib.util.find_spec('pip') is None; "
         "assert not [d for d in importlib.metadata.distributions() "
         "if d.metadata['Name'] == 'plectis']"],
        cwd=working, capture_output=True, text=True, timeout=15,
    )
    assert probe.returncode == 0, probe.stderr
    completed = run_smoke(python, working, "--require-compatibility", "--require-views", "--require-replay")
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "passed"
    assert result["repair"]["score"] == 10
    assert result["repair"]["unknown_effect_retained"] is True
    assert result["publish"]["stale_worker"] == "rejected"
    assert result["publish"]["historical_retry"] == "replayed"
    assert result["compatibility"]["continuation"] == ["read"]
    assert result["compatibility"]["counterexample_checked"] is True
    assert result["compatibility"]["stale_counterexample_rejected"] is True
    assert result["compatibility"]["missing_required_input_checked"] is True
    assert result["views"] == {
        "public_trace": ["Report A", "approved"], "private_reads_removed": True,
        "explicit_flow": "rejected", "private_control": "rejected",
        "private_record_values": "rejected",
    }
    assert result["replay"] == {
        "matching_observations": "accepted", "missing_or_duplicate": "rejected",
        "changed_identity_claim_source_input_payload": "rejected",
    }
    assert all(Path(origin).is_relative_to(library)
               for origin in result["installed_modules"].values())
    expected_sources = {
        f"plectis.{component}._generated.{kernel}":
            str((library / "plectis" / component / "_generated" / f"{kernel}.py").resolve())
        for component, kernel in (("repair", "Repair"), ("compatibility", "Compatibility"),
                                  ("compatibility", "Replay"),
                                  ("views", "Release"), ("replay", "ReplayAdmission"))
    }
    expected_sources.update({
        f"plectis.components.{slug}._generated.{kernel}":
            str((library / "plectis/components" / slug / "_generated" / f"{kernel}.py").resolve())
        for slug, kernel in COMPONENT_KERNELS.items()
    })
    assert result["components"] == {name: "passed" for name in COMPONENT_KERNELS}
    assert result["generated_sources"] == expected_sources
    assert result["component_manifests"] == {
        slug: str((library / "plectis/components" / slug / "_generated/GENERATED_SHA256.json").resolve())
        for slug in COMPONENT_KERNELS
    }
    assert list(working.iterdir()) == []


def test_copied_package_ignores_executable_ambient_shadows(isolated_python):
    python, library, working = isolated_python
    copy_components(library)
    marker = working / "shadow-executed"
    poison = f"from pathlib import Path\nPath({str(marker)!r}).touch()\nraise RuntimeError('shadow')\n"
    for relative in ("plectis/__init__.py", "BudgetPacking.py", "module_.py", "_dafny/__init__.py"):
        path = working / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(poison, encoding="utf-8")
    completed = run_smoke(python, working, "--require-compatibility", "--require-views", "--require-replay")
    assert completed.returncode == 0, completed.stderr
    assert not marker.exists()


def test_copied_package_checks_retained_formal_resources_when_requested(isolated_python):
    python, library, working = isolated_python
    copy_components(library)
    resources = copy_formal_resources(python)
    completed = run_smoke(python, working, "--require-formal-resources")
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["component_formal_resources"] == {
        slug: {"metadata": str(resources / slug / "metadata.json"),
               "source": str(resources / slug / f"{kernel}.dfy"),
               "evidence": "retained_hashes_checked"}
        for slug, kernel in COMPONENT_KERNELS.items()
    }


@pytest.mark.parametrize("changed", ["missing_source", "source", "mutant", "metadata", "unexpected", "symlink"])
def test_copied_formal_resource_damage_is_rejected(isolated_python, changed):
    python, library, working = isolated_python
    copy_components(library)
    resources = copy_formal_resources(python)
    formal = resources / "budget_packing"
    source = formal / "BudgetPacking.dfy"
    if changed == "missing_source":
        source.unlink()
    elif changed in ("source", "mutant"):
        path = source if changed == "source" else formal / "negative/FullBudgetPerItem.dfy"
        path.write_bytes(path.read_bytes() + b"\n// altered retained evidence\n")
    elif changed == "metadata":
        path = formal / "metadata.json"
        metadata = json.loads(path.read_text(encoding="utf-8"))
        metadata["generated_python"]["BudgetPacking.py"] = "0" * 64
        path.write_text(json.dumps(metadata), encoding="utf-8")
    elif changed == "unexpected":
        (formal / "unreviewed.dfy").write_text("module Unreviewed {}\n", encoding="utf-8")
    else:
        outside = working / "BudgetPacking.dfy"
        source.rename(outside)
        try:
            source.symlink_to(outside)
        except OSError as error:
            pytest.skip(f"file symlinks are unavailable: {error}")
    completed = run_smoke(python, working, "--require-formal-resources")
    assert completed.returncode != 0
    assert "operations install check failed" in completed.stderr
    assert not completed.stdout


def test_missing_install_cannot_use_inherited_pythonpath_or_working_directory(isolated_python):
    python, _, working = isolated_python
    # Both common shadowing routes are present; -I must ignore both.
    shutil.copytree(ROOT / "src/plectis", working / "plectis")
    completed = run_smoke(python, working, "--require-compatibility", "--require-views", "--require-replay")
    assert completed.returncode != 0
    assert "No module named 'plectis'" in completed.stderr
    assert not completed.stdout


def test_editable_checkout_import_is_rejected(isolated_python):
    python, library, working = isolated_python
    (library / "checkout.pth").write_text(str(ROOT / "src") + "\n", encoding="utf-8")
    completed = run_smoke(python, working)
    assert completed.returncode != 0
    assert "outside this Python installation" in completed.stderr
    assert not completed.stdout
    assert list(working.iterdir()) == []


@pytest.mark.parametrize(("component", "kernel", "arguments", "diagnostic"), [
    ("repair", "Repair", (), "kernel"),
    ("compatibility", "Compatibility", ("--require-compatibility",),
     "generated compatibility checker"),
    ("compatibility", "Replay", ("--require-compatibility",),
     "generated compatibility checker"),
    ("views", "Release", ("--require-views",), "generated-core worker"),
    ("replay", "ReplayAdmission", ("--require-replay",), "operations install check failed"),
])
def test_missing_generated_kernel_fails_the_smoke(
        isolated_python, component, kernel, arguments, diagnostic):
    python, library, working = isolated_python
    copy_components(library)
    (library / "plectis" / component / "_generated" / f"{kernel}.py").unlink()
    completed = run_smoke(python, working, *arguments)
    assert completed.returncode != 0
    assert diagnostic in completed.stderr
    assert not completed.stdout


def test_missing_compatibility_is_rejected_when_required(isolated_python):
    python, library, working = isolated_python
    copy_components(library)
    shutil.rmtree(library / "plectis/compatibility")
    completed = run_smoke(python, working, "--require-compatibility")
    assert completed.returncode != 0
    assert "plectis.compatibility" in completed.stderr
    assert not completed.stdout


def test_views_are_optional_unless_required(isolated_python):
    python, library, working = isolated_python
    copy_components(library)
    shutil.rmtree(library / "plectis/views")
    ordinary = run_smoke(python, working)
    assert ordinary.returncode == 0, ordinary.stderr
    assert "views" not in json.loads(ordinary.stdout)
    completed = run_smoke(python, working, "--require-views")
    assert completed.returncode != 0
    assert "plectis.views" in completed.stderr
    assert not completed.stdout


def test_views_requirement_is_independent_of_compatibility(isolated_python):
    python, library, working = isolated_python
    copy_components(library)
    shutil.rmtree(library / "plectis/compatibility")
    completed = run_smoke(python, working, "--require-views")
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["views"]["public_trace"] == ["Report A", "approved"]
    assert "compatibility" not in result
    assert "plectis.compatibility._generated.Compatibility" not in result["generated_sources"]
    assert "plectis.compatibility._generated.Replay" not in result["generated_sources"]
    assert "plectis.views._generated.Release" in result["generated_sources"]


def test_smoke_explains_required_isolation(isolated_python):
    python, library, working = isolated_python
    copy_components(library)
    completed = run_smoke(python, working, isolated=False)
    assert completed.returncode != 0
    assert "python -I" in completed.stderr
    assert not completed.stdout


def test_replay_requirement_is_independent_of_workflow_cores(isolated_python):
    python, library, working = isolated_python
    copy_components(library)
    for component in ("compatibility", "views"):
        shutil.rmtree(library / "plectis" / component)
    completed = run_smoke(python, working, "--require-replay")
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["replay"]["matching_observations"] == "accepted"
    assert "plectis.replay._generated.ReplayAdmission" in result["generated_sources"]
    shutil.rmtree(library / "plectis/replay")
    missing = run_smoke(python, working, "--require-replay")
    assert missing.returncode != 0
    assert "plectis.replay" in missing.stderr


@pytest.mark.parametrize("changed", ["source", "manifest", "source_and_manifest", "missing_licence", "shadow_package"])
def test_component_kernel_tampering_fails_installed_smoke(isolated_python, changed):
    python, library, working = isolated_python
    copy_components(library)
    generated = library / "plectis/components/dependency_reachability/_generated"
    marker = working / "shadow-executed"
    if changed == "missing_licence":
        (generated / "Dafny-LICENSE.txt").unlink()
    elif changed == "shadow_package":
        shadow = generated / "DependencyReachability"
        shadow.mkdir()
        (shadow / "__init__.py").write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).touch()\n", encoding="utf-8")
    else:
        path = generated / ("GENERATED_SHA256.json" if changed == "manifest" else "DependencyReachability.py")
        path.write_bytes(path.read_bytes() + b"\n")
        if changed == "source_and_manifest":
            manifest = generated / "GENERATED_SHA256.json"
            hashes = json.loads(manifest.read_text(encoding="utf-8"))
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(hashes), encoding="utf-8")
    completed = run_smoke(python, working)
    assert completed.returncode != 0
    assert "operations install check failed" in completed.stderr
    assert not completed.stdout
    assert not marker.exists()


def test_component_registry_without_a_smoke_case_is_rejected(isolated_python):
    python, library, working = isolated_python
    copy_components(library)
    registry = library / "plectis/components/_registry.py"
    text = registry.read_text(encoding="utf-8")
    target = '    "dependency_reachability": "DependencyReachability",\n'
    assert text.count(target) == 1
    registry.write_text(text.replace(target, ""), encoding="utf-8")
    completed = run_smoke(python, working)
    assert completed.returncode != 0
    assert "component smoke cases do not cover the registered kernels" in completed.stderr
    assert not completed.stdout
