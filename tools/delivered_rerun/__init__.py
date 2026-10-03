"""Preregistered analysis of the delivered rerun (freeze candidate).

Spec: development/reference/delivered_rerun_prereg.md. Traceability map:
development/delivered_rerun_traceability.md. Entry point: run.py.
"""

# The registered checks of this package are partly `assert` statements, which
# `python -O` strips. Refuse to import the package at all under -O rather than
# run with checks silently removed (review N1). constants.py repeats the guard
# for a direct module import.
if not __debug__:
    raise RuntimeError("tools.delivered_rerun refuses to run under `python -O`: its "
                       "registered checks are asserts")
