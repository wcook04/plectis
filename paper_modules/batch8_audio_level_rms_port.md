# Calculate a normalized audio level

`normalized_level` is a Python port of a Swift audio-level calculation. Given float32 samples or int16 samples, it calculates the root mean square, multiplies it by eight and clamps the result to 0–1. Int16 values are divided by 32767. An empty buffer returns zero; an unsupported format raises `ValueError`.

The fixture compares reference buffers with expected levels. Separate tests generate WAV bytes and check that decoded samples change the result. Its negative cases exercise the empty buffer, an unknown format and values above the clamp. Tests perturb both samples and expected levels to check that the verdict moves.

## Run the example

Python 3.11 or newer and the project test dependencies (install with `python3 -m pip install -e ".[test]"`) are required. Run from the repository root:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.batch8_audio_level_rms_port run \
  --input fixtures/first_wave/batch8_audio_level_rms_port/input \
  --out .microcosm/component-guides/batch8_audio_level_rms_port \
  --acceptance-out .microcosm/component-guides/batch8_audio_level_rms_port/acceptance.json
```

The command writes its result and acceptance files under `.microcosm/component-guides/`; inspect the status and findings in those files.

## Verification

The sample and byte tests do not constitute a formal proof of the audio calculation. Separately, `make component-replays` runs this component’s registered exported-bundle route through the [Dafny-proved replay admission check](../formal/replay/README.md). Using host-supplied observations, it compares source, input, claim-policy and receipt identities; it does not prove the component’s domain result. The direct command above does not invoke the shared check.

## Limits

This checks the Python calculation on the supplied cases; it does not establish sample-buffer parity on a device, microphone permissions, session behavior or audio capture.

## Sources

[src/microcosm_core/organs/batch8_audio_level_rms_port.py](../src/microcosm_core/organs/batch8_audio_level_rms_port.py) contains the implementation; the [copied Swift source](../examples/batch8_audio_level_rms_port/exported_batch8_audio_level_rms_port_bundle/source_modules/apps/demo-take-console/Sources/DemoTakeConsoleApp/AudioLevelMonitor.swift) supplies the original formula. See the [input fixtures](../fixtures/first_wave/batch8_audio_level_rms_port/input/), [tests](../tests/test_batch8_audio_level_rms_port.py), [historical sample acceptance result](../receipts/acceptance/first_wave/batch8_audio_level_rms_port_fixture_acceptance.json), and the [component JSON record](../core/paper_module_capsules.json). For background on the source platform, see [Apple AVFoundation](https://developer.apple.com/av-foundation/).
