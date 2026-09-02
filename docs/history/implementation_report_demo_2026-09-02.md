# Implementation report — one-command synthetic demonstration

**Date:** 2 September 2026  
**Branch:** `claude/project-improvement-cv-3h4k2m`  
**Scope:** Public synthetic workflow integration; no official evidence or new runtime dependency.

## Choice of interface

The demonstration is a `greek-bess demo` subcommand rather than a Make target. The CLI is already
the supported, cross-platform interface installed from the Python package, while Make would add a
second tool prerequisite and merely shell back into that interface. Registering the path through
the existing `Command` pattern also keeps parser declaration and dispatch inseparable.

## End-to-end path

One command generates a deterministic hourly synthetic year, runs independent daily
perfect-foresight solves, declares and applies a 0.7 daily-mean spread-compression factor, solves
the compressed path, aggregates its recorded interval results into the complete daily operating
path required by finance, and evaluates explicitly illustrative one-year unlevered screening
arithmetic. It records the synthetic input, both ceilings, transformation and finance result as
five verified manifests before composing one indexed self-contained report.

The demo uses a fixed record time so identical code and inputs produce identical report bytes.
Temporary manifests and the machine index are removed after rendering; the requested HTML is the
single user-facing output. No network, token, official data or new dependency is involved.

## Committed sample exception

`docs/sample_report.html` is deliberately committed despite the standing generated-output rule.
It is synthetic-only, carries the mandatory labels and exclusions beside every figure, and gives
a reader an immediate inspectable output. A test runs the public command and compares its bytes
with the committed file, making stale sample behaviour a failing gate rather than a documentation
maintenance convention.

## Validation

Ruff, mypy, pytest and a clean wheel build are required. The complete diff is also checked for
credentials, forbidden attribution and unintended generated artifacts.
