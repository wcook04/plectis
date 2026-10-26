# SPDX-License-Identifier: Apache-2.0
"""Load reviewed generated source bytes through a private import tree.

Adapted from the round-two p09 loading repair. This is tested host code, not
a verified compiler or a defence against control of Python, this loader, the
executing OS account or its private temporary directory.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile


# These pins and inventories belong to the reviewed loader release. Updating
# a generated kernel requires reviewing both, alongside its formal metadata.
MANIFEST_SHA256 = {
    "ReplayAdmission": "5dd5df3801369bb3cd65b9872bf7ee82979e5c10fa02c608402c14a20a45f63e",
    "WalkthroughValidation": "3f17d81e02688f99c0bbe1cf5895651fabf7a12d629eaefecd6f28cf8db11875",
    "McpAuthority": "9916da38ad82ad4e0fd8cf5fe34e1a1e1d05865ee8df4020362c8ad46a56e2d5",
    "InformationFlow": "056e1aaaace23ffbd90e548d9148602cc142fce268a0eebd2d434530776a8362",
    "TacticSelection": "62eb0ef436a55ca6e389651c23671fa60fdeec9b2a6dda64f1e7f7283b6d0550",
    "BudgetPacking": "d0c7fadba9df3bd488931a04758bc36ccfb12579270cca98be41ca1746947f81",
    "NavigationMetrics": "f1f0cff7becd61d38d9d4ce158775b39ee7a90bc09e204f04131e853d094ecd0",
    "EgressPolicy": "dda40ab4912d5a5bbc164db5a66bb2fbfe9625916001f2f74568d5e463e0bdff",
    "PremiseRanking": "f6baea5fa063782a1ae76046b41e7f0bd57f81e055c6ad41865764e1e0e7f3e1",
    "DependencyReachability": "8a5242c6ead4e49a13e92877c9de7ac81d4a4467798278d12d692ac6781bae77",
    "OwnershipClassification": "a3d86b84ec112c5f81386837c600efc89c93f518c39edfe66439ea3362c7a235",
    "EvidenceDiff": "27826ace402ef7917a52083ce59ea955b24b493b981123f6db3a80b348a22fcc",
    "SandboxPolicy": "78c9c9907f05d70f55628398e1c123e2de6560f2fa1fce4024e87f99bdeecd3c",
    "Repair": "0326579506855699890187cc2d1bbd16033852078adb74e59c723063cb3e079f",
    "Compatibility": "20d97d3b10cb23e52f41e71c63a15a5a9d135c1c6e4622e1c56a5ea29259c473",
    "Release": "0db832da07984ff777a3c113be472b05135ab8ee18818e19e6addaa1a0ec6b0b",
}
SUPPORT_FILES = frozenset({"module_.py", "__main__.py", "System_/__init__.py",
                           "_dafny/__init__.py"})
KERNEL_SOURCE_FILES = {
    "ReplayAdmission": SUPPORT_FILES | {"ReplayAdmission.py"},
    "WalkthroughValidation": SUPPORT_FILES | {"WalkthroughValidation.py"},
    "McpAuthority": SUPPORT_FILES | {"McpAuthority.py"},
    "InformationFlow": SUPPORT_FILES | {"InformationFlow.py"},
    "TacticSelection": SUPPORT_FILES | {"TacticSelection.py"},
    "BudgetPacking": SUPPORT_FILES | {"BudgetPacking.py"},
    "NavigationMetrics": SUPPORT_FILES | {"NavigationMetrics.py"},
    "EgressPolicy": SUPPORT_FILES | {"EgressPolicy.py"},
    "PremiseRanking": SUPPORT_FILES | {"PremiseRanking.py"},
    "DependencyReachability": SUPPORT_FILES | {"DependencyReachability.py"},
    "OwnershipClassification": SUPPORT_FILES | {"OwnershipClassification.py"},
    "EvidenceDiff": SUPPORT_FILES | {"EvidenceDiff.py"},
    "SandboxPolicy": SUPPORT_FILES | {"SandboxPolicy.py"},
    "Repair": SUPPORT_FILES | {"Repair.py"},
    "Compatibility": SUPPORT_FILES | {"Compatibility.py", "Replay.py"},
    "Release": SUPPORT_FILES | {"Release.py"},
}
NONEXECUTED_FILES = frozenset({"__init__.py", "GENERATED_SHA256.json",
                              "Dafny-LICENSE.txt"})


def read_kernel_snapshot(generated, name):
    """Return validated source bytes; never execute from the original tree.

    Unexpected files and directories, including sourceless packages, are
    refused. Installation-created __pycache__ directories may contain regular
    .pyc files, but these bytes are never copied or imported. Symlinks are
    refused as an inventory rule; hostile concurrent filesystem mutation is
    outside this cooperative local-host boundary.
    """
    generated = Path(generated)
    if name not in MANIFEST_SHA256 or name not in KERNEL_SOURCE_FILES:
        raise ValueError("unrecognised kernel")
    if not stat.S_ISDIR(generated.lstat().st_mode):
        raise ValueError("generated kernel must be a real directory")
    expected = KERNEL_SOURCE_FILES[name]
    allowed_files = expected | NONEXECUTED_FILES
    allowed_directories = {str(Path(path).parent) for path in expected
                           if Path(path).parent != Path(".")}
    found = set()

    def visit(directory, prefix="", cache=False):
        with os.scandir(directory) as entries:
            for entry in entries:
                relative = prefix + entry.name
                kind = entry.stat(follow_symlinks=False).st_mode
                if stat.S_ISLNK(kind):
                    raise ValueError("symlink in generated kernel: " + relative)
                if stat.S_ISDIR(kind):
                    if not cache and (relative in allowed_directories
                                      or entry.name == "__pycache__"):
                        visit(entry.path, relative + "/", entry.name == "__pycache__")
                    else:
                        raise ValueError("unexpected generated directory: " + relative)
                elif stat.S_ISREG(kind):
                    if cache and entry.name.endswith(".pyc"):
                        continue
                    if cache or relative not in allowed_files:
                        raise ValueError("unexpected generated file: " + relative)
                    found.add(relative)
                else:
                    raise ValueError("nonregular generated entry: " + relative)

    visit(generated)
    if found != allowed_files:
        raise ValueError("incomplete generated kernel inventory")
    manifest_bytes = (generated / "GENERATED_SHA256.json").read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != MANIFEST_SHA256[name]:
        raise ValueError("generated manifest differs from reviewed loader pin")
    manifest = json.loads(manifest_bytes)
    if set(manifest) != expected:
        raise ValueError("unexpected generated manifest entries")
    snapshot = {}
    for relative in sorted(expected):
        data = (generated / relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != manifest[relative]:
            raise ValueError("generated source differs from reviewed bytes: " + relative)
        snapshot[relative] = data
    return snapshot


@contextmanager
def sealed_kernel(generated, name):
    """Import only a private copy of the exact source bytes validated above.

    Later changes to the original source cannot select different imported
    bytes. Python, the import machinery and the private directory are trusted.
    Use in a short-lived isolated worker, not for concurrent in-process loads.
    """
    module_names = {Path(path).parts[0].removesuffix(".py")
                    for paths in KERNEL_SOURCE_FILES.values() for path in paths
                    if path != "__main__.py"}
    if module_names.intersection(sys.modules):
        raise ValueError("generated modules already present in worker")
    snapshot = read_kernel_snapshot(generated, name)
    with tempfile.TemporaryDirectory(prefix="plectis-kernel-") as directory:
        private = Path(directory)
        for relative, data in snapshot.items():
            target = private / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        sys.path.insert(0, str(private))
        try:
            yield
        finally:
            sys.path.remove(str(private))
            for module in module_names:
                sys.modules.pop(module, None)
