# Evaluate synthetic forecast losses

> **In plain terms.** When forecasting methods are compared on a short record, the best one may have been lucky. This component reads made-up error scores for a baseline method and several candidate methods over 40 occasions, plus a policy on what results may claim. It runs standard statistical tests, several by re-drawing the scores at random 40 times, to judge whether differences between the methods are bigger than luck would explain. The output is each test's result, or a clear refusal when a setup lets a forecast see later data. The scores are made up and the example is small, so it says nothing about real forecasting skill or what anyone should invest in.

This component reads a matrix of synthetic losses for a baseline and candidate forecasts, paired loss series and a boundary policy. The fixture exercises stationary bootstrap, reality check, superior predictive ability and model confidence set calculations, as well as a Diebold–Mariano comparison. The test fixture has 40 observations. Its reality check, superior predictive ability and model confidence set calls each use 40 bootstrap replicates; a separate stationary-bootstrap index demonstration uses five. The fixture deliberately blocks SciPy imports to exercise a typed refusal of the Harvey–Leybourne–Newbold correction to the paired comparison, regardless of whether SciPy is installed.

A lookahead split or a claim that the output authorizes investment advice is rejected. The exported standalone bundle can instead report a declared statistics contract without recomputing the tests; inspect its witness mode before interpreting a result. Synthetic losses and a small fixture do not establish forecasting performance or justify an investment decision.

## Run the example

Python 3.11 or later is required. From the repository root, use the Python API to direct both result and acceptance output into ignored local state. The CLI does not expose the acceptance path for this action.

```bash
PYTHONPATH=src python3 - <<'PYCODE'
from microcosm_core.organs.finance_forecast_evaluation_spine import run
result = run('fixtures/first_wave/finance_forecast_evaluation_spine/input', '.microcosm/component-guides/finance_forecast_evaluation_spine', acceptance_out='.microcosm/component-guides/finance_forecast_evaluation_spine/acceptance.json')
print(result['status'])
PYCODE
```

## Verification

The fixture tests exercise the computations and refusals, not a proof of the statistical code. `make component-replays` runs the exported finance bundle through the [shared Dafny check](../formal/replay/README.md) over supplied source, input, claim-policy and receipt observations. The direct example does not invoke that gate.

## Source

[Implementation](../src/microcosm_core/organs/finance_forecast_evaluation_spine.py) · [Input](../fixtures/first_wave/finance_forecast_evaluation_spine/input) · [Tests](../tests/test_finance_forecast_evaluation_spine.py) · [Historical sample](../receipts/first_wave/finance_forecast_evaluation_spine/finance_forecast_evaluation_spine_result.json) · [JSON record](finance_forecast_evaluation_spine.json)

For background on forecast comparison, see [Diebold and Mariano](https://www.nber.org/papers/t0169) and [Hansen on superior predictive ability](https://ideas.repec.org/a/bes/jnlbes/v23y2005p365-380.html).
