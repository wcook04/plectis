from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from plectis.views import compile_public, run_public, run_public_batch, InvalidInput, RejectedPlan
import plectis.views._api as api

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "examples/operations/public_views/schema.json").read_text())
PLAN = json.loads((ROOT / "examples/operations/public_views/mixed_report.json").read_text())
ROW = {"run_id": "r1", "score": "8/10", "passed": True}


def emit(expr, channel="public"):
    return {"emit": {"channel": channel, "value": expr}}


class ReleaseBoundaryTests(unittest.TestCase):
    def test_useful_mixed_report(self):
        compiled = compile_public(PLAN, SCHEMA)
        self.assertEqual(run_public(compiled, ROW), ("r1: 8/10", "passed"))
        self.assertEqual(compiled.read_fields, ("run_id", "score", "passed"))
        self.assertNotIn("private_note", json.dumps(compiled.public_plan))
        self.assertNotIn("embargo", json.dumps(compiled.public_plan))

    def test_explicit_flow_refused(self):
        with self.assertRaisesRegex(RejectedPlan, "private field"):
            compile_public(emit({"input": "private_note"}), SCHEMA)

    def test_constant_occurrence_flow_refused(self):
        bad = json.loads((ROOT / "examples/operations/public_views/implicit_leak.json").read_text())
        with self.assertRaisesRegex(RejectedPlan, "private control"):
            compile_public(bad, SCHEMA)

    def test_constant_value_flow_refused(self):
        bad = {"if": {"condition": {"input": "embargo"},
                      "then": emit({"literal": "yes"}), "else": emit({"literal": "no"})}}
        with self.assertRaises(RejectedPlan):
            compile_public(bad, SCHEMA)

    def test_conservative_refusal_is_visible(self):
        # These two branches are equal, but the syntactic checker is conservative.
        same = emit({"literal": "same"})
        with self.assertRaises(RejectedPlan):
            compile_public({"if": {"condition": {"input": "embargo"}, "then": same, "else": same}}, SCHEMA)

    def test_private_only_conditional_is_erasable(self):
        private = {"if": {"condition": {"input": "embargo"},
                          "then": emit({"input": "private_note"}, "internal"), "else": {"skip": True}}}
        compiled = compile_public({"seq": [private, emit({"literal": "complete"})]}, SCHEMA)
        self.assertEqual(compiled.public_plan["seq"][0], {"skip": True})
        self.assertEqual(run_public(compiled, ROW), ("complete",))

    def test_no_private_value_crosses_worker_before_rejection(self):
        compiled = compile_public(PLAN, SCHEMA)
        messages = []
        original = api._call
        def spy(message):
            messages.append(message)
            return original(message)
        with patch.object(api, "_call", spy):
            with self.assertRaises(InvalidInput):
                run_public(compiled, {**ROW, "private_note": object()})
        self.assertEqual([m["action"] for m in messages], ["compile"])

    def test_unknown_or_missing_public_field_refused(self):
        compiled = compile_public(PLAN, SCHEMA)
        for row in ({"run_id": "r1", "score": "8/10"}, {**ROW, "unknown": "x"}):
            with self.assertRaises(InvalidInput):
                run_public(compiled, row)

    def test_late_added_private_key_cannot_enter_wire_snapshot(self):
        compiled = compile_public(PLAN, SCHEMA)
        row = dict(ROW)
        original = api._call
        def mutate_at_transport(message):
            if message["action"] == "run":
                row["private_note"] = "SYNTHETIC_LATE_PRIVATE_VALUE"
                self.assertNotIn("private_note", message["rows"][0])
            return original(message)
        with patch.object(api, "_call", mutate_at_transport):
            self.assertEqual(run_public(compiled, row), ("r1: 8/10", "passed"))

    def test_nested_invalid_value_refused_before_transport(self):
        compiled = compile_public(PLAN, SCHEMA)
        messages = []
        original = api._call
        def spy(message):
            messages.append(message["action"])
            return original(message)
        with patch.object(api, "_call", spy):
            with self.assertRaises(InvalidInput):
                run_public(compiled, {**ROW, "run_id": {"internal": "SYNTHETIC_PRIVATE_VALUE"}})
        self.assertEqual(messages, ["compile"])

    def test_bool_is_not_integer_or_text(self):
        compiled = compile_public(PLAN, SCHEMA)
        for row in ({**ROW, "passed": 1}, {**ROW, "score": 8}, {**ROW, "passed": "true"}):
            with self.assertRaises(InvalidInput):
                run_public(compiled, row)

    def test_independent_policy_cannot_be_overridden_in_plan(self):
        with self.assertRaises(InvalidInput):
            compile_public({"emit": {"channel": "public", "value": {"input": "private_note", "visibility": "public"}}}, SCHEMA)

    def test_type_errors_and_unknown_reads_refused(self):
        bad_plans = [emit({"input": "passed"}), emit({"concat": [{"input": "score"}, {"literal": False}]}),
                     {"if": {"condition": {"equals": [{"input": "score"}, {"literal": True}]}, "then": {"skip": True}, "else": {"skip": True}}}]
        for plan in bad_plans:
            with self.assertRaises(RejectedPlan):
                compile_public(plan, SCHEMA)
        with self.assertRaises(InvalidInput):
            compile_public(emit({"input": "absent"}), SCHEMA)

    def test_snapshot_survives_mutation_of_original_inputs(self):
        plan, schema = copy.deepcopy(PLAN), copy.deepcopy(SCHEMA)
        compiled = compile_public(plan, schema)
        plan.clear()
        schema["fields"][0]["visibility"] = "private"
        detached = compiled.public_plan
        detached.clear()
        self.assertEqual(run_public(compiled, ROW), ("r1: 8/10", "passed"))

    def test_forged_cached_slice_or_fields_cannot_change_execution(self):
        compiled = compile_public(PLAN, SCHEMA)
        forged = dataclasses.replace(compiled, _public_plan_json=json.dumps(emit({"literal": "forged"})),
                                     public_fields=("private_note",), digest="fake")
        self.assertEqual(run_public(forged, ROW), ("r1: 8/10", "passed"))
        with self.assertRaises(InvalidInput):
            run_public(forged, {**ROW, "private_note": "not sent"})

    def test_forged_source_is_rechecked(self):
        compiled = compile_public(PLAN, SCHEMA)
        forged = dataclasses.replace(compiled, _plan_json=json.dumps(emit({"input": "private_note"})))
        with self.assertRaises(RejectedPlan):
            run_public(forged, ROW)

    def test_duplicate_schema_and_bool_version_refused(self):
        duplicate = copy.deepcopy(SCHEMA)
        duplicate["fields"].append(copy.deepcopy(duplicate["fields"][0]))
        for schema in (duplicate, {**SCHEMA, "version": True}, {**SCHEMA, "extra": 1}):
            with self.assertRaises(InvalidInput):
                compile_public(PLAN, schema)

    def test_unknown_constructors_no_eval_or_callback(self):
        for plan in ({"python": "raise Exception('must not execute')"}, {"call": "anything"}, {"skip": 1}):
            with self.assertRaises(InvalidInput):
                compile_public(plan, SCHEMA)

    def test_exact_json_input_types(self):
        for plan in ({"seq": ({"skip": True}, {"skip": True})}, {1: {"skip": True}}):
            with self.assertRaises(InvalidInput):
                compile_public(plan, SCHEMA)

    def test_unicode_scalar_roundtrip_and_surrogate_refusal(self):
        text = "Zürich 🧪\nα\u0000"
        compiled = compile_public(emit({"literal": text}), SCHEMA)
        self.assertEqual(run_public(compiled, ROW), (text,))
        with self.assertRaises(InvalidInput):
            compile_public(emit({"literal": "\ud800"}), SCHEMA)

    def test_private_known_literal_limit_demonstrated(self):
        # The checker cannot identify a private value already embedded in the plan.
        compiled = compile_public(emit({"literal": "SYNTHETIC_SECRET_ALREADY_KNOWN"}), SCHEMA)
        self.assertEqual(run_public(compiled, ROW), ("SYNTHETIC_SECRET_ALREADY_KNOWN",))

    def test_empty_report_is_secure_but_not_useful(self):
        compiled = compile_public({"skip": True}, SCHEMA)
        self.assertEqual(run_public(compiled, ROW), ())
        self.assertNotEqual(run_public(compiled, ROW), ("r1: 8/10", "passed"))

    def test_batch_order_and_public_multiplicity(self):
        compiled = compile_public(PLAN, SCHEMA)
        rows = [ROW, {**ROW, "run_id": "r2", "passed": False}, ROW]
        self.assertEqual(run_public_batch(compiled, rows), (("r1: 8/10", "passed"), ("r2: 8/10", "needs review"), ("r1: 8/10", "passed")))
        self.assertEqual(run_public_batch(compiled, []), ())

    def test_limits_refuse_without_silent_truncation(self):
        with self.assertRaises(InvalidInput):
            compile_public(emit({"literal": "x" * 16385}), SCHEMA)
        deep = {"skip": True}
        for _ in range(35):
            deep = {"seq": [{"skip": True}, deep]}
        with self.assertRaises(InvalidInput):
            compile_public(deep, SCHEMA)

    def test_raw_worker_duplicate_keys_and_nonfinite(self):
        worker = Path(api.__file__).with_name("_worker.py")
        for payload in ('{"action":"compile","action":"run"}', '{"action":NaN}', '[]'):
            result = subprocess.run([sys.executable, "-I", str(worker)], input=payload, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertFalse(json.loads(result.stdout)["ok"])

    def test_absent_core_never_falls_back(self):
        with patch.object(api, "_WORKER", ROOT / "does-not-exist.py"):
            with self.assertRaises(InvalidInput):
                compile_public(PLAN, SCHEMA)

    def test_malformed_worker_success_is_never_a_report_or_plan(self):
        cases = [
            ({"action": "compile"}, {"ok": True}),
            ({"action": "compile"}, {"ok": True, "public_plan": {}, "public_fields": ["x", "x"], "read_fields": []}),
            ({"action": "compile"}, {"ok": True, "public_plan": {}, "public_fields": ["x"], "read_fields": ["secret"]}),
            ({"action": "compile"}, {"ok": True, "public_plan": {}, "public_fields": [False], "read_fields": []}),
            ({"action": "run", "rows": [{}]}, {"ok": True, "traces": []}),
            ({"action": "run", "rows": [{}]}, {"ok": True, "traces": [[False]]}),
            ({"action": "run", "rows": [{}]}, {"ok": True, "traces": ["not-a-trace"]}),
            ({"action": "run", "rows": []}, {"ok": True, "traces": [], "unchecked": True}),
            ({"action": "run", "rows": []}, {"ok": False, "kind": "invalid", "reason": {}}),
        ]
        for request, response in cases:
            with self.subTest(response=response):
                completed = subprocess.CompletedProcess([], 0, json.dumps(response), "")
                with patch.object(api.subprocess, "run", return_value=completed):
                    with self.assertRaises(InvalidInput):
                        api._call(request)

    def test_duplicate_worker_reply_keys_are_refused(self):
        cases = [
            ({"action": "run", "rows": [{}]},
             '{"ok":false,"ok":true,"traces":[["accepted"]]}'),
            ({"action": "run", "rows": [{}]},
             '{"ok":true,"traces":[["first"]],"traces":[["second"]]}'),
            ({"action": "compile"},
             '{"ok":true,"public_plan":{"skip":true,"skip":false},'
             '"public_fields":[],"read_fields":[]}'),
        ]
        for request, wire in cases:
            with self.subTest(wire=wire):
                completed = subprocess.CompletedProcess([], 0, wire, "")
                with patch.object(api.subprocess, "run", return_value=completed):
                    with self.assertRaises(InvalidInput):
                        api._call(request)

    def test_worker_reply_text_must_use_unicode_scalars(self):
        cases = [
            ({"action": "run", "rows": [{}]}, {"ok": True, "traces": [["\ud800"]]}),
            ({"action": "run", "rows": [{}]}, {"ok": True, "traces": [["\udfff"]]}),
            ({"action": "compile"}, {"ok": True, "public_plan": emit({"literal": "\ud800"}),
                                     "public_fields": [], "read_fields": []}),
            ({"action": "compile"}, {"ok": True, "public_plan": {"skip": True},
                                     "public_fields": ["\ud800"], "read_fields": []}),
            ({"action": "compile"}, {"ok": False, "kind": "rejected", "reason": "\ud800"}),
        ]
        for request, response in cases:
            with self.subTest(response=response):
                completed = subprocess.CompletedProcess([], 0, json.dumps(response), "")
                with patch.object(api.subprocess, "run", return_value=completed):
                    with self.assertRaises(InvalidInput):
                        api._call(request)

    def test_shared_subtree_expansion_is_bounded_before_worker(self):
        plan = {"skip": True}
        for _ in range(18):
            plan = {"seq": [plan, plan]}
        with patch.object(api.subprocess, "run") as worker:
            with self.assertRaisesRegex(InvalidInput, "JSON node limit"):
                compile_public(plan, {"version": 1, "fields": []})
        worker.assert_not_called()

    def test_json_node_budget_keeps_full_batch_field_capacity(self):
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        names = list(alphabet) + ["A" + c for c in alphabet] + ["B" + c for c in alphabet[:24]]
        schema = {"version": 1, "fields": [
            {"name": name, "type": "text", "visibility": "public"} for name in names
        ]}
        row = dict.fromkeys(names, "")
        message = {"action": "run", "schema": schema, "plan": {"skip": True}, "rows": [row] * 2000}
        encoded = api._canonical(message)
        self.assertEqual(len(json.loads(encoded)["rows"]), 2000)
        self.assertLessEqual(len(encoded.encode("utf-8")), 2_000_000)


if __name__ == "__main__":
    unittest.main()
