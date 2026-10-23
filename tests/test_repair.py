import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest

import runpy

_example = runpy.run_path(str(Path(__file__).resolve().parents[1] / "examples/operations/repair.py"))
run_demo = _example["run_demo"]
ordinary_cache_oracle = _example["ordinary_cache_oracle"]
from plectis.repair._host import (EffectJournal, InvalidPlan, RepairSession, StalePlan, Task,
                    canonical, digest, kernel_request, parse)


def task(name, **changes):
    values = dict(code_id="test/" + name, version="1", deps=(), inputs=1,
                  contract="json-v1", environment="test-v1", freshness="frozen-v1",
                  replayable=True, fn=lambda inputs, deps: inputs if not deps else sum(deps))
    values.update(changes)
    return Task(name, **values)


def chain():
    return [task("a"), task("b", deps=("a",)), task("c", deps=("b",)), task("z")]


def complete(tasks):
    session = RepairSession(tasks)
    session.run(session.plan())
    return session


class DescriptorAndCheckpointTests(unittest.TestCase):
    def test_second_run_reuses_and_binds_actual_dependency_outputs(self):
        session = complete(chain())
        self.assertEqual(set(session.plan().classification().values()), {"reuse"})
        records = session.records
        self.assertEqual(records["b"]["dependency_digests"], [["a", records["a"]["output_digest"]]])
        self.assertEqual(len(session.run(session.plan()).reused), 4)

    def test_identity_changes_invalidate_descendants(self):
        records = complete(chain()).records
        for change in (dict(version="2"), dict(code_id="new-code"), dict(contract="v2"),
                       dict(environment="v2"), dict(freshness="v2"), dict(inputs=2)):
            with self.subTest(change=change):
                session = RepairSession([task("a", **change), *chain()[1:]], records=records)
                self.assertEqual(session.plan().classification(),
                                 {"a": "rerun", "b": "rerun", "c": "rerun", "z": "reuse"})

    def test_new_dependency_invalidates(self):
        old = [task("a"), task("b"), task("c", deps=("b",))]
        session = RepairSession([task("a"), task("b", deps=("a",)), old[2]],
                                records=complete(old).records)
        self.assertEqual(session.plan().classification(), {"a": "reuse", "b": "rerun", "c": "rerun"})

    def test_removed_dependency_invalidates(self):
        old = [task("a"), task("b"), task("c", deps=("a", "b"))]
        session = RepairSession([*old[:2], task("c", deps=("a",))], records=complete(old).records)
        self.assertEqual(session.plan().classification()["c"], "rerun")

    def test_dependency_order_is_semantic(self):
        old = [task("a", inputs=1), task("b", inputs=2),
               task("c", deps=("a", "b"), fn=lambda inputs, deps: list(deps))]
        records = complete(old).records
        new = [*old[:2], task("c", deps=("b", "a"), fn=lambda inputs, deps: list(deps))]
        session = RepairSession(new, records=records)
        self.assertEqual(session.plan().classification()["c"], "rerun")
        self.assertEqual(session.run(session.plan()).outputs["c"], [2, 1])

    def test_corrupt_output_bytes_rerun_known_pure_task(self):
        records = complete(chain()).records
        records["a"]["output_json"] = "999"
        session = RepairSession(chain(), records=records)
        self.assertEqual(session.plan().classification(),
                         {"a": "rerun", "b": "rerun", "c": "rerun", "z": "reuse"})
        self.assertEqual(session.run(session.plan()).outputs["c"], 1)

    def test_missing_and_incomplete_records(self):
        original = complete(chain()).records
        for variant in ("missing", "failed", "missing-output"):
            with self.subTest(variant=variant):
                records = copy.deepcopy(original)
                if variant == "missing":
                    del records["b"]
                elif variant == "failed":
                    records["b"]["status"] = "failed"
                else:
                    del records["b"]["output_json"]
                classes = RepairSession(chain(), records=records).plan().classification()
                self.assertEqual(classes, {"a": "reuse", "b": "rerun", "c": "rerun", "z": "reuse"})

    def test_actual_dependency_digest_mismatch(self):
        records = complete(chain()).records
        records["a"].update(output_json="2", output_digest=digest("2"))
        session = RepairSession(chain(), records=records)
        self.assertEqual(session.plan().classification(),
                         {"a": "reuse", "b": "rerun", "c": "rerun", "z": "reuse"})
        self.assertEqual(session.run(session.plan()).outputs["c"], 2)

    def test_corrupt_descriptor_is_conservative_effect_boundary(self):
        records = complete(chain()).records
        records["a"]["descriptor_json"] = "{}"
        session = RepairSession(chain(), records=records)
        self.assertEqual(session.plan().classification(),
                         {"a": "blocked", "b": "blocked", "c": "blocked", "z": "reuse"})

    def test_task_inputs_and_callback_arguments_are_detached(self):
        mutable = {"values": [1]}
        a = task("a", inputs=mutable, fn=lambda inputs, deps: inputs)
        mutable["values"].append(2)
        def modify(inputs, deps):
            deps[0]["values"].append(999)
            return deps[0]
        session = RepairSession([a, task("b", deps=("a",), fn=modify)])
        result = session.run(session.plan())
        self.assertEqual(result.outputs["a"], {"values": [1]})
        self.assertEqual(result.outputs["b"], {"values": [1, 999]})
        self.assertEqual(parse(a.inputs_json), {"values": [1]})

    def test_freshness_changes_sample_policy_explicitly(self):
        calls = []
        def sample(inputs, deps):
            calls.append(1)
            return len(calls)
        first = complete([task("sample", fn=sample)])
        same = RepairSession([task("sample", fn=sample)], records=first.records)
        self.assertEqual(same.run(same.plan()).outputs["sample"], 1)
        fresh = RepairSession([task("sample", fn=sample, freshness="new-sample-epoch")],
                              records=first.records)
        self.assertEqual(fresh.run(fresh.plan()).outputs["sample"], 2)

    def test_record_copies_do_not_mutate_stored_snapshot(self):
        session = complete(chain())
        exported = session.records
        exported["a"]["output_json"] = "999"
        self.assertEqual(session.run(session.plan()).outputs["a"], 1)

    def test_persistent_checkpoint_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            first = RepairSession(chain(), checkpoint=path)
            first.run(first.plan())
            second = RepairSession(chain(), checkpoint=path)
            self.assertEqual(len(second.run(second.plan()).reused), 4)


class GraphAndExecutionTests(unittest.TestCase):
    def test_duplicate_unknown_and_cyclic_graphs_rejected(self):
        graphs = ([task("a"), task("a")], [task("a", deps=("absent",))],
                  [task("a", deps=("b",)), task("b", deps=("a",))],
                  [task("a", deps=("a",))])
        for graph in graphs:
            with self.subTest(ids=[item.id for item in graph]), self.assertRaises(ValueError):
                RepairSession(graph)

    def test_descriptor_validation(self):
        for changes in (dict(version=""), dict(contract=""), dict(environment=""),
                        dict(freshness=""), dict(deps=("a", "a")), dict(replayable=1),
                        dict(inputs={1: "implicit conversion"}), dict(inputs=float("nan")),
                        dict(fn=None)):
            with self.subTest(change=changes), self.assertRaises(ValueError):
                task("x", **changes)

    def test_empty_graph(self):
        session = RepairSession([])
        self.assertEqual(session.plan().classification(), {})
        self.assertTrue(session.run(session.plan()).settled)

    def test_callback_failure_stops_dependents_but_not_independent_work(self):
        called = []
        def fail(inputs, deps):
            raise RuntimeError("intentional failure")
        graph = [task("a", fn=fail), task("b", deps=("a",),
                 fn=lambda inputs, deps: called.append("b")), task("z")]
        session = RepairSession(graph)
        result = session.run(session.plan())
        self.assertEqual(set(result.failed), {"a", "b"})
        self.assertEqual(result.executed, ("z",))
        self.assertEqual(called, [])
        self.assertFalse(result.settled)
        self.assertEqual(session.records["a"]["status"], "failed")

    def test_non_json_output_fails_before_dependent_dispatch(self):
        session = RepairSession([task("a", fn=lambda inputs, deps: float("nan")),
                                 task("b", deps=("a",))])
        result = session.run(session.plan())
        self.assertEqual(set(result.failed), {"a", "b"})
        self.assertFalse(result.outputs)

    def test_nonreplayable_is_default_even_with_callback(self):
        called = []
        boundary = Task("effect", code_id="effect", version="1", contract="json",
                        environment="local", freshness="fixed",
                        fn=lambda inputs, deps: called.append("effect"))
        session = RepairSession([boundary])
        self.assertEqual(session.run(session.plan()).blocked, ("effect",))
        self.assertEqual(called, [])


class EffectTests(unittest.TestCase):
    def graph(self, **changes):
        return [task("a"), task("effect", deps=("a",), replayable=False, **changes),
                task("after", deps=("effect",)), task("z")]

    def started(self):
        session = complete(self.graph())
        attempt = session.begin_effect("effect")
        return session, attempt

    def test_first_execution_blocks_effect_and_descendants(self):
        session = RepairSession(self.graph())
        result = session.run(session.plan())
        self.assertEqual(result.executed, ("a", "z"))
        self.assertEqual(result.blocked, ("effect", "after"))

    def test_effect_requires_ready_dependencies(self):
        session = RepairSession(self.graph())
        with self.assertRaisesRegex(ValueError, "not ready"):
            session.begin_effect("effect")

    def test_unknown_effect_cannot_be_retried(self):
        session, attempt = self.started()
        session.mark_unknown(attempt, "ack lost")
        with self.assertRaisesRegex(ValueError, "unsettled"):
            session.begin_effect("effect")
        result = session.run(session.plan())
        self.assertEqual(result.blocked, ("effect", "after"))
        self.assertFalse(result.settled)

    def test_unknown_history_invalidates_unchanged_cached_effect(self):
        confirmed, attempt = self.started()
        confirmed.resolve_effect(attempt, 7)
        confirmed.run(confirmed.plan())
        old_records = confirmed.records
        ambiguous, other = self.started()
        ambiguous.mark_unknown(other, "lost acknowledgement")
        restored = RepairSession(self.graph(), records=old_records, journal=ambiguous.journal)
        plan = restored.plan()
        index = plan.order.index("effect")
        self.assertTrue(plan.roots[index])
        self.assertIn("unsettled external effect", plan.reasons[index])
        self.assertEqual(plan.classification()["effect"], "blocked")

    def test_unknown_checkpoint_status_overrides_replayable_declaration(self):
        records = complete([task("a")]).records
        records["a"]["status"] = "unknown"
        session = RepairSession([task("a")], records=records)
        self.assertEqual(session.plan().classification()["a"], "blocked")
        with self.assertRaisesRegex(ValueError, "unsettled"):
            session.begin_effect("a")

    def test_pruned_imported_unknown_checkpoint_remains_unsettled(self):
        records = complete([task("a")]).records
        records["a"]["status"] = "unknown"
        session = RepairSession([task("new")], records=records)
        result = session.run(session.plan())
        self.assertEqual(result.executed, ("new",))
        self.assertFalse(result.settled)
        self.assertEqual(result.unresolved_effects[0]["task"], "a")

    def test_resolved_effect_is_reused_without_invocation(self):
        session, attempt = self.started()
        session.resolve_effect(attempt, 7)
        result = session.run(session.plan())
        self.assertEqual(result.outputs["after"], 7)
        self.assertIn("effect", result.reused)
        self.assertTrue(result.settled)

    def test_flag_change_cannot_erase_old_nonreplayable_record(self):
        session, attempt = self.started()
        session.resolve_effect(attempt, 7)
        new = [task("a"), task("effect", deps=("a",), replayable=True),
               task("after", deps=("effect",)), task("z")]
        # Even with only the old record (no journal), the declaration survives.
        changed = RepairSession(new, records=session.records)
        self.assertEqual(changed.plan().classification()["effect"], "blocked")

    def test_effect_attempt_marker_survives_records_only_handoff(self):
        # A legacy/corrupt descriptor requires trusted external resolution,
        # even if the current task declaration is replayable. That resolution
        # leaves an effect marker which must survive omission of the journal.
        records = complete([task("a")]).records
        records["a"]["descriptor_json"] = "{}"
        repaired = RepairSession([task("a")], records=records)
        attempt = repaired.begin_effect("a")
        repaired.resolve_effect(attempt, 7)
        self.assertTrue(parse(repaired.records["a"]["descriptor_json"])["replayable"])
        self.assertEqual(repaired.records["a"]["effect_attempt"], attempt)
        called = []
        transferred = RepairSession([task("a", version="2", fn=lambda inputs, deps: called.append(1))],
                                    records=repaired.records)
        result = transferred.run(transferred.plan())
        self.assertEqual(result.blocked, ("a",))
        self.assertEqual(called, [])
        self.assertFalse(result.settled)

    def test_malformed_effect_attempt_marker_is_blocked(self):
        original = complete([task("a")]).records
        for marker in ("", None, True):
            with self.subTest(marker=marker):
                records = copy.deepcopy(original)
                records["a"]["effect_attempt"] = marker
                session = RepairSession([task("a")], records=records)
                self.assertEqual(session.plan().classification()["a"], "blocked")

    def test_flag_change_cannot_erase_unknown_history(self):
        session, attempt = self.started()
        session.mark_unknown(attempt, "ack lost")
        new = [task("a"), task("effect", deps=("a",), replayable=True), task("z")]
        changed = RepairSession(new, records=session.records, journal=session.journal)
        self.assertEqual(changed.plan().classification()["effect"], "blocked")

    def test_pruned_unknown_effect_remains_unsettled(self):
        session, attempt = self.started()
        session.mark_unknown(attempt, "ack lost")
        pruned = RepairSession([task("a"), task("z", version="2")],
                               records=session.records, journal=session.journal)
        result = pruned.run(pruned.plan())
        self.assertEqual(result.executed, ("z",))
        self.assertFalse(result.blocked)
        self.assertFalse(result.settled)
        self.assertEqual(result.unresolved_effects[0]["task"], "effect")

    def test_empty_graph_does_not_settle_removed_unknown_effect(self):
        session, attempt = self.started()
        session.mark_unknown(attempt, "ack lost")
        empty = RepairSession([], journal=session.journal)
        self.assertFalse(empty.run(empty.plan()).settled)

    def test_exported_journal_events_cannot_erase_history(self):
        session, attempt = self.started()
        session.mark_unknown(attempt, "ack lost")
        exported = session.journal.events
        exported.clear()
        self.assertEqual(len(session.journal.unresolved()), 1)

    def test_resolution_preserves_original_attempt_binding(self):
        session, attempt = self.started()
        changed = RepairSession(self.graph(contract="changed-contract"),
                                records=session.records, journal=session.journal)
        changed.resolve_effect(attempt, 7)
        self.assertEqual(changed.plan().classification()["effect"], "blocked")
        self.assertFalse(changed.journal.unresolved())

    def test_file_journal_is_append_only_and_reload_preserves_ambiguity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "effects.jsonl"
            session = RepairSession(self.graph(), journal=path)
            session.run(session.plan())
            attempt = session.begin_effect("effect")
            prefix = path.read_bytes()
            session.mark_unknown(attempt, "ack lost")
            self.assertTrue(path.read_bytes().startswith(prefix))
            self.assertEqual(len(EffectJournal(path).unresolved()), 1)
            lines = path.read_text().splitlines()
            event = json.loads(lines[-1]); event["reason"] = "edited"
            lines[-1] = json.dumps(event)
            path.write_text("\n".join(lines) + "\n")
            with self.assertRaisesRegex(ValueError, "chain mismatch"):
                EffectJournal(path)


class CertificateTests(unittest.TestCase):
    def test_underinvalidating_candidate_rejected_before_callbacks(self):
        called = []
        session = RepairSession([task("a", fn=lambda inputs, deps: called.append(1))])
        plan = session.plan()
        with self.assertRaises(InvalidPlan):
            session.run(replace(plan, dirty=(False,)))
        self.assertEqual(called, [])

    def test_overinvalidating_candidate_rejected(self):
        session = complete(chain())
        with self.assertRaises(InvalidPlan):
            session.run(replace(session.plan(), dirty=(True,) * 4))

    def test_effect_barrier_mutant_rejected(self):
        session = RepairSession([task("a"), task("effect", deps=("a",), replayable=False),
                                 task("after", deps=("effect",))])
        plan = session.plan()
        with self.assertRaises(InvalidPlan):
            session.run(replace(plan, blocked=(False,) * 3))

    def test_stale_records_rejected(self):
        session = RepairSession(chain())
        plan = session.plan()
        session.run(plan)
        with self.assertRaises(StalePlan):
            session.run(plan)

    def test_stale_task_descriptor_rejected(self):
        old = RepairSession(chain()).plan()
        changed = RepairSession([task("a", inputs=2), *chain()[1:]])
        with self.assertRaises(StalePlan):
            changed.run(old)

    def test_stale_journal_rejected(self):
        session = complete([task("a"), task("effect", deps=("a",), replayable=False)])
        plan = session.plan()
        session.begin_effect("effect")
        with self.assertRaises(StalePlan):
            session.run(plan)

    def test_checkpoint_file_changed_after_plan_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            session = RepairSession(chain(), checkpoint=path)
            session.run(session.plan())
            plan = session.plan()
            stored = json.loads(path.read_text())
            stored["records"]["a"]["output_json"] = "999"
            path.write_text(json.dumps(stored))
            with self.assertRaises(StalePlan):
                session.run(plan)

    def test_equally_informed_cache_ties_on_branched_graph(self):
        session = RepairSession([task("a"), task("b", deps=("a",)),
                                 task("effect", deps=("b",), replayable=False),
                                 task("after", deps=("effect",)), task("z")])
        plan = session.plan()
        self.assertEqual(ordinary_cache_oracle(plan), plan.classification())


class KernelBoundaryTests(unittest.TestCase):
    def test_strict_decoder_rejects_malformed_requests(self):
        base = {"op": "make", "deps": [[], [0]], "roots": [True, False],
                "effects": [False, False]}
        variants = []
        for value in (-1, False, True, 1, 0.0, "0", None):
            request = copy.deepcopy(base); request["deps"][1] = [value]; variants.append(request)
        for field, value in (("roots", [1, 0]), ("effects", [False, "false"]),
                             ("roots", [False]), ("deps", {}), ("deps", [[], 0]),
                             ("roots", None)):
            request = copy.deepcopy(base); request[field] = value; variants.append(request)
        request = copy.deepcopy(base); request["extra"] = 1; variants.append(request)
        request = copy.deepcopy(base); request["op"] = "unknown"; variants.append(request)
        request = copy.deepcopy(base); request.update(op="check", dirty=[1, 1], blocked=[False, False]); variants.append(request)
        request = copy.deepcopy(base); request.update(op="check", dirty=[True, True], blocked=[0, 0]); variants.append(request)
        self.assertEqual(len(variants), 17)
        for index, request in enumerate(variants):
            with self.subTest(case=index), self.assertRaises(InvalidPlan):
                kernel_request(request)

    def test_duplicate_json_keys_rejected(self):
        from plectis.repair import _worker
        worker = Path(_worker.__file__)
        completed = subprocess.run([sys.executable, "-I", "-B", str(worker)], text=True,
                                   input='{"op":"make","op":"check","deps":[],"roots":[],"effects":[]}',
                                   capture_output=True)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("duplicate JSON key", completed.stdout)

    def test_integer_candidate_flags_rejected_in_dispatch_path(self):
        session = RepairSession([task("a")])
        with self.assertRaises(InvalidPlan):
            session.run(replace(session.plan(), dirty=(1,)))

    def test_kernel_does_not_pollute_or_trust_callers_module_names(self):
        prior = {name: sys.modules.get(name) for name in ("Repair", "_dafny", "module_")}
        sentinels = {name: types.ModuleType(name) for name in prior}
        try:
            sys.modules.update(sentinels)
            self.assertEqual(RepairSession([task("a")]).plan().classification(), {"a": "rerun"})
            for name, sentinel in sentinels.items():
                self.assertIs(sys.modules[name], sentinel)
        finally:
            for name, previous in prior.items():
                if previous is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = previous

    def test_vendored_generated_python_matches_manifest(self):
        from plectis.repair import _host
        root = Path(_host.__file__).with_name("_generated")
        manifest = json.loads((root / "GENERATED_SHA256.json").read_text())
        self.assertEqual(len(manifest), 5)
        for filename, expected in manifest.items():
            self.assertEqual(hashlib.sha256((root / filename).read_bytes()).hexdigest(), expected)


class WorkedDemoTests(unittest.TestCase):
    def test_evaluation_repair_restart_and_pruned_unknown_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_demo(directory)
        self.assertEqual(result["comparison"]["verified_repair"],
                         result["comparison"]["equally_informed_dependency_cache"])
        self.assertEqual(result["comparison"]["restart_with_same_effect_safety"]["sample_callbacks"], 3)
        self.assertEqual(result["simulated_publish_invocations"], 1)
        self.assertEqual(result["automatic_publish_callback_invocations"], 0)
        self.assertFalse(result["pruned_graph"]["settled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
