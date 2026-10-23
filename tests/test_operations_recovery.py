# SPDX-License-Identifier: Apache-2.0
"""Useful completion and refusal tests for confirmed-output recovery."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from plectis.repair import RepairSession, Task
from plectis.repair import _host


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.checkpoint = Path(self.directory.name) / 'checkpoint.json'
        self.calls = []

    def graph(self, value=1, request='original'):
        def input_callback(inputs, deps):
            self.calls.append('input')
            return inputs

        def forbidden_effect(inputs, deps):
            self.calls.append('EXTERNAL EFFECT')
            raise AssertionError('recovery must not execute an effect')

        def report_callback(inputs, deps):
            self.calls.append('report')
            return {'recovered_result': deps[0]}

        return [
            Task('input', code_id='example/input', version='1', inputs=value,
                 contract='json-v1', environment='local', freshness='frozen',
                 replayable=True, fn=input_callback),
            Task('send', code_id='example/send', version='1', deps=('input',),
                 inputs=request, contract='json-v1', environment='local',
                 freshness='frozen', fn=forbidden_effect),
            Task('report', code_id='example/report', version='1', deps=('send',),
                 contract='json-v1', environment='local', freshness='frozen',
                 replayable=True, fn=report_callback),
        ]

    def session(self, value=1, request='original'):
        return RepairSession(self.graph(value, request), checkpoint=self.checkpoint)

    @staticmethod
    def fail_save():
        raise OSError('injected checkpoint save failure')

    def confirmed_gap(self):
        original = self.session()
        original.run(original.plan())
        attempt = original.begin_effect('send')
        original._save = self.fail_save
        with self.assertRaisesRegex(OSError, 'injected'):
            original.resolve_effect(attempt, {'accepted_input': 1})
        self.assertNotIn('send', self.session().records)
        self.calls.clear()
        return attempt

    def rewrite_journal(self, mutate):
        """Rehash controlled malformed history to test semantic validation."""
        path = Path(str(self.checkpoint) + '.effects.jsonl')
        events = [json.loads(line) for line in path.read_text().splitlines()]
        mutate(events)
        previous = ''
        for event in events:
            event['previous'] = previous
            body = {key: value for key, value in event.items() if key != 'hash'}
            event['hash'] = _host.digest(_host.canonical(body))
            previous = event['hash']
        path.write_text(''.join(_host.canonical(event) + '\n' for event in events))

    def test_recovery_restores_useful_continuation_without_dispatch(self):
        attempt = self.confirmed_gap()
        restored = self.session()
        journal_before = restored.journal.path.read_bytes()
        start, confirmation = restored.journal.refresh()[attempt]
        self.assertTrue(restored.recover_confirmed(attempt))
        self.assertEqual(self.calls, [])
        record = restored.records['send']
        for field in ('descriptor_json', 'signature', 'dependency_digests'):
            self.assertEqual(record[field], start[field])
        self.assertEqual(record['effect_attempt'], attempt)
        self.assertEqual(record['output_json'], confirmation['output_json'])
        self.assertEqual(record['output_digest'], confirmation['output_digest'])
        self.assertEqual(restored.journal.path.read_bytes(), journal_before)

        result = restored.run(restored.plan())
        self.assertEqual(result.reused, ('input', 'send'))
        self.assertEqual(result.executed, ('report',))
        self.assertEqual(result.outputs['report'],
                         {'recovered_result': {'accepted_input': 1}})
        self.assertTrue(result.settled)
        self.assertEqual(self.calls, ['report'])

    def test_identical_materialisation_is_idempotent_after_restart(self):
        attempt = self.confirmed_gap()
        self.assertTrue(self.session().recover_confirmed(attempt))
        before = self.checkpoint.read_bytes()
        self.assertFalse(self.session().recover_confirmed(attempt))
        self.assertEqual(self.checkpoint.read_bytes(), before)
        self.assertEqual(self.calls, [])

    def test_changed_dependency_does_not_make_old_result_current(self):
        attempt = self.confirmed_gap()
        changed = self.session(value=2)
        start, _ = changed.journal.refresh()[attempt]
        self.assertTrue(changed.recover_confirmed(attempt))
        self.assertEqual(changed.records['send']['dependency_digests'],
                         start['dependency_digests'])
        result = changed.run(changed.plan())
        self.assertEqual(result.executed, ('input',))
        self.assertEqual(result.blocked, ('send', 'report'))
        self.assertNotIn('send', result.outputs)
        self.assertFalse(result.settled)
        self.assertEqual(self.calls, ['input'])

    def test_changed_descriptor_remains_historical(self):
        attempt = self.confirmed_gap()
        changed = self.session(request='different')
        self.assertTrue(changed.recover_confirmed(attempt))
        historical = json.loads(changed.records['send']['descriptor_json'])
        self.assertEqual(historical['inputs'], 'original')
        result = changed.run(changed.plan())
        self.assertEqual(result.blocked, ('send', 'report'))
        self.assertEqual(self.calls, [])

    def test_requested_unknown_and_missing_attempts_are_refused(self):
        original = self.session()
        original.run(original.plan())
        attempt = original.begin_effect('send')
        for candidate in (attempt, 'missing'):
            before = self.checkpoint.read_bytes()
            with self.assertRaisesRegex(ValueError, 'must be confirmed'):
                original.recover_confirmed(candidate)
            self.assertEqual(self.checkpoint.read_bytes(), before)
        original.mark_unknown(attempt, 'acknowledgement lost')
        with self.assertRaisesRegex(ValueError, 'must be confirmed'):
            original.recover_confirmed(attempt)
        self.assertNotIn('send', original.records)

    def test_invalid_attempt_types_are_refused(self):
        self.confirmed_gap()
        original = self.session()
        for attempt in ('', None, False, 3, []):
            with self.subTest(attempt=attempt):
                with self.assertRaisesRegex(ValueError, 'nonempty string'):
                    original.recover_confirmed(attempt)

    def test_another_save_failure_can_be_retried_without_redispatch(self):
        attempt = self.confirmed_gap()
        restored = self.session()
        journal_before = restored.journal.path.read_bytes()
        checkpoint_before = self.checkpoint.read_bytes()
        save = restored._save
        restored._save = self.fail_save
        with self.assertRaisesRegex(OSError, 'injected'):
            restored.recover_confirmed(attempt)
        self.assertEqual(self.checkpoint.read_bytes(), checkpoint_before)
        self.assertEqual(restored.journal.path.read_bytes(), journal_before)
        restored._save = save
        self.assertTrue(restored.recover_confirmed(attempt))
        self.assertFalse(self.session().recover_confirmed(attempt))
        self.assertEqual(self.calls, [])

    def test_older_confirmation_cannot_overwrite_newer_valid_record(self):
        old_attempt = self.confirmed_gap()
        changed = self.session(value=2, request='new')
        changed.run(changed.plan())
        new_attempt = changed.begin_effect('send')
        changed.resolve_effect(new_attempt, {'accepted_input': 2})
        before = self.checkpoint.read_bytes()
        with self.assertRaisesRegex(ValueError, 'conflicting checkpoint'):
            changed.recover_confirmed(old_attempt)
        self.assertEqual(self.checkpoint.read_bytes(), before)
        self.assertEqual(changed.records['send']['effect_attempt'], new_attempt)
        self.assertFalse(changed.recover_confirmed(new_attempt))
        self.assertNotIn('EXTERNAL EFFECT', self.calls)

    def test_lost_checkpoint_save_acknowledgement_is_idempotent(self):
        attempt = self.confirmed_gap()
        restored = self.session()
        save = restored._save

        def saved_then_failed():
            save()
            raise OSError('checkpoint saved but acknowledgement lost')

        restored._save = saved_then_failed
        with self.assertRaisesRegex(OSError, 'acknowledgement lost'):
            restored.recover_confirmed(attempt)
        before = self.checkpoint.read_bytes()
        self.assertFalse(self.session().recover_confirmed(attempt))
        self.assertEqual(self.checkpoint.read_bytes(), before)
        self.assertEqual(self.calls, [])

    def test_corrupt_existing_record_is_not_silently_overwritten(self):
        attempt = self.confirmed_gap()
        container = json.loads(self.checkpoint.read_text())
        container['records']['send'] = {'status': 'failed', 'error': 'other work'}
        self.checkpoint.write_text(_host.canonical(container) + '\n')
        before = self.checkpoint.read_bytes()
        with self.assertRaisesRegex(ValueError, 'conflicting checkpoint'):
            self.session().recover_confirmed(attempt)
        self.assertEqual(self.checkpoint.read_bytes(), before)

    def test_rehashed_malformed_confirmations_are_refused(self):
        cases = {
            'bad_output_digest': lambda es: es[-1].update(output_digest='0' * 64),
            'missing_output': lambda es: es[-1].pop('output_json'),
            'nontext_output': lambda es: es[-1].update(output_json={'x': 1}),
            'noncanonical_output': lambda es: es[-1].update(
                output_json='{ "accepted_input": 1 }',
                output_digest=_host.digest('{ "accepted_input": 1 }')),
            'duplicate_keys': lambda es: es[-1].update(
                output_json='{"x":1,"x":2}',
                output_digest=_host.digest('{"x":1,"x":2}')),
            'bad_signature': lambda es: es[0].update(signature='0' * 64),
            'task_binding': lambda es: es[0].update(task='different'),
            'dependency_name': lambda es: es[0]['dependency_digests'][0].__setitem__(0, 'wrong'),
            'dependency_digest': lambda es: es[0]['dependency_digests'][0].__setitem__(1, 'bad'),
            'missing_dependency': lambda es: es[0].update(dependency_digests=[]),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                # Each subcase has a fresh journal and checkpoint.
                for path in Path(self.directory.name).iterdir():
                    path.unlink()
                attempt = self.confirmed_gap()
                self.rewrite_journal(mutate)
                before = self.checkpoint.read_bytes()
                with self.assertRaisesRegex(ValueError, 'malformed confirmed'):
                    self.session().recover_confirmed(attempt)
                self.assertEqual(self.checkpoint.read_bytes(), before)
                self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
