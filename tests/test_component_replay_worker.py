"""Real interpreter isolation and evidence-boundary tests for component workers."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from microcosm_core import component_replay_worker as worker
from microcosm_core import component_replay as replay_host
from microcosm_core.receipts import _RECEIPT_WRITE_OBSERVERS
from microcosm_core.runtime_shell import RUNTIME_STEPS


ORGAN = "pattern_binding_contract"
HELPER = r'''
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import ModuleType

parser = argparse.ArgumentParser()
parser.add_argument('--root', type=Path)
parser.add_argument('--out', type=Path)
parser.add_argument('--result', type=Path)
parser.add_argument('--test-mode', default='normal')
parser.add_argument('organ_id')
args = parser.parse_args()
if args.test_mode == 'timeout':
    child = subprocess.Popen([sys.executable, '-B', '-c', 'import time; time.sleep(60)'])
    (args.root / '.microcosm/descendant.pid').write_text(str(child.pid))
    time.sleep(60)

import microcosm_core.component_replay as replay_host
from microcosm_core.component_replay import _json_digest, replay_component
from microcosm_core.component_replay_worker import RESULT_SCHEMA, _implementation_identity
from microcosm_core.receipts import _RECEIPT_WRITE_OBSERVERS, observe_receipt_writes, write_json_atomic
from microcosm_core.runtime_shell import RUNTIME_STEPS
from microcosm_core.schemas import read_json_strict
# This controlled runner has a tiny immutable source fixture. Keep the real
# hashing/receipt/admission host, while process-state tests avoid rehashing the
# entire shipped corpus. The production fixed-module test does not change this.
replay_host.CODE_ROOT = args.root / '.microcosm/test-runtime-source'

initial = {'env': os.environ.get('PLECTIS_ISOLATION_MARKER'),
           'path': 'plectis-test-import-marker' in sys.path,
           'module': 'plectis_test_import_marker' in sys.modules,
           'observers': len(_RECEIPT_WRITE_OBSERVERS.get())}
os.environ['PLECTIS_ISOLATION_MARKER'] = str(os.getpid())
sys.path.insert(0, 'plectis-test-import-marker')
sys.modules['plectis_test_import_marker'] = ModuleType('plectis_test_import_marker')
if args.test_mode == 'concurrent':
    ready = args.root / '.microcosm/rendezvous'
    ready.mkdir(exist_ok=True)
    (ready / str(os.getpid())).write_text('ready')
    deadline = time.monotonic() + 60
    while len(list(ready.iterdir())) != 2:
        if time.monotonic() > deadline:
            raise RuntimeError('second worker did not overlap')
        time.sleep(.01)
if args.test_mode == 'logs':
    print('x' * 100000)
    print('y' * 100000, file=sys.stderr)
if args.test_mode == 'binary-logs':
    os.write(1, b'\xff' * 100001)
    os.write(2, b'\xff' * 100001)

selected = next(step for step in RUNTIME_STEPS if step.organ_id == args.organ_id)
def run(source, out, command):
    if args.test_mode == 'source-change':
        (args.root / 'core/source-change-test').write_text('changed')
    result = {'organ_id': args.organ_id, 'status': 'pass',
              'isolation': {'initial': initial, 'pid': os.getpid(),
                            'marker': os.environ['PLECTIS_ISOLATION_MARKER'],
                            'tracked_writes': os.environ['MICROCOSM_TRACKED_RECEIPT_WRITES'],
                            'observer_count': len(_RECEIPT_WRITE_OBSERVERS.get())}}
    write_json_atomic(out / selected.receipt_name, result)
    return result
steps = tuple(replace(step, runner=run) if step.organ_id == args.organ_id else step
              for step in RUNTIME_STEPS)
with observe_receipt_writes(lambda event: None):
    summary = replay_component(args.root, args.out, args.organ_id, declared_steps=steps,
                               registry_rows=read_json_strict(args.root / 'core/organ_registry.json')['implemented_organs'],
                               route_provider=lambda: RUNTIME_STEPS)
assert not _RECEIPT_WRITE_OBSERVERS.get()
if args.test_mode == 'receipt-change':
    receipt = Path(summary['results'][0]['receipt_ref'])
    saved = json.loads(receipt.read_text())
    saved['isolation']['marker'] = 'tampered'
    receipt.write_text(json.dumps(saved))
if args.test_mode == 'wrong-scope':
    summary['selected_organ_ids'] = ['another-component']
    Path(summary['summary_ref']).write_text(json.dumps(summary))
if args.test_mode == 'wrong-filename':
    receipt = Path(summary['results'][0]['receipt_ref'])
    renamed = receipt.with_name('different-receipt.json')
    renamed.write_bytes(receipt.read_bytes())
    summary['results'][0]['receipt_ref'] = str(renamed)
    Path(summary['summary_ref']).write_text(json.dumps(summary))
if args.test_mode == 'false-admission':
    summary['admission']['accepted'] = False
    Path(summary['summary_ref']).write_text(json.dumps(summary))
if args.test_mode == 'source-view-change':
    summary['source'] = dict(summary['source'])
    summary['source']['runtime_source_tree_sha256'] = '0' * 64
    Path(summary['summary_ref']).write_text(json.dumps(summary))
if args.test_mode in {'wrong-inventory-scope', 'legacy-inventory', 'wrong-inventory-digest', 'wrong-package-digest-scheme'}:
    source = summary['source_identity_material']
    if args.test_mode == 'wrong-inventory-scope':
        source['runtime_package_tree_sha256']['unrelated_dependency'] = '1' * 64
        source['runtime_source_scope'].append('unrelated_dependency/**')
        source['runtime_source_tree_sha256'] = _json_digest(source['runtime_package_tree_sha256'])
    elif args.test_mode == 'legacy-inventory':
        source['source_inventory_scheme'] = 'unbounded_parent_v0'
    elif args.test_mode == 'wrong-package-digest-scheme':
        source['runtime_package_digest_scheme'] = 'mtime_only'
    else:
        source['runtime_source_tree_sha256'] = '0' * 64
    summary['source'] = json.loads(json.dumps(source))
    summary['source_after'] = json.loads(json.dumps(source))
    summary['source_identity'] = _json_digest(source)
    summary['source_inventory_scheme'] = source['source_inventory_scheme']
    summary['runtime_source_scope'] = source['runtime_source_scope']
    observation = summary['admission']['observations'][0]
    observation['source_before'] = observation['source_after'] = summary['source_identity']
    Path(summary['summary_ref']).write_text(json.dumps(summary))
implementation = _implementation_identity()
if args.test_mode == 'wrong-entry-bytes':
    implementation['entry_host_sha256']['component_replay_worker.py'] = '0' * 64
report = {'schema_version': RESULT_SCHEMA, 'replay': summary, 'implementation': implementation}
args.result.write_text(json.dumps(report))
if args.test_mode == 'duplicate-result':
    args.result.write_text('{"schema_version":' + json.dumps(RESULT_SCHEMA)
                           + ',"implementation":' + json.dumps(implementation) + ',"replay":'
                           + json.dumps(summary) + ',"replay":' + json.dumps(summary) + '}')
if args.test_mode == 'nonfinite-result':
    report['unexpected_nonfinite'] = float('nan')
    args.result.write_text(json.dumps(report))
raise SystemExit(0 if summary['status'] == 'pass' else 1)
'''


@pytest.fixture
def project(tmp_path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core/organ_registry.json").write_text(json.dumps({
        "implemented_organs": [{"organ_id": step.organ_id} for step in RUNTIME_STEPS]}))
    selected = next(step for step in RUNTIME_STEPS if step.organ_id == ORGAN)
    source = tmp_path / selected.example_rel
    source.mkdir(parents=True)
    (source / "test.json").write_text("{}")
    runtime_source = tmp_path / ".microcosm/test-runtime-source"
    runtime_source.mkdir(parents=True)
    for name in ("microcosm_core", "plectis"):
        package = runtime_source / name
        package.mkdir()
        (package / "worker.txt").write_text("immutable controlled worker source fixture")
    return tmp_path


@pytest.fixture
def trusted_worker(tmp_path, monkeypatch):
    helper = tmp_path / "trusted_worker.py"
    helper.write_text(HELPER)
    monkeypatch.setattr(replay_host, "CODE_ROOT", tmp_path / ".microcosm/test-runtime-source")

    def select(mode):
        monkeypatch.setattr(worker, "_worker_argv", lambda root, out, organ_id, result: [
            sys.executable, "-I", "-B", "-c",
            "import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); "
            "sys.argv[0]=sys.argv.pop(1); runpy.run_path(sys.argv[0],run_name='__main__')",
            str(Path(worker.__file__).resolve().parents[1]), str(helper),
            "--root", str(root), "--out", str(out),
            "--result", str(result), "--test-mode", mode, organ_id])
    return select


def test_unknown_id_rejects_before_spawn_or_output(project, monkeypatch):
    monkeypatch.setattr(worker, "_run_worker", lambda *args: pytest.fail("spawned an unknown ID"))
    out = project / ".microcosm/replay"
    result = worker.replay_component_isolated(project, out, "unknown")
    assert result["status"] == "blocked"
    assert result["execution_state"] == "unknown_component"
    assert result["replay"] is None and result["worker"]["spawned"] is False
    assert not out.exists()


def test_output_escape_rejects_before_spawn(project, monkeypatch):
    monkeypatch.setattr(worker, "_run_worker", lambda *args: pytest.fail("spawned outside confined output"))
    result = worker.replay_component_isolated(project, project / "receipts/new", ORGAN)
    assert result["status"] == "blocked" and result["worker"]["spawned"] is False
    assert not (project / "receipts").exists()


@pytest.mark.parametrize("limits", [{"timeout_seconds": True}, {"timeout_seconds": float("inf")},
                                   {"max_log_bytes": -1}, {"max_log_bytes": 1024 * 1024 + 1}])
def test_invalid_limits_reject_before_spawn(project, monkeypatch, limits):
    monkeypatch.setattr(worker, "_run_worker", lambda *args: pytest.fail("spawned with invalid limits"))
    out = project / ".microcosm/replay"
    result = worker.replay_component_isolated(project, out, ORGAN, **limits)
    assert result["status"] == "blocked" and result["execution_state"] == "invalid_limits"
    assert result["worker"]["spawned"] is False and not out.exists()


def test_actual_worker_module_ignores_workspace_and_parent_pythonpath(project, monkeypatch):
    # Exercise the actual fixed bootstrap and reviewed worker module. Argparse
    # help returns before a costly full-source replay observation; this tests
    # import selection, and makes no component execution/admission claim.
    markers = []
    for package in (project / "microcosm_core", project / "environment-shadow/microcosm_core"):
        package.mkdir(parents=True)
        marker = package.parent / "shadow-executed"
        markers.append(marker)
        (package / "__init__.py").write_text(
            "from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('executed')\n")
    monkeypatch.setenv("PYTHONPATH", str(project / "environment-shadow"))
    out = project / ".microcosm/replay"
    out.mkdir()
    argv = worker._worker_argv(project, out, ORGAN, out / "unused.json") + ["--help"]
    result = worker._run_worker(argv, project, 120, 16384)
    assert result["spawned"] is True and result["return_code"] == 0, result
    assert "Run one reviewed component in a fresh interpreter" in result["stdout"]
    assert "--result" in result["stdout"]
    assert not any(marker.exists() for marker in markers)


def test_two_real_workers_isolate_process_and_receipt_context(project, trusted_worker):
    trusted_worker("concurrent")
    baseline = (os.environ.get("PLECTIS_ISOLATION_MARKER"),
                "plectis-test-import-marker" in sys.path,
                "plectis_test_import_marker" in sys.modules,
                _RECEIPT_WRITE_OBSERVERS.get(), sys.dont_write_bytecode,
                os.environ.get("MICROCOSM_TRACKED_RECEIPT_WRITES"))
    out = project / ".microcosm/replay"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: worker.replay_component_isolated(
            project, out, ORGAN, timeout_seconds=120), range(2)))
    assert [result["status"] for result in results] == ["pass", "pass"], results
    evidence = [json.loads(Path(result["replay"]["results"][0]["receipt_ref"]).read_text())["isolation"]
                for result in results]
    assert len({item["pid"] for item in evidence}) == 2
    assert len({result["replay"]["summary_ref"] for result in results}) == 2
    for item in evidence:
        assert item["initial"] == {"env": None, "path": False, "module": False, "observers": 0}
        assert item["marker"] == str(item["pid"])
        assert item["tracked_writes"] == "0"
        assert item["observer_count"] == 2  # helper context plus admission observer
    assert baseline == (os.environ.get("PLECTIS_ISOLATION_MARKER"),
                        "plectis-test-import-marker" in sys.path,
                        "plectis_test_import_marker" in sys.modules,
                        _RECEIPT_WRITE_OBSERVERS.get(), sys.dont_write_bytecode,
                        os.environ.get("MICROCOSM_TRACKED_RECEIPT_WRITES"))


@pytest.mark.parametrize("mode", ["receipt-change", "wrong-scope", "wrong-filename", "false-admission",
                                 "duplicate-result", "nonfinite-result", "wrong-entry-bytes",
                                 "wrong-inventory-scope", "legacy-inventory", "wrong-inventory-digest",
                                 "wrong-package-digest-scheme", "source-view-change"])
def test_tampered_worker_evidence_cannot_return_pass(project, trusted_worker, mode):
    trusted_worker(mode)
    result = worker.replay_component_isolated(project, project / ".microcosm/replay", ORGAN)
    assert result["status"] == "blocked"
    assert result["execution_state"] == "worker_result_rejected"
    assert result["replay"] is None


def test_worker_source_change_remains_denied(project, trusted_worker):
    trusted_worker("source-change")
    result = worker.replay_component_isolated(project, project / ".microcosm/replay", ORGAN)
    assert result["status"] == "blocked"
    assert result["execution_state"] == "source_changed"
    assert result["replay"]["admission"]["accepted"] is False


@pytest.mark.parametrize("mode", ["logs", "binary-logs"])
def test_large_real_worker_logs_are_bounded(project, trusted_worker, mode):
    trusted_worker(mode)
    result = worker.replay_component_isolated(project, project / ".microcosm/replay", ORGAN,
                                               max_log_bytes=128)
    assert result["status"] == "pass", result
    for stream in ("stdout", "stderr"):
        assert len(result["worker"][stream].encode()) <= 128
        assert result["worker"][f"{stream}_bytes"] > 100000
        assert result["worker"][f"{stream}_truncated"] is True


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group cleanup contract")
def test_timeout_kills_real_worker_descendant(project, trusted_worker):
    trusted_worker("timeout")
    result = worker.replay_component_isolated(project, project / ".microcosm/replay", ORGAN,
                                               timeout_seconds=1)
    assert result["status"] == "blocked" and result["execution_state"] == "timeout"
    assert result["replay"] is None and result["worker"]["timed_out"] is True
    child = int((project / ".microcosm/descendant.pid").read_text())
    deadline = time.monotonic() + 2
    while True:
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(child)], capture_output=True,
                               text=True, check=False).stdout.strip()
        if not state or state.startswith("Z"):
            break
        assert time.monotonic() < deadline, f"worker descendant {child} remains live: {state}"
        time.sleep(.01)
