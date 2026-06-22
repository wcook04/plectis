"""Public Plectis compatibility stub for a withheld private source module.

The original control-plane body is intentionally not part of the public slice.
Matched private ref: system/lib/feed_envelope.py
Boundary class: private_body_exact_match
"""

PUBLIC_MICROCOSM_STUB = True
WITHHELD_PRIVATE_SOURCE_REF = 'system/lib/feed_envelope.py'


def unavailable(*_args, **_kwargs):
    raise RuntimeError(
        "This private control-plane body is withheld from the public Plectis release."
    )
