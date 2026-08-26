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
