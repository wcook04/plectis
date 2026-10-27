"""Adversarial acceptance tests using the four retained operation proof fixtures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPECS = {
    "repair": ("Repair", 21, {"RepairPropagationMutant": (19, 3)}),
    "compatibility": ("Replay", 41, {"CompatibilityOutputMutant": (13, 1),
                                      "ReplayStaleInputMutant": (37, 9),
                                      "ReplayMissedDifferenceMutant": (40, 1)}),
    "views": ("Release", 30, {"IgnoreControl": (29, 1), "RetainPrivateRead": (29, 1)}),
    "replay": ("ReplayAdmission", 16, {"MissingCoverageMutant": (14, 2),
                                      "StaleInputMutant": (13, 3)}),
}


@pytest.fixture(params=SPECS)
def specimen(request, tmp_path):
    slug = request.param
    formal = tmp_path / "formal" / slug
    generated = tmp_path / "src/plectis" / slug / "_generated"
    shutil.copytree(ROOT / "formal" / slug, formal)
    shutil.copytree(ROOT / "src/plectis" / slug / "_generated", generated,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(ROOT / "src/plectis/_sealed_kernel.py", generated.parents[1])
    checker = runpy.run_path(str(ROOT / "scripts/check" / f"check_{slug}_kernel.py"))
    namespace = checker["replay" if slug == "views" else "reprove"].__globals__
    if slug == "views":
        namespace.update(ROOT=formal, PROJECT=tmp_path)
    return slug, tmp_path, generated, checker, namespace


def _binding(specimen):
    slug, root, generated, checker, _ = specimen
    if slug == "views":
        return checker["bindings"](generated)
    if slug == "replay":
        return checker["check_binding"](root)
    return checker["check_binding"](root, generated)


def _reprove(specimen, expected=None):
    slug, root, generated, checker, _ = specimen
    if slug == "views":
        logs = root / "logs"
        logs.mkdir(exist_ok=True)
        return checker["replay"]("dafny", generated, logs, expected_metadata=expected)
    if slug == "replay":
        return checker["reprove"](root, "dafny", expected or _binding(specimen))
    return checker["reprove"](root, generated, "dafny", expected_binding=expected)


def _summary(verified, errors):
    return f"Dafny program verifier finished with {verified} verified, {errors} errors\n"


def _fake_dafny(specimen, monkeypatch, *, attack=None, mutate_after_snapshot=False):
    slug, root, generated, checker, namespace = specimen
    module, verified, negatives = SPECS[slug]
    formal = root / "formal" / slug
    initial = {path.relative_to(formal): path.read_bytes() for path in formal.rglob("*.dfy")}
    calls = []

    def run(argv, *args, **kwargs):
        calls.append(argv)
        cwd = Path(kwargs.get("cwd", args[0] if args else "."))
        if "--version" in argv:
            if mutate_after_snapshot:
                for name in initial:
                    (formal / name).write_bytes(b"// changed after checked snapshot\n")
            return subprocess.CompletedProcess(argv, 0, checker["VERSION"] + "\n")
        path = Path(next(arg for arg in argv if arg.endswith(".dfy")))
        if not path.is_absolute():
            path = cwd / path
        relative = path.relative_to(cwd)
        assert path.read_bytes() == initial[relative]
        assert not path.is_relative_to(formal)
        if "build" in argv:
            for name, source in initial.items():
                assert (cwd / name).read_bytes() == source
            rebuilt = cwd / (module + "-py")
            for name in json.loads((generated / "GENERATED_SHA256.json").read_text()):
                target = rebuilt / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(generated / name, target)
            output = _summary(verified, 0)
            if attack == "substring":
                output = _summary(int("1" + str(verified)), 0)
            elif attack == "duplicate":
                output += output
            elif attack == "clean_error":
                output += "Error: generated source compilation failed\n"
            return subprocess.CompletedProcess(argv, 0, output)
        tasks, errors = negatives[path.stem]
        diagnostics = "".join(
            f"{path.name}(12,{index}): Error: a postcondition could not be proved\n"
            for index in range(errors))
        if attack == "no_failure":
            diagnostics = "Expected diagnostic: a postcondition could not be proved\n"
        elif attack == "resolution":
            diagnostics = ("Error: resolution/type errors detected\n" +
                           diagnostics.split("\n", 1)[1])
        output = diagnostics + _summary(tasks, errors)
        if attack == "timeout":
            output = output.rstrip() + ", 1 time out\n"
        return subprocess.CompletedProcess(argv, 4, output)

    monkeypatch.setattr(shutil, "which", lambda executable: "/unused/dafny")
    name = "command" if slug == "views" else "_run" if slug == "replay" else "run"
    monkeypatch.setitem(namespace, name, run)
    return calls


def test_retained_sources_bind_and_replay_private_source_snapshot(specimen, monkeypatch):
    _binding(specimen)
    calls = _fake_dafny(specimen, monkeypatch, mutate_after_snapshot=True)
    _reprove(specimen)
    assert len(calls) == 2 + len(SPECS[specimen[0]][2])


@pytest.mark.parametrize("attack", ["substring", "duplicate", "clean_error",
                                     "no_failure", "resolution", "timeout"])
def test_replay_rejects_malicious_or_incomplete_diagnostics(specimen, monkeypatch, attack):
    _fake_dafny(specimen, monkeypatch, attack=attack)
    with pytest.raises(ValueError, match="proof diagnostic"):
        _reprove(specimen)


def _repin_source(specimen, name):
    slug, root, _, checker, _ = specimen
    formal = root / "formal" / slug
    path = formal / "metadata.json"
    metadata = json.loads(path.read_text())
    digest = hashlib.sha256((formal / name).read_bytes()).hexdigest()
    if slug == "views":
        metadata["sources"][name] = digest
    elif slug == "replay" and name == "ReplayAdmission.dfy":
        metadata["source_sha256"] = digest
    elif slug == "replay":
        metadata["negative_sha256"][name] = digest
    else:
        metadata[checker["SOURCES"][name]] = digest
    path.write_text(json.dumps(metadata))


@pytest.mark.parametrize("escape", ["@Verify(false) method Disabled() ensures false {}",
                                     "lemma {:axiom} Unproved() ensures false",
                                     "method Bad() { assume false; }"])
def test_binding_rejects_rehashed_source_verification_escapes(specimen, escape):
    slug, root, _, _, _ = specimen
    name = SPECS[slug][0] + ".dfy"
    source = root / "formal" / slug / name
    source.write_text(source.read_text() + "\n" + escape + "\n")
    _repin_source(specimen, name)
    with pytest.raises(ValueError, match="unsafe or unpinned"):
        _binding(specimen)


def test_binding_rejects_rehashed_unlinked_mutant(specimen):
    slug, root, _, _, _ = specimen
    name = "negative/" + next(iter(SPECS[slug][2])) + ".dfy"
    source = root / "formal" / slug / name
    source.write_text(source.read_text() + "\n// unrelated mutant edit\n")
    _repin_source(specimen, name)
    with pytest.raises(ValueError, match="negative|mutant"):
        _binding(specimen)


def test_binding_rejects_symlinked_mutant(specimen):
    slug, root, _, _, _ = specimen
    name = "negative/" + next(iter(SPECS[slug][2])) + ".dfy"
    source = root / "formal" / slug / name
    external = root / "external.dfy"
    external.write_bytes(source.read_bytes())
    source.unlink()
    source.symlink_to(external)
    with pytest.raises(ValueError, match="local regular file"):
        _binding(specimen)


def test_binding_rejects_duplicate_metadata_keys(specimen):
    slug, root, _, _, _ = specimen
    path = root / "formal" / slug / "metadata.json"
    path.write_text(path.read_text().rstrip().removesuffix("}") + ', "verified_tasks": 0}')
    with pytest.raises(ValueError, match="duplicate metadata key"):
        _binding(specimen)


def test_binding_hashes_exact_source_line_endings(specimen):
    slug, root, _, _, _ = specimen
    # Use Compatibility's self-contained dependency so this checks the raw
    # digest, independently of the exact include-directive formatting gate.
    name = "Compatibility.dfy" if slug == "compatibility" else SPECS[slug][0] + ".dfy"
    source = root / "formal" / slug / name
    source.write_bytes(source.read_bytes().replace(b"\n", b"\r\n"))
    with pytest.raises(ValueError, match="(?:source identity|identity mismatch)"):
        _binding(specimen)


def test_replay_rejects_binding_changed_after_receipt_selection(specimen, monkeypatch):
    expected = _binding(specimen)
    slug, root, _, _, _ = specimen
    formal = root / "formal" / slug
    for source in formal.rglob("*.dfy"):
        source.write_bytes(source.read_bytes() + b"\n// new source revision\n")
        _repin_source(specimen, source.relative_to(formal).as_posix())
    calls = _fake_dafny(specimen, monkeypatch)
    with pytest.raises(ValueError, match="changed before proof snapshot"):
        _reprove(specimen, expected)
    assert not calls


def test_binding_rejects_zero_task_metadata(specimen):
    slug, root, _, _, _ = specimen
    path = root / "formal" / slug / "metadata.json"
    metadata = json.loads(path.read_text())
    metadata["verified_tasks"] = 0
    path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError):
        _binding(specimen)


def test_views_requires_all_three_source_hashes(tmp_path):
    checker = runpy.run_path(str(ROOT / "scripts/check/check_views_kernel.py"))
    formal = tmp_path / "views"
    shutil.copytree(ROOT / "formal/views", formal)
    checker["bindings"].__globals__["ROOT"] = formal
    path = formal / "metadata.json"
    metadata = json.loads(path.read_text())
    del metadata["sources"]["negative/IgnoreControl.dfy"]
    path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="source inventory"):
        checker["bindings"](ROOT / "src/plectis/views/_generated")


def test_views_timeout_retains_partial_log(tmp_path, monkeypatch):
    checker = runpy.run_path(str(ROOT / "scripts/check/check_views_kernel.py"))

    def timeout(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"], output=b"partial proof log\n")

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(ValueError, match="timed out before complete"):
        checker["command"](["dafny", "verify"], tmp_path, tmp_path, "timeout.log")
    assert (tmp_path / "timeout.log").read_text() == "partial proof log\n"
