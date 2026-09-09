# Implementation report — Windows deterministic demonstration output

**Date:** 9 September 2026

## Finding

The Entry-gate validation on Python 3.12 for Windows passed 624 tests and failed only
`test_demo_matches_committed_sample`. The generated report carried the same analytical values,
labels and assumptions as the committed synthetic sample, but its exact bytes differed.

Two platform newline translations caused the mismatch. `Path.write_text` wrote the temporary
run manifests with CRLF on Windows, while the renderer records the SHA-256 digest of each
manifest's exact bytes. Git could also check out the committed byte-compared HTML sample with
CRLF. Neither difference was analytical, but both changed content identity.

## Correction

`write_run_manifest` now passes `newline="\n"`, and `.gitattributes` pins
`docs/sample_report.html` to LF. The existing byte-for-byte demonstration regression exercises
both requirements through the public `greek-bess demo` path.

## Interpretation

This correction changes no dispatch, forecast, stress, degradation, finance or data behavior.
It changes no reported value and accepts no new evidence. The demonstration remains deterministic
synthetic output and is not official data, a forecast, expected revenue, investment evidence,
financial advice or a bankable study.

## Validation

The complete gate passed from commit `1c850ea90fcd63118bb685ea8e273eaf87d2a142` on Windows
with Python 3.12.10: Ruff passed, mypy reported no issues in 65 source files, all 625 tests
passed in 221.92 seconds, and the wheel build completed successfully. The environment used
pytest 8.4.2 and Hypothesis 6.168.0.

After the machine's Python 3.12 installation became unavailable, the ignored development
environment was rebuilt under the other supported interpreter, Python 3.13.7. The new direct
manifest-newline regression and the end-to-end committed-sample regression both passed there.
The final gate also passed: Ruff, mypy over 65 source files, all 626 tests in 121.07 seconds,
and a clean wheel build. That environment used NumPy 2.5.3, pandas 2.3.3, SciPy 1.18.1,
scikit-learn 1.9.0, ecCodes 2.48.0, pytest 8.4.2, Hypothesis 6.168.0, Ruff 0.16.6, mypy 1.20.2
and build 1.6.0. GitHub CI remains the final clean-environment gate.
