# Implementation report — ADMIE filetype acceptance, 31 August 2026

## Outcome

The live ADMIE catalog identifiers used by the leakage quarantine are now evidence-based. A
74-entry catalog snapshot and non-empty retrieval over delivery days 26-28 August 2026 confirmed
the ISP1 and ISP2 day-ahead load/RES pairs. The declared DAM pair exists in the catalog but
returned no records over the same window and was removed from the operational declaration.

## Changes

- Replaced the non-retrieving DAM pair in `LEAKAGE_RELEVANT_FILETYPES` with the confirmed ISP2
  pair while retaining the confirmed ISP1 pair.
- Recorded the same closed list in the official source register and the timing-workflow default.
- Updated retrieval and audit examples and pinned the declaration in a regression test.
- Recorded catalog metadata, retrieval counts, limitations, status, plan and decision evidence.

No ADMIE workbook was parsed. No gate closure was declared, no publication-time verdict was
produced, no format was accepted and no forecast-feature quarantine was lifted.
