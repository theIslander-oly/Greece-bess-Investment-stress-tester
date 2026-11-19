# Stage 10 aggregate publication review — 18 November 2026

The accepted Stage 10 report is available for private review. This preparation does not
authorize publication, change any scientific result or complete Stage 10. The separate
frozen-selection result also remains in publication review.
The [implementation report](history/implementation_report_stage10_release_preparation_2026-11-18.md)
records the recovery, validation and remaining evidence boundary.

## Accepted source and release identity

| Item | Pinned identity |
| --- | --- |
| Original workflow run | [35252229873](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/35252229873) |
| Producing commit | `76d48d5aea505fefe51ca948cc901d6fbda594a0` |
| Original artifact | `integrated-study-private`, ID `10510326086` |
| Archive SHA-256 | `9aaa06804b7baf3079c24d76ee7b8dbce45264f85b7dddb5f387a7d11c20f4a9` |
| Evidence-index SHA-256 | `214a4caaf52d16f9bd7cb508eb9334f94bfa3a98696cc4820b89eec612daf938` |
| Declaration SHA-256 | `007c90444aedf17135601035c3b46a9731b7117a531692f92e4173f28cdcbe79` |
| Aggregate HTML SHA-256 | `5fb8ccc56b083d9f2cc3a1fdf05b0252c86a4599da1cec29913d3bbb9bdbd342` |
| Aggregate index SHA-256 | `08e58ca064b5b99575d8da1f5d1a6dd7e105f62228802e275f498970beb2da84` |

The archive was recovered and its hash checked against both GitHub and the prior acceptance
record. All 18 indexed files match. The unchanged declaration, successful custody receipt,
two manifests, summary identities and report index verify. Rendering those manifests with
the current code reproduces the original HTML byte for byte. This checks presentation
reproducibility; it does not rerun dispatch or repeat the original independent scientific audit.

The report covers 1 October 2025 through 25 August 2026: 329 days under the declared
50 MW/100 MWh and 25 MW/100 MWh configurations. It presents all three strategies under each
configuration, with their own ageing states, illustrative finance assumptions and finite
historical horizon. It is a retrospective configuration sensitivity, not expected revenue,
an optimal-size result, investment evidence or a lifetime forecast. The original
[acceptance report](history/implementation_report_stage10_private_study_2026-09-17.md)
records the scientific reconciliation and its limits.

## Prepare the review package

Download the original ZIP from the [accepted workflow run](https://github.com/theIslander-oly/Greece-bess-Investment-stress-tester/actions/runs/35252229873)
into the ignored `private/` directory. From the repository root, with the project installed:

```bash
python .github/scripts/prepare_stage10_release.py private/integrated-study-private.zip --output private/stage10-review
```

Use a new output directory. The helper verifies the pinned ZIP SHA-256 before extracting it
to a temporary directory, then verifies the accepted index, every indexed file, declaration,
custody receipt, manifests, report index and byte-identical re-rendering. It stages exactly:

- `index.html`: the original aggregate report bytes;
- `report.index.json`: the original machine-readable report index.

No recursive directory copy is used. Prices, forecasts, daily schedules, cash-flow tables,
logs, manifests and custody records stay outside the review surface. The printed receipt
records hashes and `publication_authorized: false`; it is not publication approval.

Open the staged HTML locally and retain the receipt with the review files. GitHub Actions
artifacts are downloadable by signed-in readers of this public repository, so preparation
runs locally. The original source artifact expires on 16 December 2026. Retaining the two
aggregate files does not preserve or replace the full original evidence.

## Decision and remaining gates

Review both configurations, all strategies, their assumptions and limitations in the exact
HTML identified above. A publication decision must name these bytes and the intended public
route. Code review and local preparation are separate from publication approval. After approval, deploy only the reviewed aggregate files, preserve
any existing public reports, and compare the served HTML and index with their approved
hashes before marking Stage 10 complete.

The 19 September frozen-selection experiment is a different result. Its private index remains
`f7cb1203898844a1539c0dd63e28415ac96252753b0c5c5c150b755f09ae4a4c`. Its
[acceptance record](history/implementation_report_frozen_selection_private_result_2026-09-19.md)
names `private/frozen-selection-experiment-2026-09-19/` in the prior workspace. That bundle
has not been recovered in this continuation. Do not reconstruct its outcome from Stage 10,
rerun training or substitute a new experiment for the accepted private result.
