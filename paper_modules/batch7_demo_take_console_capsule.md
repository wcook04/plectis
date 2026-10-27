# Check Demo Take capture contracts

> **In plain terms.** A recording app relies on a few small guards in its code, and an edit could remove one unnoticed. Its input is the program code of the Demo Take recording console. It checks the code for guards such as the rule that a recording needs at least one screen, audio or webcam source, confirms that altered copies with a guard removed are rejected, and tries to build the app. The output is a short summary of each check, which someone can use to see that the guards are still in place. These check written rules, not real recording, and the build neither launches the app nor shows anything about capture quality or transcription accuracy.

This fixture checks copied Swift sources for a recording console and exercises a build witness, capture state, helper bridge, hotkey, audio meter and transcription payload contracts. It records summaries rather than source or build-log bodies.

## Run the example

From the repository root, with Python 3.11 or newer and the project dependencies installed:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.batch7_demo_take_console_capsule run \
  --input fixtures/first_wave/batch7_demo_take_console_capsule/input \
  --out .microcosm/component-guides/batch7_demo_take_console_capsule/result \
  --acceptance-out .microcosm/component-guides/batch7_demo_take_console_capsule/acceptance.json --card
```

The command prints a compact JSON card and writes its results under `.microcosm/component-guides/`. A passing run returns exit code 0; a blocked run returns 1.

## What this checks

The source checks reject mutations that remove the guard requiring at least one screen, audio or webcam source, the required hotkey modifiers, the audio-meter clamp or the transcription audio guard. These are checks of source contracts, not simulated recording actions. A SwiftPM build witness checks that the selected app target builds; it does not launch the app or record a screen.

## Verification

The example above runs the fixture directly. In `make component-replays`, this component’s exported bundle is checked by the [shared Dafny replay admission core](../formal/replay/README.md) for agreement among supplied source, input, claim-policy and receipt observations. That admission check does not prove this component’s algorithm or the truth of its domain claims.

## Limits

The build witness needs Swift and a compatible macOS environment with the required Apple frameworks. SwiftPM writes build scratch and cache files under `PLECTIS_SWIFT_BUILD_ROOT`, or the system temporary directory when that variable is unset. A successful build and fixture checks do not establish capture quality or transcription accuracy.

## Source and evidence

Read the [implementation](../src/microcosm_core/organs/batch7_demo_take_console_capsule.py), [fixture input](../fixtures/first_wave/batch7_demo_take_console_capsule/input/batch7_demo_take_console_exercise_manifest.json), and [focused tests](../tests/test_batch7_demo_take_console_capsule.py). The [saved acceptance result](../receipts/acceptance/first_wave/batch7_demo_take_console_capsule_fixture_acceptance.json) is historical sample evidence, not the result of your run. The [JSON record](batch7_demo_take_console_capsule.json) identifies the module; the canonical capsule metadata is in [paper_module_capsules.json](../core/paper_module_capsules.json).

[ScreenCaptureKit](https://developer.apple.com/documentation/ScreenCaptureKit) documents the native capture framework.
