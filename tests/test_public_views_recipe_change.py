"""Exercise the shared-recipe example and its public acquisition boundary."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

import plectis.views._api as api

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/operations/public_views_recipe_change.py"


def test_recipe_change_preserves_reference_and_required_public_output(monkeypatch):
    messages = []
    call = api._call

    def observed_call(message):
        messages.append(message)
        return call(message)

    monkeypatch.setattr(api, "_call", observed_call)
    result = runpy.run_path(str(EXAMPLE))["demonstrate"]()
    assert result["status"] == "tested_changed_recipe"
    for revision, expected in (("before", ["run-001: 7/10", "passed"]),
                               ("after", ["run-001: 7/10", "approved"])):
        observed = result["revisions"][revision]
        assert observed["public_trace"] == observed["ordinary_trace"] == expected
        mixed = observed["mixed_reference_traces"]
        assert mixed[0] != mixed[1]
        assert [[event["text"] for event in trace if event["public"]]
                for trace in mixed] == [expected, expected]
    assert result["private_control_change_refused"] is True
    assert result["ordinary_renderer_matches_both_revisions"] is True
    runs = [message for message in messages if message["action"] == "run"]
    assert len(runs) == 2
    assert all(set(row) == {"run_id", "score", "passed"}
               for message in runs for row in message["rows"])
    assert "SYNTHETIC_PRIVATE" not in json.dumps(messages)


def test_recipe_change_example_runs_from_another_directory(tmp_path):
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"),
                       PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([sys.executable, "-B", str(EXAMPLE), "--format", "text"],
                            cwd=tmp_path, env=environment, capture_output=True,
                            text=True, timeout=30, check=True)
    assert "passed -> approved" in result.stdout
    assert "ordinary public renderer matches both versions" in result.stdout
    assert "no maintenance advantage is measured" in result.stdout
