"""Contract tests for the shared component kernel bridge and binding gate."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECK = runpy.run_path(str(ROOT / "scripts/check/check_component_kernels.py"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def sample_root(tmp_path: Path) -> Path:
    """Use the existing reviewed replay kernel as an isolated bridge specimen."""
    root = tmp_path / "root"
    formal = root / "formal/components/sample"
    generated = root / "src/plectis/components/sample/_generated"
    formal.mkdir(parents=True)
    package = generated.parent
    package.mkdir(parents=True)
    shutil.copytree(ROOT / "src/plectis/replay/_generated", generated,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("_registry.py", "_worker.py", "_bridge.py", "__init__.py"):
        shutil.copy2(ROOT / "src/plectis/components" / name, package.parent / name)
    (package.parent / "_registry.py").write_text('KERNELS = {"sample": "ReplayAdmission"}\n')
    shutil.copy2(ROOT / "src/plectis/_sealed_kernel.py", package.parent.parent / "_sealed_kernel.py")
    (package / "__init__.py").write_text("")
    (package / "_adapter.py").write_text(
        "def evaluate(payload, kernel, dafny):\n"
        "    if type(payload) is not int: raise ValueError('expected integer')\n"
        "    return kernel.default__.Check(dafny.Seq([]), payload, dafny.Seq([]))\n"
    )
    source_root = ROOT / "formal/replay"
    shutil.copy2(source_root / "ReplayAdmission.dfy", formal / "ReplayAdmission.dfy")
    shutil.copytree(source_root / "negative", formal / "negative")
    (formal / "README.md").write_text("Test specimen only.\n")
    original = json.loads((source_root / "metadata.json").read_text())
    before_coverage = (
        "    |pending| == 0 ||\n"
        "    (CountSpec(specs, pending[0].component) == 1 &&\n"
        "     CountRow(rows, pending[0].component) == 1 &&\n"
        "     FindGood(rows, pending[0], source) &&\n"
        "     CheckSpecs(pending[1..], specs, rows, source))"
    )
    after_coverage = (
        "    |pending| == 0 ||\n"
        "    CheckSpecs(pending[1..], specs, rows, source)"
        " // MUTANT: components disappear from the coverage check"
    )
    metadata = {**original, "slug": "sample", "module": "ReplayAdmission", "mutations": {
        "negative/MissingCoverageMutant.dfy": {
            "before": before_coverage, "after": after_coverage,
            "occurrence": 0, "expected_occurrences": 1,
        },
        "negative/StaleInputMutant.dfy": {
            "before": "o.inputBefore > 0 && o.inputBefore == o.inputAfter &&",
            "after": "o.inputBefore > 0 && true /* MUTANT: stale input */ &&",
            "occurrence": 1, "expected_occurrences": 2,
        },
    }}
    (formal / "metadata.json").write_text(json.dumps(metadata))
    return root


def test_binding_checks_source_linked_mutants_and_generated_inventory(sample_root: Path) -> None:
    assert CHECK["discover"](sample_root) == {"sample": "ReplayAdmission"}
    CHECK["check_binding"](sample_root, "sample", "ReplayAdmission")
    mutant = sample_root / "formal/components/sample/negative/StaleInputMutant.dfy"
    mutant.write_text(mutant.read_text() + "\n// unlinked edit\n")
    metadata_path = sample_root / "formal/components/sample/metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["negative_sha256"]["negative/StaleInputMutant.dfy"] = _sha(mutant)
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="source-linked negative"):
        CHECK["check_binding"](sample_root, "sample", "ReplayAdmission")


def test_binding_rejects_generated_shadow_package(sample_root: Path) -> None:
    shadow = sample_root / "src/plectis/components/sample/_generated/ReplayAdmission"
    shadow.mkdir()
    (shadow / "__init__.py").write_text("raise AssertionError('shadow')\n")
    with pytest.raises(ValueError, match="unexpected generated directory"):
        CHECK["check_binding"](sample_root, "sample", "ReplayAdmission")


def test_worker_isolated_strict_and_fail_closed(sample_root: Path, tmp_path: Path) -> None:
    worker = sample_root / "src/plectis/components/_worker.py"
    poison = tmp_path / "poison"
    poison.mkdir()
    (poison / "ReplayAdmission.py").write_text("raise AssertionError('ambient import')\n")
    env = {**os.environ, "PYTHONPATH": str(poison)}
    def call(value: str):
        return subprocess.run([sys.executable, "-I", "-B", str(worker)], input=value,
                              text=True, capture_output=True, env=env, check=False)
    accepted = call('{"slug":"sample","payload":1}')
    assert accepted.returncode == 0
    assert type(json.loads(accepted.stdout)["result"]) is bool
    for request in ('{"slug":"../../sample","payload":1}',
                    '{"slug":"sample","slug":"sample","payload":1}',
                    '{"slug":"sample","payload":NaN}',
                    '{"slug":"sample","payload":1e10000}'):
        rejected = call(request)
        assert rejected.returncode == 2
        assert set(json.loads(rejected.stdout)) == {"error"}


def test_bridge_invokes_worker_without_fallback(sample_root: Path, monkeypatch) -> None:
    from plectis.components import _bridge

    monkeypatch.setattr(_bridge, "KERNELS", {"sample": "ReplayAdmission"})
    monkeypatch.setattr(_bridge, "__file__", str(
        sample_root / "src/plectis/components/_bridge.py"
    ))
    assert type(_bridge.invoke("sample", 1)) is bool
    with pytest.raises(ValueError, match="unregistered"):
        _bridge.invoke("../../sample", 1)
    with pytest.raises(ValueError, match="JSON-safe"):
        _bridge.invoke("sample", float("nan"))
    with pytest.raises(RuntimeError, match="worker"):
        _bridge.invoke("sample", {"wrong": "type"})
    generated = sample_root / "src/plectis/components/sample/_generated/ReplayAdmission.py"
    generated.write_text(generated.read_text() + "\n# tampered\n")
    with pytest.raises(RuntimeError, match="worker"):
        _bridge.invoke("sample", 1)


def test_component_discovery_rejects_unregistered_directory(sample_root: Path) -> None:
    (sample_root / "formal/components/unregistered").mkdir()
    with pytest.raises(ValueError, match="inventory mismatch"):
        CHECK["discover"](sample_root)


def test_worker_rejects_symlinked_adapter(sample_root: Path, tmp_path: Path) -> None:
    worker = sample_root / "src/plectis/components/_worker.py"
    adapter = sample_root / "src/plectis/components/sample/_adapter.py"
    outsider = tmp_path / "outside.py"
    outsider.write_text("raise AssertionError('not a trusted local adapter')\n")
    adapter.unlink()
    adapter.symlink_to(outsider)
    process = subprocess.run(
        [sys.executable, "-I", "-B", str(worker)],
        input='{"slug":"sample","payload":1}',
        text=True, capture_output=True, check=False,
    )
    assert process.returncode == 2
    assert json.loads(process.stdout) == {"error": "ValueError"}


def test_bridge_accepts_large_json_payload(sample_root: Path, monkeypatch) -> None:
    from plectis.components import _bridge

    monkeypatch.setattr(_bridge, "KERNELS", {"sample": "ReplayAdmission"})
    monkeypatch.setattr(_bridge, "__file__", str(
        sample_root / "src/plectis/components/_bridge.py"
    ))
    adapter = sample_root / "src/plectis/components/sample/_adapter.py"
    adapter.write_text("def evaluate(payload, kernel, dafny):\n    return len(payload)\n")
    payload = "x" * 2_100_000
    assert _bridge.invoke("sample", payload) == len(payload)


def test_bridge_fails_closed_on_worker_timeout(monkeypatch) -> None:
    from plectis.components import _bridge

    monkeypatch.setattr(_bridge, "KERNELS", {"sample": "ReplayAdmission"})
    def timeout(*args, **kwargs):
        assert kwargs["timeout"] == 30
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])
    monkeypatch.setattr(_bridge.subprocess, "run", timeout)
    with pytest.raises(RuntimeError, match="worker failed"):
        _bridge.invoke("sample", 1)


def test_checker_recognizes_forall_postcondition_failure_only() -> None:
    diagnostic = CHECK["PROOF_FAILURE"]
    assert diagnostic.search("Error: possible violation of postcondition of forall statement")
    assert diagnostic.search("Error: a postcondition could not be proved on this return path")
    assert not diagnostic.search("Error: resolution/type errors detected")


def test_kernel_identity_validates_before_cache_use(sample_root: Path, monkeypatch) -> None:
    from plectis.components import _bridge

    monkeypatch.setattr(_bridge, "KERNELS", {"sample": "ReplayAdmission"})
    monkeypatch.setattr(_bridge, "__file__", str(
        sample_root / "src/plectis/components/_bridge.py"
    ))
    original = _bridge.kernel_identity("sample")
    assert original == json.loads(json.dumps(original))
    assert original["generated_python"] == CHECK["check_binding"](
        sample_root, "sample", "ReplayAdmission"
    )["generated_python"]
    adapter = sample_root / "src/plectis/components/sample/_adapter.py"
    adapter.write_text(adapter.read_text() + "\n# changed trusted adapter\n")
    updated = _bridge.kernel_identity("sample")
    assert updated != original
    assert updated["generated_python"] == original["generated_python"]
    assert updated["trusted_host"]["components/sample/_adapter.py"] != original[
        "trusted_host"]["components/sample/_adapter.py"]
    generated = sample_root / "src/plectis/components/sample/_generated/ReplayAdmission.py"
    generated.write_text(generated.read_text() + "\n# unreviewed kernel\n")
    with pytest.raises(ValueError, match="reviewed bytes"):
        _bridge.kernel_identity("sample")


@pytest.mark.parametrize("relative", [
    "components/__init__.py", "components/_bridge.py", "components/_worker.py",
    "components/_registry.py", "_sealed_kernel.py", "components/sample/__init__.py",
])
def test_kernel_identity_covers_shared_host_sources(sample_root: Path, monkeypatch,
                                                   relative: str) -> None:
    from plectis.components import _bridge

    monkeypatch.setattr(_bridge, "KERNELS", {"sample": "ReplayAdmission"})
    monkeypatch.setattr(_bridge, "__file__", str(
        sample_root / "src/plectis/components/_bridge.py"
    ))
    original = _bridge.kernel_identity("sample")
    host = sample_root / "src/plectis" / relative
    host.write_text(host.read_text() + "\n# source changed\n")
    updated = _bridge.kernel_identity("sample")
    assert updated["trusted_host"][relative] != original["trusted_host"][relative]


@pytest.mark.parametrize("mutation", ["extra", "missing", "symlink"])
def test_kernel_identity_rejects_invalid_generated_inventory(sample_root: Path,
                                                            monkeypatch,
                                                            mutation: str) -> None:
    from plectis.components import _bridge

    monkeypatch.setattr(_bridge, "KERNELS", {"sample": "ReplayAdmission"})
    monkeypatch.setattr(_bridge, "__file__", str(
        sample_root / "src/plectis/components/_bridge.py"
    ))
    _bridge.kernel_identity("sample")
    generated = sample_root / "src/plectis/components/sample/_generated"
    if mutation == "extra":
        (generated / "unreviewed.py").write_text("raise AssertionError('never import')\n")
    elif mutation == "missing":
        (generated / "module_.py").unlink()
    else:
        source = generated / "ReplayAdmission.py"
        external = sample_root / "identical.py"
        external.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(external)
    with pytest.raises(ValueError):
        _bridge.kernel_identity("sample")


@pytest.mark.parametrize("directive", [
    "assume false;", "include \"unbound.dfy\"",
    "lemma {:axiom} Trust() ensures false", "method {:extern} Trust()",
    "method {:verify false} Trust() {}", "module {:options \"--no-verify\"} X {}",
    "method Trust() decreases * {}",
    "@Verify(false) method Bad() returns (r: bool) ensures r { r := false; }",
    "@Axiom lemma Unproved() ensures false",
    "@VerifyOnly method Good() {}",
    '@Options("--no-verify") module Unsafe {}',
    "method {:ignore} Bad() ensures false {}",
    "lemma {:compile false} Unproved() ensures false",
])
def test_binding_rejects_explicit_verification_escapes(sample_root: Path,
                                                      directive: str) -> None:
    source = sample_root / "formal/components/sample/ReplayAdmission.dfy"
    source.write_text(source.read_text() + "\n" + directive + "\n")
    metadata_path = source.parent / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["source_sha256"] = _sha(source)
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="unsafe or unpinned"):
        CHECK["check_binding"](sample_root, "sample", "ReplayAdmission")


def test_source_policy_distinguishes_comments_literals_and_prime_names(tmp_path: Path) -> None:
    source = tmp_path / "Policy.dfy"
    source.write_text('''// assume false; and {:verify false}
module Example {
  method M() { var x' := "assume"; var c := 'a'; }
}
''')
    CHECK["_source_text"](source)
    source.write_text('method M() { var s := @"a"" assume false; \\"; }\n')
    CHECK["_source_text"](source)
    source.write_text('/* outer /* nested */ " */ method M() { assume false; var s := "tail"; }\n')
    with pytest.raises(ValueError, match="unsafe or unpinned"):
        CHECK["_source_text"](source)
    source.write_text("method M() { var x' := 0; assume false; var y' := 0; }\n")
    with pytest.raises(ValueError, match="unsafe or unpinned"):
        CHECK["_source_text"](source)


def test_binding_rejects_symlinked_source_linked_mutant(sample_root: Path) -> None:
    mutant = sample_root / "formal/components/sample/negative/StaleInputMutant.dfy"
    external = sample_root / "same-mutant.dfy"
    external.write_bytes(mutant.read_bytes())
    mutant.unlink()
    mutant.symlink_to(external)
    with pytest.raises(ValueError, match="local regular file"):
        CHECK["check_binding"](sample_root, "sample", "ReplayAdmission")


@pytest.mark.parametrize("output", [
    "Error: a postcondition could not be proved\n"
    "Dafny program verifier finished with 1 verified, 1 error, 1 time out\n",
    "Error: a postcondition could not be proved\n"
    "Error: Verification of M timed out\n"
    "Dafny program verifier finished with 1 verified, 2 errors\n",
    "Error: a postcondition could not be proved\n"
    "Error: resolution/type errors detected\n"
    "Dafny program verifier finished with 1 verified, 2 errors\n",
    "Error: a postcondition could not be proved\n"
    "Dafny program verifier finished with 1 verified, 1 error\n"
    "Dafny program verifier finished with 1 verified, 1 error\n",
])
def test_negative_proof_rejects_incomplete_or_mixed_diagnostics(output: str) -> None:
    errors = 2 if "2 errors" in output else 1
    result = subprocess.CompletedProcess([], 4, output)
    with pytest.raises(ValueError, match="proof diagnostic"):
        CHECK["_proof_result"](result, 1, errors, negative=True)


def test_negative_proof_accepts_genuine_forall_failure() -> None:
    result = subprocess.CompletedProcess([], 4,
        "Spec.dfy(12,4): Error: possible violation of postcondition of forall statement\n"
        "Dafny program verifier finished with 3 verified, 1 error\n")
    CHECK["_proof_result"](result, 3, 1, negative=True)


def test_prover_process_timeout_retains_partial_diagnostic(monkeypatch, capsys,
                                                          tmp_path: Path) -> None:
    def timeout(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"],
                                        output=b"partial verifier diagnostic\n")
    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(ValueError, match="timed out before complete"):
        CHECK["_run"](["dafny", "verify", "Spec.dfy"], cwd=tmp_path, env={})
    assert "partial verifier diagnostic" in capsys.readouterr().out


def test_bridge_rejects_json_numeric_overflow_from_worker(monkeypatch) -> None:
    from plectis.components import _bridge

    monkeypatch.setattr(_bridge, "KERNELS", {"sample": "ReplayAdmission"})
    monkeypatch.setattr(_bridge.subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess(args[0], 0, '{"result":1e10000}', ""))
    with pytest.raises(RuntimeError, match="worker failed"):
        _bridge.invoke("sample", 1)


def test_metadata_rejects_json_numeric_overflow(tmp_path: Path) -> None:
    path = tmp_path / "metadata.json"
    path.write_text('{"schema_version":1,"extra":1e10000}')
    with pytest.raises(ValueError, match="non-finite metadata number"):
        CHECK["_read_json"](path)


@pytest.mark.parametrize("output,verified", [
    ("Dafny program verifier finished with 0 verified, 0 errors\n", 0),
    ("Error: generated source compilation failed\n"
     "Dafny program verifier finished with 1 verified, 0 errors\n", 1),
])
def test_clean_proof_rejects_vacuous_or_contradictory_log(output: str, verified: int) -> None:
    with pytest.raises(ValueError, match="proof diagnostic"):
        CHECK["_proof_result"](subprocess.CompletedProcess([], 0, output), verified, 0)


def test_source_policy_requires_exact_reviewed_include_inventory(tmp_path: Path) -> None:
    source = tmp_path / "Replay.dfy"
    source.write_text('include "Compatibility.dfy"\nmodule Replay {}\n')
    assert CHECK["_source_text"](source, includes=("Compatibility.dfy",)) == source.read_text()
    for changed in ('include "Other.dfy"\nmodule Replay {}\n',
                    'include "Compatibility.dfy"\ninclude "Compatibility.dfy"\n',
                    'include "Compatibility.dfy"\ninclude "Other.dfy"\n',
                    'module Replay {}\n'):
        source.write_text(changed)
        with pytest.raises(ValueError, match="include inventory"):
            CHECK["_source_text"](source, includes=("Compatibility.dfy",))
    source.write_text('include "Compatibility.dfy"\nmethod M() { assume false; }\n')
    with pytest.raises(ValueError, match="unsafe or unpinned"):
        CHECK["_source_text"](source, includes=("Compatibility.dfy",))


def test_negative_proof_accepts_index_safety_obligation_failure() -> None:
    result = subprocess.CompletedProcess([], 4,
        "Spec.dfy(12,4): Error: index out of range\n"
        "Dafny program verifier finished with 3 verified, 1 error\n")
    CHECK["_proof_result"](result, 3, 1, negative=True)


def test_negative_proof_requires_each_counted_diagnostic() -> None:
    result = subprocess.CompletedProcess([], 4,
        "Spec.dfy(12,4): Error: assertion might not hold\n"
        "Dafny program verifier finished with 3 verified, 2 errors\n")
    with pytest.raises(ValueError, match="proof diagnostic"):
        CHECK["_proof_result"](result, 3, 2, negative=True)


def test_source_policy_preserves_raw_newlines_for_snapshot_hash(tmp_path: Path) -> None:
    source = tmp_path / "Exact.dfy"
    original = b"module Exact {\r\n  method M() {}\r\n}\r\n"
    source.write_bytes(original)
    captured = CHECK["_source_text"](source)
    assert captured.encode("utf-8") == original
    assert hashlib.sha256(captured.encode("utf-8")).hexdigest() == _sha(source)
