"""Exercise the installed-backend smoke program against its real source owners.

The full wheel/venv smoke owns installation proof; these fast tests exercise the
program's success and deliberate request-I/O failure branches.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def _smoke():
    spec = importlib.util.spec_from_file_location('backend_install_smoke', ROOT / 'scripts/release/package_install_smoke.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_program(tmp_path, *, inject_io=False, installed_guard=True):
    smoke = _smoke()
    # This unit seam permits source modules. Only run_package_smoke's -I process
    # in the freshly installed venv establishes actual installation purity.
    prefix = 'import sys; sys.path.insert(0, ' + repr(str(ROOT / 'src')) + ')\n'
    if not installed_guard:
        prefix += 'import sysconfig; sysconfig.get_path = lambda name: ' + repr(str(ROOT / 'src')) + '\n'
    if inject_io:
        prefix += ('from microcosm_core import component_http\n'
                   'original_dispatch = component_http._dispatch\n'
                   'def reads_source(*args):\n'
                   '    open("forbidden-request-read")\n'
                   '    return original_dispatch(*args)\n'
                   'component_http._dispatch = reads_source\n')
    return subprocess.run([sys.executable, '-I', '-c', prefix + smoke.BACKEND_INSTALL_CHECK,
                           json.dumps(smoke._backend_expectations(ROOT))],
                          cwd=tmp_path, text=True, capture_output=True)


def test_backend_install_check_real_snapshot_and_blocked_request_io(tmp_path):
    result = _run_program(tmp_path, installed_guard=False)
    assert result.returncode == 0, result.stderr
    row = json.loads(result.stdout)
    assert row['status'] == 'pass'
    assert row['request_filesystem_io'] == 'blocked'
    assert row['proof_count'] == 12
    assert row['core_count'] == 4
    failure = _run_program(tmp_path, inject_io=True, installed_guard=False)
    assert failure.returncode != 0


def test_backend_install_guard_rejects_shadowing_source_checkout(tmp_path):
    result = _run_program(tmp_path)
    assert result.returncode != 0
    assert 'backend imported outside installation' in result.stderr
