#!/usr/bin/env python3
"""Check explicit repository roles against Git's worktree or staged candidates.

Portable standard-library asset. Run from the repository root; policies belong
in docs/repository_layout.json. No ignored-tree traversal or Git configuration edits.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path, PurePosixPath
import subprocess


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          capture_output=True).stdout


def candidates(root: Path, index: bool) -> set[str]:
    if Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != root.resolve():
        raise ValueError('root must be the Git repository root')
    args = ['ls-files', '-z', '--cached']
    if not index:
        args += ['--others', '--exclude-standard']
    paths = {p.decode('utf-8', 'surrogateescape') for p in git(root, *args).split(b'\0') if p}
    return paths if index else {p for p in paths if (root / p).is_file() or (root / p).is_symlink()}


def read(root: Path, path: str, index: bool) -> str:
    return git(root, 'show', ':' + path).decode() if index else (root / path).read_text(encoding='utf-8')


def validate_policy(policy: dict) -> None:
    if policy.get('schema') != 'repository_layout@1':
        raise ValueError('unsupported or missing repository layout schema')
    for key in ('root_files', 'directories', 'required_files', 'content_routes'):
        if not policy.get(key):
            raise ValueError('missing policy field: ' + key)
    for name, role in policy['directories'].items():
        if '/' in name or not role.get('purpose'):
            raise ValueError('each top-level directory needs a name and purpose')
    if any(not value for value in policy.get('exceptions', {}).values()):
        raise ValueError('each placement exception needs a reason')


def check(root: Path, *, index: bool = False, config: str = 'docs/repository_layout.json') -> list[str]:
    paths = candidates(root, index)
    if config not in paths:
        raise ValueError('layout policy is missing from the selected Git view: ' + config)
    policy = json.loads(read(root, config, index))
    validate_policy(policy)
    errors = []
    exceptions = policy.get('exceptions', {})
    for path in sorted(paths):
        parts = PurePosixPath(path).parts
        if len(parts) == 1:
            if path not in policy['root_files']:
                errors.append(path + ': no root interface registered; choose an existing owner directory')
            continue
        role = policy['directories'].get(parts[0])
        if not role:
            errors.append(path + ': no directory role registered')
            continue
        if path in exceptions:
            continue
        suffixes = role.get('suffixes')
        if suffixes is not None and PurePosixPath(path).suffix not in suffixes and PurePosixPath(path).name not in role.get('filenames', []):
            errors.append(path + ': incompatible with ' + role['purpose'])
    for path in policy['required_files']:
        if path not in paths:
            errors.append('missing owner or interface: ' + path)
    for path, fragments in policy['content_routes'].items():
        if path not in paths:
            errors.append('missing route carrier: ' + path)
            continue
        content = read(root, path, index)
        for fragment in fragments:
            if fragment not in content:
                errors.append(path + ': stale route; missing ' + repr(fragment))
    return errors


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--config', default='docs/repository_layout.json')
    p.add_argument('--index', action='store_true', help='Inspect staged paths, policy and route contents.')
    a = p.parse_args()
    try:
        errors = check(a.root.resolve(), index=a.index, config=a.config)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        p.exit(2, f'Layout check could not run: {exc}\n')
    print(json.dumps({'ok': not errors, 'view': 'index' if a.index else 'worktree', 'errors': errors}, indent=2))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
