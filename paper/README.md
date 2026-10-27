# Plectis prototype paper

The [paper PDF](../plectis-public-system.pdf), *Plectis: Verifying Code and Recording Its Execution*, explains selected Dafny computations, their generated Python and actual callers. Its ownership example shows how a stale first match could hide a live owner, why the requirement changed, and how the repaired contract connects to the application. The separate replay-admission core checks recorded observations rather than proving the component algorithm.

The manuscript is [plectis-public-system.tex](plectis-public-system.tex); [paper-house-style.sty](paper-house-style.sty) supplies the shared typography. This prototype paper is distinct from the system paper maintained in `wcook04/plectis-erdos`.

## Check the source bindings

From the clone root, using Python 3.11 or newer:

```sh
python3 scripts/check/check_public_system_paper.py
```

The checker compares the paper's selected counts with maintained formal metadata, checks source and generated-code bindings through the existing formal checkers, follows the paper's human-readable guide citation, validates this guide's implementation links, and confirms that the reproduction commands here still name the maintained Make targets. It also rejects code and command blocks in the article. Success prints `Public-system paper check: pass` and exits with status `0`; a mismatch prints diagnostics and exits with status `1`.

This static comparison does not rerun proofs, component replays, tests or CI. It cannot establish that the prose accurately explains a specification or that the specification meets the intended requirement. The [formal overview](../formal/README.md) and [validation runbook](../docs/maintainers/validation.md) describe those separate checks. No historical Git commit or archived test receipt is required by the paper check.

## Build and review the PDF

Install [Tectonic](https://tectonic-typesetting.github.io/book/latest/getting-started/install.html) and confirm `tectonic --help` runs. A first build may download TeX support files into Tectonic's cache. From the clone root:

```sh
mkdir -p /tmp/plectis-paper
tectonic --outdir /tmp/plectis-paper paper/plectis-public-system.tex
```

Inspect every page of `/tmp/plectis-paper/plectis-public-system.pdf`, including the figure, source links and bibliography. The editorial target is four to six pages at the shared style's normal text size. After review, an authorized publication update replaces the stable root PDF:

```sh
cp /tmp/plectis-paper/plectis-public-system.pdf plectis-public-system.pdf
```

The root PDF is the public copy. Do not add a second PDF under `paper/`. Changes to the manuscript also require the existing paper-corpus refresh and checks, and the repository's normal release validation. Return to the [README](../README.md) for runnable examples and to the [code guide](../ARCHITECTURE.md) for implementation paths.

## Inspect the worked examples

The paper explains the architecture and behavior. This guide supplies the exact implementation and test objects:

| Object | Source and checks |
|---|---|
| Ownership requirement and computation | [Dafny source](../formal/components/ownership_classification/OwnershipClassification.dfy) |
| Ownership normalization and application caller | [Concurrency component](../src/microcosm_core/organs/concurrency_mission_control.py) |
| Same-file, cross-file and conflicting-owner cases | [Ownership tests](../tests/test_component_ownership_classification.py) |
| Evidence comparison computation | [Dafny source](../formal/components/evidence_diff/EvidenceDiff.dfy) |
| Evidence normalization | [Python adapter](../src/plectis/components/evidence_diff/_adapter.py) |
| Duplicate-ID and actual-caller cases | [Evidence-comparison tests](../tests/test_component_evidence_diff.py) |
| Replay-admission contract | [Dafny source](../formal/replay/ReplayAdmission.dfy) |
| Capture and receipt observations | [Shared replay host](../src/microcosm_core/component_replay.py) |
| Formal inventory and trust limits | [Component computations](../formal/components/README.md) and [workflow cores](../formal/README.md) |

The ownership postcondition in the maintained source requires any matching live claim on a generated path to yield classification `2` and action `11`. The host maps these to `owned_live` and `do_not_patch_from_sibling_lane`. Read the whole input model and priority contract alongside that implication; it concerns supplied normalized observations, not authenticated locks or live sessions.

## Reproduce the formal checks and execution

Install the pinned Dafny 4.11.0 distribution named by the formal guides. From the clone root, replacing the executable path with your installation:

```sh
make verify-components DAFNY=/absolute/path/to/dafny
make verify-operations DAFNY=/absolute/path/to/dafny
```

These commands invoke the maintained formal checkers, rerun native proofs, regenerate deployed Python, compare its bytes and require selected source mutants to fail. They do not replace requirements review or application tests.

To attempt fresh component execution with each route's declared native prerequisites:

```sh
make component-replays
```

Follow the [validation runbook](../docs/maintainers/validation.md) for application tests, native prerequisites, package checks and release validation. The paper's summary counts are bound to retained metadata; a current hash-only comparison is not evidence that these commands or CI have just run.
