"""Runtime inventory follows first-party packages in source and installed layouts."""
import os
from pathlib import Path
import shutil

import pytest

from microcosm_core import component_replay as replay


PACKAGE_NAMES = {"microcosm_core", "plectis"}


@pytest.fixture(params=["source", "installed"])
def installation(tmp_path, monkeypatch, request):
    if request.param == "source":
        data = tmp_path / "checkout"
        code = data / "src"
    else:
        data = tmp_path / "environment/share/plectis"
        code = tmp_path / "environment/lib/python3.13/site-packages"
    (data / "core").mkdir(parents=True)
    (data / "standards").mkdir()
    (data / "core/organ_registry.json").write_text('{"implemented_organs": []}')
    (data / "standards/policy.json").write_text('{"public": true}')
    for name in PACKAGE_NAMES:
        package = code / name
        package.mkdir(parents=True)
        (package / "__init__.py").write_text(f"# {name} implementation\n")
        (package / "logic.py").write_text("VALUE = 1\n")
    unrelated = code / "unrelated_dependency"
    unrelated.mkdir()
    (unrelated / "logic.py").write_text("VALUE = 'ambient dependency'\n")
    monkeypatch.setattr(replay, "CODE_ROOT", code)
    return request.param, data, code


def snapshot(data):
    # Inventory observation needs no runner execution or receipt creation.
    return replay._source_snapshot(data, (), [], ())


def test_source_and_installed_inventory_name_only_first_party_packages(installation):
    layout, data, code = installation
    observed = snapshot(data)
    packages = {name: replay.input_tree_hash(code / name) for name in PACKAGE_NAMES}
    assert observed["source_inventory_scheme"] == "package_roots_v1"
    assert observed["runtime_package_tree_sha256"] == packages
    assert set(observed["runtime_package_tree_sha256"]) == PACKAGE_NAMES
    assert observed["runtime_package_digest_scheme"] == "tree_type_path_bytes_posix_mode_v2"
    assert observed["runtime_source_scope"] == ["microcosm_core/**", "plectis/**"]
    assert observed["runtime_source_tree_sha256"] == replay._json_digest(packages)
    if layout == "source":
        # The separately declared clone src retains its whole-tree guard.
        assert observed["declared_source_tree_sha256"] == replay.input_tree_hash(code)
        assert observed["declared_source_tree_sha256"] != observed["runtime_source_tree_sha256"]
    else:
        assert observed["declared_source_tree_sha256"] is None


def test_ambient_sibling_mutation_does_not_invalidate_runtime_inventory(installation):
    layout, data, code = installation
    before = snapshot(data)
    sibling = code / "unrelated_dependency/logic.py"
    sibling.write_text("VALUE = 'changed ambient dependency'\n")
    sibling.chmod(sibling.stat().st_mode | 0o100)
    after = snapshot(data)
    assert before["runtime_package_tree_sha256"] == after["runtime_package_tree_sha256"]
    assert before["runtime_source_tree_sha256"] == after["runtime_source_tree_sha256"]
    if layout == "installed":
        assert before == after
    else:
        # A clone's explicitly declared source is a separate retained boundary;
        # it must not be mislabeled as the runtime package aggregate.
        assert before["declared_source_tree_sha256"] != after["declared_source_tree_sha256"]


@pytest.mark.parametrize("package", sorted(PACKAGE_NAMES))
def test_either_first_party_package_mutation_invalidates_inventory_without_mtime_change(installation, package):
    _, data, code = installation
    before = snapshot(data)
    source = code / package / "logic.py"
    old = source.stat()
    source.write_text("VALUE = 2\n")
    os.utime(source, ns=(old.st_atime_ns, old.st_mtime_ns))
    after = snapshot(data)
    assert before["runtime_package_tree_sha256"][package] != after["runtime_package_tree_sha256"][package]
    assert before["runtime_source_tree_sha256"] != after["runtime_source_tree_sha256"]
    other = next(name for name in PACKAGE_NAMES if name != package)
    assert before["runtime_package_tree_sha256"][other] == after["runtime_package_tree_sha256"][other]


@pytest.mark.parametrize("link_kind", ["package_outside", "package_inside", "file_outside", "directory_outside"])
def test_package_links_and_escapes_are_rejected(installation, tmp_path, link_kind):
    _, _, code = installation
    outside = tmp_path / "foreign-code"
    outside.mkdir()
    (outside / "foreign.py").write_text("UNREVIEWED = True\n")
    package = code / "microcosm_core"
    if link_kind.startswith("package_"):
        shutil.rmtree(package)
        target = outside
        if link_kind == "package_inside":
            target = code / "alternate-package"
            target.mkdir()
            (target / "__init__.py").write_text("# alternate bytes\n")
        package.symlink_to(target, target_is_directory=True)
    elif link_kind == "file_outside":
        (package / "escape.py").symlink_to(outside / "foreign.py")
    else:
        (package / "escaped").symlink_to(outside, target_is_directory=True)
    with pytest.raises(replay.UnsupportedInputSymlink):
        replay._runtime_source_inventory()


def test_missing_first_party_package_has_no_ambient_tree_fallback(installation):
    _, _, code = installation
    shutil.rmtree(code / "plectis")
    with pytest.raises((ValueError, FileNotFoundError)):
        replay._runtime_source_inventory()
