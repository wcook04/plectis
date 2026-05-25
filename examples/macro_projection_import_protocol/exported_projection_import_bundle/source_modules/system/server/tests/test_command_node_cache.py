"""Regression coverage for persistent command-node cache semantics."""
from __future__ import annotations

import fcntl
import multiprocessing
import time
from pathlib import Path

from system.lib.command_node_cache import cached_command_node, peek_cached_command_node


def _singleflight_worker(args: tuple[str, str, str, str, float]) -> str:
    repo_root, node_id, key, counter_path_str, sleep_s = args
    counter_path = Path(counter_path_str)

    def builder() -> dict[str, object]:
        with counter_path.open("r+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                current = int(fh.read().strip() or "0")
                fh.seek(0)
                fh.truncate()
                fh.write(str(current + 1))
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        time.sleep(sleep_s)
        return {"singleflight_value": current + 1}

    _, status = cached_command_node(
        Path(repo_root),
        node_id=node_id,
        key=key,
        ttl_s=300,
        builder=builder,
    )
    return str(status["status"])


def test_command_node_cache_reuses_value_until_input_manifest_changes(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("one", encoding="utf-8")
    calls = {"count": 0}

    def builder():
        calls["count"] += 1
        return {"value": calls["count"]}

    first, first_status = cached_command_node(
        tmp_path,
        node_id="demo.node",
        key={"q": "same"},
        input_paths=[source],
        ttl_s=60,
        builder=builder,
    )
    second, second_status = cached_command_node(
        tmp_path,
        node_id="demo.node",
        key={"q": "same"},
        input_paths=[source],
        ttl_s=60,
        builder=builder,
    )

    assert first == {"value": 1}
    assert second == {"value": 1}
    assert first_status["status"] == "miss_built"
    assert second_status["status"] == "hit"
    assert calls["count"] == 1

    source.write_text("two", encoding="utf-8")
    third, third_status = cached_command_node(
        tmp_path,
        node_id="demo.node",
        key={"q": "same"},
        input_paths=[source],
        ttl_s=60,
        builder=builder,
    )

    assert third == {"value": 2}
    assert third_status["status"] == "miss_built"
    assert third_status["reason"] == "input_manifest_changed"
    assert calls["count"] == 2


def test_command_node_cache_invalidates_on_directory_child_content_change(tmp_path):
    source_dir = tmp_path / "inputs"
    source_dir.mkdir()
    child = source_dir / "row.json"
    child.write_text('{"value": 1}', encoding="utf-8")
    calls = {"count": 0}

    def builder():
        calls["count"] += 1
        return {"value": calls["count"]}

    first, _ = cached_command_node(
        tmp_path,
        node_id="demo.directory",
        key="same",
        input_paths=[source_dir],
        ttl_s=60,
        builder=builder,
    )
    child.write_text('{"value": 100, "extra": true}', encoding="utf-8")
    second, second_status = cached_command_node(
        tmp_path,
        node_id="demo.directory",
        key="same",
        input_paths=[source_dir],
        ttl_s=60,
        builder=builder,
    )

    assert first == {"value": 1}
    assert second == {"value": 2}
    assert second_status["reason"] == "input_manifest_changed"
    assert calls["count"] == 2


def test_peek_command_node_refuses_changed_declared_inputs_without_rebuild(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("one", encoding="utf-8")
    calls = {"count": 0}

    def builder():
        calls["count"] += 1
        return {"value": calls["count"]}

    cached_command_node(
        tmp_path,
        node_id="demo.peek",
        key="same",
        input_paths=[source],
        ttl_s=60,
        builder=builder,
    )
    first, first_status = peek_cached_command_node(
        tmp_path,
        node_id="demo.peek",
        key="same",
        input_paths=[source],
        ttl_s=60,
    )

    source.write_text("two with a different manifest", encoding="utf-8")
    second, second_status = peek_cached_command_node(
        tmp_path,
        node_id="demo.peek",
        key="same",
        input_paths=[source],
        ttl_s=60,
    )

    assert first == {"value": 1}
    assert first_status["status"] == "stale_ok_hit"
    assert first_status["reason"] == "cache_valid_for_declared_inputs"
    assert second is None
    assert second_status["status"] == "deferred_stale_cache"
    assert second_status["reason"] == "input_manifest_changed"
    assert calls["count"] == 1


def test_command_node_cache_can_be_disabled_or_refreshed(tmp_path, monkeypatch):
    source = tmp_path / "source.txt"
    source.write_text("one", encoding="utf-8")
    calls = {"count": 0}

    def builder():
        calls["count"] += 1
        return {"value": calls["count"]}

    first, _ = cached_command_node(
        tmp_path,
        node_id="demo.controls",
        key="same",
        input_paths=[source],
        ttl_s=60,
        builder=builder,
    )
    monkeypatch.setenv("AIW_COMMAND_CACHE", "0")
    disabled, disabled_status = cached_command_node(
        tmp_path,
        node_id="demo.controls",
        key="same",
        input_paths=[source],
        ttl_s=60,
        builder=builder,
    )
    monkeypatch.delenv("AIW_COMMAND_CACHE")
    forced, forced_status = cached_command_node(
        tmp_path,
        node_id="demo.controls",
        key="same",
        input_paths=[source],
        ttl_s=60,
        builder=builder,
        force_refresh=True,
    )
    monkeypatch.setenv("AIW_COMMAND_CACHE_REFRESH", "1")
    refreshed, refreshed_status = cached_command_node(
        tmp_path,
        node_id="demo.controls",
        key="same",
        input_paths=[source],
        ttl_s=60,
        builder=builder,
    )

    assert first == {"value": 1}
    assert disabled == {"value": 2}
    assert disabled_status["status"] == "disabled_built"
    assert forced == {"value": 3}
    assert forced_status["status"] == "miss_built"
    assert forced_status["reason"] == "force_refresh_requested"
    assert refreshed == {"value": 4}
    assert refreshed_status["status"] == "miss_built"
    assert refreshed_status["reason"] == "AIW_COMMAND_CACHE_REFRESH=1"


def test_command_node_cache_ttl_expiration_rebuilds(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("one", encoding="utf-8")
    calls = {"count": 0}

    def builder():
        calls["count"] += 1
        return {"value": calls["count"]}

    cached_command_node(
        tmp_path,
        node_id="demo.ttl",
        key="same",
        input_paths=[source],
        ttl_s=0.001,
        builder=builder,
    )
    time.sleep(0.01)
    payload, status = cached_command_node(
        tmp_path,
        node_id="demo.ttl",
        key="same",
        input_paths=[source],
        ttl_s=0.001,
        builder=builder,
    )

    assert payload == {"value": 2}
    assert status["reason"] == "expired"


def test_command_node_cache_corrupt_json_rebuilds(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("one", encoding="utf-8")
    calls = {"count": 0}

    def builder():
        calls["count"] += 1
        return {"value": calls["count"]}

    cached_command_node(
        tmp_path,
        node_id="demo.corrupt",
        key={"q": "same"},
        input_paths=[source],
        ttl_s=60,
        builder=builder,
    )
    cache_files = list((tmp_path / "state" / "command_cache" / "demo.corrupt").glob("*.json"))
    assert len(cache_files) == 1
    cache_files[0].write_text("{not json", encoding="utf-8")

    payload, status = cached_command_node(
        tmp_path,
        node_id="demo.corrupt",
        key={"q": "same"},
        input_paths=[source],
        ttl_s=60,
        builder=builder,
    )

    assert payload == {"value": 2}
    assert status["status"] == "miss_built"
    assert status["reason"] == "missing"


def test_command_node_cache_status_labels_freshness_policy_honestly(tmp_path):
    """Callers with dynamic inputs must surface that label in cache_status."""
    source = tmp_path / "source.txt"
    source.write_text("one", encoding="utf-8")
    calls = {"count": 0}

    def builder():
        calls["count"] += 1
        return {"value": calls["count"]}

    _, status_default = cached_command_node(
        tmp_path,
        node_id="demo.freshness.default",
        key="same",
        input_paths=[source],
        ttl_s=60,
        builder=builder,
    )
    _, status_dynamic = cached_command_node(
        tmp_path,
        node_id="demo.freshness.dynamic",
        key="same",
        input_paths=[source],
        ttl_s=60,
        builder=builder,
        freshness_policy="ttl_for_dynamic_session_state_plus_static_source_manifest",
        dynamic_inputs_manifested=False,
    )

    assert status_default["freshness_policy"] == "ttl_plus_input_manifest"
    assert status_default["dynamic_inputs_manifested"] is True
    assert status_dynamic["freshness_policy"] == "ttl_for_dynamic_session_state_plus_static_source_manifest"
    assert status_dynamic["dynamic_inputs_manifested"] is False


def test_command_node_cache_singleflights_across_processes(tmp_path):
    """N concurrent processes asking for the same cold node must run the builder once."""
    counter_path = tmp_path / "build_counter.txt"
    counter_path.write_text("0", encoding="utf-8")

    process_count = 6
    args = [
        (
            str(tmp_path),
            "demo.singleflight",
            f"shared_key",
            str(counter_path),
            0.4,
        )
        for _ in range(process_count)
    ]
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(processes=process_count) as pool:
        statuses = pool.map(_singleflight_worker, args)

    final_count = int(counter_path.read_text(encoding="utf-8").strip())
    assert final_count == 1, f"builder ran {final_count} times across {process_count} workers"
    miss_built = statuses.count("miss_built")
    waited_or_hit = statuses.count("waited_hit") + statuses.count("hit")
    assert miss_built == 1, f"expected exactly one miss_built, got statuses={statuses}"
    assert miss_built + waited_or_hit == process_count, f"unexpected status mix: {statuses}"
