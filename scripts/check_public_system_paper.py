#!/usr/bin/env python3
"""Check that the public-system paper stays coupled to its live evidence."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper/plectis-public-system.tex"
REGISTRY = ROOT / "core/organ_registry.json"
FAMILIES = ROOT / "core/organ_families.json"
PUBLIC_TEST_RECEIPT = ROOT / "paper/public-test-receipt.json"

MACRO_RE = re.compile(
    r"\\newcommand\{\\(?P<name>[A-Za-z]+)\}\{(?P<value>[^}]*)\}"
)

FAMILY_MACROS = {
    "entry_and_reveal": "entrycount",
    "architecture_and_navigation": "mappingcount",
    "formal_math_and_proof": "mathcount",
    "agent_reliability_and_safety": "safetycount",
    "research_and_science_replays": "researchcount",
    "import_projection_and_drift": "publiccopycount",
    "work_landing_and_continuity": "recoverycount",
}

TRUTH_BUCKET_MACROS = {
    "copied_non_secret_macro_body": "copiedsourcecount",
    "source_faithful_refactor": "refactorcount",
    "real_runtime_receipt": "runtimecount",
    "real_import_validation": "validatorcount",
}

FORBIDDEN_OVERCLAIMS = (
    "without trusting anyone",
    "verify it is non-secret",
    "verifies it is non-secret",
    "cannot silently drift",
    "no amount of inspection",
    "one deep artifact",
    "only form that counts",
    "earns attention exactly",
    "shows the system's breadth",
    "shows its depth",
    "python 3.11 or newer and nothing else",
    "guarantees privacy",
    "proves the private system",
    "certifies the private system",
    "designed not to read the private repository at all",
    "so that any change to the contents changes the value",
    "every component in the collection currently sits in the first position",
    "only stage that could bear on the origin story",
    "bounded correctness claims for the evaluated cases",
    "dashed outline marks what a stranger cannot run or observe directly",
    "stronger evidence requires at least one consequential choice to leave",
    "an assertion about private software can only be believed or doubted as testimony",
)

FORBIDDEN_COLD_READER_RESIDUE = (
    "assembled from parts of a larger private system",
    "this paper contributes a worked boundary analysis",
    "no other repository's size or subject matter is evidence here",
    "this note reports no independent",
    "bounded public evidence",
    "record a bounded refusal",
    "bounded point of contact",
    "bounded correctness",
    "bounded examples",
    "bounded behaviour",
    "bounded calculation",
    "bounded cases only",
    "support bounded claims",
    r"bounded \code{make test} selection",
    "exercisability",
    "bounded, deterministic, and runnable in isolation",
    "supplies regression evidence",
    "held-out cases",
    "a second interpreter check",
    "the pinned manifest records none",
    "route the audio example with",
    "starts with the installed command",
    "replace it with",
    "translated line writes fresh",
    "machine-readable",
    "reference run",
    "freezing a version",
    "version is frozen",
    "inputs to freeze",
    "inputs were frozen",
    "empirical adequacy",
    "artefact",
    "private origin",
    "support for the claim as worded",
    "behaviour beyond selected cases",
    "self-supplied success criteria",
    "in order to",
    "fixed denominator",
    "{perturb it};",
    r"selection and\\re-expression",
    "has the anatomy of figure",
    "origin: provenance evidence",
    "standard: an independent oracle",
    "each dashed arrow needs a further premise",
    "needs a premise the observation does not contain",
    "public execution versus private provenance",
    "way worth noticing",
    "one assumption per distinction",
    "the five distinctions share one structure",
    "validator compares that output with a stored receipt",
    "where the oracle lives",
)

FORBIDDEN_BEFORE_COMPONENT_CONTRACT = (
    "validator",
    "commit",
    "registry",
    "route",
)

# The paper says that reading it requires no programming.  Expand specialist
# and institutional abbreviations before asking a cold reader to remember the
# shorthand.  Each expansion includes the first use of the abbreviation.
REQUIRED_FIRST_USE_EXPANSIONS = (
    ("AI", "artificial intelligence (AI)"),
    ("SACM", "Structured Assurance Case Metamodel (SACM)"),
    ("ACM", "Association for Computing Machinery (ACM)"),
    ("NIST", "National Institute of Standards and Technology (NIST)"),
    ("NASA", "National Aeronautics and Space Administration (NASA)"),
)

# Sentences the paper's argument stands on.  The first block defines terms a
# cold reader needs; the second block carries the evidential distinctions
# (provenance, repeatability, validator-vs-claim, selection, risk) that keep
# the paper's claims limited; the third block carries the author's-hand and
# record-aging cautions.  Removing one is a claim-strength change, so it
# fails this check.
REQUIRED_COLD_READER_ANCHORS = (
    r"A \emph{repository} is",
    r"A \emph{component} in",
    r"Its \emph{fixture} is",
    r"A \emph{receipt} is",
    r"A \emph{validator} is",
    r"A \emph{commit} is",
    "basic command-line use",
    # The paper's coined usage and its central three nouns must be explicit
    # enough that a cold reader does not import stronger ordinary meanings.
    r"I use \emph{answerable} in a deliberately local sense",
    "Calling them evidence does not establish their adequacy",
    r"\emph{Contract} means only",
    "descriptive analysis of one public repository, not a statistical study",
    "does not otherwise claim a full case-study design",
    "one item examined",
    "No subset of the components is used to estimate performance",
    "The repository therefore lets a reader test claims",
    "I report that its published material was copied or adapted",
    "The argument does not depend on that account or on the claimed origin",
    "cannot independently prove",
    "At the named commit, the repository's evidence still came from the project",
    "public repository does not prove the story",
    "refusal with a stated limit",
    "reader can supply the test oracle",
    "share a mistake",
    "repeatability under that public test",
    "internal consistency, not",
    "The count is an inventory, not a score",
    "did not find the patterns it was designed to find",
    "who makes the choice that matters for that claim",
    "Treat a pass as evidence only for the published rule",
    # Distinction: a validator's rule versus the stated claim.
    "narrower than the claim as worded",
    # Refusal boundaries: predeclared versus drawn after the fact.
    "before or after an awkward case",
    # Correlated records are not corroboration.
    "not independent witnesses",
    "repeat one witness rather than supply several",
    "four different limits on what may be concluded",
    # The shared structure of the five distinctions, stated without relying
    # on the unexplained economic shorthand "price a gap".
    "Once named, a gap can be disputed, assigned a cost to address",
    "An unnamed gap is easy to cross without noticing",
    # The central distinctions must be readable before specialist vocabulary
    # is introduced and must not compress all five inference limits into one
    # sentence.
    r"\subsection*{Public execution versus where the code came from}",
    "Five labels organise the gaps",
    r"The term \emph{provenance} means an object's origin and history",
    "Origin evidence and privacy pull in opposite directions",
    "For origin, one must assume that the public object came from the private one",
    "The observation itself supplies none of these assumptions",
    # The author's-hand cautions: arrangement can outrun assertion, and the
    # format itself tilts the picture.
    "cautious sentence by sentence",
    "tilts towards what publishes well",
    # Record aging: repairs add facts, they do not replace them.
    "does not subtract the first",
    # Local wins do not answer systemic objections.
    "successful execution of any number of selected items",
    # A confidential provenance review transfers trust, it does not remove it.
    "transfer trust rather than remove it",
    # Negative evaluations have the same standing as passes.
    "Disappointment is in scope",
    # The hand-equivalence claim is bounded: development methods and their
    # error rates are not compared.
    "compares no development methods and estimates no error rates",
    # Figure legends must not describe public prose as hidden, and the blue
    # action cue must remain readable without colour alone.
    "Across the figures, a dashed outline marks something",
    "This figure has no dashed boxes",
    r"Figures~\ref{fig:boundary} and~\ref{fig:gaps}",
    "Read the middle row from left to right",
    "italic blue row names what a stranger can do",
    "Above each evaluation, in italic blue",
    # Figure wording must stand on its own for readers who scan before they
    # meet the formal vocabulary in the prose.
    "change the input",
    r"I chose and\\adapted these",
    r"Each public component has the parts shown in Figure~\ref{fig:contract}",
    "origin: evidence about where it came from",
    "correctness: an answer derived separately",
    "meaning: a rule that tests the words",
    r"risk: checks beyond\\the listed patterns",
    "Each dashed arrow needs a further assumption",
    "Another person repeats the run",
    "Evaluator chooses the cases",
    "New inputs, answers worked out separately",
    "Outside task, ordinary alternative",
    "Confidential private-source review",
    # Assurance-case prior art is acknowledged without claiming conformance.
    "Plectis is not an implementation of that standard",
    "Plectis claims neither status",
    "comparison points, not statuses awarded here",
    "claims no new theory of assurance",
    # The cited ACM and NASA standards are represented by their actual
    # distinctions, not a vague appeal to independent review.
    "Artifacts Evaluated---Functional",
    "Results Reproduced",
    "independent verification and validation (IV\\&V)",
    "a formal software check, through three separations: technical",
    "the evaluator did not develop the system",
    "managerial (a separate organisation chooses scope, methods, and schedule)",
    "financial (an independent group controls the budget",
    "without adverse financial pressure",
    "not a universal test",
    "has undergone no IV\\&V",
    "No other outside evaluation report is cited or included",
    "I know of none; an unreported private rerun would remain invisible",
    # The paper must identify the object it examines, rather than announce a
    # generic contribution.
    "examines one author-curated software collection",
    # The five stronger-evidence evaluations are tied to this analysis, not universal.
    "I use the NASA criteria only for the paper's five gaps",
    "do not pair one-for-one with the distinctions",
    "None repairs a validator--claim mismatch",
    "Moving a relevant choice out of the author's hands can strengthen evidence",
    "it does not repair every gap",
    # Fresh cases and independent evaluations do not automatically confer truth.
    "Fresh inputs alone do not supply one",
    "The order is only for exposition",
    "evaluations are not cumulative stages",
    # Runtime and snapshot claims are scoped to what the checker actually does.
    "does not automatically discover a neighbouring private",
    "checks historical facts against the pinned commit",
)

REQUIRED_RECEIPT_FLOW_ANCHORS = (
    r"A \emph{receipt} is the saved record of a run",
    "repository supplies one from an earlier run",
    "rerunning can write another",
    r"Fresh receipt\\(saved run record)",
    r"\draw[flow] (val) -- node[flabel, right]{records} (rec);",
    r"compare fresh\\with stored",
    "validator judges it under the published pass and refusal rules",
    "writes a fresh receipt recording the run",
    "stored receipt from the earlier run is available for comparison; it does not determine the new verdict",
    "same checked values and verdict as the stored receipt",
)

REQUIRED_PRIVATE_EVIDENCE_SCOPE_ANCHORS = (
    "repository cannot by itself support my assertions about the unseen private "
    "system",
    "A component does something narrower",
    "related public claim a procedure that can fail in front of a stranger",
    "does not make the claim true or establish the published fragment's origin",
)

REQUIRED_FIRST_SECTION_ORIENTATION_ANCHORS = (
    "The paper examines one author-curated software collection",
    "The paper defines the component contract, then follows one ordinary component",
    "Five distinctions separate what a passing run shows",
    "the choices an evaluator would need to make independently of me",
)

REQUIRED_METHOD_DISCLOSURE_ANCHORS = (
    r"\paragraph{What I examined.}",
    r"read the list and plain descriptions of all \componentcount{} components",
    "counted them by project group",
    "by the kind of public evidence offered",
    "traced the worked component from input to limit",
    "reran the appendix's public commands",
    "did not compare every pass rule with its prose claim",
    "derive fresh expected answers",
    "reserves those checks for an outside evaluator",
)

REQUIRED_PLAIN_LANGUAGE_ORIENTATION_ANCHORS = (
    "What public evidence can and cannot show about a private system",
    # The abstract and method paragraph must state the sampling boundary
    # without requiring the reader to import statistical vocabulary.
    "whether the published selection resembles the private whole",
    "The answer is narrow",
    "lets a reader inspect and rerun its published procedures",
    "registered components (separately testable parts)",
    "whether the pass rule tests the claim as written",
    "how the code behaves on untested inputs",
    "my claim that the published material came from the private system",
    "whether the project's own pass rules are correct or even test the stated claims",
    "draw a sample and report failure rates against a fixed total",
    "I borrow only those two terms",
    "the named repository version is the single case",
    "The idea does not depend on software",
    "lets a stranger challenge, and which conclusions still lie beyond it",
    # Late-paper testing terms are written out as operations rather than
    # relying on insider shorthand.
    "gives the same output from the same input",
    "new cases whose answers were not used to design the repair",
    "Ask the repository to find the audio example",
    "saved import record reports none",
    r"\paragraph{A second Python version.}",
    "Apple silicon (arm64)",
    "Association for Computing Machinery (ACM) calls digital research materials",
    "completeness, ability to run, and evidence of verification and validation",
    "saved record of a run",
    "component list read by the programs",
    "Saving the version before an outside evaluation begins",
    "after the version is saved",
    "Evidence about a real-world outcome, where one exists",
    "inputs to include",
    "inputs went into the fixtures",
)

REQUIRED_EXAMPLE_BRIDGE_ANCHORS = (
    "The calculator check derives one expected number without the implementation",
    "project-supplied formula",
    "not that the formula is the right audio rule",
    "Its correctness evidence is limited to that calculation",
    "The next section treats these five gaps separately",
)

REQUIRED_EXPECTED_REFUSAL_EXPLANATION_ANCHORS = (
    r"Here \emph{pass} means ``refused as expected''",
    r"\code{pcm24} was not accepted",
)

REQUIRED_WORKED_EXAMPLE_COMMAND_ANCHORS = (
    "PYTHONPATH=src python3 -m plectis",
    "batch8-audio-level-rms-port run",
    r"--input fixtures/first_wave/batch8_audio_level_rms_port/input",
    r"--out /tmp/plectis-audio-rms",
    r"--acceptance-out /tmp/plectis-audio-rms-acceptance.json",
)

REQUIRED_ARITHMETIC_ORACLE_BOUNDARY_ANCHORS = (
    "but not of the project's formula",
    "only after accepting the project's formula",
    "not proof that the formula is right",
    "it does not validate the formula",
)

REQUIRED_TEST_ORACLE_EXPLANATION_ANCHORS = (
    r"a \emph{test oracle}",
    "procedure used to distinguish correct from incorrect behaviour",
    "challenge of making that distinction is called the test oracle problem",
    r"\cite[p.~507]{barr2015}",
    "conceptual ground-truth oracle that always gives the right answer",
    r"\cite[Defs.~2.4 and 2.6--2.8, pp.~509--510]{barr2015}",
    "reader can supply the test oracle",
    "expected number derived independently of the program's output",
    r"\textbf{Who or what supplies the expected answer}",
)

REQUIRED_EARLY_DISTINCTION_MAP_ANCHORS = (
    "Five labels organise the gaps",
    r"\emph{origin}, where the material came from",
    r"\emph{correctness}, whether an answer is right",
    r"\emph{meaning}, whether a rule tests its claim",
    r"\emph{reach}, whether shown cases stand for unshown ones",
    r"\emph{risk}, what the declared checks may miss",
)

REQUIRED_FIRST_REVIEW_ANCHORS = (
    "Use the appendix's no-install block",
    "select the version analysed here",
    "tour describes the checkout but does not choose a component claim",
    r"\Verb|PYTHONPATH=src python3 -m plectis comprehend --first-action",
    r'--first-action "audio level calculation" --format text',
    "do not run its first suggested command",
    "writes to the repository's saved receipt paths",
    "Run the paper's exact no-install command near the start of",
    r"it writes only to \code{/tmp}",
    "leaves the checkout unchanged",
    r"\component{/tmp/plectis-audio-rms/}",
    r"\component{batch8_audio_level_rms_port_result.json}",
    "JSON is a plain-text field-and-value format",
    r"Open \code{exercise}",
    r"\component{reference_cases}",
    r"\code{expected\_level}",
    r"\code{observed\_level}",
    "top-level",
    r"\component{anti_claim}",
    r"\component{claim_ceiling}",
    r"inside \code{exercise}",
    "The project wrote both cautions; no independent reviewer checked their limits",
    "challenge rather than repeat the supplied case",
    "make a disposable copy of the fixture input",
    "cp -R fixtures/first_wave/batch8_audio_level_rms_port/input/.",
    "/tmp/plectis-audio-rms-input",
    r"\component{batch8_audio_level_rms_port_probe_manifest.json}",
    r"second sample from \code{0.05} to \code{0.06}",
    r"leave \code{expected\_level} unchanged",
    "PYTHONPATH=src python3 -m plectis batch8-audio-level-rms-port run",
    "--input /tmp/plectis-audio-rms-input",
    "--out /tmp/plectis-audio-rms-probe",
    "--acceptance-out /tmp/plectis-audio-rms-check.json",
    "echo $?",
    r"final number printed should be \code{1}",
    "in the acceptance file",
    r"\code{status} should be \code{blocked}",
    r"\code{accepted} should be \code{false}",
    "validator caught the deliberate mismatch; the exercise did not crash",
)

REQUIRED_OUTSIDE_EVALUATION_BOUNDARY_ANCHORS = (
    "No other outside evaluation report is cited or included",
    "I know of none; an unreported private rerun would remain invisible",
    "repository's evidence still came from the project",
    "It includes no outside evaluator's report",
    "although a private rerun could be unreported",
    "the repository records none, and I know of none",
)

REQUIRED_PROVENANCE_HASH_ANCHORS = (
    "SHA-256 message digest, used here as a fingerprint: a 256-bit value calculated",
    "used to detect change",
    "computationally infeasible, not mathematically impossible",
    "relevant question is whether one can start with a specified file",
    "NIST) calls this second-preimage resistance",
    "expects an approved hash function to make such a search computationally infeasible",
    "differs from collision resistance",
    "any pair of different inputs that match",
    "supports a narrow claim",
    "agreement is evidence of internal consistency, not of origin",
)

REQUIRED_SELECTION_SCOPE_ANCHORS = (
    "Selection acts at two levels",
    "fixture covers only a few possible inputs",
    "published components are my selection from a private whole",
)

REQUIRED_COLLECTION_ROUTE_ANCHORS = (
    r"It calls this classification a \emph{route}",
    "preserves source text, re-creates behaviour on fixed cases",
    "generated from the same underlying records",
    "They cannot create an independent witness",
    r"public component map, \component{ORGANS.md}",
    "an inherited filename",
    "Follow it rather than guessing",
    "some components share a page",
    r"\component{paper_modules/batch8_audio_level_rms_port.md}",
)

REQUIRED_STRONGER_EVALUATION_ANCHORS = (
    "These are not the four publication routes",
    "A publication route classifies evidence already in the registry",
    "evaluations below describe new work by someone outside the project",
    "Five forms of independent evaluation",
    "The evaluations are not cumulative stages",
    "repository's evidence still came from the project",
    "It includes no outside evaluator's report",
    "although a private rerun could be unreported",
    "These evaluations do not pair one-for-one with the distinctions",
)

REQUIRED_APPENDIX_ORIENTATION_ANCHORS = (
    r"\section{Dated reproduction record}",
    r"README-first order (internally \component{readme_onboarding_route})",
    "wrote 21 generated files under",
)

FORBIDDEN_LEGACY_NAMING_BEFORE_APPENDIX = (
    r"\emph{organ}",
    "project was previously called Microcosm",
    r"generated page \code{ORGANS.md}",
    "named for the old term",
    "calls components ``organs''",
)

REQUIRED_APPENDIX_LEGACY_NAME_ANCHORS = (
    "Formerly Microcosm, Plectis retains",
    r"package \code{microcosm\_core}",
    r"page \code{ORGANS.md} (``organs'' means components)",
    r"the \code{microcosm} alias",
    r"This paper uses command \code{plectis}",
)

REQUIRED_FORMAL_MATH_BOUNDARY_ANCHORS = (
    "computer-checked mathematics label covers different checks",
    "small public statements checked by Lean",
    "The label itself supplies no theorem",
    "each entry supports only its own public claim and stated limit",
)

REQUIRED_LEAN_CHECK_EXPLANATION_ANCHORS = (
    r"project-wide Lean trust scan checks \leanfilecount{} files",
    "six text patterns",
    "does not run Lean or verify proofs",
    "unfinished placeholders",
    "unproved assumptions",
    "compiled calculations whose acceptance relies on more than Lean's small proof-checking core",
    r"\code{partial} definitions (runnable but not unfoldable in proofs)",
    r"\code{unsafe} definitions (barred from theorems)",
    "removed computation limits",
    "No pattern appeared",
    "scan does not show whether files compile, proofs are valid",
    "statements express their authors' intent",
    "Separate components run Lean on small test projects",
    "their results apply only to those projects",
    "Partial and Unsafe Definitions",
)

REQUIRED_PUBLIC_TEST_SCOPE_ANCHORS = (
    r"limited \code{make test} run covered 32 public test files, not every test file",
    "356 of 361 tests passed, two skipped, and three failed",
    "line-break expectation",
    "outdated line or byte counts",
    "root-layout rules that did not yet allow",
    "paper/public-test-receipt.json",
    r"\code{make ci} would add smoke and package-install checks, but was not green",
    "this is my run, not an independent repetition",
)

EXPECTED_PUBLIC_TEST_RESULT = {
    "status": "fail",
    "command_exit_code": 2,
    "passed": 356,
    "skipped": 2,
    "failed": 3,
    "total": 361,
}

EXPECTED_PUBLIC_TEST_FAILURES = {
    "tests/test_public_entry_docs.py::test_public_repo_boundary_docs_name_runtime_contracts",
    "tests/test_public_source_body_custody.py::test_public_source_body_manifest_targets_are_current_and_shipped",
    "tests/test_public_repo_profile.py::test_profile_passes_on_this_repository",
}

EXAMPLE_ORGAN_ID = "batch8_audio_level_rms_port"
EXAMPLE_RECEIPT = (
    "receipts/first_wave/batch8_audio_level_rms_port/"
    "batch8_audio_level_rms_port_validation_receipt.json"
)
EXAMPLE_RESULT = (
    "receipts/first_wave/batch8_audio_level_rms_port/"
    "batch8_audio_level_rms_port_result.json"
)

PINNED_RECEIPT_FLOW_SOURCE_TOKENS = {
    "src/microcosm_core/organs/_crown_jewel_common.py": (
        'status = PASS if not findings else "blocked"',
        "validation_path = out_path / spec.validation_receipt_name",
        "write_json_atomic(validation_path, validation_payload)",
    ),
    "src/microcosm_core/organs/batch8_audio_level_rms_port.py": (
        'expected_level = row.get("expected_level")',
        "delta = abs(observed - float(expected_level))",
        'status = "pass" if delta <= tolerance else "blocked"',
    ),
}

REQUIRED_CITATION_KEYS = (
    "runeson2009",
    "nasem2019",
    "barr2015",
    "rosenthal1979",
    "omgsacm2023",
    "acmartifact",
    "nistfips1804",
    "nisthashfunctions",
    "nasa8739",
    "leanvalidation",
)

SACM_SOURCE_FIT_ANCHORS = (
    "defines such a case as a collection of auditable claims, arguments, and evidence",
    "the relationship is itself an assertion by the case's author",
    "Representing an argument is therefore not the same as establishing its validity",
    "neither models nor independently justifies the evidential link",
)

REQUIRED_PINPOINT_CITATIONS = (
    r"\cite[\S2.5, p.~138]{runeson2009}",
    r"\cite[conclusion 3-1]{nasem2019}",
    r"\cite[p.~9]{nasem2019}",
    r"\cite[p.~507]{barr2015}",
    r"\cite[Defs.~2.4 and 2.6--2.8, pp.~509--510]{barr2015}",
    r"\cite[p.~638]{rosenthal1979}",
    r"\cite[secs. 1.1, 4, 7.3, 11.9--11.15]{omgsacm2023}",
    r"\cite[security-strength table]{nisthashfunctions}",
    r"\cite[\S4.4.1.2, p.~48]{nasa8739}",
)

MIN_BIBLIOGRAPHY_FONT_PT = 7.5

# Canonical identifiers and version markers verified against the publisher or
# standards body's own page on 18 July 2026. Checking only citation keys would
# allow an entry to keep its label while drifting to the wrong DOI, version,
# section, or website.
REQUIRED_BIBLIOGRAPHY_TOKENS = {
    "runeson2009": (
        "14(2):131--164, 2009",
        "https://doi.org/10.1007/s10664-008-9102-8",
    ),
    "nasem2019": (
        "Washington, DC",
        "The National Academies Press, 2019",
        "https://doi.org/10.17226/25303",
    ),
    "barr2015": (
        "IEEE Transactions on Software Engineering",
        "41(5):507--525, 2015",
        "https://doi.org/10.1109/TSE.2014.2372785",
    ),
    "rosenthal1979": (
        "86(3):638--641, 1979",
        "https://doi.org/10.1037/0033-2909.86.3.638",
    ),
    "omgsacm2023": (
        "2.3, formal/23-05-08, October 2023",
        "https://www.omg.org/spec/SACM/2.3/PDF",
    ),
    "acmartifact": (
        "v1.1, 24 Aug. 2020; accessed 18 July 2026",
        "https://www.acm.org/publications/policies/artifact-review-and-badging-current",
    ),
    "nistfips1804": (
        "FIPS PUB 180-4, 2015",
        "https://doi.org/10.6028/NIST.FIPS.180-4",
    ),
    "nisthashfunctions": (
        "Updated 9 September 2024",
        "Accessed 18 July 2026",
        "https://csrc.nist.gov/projects/hash-functions",
    ),
    "nasa8739": (
        "National Aeronautics and Space Administration",
        "NASA-STD-8739.8B, Section 4.4.1.2, p.~48, 2022",
        "https://standards.nasa.gov/standard/NASA/NASA-STD-87398",
    ),
    "leanvalidation": (
        "Accessed 18 July 2026",
        "https://lean-lang.org/doc/reference/latest/ValidatingProofs/",
        "https://lean-lang.org/doc/reference/latest/Definitions/Recursive-Definitions/#partial-and-unsafe-definitions",
    ),
}

EXAMPLE_CASE_VALUES = {
    "float32_reference_buffer": "0.489897949",
    "int16_reference_buffer": "0.489892970",
    "clamp_over_one_buffer": "1.000000000",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_public_test_receipt(path: Path, failures: list[str]) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        failures.append(f"cannot read public-test receipt: {path}")
        return {}
    if not isinstance(payload, dict):
        failures.append("public-test receipt is not a JSON object")
        return {}
    return payload


def _load_json_from_commit(commit: str, relative_path: str, failures: list[str]) -> dict:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        failures.append(f"cannot read pinned evidence: {relative_path} at {commit}")
        return {}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        failures.append(f"pinned evidence is not valid JSON: {relative_path} at {commit}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"pinned evidence is not a JSON object: {relative_path} at {commit}")
        return {}
    return payload


def _load_text_from_commit(commit: str, relative_path: str, failures: list[str]) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        failures.append(f"cannot read pinned source: {relative_path} at {commit}")
        return ""
    return result.stdout


def _lean_file_count_from_commit(commit: str, failures: list[str]) -> int | None:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", commit, "--"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        failures.append(f"cannot list pinned repository tree at {commit}")
        return None
    return sum(1 for path in result.stdout.splitlines() if path.endswith(".lean"))


def _macros(text: str) -> dict[str, str]:
    return {match.group("name"): match.group("value") for match in MACRO_RE.finditer(text)}


def _first_citation_order(text: str) -> list[str]:
    """Return citation keys in the order in which the paper first uses them."""
    ordered: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"\\cite(?:\[[^\]]*\])?\{([^}]*)\}", text):
        for key in match.group(1).split(","):
            key = key.strip()
            if key and key not in seen:
                ordered.append(key)
                seen.add(key)
    return ordered


def _bibliography_items(text: str) -> dict[str, str]:
    """Return each bibliography item with whitespace normalized."""
    matches = list(re.finditer(r"\\bibitem\{([^}]+)\}", text))
    items: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        items[match.group(1)] = re.sub(r"\s+", " ", text[match.start():end])
    return items


def _macro_int(macros: dict[str, str], name: str, failures: list[str]) -> int | None:
    value = macros.get(name)
    if value is None:
        failures.append(f"missing paper macro: {name}")
        return None
    try:
        return int(value)
    except ValueError:
        failures.append(f"paper macro {name} is not an integer: {value!r}")
        return None


def check_paper(
    paper_path: Path = PAPER,
    registry_path: Path = REGISTRY,
    families_path: Path = FAMILIES,
    public_test_receipt_path: Path = PUBLIC_TEST_RECEIPT,
    *,
    check_git_commit: bool = True,
) -> list[str]:
    """Return every paper/evidence mismatch; an empty list is a pass."""
    text = paper_path.read_text(encoding="utf-8")
    normalized_text = re.sub(r"\s+", " ", text)
    lower = normalized_text.lower()
    macros = _macros(text)
    failures: list[str] = []
    public_test_receipt = _load_public_test_receipt(
        public_test_receipt_path, failures
    )

    snapshot = macros.get("snapshotcommit", "")
    snapshot_resolves = False
    if not re.fullmatch(r"[0-9a-f]{40}", snapshot):
        failures.append("snapshotcommit must be a full 40-character lowercase Git hash")
    elif check_git_commit and (ROOT / ".git").exists():
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{snapshot}^{{commit}}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        snapshot_resolves = result.returncode == 0
        if not snapshot_resolves:
            failures.append(f"snapshotcommit does not resolve in this repository: {snapshot}")

    if public_test_receipt.get("subject_commit") != snapshot:
        failures.append("public-test receipt subject_commit disagrees with snapshotcommit")
    selection = public_test_receipt.get("selection") or {}
    if selection.get("selected_test_file_count") != 32:
        failures.append("public-test receipt must select 32 public test files")
    result = public_test_receipt.get("result") or {}
    for field, expected in EXPECTED_PUBLIC_TEST_RESULT.items():
        if result.get(field) != expected:
            failures.append(
                f"public-test receipt {field}={result.get(field)!r}, expected {expected!r}"
            )
    receipt_failure_ids = {
        str(row.get("node_id") or "")
        for row in public_test_receipt.get("failures") or []
        if isinstance(row, dict)
    }
    if receipt_failure_ids != EXPECTED_PUBLIC_TEST_FAILURES:
        failures.append("public-test receipt failing test ids disagree")

    use_pinned_evidence = (
        snapshot_resolves
        and registry_path == REGISTRY
        and families_path == FAMILIES
    )
    pinned_example_receipt: dict = {}
    pinned_example_result: dict = {}
    pinned_lean_file_count: int | None = None
    pinned_receipt_flow_sources: dict[str, str] = {}
    if use_pinned_evidence:
        registry = _load_json_from_commit(
            snapshot, REGISTRY.relative_to(ROOT).as_posix(), failures
        )
        families = _load_json_from_commit(
            snapshot, FAMILIES.relative_to(ROOT).as_posix(), failures
        )
        pinned_example_receipt = _load_json_from_commit(
            snapshot, EXAMPLE_RECEIPT, failures
        )
        pinned_example_result = _load_json_from_commit(
            snapshot, EXAMPLE_RESULT, failures
        )
        pinned_lean_file_count = _lean_file_count_from_commit(snapshot, failures)
        for relative_path in PINNED_RECEIPT_FLOW_SOURCE_TOKENS:
            pinned_receipt_flow_sources[relative_path] = _load_text_from_commit(
                snapshot, relative_path, failures
            )
    else:
        registry = _load_json(registry_path)
        families = _load_json(families_path)

    for relative_path, required_tokens in PINNED_RECEIPT_FLOW_SOURCE_TOKENS.items():
        source = pinned_receipt_flow_sources.get(relative_path)
        if source is None:
            continue
        for token in required_tokens:
            if token not in source:
                failures.append(
                    f"pinned receipt-flow source lacks {token!r}: {relative_path}"
                )
    common_path = "src/microcosm_core/organs/_crown_jewel_common.py"
    common_source = pinned_receipt_flow_sources.get(common_path, "")
    common_tokens = PINNED_RECEIPT_FLOW_SOURCE_TOKENS[common_path]
    if all(token in common_source for token in common_tokens):
        positions = [common_source.index(token) for token in common_tokens]
        if positions != sorted(positions):
            failures.append(
                "pinned receipt-flow source no longer decides the verdict before "
                "creating and writing its receipt"
            )

    organs = registry.get("implemented_organs", [])
    organ_ids = [str(row.get("organ_id") or "") for row in organs]
    if len(organ_ids) != len(set(organ_ids)):
        failures.append("organ registry contains duplicate organ ids")

    component_count = _macro_int(macros, "componentcount", failures)
    if component_count is not None and component_count != len(organs):
        failures.append(
            f"componentcount={component_count}, registry implemented_organs={len(organs)}"
        )

    lean_file_count = _macro_int(macros, "leanfilecount", failures)
    if (
        lean_file_count is not None
        and pinned_lean_file_count is not None
        and lean_file_count != pinned_lean_file_count
    ):
        failures.append(
            f"leanfilecount={lean_file_count}, pinned Lean sources={pinned_lean_file_count}"
        )

    family_rows = families.get("families", [])
    family_count = _macro_int(macros, "familycount", failures)
    if family_count is not None and family_count != len(family_rows):
        failures.append(f"familycount={family_count}, registry families={len(family_rows)}")

    families_by_id = {
        str(row.get("family_id") or ""): row for row in family_rows if isinstance(row, dict)
    }
    for family_id, macro_name in FAMILY_MACROS.items():
        row = families_by_id.get(family_id)
        if row is None:
            failures.append(f"missing family registry row: {family_id}")
            continue
        actual = len(row.get("organ_ids", []))
        declared = _macro_int(macros, macro_name, failures)
        if declared is not None and declared != actual:
            failures.append(f"{macro_name}={declared}, {family_id}={actual}")

    truth_counts: dict[str, int] = {}
    for row in organs:
        bucket = str(row.get("truth_accounting_bucket") or "")
        truth_counts[bucket] = truth_counts.get(bucket, 0) + 1
    for bucket, macro_name in TRUTH_BUCKET_MACROS.items():
        declared = _macro_int(macros, macro_name, failures)
        actual = truth_counts.get(bucket, 0)
        if declared is not None and declared != actual:
            failures.append(f"{macro_name}={declared}, {bucket}={actual}")
    undeclared_buckets = sorted(set(truth_counts) - set(TRUTH_BUCKET_MACROS))
    if undeclared_buckets:
        failures.append(f"paper does not account for truth buckets: {undeclared_buckets}")

    example = next((row for row in organs if row.get("organ_id") == EXAMPLE_ORGAN_ID), None)
    if EXAMPLE_ORGAN_ID not in text:
        failures.append(f"paper does not name its worked-example organ: {EXAMPLE_ORGAN_ID}")
    if Path(EXAMPLE_RECEIPT).name not in text:
        failures.append("paper does not name the worked-example validation receipt")
    if example is None:
        failures.append(f"worked-example organ is absent: {EXAMPLE_ORGAN_ID}")
    else:
        if EXAMPLE_RECEIPT not in example.get("generated_receipts", []):
            failures.append("worked-example receipt is not declared by the organ registry")
        if EXAMPLE_RESULT not in example.get("generated_receipts", []):
            failures.append("worked-example result is not declared by the organ registry")
        command = str(example.get("validator_command") or "")
        if EXAMPLE_ORGAN_ID not in command or "--input" not in command or "--out" not in command:
            failures.append("worked-example validator command no longer has the documented shape")

    if use_pinned_evidence:
        if pinned_example_receipt.get("status") != "pass":
            failures.append("pinned worked-example validation receipt is not a pass")
        exercise = pinned_example_result.get("exercise", {})
        reference_cases = {
            str(row.get("case_id") or ""): row
            for row in exercise.get("reference_cases", [])
            if isinstance(row, dict)
        }
        for case_id, displayed_value in EXAMPLE_CASE_VALUES.items():
            row = reference_cases.get(case_id)
            if row is None:
                failures.append(f"pinned worked-example result lacks case: {case_id}")
                continue
            for field in ("expected_level", "observed_level"):
                try:
                    actual = f"{float(row[field]):.9f}"
                except (KeyError, TypeError, ValueError):
                    failures.append(
                        f"pinned worked-example {case_id} lacks numeric {field}"
                    )
                    continue
                if actual != displayed_value:
                    failures.append(
                        f"paper value {displayed_value} disagrees with pinned "
                        f"{case_id} {field}={actual}"
                    )
            if displayed_value not in text:
                failures.append(
                    f"paper does not display pinned worked-example value: {displayed_value}"
                )

    for phrase in FORBIDDEN_OVERCLAIMS:
        if phrase in lower:
            failures.append(f"forbidden overclaim remains in paper: {phrase!r}")
    for phrase in FORBIDDEN_COLD_READER_RESIDUE:
        if phrase in lower:
            failures.append(f"cold-reader residue remains in paper: {phrase!r}")
    for anchor in REQUIRED_COLD_READER_ANCHORS:
        if anchor not in normalized_text:
            failures.append(f"missing cold-reader anchor: {anchor!r}")
    for anchor in SACM_SOURCE_FIT_ANCHORS:
        if anchor not in normalized_text:
            failures.append(f"missing SACM source-fit explanation: {anchor!r}")
    for anchor in REQUIRED_RECEIPT_FLOW_ANCHORS:
        if anchor not in normalized_text:
            failures.append(f"missing receipt-flow explanation: {anchor!r}")
    for anchor in REQUIRED_PRIVATE_EVIDENCE_SCOPE_ANCHORS:
        if anchor not in normalized_text:
            failures.append(f"missing private-evidence scope boundary: {anchor!r}")
    for abbreviation, expansion in REQUIRED_FIRST_USE_EXPANSIONS:
        if expansion not in normalized_text:
            failures.append(
                f"missing first-use expansion for {abbreviation}: {expansion!r}"
            )
            continue
        before_expansion = normalized_text.split(expansion, 1)[0]
        if re.search(rf"\b{re.escape(abbreviation)}\b", before_expansion):
            failures.append(
                f"abbreviation appears before its expansion: {abbreviation!r}"
            )
    for anchor in REQUIRED_OUTSIDE_EVALUATION_BOUNDARY_ANCHORS:
        if anchor not in normalized_text:
            failures.append(
                f"missing outside-evaluation knowledge boundary: {anchor!r}"
            )
    contract_section = r"\section{The component contract}"
    first_section = text.split(contract_section, 1)[0]
    normalized_first_section = re.sub(r"\s+", " ", first_section)
    opening_body = text.split(r"\begin{abstract}", 1)[-1].split(
        contract_section, 1
    )[0]
    for term in FORBIDDEN_BEFORE_COMPONENT_CONTRACT:
        if re.search(rf"\b{re.escape(term)}\b", opening_body, flags=re.IGNORECASE):
            failures.append(
                f"technical term precedes its definition in component contract: {term!r}"
            )
    for anchor in REQUIRED_FIRST_SECTION_ORIENTATION_ANCHORS:
        if anchor not in normalized_first_section:
            failures.append(f"missing first-section orientation anchor: {anchor!r}")
    for anchor in REQUIRED_METHOD_DISCLOSURE_ANCHORS:
        if anchor not in normalized_first_section:
            failures.append(f"missing first-section method disclosure: {anchor!r}")
    for anchor in REQUIRED_PLAIN_LANGUAGE_ORIENTATION_ANCHORS:
        if anchor not in normalized_text:
            failures.append(f"missing plain-language orientation anchor: {anchor!r}")
    run_section = text.split(r"\section{One run, examined}", 1)[-1]
    run_section = run_section.split(r"\section{Five distinctions}", 1)[0]
    normalized_run_section = re.sub(r"\s+", " ", run_section)
    for anchor in REQUIRED_EXAMPLE_BRIDGE_ANCHORS:
        if anchor not in normalized_run_section:
            failures.append(f"missing example-to-distinctions bridge: {anchor!r}")
    for anchor in REQUIRED_EXPECTED_REFUSAL_EXPLANATION_ANCHORS:
        if anchor not in normalized_run_section:
            failures.append(f"missing expected-refusal explanation: {anchor!r}")
    for anchor in REQUIRED_WORKED_EXAMPLE_COMMAND_ANCHORS:
        if anchor not in normalized_run_section:
            failures.append(f"missing copyable worked-example command: {anchor!r}")
    for anchor in REQUIRED_ARITHMETIC_ORACLE_BOUNDARY_ANCHORS:
        if anchor not in normalized_text:
            failures.append(f"missing arithmetic-oracle boundary: {anchor!r}")
    for anchor in REQUIRED_TEST_ORACLE_EXPLANATION_ANCHORS:
        if anchor not in normalized_text:
            failures.append(
                f"missing plain-language test-oracle explanation: {anchor!r}"
            )
    distinctions_intro = text.split(r"\section{Five distinctions}", 1)[-1]
    distinctions_intro = distinctions_intro.split(
        r"\subsection*{Public execution versus where the code came from}", 1
    )[0]
    normalized_distinctions_intro = re.sub(r"\s+", " ", distinctions_intro)
    for anchor in REQUIRED_EARLY_DISTINCTION_MAP_ANCHORS:
        if anchor not in normalized_distinctions_intro:
            failures.append(f"missing early five-gap map: {anchor!r}")
    conclusion_section = text.split(r"\section{Conclusion}", 1)[-1]
    conclusion_section = conclusion_section.split(r"\appendix", 1)[0]
    normalized_conclusion_section = re.sub(r"\s+", " ", conclusion_section)
    for anchor in REQUIRED_FIRST_REVIEW_ANCHORS:
        if anchor not in normalized_conclusion_section:
            failures.append(f"missing executable first-review route: {anchor!r}")
    provenance_section = text.split(
        r"\subsection*{Public execution versus where the code came from}", 1
    )[-1]
    provenance_section = provenance_section.split(
        r"\subsection*{Repeatability versus correctness}", 1
    )[0]
    normalized_provenance_section = re.sub(r"\s+", " ", provenance_section)
    for anchor in REQUIRED_PROVENANCE_HASH_ANCHORS:
        if anchor not in normalized_provenance_section:
            failures.append(f"missing plain-language hash boundary: {anchor!r}")
    selection_section = text.split(
        r"\subsection*{Selected cases versus general behaviour}", 1
    )[-1]
    selection_section = selection_section.split(
        r"\subsection*{Risk reduction versus guarantee}", 1
    )[0]
    normalized_selection_section = re.sub(r"\s+", " ", selection_section)
    for anchor in REQUIRED_SELECTION_SCOPE_ANCHORS:
        if anchor not in normalized_selection_section:
            failures.append(f"missing two-level selection explanation: {anchor!r}")
    if r"\begin{figure}[H]" not in selection_section:
        failures.append("selection figure must not interrupt its preceding paragraph")
    collection_section = text.split(r"\section{What the collection contains}", 1)[-1]
    collection_section = collection_section.split(r"\section{The author's hand}", 1)[0]
    normalized_collection_section = re.sub(r"\s+", " ", collection_section)
    for anchor in REQUIRED_COLLECTION_ROUTE_ANCHORS:
        if anchor not in normalized_collection_section:
            failures.append(f"missing collection route explanation: {anchor!r}")
    stronger_section = text.split(r"\section{What stronger evidence would look like}", 1)[-1]
    stronger_section = stronger_section.split(r"\section{Conclusion}", 1)[0]
    normalized_stronger_section = re.sub(r"\s+", " ", stronger_section)
    for anchor in REQUIRED_STRONGER_EVALUATION_ANCHORS:
        if anchor not in normalized_stronger_section:
            failures.append(
                f"missing stronger-evaluation terminology boundary: {anchor!r}"
            )
    for anchor in REQUIRED_FORMAL_MATH_BOUNDARY_ANCHORS:
        if anchor not in normalized_stronger_section:
            failures.append(f"missing formal-math evidence boundary: {anchor!r}")
    if r"\begin{figure}[H]" not in stronger_section:
        failures.append(
            "stronger-evaluation figure must follow its terminology definition"
        )
    pre_appendix_section, appendix_section = text.split(r"\appendix", 1)
    normalized_pre_appendix_section = re.sub(r"\s+", " ", pre_appendix_section)
    for phrase in FORBIDDEN_LEGACY_NAMING_BEFORE_APPENDIX:
        if phrase in normalized_pre_appendix_section:
            failures.append(
                f"legacy naming prose must stay in the reproduction appendix: {phrase!r}"
            )
    normalized_appendix_section = re.sub(r"\s+", " ", appendix_section)
    for anchor in REQUIRED_APPENDIX_ORIENTATION_ANCHORS:
        if anchor not in normalized_appendix_section:
            failures.append(
                f"missing appendix internal-label explanation: {anchor!r}"
            )
    for anchor in REQUIRED_APPENDIX_LEGACY_NAME_ANCHORS:
        if anchor not in normalized_appendix_section:
            failures.append(f"missing appendix legacy-name mapping: {anchor!r}")
    for anchor in REQUIRED_LEAN_CHECK_EXPLANATION_ANCHORS:
        if anchor not in normalized_appendix_section:
            failures.append(f"missing Lean check explanation: {anchor!r}")
    for anchor in REQUIRED_PUBLIC_TEST_SCOPE_ANCHORS:
        if anchor not in normalized_appendix_section:
            failures.append(f"missing bounded public-test explanation: {anchor!r}")
    for key in REQUIRED_CITATION_KEYS:
        if not re.search(
            rf"\\cite(?:\[[^\]]*\])?\{{[^}}]*\b{re.escape(key)}\b[^}}]*\}}",
            text,
        ):
            failures.append(f"missing literature citation: {key}")
        if f"\\bibitem{{{key}}}" not in text:
            failures.append(f"missing bibliography item: {key}")
    for citation in REQUIRED_PINPOINT_CITATIONS:
        if citation not in text:
            failures.append(f"missing source pinpoint: {citation}")
    bibliography_items = _bibliography_items(text)
    for key, required_tokens in REQUIRED_BIBLIOGRAPHY_TOKENS.items():
        item = bibliography_items.get(key, "")
        for token in required_tokens:
            if token not in item:
                failures.append(
                    f"bibliography item {key} lacks canonical token: {token}"
                )
    citation_order = _first_citation_order(text)
    bibliography_order = re.findall(r"\\bibitem\{([^}]+)\}", text)
    if bibliography_order != citation_order:
        failures.append(
            "bibliography items must follow first-citation order: "
            + ", ".join(citation_order)
        )
    bibliography_width = re.search(r"\\begin\{thebibliography\}\{([^}]+)\}", text)
    expected_width = str(len(bibliography_order))
    if bibliography_width is None or bibliography_width.group(1) != expected_width:
        failures.append(
            "bibliography label width must match item count: "
            f"expected {expected_width}"
        )
    bibliography_section = text.split(r"\begin{thebibliography}", 1)[-1]
    bibliography_font = re.search(
        r"\\fontsize\{(?P<size>[0-9]+(?:\.[0-9]+)?)pt\}",
        bibliography_section,
    )
    if bibliography_font is None:
        failures.append("bibliography must declare an explicit readable font size")
    elif float(bibliography_font.group("size")) < MIN_BIBLIOGRAPHY_FONT_PT:
        failures.append(
            "bibliography font must be at least "
            f"{MIN_BIBLIOGRAPHY_FONT_PT:g}pt"
        )

    if macros.get("snapshotshort") != snapshot[:12]:
        failures.append("snapshotshort must equal the first 12 characters of snapshotcommit")
    # The appendix's pasteable block hardcodes the checkout line (Verbatim
    # cannot expand macros), so pin the literal to the declared snapshot.
    if snapshot and f"git checkout {snapshot[:12]}" not in text:
        failures.append(
            "appendix code block must contain the literal 'git checkout "
            "<snapshotshort>' line matching snapshotcommit"
        )

    return failures


def main() -> int:
    failures = check_paper()
    if failures:
        print(
            f"Public-system paper check: {len(failures)} failure(s)",
            file=sys.stderr,
        )
        for failure in failures:
            print(f"  FAIL {failure}", file=sys.stderr)
        return 1

    declared_macros = _macros(PAPER.read_text(encoding="utf-8"))
    declared_count = declared_macros["componentcount"]
    declared_lean_count = declared_macros["leanfilecount"]
    print(
        "Public-system paper check: pass "
        f"({declared_count} pinned components; {declared_lean_count} pinned Lean sources; "
        "pinned family counts, evidence routes, worked example and receipt flow, public-test receipt, literature "
        "citations, readable canonical bibliography identifiers and first-citation order, cold-reader anchors, "
        "and claim language agree)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
