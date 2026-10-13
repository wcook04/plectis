#!/usr/bin/env python3
"""Behavior fixtures for the portable layout gate; no dependencies or source-tree writes."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from check_layout import check


class Layout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.git('init', '-q')
        self.policy = {'schema': 'repository_layout@1', 'root_files': ['README.md', '.gitignore'],
            'directories': {'docs': {'purpose': 'authored documentation', 'suffixes': ['.md', '.json']},
                            'scripts': {'purpose': 'maintenance commands', 'suffixes': ['.py']}},
            'required_files': ['README.md', 'docs/repository_layout.json'],
            'content_routes': {'README.md': ['run gate']},
            'exceptions': {'docs/historical.py': 'immutable recorded specimen'}}
        self.write('README.md', 'run gate')
        self.write('.gitignore', '/build/\n')
        self.write('docs/repository_layout.json', json.dumps(self.policy))
        self.write('docs/historical.py', 'recorded specimen')
        self.git('add', '.')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)

    def write(self, path, text=''):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def test_legitimate_roles_and_explicit_exception(self):
        self.write('scripts/new.py')
        self.assertEqual(check(self.root), [])

    def test_misplaced_command_with_spaces_and_newline(self):
        self.write('docs/bad name\ncommand.py')
        self.assertTrue(any('incompatible' in e for e in check(self.root)))

    def test_unknown_directory_and_root_file(self):
        self.write('random/tool.py')
        self.write('new.py')
        self.assertEqual(len(check(self.root)), 2)

    def test_ignored_outputs_are_not_candidates(self):
        self.write('build/unknown/deep/output.py')
        self.assertEqual(check(self.root), [])

    def test_index_addition_and_staged_contents(self):
        self.write('docs/new.py')
        self.git('add', 'docs/new.py')
        (self.root / 'docs/new.py').unlink()
        self.assertEqual(check(self.root), [])
        self.assertTrue(check(self.root, index=True))

    def test_staged_deletion_of_required_owner(self):
        self.git('rm', '-q', '-f', 'README.md')
        self.assertTrue(any('missing owner' in e for e in check(self.root, index=True)))

    def test_stale_route_checks_selected_contents(self):
        self.write('README.md', 'stale')
        self.assertTrue(check(self.root))
        self.assertEqual(check(self.root, index=True), [])
        self.git('add', 'README.md')
        self.write('README.md', 'run gate')
        self.assertTrue(check(self.root, index=True))

    def test_index_policy_does_not_read_unstaged_relaxation(self):
        self.write('docs/new.py')
        self.git('add', 'docs/new.py')
        self.policy['directories']['docs']['suffixes'].append('.py')
        self.write('docs/repository_layout.json', json.dumps(self.policy))
        self.assertEqual(check(self.root), [])
        self.assertTrue(check(self.root, index=True))

    def test_missing_policy_and_non_git_fail_clearly(self):
        with self.assertRaises(ValueError):
            check(self.root, config='docs/absent.json')
        child = self.root / 'nested'
        child.mkdir()
        with self.assertRaises(ValueError):
            check(child)
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(subprocess.CalledProcessError):
                check(Path(raw).resolve())


if __name__ == '__main__':
    unittest.main()
