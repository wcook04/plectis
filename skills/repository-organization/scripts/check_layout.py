#!/usr/bin/env python3
"""Validate project-declared roles against Git worktree or staged candidates."""
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


def relative_path(value: object) -> bool:
    return (isinstance(value, str) and bool(value) and '\\' not in value
            and ':' not in value and not any(ord(c) < 32 for c in value)
            and not value.startswith('/') and all(p not in ('', '.', '..') for p in value.split('/')))


def validate_policy(policy: dict) -> None:
    if not isinstance(policy, dict) or policy.get('schema') not in ('repository_layout@1', 'repository_layout@2'):
        raise ValueError('unsupported or missing repository layout schema')
    for key, kind in (('root_files', list), ('directories', dict), ('required_files', list), ('content_routes', dict)):
        if not isinstance(policy.get(key), kind):
            raise ValueError('missing or invalid policy field: ' + key)
    if policy.get('undeclared_directories', 'error') not in ('warn', 'error'):
        raise ValueError('undeclared_directories must be warn or error')
    for key in ('root_files', 'required_files'):
        if any(not relative_path(p) for p in policy[key]):
            raise ValueError(key + ' must contain repository-relative paths')
    if any('/' in p for p in policy['root_files']):
        raise ValueError('root_files must name root interfaces')
    for name, role in policy['directories'].items():
        if (not relative_path(name) or not isinstance(role, dict)
                or not isinstance(role.get('purpose'), str) or not role['purpose'].strip()):
            raise ValueError('each directory needs a relative path and nonempty purpose')
        if '/' in name and policy['schema'] == 'repository_layout@1':
            raise ValueError('nested directory declarations require repository_layout@2')
        for key in ('suffixes', 'filenames'):
            if key in role and (not isinstance(role[key], list) or any(not isinstance(v, str) for v in role[key])):
                raise ValueError(name + ': ' + key + ' must be a list of strings')
        if 'guide' in role and not relative_path(role['guide']):
            raise ValueError(name + ': guide must be a repository-relative file')
    exceptions = policy.get('exceptions', {})
    if not isinstance(exceptions, dict) or any(not relative_path(p) or not isinstance(v, str) or not v.strip() for p, v in exceptions.items()):
        raise ValueError('each exact placement exception needs a path and reason')
    for path, fragments in policy['content_routes'].items():
        if not relative_path(path) or not isinstance(fragments, list) or any(not isinstance(f, str) or not f for f in fragments):
            raise ValueError('content_routes must map relative files to nonempty string lists')


def inspect(root: Path, *, index: bool = False, config: str = 'docs/repository_layout.json') -> dict:
    if not relative_path(config):
        raise ValueError('config must be a repository-relative file')
    paths = candidates(root, index)
    if config not in paths:
        raise ValueError('layout policy is missing from the selected Git view: ' + config)
    policy = json.loads(read(root, config, index))
    validate_policy(policy)
    errors, warnings = [], []
    exceptions = policy.get('exceptions', {})
    roles = policy['directories']
    unknown = set()
    for path in sorted(paths):
        parts = PurePosixPath(path).parts
        if len(parts) == 1:
            if path not in policy['root_files']:
                errors.append(path + ': no root interface registered in ' + config)
            continue
        applicable = [(name, role) for name, role in roles.items() if path.startswith(name + '/')]
        if not applicable:
            unknown.add(parts[0])
            continue
        if path in exceptions:
            continue
        # A more specific purpose never silently removes an ancestor constraint.
        for name, role in applicable:
            suffixes = role.get('suffixes')
            if suffixes is not None and PurePosixPath(path).suffix not in suffixes and PurePosixPath(path).name not in role.get('filenames', []):
                errors.append(path + ': incompatible with ' + name + ' (' + role['purpose'] + ')')
    messages = warnings if policy.get('undeclared_directories', 'error') == 'warn' else errors
    for name in sorted(unknown):
        messages.append(name + '/: purpose not declared; add a project-specific role in ' + config
                        + '; see skills/repository-organization/SKILL.md (no approval required for ordinary folder additions)')
    for path in policy['required_files']:
        if path not in paths:
            errors.append('missing owner or interface: ' + path)
    for name, role in roles.items():
        if role.get('guide') and role['guide'] not in paths:
            errors.append(name + ': missing owner guide: ' + role['guide'])
    for path, fragments in policy['content_routes'].items():
        if path not in paths:
            errors.append('missing route carrier: ' + path)
            continue
        content = read(root, path, index)
        for fragment in fragments:
            if fragment not in content:
                errors.append(path + ': stale route; missing ' + repr(fragment))
    return {'ok': not errors, 'view': 'index' if index else 'worktree', 'policy': config,
            'errors': errors, 'warnings': warnings}


def check(root: Path, *, index: bool = False, config: str = 'docs/repository_layout.json') -> list[str]:
    """Compatibility API: hard errors only. Use inspect for discovery warnings too."""
    return inspect(root, index=index, config=config)['errors']


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--config', default='docs/repository_layout.json')
    p.add_argument('--index', action='store_true', help='Inspect staged paths, policy and route contents.')
    a = p.parse_args()
    try:
        result = inspect(a.root.resolve(), index=a.index, config=a.config)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        p.exit(2, f'Layout check could not run: {exc}\n')
    print(json.dumps(result, indent=2))
    return int(not result['ok'])


if __name__ == '__main__':
    raise SystemExit(main())
