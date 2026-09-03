# Implementation report v0.9.5 — fundamentals official-run preparation

**Date:** 3 September 2026

## Scope

This milestone prepares, but does not execute, official v0.9 acceptance. The manual workflow validates the pre-registered declarations, verifies custody of both accepted inputs, runs availability and point-in-time audits before any benchmark, checks the accepted feature digest, applies the fixed hourly-to-quarter-hour split and complete-season exploratory rule, runs forecast and settled-dispatch comparisons, records/verifies/renders their manifests, and uploads the evidence privately. Its summary contains only an artifact index and interpretation labels.

## Executable acceptance boundary

The manifest contract now refuses both fundamentals benchmark kinds unless declared inputs name the same 64-character accepted feature-set digest as the producer summary. This check runs on record and read. It prevents a generic renderer from presenting a benchmark whose feature table has not already been identified by acceptance, while leaving every numerical result with the forecast or dispatch producer.

## Custody and documents

The established custody step remains the only implementation. The record and encrypted-publication workflows gained an optional accepted-feature-table run ID and use the same digest verification, committed-record behavior, failure-closed marker, and encryption path as accepted price artifacts. No second-copy-under-separate-control rule was added. Reusable acceptance and benchmark templates enumerate required aggregate findings without interval-level official data.

## Generic renderer review

A clearly synthetic fundamentals dispatch manifest is rendered through the current generic path. No bespoke ablation layout is introduced. The synthetic review HTML is an untracked validation artifact only and contains no official input or investment evidence.

## Interpretation and external boundary

All engineering tests use synthetic fixtures. No official feature table, price interval, workflow run ID, acceptance finding, benchmark value, or custody outcome is created by this milestone. Official work must wait for merge and then proceed in the fixed order: fetch/audit, coverage preflight, custody record and verification, dated acceptance commit, benchmark from that digest, and dated benchmark commit regardless of result sign. Perfect foresight remains only a gross-margin upper bound; all results are historical research outputs, not expected revenue, financial advice, a bankable forecast, or an investment-grade study.
