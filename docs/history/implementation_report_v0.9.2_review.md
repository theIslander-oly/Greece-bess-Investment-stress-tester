# Implementation report — v0.9.2 review

**Date:** 2 September 2026

## Review scope

The review traced the v0.9.2 join from its design and point-in-time schema through revision
selection, evidence-grade admission, interval mapping, audit construction, command behavior and
synthetic tests. The standing refusal remains unchanged: the three operator declarations do not
exist, so no real feature join, acceptance document, model or investment conclusion was produced.

## Findings and corrections

Two related audit-contract defects were found and corrected.

1. The implementation filtered pre-cutoff rows to admitted evidence grades before choosing the
   latest revision. That allowed an older admissible revision to be selected when a newer
   pre-cutoff revision had an inadmissible grade. Selection now occurs across every pre-cutoff
   revision first; the selected revision is then judged against the admitted grades. An
   inadmissible selected revision excludes the whole day by `grade_not_admitted`.
2. Every audit row previously repeated the number of all post-cutoff rows for its variable-area
   pair and day. The row now counts post-cutoff revisions only for its selected native feature
   interval. The summary de-duplicates a native value broadcast to multiple price intervals, so
   its total remains a count of revisions rather than broadcasts.

A regression test constructs a newer assumed revision over an older provider-declared value and
proves that the older value cannot be cherry-picked. The existing revision test now proves that
each value reports one later revision while the summary reports all 24 later revisions once.

## Interpretation

These corrections strengthen leakage prevention and provenance accuracy. They change no accepted
figure: v0.9.2 remains synthetic-only, and the cutoff, decision lead and sampling geography remain
undeclared. Perfect foresight remains a labelled historical gross-margin upper bound, and the
standing market, financial and grid exclusions are unchanged.

## Verification record

Ruff, mypy, the full pytest suite and a clean wheel build passed. The complete diff, ignored-file
inventory and secret-pattern scan were reviewed, and build products were removed before commit.
