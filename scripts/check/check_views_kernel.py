#!/usr/bin/env python3
"""Check retained bytes; optionally replay proofs, regeneration and negative controls.

Hash checking alone is not formal verification. Full replay requires the pinned
Dafny 4.11.0 distribution; this script downloads nothing and performs no setup.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / "formal" / "views"
VERSION = '4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2'
GENERATED = {'Release.py', 'module_.py', '__main__.py', 'System_/__init__.py', '_dafny/__init__.py'}
SOURCES = {'Release.dfy', 'negative/IgnoreControl.dfy', 'negative/RetainPrivateRead.dfy'}
PROOF = runpy.run_path(str(PROJECT / 'scripts/check/check_component_kernels.py'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def _source_snapshot(metadata):
    require(set(metadata['sources']) == SOURCES, 'unexpected formal source inventory')
    snapshot = {}
    for relative, expected in metadata['sources'].items():
        source = PROOF['_source_text'](ROOT / relative).encode('utf-8')
        require(hashlib.sha256(source).hexdigest() == expected,
                'source identity mismatch: ' + relative)
        snapshot[relative] = source
    return snapshot

def bindings(generated):
    loader = runpy.run_path(str(PROJECT / 'src/plectis/_sealed_kernel.py'))
    loader['read_kernel_snapshot'](generated, 'Release')
    metadata = PROOF['_read_json'](ROOT / 'metadata.json')
    require(type(metadata['schema_version']) is int and metadata['schema_version'] == 1,
            'unexpected metadata schema')
    require(metadata['dafny_version'] == VERSION, 'unexpected Dafny version')
    require(metadata['verified_tasks'] == 30, 'unexpected verification count')
    require(type(metadata['errors']) is int and metadata['errors'] == 0,
            'unexpected clean error count')
    require(set(metadata['generated_python']) == GENERATED, 'unexpected generated manifest')
    require(metadata['generated_python'] == PROOF['_read_json'](generated / 'GENERATED_SHA256.json'),
            'generated manifest differs from proof metadata')
    require(metadata['negative_controls'] == {
        name: {'verified_tasks': 29, 'errors': 1, 'exit_code': 4}
        for name in ('IgnoreControl', 'RetainPrivateRead')}, 'unexpected negative proof results')
    sources = _source_snapshot(metadata)
    source = sources['Release.dfy'].decode('utf-8')
    for relative, expected in metadata['generated_python'].items():
        require(digest(generated / relative) == expected, 'generated identity mismatch: ' + relative)
    expected_control = source.replace('(!isPublic || (!pc && !Sensitive(e, high)))',
                                      '(!isPublic || !Sensitive(e, high))', 1)
    expected_read = source.replace('if Sensitive(e, high) then Skip\n      else Branch',
                                   'if Sensitive(e, high) then Branch(e, Skip, Skip)\n      else Branch', 1)
    require(source.count('(!isPublic || (!pc && !Sensitive(e, high)))') == 1
            and expected_control == sources['negative/IgnoreControl.dfy'].decode('utf-8'),
            'control mutant changed beyond declared guard mutation')
    require(source.count('if Sensitive(e, high) then Skip\n      else Branch') == 1
            and expected_read == sources['negative/RetainPrivateRead.dfy'].decode('utf-8'),
            'private-read mutant changed beyond declared slice mutation')
    return metadata

def command(argv, cwd, logs, filename):
    environment = os.environ.copy()
    environment.setdefault('DOTNET_GCHeapHardLimit', '0x40000000')
    environment.setdefault('DOTNET_GCConserveMemory', '9')
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    try:
        result = subprocess.run(argv, cwd=cwd, env=environment, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=180, check=False)
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ''
        if isinstance(output, bytes):
            output = output.decode('utf-8', errors='replace')
        (logs / filename).write_text(output)
        raise ValueError('Dafny process timed out before complete proof diagnostic') from error
    (logs / filename).write_text(result.stdout)
    return result

def replay(executable, generated, logs, *, expected_metadata=None):
    metadata = bindings(generated)
    require(expected_metadata is None or expected_metadata == metadata,
            'views binding changed before proof snapshot')
    sources = _source_snapshot(metadata)
    found = shutil.which(executable)
    require(found is not None, 'Dafny executable not found')
    dafny = str(Path(found).resolve())
    version = command([dafny, '--version'], ROOT, logs, 'version.log')
    require(version.returncode == 0 and version.stdout.strip() == VERSION, 'pinned Dafny version required')
    with tempfile.TemporaryDirectory(prefix='release-proof-') as temporary:
        directory = Path(temporary)
        for relative, source in sources.items():
            target = directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source)
        build = command([dafny, 'build', '--target:py', 'Release.dfy',
                         '--verification-time-limit', '30', '--cores', '1'], directory, logs, 'build.log')
        PROOF['_proof_result'](build, 30, 0)
        rebuilt = directory / 'Release-py'
        require({p.relative_to(rebuilt).as_posix() for p in rebuilt.rglob('*.py')} == GENERATED,
                'unexpected generated Python file set')
        for relative in GENERATED:
            require((rebuilt / relative).read_bytes() == (generated / relative).read_bytes(),
                    'regenerated Python differs: ' + relative)
        negative = []
        for name in ('IgnoreControl', 'RetainPrivateRead'):
            result = command([dafny, 'verify', str(directory / 'negative' / (name + '.dfy')),
                              '--verification-time-limit', '30', '--cores', '1'], directory, logs, name + '.log')
            PROOF['_proof_result'](result, 29, 1, negative=True)
            negative.append({'fixture': name, 'exit_code': result.returncode,
                             'verified_tasks': 29, 'errors': 1})
    return {'dafny_version': VERSION, 'verified_tasks': 30, 'errors': 0,
            'generated_python_byte_identical': True, 'negative_controls': negative}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', type=Path, default=PROJECT / "src" / "plectis" / "views" / "_generated")
    parser.add_argument('--dafny')
    parser.add_argument('--logs', type=Path, default=PROJECT / '.microcosm' / 'formal-views')
    args = parser.parse_args()
    try:
        metadata = bindings(args.generated.resolve())
        result = {'status': 'hash_binding_only_pass', 'mode': 'hash_binding_only',
                  'formal_source_sha256': metadata['sources']['Release.dfy'],
                  'generated_python': metadata['generated_python'],
                  'warning': 'No prover was invoked by this default mode.'}
        if args.dafny:
            args.logs.mkdir(parents=True, exist_ok=True)
            result.update(replay(args.dafny, args.generated.resolve(), args.logs.resolve(),
                                 expected_metadata=metadata))
            result.update(status='formal_replay_pass', mode='formal_replay')
            result.pop('warning')
            (args.logs / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        print(json.dumps({'status': 'failed', 'error': str(error)}, indent=2))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
