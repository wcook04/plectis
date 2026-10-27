"""Snapshot publication preserves the old generation until replacement succeeds."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def builder():
    path = Path(__file__).resolve().parents[1] / "scripts/build/build_code_lens_join_index.py"
    spec = importlib.util.spec_from_file_location("component_index_build_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_snapshot_replacement_is_atomic_and_cleans_temp(builder, monkeypatch, tmp_path):
    target = tmp_path / "index.json"
    target.write_text('{"generation":1}')
    replace = builder.os.replace
    seen = []
    def checked_replace(source, destination):
        assert json.loads(target.read_text()) == {"generation": 1}
        assert json.loads(source.read_text()) == {"generation": 2}
        assert source.parent == target.parent
        seen.append(source)
        replace(source, destination)
    monkeypatch.setattr(builder.os, "replace", checked_replace)
    builder.write_index(target, {"generation": 2})
    assert json.loads(target.read_text()) == {"generation": 2}
    assert len(seen) == 1 and not seen[0].exists()
    assert list(tmp_path.iterdir()) == [target]


def test_failed_publish_preserves_existing_snapshot(builder, monkeypatch, tmp_path):
    target = tmp_path / "index.json"
    target.write_text('{"generation":1}')
    def fail(*args):
        raise OSError("simulated replacement failure")
    monkeypatch.setattr(builder.os, "replace", fail)
    with pytest.raises(OSError):
        builder.write_index(target, {"generation": 2})
    assert json.loads(target.read_text()) == {"generation": 1}
    assert list(tmp_path.iterdir()) == [target]


def test_invalid_serialization_does_not_touch_snapshot(builder, tmp_path):
    target = tmp_path / "index.json"
    target.write_text('{"generation":1}')
    with pytest.raises(ValueError):
        builder.write_index(target, {"bad": float("nan")})
    assert target.read_text() == '{"generation":1}'
    assert list(tmp_path.iterdir()) == [target]


def test_publish_refuses_symlink_output(builder, tmp_path):
    actual = tmp_path / "actual.json"
    actual.write_text('{}')
    target = tmp_path / "index.json"
    target.symlink_to(actual)
    with pytest.raises(ValueError, match="symlink"):
        builder.write_index(target, {"replacement": True})
    assert actual.read_text() == '{}'


def test_registered_runner_input_requires_assurance_and_exclusive_input(builder):
    for argv in (["--registered-runners"], ["--claim-assurance", "--registered-runners", "--lens", "ignored.json"]):
        with pytest.raises(SystemExit) as exc:
            builder.main(argv)
        assert exc.value.code == 2


def test_registered_runner_lens_reuses_current_parser(builder):
    from microcosm_core.project_substrate import _python_span_projection
    root = Path(__file__).resolve().parents[1]
    registry = {"implemented_organs": [{"runner": "microcosm_core.component_index"}]}
    ref = "src/microcosm_core/component_index.py"
    lens = builder.registered_runner_lens(root, registry)
    assert lens["symbol_capsule_rows"] == _python_span_projection(ref, (root / ref).read_text())["symbol_capsule_rows"]
    assert lens["payload_boundary"]["source_bodies_exported"] is False
