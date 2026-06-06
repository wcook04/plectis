# Batch 8 Audio Level RMS Port

This organ ports the pure `AudioLevelMonitor.normalizedLevel` RMS math from Swift to Python and exercises it over public synthetic sample arrays.

The capsule is bounded to numeric parity. It does not start an
`AVCaptureSession`, request microphone permission, read recorded audio, capture
a device, claim UI readiness, authorize publication, or approve release.

## JSON Capsule Binding

Source authority for this reader page is
`core/paper_module_capsules.json::paper_modules[59:paper_module.batch8_audio_level_rms_port]`;
the generated instance is `paper_modules/batch8_audio_level_rms_port.json`
with `source_authority: json_capsule`.

This Markdown is a reader projection over the capsule, not the authority plane.
The generated Mermaid projection is `available_from_capsule_edges`, and the
Atlas card is linked from the same capsule edges; those projections help
navigation but do not expand the authority ceiling.

The proof boundary is deterministic RMS parity over public fixture inputs and
copied source refs only. A cold reader should not treat this page, Mermaid
availability, or Atlas linkage as macOS audio-session evidence, microphone
permission authority, device capture proof, UI readiness, publication approval,
or release approval.

## JSON Capsule Boundary

The JSON capsule is the source of record for this reader projection. It binds
the page to the `batch8_audio_level_rms_port` organ, the resolving public
audio-level RMS mechanism subject, the import/projection drift concept, the RMS
port runtime locus, and the law/dependency edges listed below.

The generated row currently exposes 19 capsule-derived relationship edges.
Mermaid is `available_from_capsule_edges`, Atlas is
`linked_from_capsule_edges`, and there are no unresolved selective relations.
Those projections make the capsule walkable; they do not start an audio
session, request microphone permission, prove device capture, approve UI
readiness, approve publication, or approve release.

## Shape

Read this module as a bounded RMS-parity pipeline: the JSON capsule names the
reader authority, runtime locus, standard, and generated navigation edges; the
runtime ports Swift `normalizedLevel` math over public fixture arrays; tests and
receipts verify numeric parity and body-free evidence. Generated Mermaid and
Atlas links are navigation status, not macOS audio-session, microphone, device,
source-mutation, publication, or release authority.

```mermaid
flowchart TD
  capsule["JSON capsule<br/>core/paper_module_capsules.json[59]<br/>source_authority: json_capsule"]
  reader["Reader projection<br/>paper_modules/batch8_audio_level_rms_port.md<br/>Markdown is not authority"]
  instance["Generated JSON instance<br/>paper_modules/batch8_audio_level_rms_port.json<br/>19 edges; 0 unresolved selective relations"]
  standard["Standards<br/>standards/std_microcosm_batch8_audio_level_rms_port.json<br/>std_microcosm ceiling applies"]
  runtime["Runtime/source locus<br/>src/microcosm_core/organs/batch8_audio_level_rms_port.py<br/>normalized_level + run + validate-bundle"]
  bundle["Fixtures and source bundle<br/>fixtures/first_wave/batch8_audio_level_rms_port/input<br/>examples/batch8_audio_level_rms_port/exported_batch8_audio_level_rms_port_bundle"]
  swift["Copied Swift source ref<br/>AudioLevelMonitor.swift<br/>source_module_manifest.json; body-free receipts"]
  cases["Public parity cases<br/>float32, int16, clamp, empty buffer, unsupported format"]
  receipts["Tests and receipts<br/>tests/test_batch8_audio_level_rms_port.py<br/>receipts/first_wave + acceptance refs"]
  projections["Generated navigation<br/>Mermaid available_from_capsule_edges<br/>Atlas linked_from_capsule_edges"]
  ceiling["Authority ceiling<br/>deterministic Python RMS parity over public fixtures only<br/>no audio session, microphone, device, source mutation, publication, or release authority"]

  capsule --> reader
  capsule --> instance
  capsule --> standard
  capsule --> runtime
  bundle --> runtime
  swift --> runtime
  runtime --> cases
  cases --> receipts
  instance --> projections
  receipts --> ceiling
  projections --> ceiling
```

## Reader Proof Boundary

A cold reader can validate this module by starting from the JSON capsule row,
then checking the generated JSON instance, exported Swift source bundle,
synthetic sample arrays, RMS parity receipt, bundle validation receipt, and
focused test. The proof is limited to deterministic numeric parity for the
ported RMS calculation over public fixture inputs.

The proof stops before microphone access, recorded-audio handling, device
capture, `AVCaptureSession` behavior, UI readiness, publication, and release.
Generated Mermaid and Atlas availability are navigation projections derived
from the capsule row, not macOS runtime evidence.

## Public Site Availability Boundary

This Markdown is safe to project on the public site because it exposes fixture
sample classes, source refs, digest anchors, validator commands, and authority
ceilings without exposing recorded audio, device identifiers, microphone state,
private runtime state, or UI screenshots.

Public rendering may explain the pure RMS-port parity route. It must not imply
audio capture, permission handling, product UI readiness, or release approval.

## Public-Safe Body Handling

The source body floor is the copied non-secret Swift source in the exported
bundle. Receipts and cards should carry refs, digests, anchors, sample counts,
and parity verdicts only; copied body text and audio samples stay out of
receipts.

Future body refreshes must preserve the bundle manifest boundary and keep
recorded audio, private device state, microphone permission state, and
credential-equivalent material out of public receipts and site projections.

## Reader Evidence Routing

- Capsule route: read `core/paper_module_capsules.json::paper_modules[59]`
  before treating this Markdown as explanation.
- Generated route: inspect `paper_modules/batch8_audio_level_rms_port.json`
  for the current generated instance derived from the capsule row.
- Bundle route: inspect `examples/batch8_audio_level_rms_port/exported_batch8_audio_level_rms_port_bundle`
  for copied Swift source refs and digest evidence.
- Runtime route: run `tests/test_batch8_audio_level_rms_port.py` and the
  commands in `## Validation Receipt Path` for recomputation evidence.

## Structured Lattice Bindings

The generated JSON row currently contributes 19 relationship edges derived from
the capsule's organ subject, resolved code locus, doctrine refs, and sibling
paper-module dependencies. The Mermaid projection is
`available_from_capsule_edges`; the Atlas projection is
`linked_from_capsule_edges`.

At this HEAD the generated instance reports zero unresolved selective
relations. If future capsule edits introduce residuals, this Markdown page may
name them but must not invent concept ids or promote candidate doctrine.

## First Command

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.batch8_audio_level_rms_port run \
  --input fixtures/first_wave/batch8_audio_level_rms_port/input \
  --out receipts/first_wave/batch8_audio_level_rms_port \
  --acceptance-out receipts/acceptance/first_wave/batch8_audio_level_rms_port_fixture_acceptance.json
```

## Validation Receipt Path

Reader-verifiable commands, run from the `microcosm-substrate/` public root:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.batch8_audio_level_rms_port run \
  --input fixtures/first_wave/batch8_audio_level_rms_port/input \
  --out /tmp/microcosm-batch8-audio-level-rms-port-vrp \
  --acceptance-out /tmp/microcosm-batch8-audio-level-rms-port-fixture-acceptance.json
PYTHONPATH=src python3 -m microcosm_core.organs.batch8_audio_level_rms_port validate-bundle \
  --input examples/batch8_audio_level_rms_port/exported_batch8_audio_level_rms_port_bundle \
  --out /tmp/microcosm-batch8-audio-level-rms-port-bundle-vrp
PYTHONPATH=src ../repo-pytest --disk-pressure-policy=warn \
  microcosm-substrate/tests/test_batch8_audio_level_rms_port.py -q \
  --basetemp /tmp/microcosm-batch8-audio-level-rms-port-tests
```

The fixture command writes the bounded RMS parity receipt and acceptance JSON.
The bundle command validates the copied Swift source module, digest anchors,
negative exercises, body-exclusion scan, and source-ref boundary. The focused
test checks the Python port, bundle validation, receipt body scan, and authority
ceiling.

This receipt path is reader-verifiable evidence only. It does not start an
audio session, request microphone permission, read recorded audio, prove device
capture, approve UI readiness, mutate source, authorize publication, or approve
release.

## Receipt Expectations

A complete local receipt should include the organ run output, bundle validation
output, focused pytest result, and the generated-row proof from
`paper_modules/batch8_audio_level_rms_port.json`. The expected generated-row
proof is `edge_count: 19`, Mermaid `available_from_capsule_edges`, Atlas
`linked_from_capsule_edges`, `source_authority: json_capsule`, and
`unresolved_selective_relation_count: 0`.

## Authority Ceiling

This is deterministic Python-port evidence over fixture inputs only. It is not
macOS audio-session evidence, not microphone permission authority, not device
capture, not UI readiness, not source mutation authority, and not release
approval.

## Claim Ceiling

This paper module can claim a deterministic Python port of the audio-level RMS
calculation with a diagram view generated for this module and navigation links
available from the same source row. It can explain deterministic numeric
RMS/level behavior over fixture inputs and body-free receipts.

It cannot claim macOS audio-session evidence, microphone permission authority,
device capture, UI readiness, source mutation, publication approval, release
approval, or whole-system correctness. Those claims would need new supporting
evidence before this module could narrate them.

## Prior Art Grounding

The organ is grounded in standard digital-audio metering practice: root mean
square amplitude is a common way to summarize signal energy for level displays,
while OS capture APIs and media tools are kept outside pure numeric tests.
Useful anchors include:

- Apple's [AVFoundation](https://developer.apple.com/av-foundation/) media
  framework family for time-based audiovisual capture and processing on Apple
  platforms.
- [FFmpeg audio/video documentation](https://www.ffmpeg.org/documentation.html),
  as a broad media-processing toolchain where audio streams and levels are
  handled as explicit inputs and transforms.

Microcosm borrows only the pure RMS-level calculation shape and ports it to
fixture-bound Python parity tests. It does not start an audio session, request
microphone permission, read recorded audio, capture a device, or approve UI or
release readiness.

## Source Reference

The exported bundle copies
`apps/demo-take-console/Sources/DemoTakeConsoleApp/AudioLevelMonitor.swift`
under
`examples/batch8_audio_level_rms_port/exported_batch8_audio_level_rms_port_bundle/source_modules/`.
Receipts carry refs, digests, anchors, sample counts, and parity verdicts, not
copied body text, recorded audio, or private device state.

## Mechanism Set

The validator requires float32 parity, int16 parity, over-one clamp behavior,
empty-buffer zero behavior, and unsupported-format refusal. Shared registry,
acceptance, runtime-shell, CLI, atlas, package-data, and generated docs wiring
is intentionally deferred while the existing shared Microcosm core lease is
active.
