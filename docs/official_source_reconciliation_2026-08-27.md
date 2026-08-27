# Official HEnEx to ENTSO-E reconciliation — 27 August 2026

## Scope and interpretation

This report records the live interval-level reconciliation of the accepted official HEnEx Greek
Day-Ahead Market history against ENTSO-E A44 day-ahead prices for the Greek bidding zone, over
market days 1 November 2020 through 25 August 2026. It is a cross-source ingestion result. It
does not estimate battery revenue, forecast prices, or support an investment decision.

Official prices, raw XML and the normalized comparison remain outside Git. Only run identifiers,
hashes, counts and aggregate statistics are recorded here.

## Method

The `Reconcile HEnEx and ENTSO-E prices` workflow performs the comparison inside GitHub Actions,
because the personal ENTSO-E token exists only as an encrypted repository secret and the accepted
history exists only as a short-lived private artifact (decision entry 2026-08-27).

1. Read the `greek-dam-official-history` artifact produced by run `32971677163`.
2. Merge its archived and daily files into one HEnEx series with `merge-canonical`.
3. Derive the reconciliation window from that history rather than from a typed boundary.
4. Retrieve ENTSO-E A44 prices for exactly that window with the private token.
5. Classify every interval with `compare-sources` at a tolerance of EUR 0.000001/MWh.

The derived window is `2020-10-31T23:00Z` to `2026-08-25T22:00Z`, which is midnight to midnight
on the CET/CEST market clock. A hand-typed `2020-10-31T22:00Z` start would have cut one hour into
the 31 October market day and failed the completeness check; deriving the window removes that
class of error entirely.

## Accepted result

Workflow run `33073631530`, reproduced identically by run `33073943495`.

| Classification | Intervals |
|---|---:|
| `match` | 74,662 |
| `price_mismatch` | 1 |
| `missing_henex` | 0 |
| `missing_entsoe` | 0 |
| **Compared** | **74,663** |

| Delivery year | Matching intervals | Mismatching intervals |
|---:|---:|---:|
| 2020 (from 1 Nov) | 1,465 | 0 |
| 2021 | 8,760 | 0 |
| 2022 | 8,760 | 0 |
| 2023 | 8,759 | 1 |
| 2024 | 8,784 | 0 |
| 2025 | 15,390 | 0 |
| 2026 (to 25 Aug) | 22,744 | 0 |

- HEnEx intervals: 74,663; deterministic quality status valid.
- ENTSO-E intervals: 74,663; deterministic quality status valid, with a negative-price
  information notice only.
- Intervals present in both sources: 74,663. Neither source covers an interval the other omits.
- Maximum absolute difference: EUR 0.01/MWh.
- Mean absolute difference: 1.34e-07 EUR/MWh, which is floating-point representation noise.
- Affected market days: 1.
- The comparison artifact `henex-entsoe-reconciliation` (run `33073631530`) has zip SHA-256
  `bee557eaf4f2fa449fe9284bf2d80225e51350c622321cf921f3cbab033b816a`; the reproduction artifact
  (run `33073943495`) has zip SHA-256
  `20ea6364fb6bd47952c254d44a5500f4c2db0ea8fd6a114dea96fe35b7f27dc1`. The two zips differ only
  because the summary gained the affected-day list between runs; every classification count,
  difference statistic and interval total is identical.

**Acceptance decision: Passed, with one recorded EUR 0.01/MWh difference.**

## The single mismatching interval

One interval on market day **29 October 2023** differs between the sources by exactly
EUR 0.01/MWh. That is the autumn DST market day, which carries 25 hours.

The magnitude is exactly the bound of the documented HEnEx MCP rounding-consensus rule, under
which 980 historical intervals took the dominant Greek-zone MCP where one or two cross-border
rows differed by no more than EUR 0.01/MWh (acceptance report 2026-08-26). This difference is
consistent with that already-accepted one-cent publication rounding and is within the bound the
project has already declared acceptable. It is recorded rather than corrected: neither source is
altered, and the interval keeps both published values in the comparison artifact.

This is a consistency observation, not a proof of cause. Attributing the difference to a specific
cross-border asset row would require the HEnEx workbook for that delivery day.

## Defects this reconciliation found in the project's own ENTSO-E reader

The reconciliation was run six times. The first four runs failed, and each failure identified a
real defect rather than a data problem. The evidence is recorded because it changes how future
ENTSO-E retrievals behave.

| Run | Outcome | Defect found |
|---|---|---|
| `33071463871` | Failed | A single 30-second read timeout discarded the entire six-year retrieval; the client had no retry. |
| `33072187707` | Failed | A rejected request reported only `HTTP 400`, naming neither the request window nor the acknowledgement reason ENTSO-E returned in the response body. |
| `33072709979` | Failed | Four consecutive `HTTP 503` responses exhausted a 30-second retry budget while the Transparency Platform was degraded. |
| `33073110475` | Failed the quality gate | The retrieval completed but classified 4,874 intervals as missing from ENTSO-E. |
| `33073631530` | **Passed** | — |
| `33073943495` | **Passed**, reproduction | — |

The fourth run is the substantive one. It reported 4,874 intervals present in HEnEx and absent
from ENTSO-E, scattered across 1,042 market days, while every interval present in both agreed.
That pattern is not an outage. A44 documents declare a `curveType`, and under `A03`
("variable sized block") a point's price holds until the next declared position: an omitted
position repeats the price before it rather than marking absent data. The parser ignored
`curveType` and emitted one interval per point, so every repeat became a false gap.

After the parser was corrected, the ENTSO-E series contained exactly 4,874 intervals labelled
`entsoe_variable_block_repeat` and the missing-interval count fell to zero. The count matches the
previously missing count exactly, which is what confirms the diagnosis.

The correction is bounded by the period's declared time interval, applies only to `A03`
documents, leaves `A01` documents unchanged so that a genuine gap in a sequential document still
fails the completeness check, and rejects an unknown curve type rather than guessing its
semantics. It does not interpolate: it materializes the repeat semantics the document declares.

## Retrieval conditions

- The ENTSO-E Transparency Platform was intermittently unavailable during the session, returning
  read timeouts and `HTTP 503` responses. Retrieval now retries timeouts, connection failures and
  429/5xx responses up to five times with ten-second linear backoff, and treats rejections such
  as `HTTP 401` as terminal.
- The accepted runs used seven annual requests rather than sixty-nine monthly ones, which reduces
  exposure to per-request platform failures. `--chunk-days` remains configurable.
- No token, endpoint URL or official price reached a job log. Retry notices name the request
  period only.

## Confirmed and still pending

Confirmed by this reconciliation:

- The accepted HEnEx history is independently corroborated by a second official source across all
  2,124 market days, at every interval, with one EUR 0.01/MWh exception.
- The ENTSO-E client works with a private token against the live platform.

Still pending:

- Durable private storage of the accepted history before the artifact expires on 2 September 2026.
- ADMIE variables remain quarantined until pre-auction publication timing is proven.
- Deleting the `ENTSOE_SECURITY_TOKEN` repository secret and rotating the token at ENTSO-E now
  that acceptance has passed.
