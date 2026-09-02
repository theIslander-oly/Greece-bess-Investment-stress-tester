# Canonical price data dictionary

The exact implemented schema is defined in `src/greek_bess/data/schema.py`. This document gives
the durable semantic contract for official and synthetic price observations.

| Field concept | Meaning |
| --- | --- |
| UTC start/end | Unique timezone-aware delivery interval boundaries |
| Market/Greece time | Human-readable local delivery views, including DST offset/fold context |
| Resolution | Delivery interval duration in minutes |
| Price | DAM market-clearing price, preserving negative and zero values |
| Currency/unit | Normally EUR/MWh; never inferred silently when ambiguous |
| Delivery day/slot | Market-day label and within-day sequence used for completeness checks |
| Source | HEnEx, ENTSO-E or explicitly synthetic |
| Publication version | Source revision/version when available |
| Retrieval/provenance | Source locator, retrieval timestamp and raw SHA-256 when available |
| Quality flags | Missing, duplicate, incomplete-day, synthetic or reconciliation status |

Downstream tables add forecasts, dispatch, state of charge, energy, revenue, degradation,
cohort, cash-flow and scenario fields. Their definitions and signs are documented in the
corresponding implementation reports and CLI summaries.

## Point-in-time feature observations

The exact implemented schema is defined in `src/greek_bess/data/point_in_time.py`; the policy it
enforces is `docs/point_in_time_feature_contract.md`. A price row says what a price was; a
feature row must additionally make it checkable that a bidder could have had the value before
they had to decide.

| Field concept | Meaning |
| --- | --- |
| UTC start/end | Delivery interval the value describes, at the feature's native resolution |
| Market day | CET/CEST date of the interval start; derived, then verified, never supplied alone |
| Source / dataset / variable / area | Closed source set, provider dataset identifier, closed variable registry, and the bidding zone or a declared geography identifier |
| Unit | Must equal the variable registry's unit; a mismatch is refused, never converted |
| Resolution | Native resolution of the datum in minutes; verified against the interval it describes |
| Value | Finite. A missing value is an **absent row**, never `NaN` |
| Publication instant | The earliest instant the provider states the datum was available. It decides availability. For a derived value it is the **latest** of its inputs' instants |
| Retrieval instant | When this project observed the datum; must not precede publication. It is what turns provider-declared evidence into witnessed evidence |
| Source document / revision | Stable identity of the publication and of a re-publication of the same datum. A derived value names every contributing document |
| Raw digest | SHA-256 of the exact bytes the value was decoded from; for a derived value, taken over its inputs' digests in a stated order |
| Forecast issue time / horizon | Model cycle, and the derived, verified minutes from cycle to delivery |
| Availability evidence grade | `witnessed`, `provider_declared`, `assumed` (quarantined) or `unavailable`. The stored grade records what the retrieval established; the effective grade is derived per delivery day against the declared cutoff, and never rises above `assumed` |
| Availability evidence detail | What produced the grade, such as `s3_last_modified` |

Every revision of a datum is stored, including revisions published after any cutoff. Selecting
the decision-time revision is the join's responsibility, not the table's: the storage layer must
not discard the evidence that a revision was superseded.
