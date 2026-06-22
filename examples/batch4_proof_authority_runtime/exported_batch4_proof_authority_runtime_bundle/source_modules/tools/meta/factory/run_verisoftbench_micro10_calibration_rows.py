"""Public Plectis compatibility stub for a withheld private source module.

The original control-plane body is intentionally not part of the public slice.
Matched private ref: tools/meta/factory/run_verisoftbench_micro10_calibration_rows.py
Boundary class: private_body_exact_match
"""

PUBLIC_MICROCOSM_STUB = True
WITHHELD_PRIVATE_SOURCE_REF = 'tools/meta/factory/run_verisoftbench_micro10_calibration_rows.py'


def unavailable(*_args, **_kwargs):
    raise RuntimeError(
        "This private control-plane body is withheld from the public Plectis release."
    )
